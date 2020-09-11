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

from inmanta.docstring_parser import parse_docstring


def test_docstring():
    """
    Test docstring which has a:
    * short description
    * long description
    * attributes
    """
    docstring = """
        This is a description.

        Next part of the description.
        Final part of the description.

        :attr param1: Description param1.
        :attr param2: Description
                      More description param2.
    """

    parsed_docstring = parse_docstring(docstring)

    assert (
        parsed_docstring.get_description() == "This is a description.\n\nNext part of the description.\nFinal part of the "
        "description."
    )

    attribute_map = {"param1": "Description param1.", "param2": "Description\nMore description param2."}

    assert parsed_docstring.get_description_for_attribute("param1") == attribute_map["param1"]
    assert parsed_docstring.get_description_for_attribute("param2") == attribute_map["param2"]
    assert parsed_docstring.get_description_for_attribute("non_existing_attr") is None
    assert parsed_docstring.get_attribute_description_map() == attribute_map


def test_docstring_only_short_description():
    """
    Test docstring consisting of a short description only.
    """
    docstring = """
        This is a description.
    """

    parsed_docstring = parse_docstring(docstring)

    assert parsed_docstring.get_description() == "This is a description."
    assert parsed_docstring.get_description_for_attribute("non_existing_attr") is None
    assert len(parsed_docstring.get_attribute_description_map()) == 0


def test_empty_docstring():
    """
    Test parser when docstring is an empty line.
    """
    parsed_docstring = parse_docstring("")

    assert parsed_docstring.get_description() is None
    assert parsed_docstring.get_description_for_attribute("non_existing_attr") is None
    assert len(parsed_docstring.get_attribute_description_map()) == 0


def test_syntax_error_in_attr_definition_docstring(caplog):
    """
    Verify that a warning is logged when a syntax error
    exists in the definition of an attribute.
    """
    docstring = """
        This is a description.

        :attr: Description param1.
        :attr param2: Description
                      More description param2.
    """

    parse_docstring(docstring)
    assert "Failed to parse attribute: ':attr: Description param1.'" in caplog.messages
