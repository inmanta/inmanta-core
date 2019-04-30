"""
    Copyright 2019 Inmanta

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

import uuid
import datetime

from inmanta import data, const
from .common import ArgOption
from .decorators import method
from . import exceptions
from tornado import gen

from typing import Any


@gen.coroutine
def convert_environment(env: uuid.UUID, metadata: dict) -> data.Environment:
    metadata[const.INMANTA_URN + "env"] = str(env)
    env = yield data.Environment.get_by_id(env)
    if env is None:
        raise exceptions.NotFound("the given environment id does not exist!")
    return env


@gen.coroutine
def add_env(env: uuid.UUID, metadata: dict) -> uuid.UUID:
    metadata[const.INMANTA_URN + "env"] = str(env)
    return env


@gen.coroutine
def ignore_env(obj: Any, metadata: dict) -> Any:
    """
        This mapper only adds an env all for authz
    """
    metadata[const.INMANTA_URN + "env"] = "all"
    return obj


ENV_OPTS = {"tid": ArgOption(header=const.INMANTA_MT_HEADER, reply_header=True, getter=convert_environment)}
AGENT_ENV_OPTS = {"tid": ArgOption(header=const.INMANTA_MT_HEADER, reply_header=True, getter=add_env)}


# Method for working with projects


@method(method_name="project", operation="PUT", client_types=["api"])
def create_project(name: str, project_id: uuid.UUID = None):
    """
        Create a new project

        :param name: The name of the project
        :param project_id: A unique uuid, when it is not provided the server generates one
    """


@method(method_name="project", operation="POST", id=True, client_types=["api"])
def modify_project(id: uuid.UUID, name: str):
    """
        Modify the given project
    """


@method(method_name="project", operation="DELETE", id=True, client_types=["api"])
def delete_project(id: uuid.UUID):
    """
        Delete the given project and all related data
    """


@method(method_name="project", operation="GET", index=True, client_types=["api"])
def list_projects():
    """
        Create a list of projects
    """


@method(method_name="project", operation="GET", id=True, client_types=["api"])
def get_project(id: uuid.UUID):
    """
        Get a project and a list of the ids of all environments
    """


# Methods for working with environments
@method(method_name="environment", operation="PUT", client_types=["api"])
def create_environment(
        project_id: uuid.UUID, name: str, repository: str = None, branch: str = None, environment_id: uuid.UUID = None
):
    """
        Create a new environment

        :param project_id: The id of the project this environment belongs to
        :param name: The name of the environment
        :param repository: The url (in git form) of the repository
        :param branch: The name of the branch in the repository
        :param environment_id: A unique environment id, if none an id is allocated by the server
    """


@method(method_name="environment", operation="POST", id=True, client_types=["api"])
def modify_environment(id: uuid.UUID, name: str, repository: str = None, branch: str = None):
    """
        Modify the given environment

        :param id: The id of the environment
        :param name: The name of the environment
        :param repository: The url (in git form) of the repository
        :param branch: The name of the branch in the repository
    """


@method(method_name="environment", operation="DELETE", id=True, client_types=["api"])
def delete_environment(id: uuid.UUID):
    """
        Delete the given environment and all related data
    """


@method(method_name="environment", operation="GET", index=True, client_types=["api"])
def list_environments():
    """
        Create a list of environments
    """


@method(
    method_name="environment", operation="GET", id=True, client_types=["api"], arg_options={"id": ArgOption(getter=add_env)}
)
def get_environment(id: uuid.UUID, versions: int = None, resources: int = None):
    """
        Get an environment and all versions associated

        :param id: The id of the environment to return
        :param versions: Include this many available version for this environment.
        :param resources: Include this many available resources for this environment.
    """


# Method for listing/getting/setting/removing settings of an environment. This API is also used by agents to configure
# environments.


@method(
    method_name="environment_settings",
    operation="GET",
    index=True,
    arg_options=ENV_OPTS,
    api=True,
    agent_server=True,
    client_types=["api", "agent", "compiler"],
)
def list_settings(tid: uuid.UUID):
    """
        List the settings in the current environment
    """


@method(
    method_name="environment_settings",
    operation="POST",
    id=True,
    arg_options=ENV_OPTS,
    api=True,
    agent_server=True,
    client_types=["api", "agent", "compiler"],
)
def set_setting(tid: uuid.UUID, id: str, value: object):
    """
        Set a value
    """


@method(
    method_name="environment_settings",
    operation="GET",
    id=True,
    arg_options=ENV_OPTS,
    api=True,
    agent_server=True,
    client_types=["api", "agent"],
)
def get_setting(tid: uuid.UUID, id: str):
    """
        Get a value
    """


@method(
    method_name="environment_settings",
    operation="DELETE",
    id=True,
    arg_options=ENV_OPTS,
    api=True,
    agent_server=True,
    client_types=["api", "agent"],
)
def delete_setting(tid: uuid.UUID, id: str):
    """
        Delete a value
    """


# Method for listing and creating auth tokens for an environment that can be used by the agent and compilers


@method(method_name="environment_auth", operation="POST", index=True, arg_options=ENV_OPTS, client_types=["api", "compiler"])
def create_token(tid: uuid.UUID, client_types: list, idempotent: bool = True):
    """
        Create or get a new token for the given client types. Tokens generated with this call are scoped to the current
        environment.

        :param tid: The environment id
        :param client_types: The client types for which this token is valid (api, agent, compiler)
        :param idempotent: The token should be idempotent, such tokens do not have an expire or issued at set so their
                           value will not change.
    """


#  Decomission an environment


@method(
    method_name="decommission",
    operation="POST",
    id=True,
    arg_options={"id": ArgOption(getter=convert_environment)},
    client_types=["api"],
)
def decomission_environment(id: uuid.UUID, metadata: dict = None):
    """
        Decommision an environment. This is done by uploading an empty model to the server and let purge_on_delete handle
        removal.
    """


@method(
    method_name="decommission",
    operation="DELETE",
    id=True,
    arg_options={"id": ArgOption(getter=convert_environment)},
    client_types=["api"],
)
def clear_environment(id: uuid.UUID):
    """
        Clear all data from this environment
    """


# Send a heartbeat to indicate that an agent is alive
@method(
    method_name="heartbeat",
    operation="POST",
    agent_server=True,
    validate_sid=False,
    arg_options=ENV_OPTS,
    client_types=["agent"],
)
def heartbeat(sid: uuid.UUID, tid: uuid.UUID, endpoint_names: list, nodename: str):
    """
        Send a heartbeat to the server

        :paran sid: The session ID used by this agent at this moment
        :param tid: The environment this node and its agents belongs to
        :param endpoint_names: The names of the endpoints on this node
        :param nodename: The name of the node from which the heart beat comes

        also registered as API method, because it is called with an invalid SID the first time
    """


@method(
    method_name="heartbeat",
    operation="PUT",
    agent_server=True,
    arg_options={"sid": ArgOption(getter=ignore_env)},
    client_types=["agent"],
)
def heartbeat_reply(sid: uuid.UUID, reply_id: uuid.UUID, data: dict):
    """
        Send a reply back to the server

        :param sid: The session ID used by this agent at this moment
        :param reply_id: The id data is a reply to
        :param data: The data as a response to the reply
    """


# Upload, retrieve and check for file. A file is identified by a hash of its content.


@method(
    method_name="file",
    operation="PUT",
    id=True,
    agent_server=True,
    api=True,
    client_types=["api", "agent", "compiler"],
    arg_options={"id": ArgOption(getter=ignore_env)},
)
def upload_file(id: str, content: str):
    """
        Upload a new file

        :param id The id of the file
        :param content The base64 encoded content of the file
    """


@method(
    method_name="file",
    operation="HEAD",
    id=True,
    agent_server=True,
    api=True,
    client_types=["api", "agent", "compiler"],
    arg_options={"id": ArgOption(getter=ignore_env)},
)
def stat_file(id: str):
    """
        Does the file exist

        :param id The id of the file to check
    """


@method(
    method_name="file",
    operation="GET",
    id=True,
    agent_server=True,
    api=True,
    client_types=["api", "agent", "compiler"],
    arg_options={"id": ArgOption(getter=ignore_env)},
)
def get_file(id: str):
    """
        Retrieve a file

        :param id: The id of the file to retrieve
    """


@method(
    method_name="file", api=True, client_types=["api", "agent", "compiler"], arg_options={"files": ArgOption(getter=ignore_env)}
)
def stat_files(files: list):
    """
        Check which files exist in the given list

        :param files: A list of file id to check
        :return: A list of files that do not exist.
    """


# Manage resources on the server


@method(
    method_name="resource",
    operation="GET",
    id=True,
    agent_server=True,
    validate_sid=False,
    arg_options=ENV_OPTS,
    api=True,
    client_types=["api", "agent"],
)
def get_resource(
    tid: uuid.UUID, id: str, logs: bool = None, status: bool = None, log_action: const.ResourceAction = None, log_limit: int = 0
):
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


@method(method_name="resource", operation="GET", index=True, agent_server=True, arg_options=ENV_OPTS, client_types=["agent"])
def get_resources_for_agent(
    tid: uuid.UUID,
    agent: str,
    sid: uuid.UUID = None,
    version: int = None,
    incremental_deploy: bool = False
):
    """
        Return the most recent state for the resources associated with agent, or the version requested

        :param tid: The id of the environment this resource belongs to
        :param agent: The agent
        :param sid: Session id of the agent (transparently added by agent client)
        :param version: The version to retrieve. If none, the latest available version is returned. With a specific version
                        that version is returned, even if it has not been released yet.
        :param incremental_deploy: Indicates whether the server should only return the resources that changed since the
                                   previous deployment.
    """


@method(method_name="resource", operation="POST", index=True, agent_server=True, arg_options=ENV_OPTS, client_types=["agent"])
def resource_action_update(
    tid: uuid.UUID,
    resource_ids: list,
    action_id: uuid.UUID,
    action: const.ResourceAction,
    started: datetime.datetime = None,
    finished: datetime.datetime = None,
    status: const.ResourceState = None,
    messages: list = [],
    changes: dict = {},
    change: const.Change = None,
    send_events: bool = False,
):
    """
        Send a resource update to the server

        :param tid: The id of the environment this resource belongs to
        :param resource_ids: The resource with the given resource_version_id id from the agent
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


