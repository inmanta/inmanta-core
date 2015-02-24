"""
    Copyright 2015 Impera

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Contact: bart@impera.io
"""

from argparse import ArgumentParser
import logging
import sys

import colorlog
from impera.command import command, Commander
from impera.compiler import do_compile
from impera.config import Config
from impera.module import ModuleTool, Project, ProjectNotFoundExcpetion
from impera.stats import Stats

LOGGER = logging.getLogger()


@command("server", help_msg="Start the impera server")
def start_server(options):
    from impera import server
    s = server.Server()
    s.start()


@command("agent", help_msg="Start the impera agent")
def start_agent(options):
    from impera import agent
    s = agent.Agent()
    s.start()


@command("compile", help_msg="Compile the project to a configuration model", require_project=True)
def compile_project(options):
    if options.profile:
        import cProfile
        import pstats
        result = cProfile.runctx('do_compile()', globals(), {}, "run.profile")
        p = pstats.Stats('run.profile')
        p.strip_dirs().sort_stats("time").print_stats(20)
    else:
        result = do_compile()

    return result


@command("list-commands", help_msg="Print out an overview of all commands")
def list_commands(options):
    print("The following commands are available:")
    for cmd, info in Commander.commands().items():
        print(" %s: %s" % (cmd, info["help"]))


def modules_parser_config(parser):
    parser.add_argument("cmd", help="The command to run")


@command("modules", help_msg="A tool to manage configuration modules in a project", parser_config=modules_parser_config)
def modules(options):
    tool = ModuleTool()
    tool.execute(options.cmd, options.other)


def export_parser_config(parser):
    """
        Configure the compiler of the export function
    """
    parser.add_argument("-g", dest="depgraph", help="Dump the dependency graph", action="store_true")
    parser.add_argument("-j", dest="json", help="Do not submit to the server but only store the json that would have been " +
                        "submitted in the supplied file")


@command("export", help_msg="Export the configuration", parser_config=export_parser_config, require_project=True)
def export(options):
    from impera.export import Exporter
    result = do_compile()
    if result is None:
        return
    export = Exporter(options)
    export.run(result)


def deploy_parser_config(parser):
    parser.add_argument("-a", dest="agent", help="Deploy the resources of this agent. Multiple agents are comma separated " +
                        "and wildcards are supported")
    parser.add_argument("-m", help="Agent mapping in the format: agentname=mappedname,agentname2=other", dest="map"),
    parser.add_argument("--dry-run", help="Only report changes", action="store_true", dest="dryrun")
    parser.add_argument("-l", help="List the deployment agents in the model", action="store_true", dest="list_agents")


@command("deploy", help_msg="""Deploy the configuration model without using a central impera server.
With the -a option the agents that need to be deployed are selected. This is a comma separated list and 
each element may have wildcards. The agents that match either the hostname of this machine or localhost use 
local io, all other agents use remote io over ssh. With the -m option a mapping can be provided: for 
example to use the ip instead of the agent name.

impera deploy -a *.example.com -m server1.example.com=172.16.0.10
""", parser_config=deploy_parser_config,
         require_project=True)
def deploy(options):
    from impera.deploy import deploy
    deploy(agents_spec=options.agent, dry_run=options.dryrun, agent_map=options.map, list_agents=options.list_agents)


def client_parser_config(parser):
    parser.add_argument("cmd", help="The command to run")


@command("client", help_msg="A client to send commands to Impera agents", parser_config=client_parser_config)
def client(options):
    from impera.server.client import Client

    client = Client()
    client.execute(options.cmd, options.other)

log_levels = {
    0: logging.ERROR,
    1: logging.WARNING,
    2: logging.INFO,
    3: logging.DEBUG
}


def cmd_parser():
    # create the argument compiler
    parser = ArgumentParser()
    parser.add_argument("-p", action="store_true", dest="profile", help='Profile this run of the program')
    parser.add_argument("-c", "--config", dest="config_file", help="Use this config file")
    parser.add_argument("-s", "--stats", dest="stats", action="store_true",
                        help="Dump all stats to the stats.json file after running")
    parser.add_argument("--log-file", dest="log_file", help="Path to the logfile")
    parser.add_argument("--log-file-level", dest="log_file_level", default=2, type=int,
                        help="Log level for messages going to the logfile: 0=ERROR, 1=WARNING, 2=INFO, 3=DEBUG")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Nothing is only errors, -v warning, -vv info and -vvv debug")
    subparsers = parser.add_subparsers(title="commands")
    for cmd_name, cmd_options in Commander.commands().items():
        cmd_subparser = subparsers.add_parser(cmd_name, help=cmd_options["help"])
        if cmd_options["parser_config"] is not None:
            cmd_options["parser_config"](cmd_subparser)
        cmd_subparser.set_defaults(func=cmd_options["function"])
        cmd_subparser.set_defaults(require_project=cmd_options["require_project"])

    return parser


def app():
    """
        Run the compiler
    """
    # set logging to sensible defaults
    formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(message)s",
        datefmt=None,
        reset=True,
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red',
        }
    )

    stream = logging.StreamHandler()
    stream.setLevel(logging.INFO)

    if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
        stream.setFormatter(formatter)

    logging.root.handlers = []
    logging.root.addHandler(stream)
    logging.root.setLevel(logging.DEBUG)

    # do an initial load of known config files to build the libdir path
    Config.load_config()

    # move to our virtual environment if there is one and then start loading plug-ins
    project = None
    try:
        project = Project.get()
        project.use_virtual_env()
        project.load_plugins()
    except ProjectNotFoundExcpetion:
        pass

    parser = cmd_parser()

    options, other = parser.parse_known_args()
    options.other = other

    # set the log level
    level = options.verbose
    if level >= len(log_levels):
        level = 3

    stream.setLevel(log_levels[level])

    # set the logfile
    if options.log_file:
        level = options.log_file_level
        if level >= len(log_levels):
            level = 3

        file_handler = logging.FileHandler(filename=options.log_file, mode="w")
        file_handler.setLevel(log_levels[level])
        logging.root.addHandler(file_handler)

    # Load the configuration
    Config.load_config(options.config_file)

    # start the command
    if not hasattr(options, "func"):
        # show help
        parser.print_usage()
        return

    if options.require_project and project is None:
        print("Unable to find a valid Impera project.")
        return

    options.func(options)

    if options.stats:
        # dump stats
        Stats.dump()

if __name__ == "__main__":
    app()
