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

import asyncio
import importlib
import logging
import pkgutil
from collections.abc import Generator
from pkgutil import ModuleInfo
from types import ModuleType
from typing import Optional

import asyncpg

from inmanta import logging as inmanta_logging
from inmanta.const import EXTENSION_MODULE, EXTENSION_NAMESPACE
from inmanta.logging import FullLoggingConfig, InmantaLoggerConfig
from inmanta.server import config
from inmanta.server.extensions import ApplicationContext, FeatureManager, InvalidSliceNameException
from inmanta.server.protocol import Server, ServerSlice
from inmanta.stable_api import stable_api

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

    def register_default_logging_config(self, log_config_extender: inmanta_logging.LoggingConfigBuilderExtension) -> None:
        self.parent.register_default_logging_config(log_config_extender)


@stable_api
class InmantaBootloader:
    """The inmanta bootloader is responsible for:
    - discovering extensions
    - loading extensions
    - loading core and extension slices
    - starting the server and its slices in the correct order
    """

    # Cache field for available extensions
    AVAILABLE_EXTENSIONS: Optional[dict[str, str]] = None

    def __init__(self, configure_logging: bool = False) -> None:
        """
        :param configure_logging: This config option is used by the tests to configure the logging framework.
                                  In normal execution, the logging framework is configured by the app.py
        """
        self.restserver = Server()
        self.started = False
        self.feature_manager: Optional[FeatureManager] = None
        # cache for ctx
        self.ctx: ApplicationContext | None = None

        if configure_logging:
            inmanta_logger_config = inmanta_logging.InmantaLoggerConfig.get_instance()
            inmanta_logger_config.apply_options(inmanta_logging.Options())

    async def start(self) -> None:
        self.start_loggers_for_extensions()
        db_wait_time: int = config.db_wait_time.get()
        if db_wait_time != 0:
            # Wait for the database to be up before starting the server
            await self.wait_for_db(db_wait_time)

        ctx = self.load_slices()
        version = ctx.get_feature_manager().get_product_metadata().version
        LOGGER.info("Starting inmanta-server version %s", version)
        for mypart in ctx.get_slices():
            self.restserver.add_slice(mypart)
            ctx.get_feature_manager().add_slice(mypart)
        await self.restserver.start()
        self.started = True

    def start_loggers_for_extensions(self, on_config: InmantaLoggerConfig | None = None) -> FullLoggingConfig:
        ctx = self.load_slices()
        log_config_extenders = ctx.get_default_log_config_extenders()
        if on_config is None:
            on_config = InmantaLoggerConfig.get_current_instance()
        return on_config.extend_config(log_config_extenders)

    async def stop(self, timeout: Optional[int] = None) -> None:
        """
        :param timeout: Raises TimeoutError when the server hasn't finished stopping after
                        this amount of seconds. This argument should only be used by test
                        cases.
        """
        if not timeout:
            await self._stop()
        else:
            await asyncio.wait_for(self._stop(), timeout=timeout)

    async def _stop(self) -> None:
        await self.restserver.stop()
        if self.feature_manager is not None:
            await self.feature_manager.stop()

    @classmethod
    def get_available_extensions(cls) -> dict[str, str]:
        """
        Returns a dictionary of all available inmanta extensions.
        The key contains the name of the extension and the value the fully qualified path to the python package.
        """
        if cls.AVAILABLE_EXTENSIONS is None:
            try:
                inmanta_ext = importlib.import_module(EXTENSION_NAMESPACE)
            except ModuleNotFoundError:
                # This only happens when a test case creates and activates a new venv
                return {}
            else:
                cls.AVAILABLE_EXTENSIONS = {
                    name[len(EXTENSION_NAMESPACE) + 1 :]: name for finder, name, ispkg in iter_namespace(inmanta_ext)
                }
        return dict(cls.AVAILABLE_EXTENSIONS)

    # Extension loading Phase I: from start to setup functions collected
    def _discover_plugin_packages(self, return_all_available_packages: bool = False) -> list[str]:
        """Discover all packages that are defined in the inmanta_ext namespace package. Filter available extensions based on
        enabled_extensions and disabled_extensions config in the server configuration.

        :param return_all_available_packages: Return all available plugin packages independent of whether the extension is
                                              enabled or not.
        :return: A list of all subpackages defined in inmanta_ext
        """
        available = self.get_available_extensions()
        LOGGER.info("Discovered extensions: %s", ", ".join(available.keys()))

        extensions: list[str] = []
        enabled = [x for x in config.server_enabled_extensions.get() if len(x)]

        if return_all_available_packages:
            extensions.extend(available.values())
        elif enabled:
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

    def _load_extension(self, name: str) -> ModuleType:
        """Import the extension defined in the package in name and return the setup function that needs to be called for the
        extension to register its slices in the application context.
        """
        try:
            importlib.import_module(name)
        except Exception as e:
            raise PluginLoadFailed(f"Could not load module {name}") from e

        try:
            mod = importlib.import_module(f"{name}.{EXTENSION_MODULE}")
        except Exception as e:
            raise PluginLoadFailed(f"Could not load module {name}.{EXTENSION_MODULE}") from e
        else:
            self._validate_extension(mod)
            return mod

    def _validate_extension(self, ext_mod: ModuleType) -> None:
        """
        Validate whether the given extension module satisfied the mandatory requirements for an Inmanta extension.
        If the requirements are not satisfied, this method raises an PluginLoadFailed exception.
        """
        if not hasattr(ext_mod, "setup"):
            raise PluginLoadFailed("extension.py doesn't have a setup method.")

    def _load_extensions(self, load_all_extensions: bool = False) -> dict[str, ModuleType]:
        """Discover all extensions, validate correct naming and load its setup function"""
        plugins: dict[str, ModuleType] = {}
        enabled_extensions: list[str] = self._discover_plugin_packages(load_all_extensions)
        LOGGER.info("Enabled extensions: %s", ", ".join(enabled_extensions))
        for name in enabled_extensions:
            try:
                module = self._load_extension(name)
                assert name.startswith(f"{EXTENSION_NAMESPACE}.")
                name = name[len(EXTENSION_NAMESPACE) + 1 :]
                plugins[name] = module
            except PluginLoadFailed:
                LOGGER.warning("Could not load extension %s", name, exc_info=True)
        return plugins

    def _collect_environment_settings(self, ext_module: ModuleType, app_ctx: ApplicationContext) -> None:
        """
        Collect the settings of an Inmanta environment defined by the given extension.
        """
        if not hasattr(ext_module, "register_environment_settings"):
            # Extension doesn't define any environment settings.
            return
        ext_module.register_environment_settings(app_ctx)

    # Extension loading Phase II: collect slices
    def _collect_slices(
        self, extensions: dict[str, ModuleType], only_register_environment_settings: bool = False
    ) -> ApplicationContext:
        """
        Call the setup function on all extensions and let them register their slices in the ApplicationContext.
        """
        ctx = ApplicationContext()
        for name, ext_module in extensions.items():
            myctx = ConstrainedApplicationContext(ctx, name)
            self._collect_environment_settings(ext_module, myctx)
            if not only_register_environment_settings:
                ext_module.setup(myctx)
        return ctx

    def load_slices(
        self, *, load_all_extensions: bool = False, only_register_environment_settings: bool = False
    ) -> ApplicationContext:
        """
        Load all slices in the server
        """
        if self.ctx is not None and not load_all_extensions:
            return self.ctx
        exts: dict[str, ModuleType] = self._load_extensions(load_all_extensions)
        ctx: ApplicationContext = self._collect_slices(exts, only_register_environment_settings)
        self.feature_manager = ctx.get_feature_manager()
        if not only_register_environment_settings and not load_all_extensions:
            self.ctx = ctx
        return ctx

    async def wait_for_db(self, db_wait_time: int) -> None:
        """Wait for the database to be up by attempting to connect at intervals.

        :param db_wait_time: Maximum time to wait for the database to be up, in seconds.
        """

        start_time = asyncio.get_event_loop().time()

        # Retrieve database connection settings from the configuration
        db_settings = {
            "host": config.db_host.get(),
            "port": config.db_port.get(),
            "user": config.db_username.get(),
            "password": config.db_password.get(),
            "database": config.db_name.get(),
        }
        while True:
            try:
                # Attempt to create a database connection
                conn = await asyncpg.connect(**db_settings, timeout=5)  # raises TimeoutError after 5 seconds
                LOGGER.info("Successfully connected to the database.")
                await conn.close(timeout=5)  # close the connection
                return
            except asyncio.TimeoutError:
                LOGGER.info("Waiting for database to be up: Connection attempt timed out.")
            except Exception:
                LOGGER.info("Waiting for database to be up.", exc_info=True)
            # Check if the maximum wait time has been exceeded
            if 0 < db_wait_time < asyncio.get_event_loop().time() - start_time:
                LOGGER.error("Timed out waiting for the database to be up.")
                raise Exception("Database connection timeout after %d seconds." % db_wait_time)
            # Sleep for a second before retrying
            await asyncio.sleep(1)
