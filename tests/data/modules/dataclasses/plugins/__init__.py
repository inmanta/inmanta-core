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

from inmanta.plugins import plugin


@dataclasses.dataclass(frozen=True)
class Virtualmachine:
    name: str
    os: str
    ram: int
    cpus: int
    disk: int


@plugin
def make_virtual_machine() -> "dataclasses::Virtualmachine":
    return Virtualmachine(name="Test", os="linux", ram=5, cpus=2, disk=15)


@plugin
def eat_vm(inp: "dataclasses::Virtualmachine") -> None:
    print(inp)
    return None


@plugin
def select_vm(inp: "dataclasses::Virtualmachine[]", name: "string") -> "dataclasses::Virtualmachine?" :
    for vm in inp:
        if vm.name == name:
            return vm

    return None
