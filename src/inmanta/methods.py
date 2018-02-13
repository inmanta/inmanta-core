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

from functools import wraps
import uuid
import datetime

from inmanta import data
from inmanta import const
from tornado import gen


VALID_CLIENT_TYPES = ["api", "agent", "compiler", "public"]


def protocol(index=False, id=False, operation="POST", reply=True, arg_options={}, timeout=None, server_agent=False, api=True,
             agent_server=False, validate_sid=None, client_types=["public"]):
    """
        Decorator to identify a method as a RPC call. The arguments of the decorator are used by each transport to build
        and model the protocol.

        :param index: A method that returns a list of resources. The url of this method is only the method/resource name.
        :param id: This method requires an id of a resource. The python function should have an id parameter.
        :param operation: The type of HTTP operation (verb)
        :param timeout: nr of seconds before request it terminated
        :param api This is a call from the client to the Server (True if not server_agent and not agent_server)
        :param server_agent: This is a call from the Server to the Agent (reverse http channel through long poll)
        :param agent_server: This is a call from the Agent to the Server
        :param validate_sid: This call requires a valid session, true by default if agent_server and not api
        :param client_types: The allowed client types for this call
        :param arg_options Options related to arguments passed to the method. The key of this dict is the name of the arg to
            which the options apply. The value is another dict that can contain the following options:
                header: Map this argument to a header with the following name.
                reply_header: If the argument is mapped to a header, this header will also be included in the reply
                getter: Call this method after validation and pass its return value to the method call. This may change the
                        type of the argument. This method can raise an HTTPException to return a 404 for example.
    """
    if api is None:
        api = not server_agent and not agent_server

    if validate_sid is None:
        validate_sid = agent_server and not api

    properties = {
        "index": index,
        "id": id,
        "reply": reply,
        "operation": operation,
        "timeout": timeout,
        "api": api,
        "server_agent": server_agent,
        "agent_server": agent_server,
        "validate_sid": validate_sid,
        "arg_options": arg_options,
        "client_types": client_types,
    }

    def wrapper(func):
        """
            Return the wrapper method so it can be used to do RPC calls. Additionally it adds the protocol properties of the
            decorator to the method.
        """
        @wraps(func)
        @gen.coroutine
        def wrapped_method(self, *args, **kwargs):
            """
                This wrapper will first call the original method to validate the arguments passed and possible custom
                validation logic in the method itself.
            """
            func(self, *args, **kwargs)

            result = yield self._call(args=args, kwargs=kwargs, protocol_properties=properties)
            return result

        properties["method"] = func
        wrapped_method.__protocol_properties__ = properties
        return wrapped_method

    return wrapper


class HTTPException(Exception):
    def __init__(self, code, message=None):
        super().__init__(code, message)
        self.code = code
        self.message = message


class Method(object):
    """
        A decorator to add methods to the protocol.
    """
    __method_name__ = None


@gen.coroutine
def get_environment(env: uuid.UUID, metadata: dict) -> data.Environment:
    metadata[const.INMANTA_URN + "env"] = str(env)
    env = yield data.Environment.get_by_id(env)
    if env is None:
        raise HTTPException(code=404, message="The given environment id does not exist!")
    return env


@gen.coroutine
def add_env(env: uuid.UUID, metadata: dict) -> uuid.UUID:
    metadata[const.INMANTA_URN + "env"] = str(env)
    return env


@gen.coroutine
def ignore_env(obj: object, metadata: dict) -> object:
    """
        This mapper only adds an env all for authz
    """
    metadata[const.INMANTA_URN + "env"] = "all"
    return obj


ENV_ARG = {"header": "X-Inmanta-tid", "getter": get_environment, "reply_header": True}
ENV_OPTS = {"tid": ENV_ARG}
AGENT_ENV_ARG = {"header": "X-Inmanta-tid", "reply_header": True, "getter": add_env}
AGENT_ENV_OPTS = {"tid": AGENT_ENV_ARG}


class Project(Method):
    """
        Method for working with projects
    """
    __method_name__ = "project"

    @protocol(operation="PUT", client_types=["api"])
    def create_project(self, name):
        """
            Create a new project
        """

    @protocol(operation="POST", id=True, client_types=["api"])
    def modify_project(self, id: uuid.UUID, name: str):
        """
            Modify the given project
        """

    @protocol(operation="DELETE", id=True, client_types=["api"])
    def delete_project(self, id: uuid.UUID):
        """
            Delete the given project and all related data
        """

    @protocol(operation="GET", index=True, client_types=["api"])
    def list_projects(self):
        """
            Create a list of projects
        """

    @protocol(operation="GET", id=True, client_types=["api"])
    def get_project(self, id: uuid.UUID):
        """
            Get a project and a list of the ids of all environments
        """


