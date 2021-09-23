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

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap


class PreservativeYamlParser:
    """
    A Yaml parser that tries to preserve comments and the order of elements.
    This parser doesn't preserve indentation.
    """

    @classmethod
    def _get_parser(cls) -> YAML:
        parser = YAML()
        # Make sure the indentation settings are used consistently
        parser.indent(mapping=2, sequence=4, offset=2)
        return parser

    @classmethod
    def parse(cls, filename: str) -> CommentedMap:
        parser = cls._get_parser()
        with open(filename, "r", encoding="utf-8") as fd:
            return parser.load(fd)

    @classmethod
    def dump(cls, filename: str, content: CommentedMap) -> None:
        parser = cls._get_parser()
        with open(filename, "w", encoding="utf-8") as fd:
            parser.dump(content, stream=fd)


class RequirementsTxtParser:
    """
    Parser for a requirements.txt file
    """

    @classmethod
    def parse(cls, filename: str) -> List[Requirement]:
        """
        Get all the requirements in `filename` as a list of `Requirement` instances.
        """
        return [Requirement.parse(r) for r in cls.parse_requirements_as_strs(filename)]

    @classmethod
    def parse_requirements_as_strs(cls, filename: str) -> List[str]:
        """
        Get all the requirements in `filename` as a list of strings.
        """
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as fd:
                requirements_txt_content = fd.read()
                req_lines = [x.strip() for x in requirements_txt_content.split("\n") if len(x.strip()) > 0]
                req_lines = cls._remove_comments(req_lines)
                req_lines = cls._remove_line_continuations(req_lines)
                return list(req_lines)
        else:
            return []

    @classmethod
    def get_content_with_dep_removed(cls, filename: str, remove_dep_on_pkg: str) -> str:
        """
        Returns the content of the requirements.txt file with the dependency on `remove_dep_on_pkg` removed.
        This method preserves all the comments.
        """
        if not os.path.exists(filename):
            raise Exception(f"File {filename} doesn't exist")

        result = ""
        line_continuation_buffer = ""
        with open(filename, "r", encoding="utf-8") as fd:
            for line in fd.readlines():
                if line_continuation_buffer:
                    line_continuation_buffer += line
                    if not line.endswith("\\"):
                        if Requirement.parse(line_continuation_buffer).key != remove_dep_on_pkg:
                            result += line_continuation_buffer
                        line_continuation_buffer = ""
                elif not line.strip() or line.strip().startswith("#"):
                    result += line
                elif line.endswith("\\"):
                    line_continuation_buffer = line
                elif Requirement.parse(line).key != remove_dep_on_pkg.lower():
                    result += line
                else:
                    # Dependency matches `remove_dep_on_pkg` => Remove line from result
                    pass
        return result

    @classmethod
    def _remove_comments(cls, lines: List[str]) -> List[str]:
        """
        This method removes elements from the given list that only include comments. If the element
        combines a comment with a version constraint, the comment part is removed from the element.

        :param lines: The lines from a requirements.txt file with all empty lines removes.
        """
        result = []
        for line in lines:
            if line.strip().startswith("#"):
                continue
            if " #" in line:
                line_without_comment = line.split(" #", maxsplit=1)[0]
                result.append(line_without_comment)
            else:
                result.append(line)
        return result

    @classmethod
    def _remove_line_continuations(cls, lines: List[str]) -> List[str]:
        """
        Join two different list elements together if they are separated by a line continuation token.

        :param lines: The lines from a requirements.txt file with all empty lines removes.
        """
        result = []
        line_continuation_buffer = ""
        for line in lines:
            if line.endswith("\\"):
                line_continuation_buffer = f"{line_continuation_buffer}{line[0:-1]}"
            else:
                if line_continuation_buffer:
                    result.append(f"{line_continuation_buffer}{line}")
                    line_continuation_buffer = ""
                else:
                    result.append(line)
        return result
