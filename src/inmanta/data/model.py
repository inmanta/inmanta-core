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
import pydantic.schema
from pydantic import Extra, validator
from pydantic.fields import ModelField

import inmanta
import inmanta.ast.export as ast_export
import inmanta.data
from inmanta import const, protocol, resources
from inmanta.stable_api import stable_api
from inmanta.types import ArgumentTypes, JsonType, SimpleTypes, StrictNonIntBool

# This reference to the actual pydantic field_type_schema method is only loaded once
old_field_type_schema = pydantic.schema.field_type_schema


def patch_pydantic_field_type_schema() -> None:
    """
    This ugly patch fixes the serialization of models containing Optional in them.
    https://github.com/samuelcolvin/pydantic/issues/1270
    """

    def patch_nullable(field: ModelField, **kwargs):
        f_schema, definitions, nested_models = old_field_type_schema(field, **kwargs)
        if field.allow_none:
            f_schema["nullable"] = True
        return f_schema, definitions, nested_models

    pydantic.schema.field_type_schema = patch_nullable


def api_boundary_datetime_normalizer(value: datetime.datetime) -> datetime.datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=datetime.timezone.utc)
    else:
        return value


def validator_timezone_aware_timestamps(value: object) -> object:
    """
    A Pydantic validator to ensure that all datetime times are timezone aware.
    """
    if isinstance(value, datetime.datetime):
        return api_boundary_datetime_normalizer(value)
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


class CompileRunBase(BaseModel):
    id: uuid.UUID
    remote_id: Optional[uuid.UUID]
    environment: uuid.UUID
    requested: Optional[datetime.datetime]
    started: Optional[datetime.datetime]

    do_export: bool
    force_update: bool
    metadata: JsonType
    environment_variables: Dict[str, str]

    partial: bool
    removed_resource_sets: list[str]

    exporter_plugin: Optional[str]

    notify_failed_compile: Optional[bool]
    failed_compile_message: Optional[str]


class CompileRun(CompileRunBase):
    compile_data: Optional[CompileData]


class CompileReport(CompileRunBase):
    completed: Optional[datetime.datetime]
    success: Optional[bool]
    version: Optional[int]


class CompileRunReport(BaseModel):
    id: uuid.UUID
    started: datetime.datetime
    completed: Optional[datetime.datetime]
    command: str
    name: str
    errstream: str
    outstream: str
    returncode: Optional[int]


class CompileDetails(CompileReport):
    compile_data: Optional[CompileData]
    reports: Optional[List[CompileRunReport]]


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

    @validator("current", "desired")
    @classmethod
    def check_serializable(cls, v: Optional[Any]) -> Optional[Any]:
        """
        Verify whether the value is serializable (https://github.com/inmanta/inmanta-core/issues/3470)
        """
        try:
            protocol.common.json_encode(v)
        except TypeError:
            if inmanta.RUNNING_TESTS:
                # Fail the test when the value is not serializable
                raise Exception(f"Failed to serialize attribute {v}")
            else:
                # In production, try to cast the non-serializable value to str to prevent the handler from failing.
                return str(v)
        return v


EnvSettingType = Union[StrictNonIntBool, int, float, str, Dict[str, Union[str, int, StrictNonIntBool]]]


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
    description: Optional[str]
    icon: Optional[str]


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


class ResourceMinimal(BaseModel):
    """
    Represents a resource object as it comes in over the API. Provides strictly required validation only.
    """

    id: ResourceVersionIdStr

    @classmethod
    def create_with_version(cls, new_version: int, id: ResourceIdStr, attributes: Dict[str, object]) -> "ResourceMinimal":
        """
        Create a new ResourceMinimal from the given attributes, but ensure that the given version
        is set on all the fields that hold the version number of the model.
        """
        if "requires" not in attributes:
            raise ValueError("'requires' attribute is missing in kwargs")
        new_attributes = attributes.copy()
        new_attributes["version"] = new_version
        new_attributes["id"] = resources.Id.set_version_in_id(id, new_version)
        new_attributes["requires"] = [
            resources.Id.set_version_in_id(r, new_version=new_version) for r in attributes["requires"]
        ]
        return cls(**new_attributes)

    def copy_with_new_version(self, new_version: int) -> "ResourceMinimal":
        """
        Create a new ResourceMinimal by cloning this ResourceMinimal. The returned object
        will have the given new_version set on all the fields that hold the version number
        of the mode.
        """
        return self.create_with_version(
            new_version=new_version,
            id=resources.Id.parse_id(self.id).resource_str(),
            attributes={k: v for k, v in self.dict().items() if k != "id"},
        )

    @classmethod
    @validator("id")
    def id_is_resource_version_id(cls, v):
        if resources.Id.is_resource_version_id(v):
            return v
        raise ValueError(f"id {v} is not of type ResourceVersionIdStr")

    def get_resource_id_str(self) -> ResourceIdStr:
        return resources.Id.parse_id(self.id).resource_str()

    class Config:
        extra = Extra.allow


