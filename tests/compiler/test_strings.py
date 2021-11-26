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

import inmanta.compiler as compiler
from inmanta.ast import Namespace


def test_multiline_string_interpolation(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
var = 42
str = \"\"\"var == {{var}}\"\"\"
        """,
    )
    (_, scopes) = compiler.do_compile()
    root: Namespace = scopes.get_child("__config__")
    assert root.lookup("str").get_value() == "var == 42"


def test_rstring(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
z=r"{{xxx}}"

entity X:
    string a
end

# Force typecheck
X(a=z)

implement X using none
implementation none for X:
end
        """,
    )
    compiler.do_compile()
