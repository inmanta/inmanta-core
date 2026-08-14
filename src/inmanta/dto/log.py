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
import logging
import uuid
from collections import abc
from collections.abc import Mapping
from typing import ClassVar, Optional, Union

from pydantic import ConfigDict, Field, field_validator

from inmanta import const, util
from inmanta.types import ArgumentTypes
from inmanta.types import BaseModel as BaseModel
from inmanta.types import JsonType, ResourceVersionIdStr


class LogLine(BaseModel):
    # Override the setting from the BaseModel class as such that the level field is
    # serialized using the name of the enum instead of its value. This is required
    # to make sure that data sent over the API is serialized consistently using the name of the enum.
    model_config: ClassVar[ConfigDict] = ConfigDict(use_enum_values=False)

    level: const.LogLevel
    msg: str
    args: list[Optional[ArgumentTypes]] = []
    kwargs: JsonType = {}
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now().astimezone())

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

    @classmethod
    def log(
        cls,
        level: Union[int, const.LogLevel],
        msg: str,
        timestamp: Optional[datetime.datetime] = None,
        **kwargs: object,
    ) -> "LogLine":
        """
        Build a log line, interpolating kwargs into msg the way the logging module would.
        """
        if timestamp is None:
            timestamp = datetime.datetime.now().astimezone()
        return cls(level=const.LogLevel(level), msg=msg % kwargs, args=[], kwargs=kwargs, timestamp=timestamp)

    @property
    def log_level(self) -> const.LogLevel:
        return self.level

    @property
    def _data(self) -> JsonType:
        """
        The dict this log line used to be backed by, kept readable for handler code and tests that reach into it.
        """
        return self.to_dict()

    def to_dict(self) -> JsonType:
        """
        The dict representation used when writing these to the database and over the API.

        This has to be built from the model rather than a fixed set of keys, because util._custom_json_encoder prefers
        to_dict over pydantic serialization, so a subclass such as ResourceLog would otherwise lose its own fields.
        """
        return self.model_dump(by_alias=True)

    def write_to_logger(self, logger: logging.Logger) -> None:
        logger.log(self.log_level.to_int, self.msg, *self.args)

    def write_to_logger_for_resource(
        self, agent: str, resource_version_string: ResourceVersionIdStr, exc_info: bool = False
    ) -> None:
        logging.getLogger(const.NAME_RESOURCE_ACTION_LOGGER).getChild(agent).log(
            self.log_level.to_int, "resource %s: %s", resource_version_string, self.msg, exc_info=exc_info
        )

    def __getstate__(self) -> dict[str, str]:
        # Pickle through json so that IPC light stays compatible with the json based RPC, and so that values which json can
        # represent but pickle cannot, such as a str subclass defined inside a function, survive the round trip.
        # The json is carried inside a dict because pydantic types __getstate__ as returning one.
        return {"json": util.json_encode(self.to_dict())}

    def __setstate__(self, state: Mapping[str, object]) -> None:
        encoded = state["json"]
        if not isinstance(encoded, str):
            raise TypeError(f"Expected the pickled state to carry json as a string, got {type(encoded).__name__}")
        decoded = json.loads(encoded)
        decoded["timestamp"] = util.parse_timestamp(decoded["timestamp"])
        validated = type(self).model_validate(decoded)
        for slot in ("__dict__", "__pydantic_fields_set__", "__pydantic_extra__", "__pydantic_private__"):
            object.__setattr__(self, slot, getattr(validated, slot))


class ResourceLog(LogLine):
    action_id: uuid.UUID
    action: const.ResourceAction