class Resource(BaseModel):
    environment: uuid.UUID
    model: int
    resource_id: ResourceIdStr
    resource_type: ResourceType
    resource_version_id: ResourceVersionIdStr
    resource_id_value: str
    agent: str
    last_deploy: Optional[datetime.datetime]
    attributes: JsonType
    status: const.ResourceState
    resource_set: Optional[str]


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


class ResourceDeploySummary(BaseModel):
    """
    :param total: The total number of resources
    :param by_state: The number of resources by state in the latest released version
    """

    total: int
    by_state: Dict[str, int]

    @classmethod
    def create_from_db_result(cls, summary_by_state: Dict[str, int]) -> "ResourceDeploySummary":
        full_summary_by_state = cls._ensure_summary_has_all_states(summary_by_state)
        total = cls._count_all_resources(full_summary_by_state)
        return ResourceDeploySummary(by_state=full_summary_by_state, total=total)

    @classmethod
    def _ensure_summary_has_all_states(cls, summary_by_state: Dict[str, int]) -> Dict[str, int]:
        full_summary = summary_by_state.copy()
        for state in const.ResourceState:
            if state not in summary_by_state.keys() and state != const.ResourceState.dry:
                full_summary[state] = 0
        return full_summary

    @classmethod
    def _count_all_resources(cls, summary_by_state: Dict[str, int]) -> int:
        return sum(resource_count for resource_count in summary_by_state.values())


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

    level: const.LogLevel
    msg: str
    args: List[Optional[ArgumentTypes]] = []
    kwargs: JsonType = {}
    timestamp: datetime.datetime


class ResourceIdDetails(BaseModel):
    resource_type: ResourceType
    agent: str
    attribute: str
    resource_id_value: str


class OrphanedResource(str, Enum):
    orphaned = "orphaned"


class StrEnum(str, Enum):
    """Enum where members are also (and must be) strs"""


ReleasedResourceState = StrEnum(
    "ReleasedResourceState", [(i.name, i.value) for i in chain(const.ResourceState, OrphanedResource)]
)


class VersionedResource(BaseModel):
    resource_id: ResourceIdStr
    resource_version_id: ResourceVersionIdStr
    id_details: ResourceIdDetails
    requires: List[ResourceVersionIdStr]

    @property
    def all_fields(self) -> Dict[str, Any]:
        return {**self.dict(), **self.id_details.dict()}


class LatestReleasedResource(VersionedResource):
    status: ReleasedResourceState


class PagingBoundaries:
    """Represents the lower and upper bounds that should be used for the next and previous pages
    when listing domain entities"""

    def __init__(
        self,
        start: Optional["inmanta.data.PRIMITIVE_SQL_TYPES"],  # Can be none if user selected field is nullable
        end: Optional["inmanta.data.PRIMITIVE_SQL_TYPES"],  # Can be none if user selected field is nullable
        first_id: Optional["inmanta.data.PRIMITIVE_SQL_TYPES"],  # Can be none if single keyed
        last_id: Optional["inmanta.data.PRIMITIVE_SQL_TYPES"],  # Can be none if single keyed
    ) -> None:
        self.start = start
        self.end = end
        self.first_id = first_id
        self.last_id = last_id


class ResourceDetails(BaseModel):
    """The details of a resource
    :param resource_id: The id of the resource
    :param resource_type: The type of the resource
    :param agent: The agent associated with this resource
    :param id_attribute: The name of the identifying attribute of the resource
    :param id_attribute_value: The value of the identifying attribute of the resource
    :param attributes: The attributes of the resource
    """

    resource_id: ResourceIdStr
    resource_type: ResourceType
    agent: str
    id_attribute: str
    id_attribute_value: str
    attributes: JsonType


class VersionedResourceDetails(ResourceDetails):
    """The details of a resource version
    :param resource_version_id: The id of the resource
    :param version: The version of the resource
    """

    resource_version_id: ResourceVersionIdStr
    version: int


class ReleasedResourceDetails(ResourceDetails):
    """The details of a released resource
    :param last_deploy: The value of the last_deploy on the latest released version of the resource
    :param first_generated_time: The first time this resource was generated
    :param first_generated_version: The first model version this resource was in
    :param status: The current status of the resource
    :param requires_status: The id and status of the resources this resource requires
    """

    last_deploy: Optional[datetime.datetime]
    first_generated_time: datetime.datetime
    first_generated_version: int
    status: ReleasedResourceState
    requires_status: Dict[ResourceIdStr, ReleasedResourceState]


class ResourceHistory(BaseModel):
    resource_id: ResourceIdStr
    date: datetime.datetime
    attributes: JsonType
    attribute_hash: str
    requires: List[ResourceIdStr]


class ResourceLog(LogLine):
    action_id: uuid.UUID
    action: const.ResourceAction


