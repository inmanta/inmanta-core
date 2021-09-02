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

import logging
import uuid
from datetime import datetime

import pytest

from inmanta import const, data
from inmanta.agent.agent import Agent
from inmanta.export import unknown_parameters
from inmanta.main import Client
from inmanta.server.protocol import Server
from inmanta.util import get_compiler_version
from utils import ClientHelper

LOGGER = logging.getLogger(__name__)


@pytest.fixture(scope="function")
async def environment(environment, client):
    """
    Override the environment fixture, defined in conftest.py, to make sure that the
    purge_on_delete environment setting is enabled for all tests defined in this file.
    """
    result = await client.set_setting(tid=environment, id=data.PURGE_ON_DELETE, value=True)
    assert result.code == 200

    yield environment


@pytest.mark.asyncio
async def test_purge_on_delete_requires(client: Client, server: Server, environment: str, clienthelper: ClientHelper):
    """
    Test purge on delete of resources and inversion of requires
    """
    agent = Agent("localhost", {"blah": "localhost"}, environment=environment, code_loader=False)
    await agent.start()
    aclient = agent._client

    version = await clienthelper.get_version()

    resources = [
        {
            "group": "root",
            "hash": "89bf880a0dc5ffc1156c8d958b4960971370ee6a",
            "id": "std::File[vm1,path=/tmp/file1],v=%d" % version,
            "owner": "root",
            "path": "/tmp/file1",
            "permissions": 644,
            "purged": False,
            "reload": False,
            "requires": [],
            "purge_on_delete": True,
            "version": version,
        },
        {
            "group": "root",
            "hash": "b4350bef50c3ec3ee532d4a3f9d6daedec3d2aba",
            "id": "std::File[vm2,path=/tmp/file2],v=%d" % version,
            "owner": "root",
            "path": "/tmp/file2",
            "permissions": 644,
            "purged": False,
            "reload": False,
            "purge_on_delete": True,
            "requires": ["std::File[vm1,path=/tmp/file1],v=%d" % version],
            "version": version,
        },
    ]

    await clienthelper.put_version_simple(resources, version)

    # Release the model and set all resources as deployed
    result = await client.release_version(environment, version, False)
    assert result.code == 200

    now = datetime.now()
    result = await aclient.resource_action_update(
        environment, ["std::File[vm1,path=/tmp/file1],v=%d" % version], uuid.uuid4(), "deploy", now, now, "deployed", [], {}
    )
    assert result.code == 200

    result = await aclient.resource_action_update(
        environment, ["std::File[vm2,path=/tmp/file2],v=%d" % version], uuid.uuid4(), "deploy", now, now, "deployed", [], {}
    )
    assert result.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["version"] == version
    assert result.result["model"]["total"] == len(resources)
    assert result.result["model"]["done"] == len(resources)
    assert result.result["model"]["released"]
    assert result.result["model"]["result"] == const.VersionState.success.name

    # validate requires and provides
    file1 = [x for x in result.result["resources"] if "file1" in x["id"]][0]
    file2 = [x for x in result.result["resources"] if "file2" in x["id"]][0]

    assert file2["id"] in file1["provides"]
    assert len(file1["attributes"]["requires"]) == 0

    assert len(file2["provides"]) == 0
    assert file1["id"] in file2["attributes"]["requires"]

    result = await client.decomission_environment(id=environment, metadata={"message": "test", "type": "test"})
    assert result.code == 200

    version = result.result["version"]
    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["total"] == len(resources)

    # validate requires and provides
    file1 = [x for x in result.result["resources"] if "file1" in x["id"]][0]
    file2 = [x for x in result.result["resources"] if "file2" in x["id"]][0]

    assert file2["id"] in file1["attributes"]["requires"]
    assert type(file1["attributes"]["requires"]) == list
    assert len(file1["provides"]) == 0

    assert len(file2["attributes"]["requires"]) == 0
    assert file1["id"] in file2["provides"]
    await agent.stop()


