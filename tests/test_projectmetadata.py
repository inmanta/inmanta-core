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
from typing import List, Optional

import pytest

from inmanta.module import ModuleRepoType, ProjectMetadata, RelationPrecedenceRule


@pytest.mark.parametrize(
    "repo",
    [
        ("https://github.com/inmanta/{}.git"),
        ("git@github.com:inmanta/{}.git"),
        (["https://github.com/inmanta/{}.git"]),
        (["git@github.com:inmanta/{}.git"]),
        ([{"type": ModuleRepoType.git, "url": "https://github.com/inmanta/{}.git"}]),
        ([{"type": ModuleRepoType.git, "url": "https://github.com/inmanta/{}.git"}]),
    ],
)
def test_repo_parsing(repo):
    project_metadata = ProjectMetadata(name="test", repo=repo)
    if isinstance(repo, str):
        assert len(project_metadata.repo) == 1
        assert project_metadata.repo[0].type == ModuleRepoType.git
        assert project_metadata.repo[0].url == repo
    else:
        for index, value in enumerate(repo):
            if isinstance(value, str):
                assert project_metadata.repo[index].type == ModuleRepoType.git
                assert project_metadata.repo[index].url == value
            else:
                assert project_metadata.repo[index].type == value["type"]
                assert project_metadata.repo[index].url == value["url"]


@pytest.mark.parametrize(
    "precedence_rule, valid, expected_precedence_rule",
    [
        (["a before b", False, None]),  # Entity type missing
        (["A::a before B::b", False, None]),  # Relationship name missing
        (["A.a befor B.b", False, None]),  # before is misspelled
        (["A:B.attr1 B:b.attr2", False, None]),  # Single colon instead of double colon
        (["A.a before B.b", True, RelationPrecedenceRule("A", "a", "B", "b")]),
        (
            [
                "__config__::B-B123.a before __config__::CC.b",
                True,
                RelationPrecedenceRule("__config__::B-B123", "a", "__config__::CC", "b"),
            ]
        ),
        (["   A.b     before     B.c   ", True, RelationPrecedenceRule("A", "b", "B", "c")]),
    ],
)
def test_relation_precedence_policy_parsing(
    precedence_rule: str, valid: bool, expected_precedence_rule: Optional[RelationPrecedenceRule]
) -> None:
    if valid:
        assert expected_precedence_rule is not None
        project_metadata = ProjectMetadata(name="test", relation_precedence_policy=[precedence_rule])
        relation_precedence_rules: List[RelationPrecedenceRule] = project_metadata.get_relation_precedence_rules()
        assert len(relation_precedence_rules) == 1
        assert relation_precedence_rules[0] == expected_precedence_rule
    else:
        with pytest.raises(ValueError):
            ProjectMetadata(name="test", relation_precedence_policy=[precedence_rule])
