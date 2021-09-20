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

import json
from pathlib import Path
from typing import Callable, Optional, Type

import pytest

import inmanta.ast.export as ast_export
import inmanta.compiler as compiler
from inmanta.ast import CompilerException, DoubleSetException, ExplicitPluginException, NotFoundException
from inmanta.config import Config
from inmanta.data.model import CompileData
from inmanta.parser import ParserException


def export_to_file(path: Path, expected_error_type: Optional[Type[CompilerException]] = None) -> CompileData:
    """
    Compiles, exporting to a file, and returns the file contents, loaded as CompileData.
    """
    Config.set("compiler", "export_compile_data", "true")
    Config.set("compiler", "export_compile_data_file", str(path))
    if expected_error_type is None:
        compiler.do_compile()
    else:
        with pytest.raises(CompilerException):
            compiler.do_compile()
    with path.open() as f:
        return CompileData(**json.loads(f.read()))


@pytest.fixture
def tempfile_export(tmp_path: Path) -> Callable[[Optional[Type[CompilerException]]], CompileData]:
    def do_export(expected_error_type: Optional[Type[CompilerException]] = None) -> CompileData:
        return export_to_file(tmp_path / "myfile", expected_error_type)

    return do_export


def test_export_compile_data_to_file(snippetcompiler, tempfile_export) -> None:
    snippetcompiler.setup_for_snippet(
        """
x = 0
        """,
    )
    assert len(tempfile_export().errors) == 0


def test_export_compile_data_to_file_overwrite(snippetcompiler, tmp_path: Path) -> None:
    path: Path = tmp_path / "myfile"
    for _ in range(2):
        snippetcompiler.setup_for_snippet(
            """
x = 0
            """,
        )
        assert len(export_to_file(path).errors) == 0


def test_export_compile_data_to_file_error(snippetcompiler, tempfile_export) -> None:
    snippetcompiler.setup_for_snippet(
        """
x = 0
x = 1
        """,
    )
    compile_data: CompileData = tempfile_export(DoubleSetException)
    assert len(compile_data.errors) == 1
    error: ast_export.Error = compile_data.errors[0]
    assert error.category == ast_export.ErrorCategory.runtime
    assert error.type == "inmanta.ast.DoubleSetException"
    filename = f"{snippetcompiler.project_dir}/main.cf"
    assert error.message == (
        f"value set twice:\n\told value: 0\n\t\tset at {filename}:2\n\tnew value: 1\n\t\tset at {filename}:3\n"
    )
    assert error.location == ast_export.Location(
        uri=filename,
        range=ast_export.Range(start=ast_export.Position(line=2, character=0), end=ast_export.Position(line=3, character=0)),
    )


@pytest.mark.parametrize_any(
    "snippet,exception,category,message,report_exnc",
    [
        (
            "1 = 1",
            ParserException,
            ast_export.ErrorCategory.parser,
            "Syntax error at token 1",
            "inmanta.parser.ParserException",
        ),
        (
            "x.n = 1",
            NotFoundException,
            ast_export.ErrorCategory.runtime,
            "variable x not found",
            "inmanta.ast.NotFoundException",
        ),
        (
            "import tests tests::raise_exception('my message')",
            ExplicitPluginException,
            ast_export.ErrorCategory.plugin,
            "Test: my message",
            "inmanta_plugins.tests.TestPluginException",
        ),
    ],
)
def test_export_compile_data_to_file_categories(
    snippetcompiler,
    snippet: str,
    exception: Type[CompilerException],
    category: ast_export.ErrorCategory,
    message,
    report_exnc,
    tempfile_export,
) -> None:
    snippetcompiler.setup_for_snippet(snippet)
    compile_data: CompileData = tempfile_export(exception)
    assert len(compile_data.errors) == 1
    assert compile_data.errors[0].category == category
    assert message == compile_data.errors[0].message
    assert report_exnc == compile_data.errors[0].type