@pytest.mark.asyncio(timeout=20)
async def test_purge_on_delete_compile_failed_with_compile(
    event_loop, client: Client, server: Server, environment: str, snippetcompiler
):
    snippetcompiler.setup_for_snippet(
        """
    h = std::Host(name="test", os=std::linux)
    f = std::ConfigFile(host=h, path="/etc/motd", content="test", purge_on_delete=true)
    """
    )
    version, _ = await snippetcompiler.do_export_and_deploy(do_raise=False)

    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["total"] == 1

    snippetcompiler.setup_for_snippet(
        """
    h = std::Host(name="test")
    """
    )

    # force deploy by having unknown
    unknown_parameters.append({"parameter": "a", "source": "b"})

    version, _ = await snippetcompiler.do_export_and_deploy(do_raise=False)
    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["total"] == 0


@pytest.mark.asyncio
async def test_purge_on_delete_compile_failed(client: Client, server: Server, clienthelper: ClientHelper, environment: str):
    """
    Test purge on delete of resources
    """
    agent = Agent("localhost", {"blah": "localhost"}, environment=environment, code_loader=False)
    await agent.start()
    aclient = agent._client

    version = await clienthelper.get_version()

    resources = [
        {
            "group": "root",
            "hash": "89bf880a0dc5ffc1156c8d958b4960971370ee6a",
            "id": "std::File[vm1,path=/tmp/file1],v=%d" % version,
            "owner": "root",
            "path": "/tmp/file1",
            "permissions": 644,
            "purged": False,
            "reload": False,
            "requires": [],
            "purge_on_delete": True,
            "version": version,
        },
        {
            "group": "root",
            "hash": "b4350bef50c3ec3ee532d4a3f9d6daedec3d2aba",
            "id": "std::File[vm1,path=/tmp/file2],v=%d" % version,
            "owner": "root",
            "path": "/tmp/file2",
            "permissions": 644,
            "purged": False,
            "reload": False,
            "purge_on_delete": True,
            "requires": ["std::File[vm1,path=/tmp/file1],v=%d" % version],
            "version": version,
        },
        {
            "group": "root",
            "hash": "89bf880a0dc5ffc1156c8d958b4960971370ee6a",
            "id": "std::File[vm1,path=/tmp/file3],v=%d" % version,
            "owner": "root",
            "path": "/tmp/file3",
            "permissions": 644,
            "purged": False,
            "reload": False,
            "requires": [],
            "purge_on_delete": True,
            "version": version,
        },
    ]

    await clienthelper.put_version_simple(resources, version)

    # Release the model and set all resources as deployed
    result = await client.release_version(environment, version, False)
    assert result.code == 200

    now = datetime.now()
    result = await aclient.resource_action_update(
        environment, ["std::File[vm1,path=/tmp/file1],v=%d" % version], uuid.uuid4(), "deploy", now, now, "deployed", [], {}
    )
    assert result.code == 200

    result = await aclient.resource_action_update(
        environment, ["std::File[vm1,path=/tmp/file2],v=%d" % version], uuid.uuid4(), "deploy", now, now, "deployed", [], {}
    )
    assert result.code == 200

    result = await aclient.resource_action_update(
        environment, ["std::File[vm1,path=/tmp/file3],v=%d" % version], uuid.uuid4(), "deploy", now, now, "deployed", [], {}
    )
    assert result.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["version"] == version
    assert result.result["model"]["total"] == len(resources)
    assert result.result["model"]["done"] == len(resources)
    assert result.result["model"]["released"]
    assert result.result["model"]["result"] == const.VersionState.success.name

    # New version with only file3
    version = await clienthelper.get_version()
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=[],
        unknowns=[{"parameter": "a", "source": "b"}],
        version_info={const.EXPORT_META_DATA: {const.META_DATA_COMPILE_STATE: const.Compilestate.failed}},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["total"] == 0
    await agent.stop()
    assert len(result.result["unknowns"]) == 1


