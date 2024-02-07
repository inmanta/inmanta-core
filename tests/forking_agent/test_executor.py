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

import asyncio

import pytest

from inmanta.agent.executor import MPManager
from inmanta.protocol.ipc_light import ConnectionLost


async def test_executor_server():
    manager = MPManager()
    manager._init_once()

    child1 = await manager.make_child_and_connect("Testchild")

    result = await child1.connection.call("echo", ["aaaa"])

    assert ["aaaa"] == result

    print("stopping")
    await manager.stop()
    print("joining")
    await manager.join(10)
    print("done")

    assert child1.connection.transport.is_closing()


async def test_executor_server_dirty_shutdown():
    manager = MPManager()
    manager._init_once()

    child1 = await manager.make_child_and_connect("Testchild")

    result = await child1.connection.call("echo", ["aaaa"])
    assert ["aaaa"] == result
    print("Child there")

    await asyncio.get_running_loop().run_in_executor(None, child1.process.kill)
    print("Kill sent")

    await asyncio.get_running_loop().run_in_executor(None, child1.process.join)
    print("Child gone")

    with pytest.raises(ConnectionLost):
        await child1.connection.call("echo", ["aaaa"])
