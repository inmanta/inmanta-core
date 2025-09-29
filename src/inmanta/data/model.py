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
import json
import os
import typing
import urllib
import uuid
from collections import abc
from collections.abc import Sequence
from enum import Enum, StrEnum
from typing import ClassVar, Mapping, Optional, Self, Union, assert_never

import pydantic.schema
from pydantic import ConfigDict, Field, computed_field, field_validator, model_validator

import inmanta
import inmanta.ast.export as ast_export
import pydantic_core.core_schema
from inmanta import const, data, protocol, resources
from inmanta.stable_api import stable_api
from inmanta.types import ArgumentTypes
from inmanta.types import BaseModel as BaseModel  # Keep in place for backwards compat with <=ISO8
from inmanta.types import JsonType
from inmanta.types import ResourceIdStr as ResourceIdStr  # Keep in place for backwards compat with <=ISO8
from inmanta.types import ResourceType as ResourceType  # Keep in place for backwards compat with <=ISO8
from inmanta.types import ResourceVersionIdStr as ResourceVersionIdStr  # Keep in place for backwards compat with <=ISO8
from inmanta.types import SimpleTypes


class ExtensionStatus(BaseModel):
    """
    Status response for extensions loaded in the server
    """

    name: str
    version: str
    package: str


class ReportedStatus(StrEnum):
    OK = "OK"
    Warning = "Warning"
    Error = "Error"

    def __gt__(self, other: str) -> bool:
        # Determines the order of severity of the reported status
        order: list[str] = [ReportedStatus.OK, ReportedStatus.Warning, ReportedStatus.Error]
        if self not in order or other not in order:
            raise ValueError
        return order.index(self) > order.index(other)


class SliceStatus(BaseModel):
    """
    Status response for slices loaded in the server
    """

    name: str
    status: Mapping[str, ArgumentTypes | Mapping[str, ArgumentTypes]]
    reported_status: ReportedStatus
    message: str | None = None


class FeatureStatus(BaseModel):
    """
    Status of the feature
    """

    slice: str
    name: str
    value: Optional[object] = None


class StatusResponse(BaseModel):
    """
    Response for the status method call

    :param product: The name of the product.
    :param edition: The edition of the product.
    :param version: The version of the product.
    :param license: The license used by the product.
    :param extensions: The status of the extensions of the server
    :param slices: The status of the slices of the server.
    :param features: The status of the features offered by the slices of the server.
    :param status: The overall status of the server
    :param python_version: The python version used by the server.
    :param postgresql_version: The postgresql version used by the database slice
        None if it is not initialized or an error occurred with the database slice.
    """

    product: str
    edition: str
    version: str
    license: Union[str, dict[str, SimpleTypes]]
    extensions: list[ExtensionStatus]
    slices: list[SliceStatus]
    features: list[FeatureStatus]
    status: ReportedStatus
    python_version: str
    postgresql_version: str | None


@stable_api
class CompileData(BaseModel):
    """
    Top level structure of compiler data to be exported.
    """

    errors: list[ast_export.Error]
    """
        All errors occurred while trying to compile.
    """


class CompileRunBase(BaseModel):
    """
    :param requested_environment_variables: environment variables requested to be passed to the compiler
    :param mergeable_environment_variables: environment variables to be passed to the compiler.
            These env vars can be compacted over multiple compiles.
            If multiple values are compacted, they will be joined using spaces.
    :param environment_variables: environment variables passed to the compiler
    :param links: An object that contains relevant links to this compile.
        It is a dictionary where the key is something that identifies one or more links
        and the value is a list of urls. i.e. {"instances": ["link-1',"link-2"], "compiles": ["link-3"]}
    """

    id: uuid.UUID
    remote_id: Optional[uuid.UUID] = None
    environment: uuid.UUID
    requested: Optional[datetime.datetime] = None
    started: Optional[datetime.datetime] = None

    do_export: bool
    force_update: bool
    metadata: JsonType
    mergeable_environment_variables: dict[str, str]
    requested_environment_variables: dict[str, str]
    environment_variables: dict[str, str]

    partial: bool
    removed_resource_sets: list[str]

    exporter_plugin: Optional[str] = None

    notify_failed_compile: Optional[bool] = None
    failed_compile_message: Optional[str] = None
    links: dict[str, list[str]] = {}

    @pydantic.field_validator("environment_variables", mode="before")
    @classmethod
    def validate_environment_variables(cls, v: typing.Any, info: pydantic_core.core_schema.ValidationInfo) -> typing.Any:
        """
        Default the environment_variables to requested_environment_variables + mergeable_environment_variables

        This relies on the fact that fields are validated in the order they are declared!
        """
        if v is None:
            out = {}
            out.update(info.data["requested_environment_variables"])
            out.update(info.data["mergeable_environment_variables"])
            return out
        else:
            return v