class ResourceDiffStatus(str, Enum):
    added = "added"
    modified = "modified"
    deleted = "deleted"
    unmodified = "unmodified"
    agent_down = "agent_down"
    undefined = "undefined"
    skipped_for_undefined = "skipped_for_undefined"


class AttributeDiff(BaseModel):
    """
    :param from_value: The value of the attribute in the earlier version
    :param to_value: The value of the attribute in the later version
    :param from_value_compare: A stringified, diff-friendly form of the 'from_value' field
    :param to_value_compare: A stringified, diff-friendly form of the 'to_value' field
    """

    from_value: Optional[object] = None
    to_value: Optional[object] = None
    from_value_compare: str
    to_value_compare: str


class ResourceDiff(BaseModel):
    """
    :param resource_id: The id of the resource the diff is about (without version)
    :param attributes: The diff between the attributes of two versions of the resource
    :param status: The kind of diff between the versions of the resource
    """

    resource_id: ResourceIdStr
    attributes: Dict[str, AttributeDiff]
    status: ResourceDiffStatus


class Parameter(BaseModel):
    id: uuid.UUID
    name: str
    value: str
    environment: uuid.UUID
    source: str
    updated: Optional[datetime.datetime]
    metadata: Optional[JsonType]


class Fact(Parameter):
    resource_id: ResourceIdStr


class Agent(BaseModel):
    """
    :param environment: Id of the agent's environment
    :param name: The name of the agent
    :param last_failover: The time of the last failover
    :param paused: Whether the agent is paused or not
    :param unpause_on_resume: Whether the agent should be unpaused when the environment is resumed
    :param status: The current status of the agent
    :param process_id: The id of the agent process that belongs to this agent, if there is one
    :param process_name: The name of the agent process that belongs to this agent, if there is one
    """

    environment: uuid.UUID
    name: str
    last_failover: Optional[datetime.datetime]
    paused: bool
    process_id: Optional[uuid.UUID]
    process_name: Optional[str]
    unpause_on_resume: Optional[bool]
    status: const.AgentStatus


class AgentProcess(BaseModel):
    sid: uuid.UUID
    hostname: str
    environment: uuid.UUID
    first_seen: Optional[datetime.datetime]
    last_seen: Optional[datetime.datetime]
    expired: Optional[datetime.datetime]
    state: Optional[Dict[str, Union[Dict[str, List[str]], Dict[str, str], Dict[str, float], str]]]


class DesiredStateLabel(BaseModel):
    name: str
    message: str


class DesiredStateVersion(BaseModel):
    version: int
    date: datetime.datetime
    total: int
    labels: List[DesiredStateLabel]
    status: const.DesiredStateVersionStatus


class NoPushTriggerMethod(str, Enum):
    no_push = "no_push"


PromoteTriggerMethod = StrEnum(
    "PromoteTriggerMethod", [(i.name, i.value) for i in chain(const.AgentTriggerMethod, NoPushTriggerMethod)]
)


class DryRun(BaseModel):
    id: uuid.UUID
    environment: uuid.UUID
    model: int
    date: Optional[datetime.datetime]
    total: int = 0
    todo: int = 0


class DryRunReport(BaseModel):
    summary: DryRun
    diff: List[ResourceDiff]


class Notification(BaseModel):
    """
    :param id: The id of this notification
    :param environment: The environment this notification belongs to
    :param created: The date the notification was created at
    :param title: The title of the notification
    :param message: The actual text of the notification
    :param severity: The severity of the notification
    :param uri: A link to an api endpoint of the server, that is relevant to the message,
                and can be used to get further information about the problem.
                For example a compile related problem should have the uri: `/api/v2/compilereport/<compile_id>`
    :param read: Whether the notification was read or not
    :param cleared: Whether the notification was cleared or not
    """

    id: uuid.UUID
    environment: uuid.UUID
    created: datetime.datetime
    title: str
    message: str
    severity: const.NotificationSeverity
    uri: str
    read: bool
    cleared: bool


class Source(BaseModel):
    """Model for source code"""

    hash: str
    is_byte_code: bool
    module_name: str
    requirements: List[str]


class EnvironmentMetricsResult(BaseModel):
    """
    A container for metrics as returned by the /metrics endpoint.

    :param start: The starting of the requested aggregation interval.
    :param end: The end of the requested aggregation interval.
    :param timestamps: The timestamps that belongs to the aggregated metrics present in the `metrics` dictionary.
    :param metrics: A dictionary that maps the name of a metric to a list of aggregated datapoints. For metrics that are not
                    grouped on a specific property, this list only contains the values of the metrics. For metrics that
                    are grouped by a specific property, this list contains a dictionary where the key is the grouping
                    attribute and the value is the value of the metric. The value is None when no data is available
                    for that specific time window.
    """

    start: datetime.datetime
    end: datetime.datetime
    timestamps: List[datetime.datetime]
    metrics: Dict[str, List[Optional[Union[float, Dict[str, float]]]]]
