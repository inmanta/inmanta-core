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

    Module defining the v1 rest api
"""

import datetime
import uuid
from typing import Any, Optional, Union

from inmanta import const, data, resources
from inmanta.data import model
from inmanta.types import JsonType, PrimitiveTypes

from . import exceptions
from .common import ArgOption
from .decorators import method, typedmethod


async def convert_environment(env: uuid.UUID, metadata: dict) -> "data.Environment":
    metadata[const.INMANTA_URN + "env"] = str(env)
    env = await data.Environment.get_by_id(env)
    if env is None:
        raise exceptions.NotFound("The given environment id does not exist!")
    return env


async def add_env(env: uuid.UUID, metadata: dict) -> uuid.UUID:
    metadata[const.INMANTA_URN + "env"] = str(env)
    return env


async def ignore_env(obj: Any, metadata: dict) -> Any:
    """
    This mapper only adds an env all for authz
    """
    metadata[const.INMANTA_URN + "env"] = "all"
    return obj


async def convert_resource_version_id(rvid: model.ResourceVersionIdStr, metadata: dict) -> "resources.Id":
    try:
        return resources.Id.parse_resource_version_id(rvid)
    except Exception:
        raise exceptions.BadRequest(f"Invalid resource version id: {rvid}")


ENV_OPTS: dict[str, ArgOption] = {
    "tid": ArgOption(header=const.INMANTA_MT_HEADER, reply_header=True, getter=convert_environment)
}
AGENT_ENV_OPTS = {"tid": ArgOption(header=const.INMANTA_MT_HEADER, reply_header=True, getter=add_env)}
RVID_OPTS = {"rvid": ArgOption(getter=convert_resource_version_id)}


# Method for working with projects
@method(path="/project", operation="PUT", client_types=[const.ClientType.api])
def create_project(name: str, project_id: uuid.UUID = None):
    """
    Create a new project

    :param name: The name of the project
    :param project_id: Optional. A unique uuid, when it is not provided the server generates one
    """


@method(path="/project/<id>", operation="POST", client_types=[const.ClientType.api])
def modify_project(id: uuid.UUID, name: str):
    """
    Modify the given project.

    :param id: The id of the project to modify.
    :param name: The new name for the project.
    """


@method(path="/project/<id>", operation="DELETE", client_types=[const.ClientType.api])
def delete_project(id: uuid.UUID):
    """
    Delete the given project and all related data.

    :param id: The id of the project to be deleted.
    """


@method(path="/project", operation="GET", client_types=[const.ClientType.api])
def list_projects():
    """
    Returns a list of projects ordered alphabetically by name. The environments within each project are also sorted by name.
    """


@method(path="/project/<id>", operation="GET", client_types=[const.ClientType.api])
def get_project(id: uuid.UUID):
    """
    Get a project and a list of the ids of all environments.

    :param id: The id of the project to retrieve.
    """


# Methods for working with environments
@method(path="/environment", operation="PUT", client_types=[const.ClientType.api])
def create_environment(
    project_id: uuid.UUID, name: str, repository: str = None, branch: str = None, environment_id: uuid.UUID = None
):
    """
    Create a new environment

    :param project_id: The id of the project this environment belongs to
    :param name: The name of the environment.
    :param repository: Optional. The URL of the repository.
    :param branch: Optional. The name of the branch in the repository.
    :param environment_id: Optional. A unique environment id, if none an id is allocated by the server.
    """


@method(path="/environment/<id>", operation="POST", client_types=[const.ClientType.api])
def modify_environment(id: uuid.UUID, name: str, repository: str = None, branch: str = None):
    """
    Modify the given environment.

    :param id: The id of the environment to modify.
    :param name: The new name for the environment.
    :param repository: Optional. The URL of the repository.
    :param branch: Optional. The name of the branch in the repository.

    If 'repository' or 'branch' is provided as None, the corresponding attribute of the environment remains unchanged.
    """


@method(path="/environment/<id>", operation="DELETE", client_types=[const.ClientType.api])
def delete_environment(id: uuid.UUID):
    """
    Delete the given environment and all related data.

    :param id: The id of the environment to be deleted.

    :raises NotFound: The given environment doesn't exist.
    :raises Forbidden: The given environment is protected.
    """


@method(path="/environment", operation="GET", client_types=[const.ClientType.api])
def list_environments():
    """
    Returns a list of environments. The results are sorted by (project id, environment name, environment id).
    """


@method(
    path="/environment/<id>",
    operation="GET",
    client_types=[const.ClientType.api],
    arg_options={"id": ArgOption(getter=add_env)},
)
def get_environment(id: uuid.UUID, versions: int = None, resources: int = None):
    """
    Get an environment and all versions associated.

    :param id: The id of the environment to return.
    :param versions: Optional. If provided and greater than 0, include this many of the most recent versions for this
                     environment, ordered in descending order of their version number.
                     If not provided or 0, no version information is included.
    :param resources: Optional. If provided and greater than 0, include a summary of the resources in the environment.
    """


# Method for listing/getting/setting/removing settings of an environment. This API is also used by agents to configure
# environments.


@method(
    path="/environment_settings",
    operation="GET",
    arg_options=ENV_OPTS,
    api=True,
    agent_server=True,
    client_types=[const.ClientType.api, const.ClientType.agent, const.ClientType.compiler],
)
def list_settings(tid: uuid.UUID):
    """
    List the settings in the current environment ordered by name alphabetically.

    :param tid: The id of the environment to list settings for.
    """


@method(
    path="/environment_settings/<id>",
    operation="POST",
    arg_options=ENV_OPTS,
    api=True,
    agent_server=True,
    client_types=[const.ClientType.api, const.ClientType.agent, const.ClientType.compiler],
)
def set_setting(tid: uuid.UUID, id: str, value: Union[PrimitiveTypes, JsonType]):
    """
    Set a value for a setting.

    :param tid: The id of the environment.
    :param id: The id of the setting to set.
    :param value: The value to set for the setting.
    """


@method(
    path="/environment_settings/<id>",
    operation="GET",
    arg_options=ENV_OPTS,
    api=True,
    agent_server=True,
    client_types=[const.ClientType.api, const.ClientType.agent],
)
def get_setting(tid: uuid.UUID, id: str):
    """
    Get the value of a setting.

    :param tid: The id of the environment.
    :param id: The id of the setting to retrieve.
    """


@method(
    path="/environment_settings/<id>",
    operation="DELETE",
    arg_options=ENV_OPTS,
    api=True,
    agent_server=True,
    client_types=[const.ClientType.api, const.ClientType.agent],
)
def delete_setting(tid: uuid.UUID, id: str):
    """
    Restore the given setting to its default value.

    :param tid: The id of the environment from which the setting is to be deleted.
    :param id: The key of the setting to delete.

    """


# Method for listing and creating auth tokens for an environment that can be used by the agent and compilers


@method(
    path="/environment_auth",
    operation="POST",
    arg_options=ENV_OPTS,
    client_types=[const.ClientType.api, const.ClientType.compiler],
)
def create_token(tid: uuid.UUID, client_types: list, idempotent: bool = True):
    """
    Create or get a new token for the given client types.

    :param tid: The environment id.
    :param client_types: The client types for which this token is valid (api, agent, compiler).
    :param idempotent: Optional. The token should be idempotent, meaning it does not have an expire or issued at set,
                       so its value will not change.
    """


#  Decomission an environment


@method(
    path="/decommission/<id>",
    operation="POST",
    arg_options={"id": ArgOption(getter=convert_environment)},
    client_types=[const.ClientType.api],
    api_version=1,
)
def decomission_environment(id: uuid.UUID, metadata: dict = None):
    """
    Decommision an environment. This is done by uploading an empty model to the server and let purge_on_delete handle
    removal.

    :param id: The uuid of the environment.
    :param metadata: Optional metadata associated with the decommissioning

    :raises NotFound: The given environment doesn't exist.
    :raises Forbidden: The given environment is protected.
    """


@method(
    path="/decommission/<id>",
    operation="DELETE",
    arg_options={"id": ArgOption(getter=convert_environment)},
    client_types=[const.ClientType.api],
)
def clear_environment(id: uuid.UUID):
    """
    Clears an environment by removing most of its associated data.
    This method deletes various components associated with the specified environment from the database,
    including agents, compile data, parameters, notifications, code, resources, and configuration models.
    However, it retains the entry in the Environment table itself and settings are kept.

    :param id: The id of the environment to be cleared.

    :raises NotFound: The given environment doesn't exist.
    :raises Forbidden: The given environment is protected.

    """


# Send a heartbeat to indicate that an agent is alive
@method(
    path="/heartbeat",
    operation="POST",
    agent_server=True,
    validate_sid=False,
    arg_options=ENV_OPTS,
    client_types=[const.ClientType.agent],
)
def heartbeat(sid: uuid.UUID, tid: uuid.UUID, endpoint_names: list, nodename: str, no_hang: bool = False):
    """
    Send a heartbeat to the server

    :param sid: The session ID used by this agent at this moment
    :param tid: The environment this node and its agents belongs to
    :param endpoint_names: The names of the endpoints on this node
    :param nodename: The name of the node from which the heart beat comes
    :param no_hang: Optional. don't use this call for long polling, but for connectivity check

    also registered as API method, because it is called with an invalid SID the first time
    """


@method(
    path="/heartbeat",
    operation="PUT",
    agent_server=True,
    arg_options={"sid": ArgOption(getter=ignore_env)},
    client_types=[const.ClientType.agent],
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
    path="/file/<id>",
    operation="PUT",
    agent_server=True,
    api=True,
    client_types=[const.ClientType.api, const.ClientType.agent, const.ClientType.compiler],
    arg_options={"id": ArgOption(getter=ignore_env)},
)
def upload_file(id: str, content: str):
    """
    Upload a new file

    :param id: The id of the file
    :param content: The base64 encoded content of the file
    """


@method(
    path="/file/<id>",
    operation="HEAD",
    agent_server=True,
    api=True,
    client_types=[const.ClientType.api, const.ClientType.agent, const.ClientType.compiler],
    arg_options={"id": ArgOption(getter=ignore_env)},
)
def stat_file(id: str):
    """
    Does the file exist

    :param id: The id of the file to check
    """


@method(
    path="/file/<id>",
    operation="GET",
    agent_server=True,
    api=True,
    client_types=[const.ClientType.api, const.ClientType.agent, const.ClientType.compiler],
    arg_options={"id": ArgOption(getter=ignore_env)},
)
def get_file(id: str):
    """
    Retrieve a file

    :param id: The id of the file to retrieve
    """


@method(
    path="/file",
    api=True,
    client_types=[const.ClientType.api, const.ClientType.agent, const.ClientType.compiler],
    arg_options={"files": ArgOption(getter=ignore_env)},
)
def stat_files(files: list):
    """
    Check which files exist in the given list

    :param files: A list of file ids to check
    :return: A list of files that do not exist.
    """


# Manage resources on the server


@method(
    path="/resource/<id>",
    operation="GET",
    agent_server=True,
    validate_sid=False,
    arg_options=ENV_OPTS,
    api=True,
    client_types=[const.ClientType.api, const.ClientType.agent],
)
def get_resource(
    tid: uuid.UUID, id: str, logs: bool = None, status: bool = None, log_action: const.ResourceAction = None, log_limit: int = 0
):
    """
    Return a resource with the given id.

    :param tid: The id of the environment this resource belongs to
    :param id: Get the resource with the given resource version id
    :param logs: Optional. Include the logs in the response
    :param status: Optional. Only return the status of the resource
    :param log_action: Optional. The log action to include, leave empty/none for all actions. Valid actions are one of
                      the action strings in const.ResourceAction
    :param log_limit: Optional. Limit the number of logs included in the response, up to a maximum of 1000.
                      To retrieve more entries, use  /api/v2/resource_actions
                      (:func:`~inmanta.protocol.methods_v2.get_resource_actions`)
                      If None, a default limit (set to 1000) is applied.
    """


@method(path="/resource", operation="GET", agent_server=True, arg_options=ENV_OPTS, client_types=[const.ClientType.agent])
def get_resources_for_agent(
    tid: uuid.UUID, agent: str, sid: uuid.UUID = None, version: int = None, incremental_deploy: bool = False
):
    """
    Return the most recent state for the resources associated with agent, or the version requested

    :param tid: The environment ID this resource belongs to.
    :param agent: The agent name.
    :param sid: Optional. Session id of the agent (transparently added by agent client).
    :param version: Optional. The version to retrieve. If none, the latest available version is returned. With a specific
                    version that version is returned, even if it has not been released yet.
    :param incremental_deploy: Optional. Indicates whether the server should only return the resources that changed since the
                               previous deployment.
    """


@method(path="/resource", operation="POST", agent_server=True, arg_options=ENV_OPTS, client_types=[const.ClientType.agent])
def resource_action_update(
    tid: uuid.UUID,
    resource_ids: list,
    action_id: uuid.UUID,
    action: const.ResourceAction,
    started: datetime.datetime = None,
    finished: datetime.datetime = None,
    status: Optional[Union[const.ResourceState, const.DeprecatedResourceState]] = None,
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
    :param started: Optional. The timestamp when this action was started. When this action (action_id) has not been saved yet,
                    started has to be defined.
    :param finished: Optional. The timestamp when this action was finished. Afterwards, no changes with the same action_id
                    can be stored. The status field also has to be set.
    :param status: Optional. The current status of the resource (if known)
    :param messages: Optional. A list of log entries to add to this entry.
    :param changes: Optional. A dict of changes to this resource. The key of this dict indicates the attributes/fields that
                   have been changed. The value contains the new value and/or the original value.
    :param change: Optional. The result of the changes
    :param send_events: Optional. [DEPRECATED] The value of this field is not used anymore.
    """