@pytest.mark.asyncio
async def test_purge_on_delete(client: Client, clienthelper: ClientHelper, server: Server, environment: str):
    """
    Test purge on delete of resources
    """
    agent = Agent("localhost", {"blah": "localhost"}, environment=environment, code_loader=False)
    await agent.start()
    aclient = agent._client

    version = await clienthelper.get_version()

    resources = [
        {
            "group": "root",
            "hash": "89bf880a0dc5ffc1156c8d958b4960971370ee6a",
            "id": "std::File[vm1,path=/tmp/file1],v=%d" % version,
            "owner": "root",
            "path": "/tmp/file1",
            "permissions": 644,
            "purged": False,
            "reload": False,
            "requires": [],
            "purge_on_delete": True,
            "version": version,
        },
        {
            "group": "root",
            "hash": "b4350bef50c3ec3ee532d4a3f9d6daedec3d2aba",
            "id": "std::File[vm1,path=/tmp/file2],v=%d" % version,
            "owner": "root",
            "path": "/tmp/file2",
            "permissions": 644,
            "purged": False,
            "reload": False,
            "purge_on_delete": True,
            "requires": ["std::File[vm1,path=/tmp/file1],v=%d" % version],
            "version": version,
        },
        {
            "group": "root",
            "hash": "89bf880a0dc5ffc1156c8d958b4960971370ee6a",
            "id": "std::File[vm1,path=/tmp/file3],v=%d" % version,
            "owner": "root",
            "path": "/tmp/file3",
            "permissions": 644,
            "purged": False,
            "reload": False,
            "requires": [],
            "purge_on_delete": True,
            "version": version,
        },
    ]

    res = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert res.code == 200

    # Release the model and set all resources as deployed
    result = await client.release_version(environment, version, False)
    assert result.code == 200

    now = datetime.now()
    result = await aclient.resource_action_update(
        environment, ["std::File[vm1,path=/tmp/file1],v=%d" % version], uuid.uuid4(), "deploy", now, now, "deployed", [], {}
    )
    assert result.code == 200

    result = await aclient.resource_action_update(
        environment, ["std::File[vm1,path=/tmp/file2],v=%d" % version], uuid.uuid4(), "deploy", now, now, "deployed", [], {}
    )
    assert result.code == 200

    result = await aclient.resource_action_update(
        environment, ["std::File[vm1,path=/tmp/file3],v=%d" % version], uuid.uuid4(), "deploy", now, now, "deployed", [], {}
    )
    assert result.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["version"] == version
    assert result.result["model"]["total"] == len(resources)
    assert result.result["model"]["done"] == len(resources)
    assert result.result["model"]["released"]
    assert result.result["model"]["result"] == const.VersionState.success.name

    # New version with only file3
    version = await clienthelper.get_version()
    res3 = {
        "group": "root",
        "hash": "89bf880a0dc5ffc1156c8d958b4960971370ee6a",
        "id": "std::File[vm1,path=/tmp/file3],v=%d" % version,
        "owner": "root",
        "path": "/tmp/file3",
        "permissions": 644,
        "purged": False,
        "reload": False,
        "requires": [],
        "purge_on_delete": True,
        "version": version,
    }
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=[res3],
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["total"] == 3

    # validate requires and provides
    file1 = [x for x in result.result["resources"] if "file1" in x["id"]][0]
    file2 = [x for x in result.result["resources"] if "file2" in x["id"]][0]
    file3 = [x for x in result.result["resources"] if "file3" in x["id"]][0]

    assert file1["attributes"]["purged"]
    assert file2["attributes"]["purged"]
    assert not file3["attributes"]["purged"]
    await agent.stop()


