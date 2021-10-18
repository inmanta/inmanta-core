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
import asyncio
import logging
import uuid
from typing import List, Optional, cast

from inmanta import data
from inmanta.data.model import ResourceVersionIdStr
from inmanta.protocol import handle, methods
from inmanta.protocol.exceptions import NotFound
from inmanta.resources import Id
from inmanta.server import (
    SLICE_AGENT_MANAGER,
    SLICE_AUTOSTARTED_AGENT_MANAGER,
    SLICE_DATABASE,
    SLICE_DRYRUN,
    SLICE_TRANSPORT,
    protocol,
)
from inmanta.server.agentmanager import AgentManager, AutostartedAgentManager
from inmanta.types import Apireturn, JsonType

LOGGER = logging.getLogger(__name__)


class DyrunService(protocol.ServerSlice):
    """Slice for dryun support"""

    agent_manager: AgentManager
    autostarted_agent_manager: AutostartedAgentManager

    def __init__(self) -> None:
        super(DyrunService, self).__init__(SLICE_DRYRUN)
        self.dryrun_lock = asyncio.Lock()

    def get_dependencies(self) -> List[str]:
        return [SLICE_DATABASE, SLICE_AGENT_MANAGER, SLICE_AUTOSTARTED_AGENT_MANAGER]

    def get_depended_by(self) -> List[str]:
        return [SLICE_TRANSPORT]

    async def prestart(self, server: protocol.Server) -> None:
        await super().prestart(server)
        self.agent_manager = cast(AgentManager, server.get_slice(SLICE_AGENT_MANAGER))
        self.autostarted_agent_manager = cast(AutostartedAgentManager, server.get_slice(SLICE_AUTOSTARTED_AGENT_MANAGER))

    @handle(methods.dryrun_request, version_id="id", env="tid")
    async def dryrun_request(self, env: data.Environment, version_id: int) -> Apireturn:
        model = await data.ConfigurationModel.get_version(environment=env.id, version=version_id)
        if model is None:
            return 404, {"message": "The request version does not exist."}

        # fetch all resource in this cm and create a list of distinct agents
        rvs = await data.Resource.get_list(model=version_id, environment=env.id)

        # Create a dryrun document
        dryrun = await data.DryRun.create(environment=env.id, model=version_id, todo=len(rvs), total=len(rvs))

        agents = await data.ConfigurationModel.get_agents(env.id, version_id)
        await self.autostarted_agent_manager._ensure_agents(env, agents)

        for agent in agents:
            client = self.agent_manager.get_agent_client(env.id, agent)
            if client is not None:
                self.add_background_task(client.do_dryrun(env.id, dryrun.id, agent, version_id))
            else:
                LOGGER.warning("Agent %s from model %s in env %s is not available for a dryrun", agent, version_id, env.id)

        # Mark the resources in an undeployable state as done
        async with self.dryrun_lock:
            undeployable_ids = await model.get_undeployable()
            undeployable_version_ids = [ResourceVersionIdStr(rid + ",v=%s" % version_id) for rid in undeployable_ids]
            undeployable = await data.Resource.get_resources(environment=env.id, resource_version_ids=undeployable_version_ids)
            for res in undeployable:
                parsed_id = Id.parse_id(res.resource_version_id)
                payload = {
                    "changes": {},
                    "id_fields": {
                        "entity_type": res.resource_type,
                        "agent_name": res.agent,
                        "attribute": parsed_id.attribute,
                        "attribute_value": parsed_id.attribute_value,
                        "version": res.model,
                    },
                    "id": res.resource_version_id,
                }
                await data.DryRun.update_resource(dryrun.id, res.resource_version_id, payload)

            skip_undeployable_ids = await model.get_skipped_for_undeployable()
            skip_undeployable_version_ids = [ResourceVersionIdStr(rid + ",v=%s" % version_id) for rid in skip_undeployable_ids]
            skipundeployable = await data.Resource.get_resources(
                environment=env.id, resource_version_ids=skip_undeployable_version_ids
            )
            for res in skipundeployable:
                parsed_id = Id.parse_id(res.resource_version_id)
                payload = {
                    "changes": {},
                    "id_fields": {
                        "entity_type": res.resource_type,
                        "agent_name": res.agent,
                        "attribute": parsed_id.attribute,
                        "attribute_value": parsed_id.attribute_value,
                        "version": res.model,
                    },
                    "id": res.resource_version_id,
                }
                await data.DryRun.update_resource(dryrun.id, res.resource_version_id, payload)

        return 200, {"dryrun": dryrun}

    @handle(methods.dryrun_list, env="tid")
    async def dryrun_list(self, env: data.Environment, version: Optional[int] = None) -> Apireturn:
        query_args = {}
        query_args["environment"] = env.id
        if version is not None:
            model = await data.ConfigurationModel.get_version(environment=env.id, version=version)
            if model is None:
                raise NotFound("The request version does not exist.")

            query_args["model"] = version

        dryruns = await data.DryRun.get_list(**query_args)

        return (
            200,
            {"dryruns": [{"id": x.id, "version": x.model, "date": x.date, "total": x.total, "todo": x.todo} for x in dryruns]},
        )

    @handle(methods.dryrun_report, dryrun_id="id", env="tid")
    async def dryrun_report(self, env: data.Environment, dryrun_id: uuid.UUID) -> Apireturn:
        dryrun = await data.DryRun.get_by_id(dryrun_id)
        if dryrun is None:
            raise NotFound("The given dryrun does not exist!")

        return 200, {"dryrun": dryrun}

    @handle(methods.dryrun_update, dryrun_id="id", env="tid")
    async def dryrun_update(
        self, env: data.Environment, dryrun_id: uuid.UUID, resource: ResourceVersionIdStr, changes: JsonType
    ) -> Apireturn:
        async with self.dryrun_lock:
            payload = {"changes": changes, "id_fields": Id.parse_id(resource).to_dict(), "id": resource}
            await data.DryRun.update_resource(dryrun_id, resource, payload)

        return 200