# Manage configuration model versions


@method(path="/version", operation="GET", arg_options=ENV_OPTS, client_types=[const.ClientType.api])
def list_versions(tid: uuid.UUID, start: int = None, limit: int = None):
    """
    Returns a list of all available versions, ordered by version number, descending

    :param tid: The id of the environment
    :param start: Optional. parameter to control the amount of results that are returned. 0 is the latest version.
    :param limit: Optional. parameter to control the amount of results returned, up to a maximum of 1000.
                  If None, a default limit (set to 1000) is applied.
    """


@method(path="/version/<id>", operation="GET", arg_options=ENV_OPTS, client_types=[const.ClientType.api])
def get_version(tid: uuid.UUID, id: int, include_logs: bool = None, log_filter: str = None, limit: int = None):
    """
    Get a particular version and a list of all resources in this version

    :param tid: The id of the environment
    :param id: The id of the version to retrieve
    :param include_logs: Optional. If true, a log of all operations on all resources is included
    :param log_filter: Optional. Filter log to only include actions of the specified type
    :param limit: Optional. The maximal number of actions to return per resource (starting from the latest),
                    up to a maximum of 1000.
                    To retrieve more entries, use /api/v2/resource_actions
                    (:func:`~inmanta.protocol.methods_v2.get_resource_actions`)
                    If None, a default limit (set to 1000) is applied.
    """


