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

import os.path
import re
import textwrap

import pytest

from inmanta import compiler
from inmanta.ast import (
    AttributeException,
    DataClassException,
    DataClassMismatchException,
    PluginTypeException,
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

# from python into plugin
dataclasses::eat_vm_dynamic(two)

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

entity HasString:
    string thestring
end
implement HasString using std::none


# Make sure we pass string like things unchanged
# but otherwise have it as a string
hs = HasString(thestring = dataclasses::odd_string())
if hs.thestring != "it":
   a = 1
   a = 2
else:
   hs.thestring = "it"
end
dataclasses::is_odd_string(hs.thestring)

# A dataclass instance that is still waiting for its values when the plugin is called.
# Plugins need to be able to reschedule when not all values are present yet. This includes when we try to construct a
# dataclass instance for which not all values are there yet. This scenario verifies the absence of a bug that was
# discovered in the `Union` type during #8946
lazy_vm = dataclasses::Virtualmachine()
dataclasses::dc_union(lazy_vm)
if true: if true:
    # nest the assignments to make sure the plugin is called before this is executed
    lazy_vm.name = "lazy_vm"
    lazy_vm.os = {}
    lazy_vm.ram = null
    lazy_vm.cpus = {}
    lazy_vm.disk = []
    lazy_vm.slots = null
end end

# simple inheritance
simple_dc = dataclasses::create_simple_dc()
assert = true
assert = simple_dc.n == 42
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
    error_first_line_regex = "The dataclass dataclasses::bad_sub_fields::Virtualmachine defined at .*/bad_sub_fields.* does "
    "not match the corresponding python dataclass at .*/bad_sub_fields.*. 7 errors:"

    with pytest.raises(DataClassMismatchException, match=error_first_line_regex) as e:
        compiler.do_compile()

    message = str(e.value)
    field_lines = [
        "-The attribute os does not have the same type as the associated field in the python domain. "
        "All attributes of a dataclasses must be identical in both the python and inmanta domain.",
        "-The attribute it does not have the same type as the associated field in the python domain. "
        "All attributes of a dataclasses must be identical in both the python and inmanta domain.",
        "-The attribute ot does not have the same type as the associated field in the python domain. "
        "All attributes of a dataclasses must be identical in both the python and inmanta domain.",
        "-The attribute ram has no counterpart in the python domain. All attributes of a dataclasses "
        "must be identical in both the python and inmanta domain.",
        "-The attribute disk does not have the same type as the associated field in the python domain. "
        "All attributes of a dataclasses must be identical in both the python and inmanta domain.",
        "-The field cpus doesn't exist in the inmanta domain. All attributes of a dataclasses must be "
        "identical in both the python and inmanta domain",
    ]
    for line in field_lines:
        assert line in message
    # regexes
    assert e.match(
        "-a relation called subs is defined at .*/bad_sub_fields.cf:.* Dataclasses are not allowed to have relations"
    )

    # explainer
    explanation = DataclassExplainer().explain(e.value)[0]
    assert """To update the python class, add the following code to inmanta_plugins.dataclasses.bad_sub_fields.Virtualmachine:

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
""" in explanation

    assert """entity Virtualmachine extends std::Dataclass:
   \"""Python comment\"""
   int cpus
   ERROR disk
   int it
   string name
   string[] os
   int ot
   dict other
end""" in explanation


def test_dataclass_type_check(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import dataclasses

# Construct in model
two = dataclasses::eat_vm("test")""",
        ministd=True,
    )

    with pytest.raises(
        PluginTypeException,
        match="Value 'test' for argument inp of plugin dataclasses::eat_vm has incompatible type. "
        "Expected type: dataclasses::Virtualmachine",
    ):
        compiler.do_compile()


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


def test_returning_any(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import dataclasses


it = dataclasses::return_any()

a=it.name
a= "Test"
""",
        ministd=True,
    )
    compiler.do_compile()


def test_docs(snippetcompiler):
    base_path = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "model_developers", "examples")
    if not os.path.exists(base_path):
        pytest.skip("Documentation not found")

    def read_file(name: str) -> str:
        with open(os.path.join(base_path, name), "r") as fh:
            return fh.read()

    def run_for_example(name: str) -> None:
        snippetcompiler.create_module(f"datatest{name}", read_file(f"dataclass_{name}.cf"), read_file(f"dataclass_{name}.py"))
        snippetcompiler.setup_for_snippet(f"import datatest{name}", autostd=True)
        compiler.do_compile()

    run_for_example("1")
    run_for_example("2")


