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

import logging
from typing import Dict, Optional

import docstring_parser

LOGGER = logging.getLogger(__name__)


class DocString:
    def __init__(self, doc_string: docstring_parser.Docstring) -> None:
        # Ignore attribute definitions with a syntax error
        new_meta = []
        for attr in doc_string.meta:
            # attr.args contains the part of an attribute definition in the docstring between the
            # colons splitted on white spaces. This check enforces the format :attr <attribute-name>:
            if len(attr.args) != 2 or attr.args[0] != "attr":
                LOGGER.warning("Failed to parse attribute: ':%s: %s'", " ".join(attr.args), attr.description)
            else:
                new_meta.append(attr)
        doc_string.meta = new_meta

        self._attr_description_map: Dict[str, str] = {attr.args[1]: attr.description for attr in doc_string.meta}
        self._doc_string: docstring_parser.Docstring = doc_string

    def get_description(self) -> Optional[str]:
        """
        Return the general description in the docstring.
        """
        if self._doc_string.short_description is None:
            return None
        if self._doc_string.long_description is not None:
            return f"{self._doc_string.short_description}\n\n{self._doc_string.long_description}"
        else:
            return self._doc_string.short_description

    def get_description_for_attribute(self, attr_name: str) -> Optional[str]:
        """
        Return the description for a certain attribute.
        """
        return self._attr_description_map.get(attr_name, None)

    def get_attribute_description_map(self) -> Dict[str, str]:
        """
        Return the dict which maps the attribute name to its description.
        """
        return dict(self._attr_description_map)


def parse_docstring(doc_string: str) -> DocString:
    """
    Parse the docstring of an entity.
    """
    doc_string = docstring_parser.parse(doc_string, style=docstring_parser.DocstringStyle.REST)
    return DocString(doc_string)