@method(path="/version/<id>", operation="DELETE", arg_options=ENV_OPTS, client_types=[const.ClientType.api])
def delete_version(tid: uuid.UUID, id: int):
    """
    Delete a particular version and resources

    :param tid: The id of the environment
    :param id: The id of the version to retrieve
    """


@method(path="/version", operation="PUT", arg_options=ENV_OPTS, client_types=[const.ClientType.compiler])
def put_version(
    tid: uuid.UUID,
    version: int,
    resources: list,
    resource_state: dict = {},
    unknowns: list = None,
    version_info: dict = None,
    compiler_version: str = None,
    resource_sets: dict[model.ResourceIdStr, Optional[str]] = {},
):
    """
    Store a new version of the configuration model

    The version number must be obtained through the reserve_version call

    :param tid: The id of the environment
    :param version: The version of the configuration model
    :param resources: A list of all resources in the configuration model (deployable)
    :param resource_state: A dictionary with the initial const.ResourceState per resource id. The ResourceState should be set
                           to undefined when the resource depends on an unknown or available when it doesn't.
    :param unknowns: Optional. A list of unknown parameters that caused the model to be incomplete
    :param version_info: Optional. Module version information
    :param compiler_version: Optional. version of the compiler, if not provided, this call will return an error
    :param resource_sets: Optional. a dictionary describing which resource belongs to which resource set
    """


