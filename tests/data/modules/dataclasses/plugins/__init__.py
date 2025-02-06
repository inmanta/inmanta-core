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
    name: "str"
    os: dict
    ram: int | None
    cpus: dict[str, int]
    disk: list[int]
    slots: list[int] | None


@plugin
def eat_vm(inp: "dataclasses::Virtualmachine") -> None:
    assert isinstance(inp, Virtualmachine)
    print(inp)
    return None


@plugin
def make_virtual_machine() -> "dataclasses::Virtualmachine":
    out = Virtualmachine(name="Test", os={"X": "x"}, ram=5, cpus={"s": 5}, disk=[15], slots=None)

    return out


@plugin
def select_vm(inp: "dataclasses::Virtualmachine[]", name: "string") -> Virtualmachine | None:
    for vm in inp:
        if vm.name == name:
            return vm

    return None


@plugin
def make_vms() -> "dataclasses::Virtualmachine[]?":
    return [
        Virtualmachine(name="Test", os={"X": "x"}, ram=5, cpus={"s": 5}, disk=[15], slots=[6]),
        Virtualmachine(name="Test", os={"X": "x"}, ram=5, cpus={"s": 5}, disk=[15], slots=[7]),
        Virtualmachine(name="Test", os={"X": "x"}, ram=5, cpus={"s": 5}, disk=[15], slots=[8]),
    ]


@plugin
def make_bad_virtual_machine() -> "dataclasses::Virtualmachine":
    # Disks should be int
    out = Virtualmachine(name="Test", os={"X": "x"}, ram=5, cpus={"s": 5}, disk=["root"], slots=None)

    return out


class SomeWhatStringLike(str):

    def also_this(self) -> int:
        return 5


@plugin
def odd_string() -> "string":
    return SomeWhatStringLike("it")


@plugin
def is_odd_string(thing: "string") -> None:
    assert isinstance(thing, SomeWhatStringLike)


@plugin
def return_any() -> "any":
    out = Virtualmachine(name="Test", os={"X": "x"}, ram=5, cpus={"s": 5}, disk=[15], slots=None)
    return out