@pytest.mark.asyncio
async def test_purge_on_delete_ignore(client: Client, clienthelper: ClientHelper, server: Server, environment: str):
    """
    Test purge on delete behavior for resources that have not longer purged_on_delete set
    """
    agent = Agent("localhost", {"blah": "localhost"}, environment=environment, code_loader=False)
    await agent.start()
    aclient = agent._client

    # Version 1 with purge_on_delete true
    version = await clienthelper.get_version()

    resources = [
        {
            "group": "root",
            "hash": "89bf880a0dc5ffc1156c8d958b4960971370ee6a",
            "id": "std::File[vm1,path=/tmp/file1],v=%d" % version,
            "owner": "root",
            "path": "/tmp/file1",
            "permissions": 644,
            "purged": False,
            "reload": False,
            "requires": [],
            "purge_on_delete": True,
            "version": version,
        }
    ]

    res = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert res.code == 200

    # Release the model and set all resources as deployed
    result = await client.release_version(environment, version, False)
    assert result.code == 200

    now = datetime.now()
    result = await aclient.resource_action_update(
        environment, ["std::File[vm1,path=/tmp/file1],v=%d" % version], uuid.uuid4(), "deploy", now, now, "deployed", [], {}
    )
    assert result.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["version"] == version
    assert result.result["model"]["total"] == len(resources)
    assert result.result["model"]["done"] == len(resources)
    assert result.result["model"]["released"]
    assert result.result["model"]["result"] == const.VersionState.success.name

    # Version 2 with purge_on_delete false
    version = await clienthelper.get_version()

    resources = [
        {
            "group": "root",
            "hash": "89bf880a0dc5ffc1156c8d958b4960971370ee6a",
            "id": "std::File[vm1,path=/tmp/file1],v=%d" % version,
            "owner": "root",
            "path": "/tmp/file1",
            "permissions": 644,
            "purged": False,
            "reload": False,
            "requires": [],
            "purge_on_delete": False,
            "version": version,
        }
    ]

    res = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert res.code == 200

    # Release the model and set all resources as deployed
    result = await client.release_version(environment, version, False)
    assert result.code == 200

    now = datetime.now()
    result = await aclient.resource_action_update(
        environment, ["std::File[vm1,path=/tmp/file1],v=%d" % version], uuid.uuid4(), "deploy", now, now, "deployed", [], {}
    )
    assert result.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["version"] == version
    assert result.result["model"]["total"] == len(resources)
    assert result.result["model"]["done"] == len(resources)
    assert result.result["model"]["released"]
    assert result.result["model"]["result"] == const.VersionState.success.name

    # Version 3 with no resources
    version = await clienthelper.get_version()
    resources = []
    res = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert res.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["version"] == version
    assert result.result["model"]["total"] == len(resources)
    await agent.stop()


@pytest.mark.asyncio
async def test_disable_purge_on_delete(client: Client, clienthelper: ClientHelper, server: Server, environment: str):
    """
    Test disable purge on delete of resources
    """
    agent = Agent("localhost", {"blah": "localhost"}, environment=environment, code_loader=False)
    await agent.start()
    aclient = agent._client
    env = await data.Environment.get_by_id(environment)
    await env.set(data.PURGE_ON_DELETE, False)

    version = await clienthelper.get_version()

    resources = [
        {
            "group": "root",
            "hash": "89bf880a0dc5ffc1156c8d958b4960971370ee6a",
            "id": "std::File[vm1,path=/tmp/file1],v=%d" % version,
            "owner": "root",
            "path": "/tmp/file1",
            "permissions": 644,
            "purged": False,
            "reload": False,
            "requires": [],
            "purge_on_delete": True,
            "version": version,
        }
    ]

    res = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert res.code == 200

    # Release the model and set all resources as deployed
    result = await client.release_version(environment, version, False)
    assert result.code == 200

    now = datetime.now()
    result = await aclient.resource_action_update(
        environment, ["std::File[vm1,path=/tmp/file1],v=%d" % version], uuid.uuid4(), "deploy", now, now, "deployed", [], {}
    )
    assert result.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["result"] == const.VersionState.success.name

    # Empty version
    version = await clienthelper.get_version()
    result = await client.put_version(
        tid=environment, version=version, resources=[], unknowns=[], version_info={}, compiler_version=get_compiler_version()
    )
    assert result.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["total"] == 0

    await agent.stop()
