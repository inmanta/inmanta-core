"""
    Copyright 2017 Inmanta

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
from typing import Iterable

from inmanta.stable_api import stable_api


class AnyType(object):
    """
    Supertype for objects that are an instance of all types
    """

    pass


@stable_api
class Unknown(AnyType):
    """
    An instance of this class is used to indicate that this value can not be determined yet.

    :param source: The source object that can determine the value
    """

    def __init__(self, source: object) -> None:
        self.source = source

    def __iter__(self) -> Iterable[object]:
        return iter([])


class NoneValue(object):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, NoneValue)

    def __hash__(self) -> int:
        return hash(None)

    def __str__(self) -> str:
        return "null"

    def __repr__(self) -> str:
        return "null"