# Manage configuration model versions


@method(method_name="version", index=True, operation="GET", arg_options=ENV_OPTS, client_types=["api"])
def list_versions(tid: uuid.UUID, start: int = None, limit: int = None):
    """
        Returns a list of all available versions

        :param tid: The id of the environment
        :param start: Optional, parameter to control the amount of results that are returned. 0 is the latest version.
        :param limit: Optional, parameter to control the amount of results returned.
    """


@method(method_name="version", operation="GET", id=True, arg_options=ENV_OPTS, client_types=["api"])
def get_version(tid: uuid.UUID, id: int, include_logs: bool = None, log_filter: str = None, limit: int = None):
    """
        Get a particular version and a list of all resources in this version

        :param tid: The id of the environment
        :param id: The id of the version to retrieve
        :param include_logs: If true, a log of all operations on all resources is included
        :param log_filter: Filter log to only include actions of the specified type
        :param limit: The maximal number of actions to return per resource (starting from the latest)
    """


@method(method_name="version", operation="DELETE", id=True, arg_options=ENV_OPTS, client_types=["api"])
def delete_version(tid: uuid.UUID, id: int):
    """
        Delete a particular version and resources

        :param tid: The id of the environment
        :param id: The id of the version to retrieve
    """


@method(method_name="version", operation="PUT", arg_options=ENV_OPTS, client_types=["compiler"])
def put_version(
    tid: uuid.UUID, version: int, resources: list, resource_state: dict = {}, unknowns: list = None, version_info: dict = None
):
    """
        Store a new version of the configuration model

        :param tid: The id of the environment
        :param version: The version of the configuration model
        :param resources: A list of all resources in the configuration model (deployable)
        :param resource_state: A dictionary with the initial const.ResourceState per resource id
        :param unknowns: A list of unknown parameters that caused the model to be incomplete
        :param version_info: Module version information
    """


