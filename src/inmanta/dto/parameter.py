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
from typing import Optional

from inmanta.types import BaseModel as BaseModel
from inmanta.types import JsonType
from inmanta.types import ResourceIdStr as ResourceIdStr


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
