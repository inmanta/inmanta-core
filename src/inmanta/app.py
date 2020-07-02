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
import json
import logging
import os
import signal
import socket
import sys
import threading
import time
import traceback
from argparse import ArgumentParser
from asyncio import ensure_future
from configparser import ConfigParser
from threading import Timer
from typing import Any, Callable, Coroutine

import colorlog
import yaml
from tornado import gen
from tornado.ioloop import IOLoop
from tornado.util import TimeoutError

import inmanta.compiler as compiler
from inmanta import const, module, moduletool, protocol
from inmanta.ast import CompilerException
from inmanta.command import CLIException, Commander, ShowUsageException, command
from inmanta.compiler import do_compile
from inmanta.config import Config
from inmanta.const import EXIT_START_FAILED
from inmanta.export import ModelExporter, cfg_env
from inmanta.server.bootloader import InmantaBootloader
from inmanta.util import get_compiler_version
from inmanta.warnings import WarningsManager

LOGGER = logging.getLogger("inmanta")


@command("server", help_msg="Start the inmanta server")
def start_server(options: argparse.Namespace) -> None:
    if options.config_file and not os.path.exists(options.config_file):
        LOGGER.warning("Config file %s doesn't exist", options.config_file)

    if options.config_dir and not os.path.isdir(options.config_dir):
        LOGGER.warning("Config directory %s doesn't exist", options.config_dir)

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
    from inmanta import agent

    a = agent.Agent()
    setup_signal_handlers(a.stop)
    IOLoop.current().add_callback(a.start)
    IOLoop.current().start()
    LOGGER.info("Agent Shutdown complete")


def dump_threads() -> None:
    print("----- Thread Dump ----")
    for th in threading.enumerate():
        print("---", th)
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

    def handle_signal(signum, frame):
        # force shutdown, even when the ioloop is stuck
        # schedule off the loop
        t = Timer(const.SHUTDOWN_GRACE_HARD, hard_exit)
        t.daemon = True
        t.start()
        ioloop.add_callback_from_signal(safe_shutdown_wrapper, shutdown_function)

    def handle_signal_dump(signum, frame):
        context_dump(ioloop)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGUSR1, handle_signal_dump)


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


