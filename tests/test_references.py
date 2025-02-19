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
import os
import typing

import pytest

from inmanta import env, references, resources, util
from inmanta.ast import ExternalException, RuntimeException, TypingException
from inmanta.references import ReferenceCycleException

if typing.TYPE_CHECKING:
    from conftest import SnippetCompilationTest

# The purpose of this module is to test references (compiler, exporter and executor). This module requires the test module
# defined in tests/data/modules_v2/refs


def test_references_in_model(snippetcompiler: "SnippetCompilationTest", modules_v2_dir: str) -> None:
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

    assert not resource.fail


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
        match=r"Invalid value `\<inmanta_plugins\.refs\.BoolReference object at 0x[0-9a-f]*\>`: "
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
