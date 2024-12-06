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
import uuid

import pytest

from inmanta import env, resources, util

if typing.TYPE_CHECKING:
    from conftest import SnippetCompilationTest

# The purpose of this module is to test references (compiler, exporter and executor). This module requires the test module
# defined in tests/data/modules_v2/refs


def test_references_in_model(snippetcompiler: "SnippetCompilationTest", modules_v2_dir: str) -> None:
    """Test the use of references in the model and if they produce the correct serialized form."""
    refs_module = os.path.join(modules_v2_dir, "refs")

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
    assert serialized["references"][0].id == uuid.UUID("541c1529-a48e-347f-b3bc-992e03ac54ef")
    assert serialized["references"][1].id == uuid.UUID("154575d1-df13-3dec-afd2-ca8c86b55f18")

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
