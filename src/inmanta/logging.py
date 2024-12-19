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
import logging.config
import os
import re
import sys
from argparse import Namespace
from collections import abc
from collections.abc import Mapping
from io import TextIOWrapper
from logging import handlers
from typing import Optional, TextIO

import colorlog
import yaml
from colorlog.formatter import LogColors
from yaml import Dumper, Node

from inmanta import config, const
from inmanta.config import component_log_configs
from inmanta.const import LOG_CONTEXT_VAR_ENVIRONMENT, NAME_RESOURCE_ACTION_LOGGER
from inmanta.server import config as server_config
from inmanta.stable_api import stable_api

logfire_enabled = os.getenv("LOGFIRE_TOKEN", None) is not None
try:
    from logfire.integrations.logging import LogfireLoggingHandler
except ModuleNotFoundError:
    logfire_enabled = False

LOGGER = logging.getLogger(__name__)


def _is_on_tty() -> bool:
    return (hasattr(sys.stdout, "isatty") and sys.stdout.isatty()) or const.ENVIRON_FORCE_TTY in os.environ


def python_log_level_to_name(python_log_level: int) -> str:
    """Convert a python log level to a human readable version that works in log config files"""
    # we build the reverse mapping every time because
    # we don't want to use private fields
    # name_to_level = logging._levelToName
    # the underlying assumption is that this code is not performance critical
    name_to_level = logging.getLevelNamesMapping()
    level_to_name = {v: k for k, v in name_to_level.items()}

    result = level_to_name.get(python_log_level)
    if result is not None:
        return result
    return str(python_log_level)


def python_log_level_to_int(level: int | str) -> int:
    # From python logging framework _checkLevel, copied to not use their private methods

    name_to_level = logging.getLevelNamesMapping()
    if isinstance(level, int):
        rv = level
    elif str(level) == level:
        if level not in name_to_level:
            raise ValueError("Unknown level: %r" % level)
        rv = name_to_level[level]
    else:
        raise TypeError("Level not an integer or a valid string: %r" % (level,))
    return rv


"""
This dictionary maps the Inmanta log levels to the corresponding Python log levels
"""
log_levels = {
    "0": logging.ERROR,
    "1": logging.WARNING,
    "2": logging.INFO,
    "3": logging.DEBUG,
    "4": 3,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "TRACE": 3,
}

logging.addLevelName(3, "TRACE")


class LogConfigDumper(Dumper):
    """
    The representer config is class level

    If we don't subclass, we re-configure the every yaml serializer for the entire process

    To prevent this, we subclass"""

    def encode_streams(self, data: object) -> Node:
        if data == sys.stdout:
            return self.represent_data("ext://sys.stdout")
        if data == sys.stderr:
            return self.represent_data("ext://sys.stderr")
        raise Exception(f"Can not encode stream {data}")


LogConfigDumper.add_representer(TextIOWrapper, LogConfigDumper.encode_streams)


@stable_api
class LoggingConfigExtension:
    """
    This class is used by an extension to declare the default logging config that should be used when
    no dict-based logging config was provided by the user. The FullLoggingConfig class provides support
    to merge this logging config into the main logging config of inmanta-core. This class supports only
    version 1 of Python's dictConfig format.
    """

    def __init__(
        self,
        *,
        formatters: Optional[abc.Mapping[str, object]] = None,
        handlers: Optional[abc.Mapping[str, object]] = None,
        loggers: Optional[abc.Mapping[str, object]] = None,
        root_handlers: Optional[list[str]] = None,
        log_dirs_to_create: Optional[abc.Set[str]] = None,
    ) -> None:
        """
        :param log_dirs_to_create: The log directories that should be created before the logging config can be used.
        """
        self.formatters = formatters if formatters else {}
        self.handlers = handlers if handlers else {}
        self.loggers = loggers if loggers else {}
        self.root_handlers = root_handlers if root_handlers else []
        self.log_dirs_to_create = log_dirs_to_create if log_dirs_to_create else set()

    def ensure_log_dirs(self) -> None:
        """
        This method makes sure that the log directories, required by this logging config, are present on disk.
        The directories are created if they don't exist yet.
        """
        for directory in self.log_dirs_to_create:
            os.makedirs(directory, exist_ok=True)


