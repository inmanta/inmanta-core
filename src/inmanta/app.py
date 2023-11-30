"""
    Copyright 2017 Inmanta

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


    Command line development guidelines
    ###################################

    do's and don'ts
    ----------------
    MUST NOT: sys.exit => use command.CLIException
    SHOULD NOT: print( => use logger for messages, only print for final output


    Entry points
    ------------
    @command annotation to register new command
"""
import argparse
import asyncio
import contextlib
import dataclasses
import enum
import json
import logging
import os
import shutil
import signal
import socket
import sys
import threading
import time
import traceback
from argparse import ArgumentParser
from asyncio import ensure_future
from collections import abc
from collections.abc import Coroutine
from configparser import ConfigParser
from threading import Timer
from types import FrameType
from typing import Any, Callable, Optional

import click
from tornado import gen
from tornado.httpclient import AsyncHTTPClient
from tornado.ioloop import IOLoop
from tornado.util import TimeoutError

import inmanta.compiler as compiler
from inmanta import const, module, moduletool, protocol, util
from inmanta.ast import CompilerException, Namespace
from inmanta.ast import type as inmanta_type
from inmanta.command import CLIException, Commander, ShowUsageException, command
from inmanta.compiler import do_compile
from inmanta.config import Config, Option
from inmanta.const import EXIT_START_FAILED
from inmanta.export import cfg_env
from inmanta.logging import InmantaLoggerConfig, LoggerMode, _is_on_tty
from inmanta.server.bootloader import InmantaBootloader
from inmanta.util import get_compiler_version
from inmanta.warnings import WarningsManager

try:
    import rpdb
except ImportError:
    rpdb = None

LOGGER = logging.getLogger("inmanta")


@command("server", help_msg="Start the inmanta server")
def start_server(options: argparse.Namespace) -> None:
    if options.config_file and not os.path.exists(options.config_file):
        LOGGER.warning("Config file %s doesn't exist", options.config_file)

    if options.config_dir and not os.path.isdir(options.config_dir):
        LOGGER.warning("Config directory %s doesn't exist", options.config_dir)

    util.ensure_event_loop()

    ibl = InmantaBootloader()
    setup_signal_handlers(ibl.stop)

    ioloop = IOLoop.current()

    # handle startup exceptions
    def _handle_startup_done(fut: asyncio.Future) -> None:
        if fut.cancelled():
            safe_shutdown(ioloop, ibl.stop)
        else:
            exc = fut.exception()
            if exc is not None:
                LOGGER.exception("Server setup failed", exc_info=exc)
                traceback.print_exception(type(exc), exc, exc.__traceback__)
                safe_shutdown(ioloop, ibl.stop)
            else:
                LOGGER.info("Server startup complete")

    ensure_future(ibl.start()).add_done_callback(_handle_startup_done)

    ioloop.start()
    LOGGER.info("Server shutdown complete")
    if not ibl.started:
        exit(EXIT_START_FAILED)


@command("agent", help_msg="Start the inmanta agent")
def start_agent(options: argparse.Namespace) -> None:
    from inmanta.agent import agent

    # The call to configure() should be done as soon as possible.
    # If an AsyncHTTPClient is started before this call, the max_client
    # will not be taken into account.
    max_clients: Optional[int] = Config.get("agent_rest_transport", "max_clients", None)
    if max_clients:
        AsyncHTTPClient.configure(None, max_clients=max_clients)

    util.ensure_event_loop()
    a = agent.Agent()

    setup_signal_handlers(a.stop)
    IOLoop.current().add_callback(a.start)
    IOLoop.current().start()
    LOGGER.info("Agent Shutdown complete")


def dump_threads() -> None:
    print("----- Thread Dump ----")
    for th in threading.enumerate():
        print("---", th)
        if th.ident:
            traceback.print_stack(sys._current_frames()[th.ident], file=sys.stdout)
        print()
    sys.stdout.flush()