class Environment(Method):
    """
        Method for working with environments
    """
    __method_name__ = "environment"

    @protocol(operation="PUT", client_types=["api"])
    def create_environment(self, project_id: uuid.UUID, name: str, repository: str=None, branch: str=None):
        """
            Create a new environment

            :param project_id The id of the project this environment belongs to
            :param name The name of the environment
            :param repository The url (in git form) of the repository
            :param branch The name of the branch in the repository
        """

    @protocol(operation="POST", id=True, client_types=["api"])
    def modify_environment(self, id: uuid.UUID, name: str, repository: str=None, branch: str=None):
        """
            Modify the given environment

            :param id The id of the environment
            :param name The name of the environment
            :param repository The url (in git form) of the repository
            :param branch The name of the branch in the repository
        """

    @protocol(operation="DELETE", id=True, client_types=["api"])
    def delete_environment(self, id: uuid.UUID):
        """
            Delete the given environment and all related data
        """

    @protocol(operation="GET", index=True, client_types=["api"])
    def list_environments(self):
        """
            Create a list of environments
        """

    @protocol(operation="GET", id=True, client_types=["api"], arg_options={"id": {"getter": add_env}})
    def get_environment(self, id: uuid.UUID, versions: int=None, resources: int=None):
        """
            Get an environment and all versions associated

            :param id The id of the environment to return
            :param versions Include this many available version for this environment.
            :param resources Include this many available resources for this environment.
        """


class EnvironmentSettings(Method):
    """
        Method for listing/getting/setting/removing settings of an environment. This API is also used by agents to configure
        environments.
    """
    __method_name__ = "environment_settings"

    @protocol(operation="GET", index=True, arg_options=ENV_OPTS, api=True, agent_server=True,
              client_types=["api", "agent", "compiler"])
    def list_settings(self, tid: uuid.UUID):
        """
            List the settings in the current environment
        """

    @protocol(operation="POST", id=True, arg_options=ENV_OPTS, api=True, agent_server=True,
              client_types=["api", "agent", "compiler"])
    def set_setting(self, tid: uuid.UUID, id: str, value: object):
        """
            Set a value
        """

    @protocol(operation="GET", id=True, arg_options=ENV_OPTS, api=True, agent_server=True,
              client_types=["api", "agent"])
    def get_setting(self, tid: uuid.UUID, id: str):
        """
            Get a value
        """

    @protocol(operation="DELETE", id=True, arg_options=ENV_OPTS, api=True, agent_server=True,
              client_types=["api", "agent"])
    def delete_setting(self, tid: uuid.UUID, id: str):
        """
            Delete a value
        """


class EnvironmentAuth(Method):
    """
        Method for listing and creating auth tokens for an environment that can be used by the agent and compilers
    """
    __method_name__ = "environment_auth"

    @protocol(operation="POST", index=True, arg_options=ENV_OPTS, client_types=["api", "compiler"])
    def create_token(self, tid: uuid.UUID, client_types: list, idempotent: bool=True):
        """
            Create or get a new token for the given client types. Tokens generated with this call are scoped to the current
            environment.

            :param tid: The environment id
            :param client_types: The client types for which this token is valid (api, agent, compiler)
            :param idempotent: The token should be idempotent, such tokens do not have an expire or issued at set so their
                               value will not change.
        """


class Decommision(Method):
    """
        Decomission an environment
    """
    __method_name__ = "decommission"

    @protocol(operation="POST", id=True, arg_options={"id": {"getter": get_environment}}, client_types=["api"])
    def decomission_environment(self, id: uuid.UUID, metadata: dict=None):
        """
            Decommision an environment. This is done by uploading an empty model to the server and let purge_on_delete handle
            removal.
        """

    @protocol(operation="DELETE", id=True, arg_options={"id": {"getter": get_environment}}, client_types=["api"])
    def clear_environment(self, id: uuid.UUID):
        """
            Clear all data from this environment
        """


