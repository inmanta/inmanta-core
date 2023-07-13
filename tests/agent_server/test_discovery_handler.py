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
import base64
import logging
import os
import typing
from collections import abc
from typing import TypeVar, Dict

import pytest

from inmanta import const, agent, data, resources
from inmanta.agent import Agent
from inmanta.agent.handler import ResourceHandler, DiscoveryHandler, HandlerContext
from inmanta.const import ResourceState
from inmanta.data import ResourceIdStr
from inmanta.protocol import SessionClient, VersionMatch, common
from inmanta.resources import resource, DiscoveryResource
from inmanta.server import SLICE_SESSION_MANAGER
from test_protocol import make_random_file
from utils import _wait_until_deployment_finishes, log_contains, retry_limited

T = TypeVar("T")


class MockSessionClient(SessionClient):
    def __init__(self):
        self._version_match = VersionMatch.highest
        pass

    # def get_file(self, hash_id):
    #     content = b""
    #     if self.return_code != 404:
    #         content = base64.b64encode(self.content)
    #     return common.Result(self.return_code, result={"content": content})

class MyDR:
    pass

class MyUR:
    pass

@resource("test_model::MyDiscoveryResource", agent="agent", id_attribute="path")
class MyDiscoveryResource(DiscoveryResource):
    fields = ("path",)

class Mock_DiscoveryHandler(DiscoveryHandler[MyDR, MyUR]):
    def __init__(self, client, path):
        self._client = client
        self._path = path


    def discover_resources(self, ctx: HandlerContext, discovery_resource: MyDR) -> abc.Mapping[ResourceIdStr, MyUR]:
        out = os.listdir(self._path)
        print(out)
        pass

    def deploy(
        self,
        ctx: HandlerContext,
        resource: resources.Resource,
        requires: Dict[ResourceIdStr, ResourceState],
    ) -> None:
        pass

    def pre(self, ctx: HandlerContext, resource: resources.Resource) -> None:
        pass
    def post(self, ctx: HandlerContext, resource: resources.Resource) -> None:
        pass

async def test_discovery_resource_handler(
    resource_container, server, client, clienthelper, environment, no_agent_backoff, async_finalizer, tmpdir
):
    pass


    client = MockSessionClient()
    resource_handler = Mock_DiscoveryHandler(client, tmpdir)
    res = MyDiscoveryResource()
    ctx = HandlerContext(res)

    resource_handler.execute(ctx, res)
    result = await client.discovered_resources_get_batch(
        environment,
    )
    assert result.code == 200
    assert len(result.result["data"]) == 6

async def test_discovery_resource(
    resource_container, server, client, clienthelper, environment, no_agent_backoff, async_finalizer
):
    resource_container.Provider.reset()
    myagent = agent.Agent(
        hostname="node1", environment=environment, agent_map={"agent1": "localhost", "agent2": "localhost"}, code_loader=False
    )
    await myagent.add_end_point_name("agent1")
    await myagent.add_end_point_name("agent2")
    await myagent.start()
    async_finalizer(myagent.stop)
    await retry_limited(lambda: len(server.get_slice(SLICE_SESSION_MANAGER)._sessions) == 1, 10)

    version = await clienthelper.get_version()

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Discover1[agent1,key=key1],v=%d" % version,
            "requires": [],
            "send_event": False,
            "purged": False,
            "purge_on_delete": False,
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Discover2[agent1,key=key2],v=%d" % version,
            "requires": [],
            "send_event": False,
            "purged": False,
            "purge_on_delete": False,
        },
        {
            "key": "key3",
            "value": "value3",
            "id": "test::Discover3[agent2,key=key3],v=%d" % version,
            "requires": [],
            "send_event": False,
            "purged": False,
            "purge_on_delete": False,
        },
    ]

    await clienthelper.put_version_simple(resources, version)

    # do a deploy
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 3

    # call the API endpoint
    await client.discover_facts(tid=environment)

    discovered_resources = await data.DiscoveredResource.get_list(environment=environment)
    assert len(discovered_resources) == 3

    await myagent.stop()
