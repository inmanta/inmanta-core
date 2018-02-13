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

import os
import logging
import uuid
import datetime
import json
from collections import defaultdict
from concurrent.futures import Future


from inmanta import protocol
from inmanta.config import Config, cmdline_rest_transport
from tornado.ioloop import IOLoop
import click
import texttable
from time import sleep


class Client(object):
    log = logging.getLogger(__name__)

    def __init__(self, host, port, io_loop):
        self._client = None
        if io_loop is not None:
            self._io_loop = io_loop
            self._own_loop = False
        else:
            self._io_loop = IOLoop.current()
            self._own_loop = True

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

        self._client = protocol.Client("cmdline")

    def run_sync(self, func):
        if self._own_loop:
            return self._io_loop.run_sync(func)

        else:
            f = Future()

            def future_to_future(future):
                exc = future.exception()
                if exc is not None:
                    f.set_exception(exc)
                else:
                    f.set_result(future.result())

            def run():
                try:
                    result = func()
                    if result is not None:
                        from tornado.gen import convert_yielded
                        result = convert_yielded(result)
                        result.add_done_callback(future_to_future)
                except Exception as e:
                    f.set_exception(e)
            self._io_loop.add_callback(run)

            return f.result()

    def do_request(self, method_name, key_name=None, arguments={}, allow_none=False):
        """
            Do a request and return the response
        """
        Client.log.debug("Calling method %s on server %s:%s with arguments %s" %
                         (method_name, cmdline_rest_transport.host.get(), cmdline_rest_transport.port.get(), arguments))

        if not hasattr(self._client, method_name):
            raise Exception("API call %s is not available." % method_name)

        method = getattr(self._client, method_name)

        def call():
            return method(**arguments)

        result = self.run_sync(call)

        if result is None:
            raise Exception("Failed to call server.")

        type(self).log.debug("Got response code %s and data: %s" % (result.code, result.result))

        if result.code == 200:
            if key_name is None:
                return result.result

            if key_name in result.result:
                return result.result[key_name]

            raise Exception("Expected %s in the response of %s." % (key_name, method_name))
        elif result.code == 404:
            if not allow_none:
                raise Exception("Requested %s not found on server" % key_name)
            return None

        else:
            msg = ": "
            if result.result is not None and "message" in result.result:
                msg += result.result["message"]

            raise Exception(("An error occurred while requesting %s" % key_name) + msg)

    def to_project_id(self, ref):
        """
            Convert ref to a uuid
        """
        try:
            project_id = uuid.UUID(ref)
        except ValueError:
            # try to resolve the id as project name
            projects = self.do_request("list_projects", "projects")

            id_list = []
            for project in projects:
                if ref == project["name"]:
                    id_list.append(project["id"])

            if len(id_list) == 0:
                raise Exception("Unable to find a project with the given id or name")

            elif len(id_list) > 1:
                raise Exception("Found multiple projects with %s name, please use the ID." % ref)

            else:
                project_id = id_list[0]

        return project_id

    def to_environment_id(self, ref, project_id=None):
        """
            Convert ref to an env uuid, optionally scoped to a project
        """
        try:
            env_id = uuid.UUID(ref)
        except ValueError:
            # try to resolve the id as project name
            envs = self.do_request("list_environments", "environments")

            id_list = []
            for env in envs:
                if ref == env["name"]:
                    if project_id is None or project_id == env["project_id"]:
                        id_list.append(env["id"])

            if len(id_list) == 0:
                raise Exception("Unable to find an environment with the given id or name")

            elif len(id_list) > 1:
                raise Exception("Found multiple environment with %s name, please use the ID." % ref)

            else:
                env_id = id_list[0]

        return env_id

    def to_form_id(self, ref, environment):
        """
            Convert ref to a form uuid
        """
        try:
            env_id = uuid.UUID(ref)
        except ValueError:
            # try to resolve the id as project name
            forms = self.do_request("list_forms", "forms", arguments=dict(tid=environment))

            id_list = []
            for form in forms:
                if ref == form["form_type"]:
                    id_list.append(form["form_id"])

            if len(id_list) == 0:
                raise Exception("Unable to find a form with the given id or name")

            elif len(id_list) > 1:
                raise Exception("Found multiple forms with %s name, please use the ID." % ref)

            else:
                env_id = id_list[0]

        return env_id


