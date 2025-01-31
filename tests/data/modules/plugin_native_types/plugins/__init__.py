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

from typing import Any, Annotated, Protocol, Literal
from typing import Union, Optional, Any
from typing import Union, Optional, Any
from inmanta.plugins import plugin, ModelType


@plugin
def get_from_dict(value: dict[str, str], key: str) -> str | None:
    return value.get(key)


@plugin
def many_arguments(il: list[str], idx: int) -> str:
    return sorted(il)[idx]


@plugin
def as_none(value: str) -> None:
    pass


# Union types (input parameter)


@plugin
def union_single_type(value: Union[str]) -> None:
    pass


@plugin
def union_multiple_types(value: Union[int, str]) -> None:
    pass


@plugin
def union_optional_1(value: Union[None, int, str]) -> None:
    pass


@plugin
def union_optional_2(value: Optional[Union[int, str]]) -> None:
    pass


@plugin
def union_optional_3(value: Union[int, str] | None) -> None:
    pass


@plugin
def union_optional_4(value: None | Union[int, str]) -> None:
    pass


# Union types (return value)


@plugin
def union_return_single_type(value: Any) -> Union[str]:
    return value


@plugin
def union_return_multiple_types(value: Any) -> Union[str, int]:
    return value


@plugin
def union_return_optional_1(value: Any) -> Union[None, int, str]:
    return value


@plugin
def union_return_optional_2(value: Any) -> Optional[Union[int, str]]:
    return value


@plugin
def union_return_optional_3(value: Any) -> Union[int, str] | None:
    return value


@plugin
def union_return_optional_4(value: Any) -> None | Union[int, str]:
    return value


# Annotated values


class MyEntity(Protocol):
    value: int


@plugin
def annotated_arg_entity(value: Annotated[MyEntity, ModelType["TestEntity"]]) -> None:
    pass


@plugin
def annotated_return_entity(value: Any) -> Annotated[MyEntity, ModelType["TestEntity"]]:
    return value


@plugin
def annotated_arg_literal(value: Annotated[Literal["yes", "no"], ModelType["response"]]) -> None:
    pass


@plugin
def annotated_return_literal(value: Any) -> Annotated[Literal["yes", "no"], ModelType["response"]]:
    return value
