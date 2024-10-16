"""
    Copyright 2024 Inmanta
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

import abc
import logging
from uuid import UUID

from inmanta import const
from inmanta.agent.executor import DeployResult
from inmanta.data.model import AttributeStateChange, ResourceIdStr, ResourceVersionIdStr
from inmanta.protocol import Client
from inmanta.resources import Id

LOGGER = logging.getLogger(__name__)


class StateUpdateManager(abc.ABC):
    """
    Interface used by tasks to flush away their state updates, none of these method must do anything for the scheduler to work

    This interface is split off from the taskmanager, to make mocking it easier
    """

    @abc.abstractmethod
    async def send_in_progress(
        self, action_id: UUID, resource_id: ResourceVersionIdStr
    ) -> dict[ResourceIdStr, const.ResourceState]:
        # FIXME: get rid of version in the id
        pass

    @abc.abstractmethod
    async def send_deploy_done(self, result: DeployResult) -> None:
        pass


class ToServerUpdateManager(StateUpdateManager):

    def __init__(self, client: Client, environment: UUID) -> None:
        self.client = client
        self.environment = environment

    async def send_in_progress(
        self, action_id: UUID, resource_id: ResourceVersionIdStr
    ) -> dict[ResourceIdStr, const.ResourceState]:
        result = await self.client.resource_deploy_start(
            tid=self.environment,
            rvid=resource_id,
            action_id=action_id,
        )
        if result.code != 200 or result.result is None:
            raise Exception("Failed to report the start of the deployment to the server")
        return {Id.parse_id(key).resource_str(): const.ResourceState[value] for key, value in result.result["data"].items()}

    async def send_deploy_done(self, result: DeployResult) -> None:
        changes: dict[ResourceVersionIdStr, dict[str, AttributeStateChange]] = {result.rvid: result.changes}
        response = await self.client.resource_deploy_done(
            tid=self.environment,
            rvid=result.rvid,
            action_id=result.action_id,
            status=result.status,
            messages=result.messages,
            changes=changes,
            change=result.change,
        )
        if response.code != 200:
            LOGGER.error("Resource status update failed %s for %s ", response.result, result.rvid)
