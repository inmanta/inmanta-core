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
from typing import Iterator, Optional
from uuid import UUID

import pytest

from inmanta import compiler, env, references, resources, util
from inmanta.agent.handler import PythonLogger
from inmanta.ast import (
    ExternalException,
    PluginTypeException,
    RuntimeException,
    TypingException,
    UnexpectedReference,
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
def raises_wrapped(
    exc_tp: type[Exception],
    *,
    match: Optional[str] = None,
    outer_exception: type[WrappingRuntimeException | ExternalException] = WrappingRuntimeException,
) -> Iterator[None]:
    """
    Context manager wrapper around pytest.raises. Expects a WrappingRuntimeException to be raised, and asserts that it wraps
    the provided exception type and that its message matches the provided pattern.
    """
    with pytest.raises(outer_exception) as exc_info:
        yield
    assert isinstance(exc_info.value.__cause__, exc_tp)
    if match is not None:
        msg: str = str(exc_info.value.__cause__)
        assert re.search(match, msg) is not None, msg


def round_trip_resource(resource):
    serialized = resource.serialize()
    data = json.dumps(serialized, default=util.api_boundary_json_encoder)
    r = resources.Resource.deserialize(json.loads(data))

    # Test cloning includes caches
    clone = r.clone()
    assert clone._references_model == r._references_model
    assert clone._references == r._references
    assert clone._resolved == r._resolved
    r.resolve_all_references(PythonLogger(logging.getLogger("test.refs")))
    # old clone shares cache, but not resolved state, as it has not been mutated
    assert clone._references_model == r._references_model
    assert clone._references == r._references
    assert clone._resolved != r._resolved
    clone = r.clone()
    assert clone._references_model == r._references_model
    assert clone._references == r._references
    assert clone._resolved == r._resolved
    return r


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

        test_ref = refs::dc::create_all_refs_dataclass_reference(maybe_ref_value=subref)
        # Test equals method, does not work on dataclasses
        # test_ref = refs::dc::create_all_refs_dataclass_reference(maybe_ref_value=refs::create_string_reference(name="CWD"))

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
    assert_id(serialized["references"], "refs::dc::AllRefsDataclassReference", "1102e0ce-2f03-31a5-ac3e-ef1a6609daaf")
    assert_id(serialized["references"], "core::AttributeReference", "8eafdfaf-9734-3d72-85dd-423df232c28e")
    assert_id(serialized["references"], "refs::String", "a8ed8c4f-204a-3f7e-a630-e21cb20e9209")

    data = json.dumps(serialized, default=util.api_boundary_json_encoder)

    resource = resources.Resource.deserialize(json.loads(data))
    resource.resolve_all_references(PythonLogger(logging.getLogger("test.refs")))
    assert not resource.fail and resource.fail is not None

    with caplog.at_level(DEBUG):
        resource.get_reference_value(UUID("1102e0ce-2f03-31a5-ac3e-ef1a6609daaf"), PythonLogger(logging.getLogger("test.refs")))

    log_contains(caplog, "test.refs", DEBUG, "Using cached value for reference AllRefsDataclassReference('CWD')")


def test_undeclared_reference_in_map(
    snippetcompiler: "SnippetCompilationTest",
    modules_v2_dir: str,
    caplog,
) -> None:
    """
    Verify that a custom field map method transparently allows references.
    """
    refs_module = os.path.join(modules_v2_dir, "refs")

    snippetcompiler.setup_for_snippet(
        snippet="""
        import std::testing
        import refs

        refs::DeepResourceNoReferences(
           name="test",
           agentname="test",
           value=refs::create_string_reference(name="test"),
       )
        """,
        install_v2_modules=[env.LocalPackagePath(path=refs_module)],
    )
    _, resources = snippetcompiler.do_export()

    # Find the resource
    rbykey = {str(k): v for k, v in resources.items()}
    r = rbykey["refs::DeepResourceNoReferences[test,name=test]"]

    # ensure we have the nastiest path possible.
    assert r.mutators[0].args[2].value == "value.'inner.something'[0]"

    # make it resolve!
    r = round_trip_resource(r)

    # ensure it did resolve
    assert r.value["inner.something"][0] == "test"


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

            # and a dict of references
            refs::DictResource(
                name="test4",
                agentname="test",
                value={"Hello": refs::create_string_reference(name="World!")},
            )

            # and a dict ref
            refs::DeepResource(
                name="test4",
                agentname="test",
                value=refs::create_DictRef(value = refs::create_string_reference(name="TESTX")),
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

    result = await client.resource_details(environment, "refs::DictResource[test,name=test4]")
    assert result.code == 200
    details = ReleasedResourceDetails(**result.result["data"])
    assert details.status == ReleasedResourceState.deployed
    result = await client.resource_logs(environment, "refs::DictResource[test,name=test4]")
    assert result.code == 200
    assert [msg for msg in result.result["data"] if "Observed value: {'Hello': 'World!'}" in msg["msg"]]

    result = await client.resource_details(environment, "refs::DeepResource[test,name=test4]")
    assert result.code == 200
    details = ReleasedResourceDetails(**result.result["data"])
    assert details.status == ReleasedResourceState.deployed
    result = await client.resource_logs(environment, "refs::DeepResource[test,name=test4]")
    assert result.code == 200
    assert [msg for msg in result.result["data"] if "Observed value: {'inner.something': ['TESTX']}" in msg["msg"]]


def test_decoding_legacy_resources(snippetcompiler, modules_v2_dir):
    """The encoding for paths in mutable json changed after iso8.2.0 this test backward compat"""

    refs_module = os.path.join(modules_v2_dir, "refs")

    # set up project
    snippetcompiler.setup_for_snippet(
        "import refs",
        install_v2_modules=[env.LocalPackagePath(path=refs_module)],
        autostd=True,
    )

    compiler.do_compile()

    old_resource = r"""
        {
        "references": [
            {
                "type": "refs::DictMade",
                "args": [
                    {
                        "type": "mjson",
                        "name": "name",
                        "value": {
                            "name": null
                        },
                        "references": {
                            ".name": {
                                "type": "reference",
                                "name": ".name",
                                "id": "187fdec1-d0e8-3652-b672-e098be97a2d1"
                            }
                        }
                    }
                ],
                "id": "83a1981c-59d1-36d9-aa07-3351b5430732"
            },
            {
                "type": "refs::String",
                "args": [
                    {
                        "type": "literal",
                        "name": "name",
                        "value": "TESTX"
                    }
                ],
                "id": "187fdec1-d0e8-3652-b672-e098be97a2d1"
            }
        ],
        "purged": false,
        "value": {
            "inner": null
        },
        "name": "test4",
        "agentname": "test",
        "mutators": [
            {
                "type": "core::Replace",
                "args": [
                    {
                        "type": "resource",
                        "name": "resource",
                        "id": "refs::DeepResource[test,name=test4]"
                    },
                    {
                        "type": "reference",
                        "name": "value",
                        "id": "83a1981c-59d1-36d9-aa07-3351b5430732"
                    },
                    {
                        "type": "literal",
                        "name": "destination",
                        "value": "value.inner"
                    }
                ]
            }
        ],
        "send_event": false,
        "managed": true,
        "purge_on_delete": false,
        "receive_events": true,
        "requires": [],
        "version": 1,
        "id": "refs::DeepResource[test,name=test4],v=1"
    }
        """

    r = resources.Resource.deserialize(json.loads(old_resource))
    # Test cloning includes caches
    clone = r.clone()
    assert clone._references_model == r._references_model
    assert clone._references == r._references
    assert clone._resolved == r._resolved
    r.resolve_all_references(PythonLogger(logging.getLogger("test.refs")))
    # old clone shares cache, but not resolved state, as it has not been mutated
    assert clone._references_model == r._references_model
    assert clone._references == r._references
    assert clone._resolved != r._resolved
    clone = r.clone()
    assert clone._references_model == r._references_model
    assert clone._references == r._references
    assert clone._resolved == r._resolved


def test_references_in_plugins(snippetcompiler: "SnippetCompilationTest", modules_v2_dir: str) -> None:
    """
    Verify the validation of references in plugins, both on the boundary, and on access through a proxy.
    """
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
        snippetcompiler.setup_for_snippet(
            f"import refs import refs::dc import refs::plugins\n{snippet}", install_project=False, autostd=True
        )
        snippetcompiler.do_export()

    # Primitives

    # Scenario: plugin argument annotated as `object`
    run_snippet(snippet="refs::plugins::takes_obj('hello')")
    with pytest.raises(PluginTypeException, match="is a reference"):
        run_snippet(snippet="refs::plugins::takes_obj(refs::create_string_reference('name'))")
    # same with kwarg
    run_snippet(snippet="refs::plugins::takes_obj(v='hello')")
    with pytest.raises(PluginTypeException, match="is a reference"):
        run_snippet(snippet="refs::plugins::takes_obj(v=refs::create_string_reference('name'))")
    ## accepts list with a reference in it and even allows access -> infeasible to check inside a black box
    ## -> this is not a strong requirement. The assertion is here simply to ensure the behavior remains stable
    run_snippet(snippet="refs::plugins::takes_obj(['hello', refs::create_string_reference('hello')])")
    run_snippet(snippet="refs::plugins::iterates_obj(['hello', refs::create_string_reference('hello')])")
    # Scenario: plugin argument annotated as `object | Reference`
    run_snippet(snippet="refs::plugins::takes_obj_ref('hello')")
    run_snippet(snippet="refs::plugins::takes_obj_ref(refs::create_string_reference('name'))")
    run_snippet(snippet="refs::plugins::takes_obj_ref(v='hello')")
    run_snippet(snippet="refs::plugins::takes_obj_ref(v=refs::create_string_reference('name'))")
    # Scenario: plugin argument annotated as `Reference`
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
    with pytest.raises(PluginTypeException, match=re.escape("Expected type: Reference[string] | string")):
        # takes a str ref, not a bool ref
        run_snippet(snippet="refs::plugins::takes_str_ref(refs::create_bool_reference('name'))")
    # Scenario: plugin argument annotated with complex union including Reference[str | None]
    run_snippet(snippet="refs::plugins::takes_complex_union_or_ref('Hello World!')")
    run_snippet(snippet="refs::plugins::takes_complex_union_or_ref(42)")
    run_snippet(snippet="refs::plugins::takes_complex_union_or_ref(null)")
    run_snippet(snippet="refs::plugins::takes_complex_union_or_ref(refs::create_string_reference('Hello'))")
    with pytest.raises(PluginTypeException, match=re.escape("Expected type: Union[int,string,Reference[string?]]?")):
        run_snippet(snippet="refs::plugins::takes_complex_union_or_ref([1])")
    with pytest.raises(PluginTypeException, match=re.escape("Expected type: Union[int,string,Reference[string?]]?")):
        # takes a string reference, not a bool reference
        run_snippet(snippet="refs::plugins::takes_complex_union_or_ref(refs::create_bool_reference('Hello'))")
    # Scenario: plugin argument annotated with Reference[bool] | Reference[str]
    run_snippet(snippet="refs::plugins::takes_union_of_refs(refs::create_string_reference('Hello'))")
    run_snippet(snippet="refs::plugins::takes_union_of_refs(refs::create_bool_reference('Hello'))")
    with pytest.raises(PluginTypeException, match=re.escape("Expected type: Union[Reference[bool],Reference[string]]")):
        run_snippet(snippet="refs::plugins::takes_union_of_refs(refs::create_int_reference('Hello'))")
    with pytest.raises(PluginTypeException, match=re.escape("Expected type: Union[Reference[bool],Reference[string]]")):
        run_snippet(snippet="refs::plugins::takes_union_of_refs('Hello World!')")
    with pytest.raises(PluginTypeException, match=re.escape("Expected type: Union[Reference[bool],Reference[string]]")):
        run_snippet(snippet="refs::plugins::takes_union_of_refs(true)")
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
    # Scenario: plugin argument annotated as `Mapping[str, object | Reference]`
    run_snippet(snippet="refs::plugins::iterates_object_ref_dict({'h': 'h', 'e': 'e'})")
    run_snippet(snippet="refs::plugins::iterates_object_ref_dict({'h': 'h', 'e': refs::create_string_reference('name')})")

    # Entities

    # Scenario: plugin annotated as `Entity`
    ## Entity annotation
    ### dataclasses allowed
    run_snippet(
        "refs::plugins::takes_entity(refs::dc::AllRefsDataclass(maybe_ref_value=refs::create_string_reference('hello')))"
    )
    run_snippet("refs::plugins::takes_entity(refs::dc::NoRefsDataclass())")
    ### references allowed, as long as no reference attribute is accessed
    run_snippet("refs::plugins::takes_entity(refs::dc::create_all_refs_dataclass_reference('hello'))")
    run_snippet("refs::plugins::takes_entity(refs::dc::create_no_refs_dataclass_reference())")

    # Scenario: plugin annotated as `Entity` accesses reference attribute during plugin execution
    ## no reference
    run_snippet("refs::plugins::read_entity_value(refs::dc::AllRefsDataclass(maybe_ref_value='Hello World!'))")
    run_snippet("refs::plugins::read_entity_list_value(refs::ListContainer(value=['Hello', 'World!']))")
    run_snippet(
        "refs::plugins::read_entity_list_head(refs::ListContainer(value=['Hello', refs::create_string_reference('hello')]))"
    )
    run_snippet("refs::plugins::read_entity_dict_value(refs::DictContainer(value={'Hello': 'World!', 'mykey': '42'}))")
    run_snippet("""
        refs::plugins::read_entity_dict_mykey(
            refs::DictContainer(value={'Hello': refs::create_string_reference('hello'), 'mykey': '42'})
        )
        """)
    ## reference
    ### in attribute
    with raises_wrapped(
        UnexpectedReference, match="Encountered unexpected reference .* Encountered at instance.maybe_ref_value"
    ):
        run_snippet("""\
            refs::plugins::read_entity_value(
                refs::dc::AllRefsDataclass(maybe_ref_value=refs::create_string_reference('hello'))
            )
            """)
    ### inside list attribute
    with raises_wrapped(UnexpectedReference, match=r"Encountered unexpected reference .* Encountered at instance\.value\[1\]"):
        run_snippet("""\
            refs::plugins::read_entity_list_value(refs::ListContainer(value=['Hello', refs::create_string_reference('hello')]))
            """)
    with raises_wrapped(UnexpectedReference, match=r"Encountered unexpected reference .* Encountered at instance\.value\[0\]"):
        run_snippet(
            "refs::plugins::read_entity_list_head(refs::ListContainer(value=[refs::create_string_reference('hello'), 'Hello']))"
        )
    ## inside list attribute but allowed
    run_snippet("""\
        refs::plugins::read_entity_list_value_or_ref(
            refs::ListContainer(value=['Hello', refs::create_string_reference('hello')])
        )
        """)
    ## inside list attribute: allowed on instance level but not on nested list level
    with raises_wrapped(UnexpectedReference, match=r"Encountered unexpected reference .* Encountered at instance\.value\[1\]"):
        run_snippet("""\
            refs::plugins::read_entity_list_value_allow_references_single_level(
                refs::ListContainer(value=['Hello', refs::create_string_reference('hello')])
            )
            """)
    ### inside dict attribute
    with raises_wrapped(
        UnexpectedReference, match=r"Encountered unexpected reference .* Encountered at instance\.value\['mykey'\]"
    ):
        run_snippet("""\
            refs::plugins::read_entity_dict_value(
                refs::DictContainer(value={'Hello': 'World!', 'mykey': refs::create_string_reference('hello')})
            )
            """)
    with raises_wrapped(
        UnexpectedReference, match=r"Encountered unexpected reference .* Encountered at instance\.value\['mykey'\]"
    ):
        run_snippet("""\
            refs::plugins::read_entity_dict_mykey(
                refs::DictContainer(value={'Hello': 'World!', 'mykey': refs::create_string_reference('hello')})
            )
            """)
    ## inside dict attribute but allowed
    run_snippet("""\
        refs::plugins::read_entity_dict_value_or_ref(
            refs::DictContainer(value={'Hello': 'World!', 'mykey': refs::create_string_reference('hello')})
        )
        """)
    ## reference, plugin explicitly allows it
    run_snippet("""\
        refs::plugins::read_entity_ref_value(
            refs::dc::AllRefsDataclass(maybe_ref_value=refs::create_string_reference('hello'))
        )
        """)
    ## reference access for list of entities
    ### no reference
    run_snippet("""\
        refs::plugins::read_list_entity_value(
            [
                refs::dc::AllRefsDataclass(maybe_ref_value='Hello'),
                refs::dc::AllRefsDataclass(maybe_ref_value='World!'),
            ]
        )
        """)
    ### reference
    with raises_wrapped(
        UnexpectedReference, match=r"Encountered unexpected reference .* Encountered at instances\[1\]\.maybe_ref_value"
    ):
        run_snippet("""\
            refs::plugins::read_list_entity_value(
                [
                    refs::dc::AllRefsDataclass(maybe_ref_value='Hello'),
                    refs::dc::AllRefsDataclass(maybe_ref_value=refs::create_string_reference('hello')),
                ]
            )
            """)
    ### reference, plugin explicitly allows it
    run_snippet("""\
        refs::plugins::read_list_entity_ref_value(
            [
                refs::dc::AllRefsDataclass(maybe_ref_value='Hello'),
                refs::dc::AllRefsDataclass(maybe_ref_value=refs::create_string_reference('hello')),
            ]
        )
        """)

    ## plugin argument annotated with Entity | DC => custom to_python
    #  -> verify that resulting dynamic proxy has appropriate path context
    with raises_wrapped(UnexpectedReference, match="Encountered unexpected reference .* Encountered at v.non_ref_value"):
        run_snippet(
            "refs::plugins::takes_union_with_dc(refs::NormalEntity(non_ref_value=refs::create_string_reference('test')))"
        )
    with raises_wrapped(UnexpectedReference, match=r"Encountered unexpected reference .* Encountered at v\[0\].non_ref_value"):
        run_snippet(
            "refs::plugins::takes_union_with_dc([refs::NormalEntity(non_ref_value=refs::create_string_reference('test'))])"
        )
    with raises_wrapped(
        UnexpectedReference, match=r"Encountered unexpected reference .* Encountered at v\['x'\].non_ref_value"
    ):
        run_snippet(
            "refs::plugins::takes_union_with_dc({'x': refs::NormalEntity(non_ref_value=refs::create_string_reference('test'))})"
        )

    # Scenario: plugin annotated as <dataclass> gets Reference[<dataclass>]
    ## dataclass type that does not support reference attrs
    ### plain dataclass
    run_snippet("refs::plugins::takes_no_refs_dataclass(refs::dc::NoRefsDataclass())")
    run_snippet("""\
        refs::plugins::takes_mixed_refs_dataclass(
            refs::dc::MixedRefsDataclass(maybe_ref_value=refs::create_string_reference('hello'))
        )
        """)
    ### basic inheritance
    run_snippet("""\
        refs::plugins::takes_no_refs_dataclass(
            refs::dc::MixedRefsDataclass(maybe_ref_value=refs::create_string_reference('hello'))
        )
        """)
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
        run_snippet("""\
            refs::plugins::takes_no_refs_dataclass(
                refs::dc::NoRefsDataclass(non_ref_value=refs::create_string_reference('hello'))
            )
            """)
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
    ### allowed because MixedRefsDataclass is a child of NoRefsDataclass
    run_snippet("refs::plugins::takes_no_refs_dataclass_or_ref(refs::dc::MixedRefsDataclass(maybe_ref_value='hello'))")
    run_snippet("refs::plugins::takes_no_refs_dataclass_or_ref(refs::dc::create_mixed_refs_dataclass_reference('hello'))")
    ### not allowed because AllRefsDataclass is no child of NoRefsDataclass
    with pytest.raises(
        PluginTypeException,
        match=re.escape("Expected type: Reference[refs::dc::MixedRefsDataclass] | refs::dc::MixedRefsDataclass"),
    ):
        run_snippet("refs::plugins::takes_mixed_refs_dataclass_or_ref(refs::dc::AllRefsDataclass(maybe_ref_value='hello'))")
    with pytest.raises(
        PluginTypeException,
        match=re.escape("Expected type: Reference[refs::dc::MixedRefsDataclass] | refs::dc::MixedRefsDataclass"),
    ):
        run_snippet("refs::plugins::takes_mixed_refs_dataclass_or_ref(refs::dc::create_all_refs_dataclass_reference('hello'))")

    # Scenario: reference to dataclass as return value is converted to dataclass of references without type errors (#9837)
    run_snippet("refs::dc::create_complex_dataclass_reference()")

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
    with pytest.raises(PluginTypeException, match=r"Return value .* has incompatible type\..*Expected type: string\[\]"):
        run_snippet(
            "refs::plugins::returns_entity_list(refs::ListContainer(value=['Hello', refs::create_string_reference('hello')]))"
        )
    ## allowed if plugin annotates reference in return type
    run_snippet(
        "refs::plugins::returns_entity_ref_list(refs::ListContainer(value=['Hello', refs::create_string_reference('hello')]))"
    )

    # Scenario: allow_reference_values() called on non-proxy list (e.g. list inside dataclass). Allowed, does nothing
    run_snippet("refs::plugins::allow_references_on_non_proxy()")

    # Scenario: accidental operators on references
    with raises_wrapped(NotImplementedError, outer_exception=ExternalException, match="is an inmanta reference, not a boolean"):
        run_snippet("refs::plugins::bool_on_reference(refs::create_string_reference('hello'))")
    # allowed by necessity because it makes error message very brittle otherwise
    run_snippet("refs::plugins::str_on_reference(refs::create_string_reference('hello'))")
    run_snippet("refs::plugins::repr_on_reference(refs::create_string_reference('hello'))")


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
    assert "Reference cycle detected: StringReference() -> StringReference()" in str(e.value.__cause__)


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
        match=r"Invalid value `BoolReference\(StringReference\(\)\)`: "
        "the condition for an if statement can only be a boolean expression",
    ):
        snippetcompiler.do_export()


@pytest.mark.parametrize("agent", [True, False])
def test_references_in_resource_id(snippetcompiler: "SnippetCompilationTest", modules_v2_dir: str, agent: bool) -> None:
    """Test that references are rejected in the resource id value"""
    refs_module = os.path.join(modules_v2_dir, "refs")

    attr_assignments: str = "name='res1', agentname=ref" if agent else "name=ref, agentname='agent1'"
    snippetcompiler.setup_for_snippet(
        snippet=f"""
        import refs
        import refs::dc
        ref = refs::create_string_reference(name="CWD")

        refs::NullResource({attr_assignments})
        """,
        install_v2_modules=[env.LocalPackagePath(path=refs_module)],
        autostd=True,
    )

    with pytest.raises(
        resources.ResourceException,
        match=(
            f"Encountered reference in resource's {'agent' if agent else 'id'} attribute.*"
            f" Encountered at attribute '{'agent' if agent else ''}name'"
        ),
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
        match=r"Invalid value `StringReference\(\)` in index for attribute value: references can not be used in indexes",
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
        match=r"Invalid value `StringReference\(\)` in index for attribute value: references can not be used in indexes",
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
    baddy = TestReference({"a": object()})
    with pytest.raises(ValueError):
        baddy.serialize()


def test_references_string_format(snippetcompiler: "SnippetCompilationTest", modules_v2_dir: str) -> None:
    """
    Verify the behavior of references in the string format operations.
    """
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
        snippetcompiler.setup_for_snippet(f"import refs\n{snippet}", install_project=False, autostd=True)
        snippetcompiler.do_export()

    # f-string format
    with pytest.raises(UnexpectedReference, match="Encountered reference in string format for variable `ref`"):
        run_snippet("ref = refs::create_string_reference('Hello') f'Hello {ref}'")
    # old-style string format
    with pytest.raises(UnexpectedReference, match="Encountered reference in string format for variable `{{ref}}`"):
        run_snippet("ref = refs::create_string_reference('Hello') 'Hello {{ref}}'")
