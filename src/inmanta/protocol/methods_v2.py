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

    Module defining the v2 rest api
"""
import datetime
import uuid
from typing import Dict, List, Literal, Optional, Union

from inmanta.const import AgentAction, ApiDocsFormat, Change, ClientType, ResourceState
from inmanta.data import model
from inmanta.protocol.common import ReturnValue
from inmanta.types import PrimitiveTypes

from ..data.model import ResourceIdStr
from . import methods
from .decorators import typedmethod
from .openapi.model import OpenAPI


@typedmethod(
    path="/version/partial",
    operation="PUT",
    arg_options=methods.ENV_OPTS,
    client_types=[ClientType.compiler],
    api_version=2,
    varkw=True,
)
def put_partial(
    tid: uuid.UUID,
    resource_state: Optional[Dict[ResourceIdStr, Literal[ResourceState.available, ResourceState.undefined]]] = None,
    unknowns: Optional[List[Dict[str, PrimitiveTypes]]] = None,
    resource_sets: Optional[Dict[ResourceIdStr, Optional[str]]] = None,
    removed_resource_sets: Optional[List[str]] = None,
    **kwargs: object,  # bypass the type checking for the resources and version_info argument
) -> int:
    """
    Store a new version of the configuration model after a partial recompile. The partial is applied on top of the latest
    version. Dynamically acquires a new version and serializes concurrent calls. Python code for the new version is copied
    from the base version.

    Concurrent put_partial calls are safe from race conditions provided that their resource sets are disjunct. A put_version
    call concurrent with a put_partial is not guaranteed to be safe. It is the caller's responsibility to appropriately
    serialize them with respect to one another. The caller must ensure the reserve_version + put_version operation is atomic
    with respect to put_partial. In other words, put_partial must not be called in the window between reserve_version and
    put_version. If not respected, either the full or the partial export might be immediately stale, and future exports will
    only be applied on top of the non-stale one.

    :param tid: The id of the environment
    :param resource_state: A dictionary with the initial const.ResourceState per resource id. The ResourceState should be set
                           to undefined when the resource depends on an unknown or available when it doesn't.
    :param unknowns: A list of unknown parameters that caused the model to be incomplete
    :param resource_sets: a dictionary describing which resources belong to which resource set
    :param removed_resource_sets: a list of resource_sets that should be deleted from the model
    :param **kwargs: The following arguments are supported:
              * resources: a list of resource objects. Since the version is not known yet resource versions should be set to 0.
              * version_info: Model version information
    :return: The newly stored version number.
    """


# Method for working with projects
@typedmethod(path="/project", operation="PUT", client_types=[ClientType.api], api_version=2)
def project_create(name: str, project_id: uuid.UUID = None) -> model.Project:
    """
    Create a new project

    :param name: The name of the project
    :param project_id: A unique uuid, when it is not provided the server generates one
    """


@typedmethod(path="/project/<id>", operation="POST", client_types=[ClientType.api], api_version=2)
def project_modify(id: uuid.UUID, name: str) -> model.Project:
    """
    Modify the given project
    """


@typedmethod(path="/project/<id>", operation="DELETE", client_types=[ClientType.api], api_version=2)
def project_delete(id: uuid.UUID) -> None:
    """
    Delete the given project and all related data
    """


@typedmethod(path="/project", operation="GET", client_types=[ClientType.api], api_version=2)
def project_list(environment_details: bool = False) -> List[model.Project]:
    """
    Returns a list of projects
    :param environment_details: Whether to include the icon and description of the environments in the results
    """


@typedmethod(path="/project/<id>", operation="GET", client_types=[ClientType.api], api_version=2)
def project_get(id: uuid.UUID, environment_details: bool = False) -> model.Project:
    """
    Get a project and a list of the environments under this project
    :param environment_details: Whether to include the icon and description of the environments in the results
    """


# Methods for working with environments
@typedmethod(path="/environment", operation="PUT", client_types=[ClientType.api], api_version=2)
def environment_create(
    project_id: uuid.UUID,
    name: str,
    repository: Optional[str] = None,
    branch: Optional[str] = None,
    environment_id: uuid.UUID = None,
    description: str = "",
    icon: str = "",
) -> model.Environment:
    """
    Create a new environment

    :param project_id: The id of the project this environment belongs to
    :param name: The name of the environment
    :param repository: The url (in git form) of the repository
    :param branch: The name of the branch in the repository
    :param environment_id: A unique environment id, if none an id is allocated by the server
    :param description: The description of the environment, maximum 255 characters
    :param icon: The data-url of the icon of the environment. It should follow the pattern `<mime-type>;base64,<image>`, where
                 <mime-type> is one of: 'image/png', 'image/jpeg', 'image/webp', 'image/svg+xml', and <image> is the image in
                 the format matching the specified mime-type, and base64 encoded.
                 The length of the whole string should be maximum 64 kb.

    :raises BadRequest: When the parameters supplied are not valid.
    """


@typedmethod(path="/environment/<id>", operation="POST", client_types=[ClientType.api], api_version=2)
def environment_modify(
    id: uuid.UUID,
    name: str,
    repository: str = None,
    branch: str = None,
    project_id: Optional[uuid.UUID] = None,
    description: Optional[str] = None,
    icon: Optional[str] = None,
) -> model.Environment:
    """
    Modify the given environment
    The optional parameters that are unspecified will be left unchanged by the update.

    :param id: The id of the environment
    :param name: The name of the environment
    :param repository: The url (in git form) of the repository
    :param branch: The name of the branch in the repository
    :param project_id: The id of the project the environment belongs to
    :param description: The description of the environment, maximum 255 characters
    :param icon: The data-url of the icon of the environment. It should follow the pattern `<mime-type>;base64,<image>` , where
                 <mime-type> is one of: 'image/png', 'image/jpeg', 'image/webp', 'image/svg+xml', and <image> is the image in
                 the format matching the specified mime-type, and base64 encoded.
                 The length of the whole string should be maximum 64 kb.
                 The icon can be removed by setting this parameter to an empty string.

    :raises BadRequest: When the parameters supplied are not valid.
    :raises NotFound: The given environment doesn't exist.
    """


@typedmethod(path="/environment/<id>", operation="DELETE", client_types=[ClientType.api], api_version=2)
def environment_delete(id: uuid.UUID) -> None:
    """
    Delete the given environment and all related data.

    :param id: The uuid of the environment.

    :raises NotFound: The given environment doesn't exist.
    :raises Forbidden: The given environment is protected.
    """


@typedmethod(path="/environment", operation="GET", client_types=[ClientType.api], api_version=2)
def environment_list(details: bool = False) -> List[model.Environment]:
    """
    Returns a list of environments
    :param details: Whether to include the icon and description of the environments in the results
    """


@typedmethod(
    path="/environment/<id>",
    operation="GET",
    client_types=[ClientType.api],
    arg_options={"id": methods.ArgOption(getter=methods.add_env)},
    api_version=2,
)
def environment_get(id: uuid.UUID, details: bool = False) -> model.Environment:
    """
    Get an environment and all versions associated

    :param id: The id of the environment to return
    :param details: Whether to include the icon and description of the environment
    """


@typedmethod(
    path="/actions/environment/halt",
    operation="POST",
    arg_options=methods.ENV_OPTS,
    client_types=[ClientType.api],
    api_version=2,
)
def halt_environment(tid: uuid.UUID) -> None:
    """
    Halt all orchestrator operations for an environment. The environment will enter a state where all agents are paused and
    can not be unpaused. Incoming compile requests will still be queued but compilation will halt. Normal operation can be
    restored using the `resume_environment` endpoint.

    :param tid: The environment id

    :raises NotFound: The given environment doesn't exist.
    """


@typedmethod(
    path="/actions/environment/resume",
    operation="POST",
    arg_options=methods.ENV_OPTS,
    client_types=[ClientType.api],
    api_version=2,
)
def resume_environment(tid: uuid.UUID) -> None:
    """
    Resume all orchestrator operations for an environment. Resumes normal environment operation and unpauses all agents
    that were active when the environment was halted.

    :param tid: The environment id

    :raises NotFound: The given environment doesn't exist.
    """


@typedmethod(
    path="/decommission/<id>",
    operation="POST",
    arg_options={"id": methods.ArgOption(getter=methods.convert_environment)},
    client_types=[ClientType.api],
    api_version=2,
)
def environment_decommission(id: uuid.UUID, metadata: Optional[model.ModelMetadata] = None) -> int:
    """
    Decommission an environment. This is done by uploading an empty model to the server and let purge_on_delete handle
    removal.

    :param id: The uuid of the environment.
    :param metadata: Optional metadata associated with the decommissioning

    :raises NotFound: The given environment doesn't exist.
    :raises Forbidden: The given environment is protected.
    """


@typedmethod(
    path="/decommission/<id>",
    operation="DELETE",
    arg_options={"id": methods.ArgOption(getter=methods.convert_environment)},
    client_types=[ClientType.api],
    api_version=2,
)
def environment_clear(id: uuid.UUID) -> None:
    """
    Clear all data from this environment.

    :param id: The uuid of the environment.

    :raises NotFound: The given environment doesn't exist.
    :raises Forbidden: The given environment is protected.
    """


# Method for listing and creating auth tokens for an environment that can be used by the agent and compilers
@typedmethod(
    path="/environment_auth",
    operation="POST",
    arg_options=methods.ENV_OPTS,
    client_types=[ClientType.api, ClientType.compiler],
    api_version=2,
)
def environment_create_token(tid: uuid.UUID, client_types: List[str], idempotent: bool = True) -> str:
    """
    Create or get a new token for the given client types. Tokens generated with this call are scoped to the current
    environment.

    :param tid: The environment id
    :param client_types: The client types for which this token is valid (api, agent, compiler)
    :param idempotent: The token should be idempotent, such tokens do not have an expire or issued at set so their
                       value will not change.
    """


# Method for listing/getting/setting/removing settings of an environment. This API is also used by agents to configure
# environments.
@typedmethod(
    path="/environment_settings",
    operation="GET",
    arg_options=methods.ENV_OPTS,
    api=True,
    agent_server=True,
    client_types=[ClientType.api, ClientType.agent, ClientType.compiler],
    api_version=2,
)
def environment_settings_list(tid: uuid.UUID) -> model.EnvironmentSettingsReponse:
    """
    List the settings in the current environment
    """


@typedmethod(
    path="/environment_settings/<id>",
    operation="POST",
    arg_options=methods.ENV_OPTS,
    api=True,
    agent_server=True,
    client_types=[ClientType.api, ClientType.agent, ClientType.compiler],
    api_version=2,
)
def environment_settings_set(tid: uuid.UUID, id: str, value: model.EnvSettingType) -> ReturnValue[None]:
    """
    Set a value
    """


@typedmethod(
    path="/environment_settings/<id>",
    operation="GET",
    arg_options=methods.ENV_OPTS,
    api=True,
    agent_server=True,
    client_types=[ClientType.api, ClientType.agent],
    api_version=2,
)
def environment_setting_get(tid: uuid.UUID, id: str) -> model.EnvironmentSettingsReponse:
    """
    Get a value
    """


@typedmethod(
    path="/environment_settings/<id>",
    operation="DELETE",
    arg_options=methods.ENV_OPTS,
    api=True,
    agent_server=True,
    client_types=[ClientType.api, ClientType.agent],
    api_version=2,
)
def environment_setting_delete(tid: uuid.UUID, id: str) -> ReturnValue[None]:
    """
    Delete a value
    """


@typedmethod(
    path="/reserve_version", operation="POST", arg_options=methods.ENV_OPTS, client_types=[ClientType.compiler], api_version=2
)
def reserve_version(tid: uuid.UUID) -> int:
    """
    Reserve a version number in this environment.
    """


@typedmethod(path="/docs", operation="GET", client_types=[ClientType.api], api_version=2)
def get_api_docs(format: Optional[ApiDocsFormat] = ApiDocsFormat.swagger) -> ReturnValue[Union[OpenAPI, str]]:
    """
    Get the OpenAPI definition of the API
    :param format: Use 'openapi' to get the schema in json format, leave empty or use 'swagger' to get the Swagger-UI view
    """


@typedmethod(
    path="/agent/<name>/<action>", operation="POST", arg_options=methods.ENV_OPTS, client_types=[ClientType.api], api_version=2
)
def agent_action(tid: uuid.UUID, name: str, action: AgentAction) -> None:
    """
    Execute an action on an agent

    :param tid: The environment this agent is defined in.
    :param name: The name of the agent.
    :param action: The type of action that should be executed on an agent.
                    Pause and unpause can only be used when the environment is not halted,
                    while the on_resume actions can only be used when the environment is halted.
                    * pause: A paused agent cannot execute any deploy operations.
                    * unpause: A unpaused agent will be able to execute deploy operations.
                    * keep_paused_on_resume: The agent will still be paused when the environment is resumed
                    * unpause_on_resume: The agent will be unpaused when the environment is resumed

    :raises Forbidden: The given environment has been halted and the action is pause/unpause,
                        or the environment is not halted and the action is related to the on_resume behavior
    """


@typedmethod(
    path="/agents/<action>", operation="POST", arg_options=methods.ENV_OPTS, client_types=[ClientType.api], api_version=2
)
def all_agents_action(tid: uuid.UUID, action: AgentAction) -> None:
    """
    Execute an action on all agents in the given environment.

    :param tid: The environment of the agents.
    :param action: The type of action that should be executed on the agents.
                    Pause and unpause can only be used when the environment is not halted,
                    while the on_resume actions can only be used when the environment is halted.
                    * pause: A paused agent cannot execute any deploy operations.
                    * unpause: A unpaused agent will be able to execute deploy operations.
                    * keep_paused_on_resume: The agents will still be paused when the environment is resumed
                    * unpause_on_resume: The agents will be unpaused when the environment is resumed

    :raises Forbidden: The given environment has been halted and the action is pause/unpause,
                        or the environment is not halted and the action is related to the on_resume behavior
    """


@typedmethod(path="/agents", operation="GET", arg_options=methods.ENV_OPTS, client_types=[ClientType.api], api_version=2)
def get_agents(
    tid: uuid.UUID,
    limit: Optional[int] = None,
    start: Optional[Union[datetime.datetime, bool, str]] = None,
    end: Optional[Union[datetime.datetime, bool, str]] = None,
    first_id: Optional[str] = None,
    last_id: Optional[str] = None,
    filter: Optional[Dict[str, List[str]]] = None,
    sort: str = "name.asc",
) -> List[model.Agent]:
    """
    Get all of the agents in the given environment

    :param tid: The id of the environment the agents should belong to.
    :param limit: Limit the number of agents that are returned.
    :param start: The lower limit for the order by column (exclusive).
    :param first_id: The name to use as a continuation token for paging, in combination with the 'start' value,
        because the order by column might contain non-unique values.
    :param last_id: The name to use as a continuation token for paging, in combination with the 'end' value,
        because the order by column might contain non-unique values.
        Only one of 'start' and 'end' should be specified at the same time.
    :param end: The upper limit for the order by column (exclusive).
        Only one of 'start' and 'end' should be specified at the same time.
    :param filter: Filter the list of returned agents.
        Filtering by 'name', 'process_name' and 'status' is supported.
    :param sort: Return the results sorted according to the parameter value.
        Sorting by 'name', 'process_name', 'status', 'paused' and 'last_failover' is supported.
        The following orders are supported: 'asc', 'desc'
    :return: A list of all matching agents
    :raise NotFound: This exception is raised when the referenced environment is not found
    :raise BadRequest: When the parameters used for filtering, sorting or paging are not valid
    """


@typedmethod(
    path="/agents/process/<id>", operation="GET", arg_options=methods.ENV_OPTS, client_types=[ClientType.api], api_version=2
)
def get_agent_process_details(tid: uuid.UUID, id: uuid.UUID, report: bool = False) -> model.AgentProcess:
    """
    Get the details of an agent process

    :param tid: Id of the environment
    :param id: The id of the specific agent process
    :param report: Whether to include a report from the agent or not
    :return: The details of an agent process
    :raise NotFound: This exception is raised when the referenced environment or agent process is not found
    """


@typedmethod(path="/agentmap", api=False, server_agent=True, operation="POST", client_types=[], api_version=2)
def update_agent_map(agent_map: Dict[str, str]) -> None:
    """
    Notify an agent about the fact that the autostart_agent_map has been updated.

    :param agent_map: The content of the new autostart_agent_map
    """


@typedmethod(
    path="/compiledata/<id>",
    operation="GET",
    client_types=[ClientType.api],
    api_version=2,
)
def get_compile_data(id: uuid.UUID) -> Optional[model.CompileData]:
    """
    Get the compile data for the given compile request.

    :param id: The id of the compile.
    """


@typedmethod(
    path="/resource_actions", operation="GET", arg_options=methods.ENV_OPTS, client_types=[ClientType.api], api_version=2
)
def get_resource_actions(
    tid: uuid.UUID,
    resource_type: Optional[str] = None,
    agent: Optional[str] = None,
    attribute: Optional[str] = None,
    attribute_value: Optional[str] = None,
    log_severity: Optional[str] = None,
    limit: Optional[int] = 0,
    action_id: Optional[uuid.UUID] = None,
    first_timestamp: Optional[datetime.datetime] = None,
    last_timestamp: Optional[datetime.datetime] = None,
) -> ReturnValue[List[model.ResourceAction]]:
    """
    Return resource actions matching the search criteria.

    :param tid: The id of the environment this resource belongs to
    :param resource_type: The resource entity type that should be queried
    :param agent: Agent name that is used to filter the results
    :param attribute: Attribute name used for filtering
    :param attribute_value: Attribute value used for filtering. Attribute and attribute value should be supplied together.
    :param log_severity: Only include ResourceActions which have a log message with this severity.
    :param limit: Limit the number of resource actions included in the response, up to 1000
    :param action_id: Start the query from this action_id.
            To be used in combination with either the first or last timestamp.
    :param first_timestamp: Limit the results to resource actions that started later
            than the value of this parameter (exclusive)
    :param last_timestamp: Limit the results to resource actions that started earlier
            than the value of this parameter (exclusive).
            Only the first_timestamp or last_timestamp parameter should be supplied
    :return: the list of matching Resource Actions in a descending order according to the 'started' timestamp.
            If a limit was specified, also return the links to the next and previous pages.
            The "next" page always refers to the actions that started earlier,
            while the "prev" page refers to actions that started later.

    :raises BadRequest: When the supplied parameters are not valid.

    """


@typedmethod(
    path="/resource/<rvid>/deploy/done",
    operation="POST",
    agent_server=True,
    arg_options={**methods.ENV_OPTS, **methods.RVID_OPTS},
    client_types=[ClientType.agent],
    api_version=2,
)
def resource_deploy_done(
    tid: uuid.UUID,
    rvid: model.ResourceVersionIdStr,
    action_id: uuid.UUID,
    status: ResourceState,
    messages: List[model.LogLine] = [],
    changes: Dict[str, model.AttributeStateChange] = {},
    change: Optional[Change] = None,
) -> None:
    """
    Report to the server that an agent has finished the deployment of a certain resource.

    :param tid: The id of the environment the resource belongs to
    :param rvid: The resource version id of the resource for which the deployment is finished.
    :param action_id: A unique ID associated with this resource deployment action. This should be the same ID that was
                      passed to the `/resource/<resource_id>/deploy/start` API call.
    :param status: The current status of the resource (if known)
    :param messages: A list of log entries produced by the deployment action.
    :param changes: A dict of changes to this resource. The key of this dict indicates the attributes/fields that
                   have been changed. The value contains the new value and/or the original value.
    :param change: The type of change that was done the given resource.
    """


@typedmethod(
    path="/resource/<rvid>/deploy/start",
    operation="POST",
    agent_server=True,
    arg_options={**methods.ENV_OPTS, **methods.RVID_OPTS},
    client_types=[ClientType.agent],
    api_version=2,
)
def resource_deploy_start(
    tid: uuid.UUID,
    rvid: model.ResourceVersionIdStr,
    action_id: uuid.UUID,
) -> Dict[model.ResourceVersionIdStr, ResourceState]:
    """
    Report to the server that the agent will start the deployment of the given resource.

    :param tid: The id of the environment the resource belongs to
    :param rvid: The resource version id of the resource for which the deployment will start
    :param action_id: A unique id used to track the action of this deployment
    :return: A dict mapping the resource version id of each dependency of resource_id to
             the last deployment status of that resource.
    """


# No pagination support is provided for this endpoint because there is no elegant way to page the output of this endpoint.
@typedmethod(
    path="/resource/<rvid>/events",
    operation="GET",
    arg_options={**methods.ENV_OPTS, **methods.RVID_OPTS},
    agent_server=True,
    client_types=[ClientType.agent],
    api_version=2,
)
def get_resource_events(
    tid: uuid.UUID,
    rvid: model.ResourceVersionIdStr,
) -> Dict[model.ResourceIdStr, List[model.ResourceAction]]:
    """
    Return relevant events for a resource, i.e. all deploy actions for each of its dependencies since this resources' last
    deploy or all deploy actions if this resources hasn't been deployed before. The resource actions are sorted in descending
    order according to their started timestamp.

    This method searches through all versions of this resource.
    This method should only be called when a deploy is in progress.

    :param tid: The id of the environment this resource belongs to
    :param rvid: The id of the resource to get events for.
    :raises BadRequest: When this endpoint in called while the resource with the given resource version is not
                        in the deploying state.
    """


@typedmethod(
    path="/resource/<rvid>/did_dependency_change",
    operation="GET",
    arg_options={**methods.ENV_OPTS, **methods.RVID_OPTS},
    agent_server=True,
    client_types=[ClientType.agent],
    api_version=2,
)
def resource_did_dependency_change(
    tid: uuid.UUID,
    rvid: model.ResourceVersionIdStr,
) -> bool:
    """
    Returns True iff this resources' events indicate a change in its dependencies since the resource's last deployment.

    This method searches through all versions of this resource.
    This method should only be called when a deploy is in progress.

    :param tid: The id of the environment this resource belongs to
    :param rvid: The id of the resource.
    :raises BadRequest: When this endpoint in called while the resource with the given resource version is not
                        in the deploying state.
    """


@typedmethod(path="/resource", operation="GET", arg_options=methods.ENV_OPTS, client_types=[ClientType.api], api_version=2)
def resource_list(
    tid: uuid.UUID,
    limit: Optional[int] = None,
    first_id: Optional[model.ResourceVersionIdStr] = None,
    last_id: Optional[model.ResourceVersionIdStr] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    filter: Optional[Dict[str, List[str]]] = None,
    sort: str = "resource_type.desc",
    deploy_summary: bool = False,
) -> List[model.LatestReleasedResource]:
    """
    :param tid: The id of the environment this resource belongs to
    :param limit: Limit the number of instances that are returned
    :param first_id: The resource_version_id to use as a continuation token for paging, in combination with the 'start' value,
            because the order by column might contain non-unique values
    :param last_id: The resource_version_id to use as a continuation token for paging, in combination with the 'end' value,
            because the order by column might contain non-unique values
    :param start: The lower limit for the order by column (exclusive).
                Only one of 'start' and 'end' should be specified at the same time.
    :param end: The upper limit for the order by column (exclusive).
                Only one of 'start' and 'end' should be specified at the same time.
    :param filter: Filter the list of returned resources.
                Filters should be specified with the syntax `?filter.<filter_key>=value`, for example `?filter.status=deployed`
                It's also possible to provide multiple values for the same filter, in this case resources are returned,
                if they match any of these filter values.
                For example: `?filter.status=deployed&filter.status=available` returns instances with either of the statuses
                deployed or available.
                Multiple different filters narrow the results however (they are treated as an 'AND' operator).
                For example `filter.status=deployed&filter.agent=internal` returns resources
                with 'deployed' status, where the 'agent' is set to 'internal_agent'.
                The following options are available:
                agent: filter by the agent of the resource
                resource_type: filter by the type of the resource
                resource_id_value: filter by the attribute values of the resource
                status: filter by the current status of the resource.
                For status filters it's also possible to invert the condition with '!', for example
                `filter.status=!orphaned` will return all the resources that are not in 'orphaned' state
                The values for the 'agent', 'resource_type' and 'value' filters are matched partially.
    :param sort: Return the results sorted according to the parameter value.
                It should follow the pattern `<attribute_to_sort_by>.<order>`, for example `resource_type.desc`
                (case insensitive).
                The following sorting attributes are supported: 'resource_type', 'agent', 'resource_id_value', 'status'.
                The following orders are supported: 'asc', 'desc'
    :param deploy_summary: If set to true, returns a summary of the deployment status of the resources in the environment
                           in the metadata, describing how many resources are in each state as well as the total number
                           of resources. The summary does not take into account the current filters or paging parameters.
                           Orphaned resources are not included in the summary
    :return: A list of all matching released resources
    :raise NotFound: This exception is raised when the referenced environment is not found
    :raise BadRequest: When the parameters used for filtering, sorting or paging are not valid
    """


@typedmethod(
    path="/resource/<rid>", operation="GET", arg_options=methods.ENV_OPTS, client_types=[ClientType.api], api_version=2
)
def resource_details(tid: uuid.UUID, rid: model.ResourceIdStr) -> model.ReleasedResourceDetails:
    """
    :return: The details of the latest released version of a resource
    :raise NotFound: This exception is raised when the referenced environment or resource is not found
    """


@typedmethod(
    path="/resource/<rid>/history", operation="GET", arg_options=methods.ENV_OPTS, client_types=[ClientType.api], api_version=2
)
def resource_history(
    tid: uuid.UUID,
    rid: model.ResourceIdStr,
    limit: Optional[int] = None,
    first_id: Optional[str] = None,
    last_id: Optional[str] = None,
    start: Optional[datetime.datetime] = None,
    end: Optional[datetime.datetime] = None,
    sort: str = "date.desc",
) -> List[model.ResourceHistory]:
    """
    :param tid: The id of the environment this resource belongs to
    :param rid: The id of the resource
    :param limit: Limit the number of instances that are returned
    :param first_id: The attribute_hash to use as a continuation token for paging, in combination with the 'start' value,
            because the order by column might contain non-unique values
    :param last_id: The attribute_hash to use as a continuation token for paging, in combination with the 'end' value,
            because the order by column might contain non-unique values
    :param start: The lower limit for the order by column (exclusive).
                Only one of 'start' and 'end' should be specified at the same time.
    :param end: The upper limit for the order by column (exclusive).
                Only one of 'start' and 'end' should be specified at the same time.
    :param sort: Return the results sorted according to the parameter value.
                It should follow the pattern `<attribute_to_sort_by>.<order>`, for example `date.desc`
                (case insensitive).
                Sorting by `date` is supported.
                The following orders are supported: 'asc', 'desc'
    :return: The history of a resource, according to its attributes
    :raise NotFound: This exception is raised when the referenced environment is not found
    :raise BadRequest: When the parameters used for sorting or paging are not valid
    """


@typedmethod(
    path="/resource/<rid>/logs", operation="GET", arg_options=methods.ENV_OPTS, client_types=[ClientType.api], api_version=2
)
def resource_logs(
    tid: uuid.UUID,
    rid: model.ResourceIdStr,
    limit: Optional[int] = None,
    start: Optional[datetime.datetime] = None,
    end: Optional[datetime.datetime] = None,
    filter: Optional[Dict[str, List[str]]] = None,
    sort: str = "timestamp.desc",
) -> List[model.ResourceLog]:
    """
    Get the logs of a specific resource.

    :param tid: The id of the environment this resource belongs to
    :param rid: The id of the resource
    :param limit: Limit the number of instances that are returned
    :param start: The lower limit for the order by column (exclusive). Only one of 'start' and 'end' should be specified at
        the same time.
    :param end: The upper limit for the order by column (exclusive). Only one of 'start' and 'end' should be specified at the
        same time.
    :param filter: Filter the list of returned logs.
        Filters should be specified with the syntax `?filter.<filter_key>=value`, for example `?filter.minimal_log_level=INFO`.
        It's also possible to provide multiple values for the same filter, in this case resources are returned, if they match
        any of these filter values.

        For example: `?filter.action=pull&filter.action=deploy` returns logs with either of the actions pull or deploy.
        Multiple different filters narrow the results however (they are treated as an 'AND' operator).
        For example `filter.minimal_log_level=INFO&filter.action=deploy` returns logs with 'deploy' action, where the
        'log_level' is at least 'INFO'.

        The following options are available:
            * action: filter by the action of the log

            * timestamp: return the logs matching the timestamp constraints. Valid constraints are of the form
              "<lt|le|gt|ge>:<x>". The expected format is YYYY-MM-DDTHH:mm:ss.ssssss, so an ISO-8601 datetime string,
              in UTC timezone.

            For example: `?filter.timestamp=ge:2021-08-18T09:21:30.568353&filter.timestamp=lt:2021-08-18T10:21:30.568353`.
            Multiple constraints can be specified, in which case only log messages that match all constraints will be
            returned.

            * message: filter by the content of the log messages. Partial matches are allowed. (case-insensitive)

            * minimal_log_level: filter by the log level of the log messages. The filter specifies the minimal level,
              so messages with either this level, or a higher severity level are going to be included in the result.

            For example, for `filter.minimal_log_level=INFO`, the log messages with level `INFO, WARNING, ERROR, CRITICAL`
            all match the query.

    :param sort: Return the results sorted according to the parameter value. It should follow the pattern
        `<attribute_to_sort_by>.<order>`, for example `timestamp.desc` (case insensitive). Only sorting by `timestamp` is
        supported. The following orders are supported: 'asc', 'desc'

    :return: A list of all matching resource logs
    :raise NotFound: This exception is raised when the referenced environment is not found
    :raise BadRequest: When the parameters used for filtering, sorting or paging are not valid
    """


@typedmethod(
    path="/resource/<rid>/facts", operation="GET", arg_options=methods.ENV_OPTS, client_types=[ClientType.api], api_version=2
)
def get_facts(tid: uuid.UUID, rid: model.ResourceIdStr) -> List[model.Fact]:
    """
    Get the facts related to a specific resource
    :param tid: The id of the environment
    :param rid: Id of the resource
    :return: The facts related to this resource
    :raise NotFound: This status code is returned when the referenced environment is not found
    """


@typedmethod(
    path="/resource/<rid>/facts/<id>",
    operation="GET",
    arg_options=methods.ENV_OPTS,
    client_types=[ClientType.api],
    api_version=2,
)
def get_fact(tid: uuid.UUID, rid: model.ResourceIdStr, id: uuid.UUID) -> model.Fact:
    """
    Get one specific fact
    :param tid: The id of the environment
    :param rid: The id of the resource
    :param id: The id of the fact
    :return: A specific fact corresponding to the id
    :raise NotFound: This status code is returned when the referenced environment or fact is not found
    """


@typedmethod(path="/compilereport", operation="GET", arg_options=methods.ENV_OPTS, client_types=[ClientType.api], api_version=2)
def get_compile_reports(
    tid: uuid.UUID,
    limit: Optional[int] = None,
    first_id: Optional[uuid.UUID] = None,
    last_id: Optional[uuid.UUID] = None,
    start: Optional[datetime.datetime] = None,
    end: Optional[datetime.datetime] = None,
    filter: Optional[Dict[str, List[str]]] = None,
    sort: str = "requested.desc",
) -> List[model.CompileReport]:
    """
    Get the compile reports from an environment.

    :param tid: The id of the environment
    :param limit: Limit the number of instances that are returned
    :param first_id: The id to use as a continuation token for paging, in combination with the 'start' value,
            because the order by column might contain non-unique values
    :param last_id: The id to use as a continuation token for paging, in combination with the 'end' value,
            because the order by column might contain non-unique values
    :param start: The lower limit for the order by column (exclusive).
                Only one of 'start' and 'end' should be specified at the same time.
    :param end: The upper limit for the order by column (exclusive).
                Only one of 'start' and 'end' should be specified at the same time.
    :param filter: Filter the list of returned compile reports.
                Filters should be specified with the syntax `?filter.<filter_key>=value`,
                for example `?filter.success=True`
                It's also possible to provide multiple values for the same filter, in this case resources are returned,
                if they match any of these filter values.
                For example: `?filter.requested=ge:2021-08-18T09:21:30.568353&filter.requested=lt:2021-08-18T10:21:30.568353`
                returns compile reports that were requested between the specified dates.
                Multiple different filters narrow the results however (they are treated as an 'AND' operator).
                For example `?filter.success=True&filter.completed=True` returns compile reports
                that are completed and successful.
                The following options are available:
                success: whether the compile was successful or not
                started: whether the compile has been started or not
                completed: whether the compile has been completed or not

                requested: return the logs matching the timestamp constraints. Valid constraints are of the form
                    "<lt|le|gt|ge>:<x>". The expected format is YYYY-MM-DDTHH:mm:ss.ssssss, so an ISO-8601 datetime string,
                    in UTC timezone. Specifying microseconds is optional. For example:
                    `?filter.requested=ge:2021-08-18T09:21:30.568353&filter.requested=lt:2021-08-18T10:21:30`.
                    Multiple constraints can be specified, in which case only compile reports that match all constraints will be
                    returned.
    :param sort: Return the results sorted according to the parameter value.
                It should follow the pattern `?sort=<attribute_to_sort_by>.<order>`, for example `?sort=requested.desc`
                (case insensitive).
                Only sorting by the `requested` timestamp is supported.
                The following orders are supported: 'asc', 'desc'
    :return: A list of all matching compile reports
    :raise NotFound: This exception is raised when the referenced environment is not found
    :raise BadRequest: When the parameters used for filtering, sorting or paging are not valid
    """


@typedmethod(
    path="/compilereport/<id>", operation="GET", arg_options=methods.ENV_OPTS, client_types=[ClientType.api], api_version=2
)
def compile_details(tid: uuid.UUID, id: uuid.UUID) -> model.CompileDetails:
    """
    :return: The details of a compile
    :raise NotFound: This exception is raised when the referenced environment or compile is not found
    """


@typedmethod(path="/desiredstate", operation="GET", arg_options=methods.ENV_OPTS, client_types=[ClientType.api], api_version=2)
def list_desired_state_versions(
    tid: uuid.UUID,
    limit: Optional[int] = None,
    start: Optional[int] = None,
    end: Optional[int] = None,
    filter: Optional[Dict[str, List[str]]] = None,
    sort: str = "version.desc",
) -> List[model.DesiredStateVersion]:
    """
    Get the desired state versions from an environment.

    :param tid: The id of the environment
    :param limit: Limit the number of versions that are returned
    :param start: The lower limit for the order by column (exclusive).
                Only one of 'start' and 'end' should be specified at the same time.
    :param end: The upper limit for the order by column (exclusive).
                Only one of 'start' and 'end' should be specified at the same time.
    :param filter: Filter the list of returned desired state versions.
                Filtering by 'version' range, 'date' range and 'status' is supported.
    :param sort: Return the results sorted according to the parameter value.
                Only sorting by 'version' is supported.
                The following orders are supported: 'asc', 'desc'
    :return: A list of all matching compile reports
    :raise NotFound: This exception is raised when the referenced environment is not found
    :raise BadRequest: When the parameters used for filtering, sorting or paging are not valid
    """


@typedmethod(
    path="/desiredstate/<version>/promote",
    operation="POST",
    arg_options=methods.ENV_OPTS,
    client_types=[ClientType.api],
    api_version=2,
)
def promote_desired_state_version(
    tid: uuid.UUID, version: int, trigger_method: Optional[model.PromoteTriggerMethod] = None
) -> None:
    """
    Promote a desired state version, making it the active version in the environment.

    :param tid: The id of the environment
    :param version: The number of the version to promote
    :param trigger_method: If set to 'push_incremental_deploy' or 'push_full_deploy',
        the agents will perform an incremental or full deploy, respectively.
        If set to 'no_push', the new version is not pushed to the agents.
        If the parameter is not set (or set to null), the new version is pushed and
        the environment setting 'environment_agent_trigger_method' decides if the deploy should be full or incremental
    """


@typedmethod(
    path="/desiredstate/<version>",
    operation="GET",
    arg_options=methods.ENV_OPTS,
    client_types=[ClientType.api],
    api_version=2,
)
def get_resources_in_version(
    tid: uuid.UUID,
    version: int,
    limit: Optional[int] = None,
    first_id: Optional[model.ResourceVersionIdStr] = None,
    last_id: Optional[model.ResourceVersionIdStr] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    filter: Optional[Dict[str, List[str]]] = None,
    sort: str = "resource_type.desc",
) -> List[model.VersionedResource]:
    """
    Get the resources that belong to a specific version.

    :param tid: The id of the environment
    :param version: The version number
    :param limit: Limit the number of resources that are returned
    :param first_id: The resource_version_id to use as a continuation token for paging, in combination with the 'start' value,
            because the order by column might contain non-unique values
    :param last_id: The resource_version_id to use as a continuation token for paging, in combination with the 'end' value,
            because the order by column might contain non-unique values
    :param start: The lower limit for the order by column (exclusive).
                Only one of 'start' and 'end' should be specified at the same time.
    :param end: The upper limit for the order by column (exclusive).
                Only one of 'start' and 'end' should be specified at the same time.
    :param filter: Filter the list of returned resources.
                The following options are available:
                agent: filter by the agent name of the resource
                resource_type: filter by the type of the resource
                resource_id_value: filter by the attribute values of the resource
    :param sort: Return the results sorted according to the parameter value.
                The following sorting attributes are supported: 'resource_type', 'agent', 'resource_id_value'.
                The following orders are supported: 'asc', 'desc'
    :return: A list of all matching resources
    :raise NotFound: This exception is raised when the referenced environment is not found
    :raise BadRequest: When the parameters used for filtering, sorting or paging are not valid
    """


@typedmethod(
    path="/desiredstate/diff/<from_version>/<to_version>",
    operation="GET",
    arg_options=methods.ENV_OPTS,
    client_types=[ClientType.api],
    api_version=2,
)
def get_diff_of_versions(
    tid: uuid.UUID,
    from_version: int,
    to_version: int,
) -> List[model.ResourceDiff]:
    """
    Compare two versions of desired states, and provide the difference between them,
    with regard to their resources and the attributes of these resources.
    Resources that are the same in both versions are not mentioned in the results.

    A resource diff describes whether the resource was 'added', 'modified' or 'deleted',
    and what the values of their attributes were in the versions.
    The values are also returned in a stringified, easy to compare way,
    which can be used to calculate a `git diff`-like summary of the changes.

    :param tid: The id of the environment
    :param from_version: The (lower) version number to compare
    :param to_version: The other (higher) version number to compare
    :return: The resource diffs between from_version and to_version
    :raise NotFound: This exception is raised when the referenced environment or versions are not found
    :raise BadRequest: When the version parameters are not valid
    """


@typedmethod(
    path="/desiredstate/<version>/resource/<rid>",
    operation="GET",
    arg_options=methods.ENV_OPTS,
    client_types=[ClientType.api],
    api_version=2,
)
def versioned_resource_details(tid: uuid.UUID, version: int, rid: model.ResourceIdStr) -> model.VersionedResourceDetails:
    """
    :param tid: The id of the environment
    :param version: The version number of the resource
    :param rid: The id of the resource
    :return: The details of a specific version of a resource
    :raise NotFound: This exception is raised when the referenced environment or resource is not found
    """


@typedmethod(
    path="/parameters",
    operation="GET",
    arg_options=methods.ENV_OPTS,
    client_types=[ClientType.api],
    api_version=2,
)
def get_parameters(
    tid: uuid.UUID,
    limit: Optional[int] = None,
    first_id: Optional[uuid.UUID] = None,
    last_id: Optional[uuid.UUID] = None,
    start: Optional[Union[datetime.datetime, str]] = None,
    end: Optional[Union[datetime.datetime, str]] = None,
    filter: Optional[Dict[str, List[str]]] = None,
    sort: str = "name.asc",
) -> List[model.Parameter]:
    """
    List the parameters in an environment

    :param tid: The id of the environment
    :param limit: Limit the number of parameters that are returned
    :param first_id: The parameter id to use as a continuation token for paging, in combination with the 'start' value,
        because the order by column might contain non-unique values
    :param last_id: The parameter id to use as a continuation token for paging, in combination with the 'end' value,
        because the order by column might contain non-unique values
    :param start: The lower limit for the order by column (exclusive). Only one of 'start' and 'end' should be specified at the
        same time.
    :param end: The upper limit for the order by column (exclusive). Only one of 'start' and 'end' should be specified at the
        same time.
    :param filter: Filter the list of returned parameters.

        The following options are available:
            * name: filter by the name of the parameter
            * source: filter by the source of the parameter
            * updated: filter by the updated time of the parameter
    :param sort: Return the results sorted according to the parameter value.
        The following sorting attributes are supported: 'name', 'source', 'updated'.
        The following orders are supported: 'asc', 'desc'
    :return: A list of all matching parameters
    :raise NotFound: This exception is raised when the referenced environment is not found
    :raise BadRequest: When the parameters used for filtering, sorting or paging are not valid
    """


@typedmethod(
    path="/facts",
    operation="GET",
    arg_options=methods.ENV_OPTS,
    client_types=[ClientType.api],
    api_version=2,
)
def get_all_facts(
    tid: uuid.UUID,
    limit: Optional[int] = None,
    first_id: Optional[uuid.UUID] = None,
    last_id: Optional[uuid.UUID] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    filter: Optional[Dict[str, List[str]]] = None,
    sort: str = "name.asc",
) -> List[model.Fact]:
    """
    List the facts in an environment.

    :param tid: The id of the environment
    :param limit: Limit the number of facts that are returned
    :param first_id: The fact id to use as a continuation token for paging, in combination with the 'start' value,
            because the order by column might contain non-unique values
    :param last_id: The fact id to use as a continuation token for paging, in combination with the 'end' value,
            because the order by column might contain non-unique values
    :param start: The lower limit for the order by column (exclusive).
                Only one of 'start' and 'end' should be specified at the same time.
    :param end: The upper limit for the order by column (exclusive).
                Only one of 'start' and 'end' should be specified at the same time.
    :param filter: Filter the list of returned facts.
                The following options are available:
                name: filter by the name of the fact
                resource_id: filter by the resource_id of the fact
    :param sort: Return the results sorted according to the parameter value.
                The following sorting attributes are supported: 'name', 'resource_id'.
                The following orders are supported: 'asc', 'desc'
    :return: A list of all matching facts
    :raise NotFound: This exception is raised when the referenced environment is not found
    :raise BadRequest: When the parameters used for filtering, sorting or paging are not valid
    """


# Dryrun related methods


@typedmethod(
    path="/dryrun/<version>", operation="POST", arg_options=methods.ENV_OPTS, client_types=[ClientType.api], api_version=2
)
def dryrun_trigger(tid: uuid.UUID, version: int) -> uuid.UUID:
    """
    Trigger a new dryrun

    :param tid: The id of the environment
    :param version: The version of the configuration model to execute the dryrun for
    :raise NotFound: This exception is raised when the referenced environment or version is not found
    :return: The id of the new dryrun
    """


@typedmethod(
    path="/dryrun/<version>", operation="GET", arg_options=methods.ENV_OPTS, client_types=[ClientType.api], api_version=2
)
def list_dryruns(tid: uuid.UUID, version: int) -> List[model.DryRun]:
    """
    Query a list of dry runs for a specific version

    :param tid: The id of the environment
    :param version: The configuration model version to return dryruns for
    :raise NotFound: This exception is raised when the referenced environment or version is not found
    :return: The list of dryruns for the specified version in descending order by date
    """


@typedmethod(
    path="/dryrun/<version>/<report_id>",
    operation="GET",
    arg_options=methods.ENV_OPTS,
    client_types=[ClientType.api],
    api_version=2,
)
def get_dryrun_diff(tid: uuid.UUID, version: int, report_id: uuid.UUID) -> model.DryRunReport:
    """
    Get the report of a dryrun, describing the changes a deployment would make,
    with the difference between the current and target states provided in a form similar to the desired state diff endpoint.

    :param tid: The id of the environment
    :param version: The version of the configuration model the dryrun belongs to
    :param report_id: The dryrun id to calculate the diff for
    :raise NotFound: This exception is raised when the referenced environment or version is not found
    :return: The dryrun report, with a summary and the list of differences.
    """


@typedmethod(
    path="/notification",
    operation="GET",
    arg_options=methods.ENV_OPTS,
    client_types=[ClientType.api],
    api_version=2,
)
def list_notifications(
    tid: uuid.UUID,
    limit: Optional[int] = None,
    first_id: Optional[uuid.UUID] = None,
    last_id: Optional[uuid.UUID] = None,
    start: Optional[datetime.datetime] = None,
    end: Optional[datetime.datetime] = None,
    filter: Optional[Dict[str, List[str]]] = None,
    sort: str = "created.desc",
) -> List[model.Notification]:
    """
    List the notifications in an environment.

    :param tid: The id of the environment
    :param limit: Limit the number of notifications that are returned
    :param first_id: The notification id to use as a continuation token for paging, in combination with the 'start' value,
            because the order by column might contain non-unique values
    :param last_id: The notification id to use as a continuation token for paging, in combination with the 'end' value,
            because the order by column might contain non-unique values
    :param start: The lower limit for the order by column (exclusive).
                Only one of 'start' and 'end' should be specified at the same time.
    :param end: The upper limit for the order by column (exclusive).
                Only one of 'start' and 'end' should be specified at the same time.
    :param filter: Filter the list of returned notifications.
                The following options are available:
                read: Whether the notification was read or not
                cleared: Whether the notification was cleared or not
                severity: Filter by the severity field of the notifications
                title: Filter by the title of the notifications
                message: Filter by the message of the notifications
    :param sort: Return the results sorted according to the parameter value.
                Only sorting by the 'created' date is supported.
                The following orders are supported: 'asc', 'desc'
    :return: A list of all matching notifications
    :raise NotFound: This exception is raised when the referenced environment is not found
    :raise BadRequest: When the parameters used for filtering or paging are not valid
    """


@typedmethod(
    path="/notification/<notification_id>",
    operation="GET",
    arg_options=methods.ENV_OPTS,
    client_types=[ClientType.api],
    api_version=2,
)
def get_notification(
    tid: uuid.UUID,
    notification_id: uuid.UUID,
) -> model.Notification:
    """
    Get a single notification

    :param tid: The id of the environment
    :param notification_id: The id of the notification
    :return: The notification with the specified id
    :raise NotFound: When the referenced environment or notification is not found
    """


@typedmethod(
    path="/notification/<notification_id>",
    operation="PATCH",
    arg_options=methods.ENV_OPTS,
    client_types=[ClientType.api],
    api_version=2,
)
def update_notification(
    tid: uuid.UUID,
    notification_id: uuid.UUID,
    read: Optional[bool] = None,
    cleared: Optional[bool] = None,
) -> model.Notification:
    """
    Update a notification by setting its flags

    :param tid: The id of the environment
    :param notification_id: The id of the notification to update
    :param read: Whether the notification has been read
    :param cleared: Whether the notification has been cleared
    :return: The updated notification
    :raise NotFound: When the referenced environment or notification is not found
    """


@typedmethod(
    path="/code/<version>",
    operation="GET",
    agent_server=True,
    arg_options=methods.ENV_OPTS,
    client_types=[ClientType.agent],
    api_version=2,
)
def get_source_code(tid: uuid.UUID, version: int, resource_type: str) -> List[model.Source]:
    """
    Get the code for the given version and the given resource
    :param tid: The id of the environment
    :param version: The id of the model version
    :param resource_type: The type name of the resource
    :raises NotFound: Raised when the version or type is not found
    """


@typedmethod(
    path="/metrics",
    operation="GET",
    arg_options=methods.ENV_OPTS,
    client_types=[ClientType.api],
    api_version=2,
)
def get_environment_metrics(
    tid: uuid.UUID,
    metrics: List[str],
    start_interval: datetime.datetime,
    end_interval: datetime.datetime,
    nb_datapoints: int,
) -> model.EnvironmentMetricsResult:
    """
    Obtain metrics about the given environment for the given time interval.

    :param tid: The id of the environment for which the metrics have to be collected.
    :param metrics: List of names of metrics that have to be returned.
    :param start_interval: The start of the time window for which the metrics should be returned.
    :param end_interval: The end of the time window for which the metrics should be returned.
    :param nb_datapoints: The amount of datapoint that will be returned within the given time interval for each metric.
    """