def compiler_config(parser: ArgumentParser) -> None:
    """
        Configure the compiler of the export function
    """
    parser.add_argument("-e", dest="environment", help="The environment to compile this model for")
    parser.add_argument(
        "-X",
        "--extended-errors",
        dest="errors_subcommand",
        help="Show stack traces for compile errors",
        action="store_true",
        default=False,
    )
    parser.add_argument("--server_address", dest="server", help="The address of the server hosting the environment")
    parser.add_argument("--server_port", dest="port", help="The port of the server hosting the environment")
    parser.add_argument("--username", dest="user", help="The username of the server")
    parser.add_argument("--password", dest="password", help="The password of the server")
    parser.add_argument("--ssl", help="Enable SSL", action="store_true", default=False)
    parser.add_argument("--ssl-ca-cert", dest="ca_cert", help="Certificate authority for SSL")
    parser.add_argument(
        "--json",
        dest="compile_json",
        help="Export structured json containing compile data such as occurred errors.",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--json-file",
        dest="compile_json_file",
        help="File to export compile json to. If omitted %s is used." % compiler.config.default_json_file,
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


@command(
    "compile", help_msg="Compile the project to a configuration model", parser_config=compiler_config, require_project=True
)
def compile_project(options: argparse.Namespace):
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

    if options.compile_json is True:
        Config.set("compiler", "json", "true")

    if options.compile_json_file is not None:
        Config.set("compiler", "json_file", options.compile_json_file)

    if options.datatrace is True:
        Config.set("compiler", "datatrace_enable", "true")

    if options.dataflow_graphic is True:
        Config.set("compiler", "dataflow_graphic_enable", "true")

    module.Project.get(options.main_file)

    if options.profile:
        import cProfile
        import pstats

        result = cProfile.runctx("do_compile()", globals(), {}, "run.profile")
        p = pstats.Stats("run.profile")
        p.strip_dirs().sort_stats("time").print_stats(20)
    else:
        t1 = time.time()
        result = do_compile()
        LOGGER.debug("Compile time: %0.03f seconds", time.time() - t1)
    return result


@command("list-commands", help_msg="Print out an overview of all commands")
def list_commands(options: argparse.Namespace) -> None:
    print("The following commands are available:")
    for cmd, info in Commander.commands().items():
        print(" %s: %s" % (cmd, info["help"]))


def help_parser_config(parser: ArgumentParser) -> None:
    parser.add_argument("subcommand", help="Output help for a particular subcommand", nargs="?", default=None)


@command("help", help_msg="show a help message and exit", parser_config=help_parser_config)
def help_command(options: argparse.Namespace):
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


def deploy_parser_config(parser: ArgumentParser) -> None:
    parser.add_argument("--dry-run", help="Only report changes", action="store_true", dest="dryrun")
    parser.add_argument("-f", dest="main_file", help="Main file", default="main.cf")
    parser.add_argument(
        "--dashboard",
        dest="dashboard",
        help="Start the dashboard and keep the server running. "
        "The server uses the current project as the source for server recompiles",
        action="store_true",
        default=False,
    )


@command("deploy", help_msg="Deploy with a inmanta all-in-one setup", parser_config=deploy_parser_config, require_project=True)
def deploy(options: argparse.Namespace) -> None:
    module.Project.get(options.main_file)
    from inmanta import deploy

    run = deploy.Deploy(options)
    try:
        if not run.setup():
            LOGGER.error("Failed to setup the orchestrator.")
            return
        run.run()
    finally:
        run.stop()


def export_parser_config(parser: ArgumentParser) -> None:
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
    parser.add_argument("--ssl", help="Enable SSL", action="store_true", default=False)
    parser.add_argument("--ssl-ca-cert", dest="ca_cert", help="Certificate authority for SSL")
    parser.add_argument(
        "-X",
        "--extended-errors",
        dest="errors_subcommand",
        help="Show stack traces for compile errors",
        action="store_true",
        default=False,
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


@command("export", help_msg="Export the configuration", parser_config=export_parser_config, require_project=True)
def export(options: argparse.Namespace) -> None:
    if options.environment is not None:
        Config.set("config", "environment", options.environment)

    if options.server is not None:
        Config.set("compiler_rest_transport", "host", options.server)

    if options.server is not None:
        Config.set("compiler_rest_transport", "port", options.port)

    if options.token is not None:
        Config.set("compiler_rest_transport", "token", options.token)

    if options.ssl:
        Config.set("compiler_rest_transport", "ssl", "true")

    if options.ca_cert is not None:
        Config.set("compiler_rest_transport", "ssl-ca-cert-file", options.ca_cert)

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

    module.Project.get(options.main_file)

    from inmanta.export import Exporter  # noqa: H307

    exp = None
    try:
        (types, scopes) = do_compile()
    except Exception as e:
        exp = e
        types, scopes = (None, None)

    # Even if the compile failed we might have collected additional data such as unknowns. So
    # continue the export

    export = Exporter(options)
    version, _ = export.run(
        types, scopes, metadata=metadata, model_export=options.model_export, export_plugin=options.export_plugin
    )

    if exp is not None:
        raise exp

    if options.model:
        modelexporter = ModelExporter(types)
        with open("testdump.json", "w", encoding="utf-8") as fh:
            print(yaml.dump(modelexporter.export_all()))
            json.dump(modelexporter.export_all(), fh)

    if options.deploy:
        conn = protocol.SyncClient("compiler")
        LOGGER.info("Triggering deploy for version %d" % version)
        tid = cfg_env.get()
        agent_trigger_method = const.AgentTriggerMethod.get_agent_trigger_method(options.full_deploy)
        conn.release_version(tid, version, True, agent_trigger_method)


log_levels = {0: logging.ERROR, 1: logging.WARNING, 2: logging.INFO, 3: logging.DEBUG, 4: 2}


def cmd_parser() -> ArgumentParser:
    # create the argument compiler
    parser = ArgumentParser()
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
        default=2,
        type=int,
        help="Log level for messages going to the logfile: 0=ERROR, 1=WARNING, 2=INFO, 3=DEBUG",
    )
    parser.add_argument("--timed-logs", dest="timed", help="Add timestamps to logs", action="store_true")
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Log level for messages going to the console. Default is only errors,"
        "-v warning, -vv info and -vvv debug and -vvvv trace",
    )
    parser.add_argument(
        "--warnings",
        dest="warnings",
        choices=["warn", "ignore", "error"],
        default="warn",
        help="The warning behaviour of the compiler. Must be one of 'warn', 'ignore', 'error'",
    )
    parser.add_argument(
        "-X", "--extended-errors", dest="errors", help="Show stack traces for errors", action="store_true", default=False
    )
    parser.add_argument(
        "--version", action="store_true", dest="version", help="Show current version of Inmanta", default=False, required=False
    )
    subparsers = parser.add_subparsers(title="commands")
    for cmd_name, cmd_options in Commander.commands().items():
        cmd_subparser = subparsers.add_parser(cmd_name, help=cmd_options["help"], aliases=cmd_options["aliases"])
        if cmd_options["parser_config"] is not None:
            cmd_options["parser_config"](cmd_subparser)
        cmd_subparser.set_defaults(func=cmd_options["function"])
        cmd_subparser.set_defaults(require_project=cmd_options["require_project"])

    return parser