@method(
    path="/version/<id>", operation="POST", arg_options=ENV_OPTS, client_types=[const.ClientType.api, const.ClientType.compiler]
)
def release_version(tid: uuid.UUID, id: int, push: bool = False, agent_trigger_method: const.AgentTriggerMethod = None):
    """
    Release version of the configuration model for deployment.

    :param tid: The id of the environment
    :param id: The version of the CM to deploy
    :param push: Notify all agents to deploy the version
    :param agent_trigger_method: Optional. Indicates whether the agents should perform a full or an incremental deploy when
                                push is true.

     :return: Returns the following status codes:
            200: The version is released
            404: The requested version does not exist
            409: The requested version was already released
    """


@method(path="/deploy", operation="POST", arg_options=ENV_OPTS, client_types=[const.ClientType.api])
def deploy(
    tid: uuid.UUID,
    agent_trigger_method: const.AgentTriggerMethod = const.AgentTriggerMethod.push_full_deploy,
    agents: list = None,
):
    """
    Notify agents to perform a deploy now.

    :param tid: The id of the environment.
    :param agent_trigger_method: Indicates whether the agents should perform a full or an incremental deploy.
    :param agents: Optional, names of specific agents to trigger
    """


# Method for requesting and quering a dryrun


@method(path="/dryrun/<id>", operation="POST", arg_options=ENV_OPTS, client_types=[const.ClientType.api])
def dryrun_request(tid: uuid.UUID, id: int):
    """
    Do a dryrun

    :param tid: The id of the environment
    :param id: The version of the CM to deploy
    """