class HeartBeatMethod(Method):
    """
        Send a heartbeat to indicate that an agent is alive
    """
    __method_name__ = "heartbeat"

    @protocol(operation="POST", agent_server=True, validate_sid=False, arg_options=ENV_OPTS, client_types=["agent"])
    def heartbeat(self, sid: uuid.UUID, tid: uuid.UUID, endpoint_names: list, nodename: str):
        """
            Send a heartbeat to the server

            :paran sid: The session ID used by this agent at this moment
            :param tid: The environment this node and its agents belongs to
            :param endpoint_names: The names of the endpoints on this node
            :param nodename: The name of the node from which the heart beat comes

            also registered as API method, because it is called with an invalid SID the first time
        """

    @protocol(operation="PUT", agent_server=True, arg_options={"sid": {"getter": ignore_env}}, client_types=["agent"])
    def heartbeat_reply(self, sid: uuid.UUID, reply_id: uuid.UUID, data: dict):
        """
            Send a reply back to the server

            :param sid: The session ID used by this agent at this moment
            :param reply_id: The id data is a reply to
            :param data: The data as a response to the reply
        """


class FileMethod(Method):
    """
        Upload, retrieve and check for file. A file is identified by a hash of its content.
    """
    __method_name__ = "file"

    @protocol(operation="PUT", id=True, agent_server=True, api=True, client_types=["api", "agent", "compiler"],
              arg_options={"id": {"getter": ignore_env}})
    def upload_file(self, id: str, content: str):
        """
            Upload a new file

            :param id The id of the file
            :param content The base64 encoded content of the file
        """

    @protocol(operation="HEAD", id=True, agent_server=True, api=True, client_types=["api", "agent", "compiler"],
              arg_options={"id": {"getter": ignore_env}})
    def stat_file(self, id: str):
        """
            Does the file exist

            :param id The id of the file to check
        """

    @protocol(operation="GET", id=True, agent_server=True, api=True, client_types=["api", "agent", "compiler"],
              arg_options={"id": {"getter": ignore_env}})
    def get_file(self, id: str):
        """
            Retrieve a file

            :param id: The id of the file to retrieve
        """

    @protocol(api=True, client_types=["api", "agent", "compiler"], arg_options={"files": {"getter": ignore_env}})
    def stat_files(self, files: list):
        """
            Check which files exist in the given list

            :param files: A list of file id to check
            :return: A list of files that do not exist.
        """


class ResourceMethod(Method):
    """
        Manage resources on the server
    """
    __method_name__ = "resource"

    @protocol(operation="GET", id=True, agent_server=True, validate_sid=False, arg_options=ENV_OPTS, api=True,
              client_types=["api", "agent"])
    def get_resource(self, tid: uuid.UUID, id: str, logs: bool=None, status: bool=None,
                     log_action: const.ResourceAction=None, log_limit: int=0):
        """
            Return a resource with the given id.

            :param tid The id of the environment this resource belongs to
            :param id Get the resource with the given id
            :param logs Include the logs in the response
            :param status return only resources of this status
            :param log_action The log action to include, leave empty/none for all actions. Valid actions are one of
                              the action strings in const.ResourceAction
            :param log_limit Limit the number of logs included in the response
        """

    @protocol(operation="GET", index=True, agent_server=True, arg_options=ENV_OPTS, client_types=["agent"])
    def get_resources_for_agent(self, tid: uuid.UUID, agent: str, version: int=None):
        """
            Return the most recent state for the resources associated with agent, or the version requested

            :param tid: The id of the environment this resource belongs to
            :param agent: The agent
            :param version: The version to retrieve. If none, the latest available version is returned. With a specific version
                            that version is returned, even if it has not been released yet.
        """

    @protocol(operation="POST", index=True, agent_server=True, arg_options=ENV_OPTS, client_types=["agent"])
    def resource_action_update(self, tid: uuid.UUID, resource_ids: list, action_id: uuid.UUID, action: const.ResourceAction,
                               started: datetime.datetime=None, finished: datetime.datetime=None,
                               status: const.ResourceState=None, messages: list=[], changes: dict={},
                               change: const.Change=None, send_events: bool=False):
        """
            Send a resource update to the server

            :param tid: The id of the environment this resource belongs to
            :param resource_ids: The resource with the given id from the agent
            :param action_id: A unique id to indicate the resource action that has be updated
            :param action: The action performed
            :param started: The timestamp when this action was started. When this action (action_id) has not been saved yet,
                            started has to be defined.
            :param finished: The timestamp when this action was finished. Afterwards, no changes with the same action_id
                            can be stored. The status field also has to be set.
            :param status: The current status of the resource (if known)
            :param messages: A list of log entries to add to this entry.
            :param change:s A dict of changes to this resource. The key of this dict indicates the attributes/fields that
                           have been changed. The value contains the new value and/or the original value.
            :param change: The result of the changes
            :param send_events: Send events to the dependents of this resource
        """