def get_current_version_and_exit():
    print(f"Current Inmanta version: {get_compiler_version()}")
    sys.exit(0)


def _is_on_tty() -> bool:
    return (hasattr(sys.stdout, "isatty") and sys.stdout.isatty()) or const.ENVIRON_FORCE_TTY in os.environ


def _get_default_stream_handler() -> logging.StreamHandler:
    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setLevel(logging.INFO)

    formatter = _get_log_formatter_for_stream_handler(timed=False)
    stream_handler.setFormatter(formatter)

    return stream_handler


def _get_watched_file_handler(options) -> logging.handlers.WatchedFileHandler:
    if not options.log_file:
        raise Exception("No logfile was provided.")
    level = _convert_to_log_level(options.log_file_level)
    formatter = logging.Formatter(fmt="%(asctime)s %(levelname)-8s %(name)-10s %(message)s")
    file_handler = logging.handlers.WatchedFileHandler(filename=options.log_file, mode="a+")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    return file_handler


def _convert_to_log_level(level):
    if level >= len(log_levels):
        level = len(log_levels) - 1
    return log_levels[level]


def _get_log_formatter_for_stream_handler(timed: bool) -> logging.Formatter:
    log_format = "%(asctime)s " if timed else ""
    if _is_on_tty():
        log_format += "%(log_color)s%(name)-25s%(levelname)-8s%(reset)s %(blue)s%(message)s"
        formatter = colorlog.ColoredFormatter(
            log_format,
            datefmt=None,
            reset=True,
            log_colors={"DEBUG": "cyan", "INFO": "green", "WARNING": "yellow", "ERROR": "red", "CRITICAL": "red"},
        )
    else:
        log_format += "%(name)-25s%(levelname)-8s%(message)s"
        formatter = logging.Formatter(fmt=log_format)
    return formatter


def app() -> None:
    """
        Run the compiler
    """
    # Send logs to stdout
    stream_handler = _get_default_stream_handler()
    logging.root.handlers = []
    logging.root.addHandler(stream_handler)
    logging.root.setLevel(0)

    # do an initial load of known config files to build the libdir path
    Config.load_config()
    parser = cmd_parser()
    options, other = parser.parse_known_args()
    options.other = other

    if options.version:
        get_current_version_and_exit()

    # Log everything to a log_file if logfile is provided
    if options.log_file:
        watched_file_handler = _get_watched_file_handler(options)
        logging.root.addHandler(watched_file_handler)
        logging.root.removeHandler(stream_handler)
    else:
        if options.timed:
            formatter = _get_log_formatter_for_stream_handler(timed=True)
            stream_handler.setFormatter(formatter)
        log_level = _convert_to_log_level(options.verbose)
        stream_handler.setLevel(log_level)

    logging.captureWarnings(True)

    if options.config_file and not os.path.exists(options.config_file):
        LOGGER.warning("Config file %s doesn't exist", options.config_file)

    # Load the configuration
    Config.load_config(options.config_file, options.config_dir)

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

    def report(e: Exception) -> None:
        minus_x_set_top_level_command = options.errors
        minus_x_set_subcommand = hasattr(options, "errors_subcommand") and options.errors_subcommand
        if not minus_x_set_top_level_command and not minus_x_set_subcommand:
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
