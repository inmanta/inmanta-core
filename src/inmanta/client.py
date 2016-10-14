"""
    Copyright 2016 Inmanta

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

from inmanta import protocol
from cliff.lister import Lister
from cliff.show import ShowOne
from cliff.command import Command
from inmanta.config import Config, cmdline_rest_transport
from blessings import Terminal
from tornado.ioloop import IOLoop


class InmantaCommand(Command):
    """
        An inmanta command
    """
    log = logging.getLogger(__name__)

    def __init__(self, app, app_args):
        super().__init__(app, app_args)
        self._client = None
        self._io_loop = IOLoop.current()

    def get_parser(self, prog_name, parser_override=None):
        if parser_override is not None:
            parser = parser_override.add_parser(prog_name, help=self.get_description())
        else:
            parser = super().get_parser(prog_name)
        Config.load_config()

        parser.add_argument("--host", dest="host", help="The server hostname to connect to (default: localhost)",
                            default=cmdline_rest_transport.host.get())
        parser.add_argument("--port", dest="port", help="The server port to connect to (default: 8888)",
                            default=cmdline_rest_transport.port.get(), type=int)
        parser = self.parser_config(parser)
        return parser

    def parser_config(self, parser):
        """
            Method for a subclass to override to add additional arguments to the command
        """
        return parser

    def do_request(self, method_name, key_name=None, arguments={}, allow_none=False):
        """
            Do a request and return the response
        """
        type(self).log.debug("Calling method %s on server %s:%s with arguments %s" %
                             (method_name, cmdline_rest_transport.host.get(),
                              cmdline_rest_transport.port.get(), arguments))

        if not hasattr(self._client, method_name):
            raise Exception("API call %s is not available." % method_name)

        method = getattr(self._client, method_name)

        def call():
            return method(**arguments)

        result = self._io_loop.run_sync(call, 2)

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

    def take_action(self, parsed_args):
        Config.set("cmdline_rest_transport", "host", parsed_args.host)
        Config.set("cmdline_rest_transport", "port", parsed_args.port)
        self._client = protocol.Client("cmdline")
        return self.run_action(parsed_args)

    def run_action(self, parsed_args):
        raise NotImplementedError()


class ProjectShow(InmantaCommand, ShowOne):
    """
        Show project details
    """

    def parser_config(self, parser):
        parser.add_argument("id", help="The the id of the project to show")
        return parser

    def run_action(self, parsed_args):
        project_id = self.to_project_id(parsed_args.id)
        project = self.do_request("get_project", "project", dict(id=project_id))
        return (('ID', 'Name'), ((project["id"], project["name"])))


class ProjectCreate(InmantaCommand, ShowOne):
    """
        Create a new project
    """

    def parser_config(self, parser):
        parser.add_argument("-n", "--name", dest="name", help="The name of the new project", required=True)
        return parser

    def run_action(self, parsed_args):
        project = self.do_request("create_project", "project", {"name": parsed_args.name})
        return (('ID', 'Name'), ((project["id"], project["name"])))


class ProjectModify(InmantaCommand, ShowOne):
    """
        Modify a project
    """

    def parser_config(self, parser):
        parser.add_argument("-n", "--name", dest="name", help="The name of the new project")
        parser.add_argument("id", help="The id of the project to modify")
        return parser

    def run_action(self, parsed_args):
        project_id = self.to_project_id(parsed_args.id)
        project = self.do_request("modify_project", "project", dict(id=project_id, name=parsed_args.name))

        return (('ID', 'Name'), ((project["id"], project["name"])))


class ProjectList(InmantaCommand, Lister):
    """
        List all projects defined on the server
    """

    def run_action(self, parsed_args):
        projects = self.do_request("list_projects", "projects")

        if len(projects) > 0:
            return (('ID', 'Name'), ((n['id'], n['name']) for n in projects))

        print("No projects defined.")
        return ((), ())


class ProjectDelete(InmantaCommand, Command):
    """
        Delete a project
    """

    def parser_config(self, parser):
        parser.add_argument("id", help="The id of the project to delete.")
        return parser

    def run_action(self, parsed_args):
        project_id = self.to_project_id(parsed_args.id)
        self.do_request("delete_project", arguments={"id": project_id})
        print("Project successfully deleted", file=self.app.stdout)


class EnvironmentCreate(InmantaCommand, ShowOne):
    """
        Create a new environment
    """

    def parser_config(self, parser):
        parser.add_argument("-n", "--name", dest="name", help="The name of the new environment", required=True)
        parser.add_argument("-p", "--project", dest="project", help="The id of the project this environment belongs to",
                            required=True)
        parser.add_argument("-r", "--repo-url", dest="repo", required=True,
                            help="The url of the repository that contains the configuration model")
        parser.add_argument("-b", "--branch", dest="branch", required=True,
                            help="The branch in the repository that contains the configuration model")
        parser.add_argument("-s", "--save", dest="save", action='store_true', default=False,
                            help="Save the ID of the environment and the server to the .inmanta config file")
        return parser

    def run_action(self, parsed_args):
        project_id = self.to_project_id(parsed_args.project)
        env = self.do_request("create_environment", "environment", dict(project_id=project_id, name=parsed_args.name,
                                                                        repository=parsed_args.repo, branch=parsed_args.branch))
        project = self.do_request("get_project", "project", {"id": project_id})

        if parsed_args.save:
            cfg = """
