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
from typing import Dict, List, Optional, Union

from inmanta.const import AgentAction, ClientType
from inmanta.data import model
from inmanta.protocol.common import ReturnValue

from . import methods
from .decorators import typedmethod
from .openapi.model import OpenAPI


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
def project_list() -> List[model.Project]:
    """
        Create a list of projects
    """


@typedmethod(path="/project/<id>", operation="GET", client_types=[ClientType.api], api_version=2)
def project_get(id: uuid.UUID) -> model.Project:
    """
        Get a project and a list of the ids of all environments
    """


# Methods for working with environments
@typedmethod(path="/environment", operation="PUT", client_types=[ClientType.api], api_version=2)
def environment_create(
    project_id: uuid.UUID,
    name: str,
    repository: Optional[str] = None,
    branch: Optional[str] = None,
    environment_id: uuid.UUID = None,
) -> model.Environment:
    """
        Create a new environment

        :param project_id: The id of the project this environment belongs to
        :param name: The name of the environment
        :param repository: The url (in git form) of the repository
        :param branch: The name of the branch in the repository
        :param environment_id: A unique environment id, if none an id is allocated by the server
    """


@typedmethod(path="/environment/<id>", operation="POST", client_types=[ClientType.api], api_version=2)
def environment_modify(id: uuid.UUID, name: str, repository: str = None, branch: str = None) -> model.Environment:
    """
        Modify the given environment

        :param id: The id of the environment
        :param name: The name of the environment
        :param repository: The url (in git form) of the repository
        :param branch: The name of the branch in the repository
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
def environment_list() -> List[model.Environment]:
    """
        Create a list of environments
    """


@typedmethod(
    path="/environment/<id>",
    operation="GET",
    client_types=[ClientType.api],
    arg_options={"id": methods.ArgOption(getter=methods.add_env)},
    api_version=2,
)
def environment_get(id: uuid.UUID) -> model.Environment:
    """
        Get an environment and all versions associated

        :param id: The id of the environment to return
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
def get_api_docs(format: Optional[str] = None) -> ReturnValue[Union[OpenAPI, str]]:
    """
       Get the OpenAPI definition of the API
       :param format: Use 'openapi' to get the schema in json format
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
                        * pause: A paused agent cannot execute any deploy operations.
                        * unpause: A unpaused agent will be able to execute deploy operations.
    """


@typedmethod(
    path="/agents/<action>", operation="POST", arg_options=methods.ENV_OPTS, client_types=[ClientType.api], api_version=2
)
def all_agents_action(tid: uuid.UUID, action: AgentAction) -> None:
    """
        Execute an action on all agents in the given environment.

        :param tid: The environment of the agents.
        :param action: The type of action that should be executed on the agents
                        * pause: A paused agent cannot execute any deploy operations.
                        * unpause: A unpaused agent will be able to execute deploy operations.
    """


@typedmethod(path="/agentmap", api=False, server_agent=True, operation="POST", client_types=[], api_version=2)
def update_agent_map(agent_map: Dict[str, str]) -> None:
    """
        Notify an agent about the fact that the autostart_agent_map has been updated.

        :param agent_map: The content of the new autostart_agent_map
    """
