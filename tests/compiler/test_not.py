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


def test_list_not_in(snippetcompiler, capsys) -> None:
    """
    Verify the basic workings of the 'not ( value in expression)' and the 'value not in expression' syntax
    """
    snippetcompiler.setup_for_snippet(
        textwrap.dedent(
            """
            test_list = [1, 2, 3, 4, 5]
            assert = true
            assert = not (6 in test_list)
            assert = 6 not in test_list
            assert = 5 in test_list
            assert = not (5 not in test_list)
            """.strip(
                "\n"
            )
        )
    )
    compiler.do_compile()
