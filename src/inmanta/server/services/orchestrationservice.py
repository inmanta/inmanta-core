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

import datetime
import logging
import uuid
from collections import abc, defaultdict
from typing import Dict, List, Mapping, Optional, Sequence, Set, Tuple, cast

import asyncpg
import asyncpg.connection
import pydantic

from inmanta import const, data
from inmanta.const import ResourceState
from inmanta.data import (
    APILIMIT,
    AVAILABLE_VERSIONS_TO_KEEP,
    ENVIRONMENT_AGENT_TRIGGER_METHOD,
    PURGE_ON_DELETE,
    DesiredStateVersionOrder,
    InvalidSort,
    QueryType,
)
from inmanta.data.model import (
    DesiredStateVersion,
    PromoteTriggerMethod,
    ResourceDiff,
    ResourceIdStr,
    ResourceMinimal,
    ResourceVersionIdStr,
)
from inmanta.data.paging import DesiredStateVersionPagingCountsProvider, DesiredStateVersionPagingHandler, QueryIdentifier
from inmanta.protocol import handle, methods, methods_v2
from inmanta.protocol.common import ReturnValue, attach_warnings
from inmanta.protocol.exceptions import BadRequest, BaseHttpException, NotFound, ServerError
from inmanta.protocol.return_value_meta import ReturnValueWithMeta
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
from inmanta.server.validate_filter import DesiredStateVersionFilterValidator, InvalidFilter
from inmanta.types import Apireturn, JsonType, PrimitiveTypes

LOGGER = logging.getLogger(__name__)