class VersionMethod(Method):
    """
        Manage configuration model versions
    """
    __method_name__ = "version"

    @protocol(index=True, operation="GET", arg_options=ENV_OPTS, client_types=["api"])
    def list_versions(self, tid: uuid.UUID, start: int=None, limit: int=None):
        """
            Returns a list of all available versions

            :param tid: The id of the environment
            :param start: Optional, parameter to control the amount of results that are returned. 0 is the latest version.
            :param limit: Optional, parameter to control the amount of results returned.
        """

    @protocol(operation="GET", id=True, arg_options=ENV_OPTS, client_types=["api"])
    def get_version(self, tid: uuid.UUID, id: int, include_logs: bool=None, log_filter: str=None, limit: int=None):
        """
            Get a particular version and a list of all resources in this version

            :param tid: The id of the environment
            :param id: The id of the version to retrieve
            :param include_logs: If true, a log of all operations on all resources is included
            :param log_filter: Filter log to only include actions of the specified type
            :param limit: The maximal number of actions to return per resource (starting from the latest)
        """

    @protocol(operation="DELETE", id=True, arg_options=ENV_OPTS, client_types=["api"])
    def delete_version(self, tid: uuid.UUID, id: int):
        """
            Delete a particular version and resources

            :param tid: The id of the environment
            :param id: The id of the version to retrieve
        """

    @protocol(operation="PUT", arg_options=ENV_OPTS, client_types=["compiler"])
    def put_version(self, tid: uuid.UUID, version: int, resources: list, resource_state: dict={}, unknowns: list=None,
                    version_info: dict=None):
        """
            Store a new version of the configuration model

            :param tid: The id of the environment
            :param version: The version of the configuration model
            :param resources: A list of all resources in the configuration model (deployable)
            :param resource_state: A dictionary with the initial const.ResourceState per resource id
            :param unknowns: A list of unknown parameters that caused the model to be incomplete
            :param version_info: Module version information
        """

    @protocol(operation="POST", id=True, arg_options=ENV_OPTS, client_types=["api", "compiler"])
    def release_version(self, tid: uuid.UUID, id: int, push: bool):
        """
            Release version of the configuration model for deployment.

            :param tid: The id of the environment
            :param id: The version of the CM to deploy
            :param push: Notify all agents to deploy the version
        """


class DryRunMethod(Method):
    """
        Method for requesting and quering a dryrun
    """
    __method_name__ = "dryrun"

    @protocol(operation="POST", id=True, arg_options=ENV_OPTS, client_types=["api"])
    def dryrun_request(self, tid: uuid.UUID, id: int):
        """
            Do a dryrun

            :param tid: The id of the environment
            :param id: The version of the CM to deploy
        """

    @protocol(operation="GET", arg_options=ENV_OPTS, client_types=["api"])
    def dryrun_list(self, tid: uuid.UUID, version: int=None):
        """
            Create a list of dry runs

            :param tid: The id of the environment
            :param version: Only for this version
        """

    @protocol(operation="GET", id=True, arg_options=ENV_OPTS, client_types=["api"])
    def dryrun_report(self, tid: uuid.UUID, id: uuid.UUID):
        """
            Create a dryrun report

            :param tid: The id of the environment
            :param id: The version dryrun to report
        """

    @protocol(operation="PUT", id=True, agent_server=True, arg_options=ENV_OPTS, client_types=["agent"])
    def dryrun_update(self, tid: uuid.UUID, id: uuid.UUID, resource: str, changes: dict):
        """
            Store dryrun results at the server

            :param tid: The id of the environment
            :param id: The version dryrun to report
            :param resource: The id of the resource
            :param changes: The required changes
        """


class AgentDryRun(Method):
    """
        Method for requesting a dryrun from an agent
    """
    __method_name__ = "agent_dryrun"

    @protocol(operation="POST", id=True, server_agent=True, timeout=5, arg_options=AGENT_ENV_OPTS, client_types=[])
    def do_dryrun(self, tid: uuid.UUID, id: uuid.UUID, agent: str, version: int):
        """
            Do a dryrun on an agent

            :param tid: The environment id
            :param id: The id of the dryrun
            :param agent: The agent to do the dryrun for
            :param version: The version of the model to dryrun
        """


