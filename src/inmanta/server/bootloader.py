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
from typing import Callable, Dict, Generator, List, Optional

from inmanta.const import EXTENSION_MODULE, EXTENSION_NAMESPACE
from inmanta.server import config
from inmanta.server.extensions import ApplicationContext, FeatureManager, InvalidSliceNameException
from inmanta.server.protocol import Server, ServerSlice

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
        super().__init__()
        self.parent = parent
        self.namespace = namespace

    def register_slice(self, slice: ServerSlice) -> None:
        name = slice.name
        if not name.startswith(self.namespace + "."):
            raise InvalidSliceNameException(f"{name} should be in namespace {self.namespace}")
        self.parent.register_slice(slice)

    def set_feature_manager(self, feature_manager: FeatureManager) -> None:
        self.parent.set_feature_manager(feature_manager)


class InmantaBootloader(object):
    """The inmanta bootloader is responsible for:
    - discovering extensions
    - loading extensions
    - loading core and extension slices
    - starting the server and its slices in the correct order
    """

    def __init__(self) -> None:
        self.restserver = Server()
        self.started = False
        self.feature_manager: Optional[FeatureManager] = None

    async def start(self) -> None:
        ctx = self.load_slices()
        self.feature_manager = ctx.get_feature_manager()
        for mypart in ctx.get_slices():
            self.restserver.add_slice(mypart)
            ctx.get_feature_manager().add_slice(mypart)
        await self.restserver.start()
        self.started = True

    async def stop(self) -> None:
        await self.restserver.stop()
        if self.feature_manager is not None:
            self.feature_manager.stop()

    # Extension loading Phase I: from start to setup functions collected
    def _discover_plugin_packages(self) -> List[str]:
        """Discover all packages that are defined in the inmanta_ext namespace package. Filter available extensions based on
        enabled_extensions and disabled_extensions config in the server configuration.

        :return: A list of all subpackages defined in inmanta_ext
        """
        inmanta_ext = importlib.import_module(EXTENSION_NAMESPACE)
        available = {name[len(EXTENSION_NAMESPACE) + 1 :]: name for finder, name, ispkg in iter_namespace(inmanta_ext)}

        LOGGER.info("Discovered extensions: %s", ", ".join(available.keys()))

        extensions = []
        enabled = [x for x in config.server_enabled_extensions.get() if len(x)]

        if enabled:
            for ext in enabled:
                if ext not in available:
                    raise PluginLoadFailed(
                        f"Extension {ext} in config option {config.server_enabled_extensions.name} in section "
                        f"{config.server_enabled_extensions.section} is not available."
                    )

                extensions.append(available[ext])
        elif len(available) > 1:
            # More than core is available
            LOGGER.info(
                f"Load extensions by setting configuration option {config.server_enabled_extensions.name} in section "
                f"{config.server_enabled_extensions.section}. {len(available) - 1} extensions available but none are enabled."
            )

        if "core" not in extensions:
            extensions.append(available["core"])

        return extensions

    def _load_extension(self, name: str) -> Callable[[ApplicationContext], None]:
        """Import the extension defined in the package in name and return the setup function that needs to be called for the
        extension to register its slices in the application context.
        """
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
        """Discover all extensions, validate correct naming and load its setup function"""
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
        """
        Call the setup function on all extensions and let them register their slices in the ApplicationContext.
        """
        ctx = ApplicationContext()
        for name, setup in extensions.items():
            myctx = ConstrainedApplicationContext(ctx, name)
            setup(myctx)
        return ctx

    def load_slices(self) -> ApplicationContext:
        """
        Load all slices in the server
        """
        exts = self._load_extensions()
        return self._collect_slices(exts)
