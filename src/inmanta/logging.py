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

import enum
import logging
import logging.config
import os
import re
import sys
from argparse import Namespace
from collections import abc
from collections.abc import Iterator
from contextlib import contextmanager
from logging import handlers
from typing import Optional, TextIO

import colorlog
from colorlog.formatter import LogColors

from inmanta import config, const
from inmanta.server import config as server_config
from inmanta.stable_api import stable_api

LOGGER = logging.getLogger(__name__)


def _is_on_tty() -> bool:
    return (hasattr(sys.stdout, "isatty") and sys.stdout.isatty()) or const.ENVIRON_FORCE_TTY in os.environ


"""
This dictionary maps the Inmanta log levels to the corresponding Python log levels
"""
log_levels = {
    "0": logging.ERROR,
    "1": logging.WARNING,
    "2": logging.INFO,
    "3": logging.DEBUG,
    "4": 2,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "TRACE": 2,
}


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
        root_handlers: Optional[abc.Set[str]] = None,
        log_dirs_to_create: Optional[abc.Set[str]] = None,
    ) -> None:
        """
        :param log_dirs_to_create: The log directories that should be created before the logging config can be used.
        """
        self.formatters = formatters if formatters else {}
        self.handlers = handlers if handlers else {}
        self.loggers = loggers if loggers else {}
        self.root_handlers = root_handlers if root_handlers else set()
        self.log_dirs_to_create = log_dirs_to_create if log_dirs_to_create else set()

    def ensure_log_dirs(self) -> None:
        """
        This method makes sure that the log directories, required by this logging config, are present on disk.
        The directories are created if they don't exist yet.
        """
        for directory in self.log_dirs_to_create:
            os.makedirs(directory, exist_ok=True)

    def validate_for_extension(self, extension_name: str) -> None:
        """
        Verify that the names of the formatters and handlers are prefixed with `<name-extension>_` and
        raise an Exception in case this constraint is violated.
        """
        for logging_config_element in ["formatters", "handlers"]:
            for name in getattr(self, logging_config_element):
                if not name.startswith(f"{extension_name}_"):
                    raise Exception(
                        f"{logging_config_element.capitalize()} defined in the default logging config of an extension must be"
                        f" prefixed with `{extension_name}_`. Extension {extension_name} defines a"
                        f" {logging_config_element[0:-1]} with the invalid name {name}."
                    )


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
        root_handlers: Optional[abc.Set[str]] = None,
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

    def join(self, logging_config_extension: LoggingConfigExtension) -> "FullLoggingConfig":
        """
        Join this FullLoggingConfig and the given LoggingConfigExtension together into a single
        FullLoggingConfig object that contains all the logging config of both objects.
        """
        common_formatter_names = set(self.formatters.keys()) & set(logging_config_extension.formatters.keys())
        if common_formatter_names:
            raise Exception(f"The following formatter names appear in multiple logging configs: {common_formatter_names}")
        common_handler_names = set(self.handlers.keys()) & set(logging_config_extension.handlers.keys())
        if common_handler_names:
            raise Exception(f"The following handler names appear in multiple logging configs: {common_handler_names}")
        common_logger_names = set(self.loggers.keys()) & set(logging_config_extension.loggers.keys())
        if common_logger_names:
            raise Exception(f"The following logger names appear in multiple logging configs: {common_logger_names}")
        return FullLoggingConfig(
            formatters=dict(**self.formatters, **logging_config_extension.formatters),
            handlers=dict(**self.handlers, **logging_config_extension.handlers),
            loggers=dict(**self.loggers, **logging_config_extension.loggers),
            root_handlers=set(*self.root_handlers, *logging_config_extension.root_handlers),
            log_dirs_to_create=set(*self.log_dirs_to_create, *logging_config_extension.log_dirs_to_create),
            root_log_level=self.root_log_level,
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
    """

    log_file: Optional[str] = None
    log_file_level: str = "INFO"
    verbose: int = 1
    timed: bool = False
    keep_logger_names: bool = False


class LoggerMode(enum.Enum):
    """
    A different log format is used when the compiler/exporter is executed. This enum
    indicates which mode we are currently executing in.
        * COMPILER: the compiler is running.
        * EXPORT: The exporter is running.
        * OTHER: We are executing neither the compiler nor the exporter (e.g. running the server).
    """

    COMPILER = "compiler"
    EXPORTER = "exporter"
    OTHER = "other"


class LoggingConfigBuilder:
    def get_bootstrap_logging_config(
        self,
        stream: TextIO = sys.stdout,
        logging_config_extensions: Optional[abc.Sequence[LoggingConfigExtension]] = None,
    ) -> FullLoggingConfig:
        """
        This method returns the logging config that should be used between the moment that the process starts,
        and the moment that the logging-related config options are parsed and applied.

        :param stream: The TextIO stream where the logs will be sent to.
        :param logging_config_extensions: The logging config required by the extensions.
        """
        name_root_handler = "core_console_handler"
        logging_config_core = FullLoggingConfig(
            formatters={
                "core_console_formatter": self._get_multiline_formatter_config(),
            },
            handlers={
                name_root_handler: {
                    "class": "logging.StreamHandler",
                    "formatter": "core_console_formatter",
                    "level": "INFO",
                    "stream": stream,
                },
            },
            loggers={},
            root_handlers={name_root_handler},
            root_log_level="INFO",
        )
        logging_config_core.validate_for_extension(extension_name="core")
        return self._join_logging_configs(logging_config_core, logging_config_extensions)

    def get_logging_config_from_options(
        self,
        stream: TextIO,
        options: Options,
        logging_config_extensions: Optional[abc.Sequence[LoggingConfigExtension]] = None,
    ) -> FullLoggingConfig:
        """
        Return the logging config based on the given configuration options, passed on the CLI,
        and the configuration options present in the config file.

        :param stream: The TextIO stream where the logs will be sent to.
        :param options: The config options passed on the CLI.
        :param logging_config_extensions: The logging config required by the extensions.
        """
        handlers: dict[str, object] = {}
        handler_root_logger: str
        log_level: int
        if options.log_file:
            log_level = convert_inmanta_log_level(options.log_file_level)
            handler_root_logger = "core_server_log"
            handlers[handler_root_logger] = {
                "class": "logging.handlers.WatchedFileHandler",
                "level": log_level,
                "formatter": "core_server_log_formatter",
                "filename": options.log_file,
                "mode": "a+",
            }
        else:
            log_level = convert_inmanta_log_level(inmanta_log_level=str(options.verbose), cli=True)
            handler_root_logger = "core_console"
            handlers[handler_root_logger] = {
                "class": "logging.StreamHandler",
                "formatter": "core_console_formatter",
                "level": log_level,
                "stream": stream,
            }

        full_logging_config = FullLoggingConfig(
            formatters={
                # Always add all the formatters, even if they are not used by configuration. This way
                # the formatters can be used if the user dumps the default logging config to file.
                "core_resource_action_log_formatter": {
                    "format": "%(asctime)s %(levelname)-8s %(name)-10s %(message)s",
                },
                "core_server_log_formatter": {
                    "format": "%(asctime)s %(levelname)-8s %(name)-10s %(message)s",
                },
                "core_console_formatter": self._get_multiline_formatter_config(options),
            },
            handlers={
                **handlers,
                "core_resource_action_handler": {
                    "class": "inmanta.logging.ParametrizedFileHandler",
                    "level": "DEBUG",
                    "formatter": "core_resource_action_log_formatter",
                    "name_parent_logger": const.NAME_RESOURCE_ACTION_LOGGER,
                    "log_file_template": os.path.join(
                        config.log_dir.get(), server_config.server_resource_action_log_prefix.get() + "{child_logger_name}.log"
                    ),
                },
                "core_tornado_debug_log_handler": {
                    "class": "inmanta.logging.TornadoDebugLogHandler",
                    "level": "DEBUG",
                },
            },
            loggers={
                const.NAME_RESOURCE_ACTION_LOGGER: {
                    "level": "DEBUG",
                    "propagate": True,
                    "handlers": ["core_resource_action_handler"],
                },
                "tornado.general": {
                    "level": "DEBUG",
                    "propagate": True,
                    "handlers": ["core_tornado_debug_log_handler"],
                },
            },
            root_handlers={handler_root_logger},
            root_log_level=log_level,
        )
        full_logging_config.validate_for_extension(extension_name="core")
        return self._join_logging_configs(full_logging_config, logging_config_extensions)

    def get_logging_config_for_agent(self, log_file: str, inmanta_log_level: str, cli_log: bool) -> FullLoggingConfig:
        """
        Returns the logging config for an agent.

        :param log_file: The log file were the logs should be sent to.
        :param inmanta_log_level: The Inmanta log level threshold, that indicates which log records should be ignored
                                  and which should be logged. This log level is taking into account for log records sent
                                  to file and to stderr.
        :param cli_log: A boolean indicating whether logs should also be sent to stderr or not.
        """
        python_log_level: int = convert_inmanta_log_level(inmanta_log_level)
        cli_handlers = {}
        name_root_handler = "core_agent_log_handler"
        root_loggers = {name_root_handler}
        if cli_log:
            cli_handlers["core_console_handler"] = {
                "class": "logging.StreamHandler",
                "formatter": "core_console_formatter",
                "level": python_log_level,
                "stream": "ext://sys.stderr",
            }
            root_loggers.add("core_console_handler")
        full_logging_config = FullLoggingConfig(
            formatters={
                # Always add all the formatters, even if they are not used by configuration. This way
                # the formatters can be used if the user dumps the default logging config to file.
                "core_agent_log_formatter": {
                    "format": "%(asctime)s %(levelname)-8s %(name)-10s %(message)s",
                },
                "core_console_formatter": self._get_multiline_formatter_config(),
            },
            handlers={
                name_root_handler: {
                    "class": "logging.handlers.WatchedFileHandler",
                    "level": python_log_level,
                    "formatter": "core_agent_log_formatter",
                    "filename": log_file,
                    "mode": "a+",
                },
                **cli_handlers,
            },
            loggers={},
            root_handlers=root_loggers,
            root_log_level=python_log_level,
        )
        full_logging_config.validate_for_extension(extension_name="core")
        return full_logging_config

    def _join_logging_configs(
        self,
        full_logger_config: FullLoggingConfig,
        logging_config_extensions: Optional[abc.Sequence[LoggingConfigExtension]] = None,
    ) -> FullLoggingConfig:
        """
        Join the given LoggingConfigCore and the LoggingConfigExtensions together into a single LoggingConfigCore
        object that contains all the loging config.
        """
        logging_config_extensions = logging_config_extensions if logging_config_extensions else []
        result = full_logger_config
        for logging_config_ext in logging_config_extensions:
            result = result.join(logging_config_ext)
        return result

    def _get_multiline_formatter_config(self, options: Optional[Options] = None) -> dict[str, object]:
        """
        Returns the dict-based formatter config for logs that will be sent to the console.

        :param options: The config options requested by the user or None if the config options are not parsed yet and
                        the bootstrap_logger_config should be used.
        """
        # Use a shorter space padding if we know that we will use short names as the logger name.
        # Otherwise the log records contains too much white spaces.
        space_padding_after_logger_name = (
            15
            if (
                options
                and not options.keep_logger_names
                and hasattr(options, "func")
                and options.func.__name__ in ["compile_project", "export"]
            )
            else 25
        )
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
            "keep_logger_names": options.keep_logger_names if options else False,
        }


@stable_api
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


class LoggerModeManager:
    """
    A singleton that keeps track of the current LoggerMode.
    """

    _instance: Optional["LoggerModeManager"] = None

    def __init__(self) -> None:
        self._logger_mode = LoggerMode.OTHER

    def get_logger_mode(self) -> LoggerMode:
        """
        Returns the current logger mode.
        """
        return self._logger_mode

    @contextmanager
    def run_in_logger_mode(self, logger_mode: LoggerMode) -> Iterator[None]:
        """
        A contextmanager that can be used to temporarily change the LoggerMode within a code block.
        This ContextManager updates the LoggerModeManager singleton and is therefore not async- or threadsafe.
        """
        prev_logger_mode = self._logger_mode
        self._logger_mode = logger_mode
        try:
            yield
        finally:
            self._logger_mode = prev_logger_mode

    @classmethod
    def get_instance(cls) -> "LoggerModeManager":
        if cls._instance is None:
            cls._instance = LoggerModeManager()
        return cls._instance


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

    @stable_api
    def apply_options(self, options: Options) -> None:
        """
        Apply the logging options to the current handler. A handler should have been created before

        :param options: The Option object coming from the command line. This function uses the following
            attributes: log_file, log_file_level, verbose, timed
        """
        if self._options_applied:
            raise Exception("Options can only be applied once to a handler.")

        config_builder = LoggingConfigBuilder()
        logging_config: FullLoggingConfig = config_builder.get_logging_config_from_options(
            self._stream, options, self._logging_configs_extensions
        )
        self._handlers = self._apply_logging_config(logging_config)
        self._options_applied = True

    def _apply_logging_config(self, logging_config: FullLoggingConfig) -> abc.Sequence[logging.Handler]:
        """
        Apply the given logging_config as the current configuration of the logging system.

        This method assume that the given config defines a single root handler.
        """
        handlers_before = list(logging.root.handlers)
        logging_config.apply_config()
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
        for handler in self._handlers:
            handler.setFormatter(formatter)

    @stable_api
    def set_logfile_location(self, location: str) -> None:
        """
        [DEPRECATED] Set the location of the log file. Be careful that this function will replace the current handler
        with a new one. This means that configurations done on the previous handler will be lost.

        :param location: The location of the log file.
        """
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
        if not self._handlers:
            raise Exception("No handlers found.")
        return self._handlers[0]

    @stable_api
    def register_default_logging_config(self, logging_config: LoggingConfigExtension) -> None:
        """
        Register the default logging config for a certain extension.
        """
        self._logging_configs_extensions.append(logging_config)


@stable_api
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
        keep_logger_names: bool,
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
        self._logger_mode_manager = LoggerModeManager.get_instance()

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
        record = self._wrap_record(record)
        indent: str = " " * self.get_header_length(record)
        head, *tail = super().format(record).splitlines(True)
        return head + "".join(indent + line for line in tail)

    def _wrap_record(self, record: logging.LogRecord) -> logging.LogRecord:
        """
        Wrap a log record to perform renaming for specific formatter as determined by the _logger_mode

        This is derived from the way the colorlog.ColoredFormatter works
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
        logger_mode = self._logger_mode_manager.get_logger_mode()
        if not self._keep_logger_names and logger_mode in [LoggerMode.COMPILER, LoggerMode.EXPORTER]:
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
            else:
                # Log record created by Inmanta code.
                return logger_mode.value
        else:
            # Don't modify the logger name
            return logger_name


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
