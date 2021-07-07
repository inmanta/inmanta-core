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
from itertools import chain
from typing import Any, ClassVar, Dict, List, NewType, Optional, Union

import pydantic

import inmanta.ast.export as ast_export
from inmanta import const
from inmanta.stable_api import stable_api
from inmanta.types import ArgumentTypes, JsonType, SimpleTypes, StrictNonIntBool


def validator_timezone_aware_timestamps(value: object) -> object:
    """
    A Pydantic validator to ensure that all datetime times are timezone aware.
    """
    if isinstance(value, datetime.datetime) and value.tzinfo is None:
        return value.replace(tzinfo=datetime.timezone.utc)
    else:
        return value


@stable_api
class BaseModel(pydantic.BaseModel):
    """
    Base class for all data objects in Inmanta
    """

    _normalize_timestamps: ClassVar[classmethod] = pydantic.validator("*", allow_reuse=True)(
        validator_timezone_aware_timestamps
    )

    class Config:
        """
        Pydantic config.
        """

        # Populate models with the value property of enums, rather than the raw enum.
        # This is useful to serialise model.dict() later
        use_enum_values = True


class ExtensionStatus(BaseModel):
    """
    Status response for extensions loaded in the server
    """

    name: str
    version: str
    package: str


class SliceStatus(BaseModel):
    """
    Status response for slices loaded in the the server
    """

    name: str
    status: Dict[str, ArgumentTypes]


class FeatureStatus(BaseModel):
    """
    Status of the feature
    """

    slice: str
    name: str
    value: Optional[Any]


class StatusResponse(BaseModel):
    """
    Response for the status method call
    """

    product: str
    edition: str
    version: str
    license: Union[str, Dict[str, SimpleTypes]]
    extensions: List[ExtensionStatus]
    slices: List[SliceStatus]
    features: List[FeatureStatus]


@stable_api
class CompileData(BaseModel):
    """
    Top level structure of compiler data to be exported.
    """

    errors: List[ast_export.Error]
    """
        All errors occurred while trying to compile.
    """


class CompileRun(BaseModel):
    id: uuid.UUID
    remote_id: Optional[uuid.UUID]
    environment: uuid.UUID
    requested: Optional[datetime.datetime]
    started: Optional[datetime.datetime]

    do_export: bool
    force_update: bool
    metadata: JsonType
    environment_variables: Dict[str, str]

    compile_data: Optional[CompileData]


ResourceVersionIdStr = NewType("ResourceVersionIdStr", str)  # Part of the stable API
"""
    The resource id with the version included.
"""

ResourceIdStr = NewType("ResourceIdStr", str)  # Part of the stable API
"""
    The resource id without the version
"""

ResourceType = NewType("ResourceType", str)
"""
    The type of the resource
"""


class AttributeStateChange(BaseModel):
    """
    Changes in the attribute
    """

    current: Optional[Any] = None
    desired: Optional[Any] = None


EnvSettingType = Union[StrictNonIntBool, int, str, Dict[str, Union[str, int, StrictNonIntBool]]]


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
    settings: Dict[str, EnvSettingType]
    halted: bool


