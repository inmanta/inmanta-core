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
from inmanta.ast import CompilerException, DuplicateException, HyphenException


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
        match=re.escape(
            f"attribute 'test' already exists on entity 'Test' (original at ({dir}/main.cf:3:12)) "
            f"(duplicate at ({dir}/main.cf:4:10))"
        ),
    ):
        compiler.do_compile()


def test_deprecation_minus_in_entity_name(snippetcompiler):
    with pytest.raises(HyphenException) as e:
        snippetcompiler.setup_for_snippet(
            """
    entity Entity-a:
    end
            """
        )
        compiler.do_compile()

    message: str = (
        f"The use of '-' in identifiers is not allowed. please rename Entity-a. "
        f"(reported in Entity-a ({snippetcompiler.project_dir}/main.cf:2:12))"
    )
    assert str(e.value) == message


def test_deprecation_minus_in_attribute_name(snippetcompiler):
    with pytest.raises(HyphenException) as e:
        snippetcompiler.setup_for_snippet(
            """
    entity Entity:
        string attribute-a
    end
            """
        )

        compiler.do_compile()

    message: str = (
        f"The use of '-' in identifiers is not allowed. please rename attribute-a. "
        f"(reported in attribute-a ({snippetcompiler.project_dir}/main.cf:3:16))"
    )
    assert str(e.value) == message


def test_deprecation_minus_in_implementation_name(snippetcompiler):
    with pytest.raises(HyphenException) as e:
        snippetcompiler.setup_for_snippet(
            """
entity Car:
   string brand
end

implementation vw-polo for Car:
    brand = "vw"
end
            """
        )
        compiler.do_compile()

    message: str = (
        f"The use of '-' in identifiers is not allowed. please rename vw-polo. "
        f"(reported in vw-polo ({snippetcompiler.project_dir}/main.cf:6:16))"
    )
    assert str(e.value) == message


def test_deprecation_minus_in_typedef_name(snippetcompiler):
    with pytest.raises(HyphenException) as e:
        snippetcompiler.setup_for_snippet(
            """
typedef tcp-port as int matching self > 0 and self < 65535
            """
        )
        compiler.do_compile()

    message: str = (
        f"The use of '-' in identifiers is not allowed. please rename tcp-port. "
        f"(reported in tcp-port ({snippetcompiler.project_dir}/main.cf:2:9))"
    )
    assert str(e.value) == message


def test_deprecation_minus_in_assign_variable_name(snippetcompiler):
    with pytest.raises(HyphenException) as e:
        snippetcompiler.setup_for_snippet(
            """
var-hello = "hello"
            """
        )
        compiler.do_compile()

    message: str = (
        f"The use of '-' in identifiers is not allowed. please rename var-hello. "
        f"(reported in var-hello ({snippetcompiler.project_dir}/main.cf:2:1))"
    )
    assert str(e.value) == message


def test_deprecation_minus_import_as(snippetcompiler):
    with pytest.raises(HyphenException) as e:
        snippetcompiler.setup_for_snippet(
            """
import std as std-std
            """
        )
        compiler.do_compile()

    message: str = (
        f"The use of '-' in identifiers is not allowed. please rename std-std. "
        f"(reported in std-std ({snippetcompiler.project_dir}/main.cf:2:15))"
    )
    assert str(e.value) == message


@pytest.mark.parametrize_any(
    "left, right, msg, location",
    [
        (
            "Host.files-hehe",
            "File.host",
            "The use of '-' in identifiers is not allowed. please rename files-hehe. (" "reported in files-hehe",
            "main.cf:10:6",
        ),
        (
            "Host.files",
            "File.host-hoho",
            "The use of '-' in identifiers is not allowed. please rename host-hoho. (" "reported in host-hoho",
            "main.cf:10:25",
        ),
    ],
)
def test_deprecation_minus_relation(snippetcompiler, left, right, msg, location):
    with pytest.raises(HyphenException) as e:
        snippetcompiler.setup_for_snippet(
            f"""
entity Host:
    string  name
end

entity File:
    string path
end

{left} [0:] -- {right} [1]
            """
        )
    message: str = f"{msg} ({snippetcompiler.project_dir}/{location}))"
    assert str(e.value) == message


def test_import_hypen_in_name(snippetcompiler):
    with pytest.raises(CompilerException) as e:
        snippetcompiler.setup_for_snippet(
            """
import st-d
            """
        )
        compiler.do_compile()

    assert "st-d is not a valid module name: hyphens are not allowed, please use underscores instead." == e.value.msg
