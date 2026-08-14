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
from typing import Optional, Union

from inmanta import const
from inmanta.types import BaseModel as BaseModel


class Agent(BaseModel):
    """
    :param environment: Id of the agent's environment
    :param name: The name of the agent
    :param paused: Whether the agent is paused or not
    :param unpause_on_resume: Whether the agent should be unpaused when the environment is resumed
    :param status: The current status of the agent
    :param process_id: The id of the agent process that belongs to this agent, if there is one
    :param process_name: The name of the agent process that belongs to this agent, if there is one
    """

    environment: uuid.UUID
    name: str
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
    expired: Optional[datetime.datetime] = None
    state: Optional[dict[str, Union[dict[str, list[str]], dict[str, str], dict[str, float], str]]] = None


type AgentName = str
