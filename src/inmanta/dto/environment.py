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

import datetime
import uuid
from enum import Enum
from typing import Optional, Self, Union, assert_never

from inmanta.types import BaseModel as BaseModel

EnvSettingType = Union[bool, int, float, str, dict[str, Union[str, int, bool]]]


class Environment(BaseModel):
    """
    An inmanta environment.

    :note: repo_url and repo_branch will be moved to the settings.
    """

    id: uuid.UUID
    name: str
    project_id: uuid.UUID
    repo_url: str
    repo_branch: str
    settings: dict[str, EnvSettingType]
    halted: bool
    is_marked_for_deletion: bool = False
    description: Optional[str] = None
    icon: Optional[str] = None


class Project(BaseModel):
    """
    An inmanta project.
    """

    id: uuid.UUID
    name: str
    environments: list[Environment]


class EnvironmentSetting(BaseModel):
    """A class to define a new environment setting.

    :param name: The name of the setting.
    :param type: The type of the value. This type is mainly used for documentation purpose.
    :param default: An optional default value for this setting. When a default is set and the
                    is requested from the database, it will return the default value and also store
                    the default value in the database.
    :param doc: The documentation/help string for this setting
    :param recompile: Trigger a recompile of the model when a setting is updated?
    :param update_model: Update the configuration model (git pull on project and repos)
    :param agent_restart: Restart autostarted agents when this settings is updated.
    :param allowed_values: list of possible values (if type is enum)
    :param section: the section this option should be rendered in. optional for backward compatibility with <iso9
    """

    name: str
    type: str
    default: EnvSettingType
    doc: str
    recompile: bool
    update_model: bool
    agent_restart: bool
    allowed_values: Optional[list[EnvSettingType]] = None
    section: Optional[str] = None


class ProtectedBy(str, Enum):
    """
    An enum that indicates the reason why an environment setting can be protected.
    """

    # The environment setting is managed using the environment_settings property of the project.yml file.
    project_yml = "project.yml"

    def get_detailed_description(self) -> str:
        """
        Return a string that explains in detail why the environment setting is protected.
        """
        match self:
            case ProtectedBy.project_yml:
                return "Setting is managed by the project.yml file of the Inmanta project."
            case _ as unreachable:
                assert_never(unreachable)

    @classmethod
    def _missing_(cls: type[Self], value: object) -> Optional[Self]:
        """
        This is a workaround for the issue where the protocol layer inconsistently handles enums.
        Enums are serialized using their name, but deserialized using their value. This method makes
        sure that we can deserialize enums using their name.
        """
        return next((p for p in cls if p.name == value), None) if isinstance(value, str) else None


class EnvironmentSettingDefinitionAPI(EnvironmentSetting):
    """
    The definition of an environment setting as served out over the API.
    """

    protected: bool = False
    protected_by: ProtectedBy | None = None


class EnvironmentSettingDetails(BaseModel):
    """
    A class that stores the value and other metadata about an environment setting.

    :param value: The value of the environment setting.
    :param protected: True iff the environment setting cannot be updated using the normal
                      endpoints to update environment settings.
    :param protected_by: This field indicates the reason why the environment setting is protected.
                         This field is set to None if the environment setting is not protected.
    """

    value: EnvSettingType
    protected: bool = False
    protected_by: ProtectedBy | None = None


class EnvironmentSettingsReponse(BaseModel):

    settings: dict[str, EnvSettingType]
    definition: dict[str, EnvironmentSettingDefinitionAPI]


class EnvironmentMetricsResult(BaseModel):
    """
    A container for metrics as returned by the /metrics endpoint.

    :param start: The starting of the aggregation interval.
    :param end: The end of the aggregation interval.
    :param timestamps: The timestamps that belongs to the aggregated metrics present in the `metrics` dictionary.
    :param metrics: A dictionary that maps the name of a metric to a list of aggregated datapoints. For metrics that are not
                    grouped on a specific property, this list only contains the values of the metrics. For metrics that
                    are grouped by a specific property, this list contains a dictionary where the key is the grouping
                    attribute and the value is the value of the metric. The value is None when no data is available
                    for that specific time window.
    """

    start: datetime.datetime
    end: datetime.datetime
    timestamps: list[datetime.datetime]
    metrics: dict[str, list[Optional[Union[float, dict[str, float]]]]]
