"""
    Copyright 2023 Inmanta

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

from typing import Any, Annotated
from inmanta.plugins import plugin
from inmanta import plugin_typing


@plugin
def get_from_dict(value: dict[str, str], key: str) -> str | None:
    return value.get(key)


@plugin
def many_arguments(il: list[str], idx: int) -> str:
    return sorted(il)[idx]


@plugin
def as_none(value: str) -> None:
    pass


# Annotated values


@plugin
def annotated_arg_entity(value: Annotated[object, plugin_typing.InmantaType("TestEntity")]) -> None:
    pass


@plugin
def annotated_return_entity(value: Any) -> Annotated[object, plugin_typing.InmantaType("TestEntity")]:
    return value