class CompileRun(CompileRunBase):
    compile_data: Optional[CompileData] = None


class CompileReport(CompileRunBase):
    completed: Optional[datetime.datetime] = None
    success: Optional[bool] = None
    version: Optional[int] = None


class CompileRunReport(BaseModel):
    id: uuid.UUID
    started: datetime.datetime
    completed: Optional[datetime.datetime] = None
    command: str
    name: str
    errstream: str
    outstream: str
    returncode: Optional[int] = None


class CompileDetails(CompileReport):
    compile_data: Optional[CompileData] = None
    reports: Optional[list[CompileRunReport]] = None


class AttributeStateChange(BaseModel):
    """
    Changes in the attribute
    """

    current: Optional[object] = None
    desired: Optional[object] = None

    @field_validator("current", "desired")
    @classmethod
    def check_serializable(cls, v: Optional[object]) -> Optional[object]:
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

    def __getstate__(self) -> str:
        # make pickle use json to keep from leaking stuff
        # Will make the objects into json-like things
        # This method exists only to keep IPC light compatible with the json based RPC
        return protocol.common.json_encode(self)

    def __setstate__(self, state: str) -> None:
        # This method exists only to keep IPC light compatible with the json based RPC
        self.__dict__.update(json.loads(state))


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
    """

    name: str
    type: str
    default: EnvSettingType
    doc: str
    recompile: bool
    update_model: bool
    agent_restart: bool
    allowed_values: Optional[list[EnvSettingType]] = None


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


class ModelMetadata(BaseModel):
    """Model metadata"""

    inmanta_compile_state: const.Compilestate = Field(default=const.Compilestate.success, alias="inmanta:compile:state")
    message: str
    type: str
    extra_data: Optional[JsonType] = None


class ResourceMinimal(BaseModel):
    """
    Represents a resource object as it comes in over the API. Provides strictly required validation only.
    """

    id: ResourceVersionIdStr

    @field_validator("id")
    @classmethod
    def id_is_resource_version_id(cls, v):
        if resources.Id.is_resource_version_id(v):
            return v
        raise ValueError(f"id {v} is not of type ResourceVersionIdStr")

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="allow")


class Resource(BaseModel):
    environment: uuid.UUID
    model: int
    resource_id: ResourceIdStr
    resource_type: ResourceType
    resource_version_id: ResourceVersionIdStr
    resource_id_value: str
    agent: str
    attributes: JsonType
    status: const.ResourceState
    resource_set: Optional[str] = None


class ResourceAction(BaseModel):
    environment: uuid.UUID
    version: int
    resource_version_ids: list[ResourceVersionIdStr]
    action_id: uuid.UUID
    action: const.ResourceAction
    started: datetime.datetime
    finished: Optional[datetime.datetime] = None
    messages: Optional[list[JsonType]] = None
    status: Optional[const.ResourceState] = None
    changes: Optional[JsonType] = None
    change: Optional[const.Change] = None
    send_event: Optional[bool] = None  # Deprecated field


class ResourceDeploySummary(BaseModel):
    """
    :param total: The total number of resources
    :param by_state: The number of resources by state in the latest released version
    """

    total: int
    by_state: dict[str, int]

    @classmethod
    def create_from_db_result(cls, summary_by_state: dict[str, int]) -> "ResourceDeploySummary":
        full_summary_by_state = cls._ensure_summary_has_all_states(summary_by_state)
        total = cls._count_all_resources(full_summary_by_state)
        return ResourceDeploySummary(by_state=full_summary_by_state, total=total)

    @classmethod
    def _ensure_summary_has_all_states(cls, summary_by_state: dict[str, int]) -> dict[str, int]:
        full_summary = summary_by_state.copy()
        for state in const.ResourceState:
            if state not in summary_by_state.keys() and state != const.ResourceState.dry:
                full_summary[state] = 0
        return full_summary

    @classmethod
    def _count_all_resources(cls, summary_by_state: dict[str, int]) -> int:
        return sum(resource_count for resource_count in summary_by_state.values())


class LogLine(BaseModel):
    # Override the setting from the BaseModel class as such that the level field is
    # serialized using the name of the enum instead of its value. This is required
    # to make sure that data sent to the API endpoints resource_action_update
    # and send_deploy_done are serialized consistently using the name of the enum.
    model_config: ClassVar[ConfigDict] = ConfigDict(use_enum_values=False)

    level: const.LogLevel
    msg: str
    args: list[Optional[ArgumentTypes]] = []
    kwargs: JsonType = {}
    timestamp: datetime.datetime

    @field_validator("level", mode="before")
    @classmethod
    def validate_log_level(cls, value: object) -> const.LogLevel:
        """
        Validate the log level using the LogLevel enum. Pydantic's default validation does not suffice because of the
        custom value aliasing behavior built on top of LogLevel to allow passing ints to the constructor.
        """
        try:
            return const.LogLevel(value)
        except ValueError:
            # error message as close to pydantic's as possible but add in the int aliases
            name_value_pairs: abc.Iterator[tuple[str, int]] = ((level.value, level.to_int) for level in const.LogLevel)
            valid_input_descriptions: list[str] = [f"'{name}' | {num_value}" for name, num_value in name_value_pairs]
            raise ValueError(
                "Input should be %s" % " or ".join((", ".join(valid_input_descriptions[:-1]), valid_input_descriptions[-1]))
            )


class ResourceIdDetails(BaseModel):
    resource_type: ResourceType
    agent: str
    attribute: str
    resource_id_value: str


class ReleasedResourceState(StrEnum):
    # Copied over from const.ResourceState
    unavailable = "unavailable"  # This state is set by the agent when no handler is available for the resource
    skipped = "skipped"  #
    dry = "dry"
    deployed = "deployed"
    failed = "failed"
    deploying = "deploying"
    available = "available"
    cancelled = "cancelled"  # When a new version is pushed, in progress deploys are cancelled
    undefined = "undefined"  # The state of this resource is unknown at this moment in the orchestration process
    skipped_for_undefined = "skipped_for_undefined"  # This resource depends on an undefined resource
    orphaned = "orphaned"


class VersionedResource(BaseModel):
    resource_id: ResourceIdStr
    resource_version_id: ResourceVersionIdStr
    id_details: ResourceIdDetails
    requires: list[ResourceVersionIdStr]

    @property
    def all_fields(self) -> dict[str, object]:
        return {**self.dict(), **self.id_details.dict()}


class LatestReleasedResource(VersionedResource):
    status: ReleasedResourceState


class PagingBoundaries:
    """
    Represents the lower and upper bounds that should be used for the next and previous pages
    when listing domain entities.

    The largest / smallest value of the current page represents respectively the min / max boundary value (exclusive) for the
    neighbouring pages. Which represents next and which prev depends on sorting order (ASC or DESC).
    So, while the names "start" and "end" might seem to indicate "left" and "right" of the page, they actually mean "highest"
    and "lowest".

    Let's show this in an example: a user requests the following:
     - all Resources with name > foo
     - ASCENDING order
     - Page size = 10

    The equivalent RequestPagingBoundary will be as follows:
        ```
        RequestPagingBoundary:
            start = foo
            end = None
        ```

    The fetched data will be: [foo1 ... foo10]

    But the Pagingboundary will be constructed this way:
        ```
        Pagingboundary:
            end = foo1
            start = foo10 # Reversed because these are meant to map to like-named fields on neighbouring RequestedPagingBoundary
        ```

    :param start: largest value of current page for the primary sort column.
    :param end: smallest value of current page for the primary sort column.
    :param first_id: largest value of current page for the secondary sort column, if there is one.
    :param last_id: smallest value of current page for the secondary sort column, if there is one.
    """

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

    @model_validator(mode="after")
    def ensure_version_field_set_in_attributes(self) -> Self:
        # Due to a bug, the version field has always been present in the attributes dictionary.
        # This bug has been fixed in the database. For backwards compatibility reason we here make sure that the
        # version field is present in the attributes dictionary served out via the API.
        if "version" not in self.attributes:
            self.attributes["version"] = self.version
        return self


class ReleasedResourceDetails(ResourceDetails):
    """The details of a released resource
    :param last_deploy: The value of the last_deploy on the latest released version of the resource
    :param first_generated_time: The first time this resource was generated
    :param first_generated_version: The first model version this resource was in
    :param status: The current status of the resource
    :param requires_status: The id and status of the resources this resource requires
    """

    last_deploy: Optional[datetime.datetime] = None
    first_generated_time: datetime.datetime
    first_generated_version: int
    status: ReleasedResourceState
    requires_status: dict[ResourceIdStr, ReleasedResourceState]


class ResourceHistory(BaseModel):
    resource_id: ResourceIdStr
    date: datetime.datetime
    attributes: JsonType
    attribute_hash: str
    requires: list[ResourceIdStr]


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
    attributes: dict[str, AttributeDiff]
    status: ResourceDiffStatus


class Parameter(BaseModel):
    id: uuid.UUID
    name: str
    value: str
    environment: uuid.UUID
    source: str
    updated: Optional[datetime.datetime] = None
    metadata: Optional[JsonType] = None


class Fact(Parameter):
    resource_id: ResourceIdStr
    expires: bool = True


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
    last_failover: Optional[datetime.datetime] = None
    paused: bool
    process_id: Optional[uuid.UUID] = None
    process_name: Optional[str] = None
    unpause_on_resume: Optional[bool] = None
    status: const.AgentStatus


class AgentProcess(BaseModel):
    sid: uuid.UUID
    hostname: str
    environment: uuid.UUID
    first_seen: Optional[datetime.datetime] = None
    last_seen: Optional[datetime.datetime] = None
    expired: Optional[datetime.datetime] = None
    state: Optional[dict[str, Union[dict[str, list[str]], dict[str, str], dict[str, float], str]]] = None


class DesiredStateLabel(BaseModel):
    name: str
    message: str


class DesiredStateVersion(BaseModel):
    """
    :param released: has this desired state version been released?
    """

    version: int
    date: datetime.datetime
    total: int
    labels: list[DesiredStateLabel]
    status: const.DesiredStateVersionStatus
    released: bool


class PromoteTriggerMethod(StrEnum):
    # partly copies from const.AgentTriggerMethod
    push_incremental_deploy = "push_incremental_deploy"
    push_full_deploy = "push_full_deploy"
    no_push = "no_push"


class DryRun(BaseModel):
    id: uuid.UUID
    environment: uuid.UUID
    model: int
    date: Optional[datetime.datetime] = None
    total: int = 0
    todo: int = 0


class DryRunReport(BaseModel):
    summary: DryRun
    diff: list[ResourceDiff]


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
    :param compile_id: The id of the compile that is associated with this notification.
    :param read: Whether the notification was read or not
    :param cleared: Whether the notification was cleared or not
    """

    id: uuid.UUID
    environment: uuid.UUID
    created: datetime.datetime
    title: str
    message: str
    severity: const.NotificationSeverity
    uri: Optional[str] = None
    compile_id: uuid.UUID | None = None
    read: bool
    cleared: bool