@method(method_name="version", operation="POST", id=True, arg_options=ENV_OPTS, client_types=["api", "compiler"])
def release_version(tid: uuid.UUID, id: int, push: bool = False, agent_trigger_method: const.AgentTriggerMethod = None):
    """
        Release version of the configuration model for deployment.

        :param tid: The id of the environment
        :param id: The version of the CM to deploy
        :param push: Notify all agents to deploy the version
        :param agent_trigger_method Indicates whether the agents should perform a full or an incremental deploy when
                                    push is true.
    """


@method(method_name="deploy", operation="POST", arg_options=ENV_OPTS, client_types=["api"])
def deploy(tid: uuid.UUID, agent_trigger_method: const.AgentTriggerMethod = const.AgentTriggerMethod.push_full_deploy,
           agents: list = None):
    """
        Notify agents to perform a deploy now.

        :param tid: The id of the environment.
        :param agent_trigger_method: Indicates whether the agents should perform a full or an incremental deploy.
        :param agents: Optional, names of specific agents to trigger
    """


# Method for requesting and quering a dryrun


@method(method_name="dryrun", operation="POST", id=True, arg_options=ENV_OPTS, client_types=["api"])
def dryrun_request(tid: uuid.UUID, id: int):
    """
        Do a dryrun

        :param tid: The id of the environment
        :param id: The version of the CM to deploy
    """


