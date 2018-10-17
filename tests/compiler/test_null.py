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

import pytest

from inmanta.ast import OptionalValueException
import inmanta.compiler as compiler
from inmanta.execute.util import NoneValue


def test_null(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
        entity A:
            string? a = null
        end
        implement A using std::none
        a = A()

    """
    )

    (_, scopes) = compiler.do_compile()
    root = scopes.get_child("__config__")
    a = root.lookup("a").get_value().get_attribute("a").get_value()
    assert isinstance(a, NoneValue)


def test_null_unset(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
        entity A:
            string? a
        end
        implement A using std::none
        a = A()

    """
    )

    (_, scopes) = compiler.do_compile()
    root = scopes.get_child("__config__")
    with pytest.raises(OptionalValueException):
        root.lookup("a").get_value().get_attribute("a").get_value()


def test_null_unset_hang(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
            entity A:
                string? a
            end
            implement A using std::none
            a = A()
            b = a.a
        """
    )
    with pytest.raises(OptionalValueException):
        (_, scopes) = compiler.do_compile()


def test_null_on_list(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
        entity A:
            string[]? a = null
        end
        implement A using std::none
        a = A()
    """
    )

    (_, scopes) = compiler.do_compile()
    root = scopes.get_child("__config__")
    a = root.lookup("a").get_value().get_attribute("a").get_value()
    assert isinstance(a, NoneValue)


def test_null_on_dict(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
        entity A:
            dict? a = null
        end
        implement A using std::none
        a = A()
    """
    )

    (_, scopes) = compiler.do_compile()
    root = scopes.get_child("__config__")
    a = root.lookup("a").get_value().get_attribute("a").get_value()
    assert isinstance(a, NoneValue)
