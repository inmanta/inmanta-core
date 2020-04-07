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
import os
import subprocess
import uuid

import pytest

from inmanta.agent import reporting
from inmanta.agent.handler import HandlerContext, InvalidOperation
from inmanta.data.model import AttributeStateChange
from inmanta.resources import Id, PurgeableResource
from inmanta.server import SLICE_SESSION_MANAGER


@pytest.mark.slowtest
@pytest.mark.asyncio
async def test_agent_get_status(server, environment, agent):
    clients = server.get_slice(SLICE_SESSION_MANAGER)._sessions.values()
    assert len(clients) == 1
    clients = [x for x in clients]
    client = clients[0].get_client()
    status = await client.get_status()
    status = status.get_result()
    for name in reporting.reports.keys():
        assert name in status and status[name] != "ERROR"
    assert status.get("env") is None


def test_context_changes():
    """ Test registering changes in the handler context
    """
    resource = PurgeableResource(Id.parse_id("std::File[agent,path=/test],v=1"))
    ctx = HandlerContext(resource)

    # use attribute change attributes
    ctx.update_changes({"value": AttributeStateChange(current="a", desired="b")})
    assert len(ctx.changes) == 1

    # use dict
    ctx.update_changes({"value": dict(current="a", desired="b")})
    assert len(ctx.changes) == 1
    assert isinstance(ctx.changes["value"], AttributeStateChange)

    # use tuple
    ctx.update_changes({"value": ("a", "b")})
    assert len(ctx.changes) == 1
    assert isinstance(ctx.changes["value"], AttributeStateChange)

    # use wrong arguments
    with pytest.raises(InvalidOperation):
        ctx.update_changes({"value": ("a", "b", 3)})

    with pytest.raises(InvalidOperation):
        ctx.update_changes({"value": ["a", "b"]})

    with pytest.raises(InvalidOperation):
        ctx.update_changes({"value": "test"})


@pytest.mark.asyncio
async def test_agent_cannot_retrieve_autostart_agent_map(unused_tcp_port_factory, tmpdir):
    """
        When an agent with the config option use_autostart_agent_map set to true, cannot retrieve the autostart_agent_map
        from the server at startup, the process should exit. Otherwise the process will hang with an empty ioloop and no
        session to the server. This tests verifies whether the process exits correctly.
    """
    state_dir = tmpdir.join("state")
    os.mkdir(state_dir)

    free_port = unused_tcp_port_factory()
    config_file = tmpdir.join("inmanta.cfg")
    with open(config_file, "w") as f:
        f.write(
            f"""[config]
state-dir={state_dir}
environment={uuid.uuid4()}
use_autostart_agent_map=true

[agent_rest_transport]
port={free_port}
host=127.0.0.1
        """
        )
    try:
        completed_process = subprocess.run(["inmanta", "-vvv", "-c", config_file, "agent"], stdout=subprocess.PIPE, timeout=10)
        assert completed_process.returncode == 1
        assert "Failed to retrieve the autostart_agent_map setting from the server" in completed_process.stdout.decode()
    except subprocess.TimeoutExpired as e:
        for line in e.stdout.decode().split("\n"):
            print(line)
        for line in e.stderr.decode().split("\n"):
            print(line)
        raise e
