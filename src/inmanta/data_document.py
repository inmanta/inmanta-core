"""
Copyright 2026 Inmanta

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
from typing import Optional, Union, cast

from inmanta import const, util
from inmanta.const import NAME_RESOURCE_ACTION_LOGGER, LogLevel
from inmanta.types import JsonType, ResourceVersionIdStr


class DataDocument:
    """
    A baseclass for objects that represent data in inmanta. The main purpose of this baseclass is to group dict creation
    logic. These documents are not stored in the database
    (use BaseDocument for this purpose). It provides a to_dict method that the inmanta rpc can serialize. You can store
    DataDocument children in BaseDocument fields, they will be serialized to dict. However, on retrieval this is not
    performed.
    """

    def __init__(self, **kwargs: object) -> None:
        self._data = kwargs

    def to_dict(self) -> JsonType:
        """
        Return a dict representation of this object.
        """
        return self._data


class LogLine(DataDocument):
    """
    LogLine data document.

    An instance of this class only has one attribute: _data.
    This unique attribute is a dict, with the following keys:
        - msg: the message to write to logs (value type: str)
        - args: the args that can be passed to the logger (value type: list)
        - level: the log level of the message (value type: str, example: "CRITICAL")
        - kwargs: the key-word args that were used to generate the log (value type: list)
        - timestamp: the time at which the LogLine was created (value type: datetime.datetime)
    """

    @property
    def msg(self) -> str:
        return self._data["msg"]

    @property
    def args(self) -> list:
        return self._data["args"]

    @property
    def log_level(self) -> LogLevel:
        level: str = self._data["level"]
        return LogLevel[level]

    @property
    def timestamp(self) -> datetime.datetime:
        return cast(datetime.datetime, self._data["timestamp"])

    def write_to_logger(self, logger: logging.Logger) -> None:
        logger.log(self.log_level.to_int, self.msg, *self.args)

    def write_to_logger_for_resource(
        self, agent: str, resource_version_string: ResourceVersionIdStr, exc_info: bool = False
    ) -> None:
        logging.getLogger(NAME_RESOURCE_ACTION_LOGGER).getChild(agent).log(
            self.log_level.to_int, "resource %s: %s", resource_version_string, self._data["msg"], exc_info=exc_info
        )

    @classmethod
    def log(
        cls,
        level: Union[int, const.LogLevel],
        msg: str,
        timestamp: Optional[datetime.datetime] = None,
        **kwargs: object,
    ) -> "LogLine":
        if timestamp is None:
            timestamp = datetime.datetime.now().astimezone()

        log_line = msg % kwargs
        return cls(level=LogLevel(level).name, msg=log_line, args=[], kwargs=kwargs, timestamp=timestamp)

    def __getstate__(self) -> str:
        if "timestamp" not in self._data:
            self._data["timestamp"] = datetime.datetime.now().astimezone()
        # make pickle use json to keep leaking stuff
        # Will make the objects into json-like things
        # This method exists only to keep IPC light compatible with the json based RPC
        return json.dumps(self._data, default=util.internal_json_encoder)

    def __setstate__(self, state: str) -> None:
        # This method exists only to keep IPC light compatible with the json based RPC
        self._data = json.loads(state)
        self._data["timestamp"] = util.parse_timestamp(cast(str, self._data["timestamp"]))
