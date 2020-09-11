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
from collections import defaultdict
from typing import Dict, List, Optional, Set, cast

import asyncpg

from inmanta import const, data
from inmanta.data import ENVIRONMENT_AGENT_TRIGGER_METHOD, PURGE_ON_DELETE
from inmanta.data.model import ResourceIdStr, ResourceVersionIdStr
from inmanta.protocol import methods, methods_v2
from inmanta.protocol.common import attach_warnings
from inmanta.protocol.exceptions import BadRequest, ServerError
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
from inmanta.server import protocol
from inmanta.server.agentmanager import AgentManager, AutostartedAgentManager
from inmanta.server.services.resourceservice import ResourceService
from inmanta.types import Apireturn, JsonType, PrimitiveTypes

LOGGER = logging.getLogger(__name__)


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
        self.schedule(self._purge_versions, opt.server_purge_version_interval.get())
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
            n_versions = opt.server_version_to_keep.get()
            versions = await data.ConfigurationModel.get_list(environment=env_item.id)
            if len(versions) > n_versions:
                LOGGER.info("Removing %s available versions from environment %s", len(versions) - n_versions, env_item.id)
                version_dict = {x.version: x for x in versions}
                delete_list = sorted(version_dict.keys())
                delete_list = delete_list[:-n_versions]

                for v in delete_list:
                    await version_dict[v].delete_cascade()

    @protocol.handle(methods.list_versions, env="tid")
    async def list_version(self, env: data.Environment, start: Optional[int] = None, limit: Optional[int] = None) -> Apireturn:
        if (start is None and limit is not None) or (limit is None and start is not None):
            raise ServerError("Start and limit should always be set together.")

        if start is None:
            start = 0
            limit = data.DBLIMIT

        models = await data.ConfigurationModel.get_versions(env.id, start, limit)
        count = len(models)

        d = {"versions": models}

        if start is not None:
            d["start"] = start
            d["limit"] = limit

        d["count"] = count

        return 200, d

    @protocol.handle(methods.get_version, version_id="id", env="tid")
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

        d = {"model": version}

        # todo: batch get_log into single query?
        d["resources"] = []
        for res_dict in resources:
            if bool(include_logs):
                res_dict["actions"] = await data.ResourceAction.get_log(
                    env.id, res_dict["resource_version_id"], log_filter, limit
                )

            d["resources"].append(res_dict)

        d["unknowns"] = await data.UnknownParameter.get_list(environment=env.id, version=version_id)

        return 200, d

    @protocol.handle(methods.delete_version, version_id="id", env="tid")
    async def delete_version(self, env, version_id):
        version = await data.ConfigurationModel.get_version(env.id, version_id)
        if version is None:
            return 404, {"message": "The given configuration model does not exist yet."}

        await version.delete_cascade()
        return 200

    @protocol.handle(methods_v2.reserve_version, env="tid")
    async def reserve_version(self, env: data.Environment) -> int:
        return await env.get_next_version()

    @protocol.handle(methods.put_version, env="tid")
    async def put_version(
        self,
        env: data.Environment,
        version: int,
        resources: List[JsonType],
        resource_state: Dict[ResourceIdStr, const.ResourceState],
        unknowns: List[Dict[str, PrimitiveTypes]],
        version_info: JsonType,
        compiler_version: str = None,
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
        :param compiler_version:
        :return:
        """

        if not compiler_version:
            raise BadRequest("Older compiler versions are no longer supported, please update your compiler")

        if version > env.last_version:
            raise BadRequest(
                f"The version number used is {version} "
                f"which is higher than the last outstanding reservation {env.last_version}"
            )
        if version <= 0:
            raise BadRequest(f"The version number used ({version}) is not positive")

        started = datetime.datetime.now()

        agents = set()
        # lookup for all RV's, lookup by resource id
        rv_dict = {}
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

        # hook up all CADs
        for f, t in cross_agent_dep:
            res_obj = rv_dict[t.resource_str()]
            res_obj.provides.append(f.resource_version_id)

        # detect failed compiles
        def safe_get(input, key, default):
            if not isinstance(input, dict):
                return default
            if key not in input:
                return default
            return input[key]

        metadata = safe_get(version_info, const.EXPORT_META_DATA, {})
        compile_state = safe_get(metadata, const.META_DATA_COMPILE_STATE, "")
        failed = compile_state == const.Compilestate.failed.name

        resources_to_purge: List[data.Resource] = []
        if not failed and (await env.get(PURGE_ON_DELETE)):
            # search for deleted resources (purge_on_delete)
            resources_to_purge = await data.Resource.get_deleted_resources(env.id, version, set(rv_dict.keys()))

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
                date=datetime.datetime.now(),
                total=len(resources),
                version_info=version_info,
                undeployable=undeployable_ids,
                skipped_for_undeployable=skip_list,
            )
            await cm.insert()
        except asyncpg.exceptions.UniqueViolationError:
            raise ServerError("The given version is already defined. Versions should be unique.")

        await data.Resource.insert_many(resource_objects)
        await cm.update_fields(total=cm.total + len(resources_to_purge))

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
            await up.insert()

        for agent in agents:
            await self.agentmanager_service.ensure_agent_registered(env, agent)

        # Don't log ResourceActions without resource_version_ids, because
        # no API call exists to retrieve them.
        if resource_version_ids:
            now = datetime.datetime.now()
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
            await ra.insert()

        LOGGER.debug("Successfully stored version %d", version)

        self.resource_service.clear_env_cache(env)

        auto_deploy = await env.get(data.AUTO_DEPLOY)
        if auto_deploy:
            LOGGER.debug("Auto deploying version %d", version)
            push_on_auto_deploy: bool = await env.get(data.PUSH_ON_AUTO_DEPLOY)
            agent_trigger_method_on_autodeploy = await env.get(data.AGENT_TRIGGER_METHOD_ON_AUTO_DEPLOY)
            agent_trigger_method_on_autodeploy = const.AgentTriggerMethod[agent_trigger_method_on_autodeploy]
            await self.release_version(env, version, push_on_auto_deploy, agent_trigger_method_on_autodeploy)

        return 200

    @protocol.handle(methods.release_version, version_id="id", env="tid")
    async def release_version(
        self,
        env: data.Environment,
        version_id: int,
        push: bool,
        agent_trigger_method: Optional[const.AgentTriggerMethod] = None,
    ) -> Apireturn:
        model = await data.ConfigurationModel.get_version(env.id, version_id)
        if model is None:
            return 404, {"message": "The request version does not exist."}

        await model.update_fields(released=True, result=const.VersionState.deploying)

        if model.total == 0:
            await model.mark_done()
            return 200, {"model": model}

        # Already mark undeployable resources as deployed to create a better UX (change the version counters)
        undep = await model.get_undeployable()
        undep = [rid + ",v=%s" % version_id for rid in undep]

        now = datetime.datetime.now()

        # not checking error conditions
        await self.resource_service.resource_action_update(
            env,
            undep,
            action_id=uuid.uuid4(),
            started=now,
            finished=now,
            status=const.ResourceState.undefined,
            action=const.ResourceAction.deploy,
            changes={},
            messages=[],
            change=const.Change.nochange,
            send_events=False,
        )

        skippable = await model.get_skipped_for_undeployable()
        skippable = [rid + ",v=%s" % version_id for rid in skippable]
        # not checking error conditions
        await self.resource_service.resource_action_update(
            env,
            skippable,
            action_id=uuid.uuid4(),
            started=now,
            finished=now,
            status=const.ResourceState.skipped_for_undefined,
            action=const.ResourceAction.deploy,
            changes={},
            messages=[],
            change=const.Change.nochange,
            send_events=False,
        )

        if push:
            # fetch all resource in this cm and create a list of distinct agents
            agents = await data.ConfigurationModel.get_agents(env.id, version_id)
            await self.autostarted_agent_manager._ensure_agents(env, agents)

            for agent in agents:
                client = self.agentmanager_service.get_agent_client(env.id, agent)
                if client is not None:
                    if not agent_trigger_method:
                        env_agent_trigger_method = await env.get(ENVIRONMENT_AGENT_TRIGGER_METHOD)
                        incremental_deploy = env_agent_trigger_method == const.AgentTriggerMethod.push_incremental_deploy
                    else:
                        incremental_deploy = agent_trigger_method is const.AgentTriggerMethod.push_incremental_deploy
                    self.add_background_task(client.trigger(env.id, agent, incremental_deploy))
                else:
                    LOGGER.warning("Agent %s from model %s in env %s is not available for a deploy", agent, version_id, env.id)

        return 200, {"model": model}

    @protocol.handle(methods.deploy, env="tid")
    async def deploy(
        self,
        env: data.Environment,
        agent_trigger_method: const.AgentTriggerMethod = const.AgentTriggerMethod.push_full_deploy,
        agents: List[str] = None,
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
