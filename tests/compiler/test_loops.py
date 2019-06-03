"""
    Copyright 2018 Inmanta

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

import sys
from io import StringIO

import inmanta.compiler as compiler


def test_order_of_execution(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
for i in std::sequence(10):
    std::print(i)
end
        """
    )

    saved_stdout = sys.stdout
    try:
        out = StringIO()
        sys.stdout = out
        compiler.do_compile()
        output = out.getvalue().strip()
        assert output == "\n".join([str(x) for x in range(10)])
    finally:
        sys.stdout = saved_stdout


def test_for_error(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
        entity A:
            string a = ""
        end
        implement A using std::none
        a = A()
        for i in a:
        end
    """,
        "A for loop can only be applied to lists and relations (reported in For(i) ({dir}/main.cf:7))",
    )


def test_for_error_2(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
        for i in "foo":
        end
    """,
        "A for loop can only be applied to lists and relations (reported in For(i) ({dir}/main.cf:2))",
    )
