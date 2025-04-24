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

import json
import logging
import os
import typing
from logging import DEBUG
from uuid import UUID

import pytest

from inmanta import env, references, resources, util
from inmanta.agent.handler import PythonLogger
from inmanta.ast import ExternalException, RuntimeException, TypingException
from inmanta.data.model import ReleasedResourceDetails, ReleasedResourceState
from inmanta.export import ResourceDict
from inmanta.references import Reference, ReferenceCycleException, reference
from inmanta.util.dict_path import Mapping, MutableMapping
from utils import ClientHelper, log_contains

if typing.TYPE_CHECKING:
    from conftest import SnippetCompilationTest

# The purpose of this module is to test references (compiler, exporter and executor). This module requires the test module
# defined in tests/data/modules_v2/refs


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
        import std::testing

        test_ref = refs::create_test(value=refs::create_string_reference(name="CWD"))

        std::testing::NullResource(
            name="test",
            agentname="test",
            fail=refs::create_bool_reference(name=test_ref.value),
        )
        """,
        install_v2_modules=[env.LocalPackagePath(path=refs_module)],
    )
    _, res_dict = snippetcompiler.do_export()
    assert len(res_dict) == 1
    serialized = res_dict.popitem()[1].serialize()

    # validate that our UUID is stable
    assert_id(serialized["references"], "refs::Bool", "ed26b59b-a567-392e-8626-f89d821532b7")
    assert_id(serialized["references"], "refs::TestReference", "78d7ff5f-6309-3011-bfff-8068471d5761")
    assert_id(serialized["references"], "core::AttributeReference", "81cc3241-2368-3b6d-8807-6755bd27b2fa")
    assert_id(serialized["references"], "refs::String", "a8ed8c4f-204a-3f7e-a630-e21cb20e9209")

    data = json.dumps(serialized, default=util.api_boundary_json_encoder)

    resource = resources.Resource.deserialize(json.loads(data))
    resource.resolve_all_references(PythonLogger(logging.getLogger("test.refs")))
    assert not resource.fail and resource.fail is not None

    with caplog.at_level(DEBUG):
        resource.get_reference_value(UUID("78d7ff5f-6309-3011-bfff-8068471d5761"), PythonLogger(logging.getLogger("test.refs")))

    log_contains(caplog, "test.refs", DEBUG, "Using cached value for reference TestReference CWD")


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


def test_reference_cycle(snippetcompiler: "SnippetCompilationTest", modules_v2_dir: str) -> None:
    """Test the correct detection of reference cycles."""
    refs_module = os.path.join(modules_v2_dir, "refs")

    snippetcompiler.setup_for_snippet(
        snippet="""
        import refs
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
    """Test that references are rejected in expressions"""
    refs_module = os.path.join(modules_v2_dir, "refs")

    snippetcompiler.setup_for_snippet(
        snippet="""
        import refs
        value = refs::create_string_reference(name="CWD")

        refs::NullResource(name=value,agentname=value)

        """,
        install_v2_modules=[env.LocalPackagePath(path=refs_module)],
        autostd=True,
    )

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
        def __init__(self, keys):
            super().__init__()
            self.keys = keys

    round_trip_ref(TestReference({"a": "A"}))

    # Only clean json is allowed
    tr = TestReference({"a": "A"})
    baddy = TestReference({"a": tr})
    with pytest.raises(ValueError):
        baddy.serialize()
