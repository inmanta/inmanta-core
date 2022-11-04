"""
    Copyright 2019 Inmanta

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
import dataclasses
import datetime
import logging
import uuid
from collections import abc, defaultdict
from typing import Dict, List, Literal, Mapping, Optional, Sequence, Set, cast

import asyncpg
import asyncpg.connection
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


class ResourceWithResourceSet:
    def __init__(
        self,
        resource: ResourceMinimal,
        resource_set: Optional[str],
        resource_state: const.ResourceState,
    ) -> None:
        self.resource = resource
        self.resource_set = resource_set
        self.resource_state = resource_state

    def get_resource_id_str(self) -> ResourceIdStr:
        return self.resource.get_resource_id_str()

    def get_resource_state_for_new_resource(self) -> Literal[ResourceState.undefined, ResourceState.available]:
        """
        Return the resource state as expected by the `resource_state` argument of the `OrchestrationService._put_version()`
        method. This method should set the resource state of a resource to undefined when it directly depends on an unknown or
        available when it doesn't.
        """
        if self.resource_state is ResourceState.undefined:
            return ResourceState.undefined
        else:
            return ResourceState.available

    def is_shared_resource(self) -> bool:
        return self.resource_set is None

    def is_update(self, other: "ResourceWithResourceSet") -> bool:
        """
        return true if the ResourceWithResourceSet is an update of other: other exists but is different from self
        """
        if other is None:
            return False
        new_resource_dict = self.resource.dict()
        old_resource_dict = other.resource.dict()
        attr_names_new_resource = set(new_resource_dict.keys()).difference("id")
        attr_names_old_resource = set(old_resource_dict.keys()).difference("id")
        return attr_names_new_resource != attr_names_old_resource or any(
            new_resource_dict[k] != old_resource_dict[k] for k in attr_names_new_resource
        )


class PairedResource:
    """
    Pairs an old and a new ResourceWithResourceSet for the same id. Offers methods to inspect the difference.
    """

    def __init__(
        self,
        new_resource: ResourceWithResourceSet,
        old_resource: Optional[ResourceWithResourceSet],
    ) -> None:
        self.new_resource = new_resource
        self.old_resource = old_resource

    def is_update(self) -> bool:
        """
        return true if new_resource is an update of old_resource: old_resource exists but is different form new_resource.
        """
        return self.new_resource.is_update(self.old_resource)

    def is_new_resource(self) -> bool:
        """
        return true if old_resource doesn't exist
        """
        return self.old_resource is None

    def resource_changed_resource_set(self) -> bool:
        """
        return true if the resource_set in new_resource and old_resource are not the same
        """
        assert self.old_resource is not None
        return self.new_resource.resource_set != self.old_resource.resource_set


@dataclasses.dataclass(frozen=True)
class MergedModel:
    """
    A class containing the result of merging an old version of a configuration model with a partial model.
    """

    resources: list[dict[str, object]]
    resource_states: dict[ResourceIdStr, Literal[ResourceState.available, ResourceState.undefined]]
    resource_sets: dict[ResourceIdStr, Optional[str]]
    unknowns: List[data.UnknownParameter]


class PartialUpdateMerger:
    """
    This class is used to merge the result of a partial compile with previous resources and resource_sets. Takes a partial spec
    that should be applied on a given base version to form the given new version.

    Any resource version ids this class works with (e.g. within resource objects) already represent the new version. It is the
    caller's responsibility to ensure this invariant is met for any resource version ids in input objects.
    """

    def __init__(
        self,
        env: data.Environment,
        base_version: int,
        new_version: int,
        partial_updates: Sequence[ResourceMinimal],
        resource_states: Mapping[ResourceIdStr, ResourceState],
        resource_sets: Mapping[ResourceIdStr, Optional[str]],
        removed_resource_sets: Sequence[str],
        unknowns: Sequence[data.UnknownParameter],
    ) -> None:
        """
        :param env: The environment in which the partial compile happens.
        :param base_version: The version number of the old configuration model from which the resources are merged
                             together with the resources from the partial compile.
        :param new_version: The version number of the newly generated configuration model.
        :param partial_updates: The resources part of the partial compile
        :param resource_states: The resource states of the resources in the partial compile.
        :param resource_sets: The resource sets of the resources in the partial compile.
        :param removed_resource_sets: The resources in these resource sets should be present in the new configuration model.
        :param unknowns: The unknowns that belong to the partial model.
        """
        self.partial_updates = partial_updates
        self.resource_states = resource_states
        self.resource_sets = resource_sets
        self.removed_resource_sets = removed_resource_sets
        self.base_version: int = base_version
        self.new_version: int = new_version
        self.env = env
        self.unknowns = unknowns

    def pair_resources_partial_update_to_old_version(
        self, old_resources: Dict[ResourceIdStr, ResourceWithResourceSet]
    ) -> List[PairedResource]:
        """
        returns a list of paired resources

        :param old_resources: A dict with as Key an ResourceIdStr and as value a resource and its resource_set.
        """
        paired_resources: List[PairedResource] = []
        for partial_update in self.partial_updates:
            key = Id.parse_id(partial_update.id).resource_str()
            resource_set = self.resource_sets.get(key)
            resource_state = self.resource_states.get(key, const.ResourceState.available)
            pair: PairedResource = PairedResource(
                new_resource=ResourceWithResourceSet(partial_update, resource_set, resource_state),
                old_resource=old_resources.get(key),
            )
            paired_resources.append(pair)
        return paired_resources

    async def _get_base_resources(
        self, *, connection: asyncpg.connection.Connection
    ) -> dict[ResourceIdStr, ResourceWithResourceSet]:
        """
        Makes a call to the DB to get the resources for this instance's base version in the environment and return a dict
        where the keys are the Ids of the resources and the values are ResourceWithResourceSet.
        Sets the resource objects' version to the new version for the partial export.
        """
        old_data = await data.Resource.get_resources_for_version(
            environment=self.env.id, version=self.base_version, connection=connection
        )
        old_resources: Dict[ResourceIdStr, ResourceWithResourceSet] = {}
        for res in old_data:
            resource: ResourceMinimal = ResourceMinimal.create_with_version(
                new_version=self.new_version, id=res.resource_id, attributes=res.attributes
            )
            old_resources[resource.get_resource_id_str()] = ResourceWithResourceSet(
                resource=resource, resource_set=res.resource_set, resource_state=res.status
            )
        return old_resources

    def _merge_resources(
        self,
        old_resources: Dict[ResourceIdStr, ResourceWithResourceSet],
        paired_resources_partial: List[PairedResource],
        updated_resource_sets: Set[str],
    ) -> dict[ResourceIdStr, ResourceWithResourceSet]:
        """
        Merges the resources of the partial compile with the old resources. To do so it keeps the old resources that are not in
        the removed_resource_sets, that are in the shared resource_set and that are not being updated. It then adds the
        resources coming form the partial compile if they don't break any rule:
        - cannot move a resource to another resource set
        - cannot update resources without a resource set.

        :param old_resources: The resources to use as base for the merge. The version for each resource is expected to already
            be set to the new version for this partial export.
        """
        to_keep: Sequence[ResourceWithResourceSet] = [
            r
            for r in old_resources.values()
            if r.resource_set not in self.removed_resource_sets
            and (r.is_shared_resource() or r.resource_set not in updated_resource_sets)
        ]

        merged_resources: Dict[ResourceIdStr, ResourceWithResourceSet] = {r.get_resource_id_str(): r for r in to_keep}

        for paired_resource in paired_resources_partial:
            new_resource = paired_resource.new_resource
            old_resource = paired_resource.old_resource
            assert (
                old_resource is None
                or Id.parse_id(old_resource.resource.id).resource_str() == Id.parse_id(new_resource.resource.id).resource_str()
            )
            if paired_resource.is_new_resource():
                merged_resources[new_resource.get_resource_id_str()] = new_resource
            else:
                if paired_resource.resource_changed_resource_set():
                    raise BadRequest(
                        f"A partial compile cannot migrate resource {new_resource.resource.id} to another resource set"
                    )
                if new_resource.is_shared_resource() and paired_resource.is_update():
                    raise BadRequest(
                        f"Resource ({new_resource.resource.id}) without a resource set cannot"
                        " be updated via a partial compile"
                    )
                else:
                    merged_resources[new_resource.get_resource_id_str()] = new_resource
        return merged_resources

    def _merge_resource_sets(
        self, old_resource_sets: Dict[ResourceIdStr, Optional[str]], updated_resource_sets: Set[str]
    ) -> Dict[ResourceIdStr, Optional[str]]:
        changed_resource_sets: Set[str] = updated_resource_sets.union(self.removed_resource_sets)
        unchanged_resource_sets: Dict[ResourceIdStr, Optional[str]] = {
            k: v for k, v in old_resource_sets.items() if v not in changed_resource_sets
        }
        return {**unchanged_resource_sets, **self.resource_sets}

    async def _merge_unknowns(
        self, merged_resources: dict[ResourceIdStr, ResourceWithResourceSet]
    ) -> List[data.UnknownParameter]:
        """
        Merge all relevant, unresolved unknowns from the old version of the model together with the unknowns
        of the partial compile.
        """
        rids_in_partial_update = {resource_minimal.get_resource_id_str() for resource_minimal in self.partial_updates}
        rids_not_in_partial_compile = {rid for rid in merged_resources if rid not in rids_in_partial_update}
        old_unresolved_unknowns_to_keep = [
            uk.copy(self.new_version)
            for uk in await data.UnknownParameter.get_list(environment=self.env.id, version=self.base_version, resolved=False)
            # Always keep unknowns not tied to a specific resource
            if not uk.resource_id or uk.resource_id in rids_not_in_partial_compile
        ]
        return [*old_unresolved_unknowns_to_keep, *self.unknowns]

    async def apply_partial(self, *, connection: asyncpg.connection.Connection) -> MergedModel:
        """
        Applies the partial model's resources on this instance's base version. The caller should acquire appropriate locks on
        the database connection as defined in the put_partial method definition.

        :param connection: The database connection to use to determine the latest version. Appropriate locks are assumed to be
            acquired.
        :return: A tuple of the resources and the resource sets. All resource version ids are set to this instance's new
            version.
        """
        old_resources: dict[ResourceIdStr, ResourceWithResourceSet] = await self._get_base_resources(connection=connection)
        old_resource_sets: Dict[ResourceIdStr, Optional[str]] = {
            res_id: res.resource_set for res_id, res in old_resources.items()
        }
        paired_resources_partial = self.pair_resources_partial_update_to_old_version(old_resources)
        updated_resource_sets: Set[str] = set(
            res.new_resource.resource_set for res in paired_resources_partial if not res.new_resource.is_shared_resource()
        )

        merged_resources: dict[ResourceIdStr, ResourceWithResourceSet] = self._merge_resources(
            old_resources, paired_resources_partial, updated_resource_sets
        )
        return MergedModel(
            resources=[r.resource.dict() for r in merged_resources.values()],
            resource_states={rid: r.get_resource_state_for_new_resource() for rid, r in merged_resources.items()},
            resource_sets=self._merge_resource_sets(old_resource_sets, updated_resource_sets),
            unknowns=await self._merge_unknowns(merged_resources),
        )


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

    async def _put_version(
        self,
        env: data.Environment,
        version: int,
        resources: List[JsonType],
        resource_state: Dict[ResourceIdStr, Literal[ResourceState.available, ResourceState.undefined]],
        unknowns: List[data.UnknownParameter],
        version_info: Optional[JsonType] = None,
        resource_sets: Optional[Dict[ResourceIdStr, Optional[str]]] = None,
        partial_base_version: Optional[int] = None,
        *,
        connection: asyncpg.connection.Connection,
    ) -> None:
        """
        :param resources: a list of serialized resources
        """

        if version > env.last_version:
            raise BadRequest(
                f"The version number used is {version} "
                f"which is higher than the last outstanding reservation {env.last_version}"
            )
        if version <= 0:
            raise BadRequest(f"The version number used ({version}) is not positive")

        for r in resources:
            resource = Id.parse_id(r["id"])
            if resource.get_version() != version:
                raise BadRequest(
                    f"The resource version of resource {r['id']} does not match the version argument (version: {version})"
                )

        if not resource_sets:
            resource_sets = {}

        for res_set in resource_sets.keys():
            try:
                Id.parse_id(res_set)
            except Exception as e:
                raise BadRequest("Invalid resource id in resource set: %s" % str(e))

        started = datetime.datetime.now().astimezone()

        agents = set()
        # lookup for all RV's, lookup by resource id
        rv_dict: Dict[ResourceIdStr, data.Resource] = {}
        # reverse dependency tree, Resource.provides [:] -- Resource.requires as resource_id
        provides_tree: Dict[str, List[str]] = defaultdict(lambda: [])
        # list of all resources which have a cross agent dependency, as a tuple, (dependant,requires)
        cross_agent_dep = []
        # list of all resources which are undeployable
        undeployable: List[data.Resource] = []

        resource_objects = []
        resource_version_ids = []
        for res_dict in resources:
            res_obj = data.Resource.new(env.id, res_dict["id"])
            if res_obj.resource_id in resource_state:
                res_obj.status = const.ResourceState[resource_state[res_obj.resource_id]]
                if res_obj.status in const.UNDEPLOYABLE_STATES:
                    undeployable.append(res_obj)
            if res_obj.resource_id in resource_sets:
                res_obj.resource_set = resource_sets[res_obj.resource_id]

            # collect all agents
            agents.add(res_obj.agent)

            attributes = {}
            for field, value in res_dict.items():
                if field != "id":
                    attributes[field] = value

            res_obj.attributes = attributes
            resource_objects.append(res_obj)
            resource_version_ids.append(res_obj.resource_version_id)

            rv_dict[res_obj.resource_id] = res_obj

            # find cross agent dependencies
            agent = res_obj.agent
            resc_id = res_obj.resource_id
            if "requires" not in attributes:
                LOGGER.warning("Received resource without requires attribute (%s)" % res_obj.resource_id)
            else:
                # Collect all requires as resource_ids instead of resource version ids
                cleaned_requires = []
                for req in attributes["requires"]:
                    rid = Id.parse_id(req)
                    provides_tree[rid.resource_str()].append(resc_id)
                    if rid.get_agent_name() != agent:
                        # it is a CAD
                        cross_agent_dep.append((res_obj, rid))
                    cleaned_requires.append(rid.resource_str())
                attributes["requires"] = cleaned_requires
        resource_ids = {res.resource_id for res in resource_objects}
        superfluous_ids = set(resource_sets.keys()) - resource_ids
        if superfluous_ids:
            raise BadRequest(
                "The following resource ids provided in the resource_sets parameter are not present "
                f"in the resources list: {', '.join(superfluous_ids)}"
            )
        requires_ids = set(provides_tree.keys())
        if not requires_ids.issubset(resource_ids):
            raise BadRequest(
                "The model should have a dependency graph that is closed and no dangling dependencies:"
                f" {requires_ids-resource_ids}"
            )
        # hook up all CADs
        for f, t in cross_agent_dep:
            res_obj = rv_dict[t.resource_str()]
            res_obj.provides.append(f.resource_id)

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

        resources_to_purge: List[data.Resource] = []
        if not failed and (await env.get(PURGE_ON_DELETE)):
            # search for deleted resources (purge_on_delete)
            resources_to_purge = await data.Resource.get_deleted_resources(
                env.id, version, list(rv_dict.keys()), connection=connection
            )

            previous_requires = {}
            for res in resources_to_purge:
                LOGGER.warning("Purging %s, purged resource based on %s" % (res.resource_id, res.resource_version_id))

                attributes = res.attributes.copy()
                attributes["purged"] = True
                attributes["requires"] = []
                res_obj = data.Resource.new(
                    env.id,
                    resource_version_id=ResourceVersionIdStr("%s,v=%s" % (res.resource_id, version)),
                    attributes=attributes,
                )
                resource_objects.append(res_obj)

                previous_requires[res_obj.resource_id] = res.attributes["requires"]
                resource_version_ids.append(res_obj.resource_version_id)
                agents.add(res_obj.agent)
                rv_dict[res_obj.resource_id] = res_obj

            # invert dependencies on purges
            for res_id, requires in previous_requires.items():
                res_obj = rv_dict[res_id]
                for require in requires:
                    req_id = Id.parse_id(require)

                    if req_id.resource_str() in rv_dict:
                        req_res = rv_dict[req_id.resource_str()]

                        req_res.attributes["requires"].append(res_obj.resource_version_id)
                        res_obj.provides.append(req_res.resource_id)

        undeployable_ids: List[str] = [res.resource_id for res in undeployable]
        # get skipped for undeployable
        work = list(undeployable_ids)
        skippeable: Set[str] = set()
        while len(work) > 0:
            current = work.pop()
            if current in skippeable:
                continue
            skippeable.add(current)
            work.extend(provides_tree[current])

        skip_list = sorted(list(skippeable - set(undeployable_ids)))

        try:
            cm = data.ConfigurationModel(
                environment=env.id,
                version=version,
                date=datetime.datetime.now().astimezone(),
                total=len(resources),
                version_info=version_info,
                undeployable=undeployable_ids,
                skipped_for_undeployable=skip_list,
                partial_base=partial_base_version,
            )
            await cm.insert(connection=connection)
        except asyncpg.exceptions.UniqueViolationError:
            raise ServerError("The given version is already defined. Versions should be unique.")

        await data.Resource.insert_many(resource_objects, connection=connection)
        await cm.update_fields(total=cm.total + len(resources_to_purge), connection=connection)

        for uk in unknowns:
            await uk.insert(connection=connection)

        for agent in agents:
            await self.agentmanager_service.ensure_agent_registered(env, agent, connection=connection)

        # Don't log ResourceActions without resource_version_ids, because
        # no API call exists to retrieve them.
        if resource_version_ids:
            now = datetime.datetime.now().astimezone()
            log_line = data.LogLine.log(logging.INFO, "Successfully stored version %(version)d", version=version)
            self.resource_service.log_resource_action(env.id, resource_version_ids, logging.INFO, now, log_line.msg)
            ra = data.ResourceAction(
                environment=env.id,
                version=version,
                resource_version_ids=resource_version_ids,
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

    def _create_unknown_from_dct(
        self, env_id: uuid.UUID, version: int, unknowns: Optional[List[Dict[str, PrimitiveTypes]]] = None
    ) -> List[data.UnknownParameter]:
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
        resource_sets: Optional[Dict[ResourceIdStr, Optional[str]]] = None,
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

        unknown_objs = self._create_unknown_from_dct(env.id, version, unknowns)
        async with data.Resource.get_connection() as con:
            async with con.transaction():
                # Acquire a lock that conflicts with the lock acquired by put_partial but not with itself
                await self._put_version_lock(env, shared=True, connection=con)
                await self._put_version(
                    env, version, resources, resource_state, unknown_objs, version_info, resource_sets, connection=con
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
            resources = pydantic.parse_obj_as(List[ResourceMinimal], resources)
        except pydantic.ValidationError:
            raise BadRequest(
                "Type validation failed for resources argument. "
                f"Expected an argument of type List[Dict[str, Any]] but received {resources}"
            )

        # validate resources before any side effects take place
        for r in resources:
            rid = Id.parse_id(r.id)
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

                unknown_objs = self._create_unknown_from_dct(env.id, version, unknowns)

                # set version on input resources
                resources = [r.copy_with_new_version(new_version=version) for r in resources]

                current_versions: abc.Sequence[data.ConfigurationModel] = await data.ConfigurationModel.get_versions(
                    env.id, limit=1
                )
                if not current_versions:
                    raise BadRequest("A partial export requires a base model but no versions have been exported yet.")
                base_version: int = current_versions[0].version

                merger = PartialUpdateMerger(
                    env=env,
                    base_version=base_version,
                    new_version=version,
                    partial_updates=resources,
                    resource_states=resource_state,
                    resource_sets=resource_sets,
                    removed_resource_sets=removed_resource_sets,
                    unknowns=unknown_objs,
                )
                merged_model: MergedModel = await merger.apply_partial(connection=con)
                await data.Code.copy_versions(env.id, base_version, version, connection=con)

                await self._put_version(
                    env,
                    version,
                    merged_model.resources,
                    merged_model.resource_states,
                    merged_model.unknowns,
                    version_info,
                    merged_model.resource_sets,
                    partial_base_version=base_version,
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

        await model.update_fields(released=True, result=const.VersionState.deploying, connection=connection)

        if model.total == 0:
            await model.mark_done(connection=connection)
            return 200, {"model": model}

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