@method(method_name="dryrun", operation="GET", arg_options=ENV_OPTS, client_types=["api"])
def dryrun_list(tid: uuid.UUID, version: int = None):
    """
        Create a list of dry runs

        :param tid: The id of the environment
        :param version: Only for this version
    """


@method(method_name="dryrun", operation="GET", id=True, arg_options=ENV_OPTS, client_types=["api"])
def dryrun_report(tid: uuid.UUID, id: uuid.UUID):
    """
        Create a dryrun report

        :param tid: The id of the environment
        :param id: The version dryrun to report
    """


@method(method_name="dryrun", operation="PUT", id=True, agent_server=True, arg_options=ENV_OPTS, client_types=["agent"])
def dryrun_update(tid: uuid.UUID, id: uuid.UUID, resource: str, changes: dict):
    """
        Store dryrun results at the server

        :param tid: The id of the environment
        :param id: The version dryrun to report
        :param resource: The id of the resource
        :param changes: The required changes
    """


# Method for requesting a dryrun from an agent


@method(
    method_name="agent_dryrun",
    operation="POST",
    id=True,
    server_agent=True,
    timeout=5,
    arg_options=AGENT_ENV_OPTS,
    client_types=[],
)
def do_dryrun(tid: uuid.UUID, id: uuid.UUID, agent: str, version: int):
    """
        Do a dryrun on an agent

        :param tid: The environment id
        :param id: The id of the dryrun
        :param agent: The agent to do the dryrun for
        :param version: The version of the model to dryrun
        """


# Method to notify the server of changes in the configuration model source code


@method(
    method_name="notify",
    operation="GET",
    id=True,
    arg_options={"id": ArgOption(getter=convert_environment)},
    client_types=["api"],
)
def notify_change_get(id: uuid.UUID, update: bool = True):
    """
        Simplified GET version of the POST method
    """


@method(
    method_name="notify",
    operation="POST",
    id=True,
    arg_options={"id": ArgOption(getter=convert_environment)},
    client_types=["api"],
)
def notify_change(id: uuid.UUID, update: bool = True, metadata: dict = {}):
    """
        Notify the server that the repository of the environment with the given id, has changed.

        :param id: The id of the environment
        :param update: Update the model code and modules. Default value is true
        :param metadata: The metadata that indicates the source of the compilation trigger.
    """


@method(method_name="notify", operation="HEAD", id=True, client_types=["api"])
def is_compiling(id: uuid.UUID):
    """
       Is a compiler running for the given environment

       :param id: The environment id
    """


# Get and set parameters on the server


@method(method_name="parameter", operation="GET", id=True, arg_options=ENV_OPTS, client_types=["api", "compiler", "agent"])
def get_param(tid: uuid.UUID, id: str, resource_id: str = None):
    """
        Get a parameter from the server.

        :param tid: The id of the environment
        :param id: The name of the parameter
        :param resource_id: Optionally, scope the parameter to resource (fact),
                            if the resource id should not contain a version, the latest version is used
        :return: Returns the following status codes:
                200: The parameter content is returned
                404: The parameter is not found and unable to find it because its resource is not known to the server
                410: The parameter has expired
                503: The parameter is not found but its value is requested from an agent
    """


@method(method_name="parameter", operation="PUT", id=True, arg_options=ENV_OPTS, client_types=["api", "compiler", "agent"])
def set_param(
    tid: uuid.UUID, id: str, source: str, value: str, resource_id: str = None, metadata: dict = {}, recompile: bool = False
):
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


