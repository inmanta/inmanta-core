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
from typing import List

import inmanta.ast.export as ast_export
import inmanta.data.model as model
from inmanta.ast import CompilerException


class CompileData(ast_export.Exportable):
    def __init__(self) -> None:
        self.errors: List[CompilerException] = []

    def add_error(self, error: CompilerException) -> None:
        self.errors.append(error)

    def export(self) -> "model.CompileData":
        return model.CompileData(errors=[e.export() for e in self.errors])
