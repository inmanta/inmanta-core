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

import multiprocessing
from typing import Callable, Iterator, Optional

import pytest

Importer = Callable[[], None]


@pytest.fixture(scope="session")
def import_entry_point() -> Iterator[Callable[[Importer], Optional[int]]]:
    """
        Yields a function that runs an importer in a seperate Python process and returns the exit code.
    """
    context = multiprocessing.get_context("spawn")

    def do_import(importer: Importer) -> Optional[int]:
        process = context.Process(target=importer)
        process.start()
        process.join()
        return process.exitcode

    yield do_import


def import_execute_proxy() -> None:
    import inmanta.execute.proxy  # noqa: F401


def test_import_proxy(import_entry_point) -> None:
    assert import_entry_point(import_execute_proxy) == 0