[config]
heartbeat-interval = 60
fact-expire = 1800
environment=%s


[compiler_rest_transport]
host = %s
port = %s

[cmdline_rest_transport]
host=%s
port=%s""" % (env["id"], parsed_args.host, parsed_args.port, parsed_args.host, parsed_args.port)
            if os.path.exists(".inmanta"):
                print(".inmanta exits, not writing config")
            else:
                with open(".inmanta", 'w') as f:
                    f.write(cfg)

        return (('Environment ID', 'Environment name', 'Project ID', 'Project name'),
                ((env["id"], env["name"], project["id"], project["name"]))
                )


class EnvironmentList(InmantaCommand, Lister):
    """
        List environment defined on the server
    """

    def run_action(self, parsed_args):
        environments = self.do_request("list_environments", "environments")

        data = []
        for env in environments:
            print(env)
            prj = self.do_request("get_project", "project", dict(id=env["project"]))
            prj_name = prj['name']
            data.append((prj_name, env['project'], env['name'], env['id']))

        if len(data) > 0:
            return (('Project name', 'Project ID', 'Environment', 'Environment ID'), data)

        print("No environment defined.")
        return ((), ())


class EnvironmentShow(InmantaCommand, ShowOne):
    """
        Show environment details
    """

    def parser_config(self, parser):
        parser.add_argument("id", help="The the id of the evironment to show")
        return parser

    def run_action(self, parsed_args):
        env = self.do_request("get_environment", "environment", dict(id=self.to_environment_id(parsed_args.id)))
        return (('ID', 'Name', 'Repository URL', 'Branch Name'),
                ((env["id"], env["name"], env["repo_url"], env["repo_branch"])))


class EnvironmentModify(InmantaCommand, ShowOne):
    """
        Modify an environment
    """

    def parser_config(self, parser):
        parser.add_argument("-n", "--name", dest="name", help="The name of the environment")
        parser.add_argument("id", help="The id of the environment to modify")
        parser.add_argument("-r", "--repo-url", dest="repo",
                            help="The url of the repository that contains the configuration model")
        parser.add_argument("-b", "--branch", dest="branch",
                            help="The branch in the repository that contains the configuration model")
        return parser

    def run_action(self, parsed_args):
        environment = self.do_request("modify_environment", "environment",
                                      dict(id=parsed_args.id, name=parsed_args.name, repository=parsed_args.repo,
                                           branch=parsed_args.branch))

        return (('ID', 'Name', 'Repository URL', 'Branch Name'), ((environment["id"], environment["name"],
                                                                   environment["repo_url"], environment["repo_branch"])))


class EnvironmentDelete(InmantaCommand, Command):
    """
        Delete an environment
    """

    def parser_config(self, parser):
        parser.add_argument("id", help="The id of the environment to delete.")
        return parser

    def run_action(self, parsed_args):
        env_id = self.to_environment_id(parsed_args.id)
        self.do_request("delete_environment", arguments=dict(id=env_id))
        print("Environment successfully deleted", file=self.app.stdout)


class VersionList(InmantaCommand, Lister):
    """
        List the configuration model versions
    """

    def parser_config(self, parser):
        parser.add_argument("-e", "--environment", dest="env", help="The id of environment", required=True)
        return parser

    def run_action(self, parsed_args):
        env_id = self.to_environment_id(parsed_args.env)
        versions = self.do_request("list_versions", "versions", arguments=dict(tid=env_id))
        return (('Created at', 'Version', 'Released', 'Deployed', '# Resources', '# Done', 'State'),
                ((x['date'], x['version'], x['released'], x['deployed'], x['total'], x['done'], x['result']) for x in versions))


class AgentList(InmantaCommand, Lister):
    """
        List all the agents connected to the server
    """

    def run_action(self, parsed_args):
        nodes = self.do_request("list_agents", "nodes")
        data = []
        for node in nodes:
            for agent in node["agents"]:
                data.append((node["hostname"], agent["name"], agent["environment"], agent["last_seen"]))

        return (('Node', 'Agent', 'Environment', 'Last seen'), data)


class VersionRelease(InmantaCommand, ShowOne):
    """
        Release a version of the configuration model
    """

    def parser_config(self, parser):
        parser.add_argument("-e", "--environment", dest="env", help="The id of environment", required=True)
        parser.add_argument("-p", "--push", dest="push", action="store_true", help="Push the version to the deployment agents")
        parser.add_argument("version", help="The version to release for deploy")
        return parser

    def run_action(self, parsed_args):
        env_id = self.to_environment_id(parsed_args.env)
        x = self.do_request("release_version", "model", dict(tid=env_id, id=parsed_args.version, push=parsed_args.push))

        return (('Created at', 'Version', 'Released', 'Deployed', '# Resources', '# Done', 'State'),
                ((x['date'], x['version'], x['released'], x['deployed'], x['total'], x['done'], x['result'])))


ISOFMT = "%Y-%m-%dT%H:%M:%S.%f"


class ParamList(InmantaCommand, Lister):
    """
        List all parameters for the environment
    """

    def parser_config(self, parser):
        parser.add_argument("-e", "--environment", dest="env", help="The id of environment", required=True)
        return parser

    def run_action(self, parsed_args):
        result = self.do_request("list_params", arguments=dict(tid=self.to_environment_id(parsed_args.env)))
        expire = result["expire"]
        now = datetime.datetime.strptime(result["now"], ISOFMT)
        when = now - datetime.timedelta(0, expire)

        data = []
        for p in result["parameters"]:
            data.append((p["resource_id"], p['name'], p['source'], p['updated'],
                         datetime.datetime.strptime(p["updated"], ISOFMT) < when))

        return (('Resource', 'Name', 'Source', 'Updated', 'Expired'), data)


class ParamSet(InmantaCommand, ShowOne):
    """
        Set a parameter in the environment
    """

    def parser_config(self, parser):
        parser.add_argument("-e", "--environment", dest="env", help="The id of environment", required=True)
        parser.add_argument("--name", dest="name", help="The name of the parameter", required=True)
        parser.add_argument("--value", dest="value", help="The value of the parameter", required=True)
        return parser

    def run_action(self, parsed_args):
        tid = self.to_environment_id(parsed_args.env)
        # first fetch the parameter
        param = self.do_request("get_param", "parameter", dict(tid=tid, id=parsed_args.name, resource_id=""), allow_none=True)

        # check the source
        if param is not None and param["source"] != "user":
            raise Exception("Only parameters set by users can be modified!")

        param = self.do_request("set_param", "parameter", dict(tid=tid, id=parsed_args.name,
                                                               value=parsed_args.value, source="user", resource_id=""))

        return (('Name', 'Value', 'Source', 'Updated'),
                (param['name'], param['value'], param['source'], param['updated']))


class ParamGet(InmantaCommand, ShowOne):
    """
        Set a parameter in the environment
    """

    def parser_config(self, parser):
        parser.add_argument("-e", "--environment", dest="env", help="The id of environment", required=True)
        parser.add_argument("--name", dest="name", help="The name of the parameter", required=True)
        parser.add_argument("--resource", dest="resource", help="The resource id of the parameter")
        return parser

    def run_action(self, parsed_args):
        tid = self.to_environment_id(parsed_args.env)

        resource = parsed_args.resource
        if resource is None:
            resource = ""

        # first fetch the parameter
        param = self.do_request("get_param", "parameter", dict(tid=tid, id=parsed_args.name, resource_id=resource))

        return (('Name', 'Value', 'Source', 'Updated'),
                (param['name'], param['value'], param['source'], param['updated']))


class VersionReport(InmantaCommand, Command):
    """
        Generate a deploy report
    """

    def parser_config(self, parser):
        parser.add_argument("-e", "--environment", dest="env", help="The id of environment", required=True)
        parser.add_argument("-i", "--version", dest="version", help="The version to create a report from", required=True)
        parser.add_argument("-l", dest="details", action="store_true", help="Show a detailed version of the report")
        return parser

    def run_action(self, parsed_args):
        tid = self.to_environment_id(parsed_args.env)

        result = self.do_request("get_version", arguments=dict(tid=tid, id=parsed_args.version, include_logs=True))

        term = Terminal()
        agents = defaultdict(lambda: defaultdict(lambda: []))
        for res in result["resources"]:
            if (len(res["actions"]) > 0 and res["actions"][0]["data"] is not None and len(res["actions"][0]["data"]) > 0) or parsed_args.details:
                agents[res["id_fields"]["agent_name"]][res["id_fields"]["entity_type"]].append(res)

        for agent in sorted(agents.keys()):
            print(term.bold("Agent: %s" % agent))
            print("=" * 72)

            for type in sorted(agents[agent].keys()):
                print("{t.bold}Resource type:{t.normal} {type} ({attr})".
                      format(type=type, attr=agents[agent][type][0]["id_fields"]["attribute"], t=term))
                print("-" * 72)

                for res in agents[agent][type]:
                    print((term.bold + "%s" + term.normal + " (#actions=%d)") %
                          (res["id_fields"]["attribute_value"], len(res["actions"])))
                    # for dryrun show only the latest, for deploy all
                    if parsed_args.release == "dryrun":
                        if len(res["actions"]) > 0:
                            action = res["actions"][0]
                            print("* last check: %s" % action["timestamp"])
                            print("* result: %s" % ("error" if action["level"] != "INFO" else "success"))
                            if len(action["data"]) == 0:
                                print("* no changes")
                            else:
                                print("* changes:")
                                for field in sorted(action["data"].keys()):
                                    values = action["data"][field]
                                    if field == "hash":
                                        print("  - content:")
                                        diff_value = self.do_request("diff", arguments=dict(a=values[0], b=values[1]))
                                        print("    " + "    ".join(diff_value["diff"]))
                                    else:
                                        print("  - %s:" % field)
                                        print("    " + term.bold + "from:" + term.normal + " %s" % values[0])
                                        print("    " + term.bold + "to:" + term.normal + " %s" % values[1])

                                    print("")

                            print("")
                    else:
                        pass

                print("")


class FormList(InmantaCommand, Lister):
    """
        List all parameters for the environment
    """

    def parser_config(self, parser):
        parser.add_argument("-e", "--environment", dest="env", help="The id of environment", required=True)
        return parser

    def run_action(self, parsed_args):
        result = self.do_request("list_forms", "forms", arguments=dict(tid=self.to_environment_id(parsed_args.env)))

        data = []
        for p in result:
            data.append((p["form_type"], p['form_id'])),

        return (('Form Type', 'Form ID'), data)


class FormShow(InmantaCommand, ShowOne):
    """
        List all parameters for the environment
    """

    def parser_config(self, parser):
        parser.add_argument("-e", "--environment", dest="env", help="The id of environment", required=True)
        parser.add_argument("-t", "--form-type", dest="form", help="Show details of this form", required=True)
        return parser

    def run_action(self, parsed_args):
        result = self.do_request("get_form", "form", arguments=dict(tid=self.to_environment_id(parsed_args.env),
                                                                    id=parsed_args.form))
        headers = []
        values = []
        for k, v in result["fields"].items():
            headers.append(k)
            if k in result["defaults"]:
                values.append("type: %s, default: %s" % (v, result["defaults"]))
            else:
                values.append("type: %s" % v)

        return (headers, values)


class FormExport(InmantaCommand, ShowOne):
    """
        Export all data in the records of a form to json
    """

    def parser_config(self, parser):
        parser.add_argument("-e", "--environment", dest="env", help="The id of environment", required=True)
        parser.add_argument("-t", "--form-type", dest="form", help="Show details of this form", required=True)
        return parser

    def run_action(self, parsed_args):
        tid = self.to_environment_id(parsed_args.env)
        form_def = self.do_request("get_form", "form", arguments=dict(tid=tid, id=parsed_args.form))
        form_records = self.do_request("list_records", "records", arguments=dict(tid=tid, form_type=parsed_args.form,
                                                                                 include_record=True))

        print(json.dumps({"form_type": form_def, "records": form_records}))
        return ((), ())


class FormImport(InmantaCommand, ShowOne):
    """
        Import records into an existing form. It creates new records!
    """

    def parser_config(self, parser):
        parser.add_argument("-e", "--environment", dest="env", help="The id of environment", required=True)
        parser.add_argument("-t", "--form-type", dest="form", help="Show details of this form", required=True)
        parser.add_argument("--file", dest="file", help="The json file with the record data", required=True)
        return parser

    def run_action(self, parsed_args):
        tid = self.to_environment_id(parsed_args.env)
        file_name = parsed_args.file
        if not os.path.exists(file_name):
            raise Exception("%s file does not exist." % file_name)

        data = {}
        with open(file_name, "r") as fd:
            try:
                data = json.load(fd)
            except Exception as e:
                raise Exception("Unable to load records, invalid json") from e

        if "records" not in data:
            raise Exception("No records found in input file")

        for record in data["records"]:
            if record["form_type"] == parsed_args.form:
                self.do_request("create_record", "record", arguments=dict(tid=tid, form_type=parsed_args.form,
                                                                          form=record["fields"]))

        return ((), ())


class RecordList(InmantaCommand, Lister):
    """
        List all parameters for the environment
    """

    def parser_config(self, parser):
        parser.add_argument("-e", "--environment", dest="env", help="The id of environment", required=True)
        parser.add_argument("-t", "--form-type", dest="form", help="Show records from this form", required=True)
        return parser

    def run_action(self, parsed_args):
        tid = self.to_environment_id(parsed_args.env)
        result = self.do_request("list_records", "records", arguments=dict(tid=tid, form_type=parsed_args.form))

        data = []
        for p in result:
            data.append((p["record_id"], p['changed'])),

        return (('Record ID', 'Changed'), data)


class RecordCreate(InmantaCommand, ShowOne):
    """
        Create a new record
    """

    def parser_config(self, parser):
        parser.add_argument("-e", "--environment", dest="env", help="The id of environment", required=True)
        parser.add_argument("-t", "--form-type", dest="form", help="Show details of this form", required=True)
        parser.add_argument("-p", "--field", help="Field values", action="append", default=[])
        return parser

    def run_action(self, parsed_args):
        tid = self.to_environment_id(parsed_args.env)

        fields = {}
        for field in parsed_args.field:
            parts = field.split("=")
            if len(parts) != 2:
                raise Exception("Argument %s should be in the key=value form." % field)

            fields[parts[0].strip()] = parts[1].strip()

        try:
            uuid.UUID(parsed_args.form)
            raise Exception("Form type should be the type string, not the uuid.")
        except ValueError:
            pass

        result = self.do_request("create_record", "record", arguments=dict(tid=tid, form_type=parsed_args.form, form=fields))

        headers = []
        values = []
        for k in sorted(result["fields"].keys()):
            headers.append(k)
            values.append(result["fields"][k])

        return (headers, values)


class RecordUpdate(InmantaCommand, ShowOne):
    """
        Create a new record
    """

    def parser_config(self, parser):
        parser.add_argument("-e", "--environment", dest="env", help="The id of environment", required=True)
        parser.add_argument("-r", "--record", dest="record", help="The id of the record to edit", required=True)
        parser.add_argument("-p", "--field", help="Field values", action="append")
        return parser

    def run_action(self, parsed_args):
        tid = self.to_environment_id(parsed_args.env)

        fields = {}
        for field in parsed_args.field:
            parts = field.split("=")
            if len(parts) != 2:
                raise Exception("Argument %s should be in the key=value form." % field)

            fields[parts[0].strip()] = parts[1].strip()

        result = self.do_request("update_record", "record", arguments=dict(tid=tid, id=parsed_args.record, form=fields))

        headers = []
        values = []
        for k in sorted(result["fields"].keys()):
            headers.append(k)
            values.append(result["fields"][k])

        return (headers, values)


class RecordDelete(InmantaCommand, ShowOne):
    """
        Delete a record
    """

    def parser_config(self, parser):
        parser.add_argument("-e", "--environment", dest="env", help="The id of environment", required=True)
        parser.add_argument("record_id", help="The the id of the record to delete")
        return parser

    def run_action(self, parsed_args):
        tid = self.to_environment_id(parsed_args.env)
        try:
            record_id = uuid.UUID(parsed_args.record_id)
        except ValueError:
            raise Exception("The record id should be a valid UUID")

        self.do_request("delete_record", arguments=dict(tid=tid, id=record_id))
        return ((), ())
