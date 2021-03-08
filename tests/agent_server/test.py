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
from typing import Callable, List, Optional
from uuid import UUID

import pytest

from agent_server.conftest import ResourceContainer
from inmanta import const, resources
from inmanta.agent.handler import CRUDHandler, HandlerContext, ResourcePurged, provider
from inmanta.const import Change, ResourceAction, ResourceState
from inmanta.data import model
from inmanta.protocol.common import Result
from inmanta.protocol.endpoints import Client
from inmanta.resources import Id, PurgeableResource, Resource, resource
from inmanta.util import get_compiler_version
from utils import _wait_until_deployment_finishes

logger = logging.getLogger("inmanta.test.event_client")

QUERY_LIMIT = 3  # For testing only, small enough to have multiple queries, big enough to iterate through elements in response


class EventClient:
    def __init__(self, client: Client, environment: UUID) -> None:
        self._client = client
        self._env = environment

    @property
    def client(self) -> Client:
        return self._client

    @property
    def environment(self) -> UUID:
        return self._env

    async def get_resource_action(
        self,
        resource_id: Id,
        action_filter: Callable[[model.ResourceAction], bool],
        oldest_first: bool = False,
        after: Optional[datetime.datetime] = None,
        before: Optional[datetime.datetime] = None,
    ) -> Optional[model.ResourceAction]:
        before = before or datetime.datetime.now()
        after = after or datetime.datetime.fromtimestamp(0)

        while before > after:
            if not oldest_first:
                response: Result = await self.client.get_resource_actions(
                    tid=self.environment,
                    resource_type=resource_id.get_entity_type(),
                    agent=resource_id.get_agent_name(),
                    attribute=resource_id.get_attribute(),
                    attribute_value=resource_id.get_attribute_value(),
                    limit=QUERY_LIMIT,
                    last_timestamp=before,
                )
                if response.code != 200:
                    raise RuntimeError(
                        f"Unexpected response code when getting resource actions: received {response.code} (expected 200)"
                    )

                actions: List[model.ResourceAction] = [
                    model.ResourceAction(**action) for action in response.result.get("data", [])
                ]
            else:
                response: Result = await self.client.get_resource_actions(
                    tid=self.environment,
                    resource_type=resource_id.get_entity_type(),
                    agent=resource_id.get_agent_name(),
                    attribute=resource_id.get_attribute(),
                    attribute_value=resource_id.get_attribute_value(),
                    limit=QUERY_LIMIT,
                    first_timestamp=after,
                )
                if response.code != 200:
                    raise RuntimeError(
                        f"Unexpected response code when getting resource actions: received {response.code} (expected 200)"
                    )

                actions: List[model.ResourceAction] = [
                    model.ResourceAction(**action) for action in response.result.get("data", [])
                ]
                actions.reverse()

            for action in actions:
                if not oldest_first and action.started < after:
                    # We get fixed size pages so this might happen when we reach the end
                    break

                if oldest_first and action.started > before:
                    # We get fixed size pages so this might happen when we reach the end
                    break

                if action_filter(action):
                    return action

            if len(actions) == 0:
                before = after
            elif not oldest_first:
                before = actions[-1].started
            else:
                after = actions[-1].started

        return None

    async def get_resource_dependencies(
        self,
        resource_id: Id,
    ) -> List[Id]:
        response = await self.client.get_resource(self.environment, id=resource_id.resource_version_str(), logs=True)
        if response.code != 200:
            raise RuntimeError(
                f"Unexpected response code when getting resource dependencies: received {response.code} (expected 200)"
            )

        resource = response.result.get("resource", {})
        attributes = resource.get("attributes", {})
        requires = attributes.get("requires", {})

        return [Id.parse_id(id) for id in requires]


def is_deployment(action: model.ResourceAction) -> bool:
    return action.action == ResourceAction.deploy and action.status == ResourceState.deployed


def is_deployment_with_change(action: model.ResourceAction) -> bool:
    return is_deployment(action) and (action.change or Change.nochange) != Change.nochange


def resource_handler():
    @resource("test::DependantResource", id_attribute="key", agent="agent")
    class DependentResource(PurgeableResource):
        fields = ("key", "value", "purged", "agent", "operation_uuid")

        @staticmethod
        def get_operation_uuid(_, resource) -> "str":
            return str(uuid.uuid4())

    @provider("test::DependantResource", name="dependant-resource")
    class DependentResource(CRUDHandler):
        def read_resource(self, ctx: HandlerContext, resource: DependentResource) -> None:
            logger.info("Calling read resource")

            if resource.operation_uuid is None:
                raise ResourcePurged()

            id = Resource.object_to_id(resource, "test::DependantResource", "key", "agent")

            environment = self._agent._env_id
            dependencies = resource.requires

            async def should_redeploy() -> bool:
                custom_client = EventClient(client=Client("agent"), environment=environment)

                last_deployment = await custom_client.get_resource_action(
                    resource_id=id,
                    action_filter=is_deployment,
                    oldest_first=False,
                )
                if last_deployment is None:
                    return True

                for dependency in dependencies:
                    dep_first_change = await custom_client.get_resource_action(
                        resource_id=dependency,
                        action_filter=is_deployment_with_change,
                        oldest_first=True,
                        after=last_deployment.started,
                    )
                    if dep_first_change is not None:
                        return True

                return False

            if self.run_sync(should_redeploy):
                logger.info("Deployment needed")
                resource.operation_uuid = str(uuid.uuid4())

        def update_resource(self, ctx: HandlerContext, changes: dict, resource: resources.PurgeableResource) -> None:
            logger.info("Calling update resource")
            resource.operation_uuid = changes["operation_uuid"]
            ctx.set_updated()
            return super().update_resource(ctx, changes, resource)

        def create_resource(self, ctx: HandlerContext, resource: resources.PurgeableResource) -> None:
            logger.info("Calling create resource")
            resource.operation_uuid = str(uuid.uuid4())
            ctx.set_created()
            return super().create_resource(ctx, resource)