class FullLoggingConfig(LoggingConfigExtension):
    """
    A FullLoggingConfig that can be applied on Python's logging framework.

    This class supports only version 1 of Python's dictConfig format.
    """

    def __init__(
        self,
        *,
        formatters: Optional[abc.Mapping[str, object]] = None,
        handlers: Optional[abc.Mapping[str, object]] = None,
        loggers: Optional[abc.Mapping[str, object]] = None,
        root_handlers: Optional[list[str]] = None,
        log_dirs_to_create: Optional[abc.Set[str]] = None,
        root_log_level: Optional[int | str] = None,
    ):
        super().__init__(
            formatters=formatters,
            handlers=handlers,
            loggers=loggers,
            root_handlers=root_handlers,
            log_dirs_to_create=log_dirs_to_create,
        )
        self.root_log_level = root_log_level

    def join(self, logging_config_extension: LoggingConfigExtension, allow_overwrite: bool = False) -> "FullLoggingConfig":
        """
        Join this FullLoggingConfig and the given LoggingConfigExtension together into a single
        FullLoggingConfig object that contains all the logging config of both objects.
        """

        def warn_or_raise(component: str, names: set[str]) -> None:
            if not allow_overwrite:
                raise Exception(f"The following {component} names appear in multiple logging configs: {names}")
            else:
                logging.warning(
                    "The following %s names appear in multiple logging configs: %s", component, common_formatter_names
                )

        common_formatter_names = set(self.formatters.keys()) & set(logging_config_extension.formatters.keys())
        if common_formatter_names:
            warn_or_raise("formatter", common_formatter_names)
        common_handler_names = set(self.handlers.keys()) & set(logging_config_extension.handlers.keys())
        if common_handler_names:
            warn_or_raise("handler", common_handler_names)
        common_logger_names = set(self.loggers.keys()) & set(logging_config_extension.loggers.keys())
        if common_logger_names:
            warn_or_raise("logger", common_logger_names)

        def update_join(one_dict: Mapping[str, object], two_dict: Mapping[str, object]) -> dict[str, object]:
            out = dict(**one_dict)
            out.update(two_dict)
            return out

        root_level = self.root_log_level
        if isinstance(logging_config_extension, FullLoggingConfig):
            if logging_config_extension.root_log_level is not None:
                if root_level is None:
                    # base config has no root level?
                    root_level = logging_config_extension.root_log_level
                else:
                    # take lowest
                    root_level_int_one = python_log_level_to_int(root_level)
                    root_level_int_other = python_log_level_to_int(logging_config_extension.root_log_level)
                    root_level = python_log_level_to_name(min(root_level_int_one, root_level_int_other))

        return FullLoggingConfig(
            formatters=update_join(self.formatters, logging_config_extension.formatters),
            handlers=update_join(self.handlers, logging_config_extension.handlers),
            loggers=update_join(self.loggers, logging_config_extension.loggers),
            root_handlers=sorted(self.root_handlers + logging_config_extension.root_handlers),
            log_dirs_to_create=self.log_dirs_to_create | logging_config_extension.log_dirs_to_create,
            root_log_level=root_level,
        )

    def apply_config(self) -> None:
        """
        Configure the logging system with this logging config.
        """
        self.ensure_log_dirs()
        dict_config = self._to_dict_config()
        logging.config.dictConfig(dict_config)

    def _to_dict_config(self) -> dict[str, object]:
        """
        Convert this object into a dictionary format that can be passed to logging.config.dictConfig() method
        to configure logging.
        """
        return {
            "version": 1,
            "formatters": dict(self.formatters),
            "handlers": dict(self.handlers),
            "loggers": dict(self.loggers),
            "root": {
                "handlers": self.root_handlers,
                **({"level": self.root_log_level} if self.root_log_level else {}),
            },
            "disable_existing_loggers": False,
        }

    def to_string(self) -> str:
        return yaml.dump(self._to_dict_config(), Dumper=LogConfigDumper)


