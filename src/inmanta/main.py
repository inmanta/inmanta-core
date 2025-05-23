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
"""

import datetime
import importlib.metadata
import logging
import os
import shutil
import uuid
from collections import defaultdict
from time import sleep
from typing import Any, Callable, Optional, Union, cast

import click
import texttable

from inmanta import protocol, util
from inmanta.config import Config, cmdline_rest_transport
from inmanta.const import AgentAction, DesiredStateVersionStatus, ResourceAction
from inmanta.resources import Id
from inmanta.types import JsonType, ResourceVersionIdStr


class Client:
    log = logging.getLogger(__name__)

    def __init__(self, host: Optional[str], port: Optional[int]) -> None:
        if host is None:
            self.host = cmdline_rest_transport.host.get()
        else:
            self.host = host
            Config.set("cmdline_rest_transport", "host", host)

        if port is None:
            self.port = cmdline_rest_transport.port.get()
        else:
            self.port = port
            Config.set("cmdline_rest_transport", "port", str(port))

        self._client = protocol.SyncClient("cmdline")

    def do_request(
        self, method_name: str, key_name: Optional[str] = None, arguments: JsonType = {}, allow_none: bool = False
    ) -> Optional[JsonType]:
        """
        Do a request and return the response
        """
        self.log.debug("Calling method %s on server %s:%s with arguments %s", method_name, self.host, self.host, arguments)

        if not hasattr(self._client, method_name):
            raise Exception("API call %s is not available." % method_name)

        method: Callable[..., protocol.Result] = getattr(self._client, method_name)
        result = method(**arguments)

        if result is None:
            raise Exception("Failed to call server.")

        self.log.debug("Got response code %s and data: %s", result.code, result.result)

        if result.code == 200:
            if key_name is None:
                return result.result

            if result.result and key_name in result.result:
                return result.result[key_name]

            raise Exception(f"Expected {key_name} in the response of {method_name}.")
        elif result.code == 404:
            if not allow_none:
                raise Exception("Requested %s not found on server" % key_name)
            return None

        else:
            msg = ": "
            if result.result is not None and "message" in result.result:
                msg += result.result["message"]

            raise Exception(("An error occurred while requesting %s" % key_name) + msg)

    def get_list(self, method_name: str, key_name: Optional[str] = None, arguments: JsonType = {}) -> list[dict[str, Any]]:
        """
        Same as do request, but return type is a list of dicts
        """
        return cast(list[dict[str, Any]], self.do_request(method_name, key_name, arguments, False))

    def get_dict(self, method_name: str, key_name: Optional[str] = None, arguments: JsonType = {}) -> dict[str, str]:
        """
        Same as do request, but return type is a list of dicts
        """
        return cast(dict[str, str], self.do_request(method_name, key_name, arguments, False))

    def to_project_id(self, ref: str) -> uuid.UUID:
        """
        Convert ref to a uuid
        """
        try:
            project_id = uuid.UUID(ref)
        except ValueError:
            # try to resolve the id as project name
            projects: list[dict[str, str]] = self.get_list("list_projects", "projects")

            id_list: list[str] = []
            for project in projects:
                if ref == project["name"]:
                    id_list.append(project["id"])

            if len(id_list) == 0:
                raise Exception("Unable to find a project with the given id or name")

            elif len(id_list) > 1:
                raise Exception("Found multiple projects with %s name, please use the ID." % ref)

            else:
                project_id = uuid.UUID(id_list[0])

        return project_id

    def to_environment_id(self, ref: str, project_id: Optional[uuid.UUID] = None) -> uuid.UUID:
        """
        Convert ref to an env uuid, optionally scoped to a project
        """
        try:
            env_id = uuid.UUID(ref)
        except ValueError:
            # try to resolve the id as project name
            envs: list[dict[str, str]] = self.get_list("list_environments", "environments")

            id_list: list[str] = []
            for env in envs:
                if ref == env["name"]:
                    if project_id is None or project_id == env["project_id"]:
                        id_list.append(env["id"])

            if len(id_list) == 0:
                raise Exception("Unable to find an environment with the given id or name")

            elif len(id_list) > 1:
                raise Exception("Found multiple environment with %s name, please use the ID." % ref)

            else:
                env_id = uuid.UUID(id_list[0])

        return env_id


def print_table(header: list[str], rows: list[list[str]], data_type: Optional[list[str]] = None) -> None:
    click.echo(get_table(header, rows, data_type))


def get_table(header: list[str], rows: list[list[str]], data_type: Optional[list[str]] = None) -> str:
    """
    Returns a table that would fit in the current terminal.
    """
    width, _ = shutil.get_terminal_size()

    table = texttable.Texttable(max_width=width)
    table.set_deco(texttable.Texttable.HEADER | texttable.Texttable.BORDER | texttable.Texttable.VLINES)
    if data_type is not None:
        table.set_cols_dtype(data_type)
    table.header(header)
    for row in rows:
        table.add_row(row)
    return table.draw()


@util.click_group_with_plugins(iter(importlib.metadata.entry_points(group="inmanta.cli_plugins")))
@click.group(help="Base command")
@click.option("--host", help="The server hostname to connect to")
@click.option("--port", help="The server port to connect to")
@click.pass_context
def cmd(ctx: click.Context, host: str, port: int) -> None:
    ctx.obj = Client(host, port)


@cmd.group("project", help="Subcommand to manage projects")
@click.pass_context
def project(ctx: click.Context) -> None:
    pass


@project.command(name="list", help="List all projects")
@click.pass_obj
def project_list(client: Client) -> None:
    projects = client.get_list("list_projects", "projects")

    if len(projects) > 0:
        print_table(["ID", "Name"], [[n["id"], n["name"]] for n in projects])

    else:
        click.echo("No projects defined.", err=True)


@project.command(name="show")
@click.argument("project")
@click.pass_obj
def project_show(client: Client, project: str) -> None:
    """
    Show the details of a single project

    PROJECT: The id or name of the project to show
    """
    project_id = client.to_project_id(project)
    project_data = client.get_dict("get_project", "project", dict(id=project_id))

    print_table(["Name", "Value"], [["ID", project_data["id"]], ["Name", project_data["name"]]])


@project.command(name="create")
@click.option("--name", "-n", help="The name of the new project", required=True)
@click.pass_obj
def project_create(client: Client, name: str) -> None:
    """Create a new project on the server"""
    project = client.get_dict("create_project", "project", {"name": name})
    print_table(["Name", "Value"], [["ID", project["id"]], ["Name", project["name"]]])


@project.command(name="modify")
@click.option("--name", "-n", help="The new name of the project", required=True)
@click.argument("project")
@click.pass_obj
def project_modify(client: Client, name: str, project: str) -> None:
    """
    Modify an existing project.

    PROJECT: The id or name of the project to modify
    """
    project_id = client.to_project_id(project)
    project_data = client.get_dict("modify_project", "project", dict(id=project_id, name=name))
    print_table(["Name", "Value"], [["ID", project_data["id"]], ["Name", project_data["name"]]])


@project.command(name="delete")
@click.argument("project")
@click.pass_obj
def project_delete(client: Client, project: str) -> None:
    """
    Delete an existing project.

    PROJECT: The id or name of the project to delete
    """
    project_id = client.to_project_id(project)
    client.do_request("delete_project", arguments={"id": project_id})
    click.echo("Project successfully deleted")


@cmd.group("environment", help="Subcommand to manage environments")
@click.pass_context
def environment(ctx: click.Context) -> None:
    pass


@environment.command(name="create", help="Create a new environment")
@click.option(
    "--name", "-n", help="The name of the new environment. The name should be unique for each project.", required=True
)
@click.option("--project", "-p", help="The id of the project this environment belongs to", required=True)
@click.option(
    "--repo-url", "-r", required=False, default="", help="The url of the repository that contains the configuration model"
)
@click.option(
    "--branch",
    "-b",
    required=False,
    default="master",
    help="The branch in the repository that contains the configuration model",
)
@click.option(
    "--save",
    "-s",
    default=False,
    is_flag=True,
    help="Save the ID of the environment and the server to the .inmanta config file",
)
@click.pass_obj
def environment_create(client: Client, name: str, project: str, repo_url: str, branch: str, save: bool) -> None:
    project_id = client.to_project_id(project)
    env = client.get_dict(
        "create_environment", "environment", dict(project_id=project_id, name=name, repository=repo_url, branch=branch)
    )
    project_data = client.get_dict("get_project", "project", {"id": project_id})

    if save:
        save_config(client, env)

    print_table(
        ["Environment ID", "Environment name", "Project ID", "Project name"],
        [[env["id"], env["name"], project_data["id"], project_data["name"]]],
    )


def save_config(client: Client, env: dict[str, str]) -> None:
    cfg = """