def print_table(header, rows, data_type=None):
    width, _ = click.get_terminal_size()

    table = texttable.Texttable(max_width=width)
    table.set_deco(texttable.Texttable.HEADER | texttable.Texttable.BORDER | texttable.Texttable.VLINES)
    if data_type is not None:
        table.set_cols_dtype(data_type)
    table.header(header)
    for row in rows:
        table.add_row(row)
    click.echo(table.draw())


@click.group()
@click.option("--host", help="The server hostname to connect to")
@click.option("--port", help="The server port to connect to")
@click.pass_context
def cmd(ctx, host, port):
    ctx.obj = Client(host, port, io_loop=ctx.obj)


@cmd.group("project")
@click.pass_context
def project(ctx):
    pass


@project.command(name="list")
@click.pass_obj
def project_list(client):
    projects = client.do_request("list_projects", "projects")

    if len(projects) > 0:
        print_table(['ID', 'Name'], [[n['id'], n['name']] for n in projects])

    else:
        click.echo("No projects defined.", err=True)


@project.command(name="show")
@click.argument("project")  # , help="The the id or name of the project to show")
@click.pass_obj
def project_show(client, project):
    project_id = client.to_project_id(project)
    project = client.do_request("get_project", "project", dict(id=project_id))

    print_table(["Name", "Value"], [["ID", project["id"]], ["Name", project["name"]]])


@project.command(name="create")
@click.option("--name", "-n", help="The name of the new project", required=True)
@click.pass_obj
def project_create(client, name):
    project = client.do_request("create_project", "project", {"name": name})
    print_table(["Name", "Value"], [["ID", project["id"]], ["Name", project["name"]]])


@project.command(name="modify")
@click.option("--name", "-n", help="The new name of the project", required=True)
@click.argument("project")  # , help="The id of the project to modify")
@click.pass_obj
def project_modify(client, name, project):
    project_id = client.to_project_id(project)
    project = client.do_request("modify_project", "project", dict(id=project_id, name=name))
    print_table(["Name", "Value"], [["ID", project["id"]], ["Name", project["name"]]])


@project.command(name="delete")
@click.argument("project")  # , help="The id of the project to modify")
@click.pass_obj
def project_delete(client, project):
    project_id = client.to_project_id(project)
    client.do_request("delete_project", arguments={"id": project_id})
    click.echo("Project successfully deleted")


@cmd.group("environment")
@click.pass_context
def environment(ctx):
    pass


@environment.command(name="create")
@click.option("--name", "-n", help="The name of the new environment", required=True)
@click.option("--project", "-p", help="The id of the project this environment belongs to", required=True)
@click.option("--repo-url", "-r", required=False, default="",
              help="The url of the repository that contains the configuration model")
@click.option("--branch", "-b", required=False, default="master",
              help="The branch in the repository that contains the configuration model")
@click.option("--save", "-s", default=False, is_flag=True,
              help="Save the ID of the environment and the server to the .inmanta config file")
@click.pass_obj
def environment_create(client, name, project, repo_url, branch, save):
    project_id = client.to_project_id(project)
    env = client.do_request("create_environment", "environment", dict(project_id=project_id, name=name,
                                                                      repository=repo_url, branch=branch))
    project = client.do_request("get_project", "project", {"id": project_id})

    if save:
        cfg = """
[config]
heartbeat-interval = 60
fact-expire = 1800
environment=%(env)s

[compiler_rest_transport]
host=%(host)s
port=%(port)s

[cmdline_rest_transport]
host=%(host)s
port=%(port)s
""" % {"env": env["id"], "host": client.host, "port": client.port}
        if os.path.exists(".inmanta"):
            click.echo(".inmanta exits, not writing config", err=True)
        else:
            with open(".inmanta", 'w') as f:
                f.write(cfg)

    print_table(('Environment ID', 'Environment name', 'Project ID', 'Project name'),
                ((env["id"], env["name"], project["id"], project["name"]),))