class NotifyMethod(Method):
    """
        Method to notify the server of changes in the configuration model source code
    """
    __method_name__ = "notify"

    @protocol(operation="GET", id=True, arg_options={"id": {"getter": get_environment}}, client_types=["api"])
    def notify_change_get(self, id: uuid.UUID, update: bool=True):
        """
            Simplified GET version of the POST method
        """

    @protocol(operation="POST", id=True, arg_options={"id": {"getter": get_environment}}, client_types=["api"])
    def notify_change(self, id: uuid.UUID, update: bool=True, metadata: dict={}):
        """
            Notify the server that the repository of the environment with the given id, has changed.

            :param id: The id of the environment
            :param update: Update the model code and modules. Default value is true
            :param metadata: The metadata that indicates the source of the compilation trigger.
        """

    @protocol(operation="HEAD", id=True, client_types=["api"])
    def is_compiling(self, id: uuid.UUID):
        """
           Is a compiler running for the given environment

           :param id: The environment id
        """


class ParameterMethod(Method):
    """
        Get and set parameters on the server
    """
    __method_name__ = "parameter"

    @protocol(operation="GET", id=True, arg_options=ENV_OPTS, client_types=["api", "compiler", "agent"])
    def get_param(self, tid: uuid.UUID, id: str, resource_id: str=None):
        """
            Get a parameter from the server.

            :param tid: The id of the environment
            :param id: The name of the parameter
            :param resource_id: Optionally, scope the parameter to resource (fact)
            :return: Returns the following status codes:
                    200: The parameter content is returned
                    404: The parameter is not found and unable to find it because its resource is not known to the server
                    410: The parameter has expired
                    503: The parameter is not found but its value is requested from an agent
        """

    @protocol(operation="PUT", id=True, arg_options=ENV_OPTS, client_types=["api", "compiler", "agent"])
    def set_param(self, tid: uuid.UUID, id: str, source: str, value: str, resource_id: str=None, metadata: dict={},
                  recompile: bool=False):
        """
            Set a parameter on the server. If the parameter is an tracked unknown, it will trigger a recompile on the server.
            Otherwise, if the value is changed and recompile is true, a recompile is also triggered.

            :param tid: The id of the environment
            :param id: The name of the parameter
            :param resource_id: Optionally, scope the parameter to resource (fact)
            :param source: The source of the parameter, this can be the user, agent, plugin, compiler, ...
            :param value: The value of the parameter
            :param metadata: metadata about the parameter
            :param recompile: Whether to trigger a recompile
        """

    @protocol(operation="DELETE", id=True, arg_options=ENV_OPTS, client_types=["api", "compiler", "agent"])
    def delete_param(self, tid: uuid.UUID, id: str, resource_id: str=None):
        """
            Delete a parameter on the server

            :param tid: The id of the environment
            :param id: The name of the parameter
            :param resource_id: The resource id of the parameter
        """

    @protocol(operation="POST", index=True, arg_options=ENV_OPTS, client_types=["api", "compiler"])
    def list_params(self, tid: uuid.UUID, query: dict={}):
        """
            List/query parameters in this environment

            :param tid: The id of the environment
            :param query: A query to match against metadata
        """


class ParametersMethod(Method):
    """
        Get and set parameters on the server
    """
    __method_name__ = "parameters"

    @protocol(operation="PUT", index=True, agent_server=True, arg_options=ENV_OPTS, client_types=["api", "compiler", "agent"])
    def set_parameters(self, tid: uuid.UUID, parameters: list):
        """
            Set a parameter on the server

            :param tid: The id of the environment
            :param parameters: A list of dicts with the following keys:
                - id The name of the parameter
                - source The source of the parameter, this can be the user, agent, plugin, compiler, ...
                - value The value of the parameter
                - resource_id Optionally, scope the parameter to resource (fact)
                - metadata metadata about the parameter
        """