class Source(BaseModel):
    """Model for source code"""

    hash: str
    is_byte_code: bool
    module_name: str
    requirements: list[str]


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


class AuthMethod(str, Enum):
    database = "database"
    oidc = "oidc"


class User(BaseModel):
    """A user"""

    username: str
    auth_method: AuthMethod


class CurrentUser(BaseModel):
    """Information about the current logged in user"""

    username: str


class LoginReturn(BaseModel):
    """
    Login information

    :param token: A token representing the user's authentication session
    :param user: The user object for which the token was created
    """

    token: str
    user: User


def _check_resource_id_str(v: str) -> ResourceIdStr:
    if resources.Id.is_resource_id(v):
        return ResourceIdStr(v)
    raise ValueError("Invalid id for resource %s" % v)


ResourceId: typing.TypeAlias = typing.Annotated[ResourceIdStr, pydantic.AfterValidator(_check_resource_id_str)]


class DiscoveredResourceABC(BaseModel):
    """
    :param discovered_resource_id: The name of the resource
    :param values: The actual resource
    :param managed_resource_uri: URI of the resource with the same ID that is already
        managed by the orchestrator e.g. "/api/v2/resource/<rid>". Or None if the resource is not managed.
    :param discovery_resource_id: Resource id of the (managed) discovery resource that reported this
        discovered resource.
    """

    discovered_resource_id: ResourceId
    values: dict[str, object]
    managed_resource_uri: Optional[str] = None

    discovery_resource_id: Optional[ResourceId]

    @computed_field  # type: ignore[misc]
    @property
    def discovery_resource_uri(self) -> str | None:
        if self.discovery_resource_id is None:
            return None
        return f"/api/v2/resource/{urllib.parse.quote(self.discovery_resource_id, safe='')}"


