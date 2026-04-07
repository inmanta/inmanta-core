"""
Copyright 2026 Inmanta

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
import yaml

from inmanta.server import SLICE_SERVER, SLICE_TRANSPORT, extensions, protocol

NAME_TEST_SLICE = "test_slice"
BOOL_FEATURE1 = extensions.BoolFeature(slice=NAME_TEST_SLICE, name="bool_feature1")
BOOL_FEATURE2 = extensions.BoolFeature(slice=NAME_TEST_SLICE, name="bool_feature2")


class TestSlice(protocol.ServerSlice):
    def __init__(self) -> None:
        super().__init__(NAME_TEST_SLICE)

    def get_dependencies(self) -> list[str]:
        return []

    def get_depended_by(self) -> list[str]:
        return [SLICE_TRANSPORT]

    def define_features(self) -> list[extensions.Feature[object]]:
        return [BOOL_FEATURE1, BOOL_FEATURE2]


@pytest.fixture(scope="function")
def content_features_file() -> str:
    content_feature_file = {
        "slices": {
            NAME_TEST_SLICE: {
                BOOL_FEATURE1.name: True,
                BOOL_FEATURE2.name: False,
            }
        }
    }
    return yaml.safe_dump(content_feature_file)


async def test_is_bool_feature_enabled(server, client):
    """
    Verify the behavior of the is_bool_feature_enabled endpoint.
    """
    server_slice = server.get_slice(SLICE_SERVER)
    test_slice = TestSlice()
    # Load features from TestSlice into the FeatureManager
    server_slice.feature_manager.add_slice(test_slice)
    server_slice.feature_manager._load_feature_config()
    assert await client.is_bool_feature_enabled(slice_name=NAME_TEST_SLICE, feature_name="bool_feature1").value()
    assert not await client.is_bool_feature_enabled(slice_name=NAME_TEST_SLICE, feature_name="bool_feature2").value()
