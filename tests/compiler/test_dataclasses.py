"""
    Copyright 2024 Inmanta

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

import pytest

from inmanta import compiler
from inmanta.ast import (
    AttributeException,
    DataClassException,
    DataClassMismatchException,
    RuntimeException,
    WrappingRuntimeException,
)
from inmanta.compiler.help.explainer import DataclassExplainer


def test_dataclass_positive(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import dataclasses

# Construct in model
two = dataclasses::Virtualmachine(name="A", os={}, ram=1, cpus={"a":5}, disk=[10], slots=[])

# from python into plugin
dataclasses::eat_vm(two)

# Construct in python
one=dataclasses::make_virtual_machine()

# Relations work
one.requires = one

# from model into plugin
dataclasses::eat_vm(one)

# # partial object into plugin
three = dataclasses::Virtualmachine(name="B", os={}, ram=null, cpus={"a":5}, slots=[])
dataclasses::eat_vm(three)
three.disk = [5]


# List into plugin
vms = [one, two, three]
selected = dataclasses::select_vm(vms, "A")


# Preserves object identity
# one = selected

# Return null
assert_true = dataclasses::select_vm(vms, "z") == null
assert_true = true


# List from relation into plugin
entity VMCollector:
end

implement VMCollector using std::none

VMCollector.vms [0:] -- dataclasses::Virtualmachine

c1 = VMCollector()
c1.vms += one
c1.vms += two
c1.vms += three

other_selected = dataclasses::select_vm(c1.vms, "A")


the_vms = dataclasses::make_vms()
std::print(the_vms)
""",
        ministd=True,
    )
    compiler.do_compile()


def test_dataclass_load_bad(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import dataclasses::bad_sub
""",
        ministd=True,
    )
    with pytest.raises(DataClassException, match="Dataclasses must have a python counterpart that is a frozen dataclass"):
        compiler.do_compile()


def test_dataclass_load_bad_fields(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import dataclasses::bad_sub_fields
""",
        ministd=True,
    )
    error_first_line_regex = "The dataclass dataclasses::bad_sub_fields::Virtualmachine defined at .*/bad_sub_fields.* does not match the corresponding python dataclass at .*/bad_sub_fields.*. 7 errors:"

    with pytest.raises(DataClassMismatchException, match=error_first_line_regex) as e:
        compiler.do_compile()

    message = str(e.value)
    field_lines = [
        "-The attribute os does not have the same type as the associated field in the python domain. All attributes of a dataclasses must be identical in both the python and inmanta domain.",
        "-The attribute it does not have the same type as the associated field in the python domain. All attributes of a dataclasses must be identical in both the python and inmanta domain.",
        "-The attribute ot does not have the same type as the associated field in the python domain. All attributes of a dataclasses must be identical in both the python and inmanta domain.",
        "-The attribute ram has no counterpart in the python domain. All attributes of a dataclasses must be identical in both the python and inmanta domain.",
        "-The attribute disk does not have the same type as the associated field in the python domain. All attributes of a dataclasses must be identical in both the python and inmanta domain.",
        "-The field cpus doesn't exist in the inmanta domain. All attributes of a dataclasses must be identical in both the python and inmanta domain",
    ]
    for line in field_lines:
        assert line in message
    # regexes
    assert e.match(
        "-a relation called subs is defined at .*/bad_sub_fields.cf:.* Dataclasses are not allowed to have relations"
    )

    # explainer
    explanation = DataclassExplainer().explain(e.value)[0]
    assert (
        """To update the python class, add the following code to inmanta_plugins.dataclasses.bad_sub_fields.Virtualmachine:

import dataclasses

@dataclasses.dataclass(frozen=True)
class Virtualmachine:
   \"""inmanta comment\"""
   disk: dict[str, object]
   it: str
   name: str
   os: list[str] | None
   ot: list[str]
   other: dict[str, object]
   ram: int
"""
        in explanation
    )

    assert (
        """entity Virtualmachine extends std::Dataclass:
   \""" Python comment \"""
   int cpus
   ERROR disk
   int it
   string name
   string[] os
   int ot
   dict other
end"""
        in explanation
    )


def test_dataclass_instance_failure(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import dataclasses

# Construct in model
two = dataclasses::make_bad_virtual_machine()""",
        ministd=True,
    )
    with pytest.raises(WrappingRuntimeException, match="Exception in plugin dataclasses::make_bad_virtual_machine") as e:
        compiler.do_compile()

    cause = e.value.get_causes()[0]
    assert isinstance(cause, AttributeException)
    assert "Could not set attribute `disk` on instance `dataclasses::Virtualmachine" in str(cause)
    cause = cause.get_causes()[0]
    assert isinstance(cause, RuntimeException)
    assert "Invalid value 'root', expected int (reported in dataclasses::make_bad_virtual_machine()" in str(cause)