@method(path="/dryrun", operation="GET", arg_options=ENV_OPTS, client_types=[const.ClientType.api])
def dryrun_list(tid: uuid.UUID, version: int = None):
    """
    Get the list of dry runs for an environment. The results are sorted by dry run id.

    :param tid: The id of the environment
    :param version: Optional. Only for this version
    """


@method(path="/dryrun/<id>", operation="GET", arg_options=ENV_OPTS, client_types=[const.ClientType.api])
def dryrun_report(tid: uuid.UUID, id: uuid.UUID):
    """
    Create a dryrun report

    :param tid: The id of the environment
    :param id: The version dryrun to report
    """


@method(path="/dryrun/<id>", operation="PUT", agent_server=True, arg_options=ENV_OPTS, client_types=[const.ClientType.agent])
def dryrun_update(tid: uuid.UUID, id: uuid.UUID, resource: str, changes: dict):
    """
    Store dryrun results at the server

    :param tid: The id of the environment
    :param id: The version dryrun to report
    :param resource: The id of the resource
    :param changes: The required changes
    """


# Method for requesting a dryrun from an agent


@method(path="/agent_dryrun/<id>", operation="POST", server_agent=True, timeout=5, arg_options=AGENT_ENV_OPTS, client_types=[])
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
    path="/notify/<id>",
    operation="GET",
    arg_options={"id": ArgOption(getter=convert_environment)},
    client_types=[const.ClientType.api],
)
def notify_change_get(id: uuid.UUID, update: bool = True):
    """
    Simplified GET version of the POST method

    :param id: The id of the environment.
    :param update: Optional. Indicates whether to update the model code and modules. Defaults to true.
    """


