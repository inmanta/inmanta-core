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
import logging
import os
import time
import uuid
from collections import abc

import pydantic
from inmanta import const

import inmanta
from agent_server.conftest import get_agent, wait_for_n_deployed_resources
from inmanta import data
from inmanta.agent.handler import DiscoveryHandler, HandlerContext, provider
from inmanta.agent.io.local import LocalIO
from inmanta.data import ResourceIdStr
from inmanta.data.model import BaseModel
from inmanta.resources import DiscoveryResource, Id, Resource, resource
from inmanta.util import get_compiler_version



#
# @resource("test_model::MyDiscoveryResource", agent="discovery_agent", id_attribute="key")
# class MyDiscoveryResource(DiscoveryResource):
#     fields = ("key",)
#
#
# @resource("test_model::MyRegularResource", agent="regular_agent", id_attribute="path")
# class MyRegularResource(Resource):
#     fields = ("path",)
#
#
# @provider("test_model::MyDiscoveryResource", name="my_discoveryresource_handler")
# class Mock_DiscoveryHandler(DiscoveryHandler[MyDiscoveryResource, MyUnmanagedResource]):
#     def __init__(self, agent: inmanta.agent.agent.AgentInstance, path):
#         super().__init__(agent)
#         self._path = path
#         self._client = None
#
#     def discover_resources(self, ctx: HandlerContext, discovery_resource: MyDiscoveryResource) -> abc.Mapping[
#         ResourceIdStr, MyUnmanagedResource]:
#         dirs = os.listdir(self._path)
#
#         resources = {Id(entity_type="std::Directory", agent_name="internal", attribute="path",
#             attribute_value=os.path.join(self._path, dir), ).resource_str(): MyUnmanagedResource(
#             path=os.path.join(self._path, dir)) for dir in dirs}
#
#         return resources


async def _deploy_resources(client, environment, resources, version, push, agent_trigger_method=None):
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(environment, version, push, agent_trigger_method)
    assert result.code == 200

    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == len(resources)

    result = await client.get_version(environment, version)
    assert result.code == 200

    return result

LOGGER = logging.getLogger(__name__)

async def test_discovery_resource_handler(
    server, client, clienthelper, environment, no_agent_backoff, async_finalizer, tmpdir, agent_factory, caplog
):
    """
    This test creates sub-directories and checks that they are onboarded as resources of type std::Directory
    """

    with caplog.at_level(logging.DEBUG):
        LOGGER.debug("Start session")
        agent = await agent_factory(
            environment=environment,
            # agent_map={"regular_agent": "", "discovery_agent": os.path.abspath(tmpdir)},
            agent_map={"host": "localhost"},
            hostname="host",
            agent_names=["regular_agent", "discovery_agent"],
            code_loader=True,
        )
        # # create 3 regular resources
        # for i in range(3):
        #     path = f"{tmpdir}/sub_dir_{i}"
        #     key = f"std::Directory[regular_agent,path={path}]"
        #     version = int(time.time())
        #     res = data.Resource.new(environment=uuid.UUID(environment), resource_version_id=key + ",v=%d" % version, attributes={"path": path})
        #     await res.insert()

        # create 3 unmanaged resources, ready for discovery

        def populate_tmp_dir():
            for i in range(6):
                tmpdir.mkdir(f"sub_dir_{i}")

        populate_tmp_dir()

        assert "regular_agent" in agent._instances
        assert "discovery_agent" in agent._instances
        discovery_agent_instance = agent._instances["discovery_agent"]

        # agent = await get_agent(server, environment, "agent")

        @resource("test::MyDiscoveryResource", agent="discovery_agent", id_attribute="key")
        class MyDiscoveryResource(DiscoveryResource):
            fields = ("key",)

        @resource("test::MyRegularResource", agent="regular_agent", id_attribute="path")
        class MyRegularResource(Resource):
            fields = ("path",)

        class MyUnmanagedResource(BaseModel):
            path: str

        @provider("test::MyDiscoveryResource", name="my_discoveryresource_handler")
        class Mock_DiscoveryHandler(DiscoveryHandler[MyDiscoveryResource, MyUnmanagedResource]):
            def __init__(self, agent: inmanta.agent.agent.AgentInstance, io:LocalIO):
                super().__init__(agent)
                self._top_dir_path = os.path.abspath(tmpdir)
                self._client = None

            def discover_resources(
                self, ctx: HandlerContext, discovery_resource: MyDiscoveryResource
            ) -> abc.Mapping[ResourceIdStr, MyUnmanagedResource]:
                dirs = os.listdir(self._top_dir_path)

                resources = {
                    Id(
                        entity_type="std::Directory",
                        agent_name="discovery_agent",
                        attribute="path",
                        attribute_value=os.path.join(self._top_dir_path, dir),
                    ).resource_str(): MyUnmanagedResource(path=os.path.join(self._top_dir_path, dir))
                    for dir in dirs
                }

                return resources

            def close(self) -> None:
                pass

        # resource_handler = Mock_DiscoveryHandler(discovery_agent_instance, os.path.abspath(tmpdir))

        # make_source_structure
        discovery_resource_id = Id(
            entity_type="test_model::MyDiscoveryResource", agent_name="discovery_agent", attribute="key", attribute_value=tmpdir
        )
        discovery_resource = MyDiscoveryResource(discovery_resource_id)
        ctx = HandlerContext(discovery_resource)

        version = await clienthelper.get_version()

        resources = [
            {
                "key": "key1",
                "value": "value2",
                "id": "test::MyDiscoveryResource[discovery_agent,key=key1],v=%d" % version,
                # "id": "test::Resource[discovery_agent,key=key1],v=%d" % version,
                "send_event": True,
                "purged": False,
                "requires": [],
            }
            ]

        # version1 = await clienthelper.get_version()
        # resources_version_1 = get_resources(version1)
        #

        #
        # assert result.code == 200
        #
        # LOGGER.debug("call to release_version")
        # result = await client.release_version(environment, version1, True, const.AgentTriggerMethod.push_full_deploy)
        # assert result.code == 200

        # version = await clienthelper.get_version()
        # result = await client.put_version(
        #     tid=environment,
        #     version=version,
        #     resources=resources,
        #     resource_state={},
        #     unknowns=[],
        #     version_info={},
        #     compiler_version=get_compiler_version(),
        # )
        result = await _deploy_resources(client, environment, resources, version, push=True)
        assert result.code == 200

        resource_list = await data.Resource.get_resources_in_latest_version(uuid.UUID(environment))

        assert resource_list, resource_list


        LOGGER.debug("call to ensure_code")
        out = await agent.ensure_code(
            environment=environment,
            version=version,
            resource_types=["test::MyDiscoveryResource"],
        )
        LOGGER.debug("call to _deploy_resources")
        assert result.code == 200

        await wait_for_n_deployed_resources(client, environment, version, n=1)
        # assert False, "result"
        result = await client.get_version(environment, version)
        # assert False, result
        # resource_handler.deploy(ctx, discovery_resource)


        result = await client.discovered_resources_get_batch(
            environment,
        )
        assert result.code == 200
        assert len(result.result["data"]) == 6
        expected = [
            {
                "discovered_resource_id": f"std::Directory[discovery_agent,path={tmpdir}/sub_dir_{i}]",
                "values": {"path": f"{tmpdir}/sub_dir_{i}"},
            }
            for i in range(6)
        ]
        assert result.result["data"] == expected