def test_dataclass_plugin_boundary_null(snippetcompiler):
    """
    Verify null conversion for dataclass fields on the plugin boundary.
    """
    snippetcompiler.setup_for_snippet(
        """\
import dataclasses

x = dataclasses::NullableDC(n=1)
y = dataclasses::NullableDC(n=null)
z = dataclasses::CollectionDC(l=[1, null, 3], d={"one": 1, "null": null})

dataclasses::takes_nullable_dc(x)
dataclasses::takes_nullable_dc(y)
dataclasses::takes_collection_dc(z)
        """,
        ministd=True,
    )

    compiler.do_compile()


def test_dataclass_plugin_boundary_unknown(snippetcompiler):
    """
    Verify that unknowns are rejected in dataclass fields on the plugin boundary.
    """

    e: PluginTypeException

    # - unknown nested in list
    snippetcompiler.setup_for_snippet(
        """\
import dataclasses
import tests

x = dataclasses::NullableDC(n=tests::unknown())

dataclasses::takes_nullable_dc(x)
        """,
        ministd=True,
    )
    with pytest.raises(PluginTypeException) as exc_info:
        compiler.do_compile()
    e = exc_info.value
    msg: str = e.format_trace()
    match = re.fullmatch(
        textwrap.dedent("""\
            Value dataclasses::NullableDC [0-9a-f]* for argument v of plugin dataclasses::takes_nullable_dc has incompatible type. Expected type: dataclasses::NullableDC \\(reported in dataclasses::takes_nullable_dc\\(x\\) \\([\\w/]*/main.cf:6:1\\)\\)
            caused by:
            Encountered unknown in field 'n'. Unknowns are not currently supported in dataclass instances in the Python domain. \\(reported in dataclasses::takes_nullable_dc\\(x\\) \\([\\w/]*/main.cf:6:1\\)\\)
            """).rstrip(),  # noqa: E501
        msg,
    )
    assert match is not None, msg

    # same with unknown in list
    snippetcompiler.setup_for_snippet(
        """\
import dataclasses
import tests

x = dataclasses::CollectionDC(l=[tests::unknown()], d={})

dataclasses::takes_collection_dc(x)
        """,
        ministd=True,
    )
    with pytest.raises(PluginTypeException) as exc_info:
        compiler.do_compile()
    e = exc_info.value
    msg: str = e.format_trace()
    match = re.fullmatch(
        textwrap.dedent("""\
            Value dataclasses::CollectionDC [0-9a-f]* for argument v of plugin dataclasses::takes_collection_dc has incompatible type. Expected type: dataclasses::CollectionDC \\(reported in dataclasses::takes_collection_dc\\(x\\) \\([\\w/]*/main.cf:6:1\\)\\)
            caused by:
            Encountered unknown in field 'l'. Unknowns are not currently supported in dataclass instances in the Python domain. \\(reported in dataclasses::takes_collection_dc\\(x\\) \\([\\w/]*/main.cf:6:1\\)\\)
            """).rstrip(),  # noqa: E501
        msg,
    )
    assert match is not None, msg

    # same with unknown in dict
    snippetcompiler.setup_for_snippet(
        """\
import dataclasses
import tests

x = dataclasses::CollectionDC(l=[], d={"hello": tests::unknown()})

dataclasses::takes_collection_dc(x)
        """,
        ministd=True,
    )
    with pytest.raises(PluginTypeException) as exc_info:
        compiler.do_compile()
    e = exc_info.value
    msg: str = e.format_trace()
    match = re.fullmatch(
        textwrap.dedent("""\
            Value dataclasses::CollectionDC [0-9a-f]* for argument v of plugin dataclasses::takes_collection_dc has incompatible type. Expected type: dataclasses::CollectionDC \\(reported in dataclasses::takes_collection_dc\\(x\\) \\([\\w/]*/main.cf:6:1\\)\\)
            caused by:
            Encountered unknown in field 'd'. Unknowns are not currently supported in dataclass instances in the Python domain. \\(reported in dataclasses::takes_collection_dc\\(x\\) \\([\\w/]*/main.cf:6:1\\)\\)
            """).rstrip(),  # noqa: E501
        msg,
    )
    assert match is not None, msg
