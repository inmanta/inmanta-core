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
from typing import Dict, List, Literal, Optional, Set, cast

import asyncpg
import asyncpg.connection
import asyncpg.exceptions
import pydantic

from inmanta import const, data
from inmanta.const import ResourceState
from inmanta.data import APILIMIT, AVAILABLE_VERSIONS_TO_KEEP, ENVIRONMENT_AGENT_TRIGGER_METHOD, PURGE_ON_DELETE, InvalidSort
from inmanta.data.dataview import DesiredStateVersionView
from inmanta.data.model import (
    DesiredStateVersion,
    PromoteTriggerMethod,
    ResourceDiff,
    ResourceIdStr,
    ResourceMinimal,
    ResourceVersionIdStr,
)
from inmanta.protocol import handle, methods, methods_v2
from inmanta.protocol.common import ReturnValue, attach_warnings
from inmanta.protocol.exceptions import BadRequest, BaseHttpException, NotFound, ServerError
from inmanta.resources import Id
from inmanta.server import (
    SLICE_AGENT_MANAGER,
    SLICE_AUTOSTARTED_AGENT_MANAGER,
    SLICE_DATABASE,
    SLICE_ORCHESTRATION,
    SLICE_RESOURCE,
    SLICE_TRANSPORT,
)
from inmanta.server import config as opt
from inmanta.server import diff, protocol
from inmanta.server.agentmanager import AgentManager, AutostartedAgentManager
from inmanta.server.services.resourceservice import ResourceService
from inmanta.server.validate_filter import InvalidFilter
from inmanta.types import Apireturn, JsonType, PrimitiveTypes

LOGGER = logging.getLogger(__name__)

