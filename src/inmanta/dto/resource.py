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
import typing
import uuid
from collections import defaultdict
from collections.abc import Sequence
from enum import StrEnum
from typing import ClassVar, Optional, cast

import asyncpg
from asyncpg import Record
from pydantic import ConfigDict, field_validator

import inmanta
from inmanta import const, resources, util
from inmanta.deploy.state import Blocked, Compliance, HandlerResult
from inmanta.types import BaseModel as BaseModel
from inmanta.types import JsonType
from inmanta.types import ResourceIdStr as ResourceIdStr
from inmanta.types import ResourceType as ResourceType
from inmanta.types import ResourceVersionIdStr as ResourceVersionIdStr


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
            util.json_encode(v)
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
        return util.json_encode(self)

    def __setstate__(self, state: str) -> None:
        # This method exists only to keep IPC light compatible with the json based RPC
        self.__dict__.update(json.loads(state))


class ResourceMinimal(BaseModel):
    """
    Represents a resource object as it comes in over the API. Provides strictly required validation only.
    """

    id: ResourceVersionIdStr

    @field_validator("id")
    @classmethod
    def id_is_resource_version_id(cls, v: ResourceVersionIdStr) -> ResourceVersionIdStr:
        if resources.Id.is_resource_version_id(v):
            return v
        raise ValueError(f"id {v} is not of type ResourceVersionIdStr")

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="allow")


class Resource(BaseModel):
    environment: uuid.UUID
    resource_id: ResourceIdStr
    resource_type: ResourceType
    resource_id_value: str
    agent: str
    attributes: JsonType
    is_undefined: bool
    resource_set: str | None = None

    @classmethod
    def from_postgres_record(cls, record: asyncpg.Record) -> "Resource":
        """
        Create a Resource from a Postgres record.
        Requires the record to have a resource_set_name.

        :param record: The postgres record to create a Resource from.
        """
        return Resource(
            environment=cast(uuid.UUID, record["environment"]),
            resource_id=cast(ResourceIdStr, record["resource_id"]),
            resource_type=cast(ResourceType, record["resource_type"]),
            resource_id_value=cast(str, record["resource_id_value"]),
            agent=cast(str, record["agent"]),
            attributes=cast(JsonType, record["attributes"]),
            is_undefined=cast(bool, record["is_undefined"]),
            resource_set=cast(str | None, record["resource_set_name"]),
        )


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


class ComposedResourceSummary(BaseModel):
    """
    A summary of the composed status of all resources in an environment.

    :param total_count: Total count of resources.
    :param compliance:  Summary of the compliance status of resources
    :param last_handler_run: Summary of the status of the last handler run of resources
    :param blocked: Summary of the blocked status of resources
    :param is_deploying: Summary of the status of the deployment status of resources
    """

    total_count: int
    compliance: dict[Compliance, int]
    last_handler_run: dict[HandlerResult, int]
    blocked: dict[Blocked, int]
    is_deploying: dict[bool, int]

    @classmethod
    def create_from_db_result(cls, summary_by_db_result: Sequence[Record]) -> "ComposedResourceSummary":
        parsed_results: typing.DefaultDict[str, dict[str, int]] = defaultdict(dict)
        for result in summary_by_db_result:
            parsed_results[str(result["metric"])][str(result["value"]).lower()] = cast(int, result["count"])

        expected_values = {
            "is_deploying": ["true", "false"],
            "blocked": [x.value for x in Blocked],
            "compliance": [x.value for x in Compliance],
            "last_handler_run": [x.value for x in HandlerResult],
        }
        for metric, values in expected_values.items():
            for value in values:
                if value not in parsed_results[metric]:
                    parsed_results[metric][value] = 0

        return ComposedResourceSummary(
            # total_count is the same on every row
            total_count=cast(int, summary_by_db_result[0]["total_count"]) if summary_by_db_result else 0,
            compliance={Compliance(k): v for k, v in parsed_results["compliance"].items()},
            blocked={Blocked(k): v for k, v in parsed_results["blocked"].items()},
            last_handler_run={HandlerResult(k): v for k, v in parsed_results["last_handler_run"].items()},
            is_deploying={k == "true": v for k, v in parsed_results["is_deploying"].items()},
        )


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
    non_compliant = "non_compliant"


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
    :param last_deploy: The value of the last_handler_run_at on the latest released version of the resource
    :param first_generated_time: The first time this resource was generated
    :param status: The current status of the resource
    :param requires_status: The id and status of the resources this resource requires
    """

    last_deploy: Optional[datetime.datetime] = None
    first_generated_time: datetime.datetime
    status: ReleasedResourceState
    requires_status: dict[ResourceIdStr, ReleasedResourceState]


class ResourceHistory(BaseModel):
    resource_id: ResourceIdStr
    date: datetime.datetime
    attributes: JsonType
    attribute_hash: str
    requires: list[ResourceIdStr]