@environment.command(name="list")
@click.pass_obj
def environment_list(client):
    environments = client.do_request("list_environments", "environments")

    data = []
    for env in environments:
        prj = client.do_request("get_project", "project", dict(id=env["project"]))
        prj_name = prj['name']
        data.append((prj_name, env['project'], env['name'], env['id']))

    if len(data) > 0:
        print_table(('Project name', 'Project ID', 'Environment', 'Environment ID'), data)
    else:
        click.echo("No environment defined.")


@environment.command(name="show")
@click.argument("environment")
@click.pass_obj
def environment_show(client, environment):
    env = client.do_request("get_environment", "environment", dict(id=client.to_environment_id(environment)))
    print_table(('ID', 'Name', 'Repository URL', 'Branch Name'),
                ((env["id"], env["name"], env["repo_url"], env["repo_branch"]),))


@environment.command(name="modify")
@click.option("--name", "-n", help="The name of the new environment", required=True)
@click.option("--repo-url", "-r", required=False, default="",
              help="The url of the repository that contains the configuration model")
@click.option("--branch", "-b", required=False, default="master",
              help="The branch in the repository that contains the configuration model")
@click.argument("environment")
@click.pass_obj
def environment_modify(client, environment, name, repo_url, branch):
    env = client.do_request("modify_environment", "environment", dict(id=client.to_environment_id(environment),
                                                                      name=name, repository=repo_url, branch=branch))

    print_table(('ID', 'Name', 'Repository URL', 'Branch Name'),
                ((env["id"], env["name"], env["repo_url"], env["repo_branch"]),))


@environment.command(name="delete")
@click.argument("environment")
@click.pass_obj
def environment_delete(client, environment):
    env_id = client.to_environment_id(environment)
    client.do_request("delete_environment", arguments=dict(id=env_id))
    click.echo("Environment successfully deleted")


@environment.group("setting")
@click.pass_context
def env_setting(ctx):
    pass


@env_setting.command(name="list")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.pass_obj
def env_setting_list(client, environment):
    tid = client.to_environment_id(environment)
    settings = client.do_request("list_settings", arguments=dict(tid=tid))

    table_body = []
    for key in sorted(settings["metadata"].keys()):
        meta = settings["metadata"][key]
        value = ""
        if key in settings["settings"]:
            value = str(settings["settings"][key])

        default_value = ""
        if "default" in meta:
            default_value = str(meta["default"])

        table_body.append((key, value, default_value, meta["type"], meta["doc"]))

    click.echo("Settings for environment %s" % tid)
    print_table(("Key", "Value", "Default value", "Type", "Help"), table_body)


@env_setting.command(name="set")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.option("--key", "-k", help="The key to set", required=True)
@click.option("--value", "-o", help="The value to set", required=True)
@click.pass_obj
def env_setting_set(client, environment, key, value):
    tid = client.to_environment_id(environment)
    client.do_request("set_setting", arguments=dict(tid=tid, id=key, value=value))


@env_setting.command(name="get")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.option("--key", "-k", help="The key to get", required=True)
@click.pass_obj
def env_setting_get(client, environment, key):
    tid = client.to_environment_id(environment)
    value = client.do_request("get_setting", arguments=dict(tid=tid, id=key))
    click.echo(value["value"])


@env_setting.command(name="delete")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.option("--key", "-k", help="The key to delete", required=True)
@click.pass_obj
def env_setting_del(client, environment, key):
    tid = client.to_environment_id(environment)
    client.do_request("delete_setting", arguments=dict(tid=tid, id=key))


@cmd.group("agent")
@click.pass_context
def agent(ctx):
    pass


