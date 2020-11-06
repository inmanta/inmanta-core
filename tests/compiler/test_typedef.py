"""
    Copyright 2018-2019 Inmanta

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


def test_typedef_in_non_constant(snippetcompiler):
    # noqa: E501
    snippetcompiler.setup_for_error(
        """
a = "A"
typedef abc as string matching self in [a,"b","c"]

entity Test:
    abc value
end

implement Test using std::none

Test(value="a")
""",
        """Could not set attribute `value` on instance `__config__::Test (instantiated at {dir}/main.cf:11)` (reported in Construct(Test) ({dir}/main.cf:11))
caused by:
  Unable to resolve `a`: a type constraint can not reference variables. (reported in a ({dir}/main.cf:3:41))""",  # noqa: E501
    )


def test_typedef_in_violates(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
typedef abc as string matching self in ["a","b","c"]

entity Test:
    abc value
end

implement Test using std::none

Test(value="ab")
""",
        """Could not set attribute `value` on instance `__config__::Test (instantiated at {dir}/main.cf:10)` (reported in Construct(Test) ({dir}/main.cf:10))
caused by:
  Invalid value 'ab', does not match constraint `(self in ['a','b','c'])` (reported in __config__::abc ({dir}/main.cf:2:9))""",  # noqa: E501
    )


def test_typedef_exception(snippetcompiler):
    snippetcompiler.setup_for_error(
        "typedef test as string matching std::to_number({}) > 0",
        """typedef expressions should reference the self variable (reported in Type(test) ({dir}/main.cf:1:9))""",
    )


def test_1575_enum_constraint_mismatch_exception(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
typedef mytype as string matching self in ["accepted", "values"]

entity Test:
        mytype v = "value"
end

implement Test using std::none
        """,
        "Invalid value 'value', does not match constraint `(self in ['accepted','values'])`"
        " (reported in mytype v = 'value' ({dir}/main.cf:5:16))",
    )


def test_1575_regex_constraint_mismatch_exception(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
typedef mytype as string matching /accepted_value/

entity Test:
        mytype v = "value"
end

implement Test using std::none
        """,
        "Invalid value 'value', does not match constraint `/accepted_value/`"
        " (reported in mytype v = 'value' ({dir}/main.cf:5:16))",
    )


def test_1575_plugin_constraint_mismatch_exception(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
typedef mytype as list matching std::unique(self)

entity A:
        mytype v = [42, 42]
end
        """,
        "Invalid value [42, 42], does not match constraint `(std::unique(self) == true)`"
        " (reported in mytype v = List() ({dir}/main.cf:5:16))",
    )


def test_1810_type_constraint_resolution_error_message(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
x = ["allowed", "values"]
typedef mytype as string matching self in x

entity A:
    mytype myvalue = "allowed"
end
implement A using std::none
        """,
        "Unable to resolve `x`: a type constraint can not reference variables. (reported in x ({dir}/main.cf:3:43))",
    )