@method(
    path="/notify/<id>",
    operation="POST",
    arg_options={"id": ArgOption(getter=convert_environment)},
    client_types=[const.ClientType.api],
)
def notify_change(id: uuid.UUID, update: bool = True, metadata: dict = {}):
    """
    Notify the server that the repository of the environment with the given id, has changed.

    :param id: The id of the environment
    :param update: Optional. Update the model code and modules. Default value is true
    :param metadata: Optional. The metadata that indicates the source of the compilation trigger.
    """


@method(path="/notify/<id>", operation="HEAD", client_types=[const.ClientType.api])
def is_compiling(id: uuid.UUID):
    """
    Is a compiler running for the given environment

    :param id: The environment id
    """


# Get and set parameters on the server


@method(
    path="/parameter/<id>",
    operation="GET",
    arg_options=ENV_OPTS,
    client_types=[const.ClientType.api, const.ClientType.compiler, const.ClientType.agent],
)
def get_param(tid: uuid.UUID, id: str, resource_id: str = None):
    """
    Get a parameter from the server.

    :param tid: The id of the environment
    :param id: The name of the parameter
    :param resource_id: Optional. scope the parameter to resource (fact),
                        if the resource id should not contain a version, the latest version is used
    :return: Returns the following status codes:
            200: The parameter content is returned
            404: The parameter is not found and unable to find it because its resource is not known to the server
            410: The parameter has expired
            503: The parameter is not found but its value is requested from an agent
    """


@method(
    path="/parameter/<id>",
    operation="PUT",
    arg_options=ENV_OPTS,
    client_types=[const.ClientType.api, const.ClientType.compiler, const.ClientType.agent],
)
def set_param(
    tid: uuid.UUID,
    id: str,
    source: const.ParameterSource,
    value: str,
    resource_id: str = None,
    metadata: dict = {},
    recompile: bool = False,
):
    """
    Set a parameter on the server. If the parameter is an tracked unknown, it will trigger a recompile on the server.
    Otherwise, if the value is changed and recompile is true, a recompile is also triggered.

    :param tid: The id of the environment
    :param id: The name of the parameter
    :param source: The source of the parameter.
    :param value: The value of the parameter
    :param resource_id: Optional. Scope the parameter to resource (fact)
    :param metadata: Optional. Metadata about the parameter
    :param recompile: Optional. Whether to trigger a recompile
    """


@method(
    path="/parameter/<id>",
    operation="DELETE",
    arg_options=ENV_OPTS,
    client_types=[const.ClientType.api, const.ClientType.compiler, const.ClientType.agent],
)
def delete_param(tid: uuid.UUID, id: str, resource_id: str = None):
    """
    Delete a parameter on the server

    :param tid: The id of the environment
    :param id: The name of the parameter
    :param resource_id: Optional. The resource id of the parameter
    """


@method(
    path="/parameter", operation="POST", arg_options=ENV_OPTS, client_types=[const.ClientType.api, const.ClientType.compiler]
)
def list_params(tid: uuid.UUID, query: dict = {}):
    """
    List/query parameters in this environment. The results are ordered alphabetically by parameter name.

    :param tid: The id of the environment
    :param query: Optional. A query to match against metadata
    """


#  Get and set parameters on the server


@method(
    path="/parameters",
    operation="PUT",
    agent_server=True,
    arg_options=ENV_OPTS,
    client_types=[const.ClientType.api, const.ClientType.compiler, const.ClientType.agent],
)
def set_parameters(tid: uuid.UUID, parameters: list):
    """
    Set a parameter on the server

    :param tid: The id of the environment
    :param parameters: A list of dicts with the following keys:
        - id The name of the parameter
        - source The source of the parameter. Valid values are defined in the ParameterSource enum (see: inmanta/const.py)
        - value The value of the parameter
        - resource_id Optionally, scope the parameter to resource (fact)
        - metadata metadata about the parameter
    """


