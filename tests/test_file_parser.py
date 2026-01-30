"""
Copyright 2021 Inmanta

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

import os
import pathlib

import pytest

import inmanta.util
import packaging.requirements
from inmanta.file_parser import RequirementsTxtParser


def test_requirements_txt_parser(tmpdir) -> None:
    content = """
        test==1.2.3

        # A comment
        other-dep~=2.0.0
        third-dep<5.0.0 # another comment
        split\
ted\
dep
        Capital
    """

    requirements_txt_file = os.path.join(tmpdir, "requirements.txt")
    with open(requirements_txt_file, "w", encoding="utf-8") as fd:
        fd.write(content)

    expected_requirements = ["test==1.2.3", "other-dep~=2.0.0", "third-dep<5.0.0", "splitteddep", "Capital"]
    requirements: list[inmanta.util.CanonicalRequirement] = RequirementsTxtParser().parse(requirements_txt_file)
    assert requirements == inmanta.util.parse_requirements(expected_requirements)
    requirements_as_str = RequirementsTxtParser.parse_requirements_as_strs(requirements_txt_file)
    assert requirements_as_str == expected_requirements

    parsed_canonical_requirements_from_file = inmanta.util.parse_requirements_from_file(pathlib.Path(requirements_txt_file))
    assert parsed_canonical_requirements_from_file == requirements

    problematic_requirements = [
        "test==1.2.3",
        "other-dep~=2.0.0",
        "third-dep<5.0.0 # another comment",
        "splitteddep",
        "Capital",
    ]

    parsed_canonical_requirements = inmanta.util.parse_requirements(expected_requirements)
    assert parsed_canonical_requirements == requirements

    with pytest.raises(Exception) as e:
        inmanta.util.parse_requirements(problematic_requirements)
    assert """Expected comma (within version specifier), semicolon (after version specifier) or end
    third-dep<5.0.0 # another comment\n""" in str(e.value)

    new_content = RequirementsTxtParser.get_content_with_dep_removed(requirements_txt_file, remove_dep_on_pkg="test")
    expected_content = """

        # A comment
        other-dep~=2.0.0
        third-dep<5.0.0 # another comment
        splitteddep
        Capital
    """
    assert new_content == expected_content
    new_content = RequirementsTxtParser.get_content_with_dep_removed(requirements_txt_file, remove_dep_on_pkg="third-dep")
    assert new_content == """
        test==1.2.3

        # A comment
        other-dep~=2.0.0
        splitteddep
        Capital
    """
    new_content = RequirementsTxtParser.get_content_with_dep_removed(requirements_txt_file, remove_dep_on_pkg="splitteddep")
    assert new_content == """
        test==1.2.3

        # A comment
        other-dep~=2.0.0
        third-dep<5.0.0 # another comment
        Capital
    """
    new_content = RequirementsTxtParser.get_content_with_dep_removed(requirements_txt_file, remove_dep_on_pkg="Capital")
    assert new_content == """
        test==1.2.3

        # A comment
        other-dep~=2.0.0
        third-dep<5.0.0 # another comment
        splitteddep
    """


@pytest.mark.parametrize(
    "iteration",
    [
        ("", True),
        ("#", True),
        ("   # ", True),
        ("#this is a comment", True),
        ("test==1.2.3", False),
        ("other-dep~=2.0.0", False),
    ],
)
def test_canonical_requirement(iteration) -> None:
    """
    Ensure that empty name requirements are not allowed in `Requirement`
    """
    name, should_fail = iteration
    if should_fail:
        with pytest.raises(packaging.requirements.InvalidRequirement):
            inmanta.util.parse_requirement(requirement=name)
    else:
        inmanta.util.parse_requirement(requirement=name)


@pytest.mark.parametrize(
    "iteration",
    [
        ("", ""),
        ("#", "#"),
        ("   # ", "#"),
        ("#this is a comment", "#this is a comment"),
        ("test==1.2.3", "test==1.2.3"),
        ("other-dep~=2.0.0", "other-dep~=2.0.0"),
        ("test==1.2.3  # a command", "test==1.2.3"),
        ("other-dep #~=2.0.0", "other-dep"),
        ("other-dep#~=2.0.0", "other-dep#~=2.0.0"),
    ],
)
def test_drop_comment_part(iteration) -> None:
    """
    Ensure that empty name requirements are not allowed in `Requirement`
    """
    value, expected_value = iteration
    current_value = inmanta.util.remove_comment_part_from_specifier(value)
    assert current_value == expected_value
