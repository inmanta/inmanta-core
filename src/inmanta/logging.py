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
import os
import sys
from argparse import Namespace
from typing import Optional, TextIO

import colorlog
from colorlog.formatter import LogColors

from inmanta import const
from inmanta.stable_api import stable_api


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


class Options(Namespace):
    """
    The Options class provides a way to configure the InmantaLoggerConfig with the following attributes:
    - `log_file`: if this attribute is set, the logs will be written to the specified file instead of the stream
      specified in `get_instance`.
    - `log_file_level`: the Inmanta logging level for the file handler (if `log_file` is set).
        The possible inmanta log levels and their associated python log level are defined in the
        inmanta.logging.log_levels dictionary.
    - `verbose`: the verbosity level of the log messages. can be a number from 0 to 4.
        if a bigger number is provided, 4 will be used. Refer to log_file_level for the explanation of each level.
        default is 1 (WARNING)
    - `timed`: if true,  adds the time to the formatter in the log lines.
    """

    log_file: Optional[str]
    log_file_level: str = "INFO"
    verbose: int = 1
    timed: bool = False


@stable_api
class InmantaLoggerConfig:
    """
    A class that provides logging functionality for Inmanta projects.

    Usage:
    To use this class, you first need to call the `get_instance`. This method takes a `stream` argument
    that specifies where the log messages should be sent to. If no `stream` is provided,
    the log messages will be sent to standard output.

    You can then call the `apply_options` method to configure the logging options.

    The setup is not done in one step as we want logs for the cmd_parser, which will provide the options needed to configure
    the 'final' logger with `apply_options`.

    for more fine-grained configuration the following functions can be used as well:
        - `set_log_level`
        - `set_log_formatter`
        - `set_logfile_location`
    """

    _instance: Optional["InmantaLoggerConfig"] = None

    def __init__(self, stream: TextIO = sys.stdout) -> None:
        """
        Set up the logging handler for Inmanta

        :param stream: The stream to send log messages to. Default is standard output (sys.stdout).
        """
        self._options_applied = False
        self._handler: logging.Handler = logging.StreamHandler(stream=stream)
        self.set_log_level("INFO")
        formatter = self._get_log_formatter_for_stream_handler(timed=False)
        self.set_log_formatter(formatter)

        logging.root.handlers = []
        logging.root.addHandler(self._handler)
        logging.root.setLevel(0)

    @classmethod
    @stable_api
    def get_instance(cls, stream: TextIO = sys.stdout) -> "InmantaLoggerConfig":
        """
        This method should be used to obtain an instance of this class, because this class is a singleton.

        :param stream: The stream to send log messages to. Default is standard output (sys.stdout)
        """
        if cls._instance:
            if not isinstance(cls._instance._handler, logging.StreamHandler):
                raise Exception("Instance already exists with a different handler")
            elif isinstance(cls._instance._handler, logging.StreamHandler) and cls._instance._handler.stream != stream:
                raise Exception("Instance already exists with a different stream")
        else:
            cls._instance = cls(stream)
        return cls._instance

    @classmethod
    @stable_api
    def clean_instance(cls) -> None:
        """
        This method should be used to clean up an instance of this class

        """
        if cls._instance and cls._instance._handler:
            cls._instance._handler.close()
            logging.root.removeHandler(cls._instance._handler)
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
        self._options_applied = True
        if options.log_file:
            self.set_logfile_location(options.log_file)
            formatter = logging.Formatter(fmt="%(asctime)s %(levelname)-8s %(name)-10s %(message)s")
            self.set_log_formatter(formatter)
            self.set_log_level(options.log_file_level, cli=False)
        else:
            if options.timed:
                formatter = self._get_log_formatter_for_stream_handler(timed=True)
                self.set_log_formatter(formatter)
            self.set_log_level(str(options.verbose))

    @stable_api
    def set_log_level(self, inmanta_log_level: str, cli: bool = True) -> None:
        """
        Set the logging level. A handler should have been created before.
        The possible inmanta log levels and their associated python log level
        are defined in the inmanta.logging.log_levels dictionary.

        :param inmanta_log_level: The inmanta logging level
        :param cli: True if the logs will be outputted to the CLI.
        """
        # maximum of 4 v's
        if inmanta_log_level.isdigit() and int(inmanta_log_level) > 4:
            inmanta_log_level = "4"

        # The minimal log level on the CLI is always WARNING
        if cli and (inmanta_log_level == "ERROR" or (inmanta_log_level.isdigit() and int(inmanta_log_level) < 1)):
            inmanta_log_level = "WARNING"

        # Converts the Inmanta log level to the Python log level
        python_log_level = log_levels[inmanta_log_level]
        self._handler.setLevel(python_log_level)

    @stable_api
    def set_log_formatter(self, formatter: logging.Formatter) -> None:
        """
        Set the log formatter. A handler should have been created before

        :param formatter: The log formatter.
        """
        self._handler.setFormatter(formatter)

    @stable_api
    def set_logfile_location(self, location: str) -> None:
        """
        Set the location of the log file. Be careful that this function will replace the current handler with a new one
        This means that configurations done on the previous handler will be lost.

        :param location: The location of the log file.
        """
        file_handler = logging.handlers.WatchedFileHandler(filename=location, mode="a+")
        if self._handler:
            self._handler.close()
            logging.root.removeHandler(self._handler)
        self._handler = file_handler
        logging.root.addHandler(self._handler)

    @stable_api
    def get_handler(self) -> logging.Handler:
        """
        Get the logging handler

        :return: The logging handler
        """
        return self._handler

    def _get_log_formatter_for_stream_handler(self, timed: bool) -> logging.Formatter:
        log_format = "%(asctime)s " if timed else ""
        if _is_on_tty():
            log_format += "%(log_color)s%(name)-25s%(levelname)-8s%(reset)s%(blue)s%(message)s"
            formatter = MultiLineFormatter(
                log_format,
                reset=True,
                log_colors={"DEBUG": "cyan", "INFO": "green", "WARNING": "yellow", "ERROR": "red", "CRITICAL": "red"},
            )
        else:
            log_format += "%(name)-25s%(levelname)-8s%(message)s"
            formatter = MultiLineFormatter(
                log_format,
                reset=False,
                no_color=True,
            )
        return formatter


class MultiLineFormatter(colorlog.ColoredFormatter):
    """
    Formatter for multi-line log records.

    This class extends the `colorlog.ColoredFormatter` class to provide a custom formatting method for log records that
    span multiple lines.
    """

    def __init__(
        self,
        fmt: Optional[str] = None,
        *,
        # keep interface minimal: only include fields we actually use
        log_colors: Optional[LogColors] = None,
        reset: bool = True,
        no_color: bool = False,
    ):
        """
        Initialize a new `MultiLineFormatter` instance.

        :param fmt: Optional string specifying the log record format.
        :param log_colors: Optional `LogColors` object mapping log level names to color codes.
        :param reset: Boolean indicating whether to reset terminal colors at the end of each log record.
        :param no_color: Boolean indicating whether to disable colors in the output.
        """
        super().__init__(fmt, log_colors=log_colors, reset=reset, no_color=no_color)
        self.fmt = fmt

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
                name=record.name,
                level=record.levelno,
                pathname=record.pathname,
                lineno=record.lineno,
                msg="",
                args=(),
                exc_info=None,
            )
        )
        return len(header)

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record with added indentation.

        :param record: The `logging.LogRecord` object to format.
        :return: The formatted log record as a string.
        """
        indent: str = " " * self.get_header_length(record)
        head, *tail = super().format(record).splitlines(True)
        return head + "".join(indent + line for line in tail)
