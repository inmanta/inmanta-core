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
import uuid
from datetime import datetime
from typing import Dict, Optional

import pytest

from inmanta import data
from inmanta.data.model import ResourceVersionIdStr


@pytest.mark.asyncio
async def test_get_facts(client, environment):
    """
    Test retrieving facts via the API
    """
    env_id = uuid.UUID(environment)
    version = 1
    await data.ConfigurationModel(
        environment=env_id,
        version=version,
        date=datetime.now(),
        total=1,
        released=True,
        version_info={},
    ).insert()

    path = "/etc/file1"
    resource_id = f"std::File[agent1,path={path}]"
    res1_v1 = data.Resource.new(
        environment=env_id, resource_version_id=ResourceVersionIdStr(f"{resource_id},v={version}"), attributes={"path": path}
    )
    await res1_v1.insert()
    path = "/etc/file2"
    resource_id_2 = f"std::File[agent1,path={path}]"
    await data.Resource.new(
        environment=env_id,
        resource_version_id=ResourceVersionIdStr(f"{resource_id_2},v={version}"),
        attributes={"path": path},
    ).insert()
    resource_id_3 = "std::File[agent1,path=/etc/file3]"

    async def insert_param(
        name: str, resource_id: str, updated: Optional[datetime] = None, metadata: Optional[Dict[str, str]] = None
    ) -> uuid.UUID:
        param_id = uuid.uuid4()
        await data.Parameter(
            id=param_id,
            name=name,
            value="42",
            environment=env_id,
            source="fact",
            resource_id=resource_id,
            updated=updated,
            metadata=metadata,
        ).insert()
        return param_id

    param_id_1 = await insert_param("param", resource_id=resource_id, updated=datetime.now())
    await insert_param("param2", resource_id=resource_id)
    param_id_3 = await insert_param(
        "param_for_other_resource", resource_id_2, updated=datetime.now(), metadata={"very_important_metadata": "123"}
    )

    # Query fact list
    result = await client.get_facts(environment, resource_id)
    assert result.code == 200
    assert len(result.result["data"]) == 2

    result = await client.get_facts(environment, resource_id_2)
    assert result.code == 200
    assert len(result.result["data"]) == 1

    # Query facts for a resource that doesn't exist
    result = await client.get_facts(environment, resource_id_3)
    assert result.code == 200
    assert len(result.result["data"]) == 0

    # Query a single fact
    result = await client.get_fact(environment, resource_id, param_id_1)
    assert result.code == 200
    assert result.result["data"]["name"] == "param"
    assert result.result["data"]["value"] == "42"

    # Query a single fact with mismatching resource id
    result = await client.get_fact(environment, resource_id, param_id_3)
    assert result.code == 404

    # Query a single not existing fact
    result = await client.get_fact(environment, resource_id, uuid.uuid4())
    assert result.code == 404