# Get parameters from the agent


@method(path="/agent_parameter", operation="POST", server_agent=True, timeout=5, arg_options=AGENT_ENV_OPTS, client_types=[])
def get_parameter(tid: uuid.UUID, agent: str, resource: dict):
    """
    Get all parameters/facts known by the agents for the given resource

    :param tid: The environment
    :param agent: The agent to get the parameters from
    :param resource: The resource to query the parameters from
    """


@method(path="/code/<id>", operation="GET", agent_server=True, arg_options=ENV_OPTS, client_types=[const.ClientType.agent])
def get_code(tid: uuid.UUID, id: int, resource: str):
    """
    Retrieve the source code associated with a specific version of a configuration model for a given resource in an environment.

    :param tid: The id of the environment to which the code belongs.
    :param id: The version number of the configuration model.
    :param resource: The identifier of the resource. This should be a resource ID, not a resource version ID.
    """


@method(path="/codebatched/<id>", operation="PUT", arg_options=ENV_OPTS, client_types=[const.ClientType.compiler])
def upload_code_batched(tid: uuid.UUID, id: int, resources: dict):
    """
    Upload batches of code for various resources associated with a specific version of a configuration model in an environment.

    :param tid: The id of the environment to which the code belongs.
    :param id: The version number of the configuration model.
    :param resources: A dictionary where each key is a string representing a resource type.
                  For each resource type, the value is a dictionary. This nested dictionary's keys are file names,
                  and each key maps to a tuple. This tuple contains three elements: the file name, the module name,
                  and a list of requirements.

    The endpoint validates that all provided file references are valid and checks for conflicts with existing code entries.
    """


# Generate download the diff of two hashes


@method(path="/filediff", client_types=[const.ClientType.api])
def diff(file_id_1: str, file_id_2: str):
    """
    Returns the diff of the files with the two given ids

    :param file_id_1: The identifier of the first file.
    :param file_id_2: The identifier of the second file.

    :return: A string representing the diff between the two files.
    """


# Get a list of compile reports


@method(path="/compilereport", operation="GET", arg_options=ENV_OPTS, client_types=[const.ClientType.api])
def get_reports(tid: uuid.UUID, start: str = None, end: str = None, limit: int = None):
    """
    Return compile reports newer then start

    :param tid: The id of the environment to get a report from
    :param start: Optional. Reports after start
    :param end: Optional. Reports before end
    :param limit: Optional. Maximum number of results, up to a maximum of 1000
                  If None, a default limit (set to 1000) is applied.
    """


@method(path="/compilereport/<id>", operation="GET", client_types=[const.ClientType.api])
def get_report(id: uuid.UUID):
    """
    Get a compile report from the server

    :param id: The id of the compile and its reports to fetch.
    """


# Get a list of all agents


@method(path="/agentproc", operation="GET", client_types=[const.ClientType.api])
def list_agent_processes(
    environment: uuid.UUID = None, expired: bool = True, start: uuid.UUID = None, end: uuid.UUID = None, limit: int = None
):
    """
    Return a list of all nodes and the agents for these nodes

    :param environment: Optional. An optional environment. If set, only the agents that belong to this environment are returned
    :param expired: Optional. if true show expired processes, otherwise only living processes are shown. True by default
    :param start: Optional. Agent processes after start (sorted by sid in ASC)
    :param end: Optional. Agent processes before end (sorted by sid in ASC)
    :param limit: Optional. Maximum number of results, up to a maximum of 1000
                  If None, a default limit (set to 1000) is applied.

    :raises BadRequest: limit parameter can not exceed 1000
    :raises NotFound: The given environment id does not exist!

    :return: A list of nodes
    """


@method(path="/agentproc/<id>", operation="GET", client_types=[const.ClientType.api])
def get_agent_process(id: uuid.UUID):
    """
    Return a detailed report for a node

    :param id: The session id of the agent
    :return: The requested node
    """


