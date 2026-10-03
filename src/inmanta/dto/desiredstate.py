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
from enum import StrEnum
from typing import Optional

from pydantic import Field

from inmanta import const
from inmanta.types import BaseModel as BaseModel
from inmanta.types import JsonType


class ModelMetadata(BaseModel):
    """Model metadata"""

    inmanta_compile_state: const.Compilestate = Field(default=const.Compilestate.success, alias="inmanta:compile:state")
    message: str
    type: str
    extra_data: Optional[JsonType] = None


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