@agent.command(name="list")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.pass_obj
def agent_list(client, environment):
    env_id = client.to_environment_id(environment)
    agents = client.do_request("list_agents", key_name="agents", arguments=dict(tid=env_id))
    data = []
    for agent in agents:
        data.append((agent["name"], agent["environment"], agent["last_failover"]))

    print_table(('Agent', 'Environment', 'Last fail over'), data)


@cmd.group("version")
@click.pass_context
def version(ctx):
    pass


@version.command(name="list")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.pass_obj
def version_list(client, environment):
    env_id = client.to_environment_id(environment)
    versions = client.do_request("list_versions", "versions", arguments=dict(tid=env_id))

    print_table(('Created at', 'Version', 'Released', 'Deployed', '# Resources', '# Done', 'State'),
                ((x['date'], x['version'], x['released'], x['deployed'], x['total'], x['done'], x['result']) for x in versions),
                ["t", "t", "t", "t", "t", "t", "t"])


@version.command(name="release")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.option("--push", "-p", help="Push the version to the deployment agents", is_flag=True)
@click.argument("version")
@click.pass_obj
def version_release(client, environment, push, version):
    env_id = client.to_environment_id(environment)
    x = client.do_request("release_version", "model", dict(tid=env_id, id=version, push=push))

    print_table(('Created at', 'Version', 'Released', 'Deployed', '# Resources', '# Done', 'State'),
                ((x['date'], x['version'], x['released'], x['deployed'], x['total'], x['done'], x['result']),))


ISOFMT = "%Y-%m-%dT%H:%M:%S.%f"


@cmd.group("param")
@click.pass_context
def param(ctx):
    pass


@param.command(name="list")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.pass_obj
def param_list(client, environment):
    result = client.do_request("list_params", arguments=dict(tid=client.to_environment_id(environment)))
    expire = result["expire"]
    now = datetime.datetime.strptime(result["now"], ISOFMT)
    when = now - datetime.timedelta(0, expire)

    data = []
    for p in result["parameters"]:
        data.append((p["resource_id"], p['name'], p['source'], p['updated'],
                     datetime.datetime.strptime(p["updated"], ISOFMT) < when))

    print_table(('Resource', 'Name', 'Source', 'Updated', 'Expired'), data)


@param.command(name="set")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.option("--name", help="The name of the parameter", required=True)
@click.option("--value", help="The value of the parameter", required=True)
@click.pass_obj
def param_set(client, environment, name, value):
    tid = client.to_environment_id(environment)
    # first fetch the parameter
    param = client.do_request("get_param", "parameter", dict(tid=tid, id=name, resource_id=""), allow_none=True)

    if param is None:
        param = {"source": "user", "metadata": {}}

    param = client.do_request("set_param", "parameter", dict(tid=tid, id=name, value=value, source=param["source"],
                                                             resource_id="", metadata=param["metadata"]))

    print_table(('Name', 'Value', 'Source', 'Updated'),
                ((param['name'], param['value'], param['source'], param['updated']),))


@param.command(name="get")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.option("--name", help="The name of the parameter", required=True)
@click.option("--resource", help="The resource id of the parameter")
@click.pass_obj
def param_get(client, environment, name, resource):
    tid = client.to_environment_id(environment)

    if resource is None:
        resource = ""

    # first fetch the parameter
    param = client.do_request("get_param", "parameter", dict(tid=tid, id=name, resource_id=resource))

    print_table(('Name', 'Value', 'Source', 'Updated'),
                ((param['name'], param['value'], param['source'], param['updated']),))


@version.command(name="report")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.option("--version", "-i", help="The version to create a report from", required=True)
@click.option("-l", is_flag=True, help="Show a detailed version of the report")
@click.pass_obj
def version_report(client, environment, version, l):
    tid = client.to_environment_id(environment)
    result = client.do_request("get_version", arguments=dict(tid=tid, id=version, include_logs=True))

    agents = defaultdict(lambda: defaultdict(lambda: []))
    for res in result["resources"]:
        if len(res["actions"]) > 0 or l:
            agents[res["agent"]][res["resource_type"]].append(res)

    for agent in sorted(agents.keys()):
        click.echo(click.style("Agent: %s" % agent, bold=True))
        click.echo("=" * 72)

        for t in sorted(agents[agent].keys()):
            click.echo(click.style("Resource type:", bold=True) +
                       "{type} ({attr})".format(type=t, attr=agents[agent][t][0]["id_attribute_name"]))
            click.echo("-" * 72)

            for res in agents[agent][t]:
                click.echo((click.style(res["id_attribute_value"], bold=True) + " (#actions=%d)") % len(res["actions"]))
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