class DiscoveredResource(DiscoveredResourceABC):
    """
    Discovered resource for API returns. Contains additional (redundant) metadata to improve user experience.
    """

    resource_type: ResourceType
    agent: str
    resource_id_value: str


class LinkedDiscoveredResource(DiscoveredResourceABC):
    """
    DiscoveredResource linked to the discovery resource that discovered it.

    :param discovery_resource_id: Resource id of the (managed) discovery resource that reported this
           discovered resource.
    """

    # This class is used as API input. Its behaviour can be directly incorporated into the DiscoveredResourceABC parent class
    # when providing the id of the discovery resource is mandatory for all discovered resource. Ticket link:
    # https://github.com/inmanta/inmanta-core/issues/8004

    discovery_resource_id: ResourceId

    def to_dao(self, env: uuid.UUID) -> "data.DiscoveredResource":
        parsed_id: resources.Id = resources.Id.parse_id(self.discovered_resource_id)
        return data.DiscoveredResource(
            discovered_resource_id=self.discovered_resource_id,
            resource_type=parsed_id.entity_type,
            agent=parsed_id.agent_name,
            resource_id_value=parsed_id.attribute_value,
            values=self.values,
            discovered_at=datetime.datetime.now(),
            environment=env,
            discovery_resource_id=self.discovery_resource_id,
        )


