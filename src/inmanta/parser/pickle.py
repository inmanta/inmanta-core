"""
    Copyright 2020 Inmanta

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
from io import BytesIO
from pickle import Pickler, Unpickler, UnpicklingError
from typing import Optional, Tuple

from inmanta.ast import Namespace


class ASTPickler(Pickler):
    def persistent_id(self, obj: object) -> Optional[Tuple[str, str]]:
        if isinstance(obj, Namespace):
            # Don't pickle namespaces
            return ("Namespace", obj.get_full_name())
        else:
            return None


class ASTUnpickler(Unpickler):
    def __init__(self, file: BytesIO, namespace: Namespace) -> None:
        super().__init__(file)
        self.namespace = namespace
        self.namespace_name = namespace.get_full_name()

    def persistent_load(self, pid: Tuple[str, str]) -> object:
        type_tag, key_id = pid
        if type_tag == "Namespace":
            assert self.namespace_name == key_id
            return self.namespace
        else:
            raise UnpicklingError("unsupported persistent object")