@cmd.group("form")
@click.pass_context
def form(ctx):
    pass


@form.command(name="list")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.pass_obj
def form_list(client, environment):
    result = client.do_request("list_forms", "forms", arguments=dict(tid=client.to_environment_id(environment)))

    data = []
    for p in result:
        data.append((p["form_type"], p['form_id'])),

    print_table(('Form Type', 'Form ID'), data)


@form.command(name="show")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.option("--form-type", "-t", help="Show details of this form", required=True)
@click.pass_obj
def form_show(client, environment, form_type):
    result = client.do_request("get_form", "form", arguments=dict(tid=client.to_environment_id(environment), id=form_type))
    values = []
    for k, v in result["fields"].items():
        if k in result["defaults"] and result["defaults"][k] != "":
            values.append([k, "type: %s, default: %s" % (v, result["defaults"][k])])
        else:
            values.append([k, "type: %s" % v])

    print_table(["Field", "Spec"], values)


@form.command(name="export")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.option("--form-type", "-t", help="Show details of this form", required=True)
@click.pass_obj
def form_export(client, environment, form_type):
    tid = client.to_environment_id(environment)
    form_def = client.do_request("get_form", "form", arguments=dict(tid=tid, id=form_type))
    form_records = client.do_request("list_records", "records", arguments=dict(tid=tid, form_type=form_type,
                                                                               include_record=True))

    click.echo(json.dumps({"form_type": form_def, "records": form_records}))


@form.command(name="import")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.option("--form-type", "-t", help="Show details of this form", required=True)
@click.option("--file", help="The json file with the record data", required=True)
@click.pass_obj
def form_import(client, environment, form_type, file):
    tid = client.to_environment_id(environment)
    if not os.path.exists(file):
        raise Exception("%s file does not exist." % file)

    data = {}
    with open(file, "r") as fd:
        try:
            data = json.load(fd)
        except Exception as e:
            raise Exception("Unable to load records, invalid json") from e

    if "records" not in data:
        raise Exception("No records found in input file")

    form_type_def = data["form_type"]
    if form_type != form_type_def["form_type"]:
        raise click.ClickException("Unable to load form data for %s into form %s" % (form_type_def["form_type"], form_type))

    form_id = form_type_def["id"]

    for record in data["records"]:
        if record["form"] == form_id:
            client.do_request("create_record", "record", arguments=dict(tid=tid, form_type=form_type, form=record["fields"]))


@cmd.group("record")
@click.pass_context
def record(ctx):
    pass


@record.command(name="list")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.option("--form-type", "-t", help="Show details of this form", required=True)
@click.option("--show-all", "-a", help="Show all fields", is_flag=True, default=False)
@click.pass_obj
def record_list(client, environment, form_type, show_all):
    tid = client.to_environment_id(environment)

    if not show_all:
        result = client.do_request("list_records", "records", arguments=dict(tid=tid, form_type=form_type))
        data = []
        for p in result:
            data.append((p["id"], p['changed'])),

        print_table(('Record ID', 'Changed'), data)
    else:
        result = client.do_request("list_records", "records", arguments=dict(tid=tid, form_type=form_type, include_record=True))
        fields = []
        data = []
        for p in result:
            fields = p["fields"].keys()
            values = [p["id"], p['changed']]
            values.extend(p["fields"].values())
            data.append(values),

        allfields = ['Record ID', 'Changed']
        allfields.extend(fields)
        print_table(allfields, data)


