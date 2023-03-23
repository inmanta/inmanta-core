"""
    Copyright 2023 Inmanta

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
import textwrap

from inmanta import compiler


def test_list_comprehension_basic(snippetcompiler) -> None:
    snippetcompiler.setup_for_snippet(
        textwrap.dedent(
            """
            base = [1, 2, 3, 4, 5]

            l1 = [x for x in base]
            l2 = ["x={{x}}" for x in base]
            l3 = [x > 2 ? x : 0 for x in base]

            l1 = base
            l2 = ["x=1", "x=2", "x=3", "x=4", "x=5"]
            l3 = [0, 0, 3, 4, 5]
            """.strip(
                "\n"
            )
        )
    )
    compiler.do_compile()