class Options(Namespace):
    """
    The Options class provides a way to configure the InmantaLoggerConfig with the following attributes:

    :param log_file: if this attribute is set, the logs will be written to the specified file instead of the stream
                     specified in `get_instance`.
    :param log_file_level: the Inmanta logging level for the file handler (if `log_file` is set).
                           The possible inmanta log levels and their associated python log level are defined in the
                           inmanta.logging.log_levels dictionary.
    :param verbose: the verbosity level of the log messages. can be a number from 0 to 4.
                    if a bigger number is provided, 4 will be used. Refer to log_file_level for the explanation of each level.
                    default is 1 (WARNING)
    :param timed: if true,  adds the time to the formatter in the log lines.
    :param logging_config: Path to the dict-based logging config file.
    """

    log_file: Optional[str] = None
    log_file_level: str = "INFO"
    verbose: int = 1
    timed: bool = False
    keep_logger_names: bool = False
    logging_config: Optional[str] = None


class LoggingConfigBuilder:
    def get_bootstrap_logging_config(
        self,
        stream: TextIO = sys.stdout,
        python_log_level: int = logging.INFO,
    ) -> FullLoggingConfig:
        """
        This method returns the logging config that should be used between the moment that the process starts,
        and the moment that the logging-related config options are parsed and applied.

        :param stream: The TextIO stream where the logs will be sent to.
        :param python_log_level: python log level to configure for the bootstrap logger
        """
        name_root_handler = "core_console_handler"
        log_level_name = python_log_level_to_name(python_log_level)
        logging_config_core = FullLoggingConfig(
            formatters={
                "core_console_formatter": self._get_multiline_formatter_config(True),
            },
            handlers={
                name_root_handler: {
                    "class": "logging.StreamHandler",
                    "formatter": "core_console_formatter",
                    "level": log_level_name,
                    "stream": stream,
                },
            },
            loggers={},
            root_handlers=[name_root_handler],
            root_log_level=log_level_name,
        )
        return logging_config_core

    def get_logging_config_from_options(
        self,
        stream: TextIO,
        options: Options,
        component: str | None,
        context: Mapping[str, str],
    ) -> FullLoggingConfig:
        """
        Return the logging config based on the given configuration options, passed on the CLI,
        and the configuration options present in the config file.

        :param stream: The TextIO stream where the logs will be sent to.
        :param options: The config options passed on the CLI.
        :param component: component we are starting
        :param context: the component context we are starting with
        """
        handlers: dict[str, object] = {}
        loggers: dict[str, object] = {}
        handler_root_logger: str
        log_level: int

        log_file_cli_option = options.log_file

        short_names = False
        if component == "compiler":
            short_names = not options.keep_logger_names

        elif component == "scheduler":
            # Override defaults
            if LOG_CONTEXT_VAR_ENVIRONMENT not in context:
                raise Exception("The scheduler expects an environment as context")

            env = context.get(LOG_CONTEXT_VAR_ENVIRONMENT)

            # use setting as formerly passed by the autostarted agent manager if not set via CLI
            if not log_file_cli_option:
                log_file_cli_option = os.path.join(config.log_dir.get(), f"agent-{env}.log")

            # We don't override log-file-level as we can't detect if it is set

        # Shared config
        if log_file_cli_option:
            log_level = convert_inmanta_log_level(options.log_file_level)
            handler_root_logger = f"{component}_handler" if component is not None else "root_handler"
            handlers[handler_root_logger] = {
                "class": "logging.handlers.WatchedFileHandler",
                "level": python_log_level_to_name(log_level),
                "formatter": "core_log_formatter",
                "filename": log_file_cli_option,
                "mode": "a+",
            }
        else:
            log_level = convert_inmanta_log_level(inmanta_log_level=str(options.verbose), cli=True)
            handler_root_logger = "core_console_handler"
            handlers[handler_root_logger] = {
                "class": "logging.StreamHandler",
                "formatter": "core_console_formatter",
                "level": python_log_level_to_name(log_level),
                "stream": stream,
            }

        formatters = {
            # Always add all the formatters, even if they are not used by configuration. This way
            # the formatters can be used if the user dumps the default logging config to file.
            "core_console_formatter": self._get_multiline_formatter_config(not short_names, options),
            "core_log_formatter": {
                "format": "%(asctime)s %(levelname)-8s %(name)-10s %(message)s",
            },
        }

        handlers.update(
            {
                "core_tornado_debug_log_handler": {
                    "class": "inmanta.logging.TornadoDebugLogHandler",
                    "level": "DEBUG",
                },
            }
        )

        loggers.update(
            {
                "tornado.general": {
                    "level": "DEBUG",
                    "propagate": True,
                    "handlers": ["core_tornado_debug_log_handler"],
                }
            }
        )

        if component == "server":
            # Fully generic
            pass
        elif component == "scheduler":
            # Resource action log
            handlers.update(
                {
                    "scheduler_resource_action_handler": {
                        "class": "logging.handlers.WatchedFileHandler",
                        "level": "DEBUG",
                        "formatter": "core_log_formatter",
                        "filename": os.path.join(
                            config.log_dir.get(),
                            server_config.server_resource_action_log_prefix.get()
                            + f"{context.get(LOG_CONTEXT_VAR_ENVIRONMENT)}.log",
                        ),
                    },
                }
            )
            loggers.update(
                {
                    NAME_RESOURCE_ACTION_LOGGER: {
                        "level": "DEBUG",
                        "propagate": True,
                        "handlers": ["scheduler_resource_action_handler"],
                    },
                }
            )

        full_logging_config = FullLoggingConfig(
            formatters=formatters,
            handlers=handlers,
            loggers=loggers,
            root_handlers=[handler_root_logger],
            root_log_level=python_log_level_to_name(log_level),
        )
        return full_logging_config

    def _get_multiline_formatter_config(self, keep_logger_names: bool, options: Optional[Options] = None) -> dict[str, object]:
        """
        Returns the dict-based formatter config for logs that will be sent to the console.

        :param options: The config options requested by the user or None if the config options are not parsed yet and
                        the bootstrap_logger_config should be used.
        """

        # Use a shorter space padding if we know that we will use short names as the logger name.
        # Otherwise the log records contains too much white spaces.
        space_padding_after_logger_name = 25 if (keep_logger_names) else 15
        log_format = "%(asctime)s " if options and options.timed else ""
        if _is_on_tty():
            log_format += f"%(log_color)s%(name)-{space_padding_after_logger_name}s%(levelname)-8s%(reset)s%(blue)s%(message)s"
            log_colors = {"DEBUG": "cyan", "INFO": "green", "WARNING": "yellow", "ERROR": "red", "CRITICAL": "red"}
        else:
            log_format += f"%(name)-{space_padding_after_logger_name}s%(levelname)-8s%(message)s"
            log_colors = None

        return {
            "()": "inmanta.logging.MultiLineFormatter",
            "fmt": log_format,
            "log_colors": log_colors,
            "reset": _is_on_tty(),
            "no_color": not _is_on_tty(),
            "keep_logger_names": keep_logger_names,
        }


