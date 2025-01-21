"""
    Copyright 2025 Inmanta

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

import typing
from dataclasses import dataclass

# TODO: move this module to inmanta.plugins.typing? Probably not because that would import the whole `plugins` namespace?


@dataclass(frozen=True)
class InmantaType:
    """
    Declaration of an inmanta type for use with typing.Annotated.
    When a plugin type is declared as typing.Annotated with an `InmantaType` as annotation, the Python type is completely
    ignored for type validation and conversion to and from the DSL. Instead the string provided to the `InmantaType` is
    evaluated as a DSL type, extended with "any".
    For maximum static type coverage, it is recommended to use these only when absolutely necessary, and to use them as deeply
    in the type as possible, e.g. prefer `Sequence[Annotated[MyEntity, InmantaType("std::Entity")]]` over
    `Annotated[Sequence[Entity], InmantaType("std::Entity[]")]`.
    """

    dsl_type: str


# TODO: how to do Entity? "object" is appropriate but raises too many errors for practical use. Any is Any
Entity: typing.TypeAlias = typing.Annotated[object, InmantaType("std::Entity")]
string: typing.TypeAlias = typing.Annotated[str, InmantaType("string")]