@method(method_name="parameter", operation="DELETE", id=True, arg_options=ENV_OPTS, client_types=["api", "compiler", "agent"])
def delete_param(tid: uuid.UUID, id: str, resource_id: str = None):
    """
        Delete a parameter on the server

        :param tid: The id of the environment
        :param id: The name of the parameter
        :param resource_id: The resource id of the parameter
    """


@method(method_name="parameter", operation="POST", index=True, arg_options=ENV_OPTS, client_types=["api", "compiler"])
def list_params(tid: uuid.UUID, query: dict = {}):
    """
        List/query parameters in this environment

        :param tid: The id of the environment
        :param query: A query to match against metadata
    """


#  Get and set parameters on the server


@method(
    method_name="parameters",
    operation="PUT",
    index=True,
    agent_server=True,
    arg_options=ENV_OPTS,
    client_types=["api", "compiler", "agent"],
)
def set_parameters(tid: uuid.UUID, parameters: list):
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


# Get parameters from the agent


@method(
    method_name="agent_parameter", operation="POST", server_agent=True, timeout=5, arg_options=AGENT_ENV_OPTS, client_types=[]
)
def get_parameter(tid: uuid.UUID, agent: str, resource: dict):
    """
        Get all parameters/facts known by the agents for the given resource

        :param tid: The environment
        :param agent: The agent get the parameters froms
        :param resource: The resource to query the parameters from
    """


# Methods for creating and manipulating forms


@method(method_name="form", operation="GET", index=True, arg_options=ENV_OPTS, client_types=["api", "compiler"])
def list_forms(tid: uuid.UUID):
    """
        List all available forms in an environment
    """


@method(method_name="form", operation="GET", id=True, arg_options=ENV_OPTS, client_types=["api", "compiler"])
def get_form(tid: uuid.UUID, id: str):
    """
        Get a form
    """


@method(method_name="form", operation="PUT", id=True, arg_options=ENV_OPTS, client_types=["api", "compiler"])
def put_form(tid: uuid.UUID, id: str, form: dict):
    """
        Upload a form
    """


# Methods for working with form records


@method(method_name="records", operation="GET", index=True, arg_options=ENV_OPTS, client_types=["api", "compiler"])
def list_records(tid: uuid.UUID, form_type: str, include_record: bool = False):
    """
        Get a list of all records of a specific form

        :param tid: The id of the environment
        :param form_type: The type of the form
        :param include_record: Include all the data contained in the record as well
    """


@method(method_name="records", operation="GET", id=True, arg_options=ENV_OPTS, client_types=["api", "compiler"])
def get_record(tid: uuid.UUID, id: uuid.UUID):
    """
        Get a record from the server

        :param tid: The id of the environment
        :param record_id: The id of the record
    """


@method(method_name="records", operation="PUT", id=True, arg_options=ENV_OPTS, client_types=["api", "compiler"])
def update_record(tid: uuid.UUID, id: uuid.UUID, form: dict):
    """
        Update a record

        :param tid: The id of the environment
        :param id: The id of the record
        :param form: The values of each field
    """


@method(method_name="records", operation="POST", index=True, arg_options=ENV_OPTS, client_types=["api", "compiler"])
def create_record(tid: uuid.UUID, form_type: str, form: dict):
    """
        Get a list of all records of a specific form

        :param tid: The id of the environment
        :param form_type: The type of the form
        :param form: The values for each field
    """


@method(method_name="records", operation="DELETE", id=True, arg_options=ENV_OPTS, client_types=["api", "compiler"])
def delete_record(tid: uuid.UUID, id: uuid.UUID):
    """
        Delete a record

        :param tid: The id of the environment
        :param id: The id of the record
    """


# Upload code to the server


@method(method_name="code", operation="PUT", id=True, arg_options=ENV_OPTS, client_types=["compiler"])
def upload_code(tid: uuid.UUID, id: int, resource: str, sources: dict):
    """
        Upload the supporting code to the server

        :param tid: The environment the code belongs to
        :param id: The id (version) of the configuration model
        :param sources: The source files that contain handlers and inmanta plug-ins
            {code_hash:(file_name, provider.__module__, source_code, [req])}
    """