class AgentParameterMethod(Method):
    """
        Get parameters from the agent
    """
    __method_name__ = "agent_parameter"

    @protocol(operation="POST", server_agent=True, timeout=5, arg_options=AGENT_ENV_OPTS, client_types=[])
    def get_parameter(self, tid: uuid.UUID, agent: str, resource: dict):
        """
            Get all parameters/facts known by the agents for the given resource

            :param tid: The environment
            :param agent: The agent get the parameters froms
            :param resource: The resource to query the parameters from
        """


class FormMethod(Method):
    """
        Methods for creating and manipulating forms
    """
    __method_name__ = "form"

    @protocol(operation="GET", index=True, arg_options=ENV_OPTS, client_types=["api", "compiler"])
    def list_forms(self, tid: uuid.UUID):
        """
            List all available forms in an environment
        """

    @protocol(operation="GET", id=True, arg_options=ENV_OPTS, client_types=["api", "compiler"])
    def get_form(self, tid: uuid.UUID, id: str):
        """
            Get a form
        """

    @protocol(operation="PUT", id=True, arg_options=ENV_OPTS, client_types=["api", "compiler"])
    def put_form(self, tid: uuid.UUID, id: str, form: dict):
        """
            Upload a form
        """


class FormRecords(Method):
    """
        Methods for working with form records
    """
    __method_name__ = "records"

    @protocol(operation="GET", index=True, arg_options=ENV_OPTS, client_types=["api", "compiler"])
    def list_records(self, tid: uuid.UUID, form_type: str, include_record: bool=False):
        """
            Get a list of all records of a specific form

            :param tid: The id of the environment
            :param form_type: The type of the form
            :param include_record: Include all the data contained in the record as well
        """

    @protocol(operation="GET", id=True, arg_options=ENV_OPTS, client_types=["api", "compiler"])
    def get_record(self, tid: uuid.UUID, id: uuid.UUID):
        """
            Get a record from the server

            :param tid: The id of the environment
            :param record_id: The id of the record
        """

    @protocol(operation="PUT", id=True, arg_options=ENV_OPTS, client_types=["api", "compiler"])
    def update_record(self, tid: uuid.UUID, id: uuid.UUID, form: dict):
        """
            Update a record

            :param tid: The id of the environment
            :param id: The id of the record
            :param form: The values of each field
        """

    @protocol(operation="POST", index=True, arg_options=ENV_OPTS, client_types=["api", "compiler"])
    def create_record(self, tid: uuid.UUID, form_type: str, form: dict):
        """
            Get a list of all records of a specific form

            :param tid: The id of the environment
            :param form_type: The type of the form
            :param form: The values for each field
        """

    @protocol(operation="DELETE", id=True, arg_options=ENV_OPTS, client_types=["api", "compiler"])
    def delete_record(self, tid: uuid.UUID, id: uuid.UUID):
        """
            Delete a record

            :param tid: The id of the environment
            :param id: The id of the record
        """


class CodeMethod(Method):
    """
        Upload code to the server
    """
    __method_name__ = "code"

    @protocol(operation="PUT", id=True, arg_options=ENV_OPTS, client_types=["compiler"])
    def upload_code(self, tid: uuid.UUID, id: int, resource: str, sources: dict):
        """
            Upload the supporting code to the server

            :param tid: The environment the code belongs to
            :param id: The id (version) of the configuration model
            :param sources: The source files that contain handlers and inmanta plug-ins
                {code_hash:(file_name, provider.__module__, source_code, [req])}
        """

    @protocol(operation="GET", id=True, agent_server=True, arg_options=ENV_OPTS, client_types=["agent"])
    def get_code(self, tid: uuid.UUID, id: int, resource: str):
        """
            Get the code for a given version of the configuration model

            :param tid: The environment the code belongs to
            :param id: The id (version) of the configuration model
        """


class CodeBatchedMethod(Method):
    """
        Upload code to the server
    """
    __method_name__ = "codebatched"

    @protocol(operation="PUT", id=True, arg_options=ENV_OPTS, client_types=["compiler"])
    def upload_code_batched(self, tid: uuid.UUID, id: int, resources: dict):
        """
            Upload the supporting code to the server

            :param tid: The environment the code belongs to
            :param id: The id (version) of the configuration model
            :param resource: a dict mapping resources to dicts mapping file names to file hashes
        """


class FileDiff(Method):
    """
        Generate download the diff of two hashes
    """
    __method_name__ = "filediff"

    @protocol(client_types=["api"])
    def diff(self, a: str, b: str):
        """
            Returns the diff of the files with the two given ids
        """