[config]
fact-expire = 1800
environment={env}

[compiler_rest_transport]
host={host}
port={port}

[cmdline_rest_transport]
host={host}
port={port}
""".format(
        env=env["id"],
        host=client.host,
        port=client.port,
    )

    if os.path.exists(".inmanta") and not click.confirm(".inmanta exists, do you want to overwrite it?"):
        click.echo("not writing config", err=True)
    else:
        with open(".inmanta", "w", encoding="utf-8") as f:
            f.write(cfg)


@environment.command(name="list", help="List all environments")
@click.pass_obj
def environment_list(client: Client) -> None:
    environments = client.get_list("list_environments", "environments")

    data = []
    for env in environments:
        prj = client.get_dict("get_project", "project", dict(id=env["project"]))
        prj_name = prj["name"]
        data.append([prj_name, env["project"], env["name"], env["id"]])

    if len(data) > 0:
        print_table(["Project name", "Project ID", "Environment", "Environment ID"], data)
    else:
        click.echo("No environments defined.")


@environment.command(name="show")
@click.argument("environment")
@click.option(
    "--format",
    "format_string",
    help=(
        "Instead of outputting a table, use the supplied format string. Accepts Python format syntax."
        " Supported fields are 'id', 'name', 'project', 'repo_url', 'repo_branch'"
    ),
    required=False,
)
@click.pass_obj
def environment_show(client: Client, environment: str, format_string: Optional[str]) -> None:
    """
    Show details of an environment

    ENVIRONMENT: ID or name of the environment to show
    """
    env = client.get_dict("environment_get", "data", dict(id=client.to_environment_id(environment)))
    if format_string is not None:
        print(format_string.format(**env))
    else:
        print_table(
            ["ID", "Name", "Repository URL", "Branch Name"], [[env["id"], env["name"], env["repo_url"], env["repo_branch"]]]
        )


@environment.command(name="save")
@click.argument("environment")
@click.pass_obj
def environment_write_config(client: Client, environment: str) -> None:
    """
    Save the ID of the environment and the server to the .inmanta config file

    ENVIRONMENT: ID or name of the environment to write the config for
    """
    env = client.get_dict("environment_get", "data", dict(id=client.to_environment_id(environment)))
    save_config(client, env)


@environment.command(name="modify")
@click.option("--name", "-n", help="The name of the new environment", required=True)
@click.option(
    "--repo-url", "-r", required=False, default="", help="The url of the repository that contains the configuration model"
)
@click.option(
    "--branch",
    "-b",
    required=False,
    default="master",
    help="The branch in the repository that contains the configuration model",
)
@click.argument("environment")
@click.pass_obj
def environment_modify(client: Client, environment: str, name: str, repo_url: str, branch: str) -> None:
    """
    Modify an existing environment

    ENVIRONMENT: ID or name of the environment to modify
    """
    env = client.get_dict(
        "modify_environment",
        "environment",
        dict(id=client.to_environment_id(environment), name=name, repository=repo_url, branch=branch),
    )

    print_table(
        ["ID", "Name", "Repository URL", "Branch Name"], [[env["id"], env["name"], env["repo_url"], env["repo_branch"]]]
    )


@environment.command(name="delete")
@click.argument("environment")
@click.pass_obj
def environment_delete(client: Client, environment: str) -> None:
    """
    Delete an existing environment

    ENVIRONMENT: ID or name of the environment to delete
    """
    env_id = client.to_environment_id(environment)
    client.do_request("delete_environment", arguments=dict(id=env_id))
    click.echo("Environment successfully deleted")


@environment.command(name="recompile")
@click.argument("environment")
@click.option(
    "--update",
    "-u",
    is_flag=True,
    required=False,
    default=False,
    show_default=True,
    help="Update the model and its dependencies before recompiling",
)
@click.pass_obj
def environment_recompile(client: Client, environment: str, update: bool) -> None:
    """
    Request the server to recompile the model of this environment.

    ENVIRONMENT: ID or name of the environment to trigger the recompile for
    """
    env_id = client.to_environment_id(environment)
    result = client.do_request(
        "notify_change",
        arguments=dict(
            id=env_id,
            update=update,
            metadata={
                "type": "cli",
                "message": "Compile triggered from the cli",
            },
        ),
    )
    if result and result.get("metadata", {}).get("warnings"):
        click.echo("\n".join(result.get("metadata", {}).get("warnings")))
    else:
        click.echo("Update & Recompile triggered successfully" if update else "Recompile triggered successfully")


@environment.group("setting", help="Subcommand to manage environment settings")
@click.pass_context
def env_setting(ctx: click.Context) -> None:
    pass


@env_setting.command(name="list", help="List settings of an environment")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.pass_obj
def env_setting_list(client: Client, environment: str) -> None:
    tid = client.to_environment_id(environment)
    settings = cast(dict[str, dict[str, str]], client.do_request("list_settings", arguments=dict(tid=tid)))

    table_body = []
    for key in sorted(settings["metadata"].keys()):
        meta = cast(dict[str, str], settings["metadata"][key])
        value = ""
        if key in settings["settings"]:
            value = str(settings["settings"][key])

        default_value = ""
        if "default" in meta:
            default_value = str(meta["default"])

        table_body.append([key, value, default_value, meta["type"], meta["doc"]])

    click.echo("Settings for environment %s" % tid)
    print_table(["Key", "Value", "Default value", "Type", "Help"], table_body)


@env_setting.command(name="set", help="Adjust an environment setting")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.option("--key", "-k", help="The key to set", required=True)
@click.option("--value", "-o", help="The value to set", required=True)
@click.pass_obj
def env_setting_set(client: Client, environment: str, key: str, value: str) -> None:
    tid = client.to_environment_id(environment)
    client.do_request("set_setting", arguments=dict(tid=tid, id=key, value=value))


@env_setting.command(name="get", help="Get an environment setting")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.option("--key", "-k", help="The key to get", required=True)
@click.pass_obj
def env_setting_get(client: Client, environment: str, key: str) -> None:
    tid = client.to_environment_id(environment)
    value = client.get_dict("get_setting", arguments=dict(tid=tid, id=key))
    click.echo(value["value"])


@env_setting.command(name="delete", help="Delete an environment setting")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.option("--key", "-k", help="The key to delete", required=True)
@click.pass_obj
def env_setting_del(client: Client, environment: str, key: str) -> None:
    tid = client.to_environment_id(environment)
    client.do_request("delete_setting", arguments=dict(tid=tid, id=key))


@cmd.group("agent", help="Subcommand to manage agents")
@click.pass_context
def agent(ctx: click.Context) -> None:
    pass


@agent.command(name="list", help="List agents in an environment")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.pass_obj
def agent_list(client: Client, environment: str) -> None:
    env_id = client.to_environment_id(environment)
    agents = client.get_list("list_agents", key_name="agents", arguments=dict(tid=env_id))
    data: list[list[str]] = []
    for agent in agents:
        data.append([agent["name"], agent["environment"], str(agent["paused"]), agent["last_failover"]])

    print_table(["Agent", "Environment", "Paused", "Last fail over"], data)


@agent.command(name="pause")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.option(
    "--agent",
    help="The name of the agent to pause.",
    default=None,
)
@click.option("--all", help="Pause all agents in the given environment", is_flag=True)
@click.pass_obj
def pause_agent(client: Client, environment: str, agent: Optional[str], all: bool) -> None:
    """
    Pause a specific agent or all agents in a given environment. A paused agent cannot execute deploy operations.
    """
    if agent is not None and all:
        raise click.ClickException("The --agent option and the --all flag cannot be used simultaneously.")
    if agent is None and not all:
        raise click.ClickException(
            "Either the --agent options should be set or use the --all flag to pause all agents in the given environment."
        )
    if agent is not None:
        client.do_request(
            method_name="agent_action", arguments=dict(tid=environment, name=agent, action=AgentAction.pause.value)
        )
    else:
        client.do_request(method_name="all_agents_action", arguments=dict(tid=environment, action=AgentAction.pause.value))


@agent.command(name="unpause")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.option(
    "--agent",
    help="The name of the agent to unpause.",
    default=None,
)
@click.option("--all", help="Unpause all agents in the given environment", is_flag=True)
@click.pass_obj
def unpause_agent(client: Client, environment: str, agent: Optional[str], all: bool) -> None:
    """
    Unpause a specific agent or all agents in a given environment. A unpaused agent will be able to execute
    deploy operations.
    """
    if agent is not None and all:
        raise click.ClickException("The --agent option and the --all flag cannot be used simultaneously.")
    if agent is None and not all:
        raise click.ClickException(
            "Either the --agent options should be set or use the --all flag to pause all agents in the given environment."
        )
    if agent is not None:
        client.do_request(
            method_name="agent_action", arguments=dict(tid=environment, name=agent, action=AgentAction.unpause.value)
        )
    else:
        client.do_request(method_name="all_agents_action", arguments=dict(tid=environment, action=AgentAction.unpause.value))


@cmd.group("version", help="Subcommand to manage versions")
@click.pass_context
def version(ctx: click.Context) -> None:
    pass


@version.command(name="list", help="List versions in an environment")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.pass_obj
def version_list(client: Client, environment: str) -> None:
    env_id = client.to_environment_id(environment)
    versions = client.get_list("list_desired_state_versions", "data", arguments=dict(tid=env_id))
    print_table(
        ["Created at", "Version", "Released", "# Resources", "State"],
        [
            [
                x["date"],
                x["version"],
                str(
                    x["status"]
                    not in [DesiredStateVersionStatus.candidate.value, DesiredStateVersionStatus.skipped_candidate.value]
                ),
                x["total"],
                x["status"],
            ]
            for x in versions
        ],
        ["t", "t", "t", "t", "t"],
    )


@version.command(name="release")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.option("--push", "-p", help="[Deprecated] will be ignored", is_flag=True)
@click.option(
    "--full",
    help="[Deprecated] will be ignored",
    is_flag=True,
)
@click.argument("version")
@click.pass_obj
def version_release(client: Client, environment: str, push: bool, full: bool, version: str) -> None:
    """
    Release the specified version of the configuration model for deployment.

    VERSION: Version of the model to release
    """
    env_id = client.to_environment_id(environment)

    x = client.get_dict("release_version", "model", dict(tid=env_id, id=version))

    print_table(
        [
            "Created at",
            "Version",
            "Released",
            "# Resources",
        ],
        [[x["date"], x["version"], x["released"], x["total"]]],
    )


@cmd.group("param", help="Subcommand to manage parameters")
@click.pass_context
def param(ctx: click.Context) -> None:
    pass


@param.command(name="list", help="List parameters in an environment")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.pass_obj
def param_list(client: Client, environment: str) -> None:
    result = client.get_dict("list_params", arguments=dict(tid=client.to_environment_id(environment)))
    expire = int(result["expire"])
    now = util.parse_timestamp(result["now"])
    when = now - datetime.timedelta(0, expire)

    data = []
    parameters = cast(list[dict[str, str]], result["parameters"])
    for p in parameters:
        data.append(
            [
                p["resource_id"],
                p["name"],
                p["source"],
                p["updated"],
                str(float(util.parse_timestamp(p["updated"]) < when)),
            ]
        )

    print_table(["Resource", "Name", "Source", "Updated", "Expired"], data)


@param.command(name="set", help="Set a parameter in an environment")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.option("--name", help="The name of the parameter", required=True)
@click.option("--value", help="The value of the parameter", required=True)
@click.pass_obj
def param_set(client: Client, environment: str, name: str, value: str) -> None:
    tid = client.to_environment_id(environment)
    # first fetch the parameter
    param_data = cast(
        Optional[dict[str, str]],
        client.do_request("get_param", "parameter", dict(tid=tid, id=name, resource_id=""), allow_none=True),
    )

    param = {"source": "user", "metadata": {}} if param_data is None else param_data
    param_return = client.get_dict(
        "set_param",
        "parameter",
        dict(tid=tid, id=name, value=value, source=param["source"], resource_id="", metadata=param["metadata"]),
    )

    print_table(
        ["Name", "Value", "Source", "Updated"],
        [[param_return["name"], param_return["value"], param_return["source"], param_return["updated"]]],
    )


@param.command(name="get", help="Get a parameter from an environment")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.option("--name", help="The name of the parameter", required=True)
@click.option("--resource", help="The resource id of the parameter")
@click.pass_obj
def param_get(client: Client, environment: str, name: str, resource: Optional[str]) -> None:
    tid = client.to_environment_id(environment)

    if resource is None:
        resource = ""

    # first fetch the parameter
    param = client.get_dict("get_param", "parameter", dict(tid=tid, id=name, resource_id=resource))

    print_table(["Name", "Value", "Source", "Updated"], [[param["name"], param["value"], param["source"], param["updated"]]])


@version.command(name="report", help="Get a report about a version, describing the involved resources, agents and actions")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.option("--version", "-i", help="The version to create a report from", required=True)
@click.option("-l", "show_detailed_report", is_flag=True, help="Show a detailed version of the report")
@click.pass_obj
def version_report(client: Client, environment: str, version: str, show_detailed_report: bool) -> None:
    tid = client.to_environment_id(environment)
    result = client.do_request("get_version", arguments=dict(tid=tid, id=version, include_logs=True))

    if not result:
        return

    agents: dict[str, dict[str, list[dict[str, object]]]] = defaultdict(lambda: defaultdict(list))
    for res in result["resources"]:
        if len(res["actions"]) > 0 or show_detailed_report:
            agents[res["agent"]][res["resource_type"]].append(res)

    for agent in sorted(agents.keys()):
        click.echo(click.style("Agent: %s" % agent, bold=True))
        click.echo("=" * 72)

        for t in sorted(agents[agent].keys()):
            resource_version_id = cast(ResourceVersionIdStr, agents[agent][t][0]["resource_version_id"])
            parsed_resource_version_id = Id.parse_id(resource_version_id)
            click.echo(click.style("Resource type:", bold=True) + f"{t} ({parsed_resource_version_id.attribute})")
            click.echo("-" * 72)

            for res in agents[agent][t]:
                parsed_id = Id.parse_id(res["resource_version_id"])
                click.echo((click.style(parsed_id.attribute_value, bold=True) + " (#actions=%d)") % len(res["actions"]))
                # for dryrun show only the latest, for deploy all
                if not result["model"]["released"]:
                    if len(res["actions"]) > 0:
                        action = res["actions"][0]
                        click.echo("* last check: %s" % action["timestamp"])
                        click.echo("* result: %s" % ("error" if action["level"] != "INFO" else "success"))
                        if len(action["data"]) == 0:
                            click.echo("* no changes")
                        else:
                            click.echo("* changes:")
                            for field in sorted(action["data"].keys()):
                                values = action["data"][field]
                                if field == "hash":
                                    click.echo("  - content:")
                                    diff_value = client.do_request("diff", arguments=dict(a=values[0], b=values[1]))
                                    click.echo("    " + "    ".join(diff_value["diff"]))
                                else:
                                    click.echo("  - %s:" % field)
                                    click.echo("    " + click.style("from:", bold=True) + " %s" % values[0])
                                    click.echo("    " + click.style("to:", bold=True) + " %s" % values[1])

                                click.echo("")

                        click.echo("")
                else:
                    pass

            click.echo("")


@cmd.command(
    name="monitor",
    help="Monitor the deployment process of the configuration model in an environment, "
    "receiving continuous updates on the deployment status",
)
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.pass_obj
def monitor_deploy(client: Client, environment: str) -> None:
    tid = client.to_environment_id(environment)

    def get_stats() -> tuple[int, int]:
        deploy_status = client.do_request("resource_list", arguments=dict(tid=tid, deploy_summary=True, limit=0))

        summary = deploy_status["metadata"]["deploy_summary"]
        done: int = (
            summary["by_state"]["deployed"]
            + summary["by_state"]["failed"]
            + summary["by_state"]["skipped"]
            + summary["by_state"]["skipped_for_undefined"]
            + summary["by_state"]["unavailable"]
            + summary["by_state"]["undefined"]
        )
        total: int = summary["total"]
        return done, total

    done, total = get_stats()

    last = done

    with click.progressbar(label="environment:%s" % environment, length=total, show_pos=True, show_eta=False) as bar:
        bar.update(done)
        while done != total:
            if done != last:
                bar.update(done - last)
                last = done
            sleep(1)
            done, total = get_stats()
        if done != last:
            bar.update(done - last)
            last = done

    click.echo(f"Complete: {done}/{total}")


@cmd.group("token", help="Subcommand to manage access tokens")
@click.pass_context
def token(ctx: click.Context) -> None:
    pass


@token.command(name="create", help="Create a new token for an environment for the specified client types")
@click.option("--environment", "-e", help="The environment to use.", required=True)
@click.option("--api", is_flag=True, help="Add client_type api to the token.")
@click.option("--compiler", is_flag=True, help="Add client_type compiler to the token.")
@click.option("--agent", is_flag=True, help="Add client_type agent to the token.")
@click.pass_obj
def create_token(client: Client, environment: str, api: str, compiler: str, agent: str) -> None:
    tid = client.to_environment_id(environment)

    client_types = []
    if api:
        client_types.append("api")

    if compiler:
        client_types.append("compiler")

    if agent:
        client_types.append("agent")

    token = cast(str, client.do_request("create_token", key_name="token", arguments=dict(tid=tid, client_types=client_types)))

    click.echo("Token: " + token)


@token.command(name="bootstrap")
@click.pass_obj
def bootstrap_token(client: Client) -> None:
    """
    Generate a bootstrap token that provides access to everything. This token is only valid for 3600 seconds.
    """
    click.echo("Token: " + protocol.encode_token(["api", "compiler", "agent"], expire=3600))


@cmd.group("action-log", help="Subcommand to view the resource action log")
@click.pass_context
def resource_action_log(ctx: click.Context) -> None:
    pass


def validate_resource_version_id(
    ctx: click.Context, option: Union[click.Option, click.Parameter], value: str
) -> ResourceVersionIdStr:
    if not Id.is_resource_version_id(value):
        raise click.BadParameter(value)
    return ResourceVersionIdStr(value)


@resource_action_log.command(name="list")
@click.option("--environment", "-e", help="The ID or name of the environment to use", required=True)
@click.option(
    "--rvid",
    help="The resource version ID of the resource",
    callback=validate_resource_version_id,
    required=True,
)
@click.option("--action", help="Only list this resource action", type=click.Choice([ra.value for ra in ResourceAction]))
@click.pass_obj
def resource_action_log_list(client: Client, environment: str, rvid: ResourceVersionIdStr, action: Optional[str]) -> None:
    """
    List the resource action log for a specific Resource.
    """
    tid = client.to_environment_id(environment)
    ra_logs = client.get_list("get_resource", "logs", arguments=dict(tid=tid, id=rvid, logs=True, log_action=action))
    headers = ["Action ID", "Action", "Started", "Finished", "Status"]
    rows = [[log["action_id"], log["action"], log["started"], log["finished"], log.get("status", "")] for log in ra_logs]
    if rows:
        print_table(headers, rows)
    else:
        click.echo("No resource action log entry found.")


@resource_action_log.command(name="show-messages")
@click.option("--environment", "-e", help="The ID or name of the environment to use", required=True)
@click.option(
    "--rvid",
    help="The resource version ID of the resource",
    callback=validate_resource_version_id,
    required=True,
)
@click.option("--action-id", type=click.UUID, help="The ID of the resource action record", required=True)
@click.pass_obj
def resource_action_log_show(client: Client, environment: str, rvid: ResourceVersionIdStr, action_id: uuid.UUID) -> None:
    """
    Show the log messages for a specific entry in the resource action log.
    """
    tid = client.to_environment_id(environment)
    action_logs = [
        action_log
        for action_log in client.get_list("get_resource", "logs", arguments=dict(tid=tid, id=rvid, logs=True))
        if action_log["action_id"] == str(action_id)
    ]
    if not action_logs:
        click.echo(f"No log messages found for action-id {action_id}")
    else:
        for msg in action_logs[0]["messages"]:
            click.echo(f"{msg['timestamp']} {msg['level']} {msg['msg']}")


def main() -> None:
    Config.load_config()
    cmd()


if __name__ == "__main__":
    main()
