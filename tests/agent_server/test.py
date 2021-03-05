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
import json
import logging
import re
import time
from typing import List, Optional
from uuid import UUID

import pytest
from pydantic import BaseModel

from agent_server.conftest import ResourceContainer
from inmanta import const
from inmanta.const import Change, ResourceAction
from inmanta.protocol.common import Result
from inmanta.protocol.endpoints import Client
from inmanta.util import get_compiler_version
from utils import _wait_until_deployment_finishes

logger = logging.getLogger("inmanta.test.wip")

QUERY_LIMIT = 3  # For testing only


class ResourceChange(BaseModel):

    change: Change
    started: datetime.datetime
    finished: datetime.datetime
    version: int


class ResourceId(BaseModel):

    resource_type: str
    agent: str
    key: str
    value: str

    def __str__(self) -> str:
        return f"{self.resource_type}[{self.agent},{self.key}={self.value}]"

    def from_str(id: str) -> "ResourceId":
        reg_match = re.compile(r"(.*)\[(.*),(.*)=(.*)\]").match(id)
        return ResourceId(
            resource_type=reg_match.group(1),
            agent=reg_match.group(2),
            key=reg_match.group(3),
            value=reg_match.group(4),
        )


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

    async def get_resource_change(
        self,
        resource_id: ResourceId,
        oldest_first: bool = False,
        before: Optional[datetime.datetime] = None,
        after: Optional[datetime.datetime] = None,
    ) -> Optional[ResourceChange]:
        before = before or datetime.datetime.now()
        after = after or datetime.datetime.fromtimestamp(0)

        while before > after:
            if not oldest_first:
                response: Result = await self.client.get_resource_actions(
                    tid=self.environment,
                    resource_type=resource_id.resource_type,
                    agent=resource_id.agent,
                    attribute=resource_id.key,
                    attribute_value=resource_id.value,
                    limit=QUERY_LIMIT,
                    last_timestamp=before,
                )
                if response.code != 200:
                    raise RuntimeError(
                        f"Unexpected response code when getting resource actions: received {response.code} (expected 200)"
                    )

                actions: List[dict] = response.result.get("data", [])
            else:
                response: Result = await self.client.get_resource_actions(
                    tid=self.environment,
                    resource_type=resource_id.resource_type,
                    agent=resource_id.agent,
                    attribute=resource_id.key,
                    attribute_value=resource_id.value,
                    limit=QUERY_LIMIT,
                    first_timestamp=after,
                )
                if response.code != 200:
                    raise RuntimeError(
                        f"Unexpected response code when getting resource actions: received {response.code} (expected 200)"
                    )

                actions: List[dict] = response.result.get("data", [])
                actions.reverse()

            for action in actions:
                timestamp = datetime.datetime.strptime(action.get("started"), "%Y-%m-%dT%H:%M:%S.%f")

                if not oldest_first and timestamp < after:
                    # We get fixed size pages so this might happen when we reach the end
                    break

                if oldest_first and timestamp > before:
                    # We get fixed size pages so this might happen when we reach the end
                    break

                if action.get("action", "") != ResourceAction.deploy:
                    continue

                change = action.get("change") or Change.nochange
                if change != Change.nochange:
                    return ResourceChange(
                        change=change,
                        started=timestamp,
                        finished=datetime.datetime.strptime(action.get("finished"), "%Y-%m-%dT%H:%M:%S.%f"),
                        version=action.get("version"),
                    )

            if len(actions) == 0:
                before = after
            elif not oldest_first:
                before = datetime.datetime.strptime(actions[-1].get("started"), "%Y-%m-%dT%H:%M:%S.%f")
            else:
                after = datetime.datetime.strptime(actions[-1].get("started"), "%Y-%m-%dT%H:%M:%S.%f")

        return None

    async def get_resource_dependencies(
        self,
        resource_id: ResourceId,
        version: int,
    ) -> List[ResourceId]:
        response = await self.client.get_resource(self.environment, id=f"{str(resource_id)},v={version}", logs=True)
        if response.code != 200:
            raise RuntimeError(
                f"Unexpected response code when getting resource dependencies: received {response.code} (expected 200)"
            )

        resource = response.result.get("resource", {})
        attributes = resource.get("attributes", {})
        requires = attributes.get("requires", {})

        return [ResourceId.from_str(id) for id in requires]


async def need_redeployment(resource_id: ResourceId, environment: str) -> bool:
    custom_client = EventClient(client=Client("agent"), environment=environment)

    last_deployment = await custom_client.get_resource_change(
        resource_id=resource_id,
        oldest_first=False,
    )
    if last_deployment is None:
        return True

    # TODO TBD Should it be resource from last deployed version or current one? or both?
    dependencies = await custom_client.get_resource_dependencies(resource_id=resource_id, version=last_deployment.version)

    for dependency in dependencies:
        dep_first_change = await custom_client.get_resource_change(
            resource_id=dependency,
            oldest_first=True,
            after=last_deployment.finished,
        )
        if dep_first_change is not None:
            return True

    return False


def get_res(key: str, val: str, version: int, requires: List[str]) -> dict:
    return  {
        "key": key,
        "value": val,
        "id": f"test::Resource[agent1,key={key}],v={version}",
        "send_event": False,
        "requires": requires,
        "purged": False,
    }


async def deploy_resources(client: Client, environment: UUID, version: int, resources: List[dict]):
    response: Result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert response.code == 200

    # do a deploy
    response: Result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert response.code == 200

    response: Result = await client.get_version(environment, version)
    assert response.code == 200
    assert response.result.get("model", {}).get("version", 0) == version

    await _wait_until_deployment_finishes(client, environment, version)


