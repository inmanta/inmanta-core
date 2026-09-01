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
import typing
import uuid
from typing import Optional

import pydantic.schema

import inmanta.ast.export as ast_export
import pydantic_core.core_schema
from inmanta.stable_api import stable_api
from inmanta.types import BaseModel as BaseModel
from inmanta.types import JsonType


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