# Get a list of all agents
@method(path="/agent/<id>", operation="POST", api=True, timeout=5, arg_options=ENV_OPTS, client_types=[const.ClientType.api])
def trigger_agent(tid: uuid.UUID, id: str):
    """
    Request the server to reload an agent

    :param tid: The environment this agent is defined in
    :param id: The name of the agent
    :return: The requested node
    """


@method(path="/agent", operation="GET", api=True, timeout=5, arg_options=ENV_OPTS, client_types=[const.ClientType.api])
def list_agents(tid: uuid.UUID, start: str = None, end: str = None, limit: int = None):
    """
    List all agent for an environment

    :param tid: The environment the agents are defined in
    :param start: Optional. Agent after start (sorted by name in ASC)
    :param end: Optional. Agent before end (sorted by name in ASC)
    :param limit: Optional. Maximum number of results, up to a maximum of 1000.
                  If None, a default limit (set to 1000) is applied.

    :raises BadRequest: limit parameter can not exceed 1000
    :raises NotFound: The given environment id does not exist!
    """


# Reporting by the agent to the server


@method(path="/status", operation="GET", server_agent=True, timeout=5, client_types=[])
def get_status():
    """
    A call from the server to the agent to report its status to the server

    :return: A map with report items
    """


# Methods to allow the server to set the agents state


@method(path="/agentstate", operation="POST", server_agent=True, timeout=5, client_types=[])
def set_state(agent: str, enabled: bool):
    """
    Set the state of the agent.

    :param agent: The name of the agent.
    :param enabled: A boolean value indicating whether the agent should be paused (enabled=False) or unpaused (enabled=True).
    """


@method(path="/agentstate/<id>", operation="POST", server_agent=True, timeout=5, arg_options=AGENT_ENV_OPTS, client_types=[])
def trigger(tid: uuid.UUID, id: str, incremental_deploy: bool):
    """
    Request an agent to reload resources

    :param tid: The environment this agent is defined in
    :param id: The name of the agent
    :param incremental_deploy: Indicates whether the agent should perform an incremental deploy or a full deploy
    """


# Methods to send event to the server


@method(
    path="/event/<id>", operation="PUT", server_agent=True, timeout=5, arg_options=AGENT_ENV_OPTS, client_types=[], reply=False
)
def resource_event(
    tid: uuid.UUID, id: str, resource: str, send_events: bool, state: const.ResourceState, change: const.Change, changes={}
):
    """
    Tell an agent a resource it waits for has been updated

    :param tid: The environment this agent is defined in
    :param id: The name of the agent
    :param resource: The resource ID of the resource being updated
    :param send_events: [DEPRECATED] The value of this field is not used anymore.
    :param state: State the resource acquired (deployed, skipped, canceled)
    :param change: The change that was made to the resource
    :param changes: Optional. The changes made to the resource
    """


# Methods for the agent to get its initial state from the server


@method(path="/agentrecovery", operation="GET", agent_server=True, arg_options=ENV_OPTS, client_types=[const.ClientType.agent])
def get_state(tid: uuid.UUID, sid: uuid.UUID, agent: str):
    """
    Get the state for this agent.

    :param tid: The id of the environment.
    :param sid: The session ID associated with this agent.
    :param agent: The name of the agent.

    :return: A map with key enabled and value a boolean.
    """


@typedmethod(path="/serverstatus", operation="GET", client_types=[const.ClientType.api])
def get_server_status() -> model.StatusResponse:
    """
    Get the status of the server
    """


@typedmethod(
    path="/compilequeue",
    operation="GET",
    arg_options=ENV_OPTS,
    client_types=[const.ClientType.api],
    api_version=1,
    envelope_key="queue",
)
def get_compile_queue(tid: uuid.UUID) -> list[model.CompileRun]:
    """
    Get the current compiler queue on the server, ordered by increasing `requested` timestamp.

    :param tid: The id of the environment for which to retrieve the compile queue.

    :return: A list of CompileRun objects representing the current state of the compiler queue,
             with each entry detailing a specific compile run.
    """