@pytest.mark.asyncio
async def test_event_client_basic(resource_container: ResourceContainer, environment: UUID, server, client: Client, agent, clienthelper):
    """
    Send and receive events within one agent
    """
    resource_container.Provider.reset()

    # EventClient setup
    event_client = EventClient(client, environment)

    # Initial version
    version = await clienthelper.get_version()
    res_1 = get_res("1", "init", version, [])
    res_1_id = ResourceId.from_str(res_1["id"])

    res_2 = get_res("2", "init", version, [])
    res_2_id = ResourceId.from_str(res_2["id"])
    res_1["requires"].append(res_2["id"])

    res_3 = get_res("3", "init", version, [])
    res_3_id = ResourceId.from_str(res_3["id"])
    res_1["requires"].append(res_3["id"])
    res_2["requires"].append(res_3["id"])

    resources = [res_1, res_2, res_3]

    await deploy_resources(client, environment, version, resources)

    for res_id in [res_1_id, res_2_id, res_3_id]:
        last_change = await event_client.get_resource_change(res_id, oldest_first=False)
        first_change = await event_client.get_resource_change(res_id, oldest_first=True)

        assert last_change == first_change
        assert last_change.change == Change.created
        assert last_change.version == version

        assert not await need_redeployment(res_id, environment)

    # Redeploying the same model
    version = await clienthelper.get_version()
    res_1 = get_res("1", "init", version, [])
    res_1_id = ResourceId.from_str(res_1["id"])

    res_2 = get_res("2", "init", version, [])
    res_2_id = ResourceId.from_str(res_2["id"])
    res_1["requires"].append(res_2["id"])

    res_3 = get_res("3", "init", version, [])
    res_3_id = ResourceId.from_str(res_3["id"])
    res_1["requires"].append(res_3["id"])
    res_2["requires"].append(res_3["id"])

    resources = [res_1, res_2, res_3]

    await deploy_resources(client, environment, version, resources)

    for res_id in [res_1_id, res_2_id, res_3_id]:
        last_change = await event_client.get_resource_change(res_id, oldest_first=False)
        first_change = await event_client.get_resource_change(res_id, oldest_first=True)

        assert last_change == first_change
        assert last_change.change == Change.created
        assert last_change.version == version - 1

        assert not await need_redeployment(res_id, environment)
    
    # Modifying second resource
    version = await clienthelper.get_version()
    res_1 = get_res("1", "init", version, [])
    res_1_id = ResourceId.from_str(res_1["id"])

    res_2 = get_res("2", "updated", version, [])
    res_2_id = ResourceId.from_str(res_2["id"])
    res_1["requires"].append(res_2["id"])

    res_3 = get_res("3", "init", version, [])
    res_3_id = ResourceId.from_str(res_3["id"])
    res_1["requires"].append(res_3["id"])
    res_2["requires"].append(res_3["id"])

    resources = [res_1, res_2, res_3]

    await deploy_resources(client, environment, version, resources)

    last_change = await event_client.get_resource_change(res_1_id, oldest_first=False)
    first_change = await event_client.get_resource_change(res_1_id, oldest_first=True)

    assert last_change == first_change
    assert last_change.change == Change.created
    assert last_change.version == version - 2

    assert await need_redeployment(res_1_id, environment)

    last_change = await event_client.get_resource_change(res_2_id, oldest_first=False)
    first_change = await event_client.get_resource_change(res_2_id, oldest_first=True)

    assert last_change != first_change
    assert last_change.change == Change.updated
    assert last_change.version == version
    assert first_change.change == Change.created
    assert first_change.version == version - 2

    assert not await need_redeployment(res_2_id, environment)

    last_change = await event_client.get_resource_change(res_3_id, oldest_first=False)
    first_change = await event_client.get_resource_change(res_3_id, oldest_first=True)

    assert last_change == first_change
    assert last_change.change == Change.created
    assert last_change.version == version - 2

    assert not await need_redeployment(res_3_id, environment)
    

@pytest.mark.asyncio
async def test_event_client(resource_container: ResourceContainer, environment: UUID, server, client: Client, agent, clienthelper):

    resource_container.Provider.reset()

    # EventClient setup
    event_client = EventClient(client, environment)

    # Initial version
    version = await clienthelper.get_version()
    resources = [
        {
            "key": "root",
            "value": "init",
            "id": f"test::Resource[agent1,key=root],v={version}",
            "send_event": False,
            "requires": [
                f"test::Wait[agent1,key=waiter],v={version}",
                f"test::Resource[agent1,key=any],v={version}",
            ],
            "purged": False,
        },
        {
            "key": "waiter",
            "value": "init",
            "id": f"test::Wait[agent1,key=waiter],v={version}",
            "send_event": False,
            "requires": [f"test::Resource[agent1,key=any],v={version}"],
            "purged": False,
        },
        {
            "key": "any",
            "value": "init",
            "id": f"test::Resource[agent1,key=any],v={version}",
            "send_event": False,
            "requires": [],
            "purged": False,
        }
    ]

    response: Result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert response.code == 200

    # do a deploy
    response: Result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert response.code == 200

    response: Result = await client.get_version(environment, version)
    assert response.code == 200
    assert response.result.get("model", {}).get("version", 0) == version

    resource_container.wait_for_done_with_waiters()
    resource_container.waiter.notify()
    await _wait_until_deployment_finishes(client, environment, version)
