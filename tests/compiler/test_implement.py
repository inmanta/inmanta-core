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

from typing import Dict

import pytest

import inmanta.compiler as compiler
from inmanta.ast import Namespace
from inmanta.execute.runtime import Instance, ResultVariable, Typeorvalue


@pytest.mark.parametrize("parents", [True, False])
def test_implement_parents(snippetcompiler, parents: bool):
    snippetcompiler.setup_for_snippet(
        """
entity Parent:
    number n
end

entity Child extends Parent:
    number m
end

implement Parent using p
implement Child using %s, generic


implementation p for Parent:
    self.n = 0
end

implementation c for Child:
    self.n = 1
end

implementation generic for Child:
    self.m = 0
end


x = Child()
        """
        % ("parents" if parents else "c"),
    )
    (_, scopes) = compiler.do_compile()
    root: Namespace = scopes.get_child("__config__")
    x: Typeorvalue = root.lookup("x")
    assert isinstance(x, ResultVariable)
    instance = x.get_value()
    assert isinstance(instance, Instance)

    expected_attrs: Dict[str, int] = {"n": 0 if parents else 1, "m": 0}
    for name, value in expected_attrs.items():
        attr: Typeorvalue = instance.lookup(name)
        assert isinstance(attr, ResultVariable)
        assert attr.get_value() == value


def test_implement_parents_conditional_error(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity Parent:
end

entity Child extends Parent:
end

implement Parent using std::none
implement Child using std::none
implement Child using parents when 1 == 1


x = Child()
        """,
        "Conditional implementation with parents not allowed (reported in Implement(Child) ({dir}/main.cf:10:11))",
    )