PERFORM_CLEANUP: bool = True
# Kill switch for cleanup, for use when working with historical data


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
        :param rids_deleted_resource_sets: The ids of the resources that in base_version that are deleted by this partial
                                           compile.
        """
        self.env_id = env_id
        self.base_version = base_version
        self.version = version
        self.rids_in_partial_compile = rids_in_partial_compile
        self.updated_resource_sets = updated_resource_sets
        self.deleted_resource_sets = deleted_resource_sets
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
        updated_and_shared_resources_old: abc.Mapping[
            ResourceIdStr, data.Resource
        ] = await data.Resource.get_resources_in_resource_sets(
            environment=env_id,
            version=base_version,
            resource_sets=updated_resource_sets,
            include_shared_resources=True,
            connection=connection,
        )
        rids_deleted_resource_sets: abc.Set[ResourceIdStr] = set(
            rid
            for rid in (
                await data.Resource.get_resources_in_resource_sets(
                    environment=env_id,
                    version=base_version,
                    resource_sets=deleted_resource_sets,
                    connection=connection,
                )
            ).keys()
        )
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
    ) -> Dict[ResourceIdStr, data.Resource]:
        """
        :param updated_and_shared_resources: The resources that are part of the partial compile.
        :returns: The subset of resources in the new version of the configuration model that belong to the shared resource set
                  or a resource set that is updated by this partial compile.
        """
        shared_resources = {r.resource_id: r for r in updated_and_shared_resources if r.resource_set is None}
        updated_resources = {r.resource_id: r for r in updated_and_shared_resources if r.resource_set is not None}
        shared_resources_merged = {r.resource_id: r for r in self._merge_shared_resources(shared_resources)}
        result = {**updated_resources, **shared_resources_merged}
        self._validate_constraints(list(result.values()))
        return result

    def _validate_constraints(self, new_updated_and_shared_resources: abc.Sequence[data.Resource]) -> None:
        """
        Validate whether the new updated and shared resources that results from the merging the old version of the model
        with resources of the partial compile, are compliant with the constraints of a partial compile.

        :param new_updated_and_shared_resources: The resources that have to be validated.
        """
        for res in new_updated_and_shared_resources:
            if res.resource_id not in self.updated_and_shared_resources_old:
                continue
            matching_resource_old_model = self.updated_and_shared_resources_old[res.resource_id]

            if res.resource_set != matching_resource_old_model.resource_set:
                raise BadRequest(f"A partial compile cannot migrate resource {res.resource_id} to another resource set.")

            if res.resource_set is None and res.attribute_hash != matching_resource_old_model.attribute_hash:
                raise BadRequest(f"Resource ({res.resource_id}) without a resource set cannot be updated via a partial compile")

    def _merge_shared_resources(self, shared_resources_new: Dict[ResourceIdStr, data.Resource]) -> abc.Sequence[data.Resource]:
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
            result.append(res)
        return result

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
            dep
            for dep in old_deps
            # * Remove the dependencies to resources in the updated resources set. Those dependencies will be present in
            #   new_deps.
            # * Remove dependencies to resources in a deleted resource set. Those resource won't exist in the new version
            #   of the model.
            if dep not in self.non_shared_resources_in_partial_update_old and dep not in self.rids_deleted_resource_sets
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

    agentmanager_service: "AgentManager"
    autostarted_agent_manager: AutostartedAgentManager
    resource_service: ResourceService

    def __init__(self) -> None:
        super(OrchestrationService, self).__init__(SLICE_ORCHESTRATION)

    def get_dependencies(self) -> List[str]:
        return [SLICE_RESOURCE, SLICE_AGENT_MANAGER, SLICE_DATABASE]

    def get_depended_by(self) -> List[str]:
        return [SLICE_TRANSPORT]

    async def prestart(self, server: protocol.Server) -> None:
        await super().prestart(server)
        self.agentmanager_service = cast("AgentManager", server.get_slice(SLICE_AGENT_MANAGER))
        self.autostarted_agent_manager = cast(AutostartedAgentManager, server.get_slice(SLICE_AUTOSTARTED_AGENT_MANAGER))
        self.resource_service = cast(ResourceService, server.get_slice(SLICE_RESOURCE))

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
        envs = await data.Environment.get_list()
        for env_item in envs:
            # get available versions
            n_versions = await env_item.get(AVAILABLE_VERSIONS_TO_KEEP)
            assert isinstance(n_versions, int)
            versions = await data.ConfigurationModel.get_list(environment=env_item.id)
            if len(versions) > n_versions:
                LOGGER.info("Removing %s available versions from environment %s", len(versions) - n_versions, env_item.id)
                version_dict = {x.version: x for x in versions}
                delete_list = sorted(version_dict.keys())
                delete_list = delete_list[:-n_versions]

                for v in delete_list:
                    await version_dict[v].delete_cascade()

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

        resources_out: List[JsonType] = []
        d = {"model": version, "resources": resources_out}
        resource_action_lookup: Dict[ResourceVersionIdStr, List[data.ResourceAction]] = {}

        for res_dict in resources:
            resources_out.append(res_dict)
            if bool(include_logs):
                actions: List[data.ResourceAction] = []
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
        version = await data.ConfigurationModel.get_version(env.id, version_id)
        if version is None:
            return 404, {"message": "The given configuration model does not exist yet."}

        await version.delete_cascade()
        return 200

    @handle(methods_v2.reserve_version, env="tid")
    async def reserve_version(self, env: data.Environment) -> int:
        return await env.get_next_version()

    def _create_dao_resources_from_api_resources(
        self,
        env_id: uuid.UUID,
        resources: List[JsonType],
        resource_state: Dict[ResourceIdStr, Literal[ResourceState.available, ResourceState.undefined]],
        resource_sets: Dict[ResourceIdStr, Optional[str]],
        set_version: Optional[int] = None,
    ) -> Dict[ResourceIdStr, data.Resource]:
        """
        Convert the resources sent to the put_version or put_partial endpoint to dao Resource objects.
        """
        rid_to_resource = {}
        # The content of the requires attribute for all the resources
        all_requires: set[ResourceIdStr] = set()
        # list of all resources which have a cross agent dependency, as a tuple, (dependant,requires)
        cross_agent_dep: list[tuple[data.Resource, Id]] = []
        for res_dict in resources:
            res_obj = data.Resource.new(env_id, res_dict["id"])
            # Populate status field
            if res_obj.resource_id in resource_state:
                res_obj.status = const.ResourceState[resource_state[res_obj.resource_id]]
            # Populate resource_set field
            if res_obj.resource_id in resource_sets:
                res_obj.resource_set = resource_sets[res_obj.resource_id]

            # Populate attributes field of resources
            attributes = {}
            for field, value in res_dict.items():
                if field != "id":
                    attributes[field] = value
            res_obj.attributes = attributes
            res_obj.make_hash()

            # Update the version fields
            if set_version is not None:
                res_obj.attributes["version"] = set_version
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
        provides_tree: Dict[ResourceIdStr, List[ResourceIdStr]] = defaultdict(lambda: [])
        for r in resources:
            if "requires" in r.attributes:
                for req in r.attributes["requires"]:
                    req_id = Id.parse_id(req)
                    provides_tree[req_id.resource_str()].append(r.resource_id)
        # Find skipped for undeployables
        work = list(undeployable_ids)
        skippeable: Set[ResourceIdStr] = set()
        while len(work) > 0:
            current = work.pop()
            if current in skippeable:
                continue
            skippeable.add(current)
            work.extend(provides_tree[current])
        return list(skippeable - set(undeployable_ids))

    async def _put_version(
        self,
        env: data.Environment,
        version: int,
        rid_to_resource: Dict[ResourceIdStr, data.Resource],
        unknowns: abc.Sequence[data.UnknownParameter],
        version_info: Optional[JsonType] = None,
        resource_sets: Optional[Dict[ResourceIdStr, Optional[str]]] = None,
        partial_base_version: Optional[int] = None,
        removed_resource_sets: Optional[List[str]] = None,
        *,
        connection: asyncpg.connection.Connection,
    ) -> None:
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

        # detect failed compiles
        def safe_get(input: object, key: str, default: object) -> object:
            if not isinstance(input, dict):
                return default
            if key not in input:
                return default
            return input[key]

        metadata: object = safe_get(version_info, const.EXPORT_META_DATA, {})
        compile_state = safe_get(metadata, const.META_DATA_COMPILE_STATE, "")
        failed = compile_state == const.Compilestate.failed

        # Add purge-on-delete resources
        if not failed and (await env.get(PURGE_ON_DELETE)):
            # search for deleted resources (purge_on_delete)
            resources_to_purge: List[data.Resource] = await data.Resource.get_deleted_resources(
                env.id, version, list(rid_to_resource.keys()), connection=connection
            )

            previous_requires = {}
            for res in resources_to_purge:
                LOGGER.warning("Purging %s, purged resource based on %s", res.resource_id, res.resource_version_id)

                attributes = res.attributes.copy()
                attributes["purged"] = True
                attributes["requires"] = []
                res_obj = data.Resource.new(
                    env.id,
                    resource_version_id=ResourceVersionIdStr("%s,v=%s" % (res.resource_id, version)),
                    attributes=attributes,
                )

                previous_requires[res_obj.resource_id] = res.attributes["requires"]
                rid_to_resource[res_obj.resource_id] = res_obj

            # invert dependencies on purges
            for res_id, requires in previous_requires.items():
                res_obj = rid_to_resource[res_id]
                for require in requires:
                    req_id = Id.parse_id(require)

                    if req_id.resource_str() in rid_to_resource:
                        req_res = rid_to_resource[req_id.resource_str()]

                        req_res.attributes["requires"].append(res_obj.resource_version_id)
                        res_obj.provides.append(req_res.resource_id)

        undeployable_ids: abc.Sequence[ResourceIdStr] = [
            res.resource_id for res in rid_to_resource.values() if res.status in const.UNDEPLOYABLE_STATES
        ]
        try:
            cm = await data.ConfigurationModel.create_and_insert(
                env_id=env.id,
                version=version,
                total=len(rid_to_resource),
                version_info=version_info,
                undeployable=undeployable_ids,
                skipped_for_undeployable=sorted(
                    self._get_skipped_for_undeployable(list(rid_to_resource.values()), undeployable_ids)
                ),
                partial_base=partial_base_version,
                rids_in_partial_compile=set(rid_to_resource.keys()) if partial_base_version else None,
                connection=connection,
            )
        except asyncpg.exceptions.UniqueViolationError:
            raise ServerError("The given version is already defined. Versions should be unique.")

        all_resource_version_ids: abc.Set[ResourceVersionIdStr] = set(
            Id.set_version_in_id(rid, version) for rid in rid_to_resource.keys()
        )
        if is_partial_update:
            # Make mypy happy
            assert partial_base_version is not None
            rids_unchanged_resource_sets: abc.Set[
                ResourceIdStr
            ] = await data.Resource.copy_resources_from_unchanged_resource_set(
                environment=env.id,
                source_version=partial_base_version,
                destination_version=version,
                updated_resource_sets=set(sr for sr in resource_sets.values() if sr is not None),
                deleted_resource_sets=set(removed_resource_sets),
                connection=connection,
            )
            resources_that_moved_resource_sets = rids_unchanged_resource_sets & set(rid_to_resource.keys())
            if resources_that_moved_resource_sets:
                raise BadRequest(
                    f"A partial compile cannot migrate resources {list(resources_that_moved_resource_sets)} to another resource"
                    " set"
                )

            all_resource_version_ids |= {Id.set_version_in_id(rid, version) for rid in rids_unchanged_resource_sets}

        await data.Resource.insert_many(list(rid_to_resource.values()), connection=connection)
        await cm.recalculate_total(connection=connection)

        await data.UnknownParameter.insert_many(unknowns, connection=connection)

        for res in rid_to_resource.values():
            await self.agentmanager_service.ensure_agent_registered(env, res.agent, connection=connection)

        # Don't log ResourceActions without resource_version_ids, because
        # no API call exists to retrieve them.
        if all_resource_version_ids:
            now = datetime.datetime.now().astimezone()
            log_line = data.LogLine.log(logging.INFO, "Successfully stored version %(version)d", version=version)
            self.resource_service.log_resource_action(env.id, list(all_resource_version_ids), logging.INFO, now, log_line.msg)
            ra = data.ResourceAction(
                environment=env.id,
                version=version,
                resource_version_ids=all_resource_version_ids,
                action_id=uuid.uuid4(),
                action=const.ResourceAction.store,
                started=started,
                finished=now,
                messages=[log_line],
            )
            await ra.insert(connection=connection)

        LOGGER.debug("Successfully stored version %d", version)

        self.resource_service.clear_env_cache(env)

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
            push_on_auto_deploy = cast(bool, await env.get(data.PUSH_ON_AUTO_DEPLOY))
            agent_trigger_method_on_autodeploy = cast(str, await env.get(data.AGENT_TRIGGER_METHOD_ON_AUTO_DEPLOY))
            agent_trigger_method_on_autodeploy = const.AgentTriggerMethod[agent_trigger_method_on_autodeploy]
            await self.release_version(env, version, push_on_auto_deploy, agent_trigger_method_on_autodeploy)

    def _create_unknown_parameter_daos_from_api_unknowns(
        self, env_id: uuid.UUID, version: int, unknowns: Optional[List[Dict[str, PrimitiveTypes]]] = None
    ) -> List[data.UnknownParameter]:
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

    async def _put_version_lock(self, env: data.Environment, *, shared: bool = False, connection: asyncpg.Connection) -> None:
        """
        Acquires a transaction-level advisory lock for concurrency control between put_version and put_partial.

        :param env: The environment to acquire the lock for.
        :param shared: If true, doesn't conflict with other shared locks, only with non-shared once.
        :param connection: The connection hosting the transaction for which to acquire a lock.
        """
        lock: str = "pg_advisory_xact_lock_shared" if shared else "pg_advisory_xact_lock"
        await connection.execute(
            # Advisory lock keys are only 32 bit (or a single 64 bit key), while a full uuid is 128 bit.
            # Since locking slightly too strictly at extremely low odds is acceptable, we only use a 32 bit subvalue
            # of the uuid. For uuid4, time_low is (despite the name) randomly generated. Since it is an unsigned
            # integer while Postgres expects a signed one, we shift it by 2**31.
            f"SELECT {lock}({const.PG_ADVISORY_KEY_PUT_VERSION}, {env.id.time_low - 2**31})"
        )

    @handle(methods.put_version, env="tid")
    async def put_version(
        self,
        env: data.Environment,
        version: int,
        resources: List[JsonType],
        resource_state: Dict[ResourceIdStr, Literal[ResourceState.available, ResourceState.undefined]],
        unknowns: List[Dict[str, PrimitiveTypes]],
        version_info: JsonType,
        compiler_version: Optional[str] = None,
        resource_sets: Dict[ResourceIdStr, Optional[str]] = {},
    ) -> Apireturn:
        """
        :param unknowns: dict with the following structure
                            {
                             "resource": ResourceIdStr,
                             "parameter": str,
                             "source": str
                            }
        """
        if not compiler_version:
            raise BadRequest("Older compiler versions are no longer supported, please update your compiler")

        unknowns_objs = self._create_unknown_parameter_daos_from_api_unknowns(env.id, version, unknowns)
        rid_to_resource = self._create_dao_resources_from_api_resources(
            env_id=env.id,
            resources=resources,
            resource_state=resource_state,
            resource_sets=resource_sets,
        )
        async with data.Resource.get_connection() as con:
            async with con.transaction():
                # Acquire a lock that conflicts with the lock acquired by put_partial but not with itself
                await self._put_version_lock(env, shared=True, connection=con)
                await self._put_version(
                    env, version, rid_to_resource, unknowns_objs, version_info, resource_sets, connection=con
                )
        await self._trigger_auto_deploy(env, version)
        return 200

    @handle(methods_v2.put_partial, env="tid")
    async def put_partial(
        self,
        env: data.Environment,
        resources: object,
        resource_state: Optional[Dict[ResourceIdStr, Literal[ResourceState.available, ResourceState.undefined]]] = None,
        unknowns: Optional[List[Dict[str, PrimitiveTypes]]] = None,
        version_info: Optional[JsonType] = None,
        resource_sets: Optional[Dict[ResourceIdStr, Optional[str]]] = None,
        removed_resource_sets: Optional[List[str]] = None,
    ) -> int:
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
            pydantic.parse_obj_as(List[ResourceMinimal], resources)
        except pydantic.ValidationError:
            raise BadRequest(
                "Type validation failed for resources argument. "
                f"Expected an argument of type List[Dict[str, Any]] but received {resources}"
            )
        else:
            # Make mypy happy
            resources = cast(List[JsonType], resources)

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
                await self._put_version_lock(env, shared=False, connection=con)

                # Only request a new version once the resource lock has been acquired to ensure a monotonic version history
                version: int = await env.get_next_version(connection=con)

                current_versions: abc.Sequence[data.ConfigurationModel] = await data.ConfigurationModel.get_versions(
                    env.id, limit=1
                )
                if not current_versions:
                    raise BadRequest("A partial export requires a base model but no versions have been exported yet.")
                base_version: int = current_versions[0].version

                rid_to_resource: Dict[ResourceIdStr, data.Resource] = self._create_dao_resources_from_api_resources(
                    env_id=env.id,
                    resources=resources,
                    resource_state=resource_state,
                    resource_sets=resource_sets,
                    set_version=version,
                )

                updated_resource_sets: abc.Set[str] = set(sr_name for sr_name in resource_sets.values() if sr_name is not None)
                partial_update_merger = await PartialUpdateMerger.create(
                    env_id=env.id,
                    base_version=base_version,
                    version=version,
                    rids_in_partial_compile=set(rid_to_resource.keys()),
                    updated_resource_sets=updated_resource_sets,
                    deleted_resource_sets=set(removed_resource_sets),
                    connection=con,
                )

                merged_resources = partial_update_merger.merge_updated_and_shared_resources(list(rid_to_resource.values()))

                await data.Code.copy_versions(env.id, base_version, version, connection=con)

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
                    connection=con,
                )
        await self._trigger_auto_deploy(env, version)
        return version

    @handle(methods.release_version, version_id="id", env="tid")
    async def release_version(
        self,
        env: data.Environment,
        version_id: int,
        push: bool,
        agent_trigger_method: Optional[const.AgentTriggerMethod] = None,
        *,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> Apireturn:
        model = await data.ConfigurationModel.get_version(env.id, version_id, connection=connection)
        if model is None:
            return 404, {"message": "The request version does not exist."}

        # Already mark undeployable resources as deployed to create a better UX (change the version counters)
        undep = await model.get_undeployable()
        now = datetime.datetime.now().astimezone()

        if undep:
            undep_ids = [ResourceVersionIdStr(rid + ",v=%s" % version_id) for rid in undep]
            # not checking error conditions
            await self.resource_service.resource_action_update(
                env,
                undep_ids,
                action_id=uuid.uuid4(),
                started=now,
                finished=now,
                status=const.ResourceState.undefined,
                action=const.ResourceAction.deploy,
                changes={},
                messages=[],
                change=const.Change.nochange,
                send_events=False,
                connection=connection,
            )

            skippable = await model.get_skipped_for_undeployable()
            if skippable:
                skippable_ids = [ResourceVersionIdStr(rid + ",v=%s" % version_id) for rid in skippable]
                # not checking error conditions
                await self.resource_service.resource_action_update(
                    env,
                    skippable_ids,
                    action_id=uuid.uuid4(),
                    started=now,
                    finished=now,
                    status=const.ResourceState.skipped_for_undefined,
                    action=const.ResourceAction.deploy,
                    changes={},
                    messages=[],
                    change=const.Change.nochange,
                    send_events=False,
                    connection=connection,
                )

        increments: tuple[abc.Set[ResourceIdStr], abc.Set[ResourceIdStr]] = await self.resource_service.get_increment(
            env, version_id
        )

        increment_ids, neg_increment = increments
        await self.resource_service.mark_deployed(env, neg_increment, now, version_id)

        # Setting the model's released field to True is the trigger for the agents to start pulling in the resources.
        # This has to be done after the resources outside of the increment have been marked as deployed.
        await model.update_fields(released=True, result=const.VersionState.deploying, connection=connection)

        if model.total == 0:
            await model.mark_done(connection=connection)
            return 200, {"model": model}

        if push:
            # fetch all resource in this cm and create a list of distinct agents
            agents = await data.ConfigurationModel.get_agents(env.id, version_id, connection=connection)
            await self.autostarted_agent_manager._ensure_agents(env, agents, connection=connection)

            for agent in agents:
                client = self.agentmanager_service.get_agent_client(env.id, agent)
                if client is not None:
                    if not agent_trigger_method:
                        env_agent_trigger_method = await env.get(ENVIRONMENT_AGENT_TRIGGER_METHOD, connection=connection)
                        incremental_deploy = env_agent_trigger_method == const.AgentTriggerMethod.push_incremental_deploy
                    else:
                        incremental_deploy = agent_trigger_method is const.AgentTriggerMethod.push_incremental_deploy
                    self.add_background_task(client.trigger(env.id, agent, incremental_deploy))
                else:
                    LOGGER.warning("Agent %s from model %s in env %s is not available for a deploy", agent, version_id, env.id)

        return 200, {"model": model}

    @handle(methods.deploy, env="tid")
    async def deploy(
        self,
        env: data.Environment,
        agent_trigger_method: const.AgentTriggerMethod = const.AgentTriggerMethod.push_full_deploy,
        agents: Optional[List[str]] = None,
    ) -> Apireturn:
        warnings = []

        # get latest version
        version_id = await data.ConfigurationModel.get_version_nr_latest_version(env.id)
        if version_id is None:
            return 404, {"message": "No version available"}

        # filter agents
        allagents = await data.ConfigurationModel.get_agents(env.id, version_id)
        if agents is not None:
            required = set(agents)
            present = set(allagents)
            allagents = list(required.intersection(present))
            notfound = required - present
            if notfound:
                warnings.append(
                    "Model version %d does not contain agents named [%s]" % (version_id, ",".join(sorted(list(notfound))))
                )

        if not allagents:
            return attach_warnings(404, {"message": "No agent could be reached"}, warnings)

        present = set()
        absent = set()

        await self.autostarted_agent_manager._ensure_agents(env, allagents)

        for agent in allagents:
            client = self.agentmanager_service.get_agent_client(env.id, agent)
            if client is not None:
                incremental_deploy = agent_trigger_method is const.AgentTriggerMethod.push_incremental_deploy
                self.add_background_task(client.trigger(env.id, agent, incremental_deploy))
                present.add(agent)
            else:
                absent.add(agent)

        if absent:
            warnings.append("Could not reach agents named [%s]" % ",".join(sorted(list(absent))))

        if not present:
            return attach_warnings(404, {"message": "No agent could be reached"}, warnings)

        return attach_warnings(200, {"agents": sorted(list(present))}, warnings)

    @handle(methods_v2.list_desired_state_versions, env="tid")
    async def desired_state_version_list(
        self,
        env: data.Environment,
        limit: Optional[int] = None,
        start: Optional[int] = None,
        end: Optional[int] = None,
        filter: Optional[Dict[str, List[str]]] = None,
        sort: str = "version.desc",
    ) -> ReturnValue[List[DesiredStateVersion]]:
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
            raise BaseHttpException(status_code, result["message"])

    @handle(methods_v2.get_diff_of_versions, env="tid")
    async def get_diff_of_versions(
        self,
        env: data.Environment,
        from_version: int,
        to_version: int,
    ) -> List[ResourceDiff]:
        await self._validate_version_parameters(env.id, from_version, to_version)

        from_version_resources = await data.Resource.get_list(environment=env.id, model=from_version)
        to_version_resources = await data.Resource.get_list(environment=env.id, model=to_version)

        from_state = diff.Version(self.convert_resources(from_version_resources))
        to_state = diff.Version(self.convert_resources(to_version_resources))

        version_diff = to_state.generate_diff(from_state)

        return version_diff

    def convert_resources(self, resources: List[data.Resource]) -> Dict[ResourceIdStr, diff.Resource]:
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
