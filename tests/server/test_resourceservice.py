"""
    Copyright 2021 Inmanta

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
import uuid

@pytest.mark.asyncio
async def test_events_api_endpoints(server, client, environment, clienthelper):
    """
    Test whether the `get_resource_events` and the `resource_did_dependency_change`
    endpoints behave as expected
    """

    async def start_deployment(rvid: str) -> uuid.UUID:
        action_id = uuid.uuid4()
        result = await client.resource_deploy_start(tid=environment, resource_id=rvid_r2_v1, action_id=action_id)
        assert result.code == 200, result
        return action_id

    async def deployment_done(rvid: str, action_id: uuid.UUID) -> uuid.UUID:


    version = await clienthelper.get_version()

    rvid_r1_v1 = f"std::File[agent1,path=/etc/file1],v={version}"
    rvid_r2_v1 = f"std::File[agent1,path=/etc/file2],v={version}"
    rvid_r3_v1 = f"std::File[agent1,path=/etc/file3],v={version}"
    resources = [
        {"id": rvid_r1_v1, "requires": [rvid_r2_v1, rvid_r3_v1], "purged": False, "send_event": False},
        {"id": rvid_r2_v1, "requires": [], "purged": False, "send_event": False},
        {"id": rvid_r3_v1, "requires": [], "purged": False, "send_event": False},
    ]

    await clienthelper.put_version_simple(resources, version)

