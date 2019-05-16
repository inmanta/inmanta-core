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
import importlib
import logging
import pkgutil
from pkgutil import ModuleInfo
from types import ModuleType

from inmanta.const import EXTENSION_NAMESPACE, EXTENSION_MODULE
from inmanta.server import server
from inmanta.server.compilerservice import CompilerService
from inmanta.server.extensions import ApplicationContext, InvalidSliceNameException
from inmanta.server.protocol import Server, ServerSlice
from inmanta.server.agentmanager import AgentManager

from typing import List, Callable, Dict, Generator

from inmanta.server.server import DatabaseSlice

LOGGER = logging.getLogger(__name__)


def iter_namespace(ns_pkg: ModuleType) -> Generator[ModuleInfo, None, None]:
    """From python docs https://packaging.python.org/guides/creating-and-discovering-plugins/"""
    # Specifying the second argument (prefix) to iter_modules makes the
    # returned name an absolute name instead of a relative one. This allows
    # import_module to work without having to do additional modification to
    # the name.
    return pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + ".")


class PluginLoadFailed(Exception):

    pass


class ConstrainedApplicationContext(ApplicationContext):
    def __init__(self, parent: ApplicationContext, namespace: str) -> None:
        self.parent = parent
        self.namespace = namespace

    def register_slice(self, slice: ServerSlice) -> None:
        name = slice.name
        if not name.startswith(self.namespace + "."):
            raise InvalidSliceNameException(f"{name} should be in namespace {self.namespace}")
        self.parent.register_slice(slice)


class InmantaBootloader(object):
    def __init__(self, agent_no_log: bool = False) -> None:
        self.restserver = Server()
        self.agent_no_log = agent_no_log
        self.started = False

    def get_bootstrap_slices(self) -> List[ServerSlice]:
        return [server.Server(agent_no_log=self.agent_no_log), AgentManager(), DatabaseSlice(), CompilerService()]

    async def start(self) -> None:
        for mypart in self.load_slices():
            self.restserver.add_slice(mypart)
        await self.restserver.start()
        self.started = True

    async def stop(self) -> None:
        await self.restserver.stop()

    # Extension loading Phase I: from start to setup functions collected
    def _discover_plugin_packages(self) -> List[str]:
        inmanta_ext = importlib.import_module(EXTENSION_NAMESPACE)
        return [name for finder, name, ispkg in iter_namespace(inmanta_ext)]

    def _load_extension(self, name: str) -> Callable[[ApplicationContext], None]:
        try:
            importlib.import_module(name)
        except Exception as e:
            raise PluginLoadFailed(f"Could not load module {name}") from e

        try:
            mod = importlib.import_module(f"{name}.{EXTENSION_MODULE}")
            return mod.setup
        except Exception as e:
            raise PluginLoadFailed(f"Could not load module {name}.{EXTENSION_MODULE}") from e

    def _load_extensions(self) -> Dict[str, Callable[[ApplicationContext], None]]:
        plugins: Dict[str, Callable[[ApplicationContext], None]] = {}
        for name in self._discover_plugin_packages():
            try:
                plugin = self._load_extension(name)
                assert name.startswith(f"{EXTENSION_NAMESPACE}.")
                name = name[len(EXTENSION_NAMESPACE) + 1 :]
                plugins[name] = plugin
            except PluginLoadFailed:
                LOGGER.warning("Could not load extension %s", name, exc_info=True)
        return plugins

    # Extension loading Phase II: collect slices
    def _collect_slices(self, extensions: Dict[str, Callable[[ApplicationContext], None]]) -> ApplicationContext:
        ctx = ApplicationContext()
        for slice in self.get_bootstrap_slices():
            ctx.register_slice(slice)
        for name, setup in extensions.items():
            myctx = ConstrainedApplicationContext(ctx, name)
            setup(myctx)
        return ctx

    def load_slices(self) -> List[ServerSlice]:
        exts = self._load_extensions()
        ctx = self._collect_slices(exts)
        return ctx.get_slices()
