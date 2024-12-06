"""
    Copyright 2024 Inmanta

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

import dataclasses


@dataclasses.dataclass(frozen=True)
class Virtualmachine:
    """Python comment"""

    name: str
    os: list[str]
    it: int
    ot: int
    cpus: int
    disk: dict[int, str]
    other: dict[str, bool]
