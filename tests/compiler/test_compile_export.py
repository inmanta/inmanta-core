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
import re
from tempfile import mkstemp
from typing import Optional, Type

import pytest

import inmanta.ast.export as ast_export
import inmanta.compiler as compiler
from inmanta.ast import CompilerException, DoubleSetException, ExplicitPluginException, NotFoundException
from inmanta.compiler.data import ExportCompileData
from inmanta.config import Config
from inmanta.parser import ParserException


def export_to_file(file: str, expected_error_type: Optional[Type[CompilerException]] = None) -> ExportCompileData:
    """
        Compiles, exporting to a file, and returns the file contents, loaded as ExportCompileData.
    """
    Config.set("compiler", "data_export", "true")
    Config.set("compiler", "data_export_file", file)
    if expected_error_type is None:
        compiler.do_compile()
    else:
        with pytest.raises(CompilerException):
            compiler.do_compile()
    with open(file) as f:
        return ExportCompileData(**json.loads(f.read()))


def export_to_tempfile(expected_error_type: Optional[Type[CompilerException]] = None) -> ExportCompileData:
    return export_to_file(mkstemp(text=True)[1], expected_error_type)


@pytest.mark.parametrize("explicit", [True, False])
def test_export_compile_data_to_stdout(capsys, snippetcompiler, explicit: bool) -> None:
    snippetcompiler.setup_for_snippet(
        """
x = 0
        """,
    )
    Config.set("compiler", "data_export", "true")
    if explicit:
        Config.set("compiler", "data_export_file", "-")
    compiler.do_compile()
    match: Optional[re.Match] = re.search(
        "---START export-compile-data---\n(.*)\n---END export-compile-data---\n", capsys.readouterr().out
    )
    assert match is not None
    assert ExportCompileData(**json.loads(match.group(1)))


def test_export_compile_data_to_file(snippetcompiler) -> None:
    snippetcompiler.setup_for_snippet(
        """
x = 0
        """,
    )
    assert len(export_to_tempfile().errors) == 0


def test_export_compile_data_to_file_overwrite(snippetcompiler) -> None:
    file: str = mkstemp(text=True)[1]
    for _ in range(2):
        snippetcompiler.setup_for_snippet(
            """
x = 0
            """,
        )
        assert len(export_to_file(file).errors) == 0


def test_export_compile_data_to_file_error(snippetcompiler) -> None:
    snippetcompiler.setup_for_snippet(
        """
x = 0
x = 1
        """,
    )
    compile_data: ExportCompileData = export_to_tempfile(DoubleSetException)
    assert len(compile_data.errors) == 1
    error: ast_export.Error = compile_data.errors[0]
    assert error.category == ast_export.ErrorCategory.runtime
    assert error.type == "<class 'inmanta.ast.DoubleSetException'>"
    filename = f"{snippetcompiler.project_dir}/main.cf"
    assert error.message == (
        f"value set twice:\n\told value: 0\n\t\tset at {filename}:2\n\tnew value: 1\n\t\tset at {filename}:3\n"
    )
    assert error.location == ast_export.Location(
        uri=filename,
        range=ast_export.Range(start=ast_export.Position(line=2, character=0), end=ast_export.Position(line=3, character=0)),
    )


@pytest.mark.parametrize(
    "snippet,exception,category",
    [
        ("1 = 1", ParserException, ast_export.ErrorCategory.parser),
        ("x.n = 1", NotFoundException, ast_export.ErrorCategory.runtime),
        ("import tests tests::raise_exception('my message')", ExplicitPluginException, ast_export.ErrorCategory.plugin),
    ],
)
def test_export_compile_data_to_file_categories(
    snippetcompiler, snippet: str, exception: Type[CompilerException], category: ast_export.ErrorCategory
) -> None:
    snippetcompiler.setup_for_snippet(snippet)
    compile_data: ExportCompileData = export_to_tempfile(exception)
    assert len(compile_data.errors) == 1
    assert compile_data.errors[0].category == category
