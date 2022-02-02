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
from typing import List

from pkg_resources import Requirement

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
    requirements: List[Requirement] = RequirementsTxtParser().parse(requirements_txt_file)
    assert requirements == [Requirement.parse(r) for r in expected_requirements]
    requirements_as_str = RequirementsTxtParser.parse_requirements_as_strs(requirements_txt_file)
    assert requirements_as_str == expected_requirements

    new_content = RequirementsTxtParser.get_content_with_dep_removed(requirements_txt_file, remove_dep_on_pkg="test")
    assert (
        new_content
        == """
        # A comment
        other-dep~=2.0.0
        third-dep<5.0.0 # another comment
        splitteddep
        Capital
    """
    )
    new_content = RequirementsTxtParser.get_content_with_dep_removed(requirements_txt_file, remove_dep_on_pkg="third-dep")
    assert (
        new_content
        == """
        test==1.2.3
        # A comment
        other-dep~=2.0.0
        splitteddep
        Capital
    """
    )
    new_content = RequirementsTxtParser.get_content_with_dep_removed(requirements_txt_file, remove_dep_on_pkg="splitteddep")
    assert (
        new_content
        == """
        test==1.2.3
        # A comment
        other-dep~=2.0.0
        third-dep<5.0.0 # another comment
        Capital
    """
    )
    new_content = RequirementsTxtParser.get_content_with_dep_removed(requirements_txt_file, remove_dep_on_pkg="Capital")
    assert (
        new_content
        == """
        test==1.2.3
        # A comment
        other-dep~=2.0.0
        third-dep<5.0.0 # another comment
        splitteddep
    """
    )