class ResourceWithResourceSet:
    def __init__(
        self,
        resource: ResourceMinimal,
        resource_set: Optional[str],
    ) -> None:
        self.resource = resource
        self.resource_set = resource_set

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
        resource_sets: Mapping[ResourceIdStr, Optional[str]],
        removed_resource_sets: Sequence[str],
    ) -> None:
        self.partial_updates = partial_updates
        self.resource_sets = resource_sets
        self.removed_resource_sets = removed_resource_sets
        self.base_version: int = base_version
        self.new_version: int = new_version
        self.env = env

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
            pair: PairedResource = PairedResource(
                new_resource=ResourceWithResourceSet(partial_update, resource_set), old_resource=None
            )
            if key in old_resources:
                pair.old_resource = ResourceWithResourceSet(old_resources[key].resource, old_resources[key].resource_set)
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
        old_data = await data.Resource.get_resources_for_version(environment=self.env.id, version=self.base_version, connection=connection)
        old_resources: Dict[ResourceIdStr, ResourceWithResourceSet] = {}
        for res in old_data:
            new_version_id: Id = Id.parse_id(res.resource_version_id).copy(version=self.new_version)
            resource: ResourceMinimal = ResourceMinimal(id=new_version_id.resource_version_str(), **res.attributes)
            old_resources[new_version_id.resource_str()] = ResourceWithResourceSet(resource, res.resource_set)
        return old_resources

    def _merge_resources(
        self, old_resources: Dict[ResourceIdStr, ResourceWithResourceSet], paired_resources: List[PairedResource]
    ) -> list[dict[str, object]]:
        """
        Merges the resources of the partial compile with the old resources. To do so it keeps the old resources that are not in
        the removed_resource_sets, that are in the shared resource_set and that are not being updated. It then adds the
        resources coming form the partial compile if they don't break any rule:
        - cannot move a resource to another resource set
        - cannot update resources without a resource set.

        :param old_resources: The resources to use as base for the merge. The version for each resource is expected to already
            be set to the new version for this partial export.
        """
        updated_resource_sets: Set[str] = set(
            res.new_resource.resource_set for res in paired_resources if not res.new_resource.is_shared_resource()
        )

        to_keep: Sequence[ResourceMinimal] = [
            r.resource
            for r in old_resources.values()
            if r.resource_set not in self.removed_resource_sets
            and (r.is_shared_resource() or r.resource_set not in updated_resource_sets)
        ]

        merged_resources: Dict[ResourceVersionIdStr, Dict[str, object]] = {r.id: r.dict() for r in to_keep}

        for paired_resource in paired_resources:
            new_resource = paired_resource.new_resource
            old_resource = paired_resource.old_resource
            assert (
                old_resource is None
                or Id.parse_id(old_resource.resource.id).resource_str() == Id.parse_id(new_resource.resource.id).resource_str()
            )
            if paired_resource.is_new_resource():
                merged_resources[new_resource.resource.id] = new_resource.resource.dict()
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
                    merged_resources[new_resource.resource.id] = new_resource.resource.dict()
        return list(merged_resources.values())

    def _merge_resource_sets(
        self, old_resource_sets: Dict[ResourceIdStr, Optional[str]], paired_resources: List[PairedResource]
    ) -> Dict[ResourceIdStr, Optional[str]]:
        updated_resource_sets: Set[str] = set(
            res.new_resource.resource_set for res in paired_resources if not res.new_resource.is_shared_resource()
        )
        changed_resource_sets: Set[str] = updated_resource_sets.union(self.removed_resource_sets)
        unchanged_resource_sets: Dict[ResourceIdStr, Optional[str]] = {
            k: v for k, v in old_resource_sets.items() if v not in changed_resource_sets
        }
        return {**unchanged_resource_sets, **self.resource_sets}

    async def apply_partial(
        self, *, connection: asyncpg.connection.Connection
    ) -> tuple[list[dict[str, object]], dict[ResourceIdStr, Optional[str]]]:
        """
        Applies the partial model's resources on this instance's base version. The caller should acquire appropriate locks on the
        database connection as defined in the put_partial method definition.

        :param connection: The database connection to use to determine the latest version. Appropriate locks are assumed to be
            acquired.
        :return: A tuple of the resources and the resource sets. All resource version ids are set to this instance's new
            version.
        """
        old_resources = await self._get_base_resources(connection=connection)

        old_resource_sets: Dict[ResourceIdStr, Optional[str]] = {
            res_id: res.resource_set for res_id, res in old_resources.items()
        }

        paired_resources = self.pair_resources_partial_update_to_old_version(old_resources)
        new_resources = self._merge_resources(old_resources, paired_resources)
        new_resource_sets = self._merge_resource_sets(old_resource_sets, paired_resources)
        return new_resources, new_resource_sets


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
        resource_state: Dict[ResourceIdStr, const.ResourceState],
        unknowns: List[Dict[str, PrimitiveTypes]],
        version_info: Optional[JsonType] = None,
        resource_sets: Optional[Dict[ResourceIdStr, Optional[str]]] = None,
        *,
        connection: asyncpg.connection.Connection
    ) -> Apireturn:
        """
        :param resources: a list of serialized resources
        :param unknowns: dict with the following structure
        {
         "resource": ResourceIdStr,
         "parameter": str,
         "source": str
         }
        :param version_info:
        :return:
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
                for req in attributes["requires"]:
                    rid = Id.parse_id(req)
                    provides_tree[rid.resource_str()].append(resc_id)
                    if rid.get_agent_name() != agent:
                        # it is a CAD
                        cross_agent_dep.append((res_obj, rid))
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
            res_obj.provides.append(f.resource_version_id)

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
                        res_obj.provides.append(req_res.resource_version_id)

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
            )
            await cm.insert(connection=connection)
        except asyncpg.exceptions.UniqueViolationError:
            raise ServerError("The given version is already defined. Versions should be unique.")

        await data.Resource.insert_many(resource_objects, connection=connection)
        await cm.update_fields(total=cm.total + len(resources_to_purge), connection=connection)

        for uk in unknowns:
            if "resource" not in uk:
                uk["resource"] = ""

            if "metadata" not in uk:
                uk["metadata"] = {}

            up = data.UnknownParameter(
                resource_id=uk["resource"],
                name=uk["parameter"],
                source=uk["source"],
                environment=env.id,
                version=version,
                metadata=uk["metadata"],
            )
            await up.insert(connection=connection)

        for agent in agents:
            await self.agentmanager_service.ensure_agent_registered(env, agent, connection=connection)

        # Don't log ResourceActions without resource_version_ids, because
        # no API call exists to retrieve them.
        if resource_version_ids:
            now = datetime.datetime.now().astimezone()
            log_line = data.LogLine.log(logging.INFO, "Successfully stored version %(version)d", version=version)
            self.resource_service.log_resource_action(
                env.id, resource_version_ids, logging.INFO, now, log_line.msg
            )
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

        auto_deploy = await env.get(data.AUTO_DEPLOY, connection=connection)
        if auto_deploy:
            LOGGER.debug("Auto deploying version %d", version)
            push_on_auto_deploy = cast(bool, await env.get(data.PUSH_ON_AUTO_DEPLOY, connection=connection))
            agent_trigger_method_on_autodeploy = cast(
                str, await env.get(data.AGENT_TRIGGER_METHOD_ON_AUTO_DEPLOY, connection=connection)
            )
            agent_trigger_method_on_autodeploy = const.AgentTriggerMethod[agent_trigger_method_on_autodeploy]
            await self.release_version(
                env, version, push_on_auto_deploy, agent_trigger_method_on_autodeploy, connection=connection
            )

        return 200

    @handle(methods.put_version, env="tid")
    async def put_version(
        self,
        env: data.Environment,
        version: int,
        resources: List[JsonType],
        resource_state: Dict[ResourceIdStr, const.ResourceState],
        unknowns: List[Dict[str, PrimitiveTypes]],
        version_info: JsonType,
        compiler_version: Optional[str] = None,
        resource_sets: Optional[Dict[ResourceIdStr, Optional[str]]] = None,
    ) -> Apireturn:
        if not compiler_version:
            raise BadRequest("Older compiler versions are no longer supported, please update your compiler")

        async with data.Resource.get_connection() as con:
            async with con.transaction():
                # Acquire a lock that conflicts with the lock acquired by put_partial.
                await data.Resource.lock_table(data.TableLockMode.ROW_EXCLUSIVE, connection=con)
                return await self._put_version(
                    env, version, resources, resource_state, unknowns, version_info, resource_sets, connection=con
                )

    @handle(methods_v2.put_partial, env="tid")
    async def put_partial(
        self,
        env: data.Environment,
        resources: object,
        resource_state: Optional[Dict[ResourceIdStr, ResourceState]] = None,
        unknowns: Optional[List[Dict[str, PrimitiveTypes]]] = None,
        version_info: Optional[JsonType] = None,
        resource_sets: Optional[Dict[ResourceIdStr, Optional[str]]] = None,
        removed_resource_sets: Optional[List[str]] = None,
    ) -> int:
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

        intersection: set[str] = set(resource_sets.values()).intersection(set(removed_resource_sets))
        if intersection:
            raise BadRequest(
                "Following resource sets are present in the removed resource sets and in the resources that are exported: "
                f"{intersection}"
            )

        async with data.Resource.get_connection() as con:
            async with con.transaction():
                # Acquire a lock that conflicts with itself and with the lock acquired by put_version.
                await data.Resource.lock_table(data.TableLockMode.SHARE_ROW_EXCLUSIVE, connection=con)

                # Only request a new version once the resource lock has been acquired to prevent races between two
                # put_partial calls: this way the requested version will never be made stale by another call between now and
                # when we store the resources.
                # For this call, treat the lock as a plain Python lock: request the new version outside of the transaction so
                # as not to block new version requests on code paths other than this one. Being more strict does not
                # provide stronger gaurantees because a specific type of race, where put_partial is called in
                # the window between reserve_version and put_version, is unavoidable due to the two-part nature of
                # put_version (see put_partial docstring and #4416).
                version: int = await env.get_next_version()
                for r in resources:
                    resource = Id.parse_id(r.id)
                    if resource.get_version() != 0:
                        raise BadRequest(
                            "Resources for partial export should not contain version information"
                        )
                    resource.set_version(version)

                current_versions: abc.Sequence[data.ConfigurationModel] = await data.ConfigurationModel.get_versions(env.id, limit=1)
                if not current_versions:
                    raise BadRequest(
                        "A partial export requires a base model but no versions have been exported yet."
                    )
                base_version: int = current_versions[0].version

                merger = PartialUpdateMerger(
                    env=env,
                    base_version=base_version,
                    new_version=version,
                    partial_updates=resources,
                    resource_sets=resource_sets,
                    removed_resource_sets=removed_resource_sets,
                )
                merged_resources, merged_resource_sets = await merger.apply_partial(connection=con)
                await data.Code.copy_versions(env.id, base_version, version)

                # TODO: does this really need to live within the transaction?
                await self._put_version(
                    env,
                    version,
                    merged_resources,
                    resource_state,
                    unknowns,
                    version_info,
                    merged_resource_sets,
                    connection=con,
                )
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
        undep_ids = [ResourceVersionIdStr(rid + ",v=%s" % version_id) for rid in undep]

        now = datetime.datetime.now().astimezone()

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
            await self.autostarted_agent_manager._ensure_agents(env, agents)

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
        if limit is None:
            limit = APILIMIT
        elif limit > APILIMIT:
            raise BadRequest(f"limit parameter can not exceed {APILIMIT}, got {limit}.")

        query: Dict[str, Tuple[QueryType, object]] = {}
        if filter:
            try:
                query.update(DesiredStateVersionFilterValidator().process_filters(filter))
            except InvalidFilter as e:
                raise BadRequest(e.message) from e
        try:
            resource_order = DesiredStateVersionOrder.parse_from_string(sort)
        except InvalidSort as e:
            raise BadRequest(e.message) from e
        try:
            dtos = await data.ConfigurationModel.get_desired_state_versions(
                database_order=resource_order,
                limit=limit,
                environment=env.id,
                start=start,
                end=end,
                connection=None,
                **query,
            )
        except (data.InvalidQueryParameter, data.InvalidFieldNameException) as e:
            raise BadRequest(e.message)

        paging_handler = DesiredStateVersionPagingHandler(DesiredStateVersionPagingCountsProvider())
        metadata = await paging_handler.prepare_paging_metadata(
            QueryIdentifier(environment=env.id), dtos, query, limit, resource_order
        )
        links = await paging_handler.prepare_paging_links(
            dtos,
            filter,
            resource_order,
            limit,
            start=start,
            end=end,
            first_id=None,
            last_id=None,
            has_next=metadata.after > 0,
            has_prev=metadata.before > 0,
        )

        return ReturnValueWithMeta(response=dtos, links=links if links else {}, metadata=vars(metadata))

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
