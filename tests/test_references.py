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

import json
import os
import typing

import pytest

from inmanta import env, references, resources, util

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
    assert_id(serialized["references"], "refs::Bool", "207f236b-43ea-36e3-b5a2-998117929c04")
    assert_id(serialized["references"], "refs::TestReference", "78d7ff5f-6309-3011-bfff-8068471d5761")
    assert_id(serialized["references"], "core::AttributeReference", "a2a6c977-699f-3294-8e53-9d4d101b6b72")
    assert_id(serialized["references"], "refs::String", "a8ed8c4f-204a-3f7e-a630-e21cb20e9209")

    data = json.dumps(serialized, default=util.api_boundary_json_encoder)

    resource = resources.Resource.deserialize(json.loads(data))

    resource.resolve_all_references()
    assert not resource.fail


def test_reference_cycle(snippetcompiler: "SnippetCompilationTest", modules_v2_dir: str) -> None:
    """Test the use of references in the model and if they produce the correct serialized form."""
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

    with pytest.raises(Exception):
        # TODO: catch correct exception!
        snippetcompiler.do_export()