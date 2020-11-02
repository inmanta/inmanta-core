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
import re

import pytest

import inmanta.compiler as compiler
from inmanta.ast import DuplicateException


def test_2386_duplicate_attribute_error_message(snippetcompiler) -> None:
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    string test
    bool test
end
        """
    )
    dir: str = snippetcompiler.project_dir
    with pytest.raises(
        DuplicateException,
        match=re.escape(f"attribute already exists (original at ({dir}/main.cf:3:12)) (duplicate at ({dir}/main.cf:4:10))"),
    ):
        compiler.do_compile()
