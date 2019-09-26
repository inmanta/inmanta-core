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
from typing import List, Optional

from inmanta.data import model

from . import methods
from .decorators import typedmethod


# Method for working with projects
@typedmethod(path="/project", operation="PUT", client_types=["api"], api_version=2)
def project_create(name: str, project_id: uuid.UUID = None) -> model.Project:
    """
        Create a new project

        :param name: The name of the project
        :param project_id: A unique uuid, when it is not provided the server generates one
    """


@typedmethod(path="/project/<id>", operation="POST", client_types=["api"], api_version=2)
def project_modify(id: uuid.UUID, name: str) -> model.Project:
    """
        Modify the given project
    """


@typedmethod(path="/project/<id>", operation="DELETE", client_types=["api"], api_version=2)
def project_delete(id: uuid.UUID) -> None:
    """
        Delete the given project and all related data
    """


@typedmethod(path="/project", operation="GET", client_types=["api"], api_version=2)
def project_list() -> List[model.Project]:
    """
        Create a list of projects
    """


@typedmethod(path="/project/<id>", operation="GET", client_types=["api"], api_version=2)
def project_get(id: uuid.UUID) -> model.Project:
    """
        Get a project and a list of the ids of all environments
    """


# Methods for working with environments
@typedmethod(path="/environment", operation="PUT", client_types=["api"], api_version=2)
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


@typedmethod(path="/environment/<id>", operation="POST", client_types=["api"], api_version=2)
def environment_modify(id: uuid.UUID, name: str, repository: str = None, branch: str = None) -> model.Environment:
    """
        Modify the given environment

        :param id: The id of the environment
        :param name: The name of the environment
        :param repository: The url (in git form) of the repository
        :param branch: The name of the branch in the repository
    """


@typedmethod(path="/environment/<id>", operation="DELETE", client_types=["api"], api_version=2)
def environment_delete(id: uuid.UUID) -> None:
    """
        Delete the given environment and all related data
    """


@typedmethod(path="/environment", operation="GET", client_types=["api"], api_version=2)
def environment_list() -> List[model.Environment]:
    """
        Create a list of environments
    """


@typedmethod(
    path="/environment/<id>",
    operation="GET",
    client_types=["api"],
    arg_options={"id": methods.ArgOption(getter=methods.add_env)},
    api_version=2,
)
def environment_get(id: uuid.UUID) -> model.Environment:
    """
        Get an environment and all versions associated

        :param id: The id of the environment to return
    """
