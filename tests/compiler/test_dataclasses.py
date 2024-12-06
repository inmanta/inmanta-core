"""
    Copyright 2024 Inmanta

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

import pytest

from inmanta import compiler
from inmanta.ast import DataClassException


def test_dataclass_load(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import dataclasses
""",
        ministd=True,
    )
    compiler.do_compile()


def test_dataclass_load_bad(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import dataclasses::bad_sub
""",
        ministd=True,
    )
    with pytest.raises(DataClassException, match="Dataclasses must have a python counterpart that is a frozen dataclass"):
        compiler.do_compile()
