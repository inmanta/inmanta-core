"""
Copyright 2023 Inmanta

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Contact: code@inmanta.com
"""

import datetime
import logging
import uuid
from collections import abc, defaultdict
from collections.abc import Mapping, Sequence
from typing import Literal, Optional, cast

import asyncpg
import asyncpg.connection
import asyncpg.exceptions
import pydantic

import inmanta.exceptions
import inmanta.util
from inmanta import const, data, tracing
from inmanta.const import ResourceState
from inmanta.data import APILIMIT, AVAILABLE_VERSIONS_TO_KEEP, InvalidSort, ResourcePersistentState, RowLockMode
from inmanta.data.dataview import DesiredStateVersionView
from inmanta.data.model import AgentName, DesiredStateVersion
from inmanta.data.model import InmantaModule as InmantaModuleDTO
from inmanta.data.model import (
    InmantaModuleName,
    InmantaModuleVersion,
    PipConfig,
    PromoteTriggerMethod,
    ResourceDiff,
    ResourceMinimal,
    SchedulerStatusReport,
)
from inmanta.data.sqlalchemy import AgentModules, InmantaModule
from inmanta.protocol import handle, methods, methods_v2
from inmanta.protocol.common import ReturnValue, attach_warnings
from inmanta.protocol.exceptions import BadRequest, BaseHttpException, Conflict, NotFound, ServerError
from inmanta.resources import Id
from inmanta.server import (
    SLICE_AGENT_MANAGER,
    SLICE_AUTOSTARTED_AGENT_MANAGER,
    SLICE_DATABASE,
    SLICE_ORCHESTRATION,
    SLICE_RESOURCE,
    SLICE_TRANSPORT,
    agentmanager,
)
from inmanta.server import config as opt
from inmanta.server import diff, protocol
from inmanta.server.services import resourceservice
from inmanta.server.validate_filter import InvalidFilter
from inmanta.types import Apireturn, JsonType, PrimitiveTypes, ResourceIdStr, ResourceVersionIdStr, ReturnTupple

LOGGER = logging.getLogger(__name__)
PLOGGER = logging.getLogger("performance")


PERFORM_CLEANUP: bool = True
# Kill switch for cleanup, for use when working with historical data


def get_printable_name_for_resource_set(native: str | None) -> str:
    if native is None:
        return "<SHARED>"
    return native


class CrossResourceSetDependencyError(Exception):
    def __init__(self, resource_id1: ResourceIdStr, resource_id2: ResourceIdStr) -> None:
        """
        Raised when a cross-resource set dependency was detected between the resource with id
        resource_id1 and resource_id2.
        """
        self.resource_id1 = resource_id1
        self.resource_id2 = resource_id2
        super().__init__(self.get_error_message())

    def get_error_message(self) -> str:
        return (
            f"A dependency exists between resources {self.resource_id1} and {self.resource_id2}, but they belong to"
            f" different resource sets."
        )


class ResourceSetValidator:
    def __init__(self, resources: abc.Set[data.Resource]) -> None:
        self.resources = resources
        self.rid_to_resource_set = {res.resource_id: res.resource_set for res in self.resources}

    def _is_cross_resource_set_dependency(self, res: data.Resource, rid_dependency: ResourceIdStr) -> bool:
        """
        Return True iff the dependency between resource res and the resource with id rid_dependency is a cross-resource set
        dependency.
        """
        if res.resource_set is None:
            # Resource is in shared resource set.
            return False
        if rid_dependency not in self.rid_to_resource_set:
            # A partial compile was done and we have a dependency on a resource in another resource set
            # that is not part of the partial compile.
            return True
        resource_set_dep = self.rid_to_resource_set[rid_dependency]
        if resource_set_dep is None:
            # Dependency towards shared resource set.
            return False
        return res.resource_set != resource_set_dep

    def ensure_no_cross_resource_set_dependencies(self) -> None:
        """
        This method raises a CrossResourceSetDependencyError when a resource in self.resources that belongs to a non-shared
        resource set has a dependency (requires/provides) on another resource that belongs to a different non-shared resource
        set.
        """
        for res in self.resources:
            # It's sufficient to only check the requires relationship. The provides
            # relationship is always a subset of the reverse relationship (provides relationship).
            # The provides relationship only contains the cross-agent dependencies.
            for req in res.get_requires():
                if self._is_cross_resource_set_dependency(res, req):
                    raise CrossResourceSetDependencyError(res.resource_id, req)

    def has_cross_resource_set_dependency(self) -> bool:
        """
        Return True iff a cross resource set dependency exists between the resources in self.resources.
        """
        try:
            self.ensure_no_cross_resource_set_dependencies()
        except CrossResourceSetDependencyError:
            return True
        else:
            return False