def convert_inmanta_log_level(inmanta_log_level: str, cli: bool = False) -> int:
    """
    Convert the given Inmanta log level to the corresponding Python log level.

    :param inmanta_log_level: The inmanta logging level
    :param cli: True if the logs will be outputted to the CLI.
    :return: python log level
    """
    # maximum of 4 v's
    if inmanta_log_level.isdigit() and int(inmanta_log_level) > 4:
        inmanta_log_level = "4"
    # The minimal log level on the CLI is always WARNING
    if cli and (inmanta_log_level == "ERROR" or (inmanta_log_level.isdigit() and int(inmanta_log_level) < 1)):
        inmanta_log_level = "WARNING"
    # Converts the Inmanta log level to the Python log level
    python_log_level = log_levels[inmanta_log_level]
    return python_log_level


@stable_api
class InmantaLoggerConfig:
    """
    This class is the entry-point for configuring the Python logging framework.

    Usage:
    To use this class, you first need to call the `get_instance`. This method takes a `stream` argument
    that specifies where the log messages should be sent to. If no `stream` is provided,
    the log messages will be sent to standard output.

    You can then call the `apply_options` method to configure the logging options.

    The setup is not done in one step as we want logs for the cmd_parser, which will provide the options needed to configure
    the 'final' logger with `apply_options`.
    """

    _instance: Optional["InmantaLoggerConfig"] = None

    def __init__(self, stream: TextIO = sys.stdout) -> None:
        """
        Set up the logging handler for Inmanta

        :param stream: The TextIO stream where the logs will be sent to.
        """
        log_config: FullLoggingConfig = LoggingConfigBuilder().get_bootstrap_logging_config(stream)
        self._stream = stream
        self._handlers: abc.Sequence[logging.Handler] = self._apply_logging_config(log_config)
        self._options_applied: bool = False
        self._logging_configs_extensions: list[LoggingConfigExtension] = []
        self._loaded_config: FullLoggingConfig | None = None
        if logfire_enabled:
            logging.root.addHandler(LogfireLoggingHandler())

    @classmethod
    def get_current_instance(cls) -> "InmantaLoggerConfig":
        """
        Obtain the InmantaLoggerConfig singleton. This method assumes that an InmantaLoggerConfig was already initialized
        using the `get_instance()` method.
        """
        if not cls._instance:
            raise Exception("InmantaLoggerConfig was not yet initialized. Call get_instance() first.")
        return cls._instance

    @classmethod
    @stable_api
    def get_instance(cls, stream: TextIO = sys.stdout) -> "InmantaLoggerConfig":
        """
        This method should be used to obtain an instance of this class, because this class is a singleton.

        :param stream: The stream to send log messages to. Default is standard output (sys.stdout)
        """
        if cls._instance:
            if not cls._instance._handlers:
                raise Exception("No handlers found.")
            if not isinstance(cls._instance._handlers[0], logging.StreamHandler):
                raise Exception("Instance already exists with a different handler")
            elif isinstance(cls._instance._handlers[0], logging.StreamHandler) and cls._instance._handlers[0].stream != stream:
                raise Exception("Instance already exists with a different stream")
        else:
            cls._instance = cls(stream)
        return cls._instance

    @classmethod
    @stable_api
    def clean_instance(cls, root_handlers_to_remove: Optional[abc.Sequence[logging.Handler]] = None) -> None:
        """
        This method should be used to clean up an instance of this class.

        By default, this method removes and closes all root handlers from the logging framework. If the
        root_handlers_to_remove argument is not None, only the provided root handlers will be removed and closed.
        """
        logging.shutdown()
        cls._instance = None

    def _get_path_to_logging_config_file(self, options: Options, component: str | None = None) -> Optional[str]:
        """
        Returns the path to the logging config file that was configured by the user
        or None if no logging config file was set.

        The configuration options are considered in the following order:
           1. The --logging-config CLI option.
           2. The INMANTA_CONFIG_LOGGING_CONFIG environment variable.
           3. The component specific log config option
           4. The logging_config option in the config files.

        :param options: The configuration options passed on the CLI.
        """
        if options.logging_config:
            return options.logging_config
        if component is not None:
            return component_log_configs[component].get()
        return config.logging_config.get()

    @stable_api
    def apply_options(self, options: Options, component: str | None = None, context: Mapping[str, str] = {}) -> None:
        """
        Apply the logging options to the current handler. A handler should have been created before

        :param options: The Option object coming from the command line. This function uses the following
            attributes: log_file, log_file_level, verbose, timed
        :param component: The component to configure (e.g. server, scheduler, compiler).
        Used to select which config file option to use (logging.component)
        :param context: context variables to use if the config file is a template
        """
        if self._options_applied:
            raise Exception("Options can only be applied once to a handler.")

        logging_config_file: Optional[str] = self._get_path_to_logging_config_file(options, component)
        if logging_config_file:
            self._apply_logging_config_from_file(logging_config_file, context)
            if options.verbose != 0:
                # Force cli as well
                self.force_cli(convert_inmanta_log_level(str(options.verbose), cli=True))
        else:
            self._apply_logging_config_from_options(options, component, context)
        self._options_applied = True

    def force_cli(self, python_log_level: int) -> None:
        """Ensure a cli logger is attached at the given level"""
        config_builder = LoggingConfigBuilder()
        logger_config = config_builder.get_bootstrap_logging_config(python_log_level=python_log_level)
        self.add_extension_config(logger_config)

    def _apply_logging_config_from_file(self, config_file: str, context: Mapping[str, str] = {}) -> None:
        """
        Apply the given logging config file.
        """
        handlers_before = list(logging.root.handlers)
        dict_config = load_config_file_to_dict(config_file, context)
        try:
            logging.config.dictConfig(dict_config)
        except Exception:
            raise Exception(f"Failed to apply the logging config defined in {dict_config}.")
        self._handlers = [handler for handler in logging.root.handlers if handler not in handlers_before]

        def as_dict(inp: dict[str, object], key: str) -> dict[str, object]:
            root = inp.get(key, {})
            if not isinstance(root, dict):
                raise Exception(f"{key} entry should be a dict, got {root}")
            return root

        root = as_dict(dict_config, "root")
        # Build config for later merges
        self._loaded_config = FullLoggingConfig(
            formatters=as_dict(dict_config, "formatters"),
            handlers=as_dict(dict_config, "handlers"),
            loggers=as_dict(dict_config, "loggers"),
            root_handlers=root.get("handlers", []),
            root_log_level=root.get("level", None),
        )

    def _apply_logging_config_from_options(
        self, options: Options, component: str | None = None, context: Mapping[str, str] = {}
    ) -> None:
        """
        Apply the logging configuration as defined by the CLI options when the --logging-config option is not set.
        """
        config_builder = LoggingConfigBuilder()
        logging_config: FullLoggingConfig = config_builder.get_logging_config_from_options(
            self._stream, options, component, context
        )
        self._handlers = self._apply_logging_config(logging_config)

    def _apply_logging_config(self, logging_config: FullLoggingConfig) -> abc.Sequence[logging.Handler]:
        """
        Apply the given logging_config as the current configuration of the logging system.

        This method assume that the given config defines a single root handler.
        """
        handlers_before = list(logging.root.handlers)
        logging_config.apply_config()
        self._loaded_config = logging_config
        return [handler for handler in logging.root.handlers if handler not in handlers_before]

    @stable_api
    def set_log_level(self, inmanta_log_level: str, cli: bool = True) -> None:
        """
        [DEPRECATED] Set the logging level. A handler should have been created before.
        The possible inmanta log levels and their associated python log level
        are defined in the inmanta.logging.log_levels dictionary.

        :param inmanta_log_level: The inmanta logging level
        :param cli: True if the logs will be outputted to the CLI.
        """
        # ToDO: remove?
        python_log_level = convert_inmanta_log_level(inmanta_log_level, cli)
        for handler in self._handlers:
            handler.setLevel(python_log_level)
        logging.root.setLevel(python_log_level)

    @stable_api
    def set_log_formatter(self, formatter: logging.Formatter) -> None:
        """
        [DEPRECATED] Set the log formatter. A handler should have been created before

        :param formatter: The log formatter.
        """
        # ToDO: remove?
        for handler in self._handlers:
            handler.setFormatter(formatter)

    @stable_api
    def set_logfile_location(self, location: str) -> None:
        """
        [DEPRECATED] Set the location of the log file. Be careful that this function will replace the current handler
        with a new one. This means that configurations done on the previous handler will be lost.

        :param location: The location of the log file.
        """
        # ToDO: remove?
        file_handler = logging.handlers.WatchedFileHandler(filename=location, mode="a+")
        for handler in self._handlers:
            handler.close()
            logging.root.removeHandler(handler)
        self._handlers = [file_handler]
        logging.root.addHandler(file_handler)

    @stable_api
    def get_handler(self) -> logging.Handler:
        """
        [DEPRECATED] Get the logging handler

        :return: The logging handler
        """
        # ToDO: remove?
        if not self._handlers:
            raise Exception("No handlers found.")
        return self._handlers[0]

    @stable_api
    def add_extension_config(self, logging_config: LoggingConfigExtension) -> None:
        """
        Register the default logging config for a certain extension.
        """
        assert self._loaded_config is not None
        complete_config = self._loaded_config.join(logging_config, allow_overwrite=True)
        self._apply_logging_config(complete_config)


