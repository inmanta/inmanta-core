"""
    Copyright 2022 Inmanta

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
import datetime
import json
import uuid
from operator import itemgetter

import pytest
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from inmanta import data
from inmanta.server.config import get_bind_port
from inmanta.util import parse_timestamp


@pytest.fixture
async def env_with_parameters(server, client, environment: str):
    env_id = uuid.UUID(environment)
    version = 1
    await data.ConfigurationModel(
        environment=env_id,
        version=version,
        date=datetime.datetime.now(),
        total=1,
        released=True,
        version_info={},
        is_suitable_for_partial_compiles=False,
    ).insert()

    id_counter = [0x1000]

    async def insert_param(
        name: str, source: str, updated: datetime.datetime | None = None, metadata: dict[str, str] | None = None
    ) -> uuid.UUID:
        id_counter[0] += 1
        param_id = uuid.UUID(int=id_counter[0])
        await data.Parameter(
            id=param_id,
            name=name,
            value="42",
            environment=env_id,
            source=source,
            updated=updated,
            metadata=metadata,
        ).insert()
        return param_id

    def get_timestamp(minutes: int) -> datetime.datetime:
        return datetime.datetime.strptime(f"2022-01-20T11:{minutes}:00.0", "%Y-%m-%dT%H:%M:%S.%f")

    timestamps = []
    for i in range(9):
        updated = get_timestamp(i)
        timestamps.append(updated)
        await insert_param(f"param{i}", source="plugin" if i not in [1, 4, 5] else "report", updated=updated if i % 2 else None)

    updated = get_timestamp(9)
    timestamps.append(updated)
    await insert_param("different_param", "user", updated, metadata={"meta": "success"})
    await insert_param("param18", "fact")

    yield environment, timestamps


async def test_parameter_list_filters(client, env_with_parameters: tuple[str, list[datetime.datetime]]):
    environment, timestamps = env_with_parameters
    result = await client.get_parameters(
        environment,
    )
    assert result.code == 200
    assert len(result.result["data"]) == 10
    # Facts are not returned by this endpoint
    assert not any(param["source"] == "fact" for param in result.result["data"])

    result = await client.get_parameters(environment, filter={"name": "different"})
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert result.result["data"][0]["name"] == "different_param"
    assert result.result["data"][0]["source"] == "user"
    result = await client.get_parameters(environment, filter={"source": "plugin"})
    assert result.code == 200
    assert len(result.result["data"]) == 6
    assert all(param["source"] == "plugin" for param in result.result["data"])
    result = await client.get_parameters(
        environment, filter={"source": "report", "updated": f"gt:{timestamps[1].astimezone(datetime.timezone.utc)}"}
    )
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert result.result["data"][0]["name"] == "param5"

    result = await client.get_parameters(
        uuid.uuid4(),
    )
    assert result.code == 404


def parameter_ids(parameter_objects):
    return [parameter["id"] for parameter in parameter_objects]


@pytest.mark.parametrize("order_by_column", ["name", "source", "updated"])
@pytest.mark.parametrize("order", ["DESC", "ASC"])
async def test_parameters_paging(server, client, order_by_column, order, env_with_parameters):
    """Test querying parameters with paging, using different sorting parameters."""
    env, timestamps = env_with_parameters
    result = await client.get_parameters(
        env,
        filter={"source": "plugin"},
    )
    assert result.code == 200
    assert len(result.result["data"]) == 6
    all_parameters = result.result["data"]
    for parameter in all_parameters:
        if not parameter["updated"]:
            parameter["updated"] = datetime.datetime.min.replace(tzinfo=datetime.UTC)
        else:
            parameter["updated"] = parse_timestamp(parameter["updated"])
    all_parameters_in_expected_order = sorted(all_parameters, key=itemgetter(order_by_column, "id"), reverse=order == "DESC")
    all_parameter_ids_in_expected_order = parameter_ids(all_parameters_in_expected_order)

    result = await client.get_parameters(env, limit=2, sort=f"{order_by_column}.{order}", filter={"source": "plugin"})
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert parameter_ids(result.result["data"]) == all_parameter_ids_in_expected_order[:2]

    assert result.result["metadata"] == {"total": 6, "before": 0, "after": 4, "page_size": 2}
    assert result.result["links"].get("next") is not None
    assert result.result["links"].get("prev") is None

    port = get_bind_port()
    base_url = f"http://localhost:{port}"
    http_client = AsyncHTTPClient()

    # Test link for self page
    url = f"""{base_url}{result.result["links"]["self"]}"""
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": env},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    assert response == result.result

    # Test link for next page
    url = f"""{base_url}{result.result["links"]["next"]}"""
    assert "limit=2" in url
    assert "filter.source=plugin" in url
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": env},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    assert parameter_ids(response["data"]) == all_parameter_ids_in_expected_order[2:4]
    assert response["links"].get("prev") is not None
    assert response["links"].get("next") is not None
    assert response["metadata"] == {"total": 6, "before": 2, "after": 2, "page_size": 2}

    # Test link for next page
    url = f"""{base_url}{response["links"]["next"]}"""
    # The filters should be present for the links as well
    assert "limit=2" in url
    assert "filter.source=plugin" in url
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": env},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    next_page_ids = parameter_ids(response["data"])
    assert next_page_ids == all_parameter_ids_in_expected_order[4:]
    assert response["links"].get("prev") is not None
    assert response["links"].get("next") is None
    assert response["metadata"] == {"total": 6, "before": 4, "after": 0, "page_size": 2}

    # Test link for previous page
    url = f"""{base_url}{response["links"]["prev"]}"""
    assert "limit=2" in url
    assert "filter.source=plugin" in url
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": env},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    prev_page_ids = parameter_ids(response["data"])
    assert prev_page_ids == all_parameter_ids_in_expected_order[2:4]
    assert response["links"].get("prev") is not None
    assert response["links"].get("next") is not None
    assert response["metadata"] == {"total": 6, "before": 2, "after": 2, "page_size": 2}


async def test_sorting_validation(server, client, env_with_parameters):
    env, _ = env_with_parameters
    sort_status_map = {
        "agents.Desc": 400,
        "name.asc": 200,
        "version.desc": 400,
        "updated": 400,
        "total.asc": 400,
        "value.asc": 400,
        "source.asc": 200,
    }
    for sort, expected_status in sort_status_map.items():
        result = await client.get_parameters(env, sort=sort)
        assert result.code == expected_status


async def test_filter_validation(server, client, env_with_parameters):
    env, _ = env_with_parameters
    filter_status_map = [
        ("name.desc", 400),
        ({"name": ["file1", "res2"]}, 200),
        ({"updated": [1, 2]}, 400),
        ({"updated": "le:42"}, 400),
        ({"source": "internal"}, 200),
        ({"updated": True}, 400),
    ]
    for filter, expected_status in filter_status_map:
        result = await client.get_parameters(env, filter=filter)
        assert result.code == expected_status
