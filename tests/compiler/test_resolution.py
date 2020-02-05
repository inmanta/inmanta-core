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

import inmanta.compiler as compiler
from inmanta.ast import DuplicateException, NotFoundException, TypeNotFoundException, TypingException


def test_issue_92(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
    entity Host extends std::NotThere:
    end
"""
    )
    try:
        compiler.do_compile()
        raise AssertionError("Should get exception")
    except TypeNotFoundException as e:
        assert e.location.lnr == 2


def test_issue_73(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
vm1 = std::floob()
"""
    )
    with pytest.raises(TypeNotFoundException):
        compiler.do_compile()


def test_issue_110_resolution(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test1:

end
implement Test1 using test1i


implementation test1i for Test1:
    test = host
end

t = Test1()
"""
    )
    with pytest.raises(NotFoundException):
        compiler.do_compile()


def test_issue_134_colliding_umplementations(snippetcompiler):

    snippetcompiler.setup_for_snippet(
        """
implementation test for std::Entity:
end
implementation test for std::Entity:
end"""
    )
    with pytest.raises(DuplicateException):
        compiler.do_compile()


def test_issue_164_fqn_in_when(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
implementation linux for std::HostConfig:
end

implement std::HostConfig using linux when host.os == std::linux

std::Host(name="vm1", os=std::linux)
"""
    )
    compiler.do_compile()


def test_400_typeloops(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
    entity Test extends Test:

    end
    """
    )
    with pytest.raises(TypingException):
        compiler.do_compile()


def test_400_typeloops_2(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
    entity Test extends Test2:

    end

    entity Test2 extends Test:

    end
    """
    )
    with pytest.raises(TypingException):
        compiler.do_compile()


def test_438_parent_scopes_accessible(snippetcompiler):

    snippetcompiler.setup_for_snippet(
        """
entity Host:
    string name
end

entity HostConfig:
    string result
end

HostConfig.host [1] -- Host

implementation hostDefaults for Host:
    test="foo"
    HostConfig(host=self)
end

implement Host using hostDefaults

implementation test for HostConfig:
    # fails correctly
    # std::print(test)
    # works and should fail
    self.result = name
end

implement HostConfig using test

Host(name="bar")
""",
        autostd=False,
    )
    with pytest.raises(NotFoundException):
        compiler.do_compile()


def test_438_parent_scopes_accessible_2(snippetcompiler):

    snippetcompiler.setup_for_snippet(
        """
entity Host:
    string name
end

entity HostConfig:
    string result
end

HostConfig.host [1] -- Host

implementation hostDefaults for Host:
    test="foo"
    HostConfig(host=self)
end

implement Host using hostDefaults

implementation test for HostConfig:
    self.result = test
end

implement HostConfig using test

Host(name="bar")
""",
        autostd=False,
    )
    with pytest.raises(NotFoundException):
        compiler.do_compile()


def test_484_attr_redef(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
typedef type as string matching self == "component" or self == "package" or self == "frame"

entity Node:
    type viz_type
end

entity Group extends Node:
end

entity Service extends Group:
    string viz_type="package"
end
""",
        autostd=False,
    )
    with pytest.raises(DuplicateException):
        compiler.do_compile()


def test_duplicate_attribute(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Node:
    string viz_type
    string viz_type
end
""",
        autostd=False,
    )
    with pytest.raises(DuplicateException):
        compiler.do_compile()


def test_bad_deref(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
h = std::Host(name="test", os=std::linux)
std::print(h.name.test)
""",
        "can not get a attribute test, test not an entity (reported in h.name.test ({dir}/main.cf:3))",
    )


def test_672_missing_type(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
        entity Test:
        end

        implementation test for Testt:
        end

        """,
        "could not find type Testt in namespace __config__" " (reported in Implementation(test) ({dir}/main.cf:5:33))",
    )
