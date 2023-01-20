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
"""
    These tests make sure that for each module mentioned in the compiler API docs, using it as an entry point for importing
    does not result in an import loop (see #2341 and #2342).
"""

import importlib
import multiprocessing
from typing import Callable, Iterator, Optional

import pytest


@pytest.fixture(scope="session")
def import_entry_point() -> Iterator[Callable[[str], Optional[int]]]:
    """
    Yields a function that imports a module in a seperate Python process and returns the exit code.
    """
    context = multiprocessing.get_context("spawn")

    def do_import(module: str) -> Optional[int]:
        process = context.Process(target=importlib.import_module, args=(module,))
        process.start()
        process.join()
        return process.exitcode

    yield do_import


def test_import_exceptions(import_entry_point) -> None:
    assert import_entry_point("inmanta.ast") == 0
    assert import_entry_point("inmanta.parser") == 0


def test_import_plugins(import_entry_point) -> None:
    assert import_entry_point("inmanta.plugins") == 0


def test_import_resources(import_entry_point) -> None:
    assert import_entry_point("inmanta.resources") == 0
    assert import_entry_point("inmanta.execute.util") == 0


def test_import_handlers(import_entry_point) -> None:
    assert import_entry_point("inmanta.agent.handler") == 0
    assert import_entry_point("inmanta.agent.io.local") == 0


def test_import_export(import_entry_point) -> None:
    assert import_entry_point("inmanta.export") == 0


def test_import_attributes(import_entry_point) -> None:
    assert import_entry_point("inmanta.ast.attribute") == 0


def test_import_variables(import_entry_point) -> None:
    assert import_entry_point("inmanta.ast.variables") == 0


def test_import_typing(import_entry_point) -> None:
    assert import_entry_point("inmanta.ast.type") == 0


def test_import_proxy(import_entry_point) -> None:
    assert import_entry_point("inmanta.execute.proxy") == 0


def test_import_data(import_entry_point) -> None:
    assert import_entry_point("inmanta.data") == 0
    assert import_entry_point("inmanta.data.model") == 0
    assert import_entry_point("inmanta.db.util") == 0


def test_import_compile_data(import_entry_point) -> None:
    assert import_entry_point("inmanta.ast.export") == 0


def test_import_module(import_entry_point) -> None:
    assert import_entry_point("inmanta.module") == 0


def test_import_protocol(import_entry_point) -> None:
    assert import_entry_point("inmanta.protocol") == 0
    assert import_entry_point("inmanta.protocol.exceptions") == 0


def test_import_const(import_entry_point) -> None:
    assert import_entry_point("inmanta.const") == 0


def test_import_util(import_entry_point: Callable[[str], Optional[int]]) -> None:
    assert import_entry_point("inmanta.util") == 0


def test_import_ast(import_entry_point: Callable[[str], Optional[int]]) -> None:
    assert import_entry_point("inmanta.ast.constraint.expression") == 0


def test_import_env(import_entry_point: Callable[[str], Optional[int]]) -> None:
    assert import_entry_point("inmanta.env") == 0


def test_import_compiler(import_entry_point: Callable[[str], Optional[int]]) -> None:
    assert import_entry_point("inmanta.compiler") == 0


def test_import_server(import_entry_point: Callable[[str], Optional[int]]) -> None:
    assert import_entry_point("inmanta.server.extensions") == 0
    assert import_entry_point("inmanta.server.bootloader") == 0