class CompileReport(Method):
    """
        Get a list of compile reports
    """
    __method_name__ = "compilereport"

    @protocol(operation="GET", index=True, arg_options=ENV_OPTS, client_types=["api"])
    def get_reports(self, tid: uuid.UUID, start: str=None, end: str=None, limit: int=None):
        """
            Return compile reports newer then start

            :param tid: The id of the environment to get a report from
            :param start: Reports after start
            :param end: Reports before end
            :param limit: Maximum number of results
        """

    @protocol(operation="GET", id=True, client_types=["api"])
    def get_report(self, id: uuid.UUID):
        """
            Get a compile report from the server

            :param compile_id: The id of the compile and its reports to fetch.
        """


class Snapshot(Method):
    """
        Methods to create and restore snapshots
    """
    __method_name__ = "snapshot"

    @protocol(operation="GET", index=True, arg_options=ENV_OPTS, client_types=["api"])
    def list_snapshots(self, tid: uuid.UUID):
        """
            Create a list of all snapshots
        """

    @protocol(operation="GET", id=True, arg_options=ENV_OPTS, client_types=["api"])
    def get_snapshot(self, tid: uuid.UUID, id: uuid.UUID):
        """
            Get details about a snapshot and a list of resources that can be snapshot-ed
        """

    @protocol(operation="POST", index=True, arg_options=ENV_OPTS, client_types=["api"])
    def create_snapshot(self, tid: uuid.UUID, name: str=None):
        """
            Request a new snapshot
        """

    @protocol(operation="PUT", id=True, agent_server=True, arg_options=ENV_OPTS, client_types=["agent"])
    def update_snapshot(self, tid: uuid.UUID, id: uuid.UUID, resource_id: str, snapshot_data: str, error: bool, success: bool,
                        start: datetime.datetime, stop: datetime.datetime, size: int, msg: str=None):
        """
            Update a snapshot with the details of a specific resource

            :param tid :The environment the snapshot is created in
            :param id: The id of the snapshot to update
            :param resource_id: The id of the resource of which a snapshot was created
            :param snapshot_data: The hash of the snapshot data that was uploaded to the fileserver
            :param start: The time when the snapshot was started
            :param stop: The time the snapshot ended
            :param size: The size of the snapshot in bytes
            :param msg: An optional message about the snapshot
        """

    @protocol(operation="DELETE", id=True, arg_options=ENV_OPTS, client_types=["api"])
    def delete_snapshot(self, tid: uuid.UUID, id: uuid.UUID):
        """
            Delete a snapshot
        """


class AgentSnapshot(Method):
    """
        Snapshot operations performed on the agent
    """
    __method_name__ = "agent_snapshot"

    @protocol(operation="POST", server_agent=True, timeout=5, arg_options=AGENT_ENV_OPTS, client_types=[])
    def do_snapshot(self, tid: uuid.UUID, agent: str, snapshot_id: uuid.UUID, resources: list):
        """
            Create a snapshot of the requested resource

            :param tid The environment the snapshot is created in
            :param agent The name of the agent
            :param snapshot_id The id of the snapshot to create
            :param resource A list of resources to snapshot
        """


class RestoreSnapshot(Method):
    """
        Restore a snapshot
    """
    __method_name__ = "restore"

    @protocol(operation="POST", index=True, arg_options=ENV_OPTS, client_types=["api"])
    def restore_snapshot(self, tid: uuid.UUID, snapshot: uuid.UUID):
        """
            Restore a snapshot

            :param tid: The environment the snapshot is created in
            :param snapshot: The id of the snapshot to restore
        """

    @protocol(operation="POST", id=True, agent_server=True, arg_options=ENV_OPTS, client_types=["agent"])
    def update_restore(self, tid: uuid.UUID, id: uuid.UUID, resource_id: str, success: bool, error: bool, msg: str,
                       start: datetime.datetime, stop: datetime.datetime):
        """
            Update the status of a restore

            :param tid: The environment to restore the snapshot in
            :param id: The id of the restore
            :param resource_id: The state id of the resource that was restored.
        """

    @protocol(operation="GET", index=True, arg_options=ENV_OPTS, client_types=["api"])
    def list_restores(self, tid: uuid.UUID):
        """
            List finished and ongoing restores
        """

    @protocol(operation="GET", id=True, arg_options=ENV_OPTS, client_types=["api"])
    def get_restore_status(self, tid: uuid.UUID, id: uuid.UUID):
        """
            Get the status of a restore
        """

    @protocol(operation="DELETE", id=True, arg_options=ENV_OPTS, client_types=["api"])
    def delete_restore(self, tid: uuid.UUID, id: uuid.UUID):
        """
            Cancel a restore
        """


