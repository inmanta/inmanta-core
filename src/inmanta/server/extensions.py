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
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from inmanta.server.protocol import ServerSlice


class InvalidSliceNameException(Exception):

    pass


class ApplicationContext(object):
    def __init__(self) -> None:
        self._slices: List[ServerSlice] = []

    def register_slice(self, slice: "ServerSlice") -> None:
        assert slice is not None
        self._slices.append(slice)

    def get_slices(self) -> "List[ServerSlice]":
        return self._slices
