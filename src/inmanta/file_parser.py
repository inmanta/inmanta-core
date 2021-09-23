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