async def dump_ioloop_running() -> None:
    # dump async IO
    print("----- Async IO tasks ----")
    for task in asyncio.all_tasks():
        print(task)
    print()
    sys.stdout.flush()


def context_dump(ioloop: IOLoop) -> None:
    dump_threads()
    if hasattr(asyncio, "all_tasks"):
        ioloop.add_callback_from_signal(dump_ioloop_running)


def setup_signal_handlers(shutdown_function: Callable[[], Coroutine[Any, Any, None]]) -> None:
    """
    Make sure that shutdown_function is called when a SIGTERM or a SIGINT interrupt occurs.

    :param shutdown_function: The function that contains the shutdown logic.
    """
    # ensure correct ioloop
    ioloop = IOLoop.current()

    def hard_exit() -> None:
        context_dump(ioloop)
        sys.stdout.flush()
        # Hard exit, not sys.exit
        # ensure shutdown when the ioloop is stuck
        os._exit(const.EXIT_HARD)

    def handle_signal(signum: signal.Signals, frame: Optional[FrameType]) -> None:
        # force shutdown, even when the ioloop is stuck
        # schedule off the loop
        t = Timer(const.SHUTDOWN_GRACE_HARD, hard_exit)
        t.daemon = True
        t.start()
        ioloop.add_callback_from_signal(safe_shutdown_wrapper, shutdown_function)

    def handle_signal_dump(signum: signal.Signals, frame: Optional[FrameType]) -> None:
        context_dump(ioloop)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGUSR1, handle_signal_dump)
    if rpdb:
        rpdb.handle_trap()


def safe_shutdown(ioloop: IOLoop, shutdown_function: Callable[[], None]) -> None:
    def hard_exit() -> None:
        context_dump(ioloop)
        sys.stdout.flush()
        # Hard exit, not sys.exit
        # ensure shutdown when the ioloop is stuck
        os._exit(const.EXIT_HARD)

    # force shutdown, even when the ioloop is stuck
    # schedule off the loop
    t = Timer(const.SHUTDOWN_GRACE_HARD, hard_exit)
    t.daemon = True
    t.start()
    ioloop.add_callback(safe_shutdown_wrapper, shutdown_function)


async def safe_shutdown_wrapper(shutdown_function: Callable[[], Coroutine[Any, Any, None]]) -> None:
    """
    Wait 10 seconds to gracefully shutdown the instance.
    Afterwards stop the IOLoop
    Wait for 3 seconds to force stop
    """
    future = shutdown_function()
    try:
        timeout = IOLoop.current().time() + const.SHUTDOWN_GRACE_IOLOOP
        await gen.with_timeout(timeout, future)
    except TimeoutError:
        pass
    finally:
        IOLoop.current().stop()