def hyphenize(field: str) -> str:
    """Alias generator to convert python names (with `_`) to config file name (with `-`)"""
    return field.replace("_", "-")


@stable_api
# This is part of both the config file schema and the api schema
class PipConfig(BaseModel):
    """
    Base class to represent pip config internally

    :param index_url: one pip index url for this project.
    :param extra_index_url:  additional pip index urls for this project. This is generally only
        recommended if all configured indexes are under full control of the end user to protect against dependency
        confusion attacks. See the `pip install documentation <https://pip.pypa.io/en/stable/cli/pip_install/>`_ and
        `PEP 708 (draft) <https://peps.python.org/pep-0708/>`_ for more information.
    :param pre:  allow pre-releases when installing Python packages, i.e. pip --pre.
        Defaults to None.
        When None and pip.use-system-config=true we follow the system config.
        When None and pip.use-system-config=false, we don't allow pre-releases.
    :param use_system_config: defaults to false.
        When true, sets the pip index url, extra index urls and pre according to the respective settings outlined above
        but otherwise respect any pip environment variables and/or config in the pip config file,
        including any extra-index-urls.

        If no indexes are configured in pip.index-url/pip.extra-index-url
        with this option enabled means to fall back to pip's default behavior:
        use the pip index url from the environment, the config file, or PyPi, in that order.

        For development, it is recommended to set this option to false, both for portability
        (and related compatibility with tools like pytest-inmanta-lsm) and for security
        (dependency confusion attacks could affect users that aren't aware that inmanta installs Python packages).
    """

    # Config needs to be in the top-level object, because is also affect serialization/deserialization
    model_config: typing.ClassVar[pydantic.ConfigDict] = pydantic.ConfigDict(
        # use alias generator have `-` in names
        alias_generator=hyphenize,
        # allow use of aliases
        populate_by_name=True,
        extra="ignore",
    )

    index_url: Optional[str] = None
    # Singular to be consistent with pip itself
    extra_index_url: Sequence[str] = []
    pre: Optional[bool] = None
    use_system_config: bool = False

    def has_source(self) -> bool:
        """Can this config get packages from anywhere?"""
        return bool(self.index_url) or self.use_system_config

    def get_index_args(self) -> list[str]:
        """
        Returns the index-related arguments that should be used to run a pip command
        with this pip config.
        """
        index_args: list[str] = []
        if self.index_url:
            index_args.append("--index-url")
            index_args.append(self.index_url)
        elif not self.use_system_config:
            # If the config doesn't set index url
            # and we are not using system config,
            # then we need to disable the index.
            # This can only happen if paths is also set.
            index_args.append("--no-index")
        for extra_index_url in self.extra_index_url:
            index_args.append("--extra-index-url")
            index_args.append(extra_index_url)
        return index_args

    def get_environment_variables(self) -> dict[str, str]:
        """
        Returns the environment variables that should be used to run a pip command
        with this pip config.
        """
        sub_env = os.environ.copy()
        if not self.use_system_config:
            # If we don't use system config, unset env vars
            for key in ("PIP_EXTRA_INDEX_URL", "PIP_INDEX_URL", "PIP_PRE", "PIP_NO_INDEX"):
                sub_env.pop(key, None)

            # setting this env_var to os.devnull disables the loading of all pip configuration file
            sub_env["PIP_CONFIG_FILE"] = os.devnull
        if self.pre is not None:
            # Make sure that IF pip pre is set, we enforce it
            # The `--pre` option can only enable it
            # The env var can both enable and disable
            sub_env["PIP_PRE"] = str(self.pre)
        return sub_env