@record.command(name="create")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.option("--form-type", "-t", help="Create a record of this type.", required=True)
@click.option("--field", "-p", help="Field values", multiple=True, default=[])
@click.pass_obj
def record_create(client, environment, form_type, field):
    tid = client.to_environment_id(environment)

    fields = {}
    for f in field:
        parts = f.split("=")
        if len(parts) != 2:
            raise Exception("Argument %s should be in the key=value form." % f)

        fields[parts[0].strip()] = parts[1].strip()

    try:
        uuid.UUID(form_type)
        raise Exception("Form type should be the type string, not the uuid.")
    except ValueError:
        pass

    result = client.do_request("create_record", "record", arguments=dict(tid=tid, form_type=form_type, form=fields))

    values = []
    for k in sorted(result["fields"].keys()):
        values.append([k, result["fields"][k]])

    print_table(["Field", "Value"], values)


@record.command(name="update")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.option("--record", "-r", help="The id of the record to edit", required=True)
@click.option("--field", "-p", help="Field values", multiple=True, default=[])
@click.pass_obj
def record_update(client, environment, record, field):
    tid = client.to_environment_id(environment)

    fields = {}
    for f in field:
        parts = f.split("=")
        if len(parts) != 2:
            raise Exception("Argument %s should be in the key=value form." % f)

        fields[parts[0].strip()] = parts[1].strip()

    result = client.do_request("update_record", "record", arguments=dict(tid=tid, id=record, form=fields))

    values = []
    for k in sorted(result["fields"].keys()):
        values.append([k, result["fields"][k]])

    print_table(["Field", "Value"], values)


@record.command(name="delete")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.argument("record")
@click.pass_obj
def record_delete(client, environment, record):
    tid = client.to_environment_id(environment)
    try:
        record_id = uuid.UUID(record)
    except ValueError:
        raise Exception("The record id should be a valid UUID")

    client.do_request("delete_record", arguments=dict(tid=tid, id=record_id))
    return ((), ())


@cmd.command(name="monitor")
@click.option("--environment", "-e", help="The environment to use", required=True)
@click.pass_obj
def monitor_deploy(client, environment):
    tid = client.to_environment_id(environment)

    versions = client.do_request("list_versions", arguments=dict(tid=tid))
    allversion = versions["versions"]
    first = next(version for version in allversion if version["result"] != "pending")

    total = first["total"]
    done = first["done"]
    last = done
    ident = first["version"]

    with click.progressbar(label="version:%d" % ident, length=total, show_pos=True, show_eta=False) as bar:
        bar.update(done)
        while done != total:
            if done != last:
                bar.update(done - last)
                last = done
            sleep(1)
            version = client.do_request("get_version", arguments=dict(tid=tid, id=int(ident), limit=0))
            done = version["model"]["done"]
        if done != last:
            bar.update(done - last)
            last = done

    click.echo("Complete: %s/%s" % (done, total))


@cmd.group("token")
@click.pass_context
def token(ctx):
    pass


@token.command(name="create")
@click.option("--environment", "-e", help="The environment to use.", required=True)
@click.option("--api", is_flag=True, help="Add client_type api to the token.")
@click.option("--compiler", is_flag=True, help="Add client_type compiler to the token.")
@click.option("--agent", is_flag=True, help="Add client_type agent to the token.")
@click.pass_obj
def create_token(client, environment, api, compiler, agent):
    tid = client.to_environment_id(environment)

    client_types = []
    if api:
        client_types.append("api")

    if compiler:
        client_types.append("compiler")

    if agent:
        client_types.append("agent")

    token = client.do_request("create_token", key_name="token", arguments=dict(tid=tid, client_types=client_types))

    click.echo("Token: " + token)


@token.command(name="bootstrap")
@click.pass_obj
def bootstrap_token(client):
    """
        Generate a bootstrap token that provides access to everything. This token is only valid for 3600 seconds.
    """
    click.echo("Token: " + protocol.encode_token(["api", "compiler", "agent"], expire=3600))


def main():
    Config.load_config()
    cmd()


if __name__ == '__main__':
    main()