class ExperimentalFeatureFlags:
    """
    Class to expose feature flag configs as options in a uniform matter
    """

    def __init__(self) -> None:
        self.metavar_to_option: dict[str, Option[bool]] = {}

    def _get_name(self, option: Option[bool]) -> str:
        return f"flag_{option.name}"

    def add(self, option: Option[bool]) -> None:
        """Add an option to the set of feature flags"""
        self.metavar_to_option[self._get_name(option)] = option

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add all feature flag options to the argument parser"""
        for metavar, option in self.metavar_to_option.items():
            parser.add_argument(
                f"--experimental-{option.name}",
                dest=metavar,
                help=option.documentation,
                action="store_true",
                default=False,
            )

    def read_options_to_config(self, options: argparse.Namespace) -> None:
        """
        This method takes input from the commandline parser
        and sets the appropriate feature flag config based
        on the parsed command line arguments

        :param options: the options, as parsed by argparse.
        """
        for metavar, option in self.metavar_to_option.items():
            value = getattr(options, metavar, False)
            if value:
                option.set("true")


def compiler_config(parser: argparse.ArgumentParser, parent_parsers: abc.Sequence[ArgumentParser]) -> None:
    """
    Configure the compiler of the export function
    """
    parser.add_argument("-e", dest="environment", help="The environment to compile this model for")
    parser.add_argument(
        "-X",
        "--extended-errors",
        dest="errors",
        help="Show stack traces for compile errors",
        action="store_true",
        default=argparse.SUPPRESS,
    )
    parser.add_argument("--server_address", dest="server", help="The address of the server hosting the environment")
    parser.add_argument("--server_port", dest="port", help="The port of the server hosting the environment")
    parser.add_argument("--username", dest="user", help="The username of the server")
    parser.add_argument("--password", dest="password", help="The password of the server")
    parser.add_argument("--ssl", help="Enable SSL", action="store_true", default=False)
    parser.add_argument("--ssl-ca-cert", dest="ca_cert", help="Certificate authority for SSL")
    parser.add_argument(
        "--export-compile-data",
        dest="export_compile_data",
        help="Export structured json containing compile data such as occurred errors.",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--export-compile-data-file",
        dest="export_compile_data_file",
        help="File to export compile data to. If omitted %s is used." % compiler.config.default_compile_data_file,
    )
    parser.add_argument(
        "--no-cache",
        dest="feature_compiler_cache",
        help="Disable caching of compiled CF files",
        action="store_false",
        default=True,
    )
    parser.add_argument(
        "--experimental-data-trace",
        dest="datatrace",
        help="Experimental data trace tool useful for debugging",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--experimental-dataflow-graphic",
        dest="dataflow_graphic",
        help="Experimental graphic data flow visualization",
        action="store_true",
        default=False,
    )

    parser.add_argument("-f", dest="main_file", help="Main file", default="main.cf")
    moduletool.add_deps_check_arguments(parser)


@command(
    "compile", help_msg="Compile the project to a configuration model", parser_config=compiler_config, require_project=True
)
def compile_project(options: argparse.Namespace) -> None:
    inmanta_logger_config = InmantaLoggerConfig.get_current_instance()
    with inmanta_logger_config.run_in_logger_mode(LoggerMode.COMPILER):
        if options.environment is not None:
            Config.set("config", "environment", options.environment)

        if options.server is not None:
            Config.set("compiler_rest_transport", "host", options.server)

        if options.port is not None:
            Config.set("compiler_rest_transport", "port", options.port)

        if options.user is not None:
            Config.set("compiler_rest_transport", "username", options.user)

        if options.password is not None:
            Config.set("compiler_rest_transport", "password", options.password)

        if options.ssl:
            Config.set("compiler_rest_transport", "ssl", "true")

        if options.ca_cert is not None:
            Config.set("compiler_rest_transport", "ssl-ca-cert-file", options.ca_cert)

        if options.export_compile_data is True:
            Config.set("compiler", "export_compile_data", "true")

        if options.export_compile_data_file is not None:
            Config.set("compiler", "export_compile_data_file", options.export_compile_data_file)

        if options.feature_compiler_cache is False:
            Config.set("compiler", "cache", "false")

        if options.datatrace is True:
            Config.set("compiler", "datatrace_enable", "true")

        if options.dataflow_graphic is True:
            Config.set("compiler", "dataflow_graphic_enable", "true")

        strict_deps_check = moduletool.get_strict_deps_check(
            no_strict_deps_check=options.no_strict_deps_check, strict_deps_check=options.strict_deps_check
        )
        module.Project.get(options.main_file, strict_deps_check=strict_deps_check)

        summary_reporter = CompileSummaryReporter()
        if options.profile:
            import cProfile
            import pstats

            with summary_reporter.compiler_exception.capture():
                cProfile.runctx("do_compile()", globals(), {}, "run.profile")
            p = pstats.Stats("run.profile")
            p.strip_dirs().sort_stats("time").print_stats(20)
        else:
            t1 = time.time()
            with summary_reporter.compiler_exception.capture():
                do_compile()
            LOGGER.debug("The entire compile command took %0.03f seconds", time.time() - t1)

        summary_reporter.print_summary_and_exit(show_stack_traces=options.errors)


@command("list-commands", help_msg="Print out an overview of all commands", add_verbose_flag=False)
def list_commands(options: argparse.Namespace) -> None:
    print("The following commands are available:")
    for cmd, info in Commander.commands().items():
        print(" {}: {}".format(cmd, info["help"]))


def help_parser_config(parser: argparse.ArgumentParser, parent_parsers: abc.Sequence[ArgumentParser]) -> None:
    parser.add_argument("subcommand", help="Output help for a particular subcommand", nargs="?", default=None)


@command("help", help_msg="show a help message and exit", parser_config=help_parser_config, add_verbose_flag=False)
def help_command(options: argparse.Namespace) -> None:
    if options.subcommand is None:
        cmd_parser().print_help()
    else:
        subc = options.subcommand
        parser = cmd_parser()
        parser.parse_args([subc, "-h"])
    sys.exit(0)


@command(
    "modules",
    help_msg="Subcommand to manage modules",
    parser_config=moduletool.ModuleTool.modules_parser_config,
    aliases=["module"],
)
def modules(options: argparse.Namespace) -> None:
    tool = moduletool.ModuleTool()
    tool.execute(options.cmd, options)


@command("project", help_msg="Subcommand to manage the project", parser_config=moduletool.ProjectTool.parser_config)
def project(options: argparse.Namespace) -> None:
    tool = moduletool.ProjectTool()
    tool.execute(options.cmd, options)


def deploy_parser_config(parser: argparse.ArgumentParser, parent_parsers: abc.Sequence[ArgumentParser]) -> None:
    parser.add_argument("--dry-run", help="Only report changes", action="store_true", dest="dryrun")
    parser.add_argument("-f", dest="main_file", help="Main file", default="main.cf")


@command("deploy", help_msg="Deploy with a inmanta all-in-one setup", parser_config=deploy_parser_config, require_project=True)
def deploy(options: argparse.Namespace) -> None:
    module.Project.get(options.main_file)
    from inmanta import deploy as deploy_module

    run = deploy_module.Deploy(options)
    try:
        if not run.setup():
            raise Exception("Failed to setup an embedded Inmanta orchestrator.")
        run.run()
    finally:
        run.stop()


def export_parser_config(parser: argparse.ArgumentParser, parent_parsers: abc.Sequence[ArgumentParser]) -> None:
    """
    Configure the compiler of the export function
    """
    parser.add_argument("-g", dest="depgraph", help="Dump the dependency graph", action="store_true")
    parser.add_argument(
        "-j",
        dest="json",
        help="Do not submit to the server but only store the json that would have been " "submitted in the supplied file",
    )
    parser.add_argument("-e", dest="environment", help="The environment to compile this model for")
    parser.add_argument("-d", dest="deploy", help="Trigger a deploy for the exported version", action="store_true")
    parser.add_argument(
        "--full",
        dest="full_deploy",
        help="Make the agents execute a full deploy instead of an incremental deploy. "
        "Should be used together with the -d option",
        action="store_true",
        default=False,
    )
    parser.add_argument("-m", dest="model", help="Also export the complete model", action="store_true", default=False)
    parser.add_argument("--server_address", dest="server", help="The address of the server to submit the model to")
    parser.add_argument("--server_port", dest="port", help="The port of the server to submit the model to")
    parser.add_argument("--token", dest="token", help="The token to auth to the server")
    parser.add_argument("--ssl", help="Enable SSL", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--ssl-ca-cert", dest="ca_cert", help="Certificate authority for SSL")
    parser.add_argument(
        "-X",
        "--extended-errors",
        dest="errors",
        help="Show stack traces for compile errors",
        action="store_true",
        default=argparse.SUPPRESS,
    )
    parser.add_argument("-f", dest="main_file", help="Main file", default="main.cf")
    parser.add_argument(
        "--metadata",
        dest="metadata",
        help="JSON metadata why this compile happened. If a non-json string is "
        "passed it is used as the 'message' attribute in the metadata.",
        default=None,
    )
    parser.add_argument(
        "--model-export",
        dest="model_export",
        help="Export the configuration model to the server as metadata.",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--export-plugin",
        dest="export_plugin",
        help="Only use this export plugin. This option also disables the execution of the plugins listed in "
        "the configuration file in the export setting.",
        default=None,
    )

    parser.add_argument(
        "--export-compile-data",
        dest="export_compile_data",
        help="Export structured json containing compile data such as occurred errors.",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--export-compile-data-file",
        dest="export_compile_data_file",
        help="File to export compile data to. If omitted %s is used." % compiler.config.default_compile_data_file,
    )
    parser.add_argument(
        "--no-cache",
        dest="feature_compiler_cache",
        help="Disable caching of compiled CF files",
        action="store_false",
        default=True,
    )
    parser.add_argument(
        "--partial",
        dest="partial_compile",
        help=(
            "Execute a partial export. Does not upload new Python code to the server: it is assumed to be unchanged since the"
            " last full export. Multiple partial exports for disjunct resource sets may be performed concurrently but not"
            " concurrent with a full export. When used in combination with the `--json` option, 0 is used as a placeholder for"
            " the model version."
        ),
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--delete-resource-set",
        dest="delete_resource_set",
        help="Remove a resource set as part of a partial compile. This option can be provided multiple times and should always "
        "be used together with the --partial option.",
        action="append",
    )
    moduletool.add_deps_check_arguments(parser)


@command("export", help_msg="Export the configuration", parser_config=export_parser_config, require_project=True)
def export(options: argparse.Namespace) -> None:
    inmanta_logger_config = InmantaLoggerConfig.get_current_instance()
    with inmanta_logger_config.run_in_logger_mode(LoggerMode.COMPILER):
        if not options.partial_compile and options.delete_resource_set:
            raise CLIException(
                "The --delete-resource-set option should always be used together with the --partial option", exitcode=1
            )
        if options.environment is not None:
            Config.set("config", "environment", options.environment)

        if options.server is not None:
            Config.set("compiler_rest_transport", "host", options.server)

        if options.port is not None:
            Config.set("compiler_rest_transport", "port", options.port)

        if options.token is not None:
            Config.set("compiler_rest_transport", "token", options.token)

        if options.ssl is not None:
            Config.set("compiler_rest_transport", "ssl", f"{options.ssl}".lower())

        if options.ca_cert is not None:
            Config.set("compiler_rest_transport", "ssl-ca-cert-file", options.ca_cert)

        if options.export_compile_data is True:
            Config.set("compiler", "export_compile_data", "true")

        if options.export_compile_data_file is not None:
            Config.set("compiler", "export_compile_data_file", options.export_compile_data_file)

        if options.feature_compiler_cache is False:
            Config.set("compiler", "cache", "false")

        # try to parse the metadata as json. If a normal string, create json for it.
        if options.metadata is not None and len(options.metadata) > 0:
            try:
                metadata = json.loads(options.metadata)
            except json.decoder.JSONDecodeError:
                metadata = {"message": options.metadata}
        else:
            metadata = {"message": "Manual compile on the CLI by user"}

        if "cli-user" not in metadata and "USERNAME" in os.environ:
            metadata["cli-user"] = os.environ["USERNAME"]

        if "hostname" not in metadata:
            metadata["hostname"] = socket.gethostname()

        if "type" not in metadata:
            metadata["type"] = "manual"

        strict_deps_check = moduletool.get_strict_deps_check(
            no_strict_deps_check=options.no_strict_deps_check, strict_deps_check=options.strict_deps_check
        )
        module.Project.get(options.main_file, strict_deps_check=strict_deps_check)

        from inmanta.export import Exporter  # noqa: H307

        summary_reporter = CompileSummaryReporter()

        types: Optional[dict[str, inmanta_type.Type]]
        scopes: Optional[Namespace]

        t1 = time.time()
        with summary_reporter.compiler_exception.capture():
            try:
                (types, scopes) = do_compile()
            except Exception:
                types, scopes = (None, None)
                raise

    with inmanta_logger_config.run_in_logger_mode(LoggerMode.EXPORTER):
        # Even if the compile failed we might have collected additional data such as unknowns. So
        # continue the export

        export = Exporter(options)
        with summary_reporter.exporter_exception.capture():
            results = export.run(
                types,
                scopes,
                metadata=metadata,
                model_export=options.model_export,
                export_plugin=options.export_plugin,
                partial_compile=options.partial_compile,
                resource_sets_to_remove=options.delete_resource_set,
            )

        if not summary_reporter.is_failure() and options.deploy:
            version = results[0]
            conn = protocol.SyncClient("compiler")
            LOGGER.info("Triggering deploy for version %d" % version)
            tid = cfg_env.get()
            agent_trigger_method = const.AgentTriggerMethod.get_agent_trigger_method(options.full_deploy)
            conn.release_version(tid, version, True, agent_trigger_method)

        LOGGER.debug("The entire export command took %0.03f seconds", time.time() - t1)
        summary_reporter.print_summary_and_exit(show_stack_traces=options.errors)


class Color(enum.Enum):
    RED = "red"
    GREEN = "green"


@dataclasses.dataclass
class ExceptionCollector:
    """
    This class defines a context manager that captures any unhandled exception raised within the context.
    """

    exception: Optional[Exception] = None

    def has_exception(self) -> bool:
        return self.exception is not None

    @contextlib.contextmanager
    def capture(self) -> abc.Iterator["ExceptionCollector"]:
        """
        Record any exceptions raised within the context manager. The exception will not be re-raised.
        """
        try:
            yield self
        except Exception as e:
            self.exception = e


class CompileSummaryReporter:
    """
    Contains the logic to print a summary at the end of the `inmanta compile` or `inmanta export`
    command that provides an overview on whether the command was successful or not.
    """

    def __init__(self) -> None:
        self.compiler_exception: ExceptionCollector = ExceptionCollector()
        self.exporter_exception: ExceptionCollector = ExceptionCollector()

    def is_failure(self) -> bool:
        """
        Return true iff an exception has occurred during the compile or export stage.
        """
        return self.compiler_exception.has_exception() or self.exporter_exception.has_exception()

    def _get_global_status(self) -> str:
        """
        Return the global status of the run.
        """
        if self.compiler_exception.has_exception():
            return "COMPILATION FAILURE"
        elif self.exporter_exception.has_exception():
            return "EXPORT FAILURE"
        else:
            return "SUCCESS"

    def _get_header(self, header_text: str) -> str:
        """
        Return a header for the summary with the given header_text.
        """
        terminal_width = shutil.get_terminal_size()[0]
        minimal_header = f"= {header_text.upper()} ="
        length_minimal_header = len(minimal_header)
        if terminal_width <= length_minimal_header:
            return minimal_header
        else:
            nr_equals_signs_to_add_each_side = int((terminal_width - length_minimal_header) / 2)
            extra_equals_signs_each_side = "=" * nr_equals_signs_to_add_each_side
            return f"{extra_equals_signs_each_side}{minimal_header}{extra_equals_signs_each_side}"

    def _get_exception_to_report(self) -> Exception:
        """
        Return the exception that should be reported in the summary. Compiler exceptions take precedence
        over exporter exceptions because they happen first.
        """
        assert self.is_failure()
        if self.compiler_exception.has_exception():
            assert self.compiler_exception.exception is not None
            return self.compiler_exception.exception
        else:
            assert self.exporter_exception.exception is not None
            return self.exporter_exception.exception

    def _get_error_message(self) -> str:
        """
        Return the error message associated with `self._get_exception_to_report()`.
        """
        exc = self._get_exception_to_report()
        if isinstance(exc, CompilerException):
            error_message = exc.format_trace(indent="  ").strip("\n")
            # Add explainer text if any
            from inmanta.compiler.help.explainer import ExplainerFactory

            helpmsg = ExplainerFactory().explain_and_format(exc, plain=not _is_on_tty())
            if helpmsg is not None:
                helpmsg = helpmsg.strip("\n")
                return f"{error_message}\n\n{helpmsg}"
        else:
            error_message = str(exc).strip("\n")
        return f"Error: {error_message}"

    def _get_stack_trace(self) -> str:
        """
        Return the stack trace associated with `self._get_exception_to_report()`.
        """
        exc = self._get_exception_to_report()
        return "".join(traceback.format_exception(None, value=exc, tb=exc.__traceback__)).strip("\n")

    def _print_to_stderr(self, text: str = "", bold: bool = False, **kwargs: object) -> None:
        """
        Prints the given text to stderr with the given styling requirements. On a tty the text
        is printed in green in case of success and in red in case of a failure.
        """
        if _is_on_tty():
            color = Color.RED if self.is_failure() else Color.GREEN
            text = click.style(text, fg=color.value, bold=bold)
        print(text, file=sys.stderr, **kwargs)

    def print_summary(self, show_stack_traces: bool) -> None:
        """
        Print the summary of the compile run.
        """
        self._print_to_stderr()
        if show_stack_traces and self.is_failure():
            self._print_to_stderr(text=self._get_header(header_text="EXCEPTION TRACE"))
            self._print_to_stderr(text=self._get_stack_trace(), end="\n\n")

        self._print_to_stderr(text=self._get_header(header_text=self._get_global_status()))
        if self.is_failure():
            self._print_to_stderr(text=self._get_error_message())

    def print_summary_and_exit(self, show_stack_traces: bool) -> None:
        """
        Print the compile summary and exit with a 0 status code in case of success or 1 in case of failure.
        """
        self.print_summary(show_stack_traces)
        exit(1 if self.is_failure() else 0)


def cmd_parser() -> argparse.ArgumentParser:
    # create the argument compiler

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", action="store_true", dest="profile", help="Profile this run of the program")
    parser.add_argument("-c", "--config", dest="config_file", help="Use this config file", default=None)
    parser.add_argument(
        "--config-dir",
        dest="config_dir",
        help="The directory containing the Inmanta configuration files",
        default="/etc/inmanta/inmanta.d",
    )
    parser.add_argument("--log-file", dest="log_file", help="Path to the logfile")
    parser.add_argument(
        "--log-file-level",
        dest="log_file_level",
        choices=["0", "1", "2", "3", "4", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE"],
        default="INFO",
        help="Log level for messages going to the logfile: 0=ERROR, 1=WARNING, 2=INFO, 3=DEBUG",
    )
    parser.add_argument("--timed-logs", dest="timed", help="Add timestamps to logs", action="store_true")
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Log level for messages going to the console. Default is warnings,"
        "-v warning, -vv info, -vvv debug and -vvvv trace",
    )
    parser.add_argument(
        "--warnings",
        dest="warnings",
        choices=["warn", "ignore", "error"],
        default="warn",
        help="The warning behaviour. Must be one of 'warn', 'ignore', 'error'",
    )
    parser.add_argument(
        "-X", "--extended-errors", dest="errors", help="Show stack traces for errors", action="store_true", default=False
    )
    parser.add_argument(
        "--version",
        action="store_true",
        dest="inmanta_version",
        help="Show the version of the installed Inmanta product and the version of its subcomponents",
        default=False,
        required=False,
    )
    parser.add_argument(
        "--keep-logger-names",
        dest="keep_logger_names",
        help="Display the log messages using the name of the logger that created the log messages.",
        action="store_true",
        default=False,
    )

    verbosity_parser = argparse.ArgumentParser(add_help=False)
    verbosity_parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=argparse.SUPPRESS,
        help="Log level for messages going to the console. Default is warnings,"
        "-v warning, -vv info, -vvv debug and -vvvv trace",
    )

    subparsers = parser.add_subparsers(title="commands")
    for cmd_name, cmd_options in Commander.commands().items():
        parent_parsers: list[argparse.ArgumentParser] = []
        if cmd_options["add_verbose_flag"]:
            parent_parsers.append(verbosity_parser)
        cmd_subparser = subparsers.add_parser(
            cmd_name, help=cmd_options["help"], aliases=cmd_options["aliases"], parents=parent_parsers
        )
        if cmd_options["parser_config"] is not None:
            cmd_options["parser_config"](cmd_subparser, parent_parsers)
        cmd_subparser.set_defaults(func=cmd_options["function"])
        cmd_subparser.set_defaults(require_project=cmd_options["require_project"])

    return parser


def print_versions_installed_components_and_exit() -> None:
    # coroutine to make sure event loop is running for server slices
    async def print_status() -> None:
        bootloader = InmantaBootloader()
        app_context = bootloader.load_slices()
        product_metadata = app_context.get_product_metadata()
        extension_statuses = app_context.get_extension_statuses()

        if product_metadata.version:
            print(f"{product_metadata.product} ({product_metadata.edition}): {product_metadata.version}")
        else:
            print(f"{product_metadata.product} ({product_metadata.edition}): version unknown")
        print(f"Compiler version: {get_compiler_version()}")
        if extension_statuses:
            print("Extensions:")
            for ext_status in extension_statuses:
                print(f"    * {ext_status.name}: {ext_status.version}")
        else:
            print("Extensions: No extensions found")

        await bootloader.stop()

    asyncio.run(print_status())
    sys.exit(0)


def app() -> None:
    """
    Run the compiler
    """
    log_config = InmantaLoggerConfig.get_instance()

    # do an initial load of known config files to build the libdir path
    Config.load_config()
    parser = cmd_parser()
    options, other = parser.parse_known_args()
    options.other = other

    log_config.apply_options(options)

    logging.captureWarnings(True)

    if options.config_file and not os.path.exists(options.config_file):
        LOGGER.warning("Config file %s doesn't exist", options.config_file)

    # Load the configuration
    Config.load_config(options.config_file, options.config_dir)

    if options.inmanta_version:
        print_versions_installed_components_and_exit()

    if options.warnings is not None:
        Config.set("warnings", "default", options.warnings)

    config = Config.get()
    assert isinstance(config, ConfigParser)
    WarningsManager.apply_config(config["warnings"] if "warnings" in config else None)

    # start the command
    if not hasattr(options, "func"):
        # show help
        parser.print_usage()
        return

    def report(e: BaseException) -> None:
        if not options.errors:
            if isinstance(e, CompilerException):
                print(e.format_trace(indent="  "), file=sys.stderr)
            else:
                print(str(e), file=sys.stderr)
        else:
            sys.excepthook(*sys.exc_info())

        if isinstance(e, CompilerException):
            from inmanta.compiler.help.explainer import ExplainerFactory

            helpmsg = ExplainerFactory().explain_and_format(e, plain=not _is_on_tty())
            if helpmsg is not None:
                print(helpmsg)

    try:
        options.func(options)
    except ShowUsageException as e:
        print(e.args[0], file=sys.stderr)
        parser.print_usage()
    except CLIException as e:
        report(e)
        sys.exit(e.exitcode)
    except Exception as e:
        report(e)
        sys.exit(1)
    except KeyboardInterrupt as e:
        report(e)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    app()