@pytest.mark.asyncio
async def test_incremental_deploys(
    resource_container: ResourceContainer, environment: UUID, server, client: Client, agent, clienthelper
):
    resource_container.Provider.reset()

    # Setting up handler
    resource_handler()

    version = await clienthelper.get_version()
    resources = [
        {
            "key": "1",
            "value": "init",
            "id": f"test::DependantResource[agent1,key=1],v={version}",
            "send_event": False,
            "requires": [
                f"test::Resource[agent1,key=2],v={version}",
                f"test::Resource[agent1,key=3],v={version}",
            ],
            "purged": False,
            "purge_on_delete": True,
            "operation_uuid": None,
            "agent": "agent1",
        },
        {
            "key": "2",
            "value": "init",
            "id": f"test::Resource[agent1,key=2],v={version}",
            "send_event": False,
            "requires": [],
            "purged": False,
        },
        {
            "key": "3",
            "value": "init",
            "id": f"test::Resource[agent1,key=3],v={version}",
            "send_event": False,
            "requires": [],
            "purged": False,
        },
    ]

    # EventClient setup
    event_client = EventClient(client, environment)

    # Initial version
    response: Result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert response.code == 200

    # Initial deployment
    response: Result = await client.release_version(
        environment,
        version,
        True,
        const.AgentTriggerMethod.push_incremental_deploy,
    )
    assert response.code == 200
    await _wait_until_deployment_finishes(client, environment, version)

    resource_id = Id.parse_id(resources[0]["id"])
    last_change = await event_client.get_resource_action(resource_id, is_deployment_with_change, oldest_first=False)
    first_change = await event_client.get_resource_action(resource_id, is_deployment_with_change, oldest_first=True)

    # We check that we only did one deployment, to create the resource
    assert last_change == first_change
    assert last_change.change == Change.created
    assert last_change.version == version

    # TODO create new version with changed dependency


@pytest.mark.asyncio
async def test_redeploy_version(
    resource_container: ResourceContainer, environment: UUID, server, client: Client, agent, clienthelper
):
    resource_container.Provider.reset()

    # Setting up handler
    resource_handler()

    version = await clienthelper.get_version()
    resources = [
        {
            "key": "1",
            "value": "init",
            "id": f"test::DependantResource[agent1,key=1],v={version}",
            "send_event": False,
            "requires": [
                f"test::Resource[agent1,key=2],v={version}",
                f"test::Resource[agent1,key=3],v={version}",
            ],
            "purged": False,
            "purge_on_delete": True,
            "operation_uuid": None,
            "agent": "agent1",
        },
        {
            "key": "2",
            "value": "init",
            "id": f"test::Resource[agent1,key=2],v={version}",
            "send_event": False,
            "requires": [],
            "purged": False,
        },
        {
            "key": "3",
            "value": "init",
            "id": f"test::Resource[agent1,key=3],v={version}",
            "send_event": False,
            "requires": [],
            "purged": False,
        },
    ]

    # EventClient setup
    event_client = EventClient(client, environment)

    # Initial version
    response: Result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert response.code == 200

    # Initial deployment
    response: Result = await client.release_version(
        environment,
        version,
        True,
        const.AgentTriggerMethod.push_full_deploy,
    )
    assert response.code == 200
    await _wait_until_deployment_finishes(client, environment, version)

    resource_id = Id.parse_id(resources[0]["id"])
    last_change = await event_client.get_resource_action(resource_id, is_deployment_with_change, oldest_first=False)
    first_change = await event_client.get_resource_action(resource_id, is_deployment_with_change, oldest_first=True)

    # We check that we only did one deployment, to create the resource
    assert last_change == first_change
    assert last_change.change == Change.created
    assert last_change.version == version

    # This shouldn't change anything
    resources[0]["operation_uuid"] = str(uuid.uuid4())

    # Redeploying same version deployment
    response: Result = await client.release_version(
        environment,
        version,
        True,
        const.AgentTriggerMethod.push_full_deploy,
    )
    assert response.code == 200
    await _wait_until_deployment_finishes(client, environment, version)

    previous_change = last_change
    last_change = await event_client.get_resource_action(resource_id, is_deployment_with_change, oldest_first=False)

    # We check that no redeployment is done
    assert previous_change == last_change
    assert last_change.change == Change.created
    assert last_change.version == version
