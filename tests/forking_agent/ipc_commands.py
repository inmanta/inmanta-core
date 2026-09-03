"""
Copyright 2025 Inmanta

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

# This is a separate file to cause the remote side to not load too much code

import logging

import inmanta.agent
import inmanta.agent.executor
import inmanta.config
import inmanta.data
import inmanta.loader
import inmanta.protocol.ipc_light
import inmanta.util


class Echo(inmanta.protocol.ipc_light.IPCMethod[list[str], None]):
    def __init__(self, args: list[str]) -> None:
        self.args = args

    async def call(self, ctx) -> list[str]:
        logging.getLogger(__name__).info("Echo ")
        return self.args


class GetConfig(inmanta.protocol.ipc_light.IPCMethod[str, None]):
    def __init__(self, section: str, name: str) -> None:
        self.section = section
        self.name = name

    async def call(self, ctx) -> str:
        return inmanta.config.Config.get(self.section, self.name)


class GetName(inmanta.protocol.ipc_light.IPCMethod[str, None]):
    async def call(self, ctx) -> str:
        return ctx.name


class TestLoader(inmanta.protocol.ipc_light.IPCMethod[list[str], None]):
    """
    Part of assertions for test_executor_server

    Must be module level to be able to pickle it
    """

    async def call(self, ctx) -> list[str]:
        import inmanta_plugins.test.testB
        import lorem  # noqa: F401

        return [inmanta_plugins.test.testA.test(), inmanta_plugins.test.testB.test()]


class ImportModule(inmanta.protocol.ipc_light.IPCMethod[str, None]):
    """
    Import the given fully-qualified python module from the executor venv and return the result of its test()
    function. Used to assert that a module installed in the executor venv (e.g. an inmanta module installed in
    editable mode) is importable and was loaded.

    Must be module level to be able to pickle it.
    """

    def __init__(self, fq_module_name: str) -> None:
        self.fq_module_name = fq_module_name

    async def call(self, ctx) -> str:
        import importlib

        return importlib.import_module(self.fq_module_name).test()


class IsModuleLoaded(inmanta.protocol.ipc_light.IPCMethod[bool, None]):
    """
    Is the given fully-qualified python module already loaded in the executor process? Unlike ImportModule, this does not
    import it: it asserts that the code install loaded the module by itself.

    Must be module level to be able to pickle it.
    """

    def __init__(self, fq_module_name: str) -> None:
        self.fq_module_name = fq_module_name

    async def call(self, ctx) -> bool:
        import sys

        return self.fq_module_name in sys.modules
