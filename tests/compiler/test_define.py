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
    snippetcompiler.setup_for_snippet("""
entity Test:
    string test
    bool test
end
        """)
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
        snippetcompiler.setup_for_snippet("""
    entity Entity-a:
    end
            """)
        compiler.do_compile()

    message: str = (
        f"The use of '-' in identifiers is not allowed. please rename Entity-a. "
        f"(reported in Entity-a ({snippetcompiler.project_dir}/main.cf:2:12))"
    )
    assert str(e.value) == message


def test_deprecation_minus_in_attribute_name(snippetcompiler):
    with pytest.raises(HyphenException) as e:
        snippetcompiler.setup_for_snippet("""
    entity Entity:
        string attribute-a
    end
            """)

        compiler.do_compile()

    message: str = (
        f"The use of '-' in identifiers is not allowed. please rename attribute-a. "
        f"(reported in attribute-a ({snippetcompiler.project_dir}/main.cf:3:16))"
    )
    assert str(e.value) == message


def test_deprecation_minus_in_implementation_name(snippetcompiler):
    with pytest.raises(HyphenException) as e:
        snippetcompiler.setup_for_snippet("""
entity Car:
   string brand
end

implementation vw-polo for Car:
    brand = "vw"
end
            """)
        compiler.do_compile()

    message: str = (
        f"The use of '-' in identifiers is not allowed. please rename vw-polo. "
        f"(reported in vw-polo ({snippetcompiler.project_dir}/main.cf:6:16))"
    )
    assert str(e.value) == message


def test_deprecation_minus_in_typedef_name(snippetcompiler):
    with pytest.raises(HyphenException) as e:
        snippetcompiler.setup_for_snippet("""
typedef tcp-port as int matching self > 0 and self < 65535
            """)
        compiler.do_compile()

    message: str = (
        f"The use of '-' in identifiers is not allowed. please rename tcp-port. "
        f"(reported in tcp-port ({snippetcompiler.project_dir}/main.cf:2:9))"
    )
    assert str(e.value) == message


def test_deprecation_minus_in_assign_variable_name(snippetcompiler):
    with pytest.raises(HyphenException) as e:
        snippetcompiler.setup_for_snippet("""
var-hello = "hello"
            """)
        compiler.do_compile()

    message: str = (
        f"The use of '-' in identifiers is not allowed. please rename var-hello. "
        f"(reported in var-hello ({snippetcompiler.project_dir}/main.cf:2:1))"
    )
    assert str(e.value) == message


def test_deprecation_minus_import_as(snippetcompiler):
    with pytest.raises(HyphenException) as e:
        snippetcompiler.setup_for_snippet("""
import std as std-std
            """)
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
        snippetcompiler.setup_for_snippet(f"""
entity Host:
    string  name
end

entity File:
    string path
end

{left} [0:] -- {right} [1]
            """)
    message: str = f"{msg} ({snippetcompiler.project_dir}/{location}))"
    assert str(e.value) == message


def test_import_hypen_in_name(snippetcompiler):
    with pytest.raises(CompilerException) as e:
        snippetcompiler.setup_for_snippet("""
import st-d
            """)
        compiler.do_compile()

    assert "st-d is not a valid module name: hyphens are not allowed, please use underscores instead." == e.value.msg


def test_get_all_parent_entities_sorted(snippetcompiler) -> None:
    """
    Verify that Entity.get_all_parent_entities_sorted() returns each parent entity exactly once,
    in parent-to-child and right-to-left order.
    """
    snippetcompiler.setup_for_snippet("""
entity Root:
end

entity Left extends Root:
end

entity Right extends Root:
end

entity Standalone:
end

entity Leaf extends Left, Standalone, Right:
end

entity SubLeaf extends Leaf:
end

entity DirectAndIndirectParent extends Left, Root:
end
    """)
    types, _ = compiler.do_compile()

    def get_sorted_parent_names(entity_name: str) -> list[str]:
        entity = types[f"__config__::{entity_name}"]
        return [str(parent) for parent in entity.get_all_parent_entities_sorted()]

    # Every entity implicitly extends std::Entity.
    assert get_sorted_parent_names("Root") == ["std::Entity"]
    assert get_sorted_parent_names("Standalone") == ["std::Entity"]
    assert get_sorted_parent_names("Left") == ["std::Entity", "__config__::Root"]
    assert get_sorted_parent_names("Right") == ["std::Entity", "__config__::Root"]
    assert get_sorted_parent_names("Leaf") == [
        "std::Entity",
        "__config__::Root",
        "__config__::Right",
        "__config__::Standalone",
        "__config__::Left",
    ]
    assert get_sorted_parent_names("SubLeaf") == [
        "std::Entity",
        "__config__::Root",
        "__config__::Right",
        "__config__::Standalone",
        "__config__::Left",
        "__config__::Leaf",
    ]
    # Root is both a direct parent and a parent of the direct parent Left. It must still be
    # reported only once and before Left.
    assert get_sorted_parent_names("DirectAndIndirectParent") == [
        "std::Entity",
        "__config__::Root",
        "__config__::Left",
    ]

    # The result is cached. Verify that a second invocation returns the same result and that
    # the caller cannot alter the cache by mutating the returned list.
    leaf = types["__config__::Leaf"]
    first_result = leaf.get_all_parent_entities_sorted()
    first_result.clear()
    assert get_sorted_parent_names("Leaf") == [
        "std::Entity",
        "__config__::Root",
        "__config__::Right",
        "__config__::Standalone",
        "__config__::Left",
    ]
    assert leaf.get_all_parent_entities() == set(leaf.get_all_parent_entities_sorted())
