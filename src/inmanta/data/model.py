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
from typing import Dict, List, Union

import pydantic

from inmanta.types import ArgumentTypes, SimpleTypes


class BaseModel(pydantic.BaseModel):
    """
        Base class for all data objects in Inmanta
    """

    class Config:
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


class StatusResponse(BaseModel):
    """
        Response for the status method call
    """

    version: str
    license: Union[str, Dict[str, SimpleTypes]]
    extensions: List[ExtensionStatus]
    slices: List[SliceStatus]
