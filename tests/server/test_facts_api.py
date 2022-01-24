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
import json
import uuid
from datetime import datetime
from operator import itemgetter
from typing import Dict, List, Optional, Tuple

import pytest
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from inmanta import data
from inmanta.data.model import ResourceVersionIdStr
from inmanta.server.config import get_bind_port


@pytest.fixture
async def env_with_facts(environment, client) -> Tuple[str, List[str], List[str]]:
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

    path = "/tmp/filex"
    resource_id_4 = f"std::File[agent1,path={path}]"
    await data.Resource.new(
        environment=env_id,
        resource_version_id=ResourceVersionIdStr(f"{resource_id_4},v={version}"),
        attributes={"path": path},
    ).insert()

    async def insert_param(
        name: str,
        resource_id: Optional[str] = None,
        source: str = "fact",
        updated: Optional[datetime] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> uuid.UUID:
        param_id = uuid.uuid4()
        await data.Parameter(
            id=param_id,
            name=name,
            value="42",
            environment=env_id,
            source=source,
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
    for i in range(5):
        await insert_param(
            f"param_for_new_resource{i}",
            resource_id_4,
            updated=datetime.now() if i % 2 else None,
            metadata={"new_metadata": "42"} if i % 3 else None,
        )
    await insert_param("param_not_related_to_resource", source="plugin")
    yield environment, [param_id_1, param_id_3], [resource_id, resource_id_2, resource_id_3, resource_id_4]


@pytest.mark.asyncio
async def test_get_facts(client, env_with_facts):
    """
    Test retrieving facts via the API
    """
    environment, param_ids, resource_ids = env_with_facts

    # Query fact list
    result = await client.get_facts(environment, resource_ids[0])
    assert result.code == 200
    assert len(result.result["data"]) == 2

    result = await client.get_facts(environment, resource_ids[1])
    assert result.code == 200
    assert len(result.result["data"]) == 1

    # Query facts for a resource that doesn't exist
    result = await client.get_facts(environment, resource_ids[2])
    assert result.code == 200
    assert len(result.result["data"]) == 0

    # Query a single fact
    result = await client.get_fact(environment, resource_ids[0], param_ids[0])
    assert result.code == 200
    assert result.result["data"]["name"] == "param"
    assert result.result["data"]["value"] == "42"

    # Query a single fact with mismatching resource id
    result = await client.get_fact(environment, resource_ids[0], param_ids[1])
    assert result.code == 404

    # Query a single not existing fact
    result = await client.get_fact(environment, resource_ids[0], uuid.uuid4())
    assert result.code == 404


@pytest.mark.asyncio
async def test_fact_list_filters(client, env_with_facts: Tuple[str, List[str], List[str]]):
    environment, param_ids, resource_ids = env_with_facts
    result = await client.get_all_facts(
        environment,
    )
    assert result.code == 200
    assert len(result.result["data"]) == 8
    # Only facts are returned by this endpoint
    assert all(fact["source"] == "fact" for fact in result.result["data"])

    result = await client.get_all_facts(environment, filter={"name": "other"})
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert result.result["data"][0]["name"] == "param_for_other_resource"
    result = await client.get_all_facts(environment, filter={"resource_id": resource_ids[3]})
    assert result.code == 200
    assert len(result.result["data"]) == 5
    assert all(fact["resource_id"] == resource_ids[3] for fact in result.result["data"])

    result = await client.get_all_facts(environment, filter={"updated": f"gt:{datetime.now()}"})
    assert result.code == 400

    result = await client.get_all_facts(environment, filter={"resource_id": resource_ids[2]})
    assert result.code == 200
    assert len(result.result["data"]) == 0

    result = await client.get_all_facts(
        uuid.uuid4(),
    )
    assert result.code == 404


def fact_ids(fact_objects):
    return [fact["id"] for fact in fact_objects]


@pytest.mark.parametrize("order_by_column", ["name", "resource_id"])
@pytest.mark.parametrize("order", ["DESC", "ASC"])
@pytest.mark.asyncio
async def test_facts_paging(server, client, order_by_column, order, env_with_facts):
    """ Test querying facts with paging, using different sorting parameters."""
    env, _, _ = env_with_facts
    result = await client.get_all_facts(
        env,
        filter={"name": "res"},
    )
    assert result.code == 200
    assert len(result.result["data"]) == 6
    all_facts_in_expected_order = sorted(result.result["data"], key=itemgetter(order_by_column, "id"), reverse=order == "DESC")
    all_fact_ids_in_expected_order = fact_ids(all_facts_in_expected_order)

    result = await client.get_all_facts(env, limit=2, sort=f"{order_by_column}.{order}", filter={"name": "res"})
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert fact_ids(result.result["data"]) == all_fact_ids_in_expected_order[:2]

    assert result.result["metadata"] == {"total": 6, "before": 0, "after": 4, "page_size": 2}
    assert result.result["links"].get("next") is not None
    assert result.result["links"].get("prev") is None

    port = get_bind_port()
    base_url = "http://localhost:%s" % (port,)
    http_client = AsyncHTTPClient()

    # Test link for next page
    url = f"""{base_url}{result.result["links"]["next"]}"""
    assert "limit=2" in url
    assert "filter.name=res" in url
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": env},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    assert fact_ids(response["data"]) == all_fact_ids_in_expected_order[2:4]
    assert response["links"].get("prev") is not None
    assert response["links"].get("next") is not None
    assert response["metadata"] == {"total": 6, "before": 2, "after": 2, "page_size": 2}

    # Test link for next page
    url = f"""{base_url}{response["links"]["next"]}"""
    # The filters should be present for the links as well
    assert "limit=2" in url
    assert "filter.name=res" in url
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": env},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    next_page_ids = fact_ids(response["data"])
    assert next_page_ids == all_fact_ids_in_expected_order[4:]
    assert response["links"].get("prev") is not None
    assert response["links"].get("next") is None
    assert response["metadata"] == {"total": 6, "before": 4, "after": 0, "page_size": 2}

    # Test link for previous page
    url = f"""{base_url}{response["links"]["prev"]}"""
    assert "limit=2" in url
    assert "filter.name=res" in url
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": env},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    prev_page_ids = fact_ids(response["data"])
    assert prev_page_ids == all_fact_ids_in_expected_order[2:4]
    assert response["links"].get("prev") is not None
    assert response["links"].get("next") is not None
    assert response["metadata"] == {"total": 6, "before": 2, "after": 2, "page_size": 2}


@pytest.mark.asyncio
async def test_sorting_validation(server, client, env_with_facts):
    env, _, _ = env_with_facts
    sort_status_map = {
        "agents.Desc": 400,
        "name.asc": 200,
        "version.desc": 400,
        "name": 400,
        "resourceid.asc": 400,
        "res_id.asc": 400,
        "resource_id.asc": 200,
    }
    for sort, expected_status in sort_status_map.items():
        result = await client.get_all_facts(env, sort=sort)
        assert result.code == expected_status


@pytest.mark.asyncio
async def test_filter_validation(server, client, env_with_facts):
    env, _, _ = env_with_facts
    filter_status_map = [
        ("name.desc", 400),
        ({"name": ["file1", "res2"]}, 200),
        ({"resource_id": [1, 2]}, 200),
        ({"updated": "le:42"}, 400),
        ({"source": "internal"}, 400),
        ({"updated": True}, 400),
    ]
    for filter, expected_status in filter_status_map:
        result = await client.get_all_facts(env, filter=filter)
        assert result.code == expected_status