class AgentRestore(Method):
    """
        Snapshot operations performed on the agent
    """
    __method_name__ = "agent_restore"

    @protocol(operation="POST", server_agent=True, timeout=5, arg_options=AGENT_ENV_OPTS, client_types=[])
    def do_restore(self, tid: uuid.UUID, agent: str, restore_id: uuid.UUID, snapshot_id: uuid.UUID, resources: list):
        """
            Create a snapshot of the requested resource

            :param tid: The environment the snapshot is created in
            :param agent: The name of the agent
            :param restore_id: THe id of the restore operation
            :param snapshot_id: The id of the snapshot to restore
            :param resource: A list of resources to restore
        """


class NodeMethod(Method):
    """
        Get a list of all agents
    """
    __method_name__ = "agentproc"

    @protocol(operation="GET", index=True, client_types=["api"])
    def list_agent_processes(self, environment: uuid.UUID=None, expired: bool=True):
        """
            Return a list of all nodes and the agents for these nodes

            :param environment: An optional environment. If set, only the agents that belong to this environment are returned
            :param all: Optional, also show expired.
            :return: A list of nodes
        """

    @protocol(operation="GET", id=True, client_types=["api"])
    def get_agent_process(self, id: uuid.UUID):
        """
            Return a detailed report for a node

            :param agentid: The id of the node
            :return: The requested node
        """


class ServerAgentApiMethod(Method):
    """
        Get a list of all agents
    """
    __method_name__ = "agent"

    @protocol(operation="POST", id=True, api=True, timeout=5, arg_options=ENV_OPTS, client_types=["api"])
    def trigger_agent(self, tid: uuid.UUID, id: str):
        """
            Request the server to reload an agent

            :param tid The environment this agent is defined in
            :param id The name of the agent
            :return The requested node
        """

    @protocol(operation="GET", api=True, timeout=5, arg_options=ENV_OPTS, client_types=["api"])
    def list_agents(self, tid: uuid.UUID):
        """
            List all agent for an environment

            :param tid The environment the agents are defined in
        """


class AgentReporting(Method):
    """
        Reporting by the agent to the server
    """
    __method_name__ = "status"

    @protocol(operation="GET", server_agent=True, timeout=5, client_types=[])
    def get_status(self):
        """
            A call from the server to the agent to report its status to the server

            :return: A map with report items
        """


class AgentState(Method):
    """
        Methods to allow the server to set the agents state
    """
    __method_name__ = "agentstate"

    @protocol(operation="POST", server_agent=True, timeout=5, client_types=[])
    def set_state(self, agent: str, enabled: bool):
        """
            Set the state of the agent.
        """

    @protocol(operation="POST", id=True, server_agent=True, timeout=5, arg_options=AGENT_ENV_OPTS, client_types=[])
    def trigger(self, tid: uuid.UUID, id: str):
        """
            Request an agent to reload resources

            :param tid The environment this agent is defined in
            :param id The name of the agent
        """


class AgentResourceEvent(Method):
    """
        Methods to send event to the server
    """
    __method_name__ = "event"

    @protocol(operation="PUT", id=True, server_agent=True, timeout=5, arg_options=AGENT_ENV_OPTS, client_types=[])
    def resource_event(self, tid: uuid.UUID, id: str, resource: str, send_events: bool,
                       state: const.ResourceState, change: const.Change, changes={}):
        """
            Tell an agent a resource it waits for has been updated

            :param tid The environment this agent is defined in
            :param id The name of the agent
            :param resource The resource ID of the resource being updated
            :param send_events Does the resource have send_events enabled?
            :param state State the resource acquired (deployed, skipped, canceled)
            :param change The change that was made to the resource
            :param changes The changes made to the resource
        """


class AgentRecovery(Method):
    """
        Methods for the agent to get its initial state from the server
    """
    __method_name__ = "agentrecovery"

    @protocol(operation="GET", agent_server=True, arg_options=ENV_OPTS, client_types=["agent"])
    def get_state(self, tid: uuid.UUID, sid: uuid.UUID, agent: str):
        """
            Get the state for this agent.

            returns a map
            {
             enabled: bool
            }
        """
