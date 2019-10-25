"""
    Copyright 2019 Inmanta

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

from inmanta.server import SLICE_PROJECT
from inmanta.server.services.projectservice import project_limit


@pytest.mark.asyncio
async def test_project_limit(server, client):
    project_slice = server.get_slice(SLICE_PROJECT)
    project_slice.feature_manager.set_feature(project_limit, 0)

    result = await client.create_project("project-test")
    assert result.code == 403

    project_slice.feature_manager.set_feature(project_limit, 1)

    result = await client.create_project("project-test")
    assert result.code == 200

    result = await client.create_project("project-test2")
    assert result.code == 403

    project_slice.feature_manager.set_feature(project_limit, -1)

    result = await client.create_project("project-test2")
    assert result.code == 200