@method(method_name="code", operation="GET", id=True, agent_server=True, arg_options=ENV_OPTS, client_types=["agent"])
def get_code(tid: uuid.UUID, id: int, resource: str):
    """
        Get the code for a given version of the configuration model

        :param tid: The environment the code belongs to
        :param id: The id (version) of the configuration model
    """


# Upload code to the server


@method(method_name="codebatched", operation="PUT", id=True, arg_options=ENV_OPTS, client_types=["compiler"])
def upload_code_batched(tid: uuid.UUID, id: int, resources: dict):
    """
        Upload the supporting code to the server

        :param tid: The environment the code belongs to
        :param id: The id (version) of the configuration model
        :param resource: a dict mapping resources to dicts mapping file names to file hashes
    """


# Generate download the diff of two hashes


@method(method_name="filediff", client_types=["api"])
def diff(a: str, b: str):
    """
        Returns the diff of the files with the two given ids
    """


# Get a list of compile reports


@method(method_name="compilereport", operation="GET", index=True, arg_options=ENV_OPTS, client_types=["api"])
def get_reports(tid: uuid.UUID, start: str = None, end: str = None, limit: int = None):
    """
        Return compile reports newer then start

        :param tid: The id of the environment to get a report from
        :param start: Reports after start
        :param end: Reports before end
        :param limit: Maximum number of results
    """


@method(method_name="compilereport", operation="GET", id=True, client_types=["api"])
def get_report(id: uuid.UUID):
    """
        Get a compile report from the server

        :param compile_id: The id of the compile and its reports to fetch.
    """


# Get a list of all agents


@method(method_name="agentproc", operation="GET", index=True, client_types=["api"])
def list_agent_processes(environment: uuid.UUID = None, expired: bool = True):
    """
        Return a list of all nodes and the agents for these nodes

        :param environment: An optional environment. If set, only the agents that belong to this environment are returned
        :param all: Optional, also show expired.
        :return: A list of nodes
    """


@method(method_name="agentproc", operation="GET", id=True, client_types=["api"])
def get_agent_process(id: uuid.UUID):
    """
        Return a detailed report for a node

        :param agent_sid: The session id of the agent
        :return: The requested node
    """


# Get a list of all agents
@method(method_name="agent", operation="POST", id=True, api=True, timeout=5, arg_options=ENV_OPTS, client_types=["api"])
def trigger_agent(tid: uuid.UUID, id: str):
    """
        Request the server to reload an agent

        :param tid The environment this agent is defined in
        :param id The name of the agent
        :return The requested node
    """


@method(method_name="agent", operation="GET", api=True, timeout=5, arg_options=ENV_OPTS, client_types=["api"])
def list_agents(tid: uuid.UUID):
    """
        List all agent for an environment

        :param tid The environment the agents are defined in
    """


# Reporting by the agent to the server


@method(method_name="status", operation="GET", server_agent=True, timeout=5, client_types=[])
def get_status():
    """
        A call from the server to the agent to report its status to the server

        :return: A map with report items
    """


# Methods to allow the server to set the agents state


@method(method_name="agentstate", operation="POST", server_agent=True, timeout=5, client_types=[])
def set_state(agent: str, enabled: bool):
    """
        Set the state of the agent.
    """


@method(
    method_name="agentstate",
    operation="POST",
    id=True,
    server_agent=True,
    timeout=5,
    arg_options=AGENT_ENV_OPTS,
    client_types=[],
)
def trigger(tid: uuid.UUID, id: str, incremental_deploy: bool):
    """
        Request an agent to reload resources

        :param tid The environment this agent is defined in
        :param id The name of the agent
        :param incremental_deploy Indicates whether the agent should perform an incremental deploy or a full deploy
    """


# Methods to send event to the server


@method(
    method_name="event", operation="PUT", id=True, server_agent=True, timeout=5, arg_options=AGENT_ENV_OPTS, client_types=[]
)
def resource_event(
    tid: uuid.UUID, id: str, resource: str, send_events: bool, state: const.ResourceState, change: const.Change, changes={}
):
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


# Methods for the agent to get its initial state from the server


@method(method_name="agentrecovery", operation="GET", agent_server=True, arg_options=ENV_OPTS, client_types=["agent"])
def get_state(tid: uuid.UUID, sid: uuid.UUID, agent: str):
    """
        Get the state for this agent.

        returns a map
        {
         enabled: bool
        }
    """