class Project(BaseModel):
    """
    An inmanta environment.
    """

    id: uuid.UUID
    name: str
    environments: List[Environment]


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
    """

    name: str
    type: str
    default: EnvSettingType
    doc: str
    recompile: bool
    update_model: bool
    agent_restart: bool
    allowed_values: Optional[List[EnvSettingType]]


class EnvironmentSettingsReponse(BaseModel):
    settings: Dict[str, EnvSettingType]
    definition: Dict[str, EnvironmentSetting]


class ModelMetadata(BaseModel):
    """Model metadata"""

    inmanta_compile_state: const.Compilestate = const.Compilestate.success
    message: str
    type: str
    extra_data: Optional[JsonType]

    class Config:
        fields = {"inmanta_compile_state": {"alias": "inmanta:compile:state"}}


class ModelVersionInfo(BaseModel):
    """Version information that can be associated with an orchestration model

    :param export_metadata: Metadata associated with this version
    :param model: A serialization of the complete orchestration model
    """

    export_metadata: ModelMetadata
    model: Optional[JsonType]


class Resource(BaseModel):
    environment: uuid.UUID
    model: int
    resource_id: ResourceVersionIdStr
    resource_type: ResourceType
    resource_version_id: ResourceVersionIdStr
    resource_id_value: str
    agent: str
    last_deploy: Optional[datetime.datetime]
    attributes: JsonType
    status: const.ResourceState


class ResourceAction(BaseModel):
    environment: uuid.UUID
    version: int
    resource_version_ids: List[ResourceVersionIdStr]
    action_id: uuid.UUID
    action: const.ResourceAction
    started: datetime.datetime
    finished: Optional[datetime.datetime]
    messages: Optional[List[JsonType]]
    status: Optional[const.ResourceState]
    changes: Optional[JsonType]
    change: Optional[const.Change]
    send_event: Optional[bool] = None  # Deprecated field


class LogLine(BaseModel):
    class Config:
        """
        Pydantic config.
        """

        # Override the setting from the BaseModel class as such that the level field is
        # serialises using the name of the enum instead of its value. This is required
        # to make sure that data sent to the API endpoints resource_action_update
        # and resource_deploy_done are serialized consistently using the name of the enum.
        use_enum_values = False

    @pydantic.validator("level", pre=True)
    def level_from_enum_attribute(cls, v: object) -> object:
        """
        Ensure that a LogLine object can be instantiated using pydantic when the level field
        is represented using the name of the enum instead of its value. This is required to
        make sure that a serialized version of this object passes pydantic validation.
        """
        if isinstance(v, str):
            try:
                return const.LogLevel[v]
            except KeyError:
                raise ValueError(f"Invalid enum value {v}. Valid values: {','.join([x.name for x in const.LogLevel])}")
        return v

    level: const.LogLevel
    msg: str
    args: List[Optional[ArgumentTypes]] = []
    kwargs: Dict[str, Optional[ArgumentTypes]] = {}
    timestamp: datetime.datetime


class ResourceIdDetails(BaseModel):
    resource_type: ResourceType
    agent: str
    attribute: str
    resource_id_value: str


class OrphanedResource(Enum):
    orphaned = "orphaned"


ReleasedResourceState = Enum("ReleasedResourceState", [(i.name, i.value) for i in chain(const.ResourceState, OrphanedResource)])


class LatestReleasedResource(BaseModel):
    resource_id: ResourceIdStr
    resource_version_id: ResourceVersionIdStr
    id_details: ResourceIdDetails
    requires: List[ResourceVersionIdStr]
    status: ReleasedResourceState

    @property
    def all_fields(self) -> Dict[str, Any]:
        return {**self.dict(), **self.id_details.dict()}


class PagingBoundaries:
    """Represents the lower and upper bounds that should be used for the next and previous pages
    when listing domain entities"""

    def __init__(
        self,
        start: Union[datetime.datetime, int, str],
        end: Union[datetime.datetime, int, str],
        first_id: Union[uuid.UUID, str],
        last_id: Union[uuid.UUID, str],
    ) -> None:
        self.start = start
        self.end = end
        self.first_id = first_id
        self.last_id = last_id


class ResourceDetails(BaseModel):
    """The details of a released resource
    :param last_deploy_finished: the time the last deploy of the resource was finished
    :param first_generated_time: the first time this resource was generated
    :param first_generated_version: the first model version this resource was in
    :param status: the current status of the resource
    :param requires_status: The id and status of the resources this resource requires
    """

    resource_id: ResourceIdStr
    resource_type: ResourceType
    agent: str
    attribute: str
    resource_id_value: str
    last_deploy_finished: Optional[datetime.datetime]
    first_generated_time: datetime.datetime
    first_generated_version: int
    attributes: JsonType
    status: const.ResourceState
    requires_status: Dict[ResourceVersionIdStr, const.ResourceState]