class PartialUpdateMerger:
    """
    Class that contains the functionality to merge the shared resources and resources, present in a resource set that is updated
    by the partial compile, together with the resources from the corresponding resources sets in the old version of the model.
    """

    def __init__(
        self,
        env_id: uuid.UUID,
        base_version: int,
        version: int,
        rids_in_partial_compile: abc.Set[ResourceIdStr],
        updated_resource_sets: abc.Set[str],
        deleted_resource_sets: abc.Set[str],
        updated_and_shared_resources_old: abc.Mapping[ResourceIdStr, data.Resource],
        rids_deleted_resource_sets: abc.Set[ResourceIdStr],
    ) -> None:
        """
        :param env_id: The id of the environment for which a partial compile is being done.
        :param base_version: The source version on which the partial compile in based.
        :param version: The version of the new configuration model created by this partial compile.
        :param rids_in_partial_compile: The ids of the resource that are part of the partial compile.
        :param updated_resource_sets: The names of the resource sets that are updated by the partial compile.
        :param deleted_resource_sets: The names of the resource sets that are deleted by the partial compile.
        :param updated_and_shared_resources_old: A dictionary that contains all the resources in base_version that belong
                                                 to a resource set in updated_resource_sets or to the shared resource set.
        :param rids_deleted_resource_sets: The ids of the resources that are in the base_version and that are deleted by this
                                           partial compile.
        """
        self.env_id = env_id
        self.base_version = base_version
        self.version = version
        self.rids_in_partial_compile = rids_in_partial_compile
        self.updated_resource_sets = updated_resource_sets
        self.deleted_resource_sets = deleted_resource_sets
        self.modified_resource_sets = updated_resource_sets | deleted_resource_sets
        self.updated_and_shared_resources_old = updated_and_shared_resources_old
        self.non_shared_resources_in_partial_update_old: abc.Mapping[ResourceIdStr, data.Resource] = {
            rid: r for rid, r in self.updated_and_shared_resources_old.items() if r.resource_set is not None
        }
        self.shared_resources_old: abc.Mapping[ResourceIdStr, data.Resource] = {
            rid: r for rid, r in self.updated_and_shared_resources_old.items() if r.resource_set is None
        }
        self.rids_deleted_resource_sets = rids_deleted_resource_sets

    @classmethod
    async def create(
        cls,
        env_id: uuid.UUID,
        base_version: int,
        version: int,
        rids_in_partial_compile: abc.Set[ResourceIdStr],
        updated_resource_sets: abc.Set[str],
        deleted_resource_sets: abc.Set[str],
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> "PartialUpdateMerger":
        """
        A replacement constructor method for this class. This method is used to work around the limitation that no async
        calls can be done in a constructor. See docstring real constructor for meaning of arguments.
        """
        updated_and_shared_resources_old: abc.Mapping[ResourceIdStr, data.Resource] = (
            await data.Resource.get_resources_in_resource_sets(
                environment=env_id,
                version=base_version,
                resource_sets=updated_resource_sets,
                include_shared_resources=True,
                connection=connection,
            )
        )
        rids_deleted_resource_sets: abc.Set[ResourceIdStr] = {
            rid
            for rid in (
                await data.Resource.get_resources_in_resource_sets(
                    environment=env_id,
                    version=base_version,
                    resource_sets=deleted_resource_sets,
                    connection=connection,
                )
            ).keys()
        }
        return PartialUpdateMerger(
            env_id,
            base_version,
            version,
            rids_in_partial_compile,
            updated_resource_sets,
            deleted_resource_sets,
            updated_and_shared_resources_old,
            rids_deleted_resource_sets,
        )

    def merge_updated_and_shared_resources(
        self, updated_and_shared_resources: abc.Sequence[data.Resource]
    ) -> dict[ResourceIdStr, data.Resource]:
        """
         Separates named resource sets from the shared resource set and expands the shared set with the shared resources in
         the previous model version.

        :param updated_and_shared_resources: The resources that are part of the partial compile.
        :returns: The subset of resources in the new version of the configuration model that belong to the shared resource set
                  or a resource set that is updated by this partial compile.
        """
        shared_resources = {r.resource_id: r for r in updated_and_shared_resources if r.resource_set is None}
        updated_resources = {r.resource_id: r for r in updated_and_shared_resources if r.resource_set is not None}
        shared_resources_merged = {r.resource_id: r for r in self._merge_shared_resources(shared_resources)}
        # Updated go last, so that in case of overlap, we get the updated one
        # Validation on move is done later
        result = {**shared_resources_merged, **updated_resources}
        self._validate_constraints(result)
        return result

    def _validate_constraints(self, new_updated_and_shared_resources: abc.Mapping[ResourceIdStr, data.Resource]) -> None:
        """
        Validate whether the new updated and shared resources that results from the merging the old version of the model
        with resources of the partial compile, are compliant with the constraints of a partial compile.

        :param new_updated_and_shared_resources: The resources that have to be validated.
        """
        for res_id, res in new_updated_and_shared_resources.items():
            if res.resource_id not in self.updated_and_shared_resources_old:
                continue
            matching_resource_old_model = self.updated_and_shared_resources_old[res.resource_id]

            if (
                res.resource_set != matching_resource_old_model.resource_set
                and matching_resource_old_model.resource_set not in self.modified_resource_sets
            ):
                # We can't move resource
                # Unless between resource sets we are updating
                # Shared set is never in modified_resource_sets, so no escape from there
                raise BadRequest(
                    "A partial compile only migrate resources between resource set that are pushed together:"
                    f" trying to move {res.resource_id} from resource set "
                    f"{get_printable_name_for_resource_set(matching_resource_old_model.resource_set)} "
                    f"to {get_printable_name_for_resource_set(res.resource_set)}."
                )

            if res.resource_set is None and res.attribute_hash != matching_resource_old_model.attribute_hash:
                raise BadRequest(f"Resource ({res.resource_id}) without a resource set cannot be updated via a partial compile")

            resource_set_validator = ResourceSetValidator(set(new_updated_and_shared_resources.values()))
            try:
                resource_set_validator.ensure_no_cross_resource_set_dependencies()
            except CrossResourceSetDependencyError as e:
                raise BadRequest(e.get_error_message())

    def _merge_shared_resources(self, shared_resources_new: dict[ResourceIdStr, data.Resource]) -> abc.Sequence[data.Resource]:
        """
        Merge the set of shared resources present in the old version of the model together with the set of shared resources
        present in the partial compile.

        :param shared_resources_new: The set of shared resources present in the partial compile.
        :returns: The set of shared resources that should be present in the new version of the model.
        """
        all_rids_shared_resources = set(self.shared_resources_old.keys()) | set(shared_resources_new.keys())
        result = []
        for rid_shared_resource in all_rids_shared_resources:
            if rid_shared_resource in shared_resources_new and rid_shared_resource in self.shared_resources_old:
                # Merge requires/provides shared resource
                old_shared_resource = self.shared_resources_old[rid_shared_resource]
                new_shared_resource = shared_resources_new[rid_shared_resource]
                res = self._merge_requires_and_provides_of_shared_resource(old_shared_resource, new_shared_resource)
            elif rid_shared_resource in shared_resources_new:
                # New shared resource in partial compile
                res = shared_resources_new[rid_shared_resource]
            else:
                # Old shared resource not referenced by partial compile
                res_old = self.shared_resources_old[rid_shared_resource]
                res = res_old.copy_for_partial_compile(new_version=self.version)
                res = self._clean_requires_provides_old_shared_resource(res)
            result.append(res)
        return result

    def _should_keep_dependency_old_shared_resources(self, rid_dependency: ResourceIdStr) -> bool:
        """
        Return True iff the given dependency present in a shared resource from the base version should be retained
        in the new version of the model.
        """
        if rid_dependency in self.rids_deleted_resource_sets:
            # Resource belongs to a deleted resource set
            return False
        if rid_dependency in self.non_shared_resources_in_partial_update_old:
            # If this dependency is still present in the new version of the model, this dependency
            # will be present in the resources that are part of the partial compile.
            return False
        return True

    def _clean_requires_provides_old_shared_resource(self, resource: data.Resource) -> data.Resource:
        """
        Cleanup the requires/provides relationship for shared resources that are not present in the partial compile
        and that were copied from the old version of the model.
        """
        resource.attributes["requires"] = [
            rid for rid in resource.attributes["requires"] if self._should_keep_dependency_old_shared_resources(rid)
        ]
        resource.provides = [rid for rid in resource.provides if self._should_keep_dependency_old_shared_resources(rid)]
        return resource

    def _merge_requires_and_provides_of_shared_resource(self, old: data.Resource, new: data.Resource) -> data.Resource:
        """
        Update the requires and provides relationship of `new` to make it consistent with the new version of the model.

        :param old: The shared resource present in the old version of the model.
        :param new: The shared resource part of the incremental compile.
        """
        new.provides = list(self._merge_dependencies_shared_resource(old.provides, new.provides))
        new.attributes["requires"] = self._merge_dependencies_shared_resource(old.get_requires(), new.get_requires())
        return new

    def _merge_dependencies_shared_resource(
        self, old_deps: abc.Sequence[ResourceIdStr], new_deps: abc.Sequence[ResourceIdStr]
    ) -> abc.Sequence[ResourceIdStr]:
        """
        Merge the dependencies for a certain shared resource together to make it consistent with the new version of the model.

        :param old_deps: The set of dependencies present in the old version of the shared resource.
        :param new_deps: The set of dependencies present in the shared resource that is part of the partial compile.
        """
        old_deps_cleaned: abc.Set[ResourceIdStr] = {
            dep for dep in old_deps if self._should_keep_dependency_old_shared_resources(dep)
        }
        return list(old_deps_cleaned | set(new_deps))

    async def merge_unknowns(
        self, unknowns_in_partial_compile: abc.Sequence[data.UnknownParameter]
    ) -> abc.Sequence[data.UnknownParameter]:
        """
        Merge all relevant, unresolved unknowns from the old version of the model together with the unknowns
        of the partial compile.
        """
        old_unresolved_unknowns_to_keep = [
            uk.copy(self.version)
            for uk in await data.UnknownParameter.get_unknowns_to_copy_in_partial_compile(
                environment=self.env_id,
                source_version=self.base_version,
                updated_resource_sets=self.updated_resource_sets,
                deleted_resource_sets=self.deleted_resource_sets,
                rids_in_partial_compile=self.rids_in_partial_compile,
            )
        ]
        return [*old_unresolved_unknowns_to_keep, *unknowns_in_partial_compile]


class OrchestrationService(protocol.ServerSlice):
    """Resource Manager service"""

    agentmanager_service: "agentmanager.AgentManager"
    autostarted_agent_manager: "agentmanager.AutostartedAgentManager"
    resource_service: "resourceservice.ResourceService"

    def __init__(self) -> None:
        super().__init__(SLICE_ORCHESTRATION)

    def get_dependencies(self) -> list[str]:
        return [SLICE_RESOURCE, SLICE_AGENT_MANAGER, SLICE_DATABASE]

    def get_depended_by(self) -> list[str]:
        return [SLICE_TRANSPORT]

    async def prestart(self, server: protocol.Server) -> None:
        await super().prestart(server)
        self.agentmanager_service = cast("agentmanager.AgentManager", server.get_slice(SLICE_AGENT_MANAGER))
        self.autostarted_agent_manager = cast(
            agentmanager.AutostartedAgentManager, server.get_slice(SLICE_AUTOSTARTED_AGENT_MANAGER)
        )
        self.resource_service = cast("resourceservice.ResourceService", server.get_slice(SLICE_RESOURCE))

    async def start(self) -> None:
        if PERFORM_CLEANUP:
            self.schedule(self._purge_versions, opt.server_purge_version_interval.get(), cancel_on_stop=False)
            self.add_background_task(self._purge_versions())
        await super().start()

    async def _purge_versions(self) -> None:
        """
        Purge versions from the database
        """
        # TODO: move to data and use queries for delete
        async with data.Environment.get_connection() as connection:
            envs = await data.Environment.get_list(halted=False, connection=connection)
            for env_item in envs:
                # get available versions
                n_versions = await env_item.get(AVAILABLE_VERSIONS_TO_KEEP, connection=connection)
                assert isinstance(n_versions, int)
                versions = await data.ConfigurationModel.get_list(
                    environment=env_item.id, connection=connection, order_by_column="version", order="DESC"
                )
                if len(versions) > n_versions:
                    version_dict = {x.version: x for x in versions}
                    latest_released_version: Optional[int] = next((v.version for v in versions if v.released), None)
                    if latest_released_version is not None:
                        # Never cleanup the latest released version
                        del version_dict[latest_released_version]
                    delete_list = sorted(version_dict.keys())
                    delete_list = delete_list[:-n_versions]
                    if delete_list:
                        LOGGER.info("Removing %s available versions from environment %s", len(delete_list), env_item.id)
                    for v in delete_list:
                        await version_dict[v].delete_cascade(connection=connection)

                await ResourcePersistentState.trim(env_item.id, connection=connection)
            # Cleanup old agents from agent table in db
            await data.Agent.clean_up()

    @handle(methods.list_versions, env="tid")
    async def list_version(self, env: data.Environment, start: Optional[int] = None, limit: Optional[int] = None) -> Apireturn:
        if (start is None and limit is not None) or (limit is None and start is not None):
            raise ServerError("Start and limit should always be set together.")

        if start is None or limit is None:
            start = 0
            limit = data.APILIMIT

        if limit > APILIMIT:
            raise BadRequest(f"limit parameter can not exceed {APILIMIT}, got {limit}.")

        models = await data.ConfigurationModel.get_versions(env.id, start, limit)
        count = len(models)

        d = {
            "versions": models,
            "start": start,
            "limit": limit,
            "count": count,
        }

        return 200, d

    @handle(methods.get_version, version_id="id", env="tid")
    async def get_version(
        self,
        env: data.Environment,
        version_id: int,
        include_logs: Optional[bool] = None,
        log_filter: Optional[str] = None,
        limit: Optional[int] = 0,
    ) -> Apireturn:
        version = await data.ConfigurationModel.get_version(env.id, version_id)
        if version is None:
            return 404, {"message": "The given configuration model does not exist yet."}

        resources = await data.Resource.get_resources_for_version(env.id, version_id, no_obj=True)
        if resources is None:
            return 404, {"message": "The given configuration model does not exist yet."}

        if limit is None:
            limit = APILIMIT
        elif limit > APILIMIT:
            raise BadRequest(
                f"limit parameter can not exceed {APILIMIT}, got {limit}."
                f" To retrieve more entries, use /api/v2/resource_actions"
            )

        resources_out: list[JsonType] = []
        d = {"model": version, "resources": resources_out}
        resource_action_lookup: dict[ResourceVersionIdStr, list[data.ResourceAction]] = {}

        for res_dict in resources:
            resources_out.append(res_dict)
            if bool(include_logs):
                actions: list[data.ResourceAction] = []
                res_dict["actions"] = actions
                resource_action_lookup[res_dict["resource_version_id"]] = actions

        if include_logs:
            # get all logs, unsorted
            all_logs = await data.ResourceAction.get_logs_for_version(env.id, version_id, log_filter, limit)
            for log in all_logs:
                for resource_version_id in log.resource_version_ids:
                    resource_action_lookup[resource_version_id].append(log)

        d["unknowns"] = await data.UnknownParameter.get_list(environment=env.id, version=version_id)

        return 200, d

    @handle(methods.delete_version, version_id="id", env="tid")
    async def delete_version(self, env: data.Environment, version_id: int) -> Apireturn:
        async with data.ConfigurationModel.get_connection() as connection:
            version = await data.ConfigurationModel.get_version(env.id, version_id, connection=connection)

            if version is None:
                return 404, {"message": "The given configuration model does not exist yet."}

            active_version = await data.ConfigurationModel.get_latest_version(env.id, connection=connection)
            if active_version and active_version.version == version.version:
                raise BadRequest("Cannot delete the active version")

            await version.delete_cascade(connection=connection)
            # Make sure the ResourcePersistentState is consistent with resources
            await ResourcePersistentState.trim(env.id, connection=connection)
            return 200

    @handle(methods_v2.reserve_version, env="tid")
    async def reserve_version(self, env: data.Environment) -> int:
        return await env.get_next_version()

    @handle(methods_v2.get_pip_config, env="tid")
    async def get_pip_config(
        self,
        env: data.Environment,
        version: int,
    ) -> Optional[PipConfig]:
        version_object = await data.ConfigurationModel.get_version(env.id, version)
        if version_object is None:
            raise NotFound(f"No configuration model with version {version} exists.")
        out = version_object.pip_config
        return out

    def _create_dao_resources_from_api_resources(
        self,
        env_id: uuid.UUID,
        resources: list[JsonType],
        resource_state: dict[ResourceIdStr, Literal[ResourceState.available, ResourceState.undefined]],
        resource_sets: dict[ResourceIdStr, Optional[str]],
        set_version: Optional[int] = None,
    ) -> dict[ResourceIdStr, data.Resource]:
        """
        This method converts the resources sent to the put_version or put_partial endpoint to dao Resource objects.
        The resulting resource objects will have their provides set up correctly for cross agent dependencies
        and the version field of these resources will be set to set_version if provided.

        An exception will be raised when the one of the following constraints is not satisfied:
            * A resource present in the resource_sets parameter is not present in the resources dictionary.
            * The dependency graph of the provided resources is not closed.
        """
        rid_to_resource = {}
        # The content of the requires attribute for all the resources
        all_requires: set[ResourceIdStr] = set()
        # list of all resources which have a cross agent dependency, as a tuple, (dependant,requires)
        cross_agent_dep: list[tuple[data.Resource, Id]] = []
        for res_dict in resources:
            # Verify that the version field and the version in the resource version id field match
            version_part_of_resource_id = Id.parse_id(res_dict["id"]).version
            if "version" in res_dict and res_dict["version"] != version_part_of_resource_id:
                raise BadRequest(
                    f"Invalid resource: The version in the id field ({res_dict['id']}) doesn't match the version in the"
                    f" version field ({res_dict['version']})."
                )
            res_obj = data.Resource.new(env_id, res_dict["id"])
            # Populate is_undefined field
            if res_obj.resource_id in resource_state:
                res_obj.is_undefined = const.ResourceState[resource_state[res_obj.resource_id]] == const.ResourceState.undefined
            # Populate resource_set field
            if res_obj.resource_id in resource_sets:
                res_obj.resource_set = resource_sets[res_obj.resource_id]

            # Populate attributes field of resources
            attributes = {}
            for field, value in res_dict.items():
                if field not in {"id", "version"}:
                    attributes[field] = value
            res_obj.attributes = attributes
            res_obj.make_hash()

            # Update the version fields
            if set_version is not None:
                res_obj.model = set_version

            # find cross agent dependencies
            agent = res_obj.agent
            if "requires" not in attributes:
                LOGGER.warning("Received resource without requires attribute (%s)", res_obj.resource_id)
            else:
                # Collect all requires as resource_ids instead of resource version ids
                cleaned_requires = []
                for req in attributes["requires"]:
                    rid = Id.parse_id(req)
                    all_requires.add(rid.resource_str())
                    if rid.get_agent_name() != agent:
                        # it is a CAD
                        cross_agent_dep.append((res_obj, rid))
                    cleaned_requires.append(rid.resource_str())
                attributes["requires"] = cleaned_requires

            rid_to_resource[res_obj.resource_id] = res_obj

        # hook up all CADs
        for f, t in cross_agent_dep:
            res_obj = rid_to_resource[t.resource_str()]
            res_obj.provides.append(f.resource_id)

        rids = set(rid_to_resource.keys())

        # Sanity checks
        superfluous_ids = set(resource_sets.keys()) - rids
        if superfluous_ids:
            raise BadRequest(
                "The following resource ids provided in the resource_sets parameter are not present "
                f"in the resources list: {', '.join(superfluous_ids)}"
            )
        if not all_requires.issubset(rids):
            raise BadRequest(
                "The model should have a dependency graph that is closed and no dangling dependencies:"
                f" {all_requires - rids}"
            )

        return rid_to_resource

    def _get_skipped_for_undeployable(
        self, resources: abc.Sequence[data.Resource], undeployable_ids: abc.Sequence[ResourceIdStr]
    ) -> abc.Sequence[ResourceIdStr]:
        """
        Return the resources that are skipped_for_undeployable given the full set of resources and
        the resource ids of the resources that are undeployable.

        :param resources: All resources in the model.
        :param undeployable_ids: The ids of the resource that are undeployable.
        """
        # Build up provides tree
        provides_tree: dict[ResourceIdStr, list[ResourceIdStr]] = defaultdict(list)
        for r in resources:
            if "requires" in r.attributes:
                for req in r.attributes["requires"]:
                    req_id = Id.parse_id(req)
                    provides_tree[req_id.resource_str()].append(r.resource_id)
        # Find skipped for undeployables
        work = list(undeployable_ids)
        skippeable: set[ResourceIdStr] = set()
        while len(work) > 0:
            current = work.pop()
            if current in skippeable:
                continue
            skippeable.add(current)
            work.extend(provides_tree[current])
        return list(skippeable - set(undeployable_ids))

    async def _check_version_info(
        self,
        modules_version_in_current_export: Mapping[InmantaModuleName, InmantaModuleDTO],
        registered_modules_version: Mapping[InmantaModuleName, InmantaModuleVersion],
    ) -> None:
        """
        Make sure that modules used in this partial version are either new modules, or that the version
        being used is the same as the registered version for the base compile.


        :param modules_version_in_current_export: Inmanta modules used to deploy resources in
            the current export.
        :param registered_modules_version: All Inmanta module versions used in the base compile.
        :raises BadRequest: Some module version in the current export differs from its
            registered counterpart.
        """

        for inmanta_module_name, module_data in modules_version_in_current_export.items():

            if inmanta_module_name not in registered_modules_version:
                # This didn't exist in the previous version: nothing
                # to check, we always allow new modules registration.
                continue

            registered_version = registered_modules_version[inmanta_module_name]
            module_version = module_data.version
            if registered_version != module_version:
                raise BadRequest(
                    f"Cannot perform partial export because the source code for module {inmanta_module_name} in this "
                    "partial version is different from the currently registered source code. Consider running a full "
                    "export instead. Alternatively, if you are sure the new code is compatible and want to forcefully "
                    "update, you can bypass this version check with the `--allow-handler-code-update` CLI option."
                )

    async def _register_agent_code(
        self,
        partial_base_version: int | None,
        version: int,
        environment: uuid.UUID,
        module_version_info: Mapping[InmantaModuleName, InmantaModuleDTO],
        *,
        allow_handler_code_update: bool = False,
        connection: asyncpg.connection.Connection,
    ) -> None:
        """
        Helper method for the _put_version method.

        Register the relevant inmanta modules for all agents that need them for this version.
        Use the `module_version_info` dict to populate the relevant tables
        AgentModules, InmantaModule and ModuleFiles.

        The `module_version_info` map contains inmanta modules used by resources that are
        being exported in this version.

        For partial compiles, this method makes sure that:
            - the version of modules in this partial export is the same as the one used in the base version.
                (this check can be exceptionally bypassed with the allow_handler_code_update flag)
            - all other inmanta modules registered in the base version are registered again
              for this version. (e.g. to be able to repair an existing resource that wasn't
              exported in this partial compile)

        :param partial_base_version: In case of a partial compile, base version it is based on.
        :param version: Configuration model version.
        :param environment: Environment this compile belongs to.
        :param module_version_info: Inmanta module information about inmanta modules that are used by
            resources exported in this version.
        :param allow_handler_code_update: In case of a partial compile, this flag will disable the check
            for source code consistency between the base version and the current partial version.
        :param connection: DB connection expected to be managed by the caller method.
        """

        modules_to_register: dict[InmantaModuleName, InmantaModuleDTO] = {
            module_name: inmanta_module
            for module_name, inmanta_module in module_version_info.items()
            if inmanta_module.for_agents
        }
        module_usage_info: dict[InmantaModuleName, tuple[InmantaModuleVersion, set[AgentName]]] = {}

        if partial_base_version is not None:
            module_usage_info = await AgentModules.get_registered_modules_data(
                model_version=partial_base_version, environment=environment, connection=connection
            )

            if not allow_handler_code_update:
                await self._check_version_info(
                    modules_version_in_current_export=modules_to_register,
                    registered_modules_version={
                        module_name: module_data[0] for module_name, module_data in module_usage_info.items()
                    },
                )

        for module_name, module in modules_to_register.items():
            current_module_version = module.version
            current_module_agent_set = set(module.for_agents)

            if module_name in module_usage_info:
                # This module was previously known: make sure we register agents
                # that were already using it before in this model version
                current_module_agent_set.update(module_usage_info[module_name][1])

            module_usage_info[module_name] = (current_module_version, current_module_agent_set)

        await InmantaModule.register_modules(environment=environment, modules=modules_to_register, connection=connection)
        await AgentModules.register_modules_for_agents(
            model_version=version,
            environment=environment,
            module_usage_info=module_usage_info,
            connection=connection,
        )

    async def _put_version(
        self,
        env: data.Environment,
        version: int,
        rid_to_resource: dict[ResourceIdStr, data.Resource],
        unknowns: abc.Sequence[data.UnknownParameter],
        version_info: Optional[JsonType] = None,
        resource_sets: Optional[dict[ResourceIdStr, Optional[str]]] = None,
        partial_base_version: Optional[int] = None,
        removed_resource_sets: Optional[list[str]] = None,
        pip_config: Optional[PipConfig] = None,
        *,
        connection: asyncpg.connection.Connection,
        module_version_info: Mapping[InmantaModuleName, InmantaModuleDTO],
        allow_handler_code_update: bool = False,
    ) -> None:
        """
        :param rid_to_resource: This parameter should contain all the resources when a full compile is done.
                                When a partial compile is done, it should contain all the resources that belong to the
                                updated resource sets or the shared resource sets.
        :param unknowns: This parameter should contain all the unknowns for all the resources in the new version of the model.
                         Also the unknowns for resources that are not present in rid_to_resource.
        :param partial_base_version: When a partial compile is done, this parameter contains the version of the
                                     configurationmodel this partial compile was based on. Otherwise, this parameter should be
                                     None.
        :param removed_resource_sets: When a partial compile is done, this parameter should indicate the names of the resource
                                      sets that are removed by the partial compile. When no resource sets are removed by
                                      a partial compile or when a full compile is done, this parameter can be set to None.
        :param module_version_info: Mapping of module name to in-memory representation of a module. This represents all inmanta
            modules that might be used during deployment of resources in the current [partial] version.
        :param allow_handler_code_update: During partial compiles (i.e. partial_base_version is not None), a check is performed
            to make sure the source code of modules in this partial version is identical to the source code in the base
            version. Set this parameter to True to bypass this check.

        Pre-conditions:
            * The requires and provides relationships of the resources in rid_to_resource must be set correctly. For a
              partial compile, this means it is assumed to be valid with respect to all absolute constraints that apply to
              partial compiles. Constraints that are relative to the base version will be verified by this method.
            * When a partial compile was done, all resources in rid_to_resource must meet the constraints of a partial compile.
            * The resource sets defined in the removed_resource_sets argument must not overlap with the resource sets present
              in the resource_sets argument.

        When a partial compile is done, the undeployable and skipped_for_undeployable resources of a configurationmodel are
        copied from the old version to the new version. This operation is safe because the only resources missing from
        rid_to_resource are resources that belong to an unchanged, non-shared resource set. Those resources can only have
        cross resource set dependencies in a non-shared resource set and the latter resource set cannot be changed by a partial
        compile.

        Validations done by this method:
            * In case of a full export: Checks whether this version has any requires-provides across resource sets and
                                        sets the is_suitable_for_partial_compiles field appropriately, indicating whether
                                        this version is eligible to be used as a base version for a future partial compile.
            * In case of a partial export: Verifies that no resources moved resource sets.
        """
        is_partial_update = partial_base_version is not None

        if resource_sets is None:
            resource_sets = {}

        if removed_resource_sets is None:
            removed_resource_sets = []

        if version > env.last_version:
            raise BadRequest(
                f"The version number used is {version} "
                f"which is higher than the last outstanding reservation {env.last_version}"
            )
        if version <= 0:
            raise BadRequest(f"The version number used ({version}) is not positive")

        for r in rid_to_resource.values():
            if r.model != version:
                raise BadRequest(
                    f"The resource version of resource {r.resource_version_id} does not match the version argument "
                    f"(version: {version})"
                )

        for rid_name in resource_sets.keys():
            try:
                Id.parse_id(rid_name)
            except Exception as e:
                raise BadRequest("Invalid resource id in resource set: %s" % str(e))

        started = datetime.datetime.now().astimezone()

        resource_set_validator = ResourceSetValidator(set(rid_to_resource.values()))
        undeployable_ids: abc.Sequence[ResourceIdStr] = [
            res.resource_id for res in rid_to_resource.values() if res.is_undefined
        ]
        updated_resource_sets: abc.Set[str] = {sr for sr in resource_sets.values() if sr is not None}
        deleted_resource_sets_as_set: abc.Set[str] = set(removed_resource_sets)
        async with connection.transaction():
            try:
                if is_partial_update:
                    # Make mypy happy
                    assert partial_base_version is not None
                    cm = await data.ConfigurationModel.create_for_partial_compile(
                        env_id=env.id,
                        version=version,
                        # When a partial compile is done, the total will be updated in cm.recalculate_total()
                        # with all the resources that belong to a resource set that was not updated.
                        total=len(rid_to_resource),
                        version_info=version_info,
                        undeployable=undeployable_ids,
                        skipped_for_undeployable=sorted(
                            self._get_skipped_for_undeployable(list(rid_to_resource.values()), undeployable_ids)
                        ),
                        partial_base=partial_base_version,
                        pip_config=pip_config,
                        updated_resource_sets=updated_resource_sets,
                        deleted_resource_sets=deleted_resource_sets_as_set,
                        connection=connection,
                    )
                else:
                    cm = data.ConfigurationModel(
                        environment=env.id,
                        version=version,
                        date=datetime.datetime.now().astimezone(),
                        total=len(rid_to_resource),
                        version_info=version_info,
                        undeployable=undeployable_ids,
                        skipped_for_undeployable=sorted(
                            self._get_skipped_for_undeployable(list(rid_to_resource.values()), undeployable_ids)
                        ),
                        pip_config=pip_config,
                        is_suitable_for_partial_compiles=not resource_set_validator.has_cross_resource_set_dependency(),
                    )
                    await cm.insert(connection=connection)
            except asyncpg.exceptions.UniqueViolationError:
                raise ServerError("The given version is already defined. Versions should be unique.")

            with tracing.span("put_version.partial"):
                all_ids: set[Id] = {Id.parse_id(rid, version) for rid in rid_to_resource.keys()}
                if is_partial_update:
                    # Make mypy happy
                    assert partial_base_version is not None
                    # This dict maps a resource id to its resource set for unchanged resource sets.
                    rids_unchanged_resource_sets: dict[ResourceIdStr, str] = (
                        await data.Resource.copy_resources_from_unchanged_resource_set(
                            environment=env.id,
                            source_version=partial_base_version,
                            destination_version=version,
                            updated_resource_sets=updated_resource_sets,
                            deleted_resource_sets=deleted_resource_sets_as_set,
                            connection=connection,
                        )
                    )
                    resources_that_moved_resource_sets = rids_unchanged_resource_sets.keys() & rid_to_resource.keys()
                    if resources_that_moved_resource_sets:
                        msg = (
                            "The following Resource(s) cannot be migrated to a different resource set using a partial compile, "
                            "a full compile is necessary for this process:\n"
                        )
                        msg += "\n".join(
                            f"    {rid} moved from {get_printable_name_for_resource_set(rids_unchanged_resource_sets[rid])} "
                            f"to {get_printable_name_for_resource_set(resource_sets.get(rid))}"
                            for rid in resources_that_moved_resource_sets
                        )

                        raise BadRequest(msg)
                    all_ids |= {Id.parse_id(rid, version) for rid in rids_unchanged_resource_sets.keys()}

                await data.Resource.insert_many(list(rid_to_resource.values()), connection=connection)
                await cm.recalculate_total(connection=connection)

            await data.UnknownParameter.insert_many(unknowns, connection=connection)

            all_agents: set[str] = {res.agent for res in rid_to_resource.values()}
            all_agents.add(const.AGENT_SCHEDULER_ID)

            for agent in all_agents:
                await self.agentmanager_service.ensure_agent_registered(env, agent, connection=connection)

            await self._register_agent_code(
                partial_base_version,
                version,
                env.id,
                module_version_info,
                allow_handler_code_update=allow_handler_code_update,
                connection=connection,
            )

            # Don't log ResourceActions without resource_version_ids, because
            # no API call exists to retrieve them.
            all_rvids = [i.resource_version_str() for i in all_ids]
            if all_rvids:
                now = datetime.datetime.now().astimezone()
                log_line = data.LogLine.log(logging.INFO, "Successfully stored version %(version)d", version=version)
                self.resource_service.log_resource_action(env.id, list(all_rvids), logging.INFO, now, log_line.msg)
                ra = data.ResourceAction(
                    environment=env.id,
                    version=version,
                    resource_version_ids=all_rvids,
                    action_id=uuid.uuid4(),
                    action=const.ResourceAction.store,
                    started=started,
                    finished=now,
                    messages=[log_line],
                )
                await ra.insert(connection=connection)

        LOGGER.debug("Successfully stored version %d", version)

    async def _trigger_auto_deploy(
        self,
        env: data.Environment,
        version: int,
    ) -> None:
        """
        Triggers auto-deploy for stored resources. Must be called only after transaction that stores resources has been allowed
        to commit. If not respected, the auto deploy might work on stale data, likely resulting in resources hanging in the
        deploying state.
        """
        auto_deploy = await env.get(data.AUTO_DEPLOY)
        if auto_deploy:
            LOGGER.debug("Auto deploying version %d", version)
            self.add_background_task(self.release_version(env, version, push=False, agent_trigger_method=None))

    def _create_unknown_parameter_daos_from_api_unknowns(
        self, env_id: uuid.UUID, version: int, unknowns: Optional[list[dict[str, PrimitiveTypes]]] = None
    ) -> list[data.UnknownParameter]:
        """
        Create UnknownParameter dao's from the unknowns dictionaries passed through the put_version() and put_partial API
        endpoint.
        """
        if not unknowns:
            return []
        result = []
        for uk in unknowns:
            if "resource" not in uk:
                uk["resource"] = ""
            if "metadata" not in uk:
                uk["metadata"] = {}
            unknown_parameter = data.UnknownParameter(
                resource_id=uk["resource"],
                name=uk["parameter"],
                source=uk["source"],
                environment=env_id,
                version=version,
                metadata=uk["metadata"],
            )
            result.append(unknown_parameter)
        return result

    @handle(methods.put_version, env="tid")
    async def put_version(
        self,
        env: data.Environment,
        version: int,
        resources: list[JsonType],
        resource_state: dict[ResourceIdStr, Literal[ResourceState.available, ResourceState.undefined]],
        unknowns: list[dict[str, PrimitiveTypes]],
        version_info: JsonType,
        module_version_info: Mapping[InmantaModuleName, InmantaModuleDTO],
        compiler_version: Optional[str] = None,
        resource_sets: Optional[dict[ResourceIdStr, Optional[str]]] = None,
        pip_config: Optional[PipConfig] = None,
    ) -> Apireturn:
        """
        :param unknowns: dict with the following structure
                            {
                             "resource": ResourceIdStr,
                             "parameter": str,
                             "source": str
                            }
        """
        if resource_sets is None:
            resource_sets = {}

        if not compiler_version:
            raise BadRequest("Older compiler versions are no longer supported, please update your compiler")

        unknowns_objs = self._create_unknown_parameter_daos_from_api_unknowns(env.id, version, unknowns)
        rid_to_resource: dict[ResourceIdStr, data.Resource] = self._create_dao_resources_from_api_resources(
            env_id=env.id,
            resources=resources,
            resource_state=resource_state,
            resource_sets=resource_sets,
        )

        async with data.Resource.get_connection() as con:
            # We don't allow connection reuse here, because the last line in this block can't tolerate a transaction
            # assert not con.is_in_transaction()
            async with con.transaction():
                # Acquire a lock that conflicts with the lock acquired by put_partial but not with itself
                await env.put_version_lock(shared=True, connection=con)
                await self._put_version(
                    env,
                    version,
                    rid_to_resource,
                    unknowns_objs,
                    version_info,
                    resource_sets,
                    pip_config=pip_config,
                    connection=con,
                    module_version_info=module_version_info or {},
                )
            # This must be outside all transactions, as it relies on the result of _put_version
            # and it starts a background task, so it can't re-use this connection
            await self._trigger_auto_deploy(env, version)

        return 200

    @handle(methods_v2.put_partial, env="tid")
    async def put_partial(
        self,
        env: data.Environment,
        resources: object,
        resource_state: Optional[dict[ResourceIdStr, Literal[ResourceState.available, ResourceState.undefined]]] = None,
        unknowns: Optional[list[dict[str, PrimitiveTypes]]] = None,
        version_info: Optional[JsonType] = None,
        resource_sets: Optional[dict[ResourceIdStr, Optional[str]]] = None,
        removed_resource_sets: Optional[list[str]] = None,
        pip_config: Optional[PipConfig] = None,
        module_version_info: dict[str, InmantaModuleDTO] | None = None,
        allow_handler_code_update: bool = False,
    ) -> ReturnValue[int]:
        """
        :param unknowns: dict with the following structure
                    {
                     "resource": ResourceIdStr,
                     "parameter": str,
                     "source": str
                    }
        """
        if resource_state is None:
            resource_state = {}
        if unknowns is None:
            unknowns = []
        if resource_sets is None:
            resource_sets = {}
        if removed_resource_sets is None:
            removed_resource_sets = []

        try:
            pydantic.TypeAdapter(abc.Sequence[ResourceMinimal]).validate_python(resources)
        except pydantic.ValidationError:
            raise BadRequest(
                "Type validation failed for resources argument. "
                f"Expected an argument of type List[Dict[str, Any]] but received {resources}"
            )
        else:
            # Make mypy happy
            resources = cast(list[JsonType], resources)

        # validate resources before any side effects take place
        for r in resources:
            rid = Id.parse_id(r["id"])
            if rid.get_version() != 0:
                raise BadRequest("Resources for partial export should not contain version information")

        intersection: set[str] = set(resource_sets.values()).intersection(set(removed_resource_sets))
        if intersection:
            raise BadRequest(
                "Following resource sets are present in the removed resource sets and in the resources that are exported: "
                f"{intersection}"
            )

        async with data.Resource.get_connection() as con:
            async with con.transaction():
                # Acquire a lock that conflicts with itself and with the lock acquired by put_version
                await env.put_version_lock(shared=False, connection=con)

                # Only request a new version once the resource lock has been acquired to ensure a monotonic version history
                version: int = await env.get_next_version(connection=con)

                current_versions: abc.Sequence[data.ConfigurationModel] = await data.ConfigurationModel.get_versions(
                    env.id, limit=1
                )
                if not current_versions:
                    raise BadRequest("A partial export requires a base model but no versions have been exported yet.")

                base_model = current_versions[0]
                base_version: int = base_model.version
                if not base_model.is_suitable_for_partial_compiles:
                    resources_in_base_version = await data.Resource.get_resources_for_version(env.id, base_version)
                    resource_set_validator = ResourceSetValidator(set(resources_in_base_version))
                    try:
                        resource_set_validator.ensure_no_cross_resource_set_dependencies()
                    except CrossResourceSetDependencyError as e:
                        raise BadRequest(
                            f"Base version {base_version} is not suitable for a partial compile. {e.get_error_message()}"
                        )
                    else:
                        # This should never happen
                        LOGGER.warning(
                            "Base version %d was marked as not suitable for partial compiles, but no cross resource set"
                            " dependencies were found.",
                            base_version,
                        )

                rid_to_resource: dict[ResourceIdStr, data.Resource] = self._create_dao_resources_from_api_resources(
                    env_id=env.id,
                    resources=resources,
                    resource_state=resource_state,
                    resource_sets=resource_sets,
                    set_version=version,
                )

                updated_resource_sets: abc.Set[str] = {sr_name for sr_name in resource_sets.values() if sr_name is not None}
                partial_update_merger = await PartialUpdateMerger.create(
                    env_id=env.id,
                    base_version=base_version,
                    version=version,
                    rids_in_partial_compile=set(rid_to_resource.keys()),
                    updated_resource_sets=updated_resource_sets,
                    deleted_resource_sets=set(removed_resource_sets),
                    connection=con,
                )

                # add shared resources
                merged_resources = partial_update_merger.merge_updated_and_shared_resources(list(rid_to_resource.values()))

                merged_unknowns = await partial_update_merger.merge_unknowns(
                    unknowns_in_partial_compile=self._create_unknown_parameter_daos_from_api_unknowns(env.id, version, unknowns)
                )

                await self._put_version(
                    env,
                    version,
                    merged_resources,
                    merged_unknowns,
                    version_info,
                    resource_sets,
                    partial_base_version=base_version,
                    removed_resource_sets=removed_resource_sets,
                    pip_config=pip_config,
                    connection=con,
                    module_version_info=module_version_info or {},
                    allow_handler_code_update=allow_handler_code_update,
                )

            returnvalue: ReturnValue[int] = ReturnValue[int](200, response=version)
            await self._trigger_auto_deploy(env, version)

        return returnvalue

    @handle(methods.release_version, version_id="id", env="tid")
    async def release_version(
        self,
        env: data.Environment,
        version_id: int,
        push: bool,
        agent_trigger_method: Optional[const.AgentTriggerMethod] = None,
        *,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> ReturnTupple:
        """
        :param agents: agents that have to be notified by the push, defaults to all
        """
        async with data.ConfigurationModel.get_connection(connection) as connection:
            async with connection.transaction():
                # explicit lock to prevent racing with this code itself.
                await env.acquire_release_version_lock(connection=connection)
                model = await data.ConfigurationModel.get_version_internal(
                    env.id, version_id, connection=connection, lock=RowLockMode.FOR_NO_KEY_UPDATE
                )
                if model is None:
                    return 404, {"message": "The request version does not exist."}

                if model.released:
                    raise Conflict(f"The version {version_id} on environment {env.id} is already released.")

                latest_version = await data.ConfigurationModel.get_version_nr_latest_version(env.id, connection=connection)

                # ensure we are the latest version
                # this does introduce a race condition, with any OTHER release running concurrently on this environment
                # We could lock the get_version_nr_latest_version for update to prevent this
                if model.version < (latest_version or -1):
                    raise Conflict(
                        f"The version {version_id} on environment {env.id} "
                        f"is older then the latest released version {latest_version}."
                    )

                # Ensure there is a record for every resource in the resource_persistent_state table.
                await data.ResourcePersistentState.populate_for_version(env.id, version_id, connection=connection)

                # Setting the model's released field to True is the trigger for the agents
                # to start pulling in the resources.
                await model.update_fields(released=True, connection=connection)

            if connection.is_in_transaction():
                raise RuntimeError(
                    "The release of a new version cannot be in a transaction! "
                    "The agent would not see the data that as committed"
                )
            await self.autostarted_agent_manager._ensure_scheduler(env.id)
            agent = const.AGENT_SCHEDULER_ID

            client = self.agentmanager_service.get_agent_client(env.id, const.AGENT_SCHEDULER_ID)
            if client is not None:
                self.add_background_task(client.trigger_read_version(env.id))
            else:
                LOGGER.warning("Agent %s from model %s in env %s is not available for a deploy", agent, version_id, env.id)

            return 200, {"model": model}

    @handle(methods.deploy, env="tid")
    async def deploy(
        self,
        env: data.Environment,
        agent_trigger_method: const.AgentTriggerMethod = const.AgentTriggerMethod.push_full_deploy,
        agents: Optional[list[str]] = None,
    ) -> Apireturn:
        warnings: list[str] = []

        # get latest version
        version_id = await data.ConfigurationModel.get_version_nr_latest_version(env.id)
        if version_id is None:
            return 404, {"message": "No version available"}

        # filter agents
        allagents = await data.ConfigurationModel.get_agents(env.id, version_id)
        agents_to_call: Sequence[str] = []

        if agents is not None:
            # select specific agents
            required = set(agents)
            present = set(allagents)
            allagents = list(required.intersection(present))
            agents_to_call = allagents
            notfound = required - present
            if notfound:
                warnings.append(
                    "Model version %d does not contain agents named [%s]" % (version_id, ",".join(sorted(list(notfound))))
                )

        if not allagents:
            return attach_warnings(404, {"message": "No agent could be reached"}, warnings)

        await self.autostarted_agent_manager._ensure_scheduler(env.id)

        client = self.agentmanager_service.get_agent_client(env.id, const.AGENT_SCHEDULER_ID)
        if not client:
            return attach_warnings(404, {"message": "Scheduler could not be reached"}, warnings)

        incremental_deploy = agent_trigger_method is const.AgentTriggerMethod.push_incremental_deploy

        if agents is None:
            self.add_background_task(client.trigger(env.id, None, incremental_deploy))
        else:
            for agent in agents_to_call:
                self.add_background_task(client.trigger(env.id, agent, incremental_deploy))

        return attach_warnings(200, {"agents": sorted(allagents)}, warnings)

    @handle(methods_v2.list_desired_state_versions, env="tid")
    async def desired_state_version_list(
        self,
        env: data.Environment,
        limit: Optional[int] = None,
        start: Optional[int] = None,
        end: Optional[int] = None,
        filter: Optional[dict[str, list[str]]] = None,
        sort: str = "version.desc",
    ) -> ReturnValue[list[DesiredStateVersion]]:
        try:
            return await DesiredStateVersionView(
                environment=env,
                limit=limit,
                filter=filter,
                sort=sort,
                start=start,
                end=end,
            ).execute()
        except (InvalidFilter, InvalidSort, data.InvalidQueryParameter, data.InvalidFieldNameException) as e:
            raise BadRequest(e.message) from e

    @handle(methods_v2.promote_desired_state_version, env="tid")
    async def promote_desired_state_version(
        self,
        env: data.Environment,
        version: int,
        trigger_method: Optional[PromoteTriggerMethod] = None,
    ) -> None:
        if trigger_method == PromoteTriggerMethod.push_incremental_deploy:
            push = True
            agent_trigger_method = const.AgentTriggerMethod.push_incremental_deploy
        elif trigger_method == PromoteTriggerMethod.push_full_deploy:
            push = True
            agent_trigger_method = const.AgentTriggerMethod.push_full_deploy
        elif trigger_method == PromoteTriggerMethod.no_push:
            push = False
            agent_trigger_method = None
        else:
            push = True
            agent_trigger_method = None

        status_code, result = await self.release_version(
            env, version_id=version, push=push, agent_trigger_method=agent_trigger_method
        )
        if status_code != 200:
            raise BaseHttpException(status_code, result["message"] if result else "")

    @handle(methods_v2.get_diff_of_versions, env="tid")
    async def get_diff_of_versions(
        self,
        env: data.Environment,
        from_version: int,
        to_version: int,
    ) -> list[ResourceDiff]:
        await self._validate_version_parameters(env.id, from_version, to_version)

        from_version_resources = await data.Resource.get_list(environment=env.id, model=from_version)
        to_version_resources = await data.Resource.get_list(environment=env.id, model=to_version)

        from_state = diff.Version(self.convert_resources(from_version_resources))
        to_state = diff.Version(self.convert_resources(to_version_resources))

        version_diff = to_state.generate_diff(from_state)

        return version_diff

    @handle(methods_v2.get_scheduler_status, env="tid")
    async def get_scheduler_status(
        self,
        env: data.Environment,
    ) -> SchedulerStatusReport:
        if env.halted:
            raise NotFound(message=f"No scheduler is running for environment {env.id}, because the environment is halted.")
        try:
            await self.autostarted_agent_manager._ensure_scheduler(env.id)
        except inmanta.exceptions.EnvironmentNotFound:
            raise NotFound(message=f"Environment {env.id} doesn't exist.")
        except Exception:
            raise ServerError(f"Scheduler in environment {env.id} failed to start.")
        else:
            client = self.agentmanager_service.get_agent_client(env.id, const.AGENT_SCHEDULER_ID)

            if client is None:
                raise NotFound(message=f"No scheduler is running for environment {env.id}.")

            status = await client.trigger_get_status(env.id)

            status_code = status.code
            result = status.result

            if status_code != 200:
                raise BaseHttpException(status_code, result["message"] if result else "")

            assert result is not None

            resp = SchedulerStatusReport.model_validate(result["data"])
            return resp

    def convert_resources(self, resources: list[data.Resource]) -> dict[ResourceIdStr, diff.Resource]:
        return {res.resource_id: diff.Resource(resource_id=res.resource_id, attributes=res.attributes) for res in resources}

    async def _validate_version_parameters(self, env: uuid.UUID, first_version: int, other_version: int) -> None:
        if first_version >= other_version:
            raise BadRequest(
                f"Invalid version parameters: ({first_version}, {other_version}). "
                "The second version number should be strictly greater than the first"
            )
        await self._check_version_exists(env, first_version)
        await self._check_version_exists(env, other_version)

    async def _check_version_exists(self, env: uuid.UUID, version: int) -> None:
        version_object = await data.ConfigurationModel.get_version(env, version)
        if not version_object:
            raise NotFound(f"Version {version} not found")
