"""
Copyright 2025 Inmanta

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

import contextlib
import json
import logging
import os
import re
import typing
from logging import DEBUG
from typing import Optional, Iterator
from uuid import UUID

import pytest

from inmanta import env, references, resources, util
from inmanta.agent.handler import PythonLogger
from inmanta.ast import (
    ExternalException,
    PluginTypeException,
    RuntimeException,
    TypingException,
    UndeclaredReference,
    WrappingRuntimeException,
)
from inmanta.data.model import ReleasedResourceDetails, ReleasedResourceState
from inmanta.export import ResourceDict
from inmanta.references import Reference, ReferenceCycleException, reference
from inmanta.util.dict_path import Mapping, MutableMapping
from utils import ClientHelper, log_contains

if typing.TYPE_CHECKING:
    from conftest import SnippetCompilationTest

# The purpose of this module is to test references (compiler, exporter and executor). This module requires the test module
# defined in tests/data/modules_v2/refs


@contextlib.contextmanager
def raises_wrapped(exc_tp: type[RuntimeException], *, match: Optional[str] = None) -> Iterator[None]:
    """
    Context manager wrapper around pytest.raises. Expects a WrappingRuntimeException to be raised, and asserts that it wraps
    the provided exception type and that its message matches the provided pattern.
    """
    with pytest.raises(WrappingRuntimeException) as exc_info:
        yield
    assert isinstance(exc_info.value.__cause__, exc_tp)
    if match is not None:
        msg: str = exc_info.value.__cause__.format()
        assert re.search(match, msg) is not None, msg


def round_trip_resource(resource):
    serialized = resource.serialize()
    data = json.dumps(serialized, default=util.api_boundary_json_encoder)
    r = resources.Resource.deserialize(json.loads(data))
    r.resolve_all_references(PythonLogger(logging.getLogger("test.refs")))


def round_trip_ref(reference: Reference):
    serialized = reference.serialize()
    data = json.dumps(serialized, default=util.api_boundary_json_encoder)
    intermediate = references.ReferenceModel(**json.loads(data))
    references.reference.get_class(intermediate.type).deserialize(intermediate, None, logging.getLogger("test.refs"))


def test_references_in_model(
    snippetcompiler: "SnippetCompilationTest",
    modules_v2_dir: str,
    caplog,
) -> None:
    """Test the use of references in the model and if they produce the correct serialized form."""
    refs_module = os.path.join(modules_v2_dir, "refs")

    def assert_id(ref_list: list[references.ReferenceModel], ref_type: str, ref_id: str) -> references.ReferenceModel:
        """Assert that the reference of type `ref_type` has id `ref_id`"""
        refs = {str(ref.id): ref for ref in ref_list}
        assert ref_id in refs
        assert refs[ref_id].type == ref_type

        return refs[ref_id]

    snippetcompiler.setup_for_snippet(
        snippet="""
        import refs
        import refs::dc
        import std::testing

        subref = refs::create_string_reference(name="CWD")
        # Test equals method
        subref = refs::create_string_reference(name="CWD")

        test_ref = refs::create_all_refs_dataclass_reference(maybe_ref_value=subref)
        # Test equals method, does not work on dataclasses
        # test_ref = refs::create_all_refs_dataclass_reference(maybe_ref_value=refs::create_string_reference(name="CWD"))

        std::testing::NullResource(
            name="test",
            agentname="test",
            fail=refs::create_bool_reference(name=test_ref.maybe_ref_value),
        )
        """,
        install_v2_modules=[env.LocalPackagePath(path=refs_module)],
    )
    _, res_dict = snippetcompiler.do_export()
    assert len(res_dict) == 1
    serialized = res_dict.popitem()[1].serialize()

    # validate that our UUID is stable
    assert_id(serialized["references"], "refs::Bool", "0d3b10e5-3f6c-32ae-8662-02e5d46a59c7")
    # TODO: add other reference types?
    # TODO: why did the untouched ones fail??
    assert_id(serialized["references"], "refs::dc::AllRefsDataclassReference", "1102e0ce-2f03-31a5-ac3e-ef1a6609daaf")
    assert_id(serialized["references"], "core::AttributeReference", "8eafdfaf-9734-3d72-85dd-423df232c28e")
    assert_id(serialized["references"], "refs::String", "a8ed8c4f-204a-3f7e-a630-e21cb20e9209")

    data = json.dumps(serialized, default=util.api_boundary_json_encoder)

    resource = resources.Resource.deserialize(json.loads(data))
    resource.resolve_all_references(PythonLogger(logging.getLogger("test.refs")))
    assert not resource.fail and resource.fail is not None

    with caplog.at_level(DEBUG):
        resource.get_reference_value(UUID("1102e0ce-2f03-31a5-ac3e-ef1a6609daaf"), PythonLogger(logging.getLogger("test.refs")))

    log_contains(caplog, "test.refs", DEBUG, "Using cached value for reference AllRefsDataclassReference CWD")


async def test_deploy_end_to_end(
    snippetcompiler: "SnippetCompilationTest",
    modules_v2_dir: str,
    caplog,
    agent,
    client,
    clienthelper: ClientHelper,
    environment,
) -> None:
    refs_module = os.path.join(modules_v2_dir, "refs")
    snippetcompiler.setup_for_snippet(
        snippet="""
           import refs
           import refs::dc
           import std::testing

           test_ref = refs::create_bad_reference(name=refs::create_string_reference(name="CWD"))

           # bad ref will fail
           std::testing::NullResource(
               name="test",
               agentname="test",
               fail=refs::create_bool_reference(name=test_ref),
           )

            # good ref will work
            std::testing::NullResource(
               name="test2",
               agentname="test",
               fail=refs::create_bool_reference(name="testx"),
           )

           # Deeper mutator should also work
            refs::DeepResource(
               name="test3",
               agentname="test",
               value=refs::create_string_reference(name="testx"),
           )


           """,
        install_v2_modules=[env.LocalPackagePath(path=refs_module)],
    )

    await clienthelper.set_auto_deploy()
    version, resource = await snippetcompiler.do_export_and_deploy()

    # All resource must be dictpath compatible for the mutators to work!
    for resource in resource.values():
        assert isinstance(resource, Mapping)
        assert isinstance(resource, MutableMapping)

    await clienthelper.wait_for_released()
    await clienthelper.wait_for_deployed()
    result = await client.resource_details(environment, "std::testing::NullResource[test,name=test]")
    assert result.code == 200
    details = ReleasedResourceDetails(**result.result["data"])
    assert details.status == ReleasedResourceState.failed

    result = await client.resource_details(environment, "std::testing::NullResource[test,name=test2]")
    assert result.code == 200
    details = ReleasedResourceDetails(**result.result["data"])
    assert details.status == ReleasedResourceState.deployed

    result = await client.resource_details(environment, "refs::DeepResource[test,name=test3]")
    assert result.code == 200
    details = ReleasedResourceDetails(**result.result["data"])
    assert details.status == ReleasedResourceState.deployed
    result = await client.resource_logs(environment, "refs::DeepResource[test,name=test3]")
    assert result.code == 200
    assert [msg for msg in result.result["data"] if "Observed value: {'inner.something': 'testx'}" in msg["msg"]]


# TODO: critical review of this test's contents. Should inheritance-based tests be moved? Should dataclass-based tests be moved?
# TODO: name -> more like "references in plugins"
def test_undeclared_references(snippetcompiler: "SnippetCompilationTest", modules_v2_dir: str) -> None:
    # TODO: docstring
    refs_module = os.path.join(modules_v2_dir, "refs")

    # set up project
    snippetcompiler.setup_for_snippet(
        "import refs",
        install_v2_modules=[env.LocalPackagePath(path=refs_module)],
        autostd=True,
    )

    def run_snippet(snippet: str) -> None:
        """
        Wrapper around snippetcompiler.setup_for_snippet + runs compile and export.
        Passes appropriate options and prepends snippet with refs import.
        """
        # TODO: fix/discuss bug that causes dataclass error to be raised if associated model file is not loaded
        snippetcompiler.setup_for_snippet(f"import refs import refs::dc import refs::plugins\n{snippet}", install_project=False, autostd=True)
        snippetcompiler.do_export()

    # Primitives

    # Scenario: plugin argument annotated as `object`
    run_snippet(snippet="refs::plugins::takes_obj('hello')")
    with pytest.raises(PluginTypeException, match="is a reference"):
        run_snippet(snippet="refs::plugins::takes_obj(refs::create_string_reference('name'))")
    ## accepts list with a reference in it and even allows access -> infeasible to check inside a black box
    ## -> this is not a strong requirement. The assertion is here simply to ensure the behavior remains stable
    run_snippet(snippet="refs::plugins::takes_obj(['hello', refs::create_string_reference('hello')])")
    run_snippet(snippet="refs::plugins::iterates_obj(['hello', refs::create_string_reference('hello')])")
    # Scenario: plugin argument annotated as `object | Reference[object]`
    run_snippet(snippet="refs::plugins::takes_obj_ref('hello')")
    run_snippet(snippet="refs::plugins::takes_obj_ref(refs::create_string_reference('name'))")
    # Scenario: plugin argument annotated as `Reference[object]`
    with pytest.raises(PluginTypeException, match=re.escape("Expected type: Reference[any]")):
        run_snippet(snippet="refs::plugins::takes_obj_ref_only('hello')")
    run_snippet(snippet="refs::plugins::takes_obj_ref_only(refs::create_string_reference('name'))")
    # Scenario: plugin argument annotated as `str`
    run_snippet(snippet="refs::plugins::takes_str('hello')")
    with pytest.raises(PluginTypeException, match="is a reference"):
        run_snippet(snippet="refs::plugins::takes_str(refs::create_string_reference('name'))")
    # Scenario: plugin argument annotated as `str | Reference[str]`
    run_snippet(snippet="refs::plugins::takes_str_ref('hello')")
    run_snippet(snippet="refs::plugins::takes_str_ref(refs::create_string_reference('name'))")
    with pytest.raises(PluginTypeException, match=re.escape("Expected type: Reference[string]")):
        # takes a str ref, not a bool ref
        run_snippet(snippet="refs::plugins::takes_str_ref(refs::create_bool_reference('name'))")
    # Scenario: plugin argument annotated as `Sequence[object]`
    run_snippet(snippet="refs::plugins::iterates_obj_list(['h', 'e'])")
    run_snippet(snippet="refs::plugins::iterates_obj_list(['h', 1])")
    with pytest.raises(PluginTypeException, match="contains a reference"):
        run_snippet(snippet="refs::plugins::iterates_obj_list(['h', refs::create_string_reference('name')])")
    # Scenario: plugin argument annotated as `Sequence[str]`
    run_snippet(snippet="refs::plugins::iterates_str_list(['h', 'e'])")
    with pytest.raises(PluginTypeException, match=re.escape("Expected type: string[]")):
        run_snippet(snippet="refs::plugins::iterates_str_list(['h', 1])")
    with pytest.raises(PluginTypeException, match="contains a reference"):
        run_snippet(snippet="refs::plugins::iterates_str_list(['h', refs::create_string_reference('name')])")
    # Scenario: plugin argument annotated as `Sequence[str | Reference[str]]`
    run_snippet(snippet="refs::plugins::iterates_str_ref_list(['h', 'e'])")
    with pytest.raises(PluginTypeException, match=re.escape("Expected type: (Reference[string] | string)[]")):
        run_snippet(snippet="refs::plugins::iterates_str_ref_list(['h', 1])")
    run_snippet(snippet="refs::plugins::iterates_str_ref_list(['h', refs::create_string_reference('name')])")
    # Scenario: plugin argument annotated as `Mapping[str, object]`
    run_snippet(snippet="refs::plugins::iterates_object_dict({'h': 'h', 'e': 'e'})")
    with pytest.raises(PluginTypeException, match="contains a reference"):
        run_snippet(snippet="refs::plugins::iterates_object_dict({'h': 'h', 'e': refs::create_string_reference('name')})")
    # Scenario: plugin argument annotated as `Mapping[str, object | Reference[object]]`
    run_snippet(snippet="refs::plugins::iterates_object_ref_dict({'h': 'h', 'e': 'e'})")
    run_snippet(snippet="refs::plugins::iterates_object_ref_dict({'h': 'h', 'e': refs::create_string_reference('name')})")

    # Entities

    # Scenario: plugin annotated as `Entity`
    ## Entity annotation
    ### dataclasses allowed
    run_snippet("refs::plugins::takes_entity(refs::dc::AllRefsDataclass(maybe_ref_value=refs::create_string_reference('hello')))")
    run_snippet("refs::plugins::takes_entity(refs::dc::NoRefsDataclass())")
    ### references allowed, as long as no reference attribute is accessed
    run_snippet("refs::plugins::takes_entity(refs::dc::create_all_refs_dataclass_reference('hello'))")
    run_snippet("refs::plugins::takes_entity(refs::dc::create_no_refs_dataclass_reference())")

    # Scenario: plugin annotated as `Entity` accesses reference attribute during plugin execution
    ## no reference
    run_snippet("refs::plugins::read_entity_value(refs::dc::AllRefsDataclass(maybe_ref_value='Hello World!'))")
    run_snippet("refs::plugins::read_entity_list_value(refs::ListContainer(value=['Hello', 'World!']))")
    run_snippet("refs::plugins::read_entity_list_head(refs::ListContainer(value=['Hello', refs::create_string_reference('hello')]))")
    run_snippet("refs::plugins::read_entity_dict_value(refs::DictContainer(value={'Hello': 'World!', 'mykey': '42'}))")
    run_snippet(
        "refs::plugins::read_entity_dict_mykey(refs::DictContainer(value={'Hello': refs::create_string_reference('hello'), 'mykey': '42'}))"
    )
    ## reference
    ### in attribute
    with raises_wrapped(UndeclaredReference, match="Encountered reference value in instance attribute"):
        run_snippet("refs::plugins::read_entity_value(refs::dc::AllRefsDataclass(maybe_ref_value=refs::create_string_reference('hello')))")
    ### inside list attribute
    with raises_wrapped(UndeclaredReference, match="Undeclared reference found"):
        run_snippet("refs::plugins::read_entity_list_value(refs::ListContainer(value=['Hello', refs::create_string_reference('hello')]))")
    with raises_wrapped(UndeclaredReference, match="Undeclared reference found"):
        run_snippet("refs::plugins::read_entity_list_head(refs::ListContainer(value=[refs::create_string_reference('hello'), 'Hello']))")
    ### inside dict attribute
    with raises_wrapped(UndeclaredReference, match="Undeclared reference found"):
        run_snippet(
            """\
            refs::plugins::read_entity_dict_value(
                refs::DictContainer(value={'Hello': 'World!', 'mykey': refs::create_string_reference('hello')})
            )
            """
        )
    with raises_wrapped(UndeclaredReference, match="Undeclared reference found"):
        run_snippet(
            """\
            refs::plugins::read_entity_dict_mykey(
                refs::DictContainer(value={'Hello': 'World!', 'mykey': refs::create_string_reference('hello')})
            )
            """
        )
    ## reference, plugin explicitly allows it
    run_snippet("refs::plugins::read_entity_ref_value(refs::dc::AllRefsDataclass(maybe_ref_value=refs::create_string_reference('hello')))")
    ## reference access for list of entities
    ### no reference
    run_snippet(
        """\
        refs::plugins::read_list_entity_value(
            [
                refs::dc::AllRefsDataclass(maybe_ref_value='Hello'),
                refs::dc::AllRefsDataclass(maybe_ref_value='World!'),
            ]
        )
        """
    )
    ### reference
    with raises_wrapped(UndeclaredReference, match="Encountered reference value in instance attribute"):
        run_snippet(
            """\
            refs::plugins::read_list_entity_value(
                [
                    refs::dc::AllRefsDataclass(maybe_ref_value='Hello'),
                    refs::dc::AllRefsDataclass(maybe_ref_value=refs::create_string_reference('hello')),
                ]
            )
            """
        )
    ### reference, plugin explicitly allows it
    run_snippet(
        """\
        refs::plugins::read_list_entity_ref_value(
            [
                refs::dc::AllRefsDataclass(maybe_ref_value='Hello'),
                refs::dc::AllRefsDataclass(maybe_ref_value=refs::create_string_reference('hello')),
            ]
        )
        """
    )

    # Scenario: plugin annotated as <dataclass> gets Reference[<dataclass>]
    ## dataclass type that does not support reference attrs
    ### plain dataclass
    run_snippet("refs::plugins::takes_no_refs_dataclass(refs::dc::NoRefsDataclass())")
    run_snippet("refs::plugins::takes_mixed_refs_dataclass(refs::dc::MixedRefsDataclass(maybe_ref_value=refs::create_string_reference('hello')))")
    ### basic inheritance
    run_snippet("refs::plugins::takes_no_refs_dataclass(refs::dc::MixedRefsDataclass(maybe_ref_value=refs::create_string_reference('hello')))")
    ### basic inheritance the wrong direction
    with pytest.raises(PluginTypeException, match=re.escape("Expected type: refs::dc::MixedRefsDataclass")):
        run_snippet("refs::plugins::takes_mixed_refs_dataclass(refs::dc::NoRefsDataclass())")
    ### references not allowed
    #### references to dataclass
    with pytest.raises(PluginTypeException, match="contains a reference"):
        run_snippet("refs::plugins::takes_no_refs_dataclass(refs::dc::create_no_refs_dataclass_reference())")
    with pytest.raises(PluginTypeException, match="contains a reference"):
        run_snippet("refs::plugins::takes_mixed_refs_dataclass(refs::dc::create_mixed_refs_dataclass_reference('hello'))")
    #### dataclass containing undeclared reference
    with pytest.raises(PluginTypeException, match="contains a reference"):
        run_snippet("refs::plugins::takes_no_refs_dataclass(refs::dc::NoRefsDataclass(non_ref_value=refs::create_string_reference('hello')))")
    ## dataclass type that supports reference attrs -> references are coerced
    ### references are coerced to dataclass of references
    run_snippet("refs::plugins::takes_all_refs_dataclass(refs::dc::create_all_refs_dataclass_reference('hello'))")
    ### references are coerced to dataclass of references, with inheritance
    run_snippet("refs::plugins::takes_dataclass(refs::dc::create_all_refs_dataclass_reference('hello'))")
    with pytest.raises(PluginTypeException, match="contains a reference"):
        run_snippet("refs::plugins::takes_dataclass(refs::dc::create_no_refs_dataclass_reference())")

    # Scenario: plugin annotated as Reference[<dataclass>]
    ## accepts a reference
    run_snippet("refs::plugins::takes_no_refs_dataclass_ref(refs::dc::create_no_refs_dataclass_reference())")
    ## rejects a dataclass
    with pytest.raises(PluginTypeException, match=re.escape("Expected type: Reference[refs::dc::NoRefsDataclass]")):
        run_snippet("refs::plugins::takes_no_refs_dataclass_ref(refs::dc::NoRefsDataclass())")

    # Scenario: plugin annotated as <dataclass> | Reference[<dataclass>]
    ## accepts either
    run_snippet("refs::plugins::takes_no_refs_dataclass_or_ref(refs::dc::create_no_refs_dataclass_reference())")
    run_snippet("refs::plugins::takes_no_refs_dataclass_or_ref(refs::dc::NoRefsDataclass())")
    run_snippet("refs::plugins::takes_mixed_refs_dataclass_or_ref(refs::dc::create_mixed_refs_dataclass_reference('hello'))")
    run_snippet("refs::plugins::takes_mixed_refs_dataclass_or_ref(refs::dc::MixedRefsDataclass(maybe_ref_value='hello'))")
    ## rejects other dataclasses / references to other dataclasses, except for inheritance
    run_snippet("refs::plugins::takes_no_refs_dataclass_or_ref(refs::dc::MixedRefsDataclass(maybe_ref_value='hello'))")
    run_snippet("refs::plugins::takes_no_refs_dataclass_or_ref(refs::dc::create_mixed_refs_dataclass_reference('hello'))")
    with pytest.raises(
        PluginTypeException, match=re.escape("Expected type: Reference[refs::dc::MixedRefsDataclass] | refs::dc::MixedRefsDataclass")
    ):
        run_snippet("refs::plugins::takes_mixed_refs_dataclass_or_ref(refs::dc::AllRefsDataclass(maybe_ref_value='hello'))")
    with pytest.raises(
        PluginTypeException, match=re.escape("Expected type: Reference[refs::dc::MixedRefsDataclass] | refs::dc::MixedRefsDataclass")
    ):
        run_snippet("refs::plugins::takes_mixed_refs_dataclass_or_ref(refs::dc::create_all_refs_dataclass_reference('hello'))")

    # Scenario: inheritance on return type
    ## declare generic, return specific
    ### takes_no_refs_dataclass only accepts specific no_refs_dataclass.
    ### We use it as an assertion that the other plugin returns the specific type in the DSL.
    run_snippet("refs::plugins::takes_no_refs_dataclass(refs::plugins::inheritance_return_specific())")
    ## declare generic reference, return specific reference
    run_snippet("refs::plugins::takes_no_refs_dataclass_ref(refs::plugins::inheritance_return_specific_ref())")

    # Scenario: plugin returns list attribute without reading elements, declares list[str] return
    ## allowed if attribute has no references
    run_snippet("refs::plugins::returns_entity_list(refs::ListContainer(value=['Hello', 'World!']))")
    ## error on return validation if attribute has references
    with pytest.raises(PluginTypeException, match="Return value .* has incompatible type\..*Expected type: string\[\]"):
        run_snippet("refs::plugins::returns_entity_list(refs::ListContainer(value=['Hello', refs::create_string_reference('hello')]))")
    ## allowed if plugin annotates reference in return type
    run_snippet(
        "refs::plugins::returns_entity_ref_list(refs::ListContainer(value=['Hello', refs::create_string_reference('hello')]))"
    )

    # TODO: allow_references() test on list access and iteration
    # TODO: verify that allow_references() only allows it on that level, not nested


def test_reference_cycle(snippetcompiler: "SnippetCompilationTest", modules_v2_dir: str) -> None:
    """Test the correct detection of reference cycles."""
    refs_module = os.path.join(modules_v2_dir, "refs")

    snippetcompiler.setup_for_snippet(
        snippet="""
        import refs
        import refs::dc
        import std::testing

        std::testing::NullResource(
            name="test",
            agentname="test",
            fail=refs::create_bool_reference_cycle(name="CWD"),
        )
        """,
        install_v2_modules=[env.LocalPackagePath(path=refs_module)],
    )

    with pytest.raises(
        ExternalException, match="Failed to get attribute 'fail' for export on 'std::testing::NullResource'"
    ) as e:
        snippetcompiler.do_export()
    assert isinstance(e.value.__cause__, ReferenceCycleException)
    assert "Reference cycle detected: StringReference -> StringReference" in str(e.value.__cause__)


def test_references_in_expression(snippetcompiler: "SnippetCompilationTest", modules_v2_dir: str) -> None:
    """Test that references are rejected in expressions"""
    refs_module = os.path.join(modules_v2_dir, "refs")

    snippetcompiler.setup_for_snippet(
        snippet="""
        import refs
        if refs::create_bool_reference_cycle(name="CWD"):
        end
        """,
        install_v2_modules=[env.LocalPackagePath(path=refs_module)],
        autostd=True,
    )

    with pytest.raises(
        RuntimeException,
        match=r"Invalid value `BoolReference StringReference`: "
        "the condition for an if statement can only be a boolean expression",
    ):
        snippetcompiler.do_export()


def test_references_in_resource_id(snippetcompiler: "SnippetCompilationTest", modules_v2_dir: str) -> None:
    """Test that references are rejected in the resource id value"""
    refs_module = os.path.join(modules_v2_dir, "refs")

    snippetcompiler.setup_for_snippet(
        snippet="""
        import refs
        import refs::dc
        value = refs::create_string_reference(name="CWD")

        refs::NullResource(name=value,agentname=value)
        """,
        install_v2_modules=[env.LocalPackagePath(path=refs_module)],
        autostd=True,
    )

    # TODO: when do we expect this error vs UndeclaredReference? The latter seems useful for custom handler implementations
    #       =>
    #       1 for non-id values, UndeclaredReference
    #       2 for non-id values, user can use with_references()
    #       3 for id values, provide the more to-the-point error message. Definitely relevant for 2 with id value.
    #           But does 1 or 3 get preference?
    with pytest.raises(
        RuntimeException,
        match=r"Failed to get attribute 'name' for export on 'refs::NullResource'",
    ):
        snippetcompiler.do_export()


def test_references_in_wrong_resource(snippetcompiler: "SnippetCompilationTest", modules_v2_dir: str) -> None:
    """
    Test that we can't refer to other resources directly

    We only catch this on the remote side, as it is very hard to get into this situation.

    We use specially crafted resources, where the one to be constructed last creates a reference to the first one.
    """
    refs_module = os.path.join(modules_v2_dir, "refs")

    snippetcompiler.setup_for_snippet(
        snippet="""
        import refs
        value = refs::create_string_reference(name="CWD")

        refs::NullResource(name="test",agentname="test", fail=true)
        refs::NullResource(name="test2",agentname="test", fail=true)
        """,
        install_v2_modules=[env.LocalPackagePath(path=refs_module)],
        autostd=True,
    )

    _, res_dict = snippetcompiler.do_export()

    with pytest.raises(
        Exception,
        match=r"This resource refers to another resource refs::NullResource\[test,name=test2?\] instead of "
        r"itself refs::NullResource\[test,name=test2?\], this is not supported",
    ):
        for resource in res_dict.values():
            round_trip_resource(resource)


def test_references_in_index(snippetcompiler: "SnippetCompilationTest", modules_v2_dir: str) -> None:
    """Test that references are rejected in indexes"""
    refs_module = os.path.join(modules_v2_dir, "refs")

    snippetcompiler.setup_for_snippet(
        snippet="""
        import refs

        mystr = refs::create_string_reference("test")

        entity Test:
           string value
        end

        implement Test using std::none

        index Test(value)

        Test(value=mystr)
        """,
        install_v2_modules=[env.LocalPackagePath(path=refs_module)],
        autostd=True,
    )
    with pytest.raises(
        TypingException,
        match="Invalid value `StringReference` in index for attribute value: references can not be used in indexes",
    ):
        snippetcompiler.do_export()

    snippetcompiler.setup_for_snippet(
        snippet="""
          import refs

          mystr = refs::create_string_reference("test")

          entity Test:
             string value
          end

          implement Test using std::none

          index Test(value)

          a = Test[value=mystr]
          """,
        install_v2_modules=[env.LocalPackagePath(path=refs_module)],
        autostd=True,
    )
    with pytest.raises(
        TypingException,
        match="Invalid value `StringReference` in index for attribute value: references can not be used in indexes",
    ):
        snippetcompiler.do_export()


def test_ref_docs(snippetcompiler, monkeypatch, capsys):
    base_path = os.path.join(os.path.dirname(__file__), "..", "docs", "model_developers", "examples")

    def read_file(name: str) -> str:
        with open(os.path.join(base_path, name), "r") as fh:
            return fh.read()

    def run_for_example(name: str) -> ResourceDict:
        snippetcompiler.create_module(
            f"references{name}", read_file(f"references_{name}.cf"), read_file(f"references_{name}.py")
        )
        snippetcompiler.setup_for_snippet(f"import references{name}", autostd=True)
        _, resources = snippetcompiler.do_export()
        return resources

    resources = run_for_example(1)
    assert len(resources) == 1
    resource = next(iter(resources.values()))
    assert len(resource["mutators"]) != 0

    monkeypatch.setenv("test", "TEST VALUE")
    run_for_example(2)

    assert "TEST VALUE" in capsys.readouterr()[0]


def test_ref_serialization():

    @reference("test::Test")
    class TestReference(Reference[str]):

        def __init__(self, keys, none_attr=None):
            super().__init__()
            self.keys = keys
            self.none_attr = None

    round_trip_ref(TestReference({"a": "A"}))

    # Only clean json is allowed
    tr = TestReference({"a": "A"})
    baddy = TestReference({"a": tr})
    with pytest.raises(ValueError):
        baddy.serialize()