LEGACY_PIP_DEFAULT = PipConfig(use_system_config=True)


class Discrepancy(BaseModel):
    """
    Records a discrepancy between the state as persisted in the database and
    the in-memory state in the scheduler. Either model-wide when no
    resource id is specified (e.g. when model versions are mismatched)
    or for a specific resource.

    :param rid: If set, this discrepancy is specific to this resource.
        If left unset, this discrepancy is not specific to any particular resource.
    :param field: If set, specifies on which field this discrepancy was detected.
        If left unset, and a rid is specified, the discrepancy was detected on the
        resource level i.e. it is missing from either the db or the scheduler.
    :param expected: User-facing message denoting the expected state (i.e. as persisted
        in the DB).
    :param actual: User-facing message denoting the actual state (i.e. in-memory state
        in the scheduler).

    """

    rid: ResourceIdStr | None
    field: str | None
    expected: str
    actual: str


class SchedulerStatusReport(BaseModel):
    """
    Status report for the scheduler self-check

    :param scheduler_state: In-memory representation of the resources in the scheduler
    :param db_state: Desired state of the resources as persisted in the database
    :param discrepancies: Discrepancies between the in-memory representation of the resources
        and their state in the database.
    """

    # Can't type properly because of current module structure
    scheduler_state: Mapping[ResourceIdStr, object]  # "True" type is deploy.state.ResourceState
    db_state: Mapping[ResourceIdStr, object]  # "True" type is deploy.state.ResourceIntent
    resource_states: Mapping[ResourceIdStr, const.ResourceState]
    discrepancies: list[Discrepancy] | dict[ResourceIdStr, list[Discrepancy]]


class DataBaseReport(BaseModel):
    """
    :param max_pool: maximal pool size
    :param free_pool: number of connections not in use in the pool
    :param open_connections: number of connections currently open
    :param free_connections: number of connections currently open and not in use
    :param pool_exhaustion_time: nr of seconds since start we observed the pool to be exhausted
    """

    connected: bool
    database: str
    host: str
    max_pool: int
    free_pool: int
    open_connections: int
    free_connections: int
    pool_exhaustion_time: float

    def __add__(self, other: "DataBaseReport") -> "DataBaseReport":
        if not isinstance(other, DataBaseReport):
            return NotImplemented
        if other.database != self.database:
            return NotImplemented
        if other.host != self.host:
            return NotImplemented
        return DataBaseReport(
            connected=self.connected and other.connected,
            database=self.database,
            host=self.host,
            max_pool=self.max_pool + other.max_pool,
            free_pool=self.free_pool + other.free_pool,
            open_connections=self.open_connections + other.open_connections,
            free_connections=self.free_connections + other.free_connections,
            pool_exhaustion_time=self.pool_exhaustion_time + other.pool_exhaustion_time,
        )


class GetSourceCodeResponse(BaseModel):
    sources: list[Source]
    project_constraints: str | None
