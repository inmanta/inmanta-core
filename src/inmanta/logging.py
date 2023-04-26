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
from typing import Optional

import colorlog
from colorlog.formatter import LogColors

from inmanta import const


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


class InmantaLogs:
    """
    A class that provides logging functionality for Inmanta projects.

    Usage:
    To use this class, you first need to call the `setup_handler` method to configure the logging handler. This method
    takes a `stream` argument that specifies where the log messages should be sent to. If no `stream` is provided,
    the log messages will be sent to standard output.

    You can then call the `apply_options` method to configure the logging options. This method takes an `options`
    argument that should be an object with the following attributes:
    - `log_file`: if this attribute is set, the logs will be written to the specified file instead of the stream
      specified in `setup_handler`.
    - `log_file_level`: the logging level for the file handler (if `log_file` is set).
    - `verbose`: the verbosity level of the log messages.
    - 'timed': if true,  adds the time to the formatter in the log lines.

    The setup is not done in one step as we want logs for the cmd_parser, which will provide the options needed to configure
    the 'final' logger with apply_options.
    """

    _handler: Optional[logging.Handler] = None

    @classmethod
    def create_default_handler(cls, stream: Optional[str] = sys.stdout) -> None:
        """
        Set up the logging handler for Inmanta.

        :param stream: The stream to send log messages to. Default is standard output (sys.stdout).
        """
        cls._handler = logging.StreamHandler(stream=stream)
        cls.set_log_level(logging.INFO)
        formatter = cls._get_log_formatter_for_stream_handler(timed=False)
        cls.set_log_formatter(formatter)

        logging.root.handlers = []
        logging.root.addHandler(cls._handler)
        logging.root.setLevel(0)

    @classmethod
    def apply_options(cls, options) -> None:
        """
        Apply the logging options to the current handler. If there is no handler yet, this function starts one
        with setup_handler

        :param options: the option object coming from the command line. This function use the following
            attribute: log_file, log_file_level, verbose, timed
        """
        if options.log_file:
            cls.set_logfile_location(options.log_file)
            formatter = logging.Formatter(fmt="%(asctime)s %(levelname)-8s %(name)-10s %(message)s")
            cls.set_log_formatter(formatter)
            log_level = cls._convert_inmanta_log_level_to_python_log_level(options.log_file_level)
            cls.set_log_level(log_level)
        else:
            if options.timed:
                formatter = InmantaLogs._get_log_formatter_for_stream_handler(timed=True)
                cls.set_log_formatter(formatter)
            log_level = InmantaLogs._convert_cli_log_level(options.verbose)
            cls.set_log_level(log_level)

    @classmethod
    def set_log_level(cls, log_level: int) -> None:
        """
        Set the logging level.

        :param log_level: The logging level.
        """
        cls._handler.setLevel(log_level)

    @classmethod
    def set_log_formatter(cls, formatter: logging.Formatter) -> None:
        """
        Set the log formatter.

        :param formatter: The log formatter.
        """
        cls._handler.setFormatter(formatter)

    @classmethod
    def set_logfile_location(cls, location: str) -> None:
        """
        Set the location of the log file. Be carefull taht this function will replace the current handler with a new one
        This means that configurations done on the previous handler will be lost. It might be a good idea to
        call this function first.

        :param location: The location of the log file.
        """
        file_handler = logging.handlers.WatchedFileHandler(filename=location, mode="a+")
        logging.root.removeHandler(cls._handler)
        cls._handler = file_handler
        logging.root.addHandler(cls._handler)

    @classmethod
    def get_handler(cls) -> logging.Handler:
        """
        Get the logging handler instance used by this class

        :return: The logging handler instance used by this class
        """
        return cls._handler

    @classmethod
    def _convert_cli_log_level(cls, level: int) -> int:
        """
        Converts the number of -v's passed on the CLI to the corresponding Inmanta log level
        """
        if level < 1:
            # The minimal log level on the CLI is always WARNING
            return logging.WARNING
        else:
            return cls._convert_inmanta_log_level_to_python_log_level(str(level))

    @classmethod
    def _convert_inmanta_log_level_to_python_log_level(cls, level: str) -> int:
        """
        Converts the Inmanta log level to the Python log level
        """
        if level.isdigit() and int(level) > 4:
            level = "4"
        return log_levels[level]

    @classmethod
    def _get_log_formatter_for_stream_handler(cls, timed: bool) -> logging.Formatter:
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
    """Multi-line formatter."""

    def __init__(
        self,
        fmt: Optional[str] = None,
        *,
        # keep interface minimal: only include fields we actually use
        log_colors: Optional[LogColors] = None,
        reset: bool = True,
        no_color: bool = False,
    ):
        super().__init__(fmt, log_colors=log_colors, reset=reset, no_color=no_color)
        self.fmt = fmt

    def get_header_length(self, record: logging.LogRecord) -> int:
        """Get the header length of a given record."""
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
        """Format a record with added indentation."""
        indent: str = " " * self.get_header_length(record)
        head, *tail = super().format(record).splitlines(True)
        return head + "".join(indent + line for line in tail)