class MultiLineFormatter(colorlog.ColoredFormatter):
    """
    Formatter for multi-line log records.

    This class extends the `colorlog.ColoredFormatter` class to provide a custom formatting method for log records that
    span multiple lines.
    """

    inmanta_plugin_pkg_regex = re.compile(r"^inmanta_plugins\.(?P<module_name>[^.]+)")
    # Regex that extracts the name of the module from a fully qualified import of a Python
    # module inside an Inmanta module.

    def __init__(
        self,
        fmt: Optional[str] = None,
        *,
        # keep interface minimal: only include fields we actually use
        log_colors: Optional[LogColors] = None,
        reset: bool = True,
        no_color: bool = False,
        keep_logger_names: bool = True,
    ):
        """
        Initialize a new `MultiLineFormatter` instance.

        :param fmt: Optional string specifying the log record format.
        :param log_colors: Optional `LogColors` object mapping log level names to color codes.
        :param reset: Boolean indicating whether to reset terminal colors at the end of each log record.
        :param no_color: Boolean indicating whether to disable colors in the output.
        :param keep_logger_names: Display the log messages using the name of the logger that created the log message,
                                  instead of the component of the compiler that was executing while the log record was created
                                  or the name of the module that created the log message.
        """
        super().__init__(fmt, log_colors=log_colors, reset=reset, no_color=no_color)
        self.fmt = fmt
        self._keep_logger_names = keep_logger_names

    def get_header_length(self, record: logging.LogRecord) -> int:
        """
        Get the header length of a given log record.

        :param record: The `logging.LogRecord` object for which to calculate the header length.
        :return: The length of the header in the log record, without color codes.
        """
        # to get the length of the header we want to get the header without the color codes
        formatter = colorlog.ColoredFormatter(
            fmt=self.fmt,
            log_colors=self.log_colors,
            reset=False,
            no_color=True,
        )
        header = formatter.format(
            logging.LogRecord(
                record.name,
                record.levelno,
                record.pathname,
                record.lineno,
                "",
                (),
                None,
            )
        )
        return len(header)

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record with added indentation.

        :param record: The `logging.LogRecord` object to format.
        :return: The formatted log record as a string.
        """
        if not self._keep_logger_names:
            record = self._wrap_record(record)
        indent: str = " " * self.get_header_length(record)
        head, *tail = super().format(record).splitlines(True)
        return head + "".join(indent + line for line in tail)

    def _rename_logger(self, record: logging.LogRecord) -> logging.LogRecord:
        """
        Rename the logger for the given log record. This only affects logs generated by
        the inmanta app. This is both used to display shorter names and to group records generated
        by different modules under a common name.
        """
        old_name = record.name
        new_name = self._get_logger_name_for(old_name)
        if old_name == new_name:
            return record
        attributes = dict(record.__dict__)
        attributes["name"] = new_name
        return logging.makeLogRecord(attributes)

    def _get_logger_name_for(self, logger_name: str) -> str:
        """
        Returns the logger name that should be used in the log record.

        :attr logger_name: The name of the logger that was used to create the log record.
        """
        if not logger_name.startswith("inmanta"):
            # This is a log record from a third-party library. Don't adjust the logger name.
            return logger_name
        if logger_name == "inmanta.pip":
            # Log record created by a pip subprocess started by the inmanta.
            return "pip"
        match: Optional[re.Match[str]] = self.inmanta_plugin_pkg_regex.match(logger_name)
        if match:
            # Log record created by an Inmanta module.
            return match.groupdict()["module_name"]
        elif "export" in logger_name:
            return "exporter"
        elif "protocol" in logger_name:
            return "exporter"
        else:
            # Log record created by Inmanta code.
            return "compiler"


@stable_api
class ParametrizedFileHandler(logging.Handler):
    """
    A file handler that writes to different files based on the last part of the logger name.
    """

    def __init__(self, name_parent_logger: str, log_file_template: str) -> None:
        """
        :param name_parent_logger: The log records created by children of this logger will be written to file by this handler.
                                   This handler will ignore log records created by any other logger.
        :param log_file_template: A template for the path to the log file. This is an f-string that holds the parameter
                                  `child_logger_name`. This part will be replaced by the name of the direct child of
                                  self.name_parent_logger that belongs to the logger that created the record.
        """
        super().__init__()
        self.name_parent_logger = name_parent_logger
        self.log_file_template: str = log_file_template
        self.child_handlers: dict[str, handlers.WatchedFileHandler] = {}

    def flush(self) -> None:
        for child in self.child_handlers.values():
            child.flush()

    def setFormatter(self, fmt: Optional[logging.Formatter]) -> None:
        super().setFormatter(fmt)
        for child in self.child_handlers.values():
            child.setFormatter(fmt)

    def setLevel(self, level: str | int) -> None:
        super().setLevel(level)
        for child in self.child_handlers.values():
            child.setLevel(level)

    def close(self) -> None:
        for child in self.child_handlers.values():
            child.close()
        self.child_handlers = {}
        super().close()

    def emit(self, record: logging.LogRecord) -> None:
        if not record.name.startswith(f"{self.name_parent_logger}."):
            return
        logger_name_without_parent_prefix = record.name.removeprefix(f"{self.name_parent_logger}.")
        logger_name_direct_child_of_parent_logger = logger_name_without_parent_prefix.split(".")[0]
        path_logfile = self.log_file_template.format(child_logger_name=logger_name_direct_child_of_parent_logger)
        if path_logfile not in self.child_handlers:
            try:
                handler = logging.handlers.WatchedFileHandler(filename=path_logfile, mode="a+")
            except FileNotFoundError:
                log_dir = os.path.dirname(self.log_file_template)
                if not os.path.exists(log_dir):
                    LOGGER.warning(
                        "Cannot write to resource action log, because directory %s doesn't exist.",
                        path_logfile,
                    )
                else:
                    LOGGER.exception("Failed to write to resource action log file.")
                return
            handler.setFormatter(self.formatter)
            handler.setLevel(self.level)
            self.child_handlers[path_logfile] = handler
        self.child_handlers[path_logfile].emit(record)


class TornadoDebugLogHandler(logging.Handler):
    """
    A custom log handler for Tornados 'max_clients limit reached' debug logs.
    """

    def __init__(self, level: int = logging.NOTSET) -> None:
        super().__init__(level)
        self.logger = logging.getLogger("inmanta.protocol.endpoints")

    def emit(self, record: logging.LogRecord) -> None:
        if (
            record.levelno == logging.DEBUG
            and record.name.startswith("tornado.general")
            and record.msg.startswith("max_clients limit reached")
        ):
            self.logger.warning(record.msg)  # Log Tornado log as inmanta warnings


def load_config_file_to_dict(file_name: str, context: Mapping[str, str]) -> dict[str, object]:
    # will raise os error if something is wrong
    with open(file_name, "r") as fh:
        content = fh.read()

    if file_name.endswith(".tmpl"):
        try:
            content = content.format(**context)
        except KeyError as e:
            all_keys = ", ".join(context.keys())
            # Not very good exception
            raise Exception(
                f"The configuration template at {file_name} refers to context variable {str(e)}, "
                f"but this variable is not available. The context is limited to {all_keys}"
            )

    dict_config = yaml.safe_load(content)

    return dict_config
