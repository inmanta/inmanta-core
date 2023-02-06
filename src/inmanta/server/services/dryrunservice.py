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
from typing import Dict, List, Optional, cast

from inmanta import data
from inmanta.data.model import DryRun, DryRunReport, ResourceDiff, ResourceDiffStatus, ResourceVersionIdStr
from inmanta.protocol import handle, methods, methods_v2
from inmanta.protocol.exceptions import NotFound
from inmanta.resources import Id
from inmanta.server import (
    SLICE_AGENT_MANAGER,
    SLICE_AUTOSTARTED_AGENT_MANAGER,
    SLICE_DATABASE,
    SLICE_DRYRUN,
    SLICE_TRANSPORT,
    diff,
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

        dryrun = await self.create_dryrun(env, version_id, model)

        return 200, {"dryrun": dryrun}

    async def create_dryrun(self, env: data.Environment, version_id: int, model: data.ConfigurationModel) -> data.DryRun:
        # fetch all resource in this cm and create a list of distinct agents
        rvs = await data.Resource.get_list(model=version_id, environment=env.id)

        # Create a dryrun document
        dryrun = await data.DryRun.create(environment=env.id, model=version_id, todo=len(rvs), total=len(rvs))

        agents = await data.ConfigurationModel.get_agents(env.id, version_id)
        await self.autostarted_agent_manager._ensure_agents(env, agents)

        agents_down = []
        for agent in agents:
            client = self.agent_manager.get_agent_client(env.id, agent)
            if client is not None:
                self.add_background_task(client.do_dryrun(env.id, dryrun.id, agent, version_id))
            else:
                agents_down.append(agent)
                LOGGER.warning("Agent %s from model %s in env %s is not available for a dryrun", agent, version_id, env.id)

        # Mark the resources in an undeployable state as done
        async with self.dryrun_lock:
            undeployable_ids = await model.get_undeployable()
            undeployable_version_ids = [ResourceVersionIdStr(rid + ",v=%s" % version_id) for rid in undeployable_ids]
            undeployable = await data.Resource.get_resources(environment=env.id, resource_version_ids=undeployable_version_ids)
            await self._save_resources_without_changes_to_dryrun(
                dryrun_id=dryrun.id, resources=undeployable, diff_status=ResourceDiffStatus.undefined
            )

            skip_undeployable_ids = await model.get_skipped_for_undeployable()
            skip_undeployable_version_ids = [ResourceVersionIdStr(rid + ",v=%s" % version_id) for rid in skip_undeployable_ids]
            skipundeployable = await data.Resource.get_resources(
                environment=env.id, resource_version_ids=skip_undeployable_version_ids
            )
            await self._save_resources_without_changes_to_dryrun(
                dryrun_id=dryrun.id, resources=skipundeployable, diff_status=ResourceDiffStatus.skipped_for_undefined
            )

            resources_with_agents_down = [
                res
                for res in rvs
                if res.resource_version_id not in undeployable_version_ids
                and res.resource_version_id not in skip_undeployable_version_ids
                and res.agent in agents_down
            ]
            await self._save_resources_without_changes_to_dryrun(
                dryrun_id=dryrun.id, resources=resources_with_agents_down, diff_status=ResourceDiffStatus.agent_down
            )

        return dryrun

    async def _save_resources_without_changes_to_dryrun(
        self, dryrun_id: uuid.UUID, resources: List[data.Resource], diff_status: Optional[ResourceDiffStatus] = None
    ):
        for res in resources:
            parsed_id = Id.parse_id(res.resource_id)
            parsed_id.set_version(res.model)
            payload = {
                "changes": {},
                "id_fields": {
                    "entity_type": res.resource_type,
                    "agent_name": res.agent,
                    "attribute": parsed_id.attribute,
                    "attribute_value": parsed_id.attribute_value,
                    "version": res.model,
                },
                "id": parsed_id.resource_version_str(),
            }
            payload = {**payload, "diff_status": diff_status} if diff_status else payload
            await data.DryRun.update_resource(dryrun_id, parsed_id.resource_version_str(), payload)

    @handle(methods_v2.dryrun_trigger, env="tid")
    async def dryrun_trigger(self, env: data.Environment, version: int) -> uuid.UUID:
        model = await data.ConfigurationModel.get_version(environment=env.id, version=version)
        if model is None:
            raise NotFound("The requested version does not exist.")

        dryrun = await self.create_dryrun(env, version, model)

        return dryrun.id

    @handle(methods.dryrun_list, env="tid")
    async def dryrun_list(self, env: data.Environment, version: Optional[int] = None) -> Apireturn:
        query_args = {}
        query_args["environment"] = env.id
        if version is not None:
            model = await data.ConfigurationModel.get_version(environment=env.id, version=version)
            if model is None:
                raise NotFound("The request version does not exist.")

            query_args["model"] = version

        dryruns = await data.DryRun.get_list(
            order_by_column=None, order=None, limit=None, offset=None, no_obj=None, lock=None, connection=None, **query_args
        )

        return (
            200,
            {"dryruns": [{"id": x.id, "version": x.model, "date": x.date, "total": x.total, "todo": x.todo} for x in dryruns]},
        )

    @handle(methods_v2.list_dryruns, env="tid")
    async def list_dryruns(self, env: data.Environment, version: int) -> List[DryRun]:
        model = await data.ConfigurationModel.get_version(environment=env.id, version=version)
        if model is None:
            raise NotFound("The requested version does not exist.")

        dtos = await data.DryRun.list_dryruns(order_by_column="date", order="DESC", environment=env.id, model=version)
        return dtos

    @handle(methods.dryrun_report, dryrun_id="id", env="tid")
    async def dryrun_report(self, env: data.Environment, dryrun_id: uuid.UUID) -> Apireturn:
        dryrun = await data.DryRun.get_by_id(dryrun_id)
        if dryrun is None:
            raise NotFound("The given dryrun does not exist!")

        return 200, {"dryrun": dryrun}

    @handle(methods_v2.get_dryrun_diff, env="tid")
    async def dryrun_diff(self, env: data.Environment, version: int, report_id: uuid.UUID) -> DryRunReport:
        dryrun = await data.DryRun.get_one(environment=env.id, model=version, id=report_id)
        if dryrun is None:
            raise NotFound("The given dryrun does not exist!")
        resources = dryrun.to_dict()["resources"]
        from_resources = {}
        to_resources = {}
        resources_with_already_known_status = {
            resource_version_id: resource for resource_version_id, resource in resources.items() if resource.get("diff_status")
        }
        resources_to_diff = {
            resource_version_id: resource
            for resource_version_id, resource in resources.items()
            if resource_version_id not in resources_with_already_known_status.keys()
        }
        for resource_version_id, resource in resources_to_diff.items():
            resource_id = Id.parse_id(resource_version_id).resource_str()

            from_attributes = self.get_attributes_from_changes(resource["changes"], "current")
            to_attributes = self.get_attributes_from_changes(resource["changes"], "desired")
            from_resources[resource_id] = diff.Resource(resource_id, from_attributes)
            to_resources[resource_id] = diff.Resource(resource_id, to_attributes)

            if "purged" in resource["changes"]:
                if self.resource_will_be_unpurged(from_attributes, to_attributes):
                    from_resources.pop(resource_id)
                if self.resource_will_be_purged(from_attributes, to_attributes):
                    to_resources.pop(resource_id)

        version_diff = diff.generate_diff(from_resources, to_resources, include_unmodified=True)
        version_diff += [
            ResourceDiff(
                resource_id=Id.parse_resource_version_id(rvid).resource_str(), attributes={}, status=resource.get("diff_status")
            )
            for rvid, resource in resources_with_already_known_status.items()
        ]
        version_diff.sort(key=lambda r: r.resource_id)
        dto = DryRunReport(summary=dryrun.to_dto(), diff=version_diff)

        return dto

    def get_attributes_from_changes(self, changes: Dict[str, Dict[str, object]], key: str) -> Dict[str, object]:
        return {attr_name: values[key] for attr_name, values in changes.items() if attr_name != "requires"}

    def resource_will_be_unpurged(self, from_attributes: Dict[str, object], to_attributes: Dict[str, object]) -> bool:
        return from_attributes.get("purged") is True and to_attributes.get("purged") is False

    def resource_will_be_purged(self, from_attributes: Dict[str, object], to_attributes: Dict[str, object]) -> bool:
        return from_attributes.get("purged") is False and to_attributes.get("purged") is True

    @handle(methods.dryrun_update, dryrun_id="id", env="tid")
    async def dryrun_update(
        self, env: data.Environment, dryrun_id: uuid.UUID, resource: ResourceVersionIdStr, changes: JsonType
    ) -> Apireturn:
        async with self.dryrun_lock:
            payload = {"changes": changes, "id_fields": Id.parse_id(resource).to_dict(), "id": resource}
            await data.DryRun.update_resource(dryrun_id, resource, payload)

        return 200
