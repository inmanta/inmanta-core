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
from collections import abc
from typing import ClassVar, Optional

from pydantic import ConfigDict, field_validator

from inmanta import const
from inmanta.types import ArgumentTypes
from inmanta.types import BaseModel as BaseModel
from inmanta.types import JsonType


class LogLine(BaseModel):
    # Override the setting from the BaseModel class as such that the level field is
    # serialized using the name of the enum instead of its value. This is required
    # to make sure that data sent over the API is serialized consistently using the name of the enum.
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


class ResourceLog(LogLine):
    action_id: uuid.UUID
    action: const.ResourceAction
