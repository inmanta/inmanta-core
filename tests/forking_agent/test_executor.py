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

import inmanta.config
import inmanta.protocol.ipc_light
from inmanta.agent.executor import MPManager
from inmanta.protocol.ipc_light import ConnectionLost


class Echo(inmanta.protocol.ipc_light.IPCMethod[list[str], None]):

    def __init__(self, args: list[str]) -> None:
        self.args = args

    async def call(self, ctx) -> list[str]:
        return self.args


class GetConfig(inmanta.protocol.ipc_light.IPCMethod[str, None]):

    def __init__(self, section: str, name: str) -> None:
        self.section = section
        self.name = name

    async def call(self, ctx) -> str:
        return inmanta.config.Config.get(self.section, self.name)


async def test_executor_server(tmp_path):
    manager = MPManager(log_folder=str(tmp_path))
    manager._init_once()

    inmanta.config.Config.set("test", "aaa", "bbbb")

    child1 = await manager.make_child_and_connect("Testchild")

    result = await child1.connection.call(Echo(["aaaa"]))

    assert ["aaaa"] == result

    result = await child1.connection.call(GetConfig("test", "aaa"))
    assert "bbbb" == result

    print("stopping")
    await manager.stop()
    print("joining")
    await manager.join(10)
    print("done")

    assert child1.connection.transport.is_closing()


async def test_executor_server_dirty_shutdown(tmp_path):
    manager = MPManager(log_folder=str(tmp_path))
    manager._init_once()

    child1 = await manager.make_child_and_connect("Testchild")

    result = await child1.connection.call(Echo(["aaaa"]))
    assert ["aaaa"] == result
    print("Child there")

    await asyncio.get_running_loop().run_in_executor(None, child1.process.kill)
    print("Kill sent")

    await asyncio.get_running_loop().run_in_executor(None, child1.process.join)
    print("Child gone")

    with pytest.raises(ConnectionLost):
        await child1.connection.call("echo", ["aaaa"])
