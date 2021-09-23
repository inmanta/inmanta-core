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
import datetime
import json
import uuid
from operator import itemgetter

import pytest
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from inmanta import data
from inmanta.server.config import get_bind_port


def compile_ids(compile_objects):
    return [compile["id"] for compile in compile_objects]


@pytest.fixture
async def env_with_compile_reports(client, environment):
    compile_requested_timestamps = []
    for i in range(8):
        requested = datetime.datetime.strptime(f"2021-09-09T11:{i}:00.0", "%Y-%m-%dT%H:%M:%S.%f")
        compile_requested_timestamps.append(requested)
        await data.Compile(
            id=uuid.uuid4(),
            remote_id=uuid.uuid4(),
            environment=uuid.UUID(environment),
            requested=requested,
            started=requested.replace(second=20) if i % 2 else None,
            completed=requested.replace(second=40) if i % 2 else None,
            do_export=bool(i % 3),
            force_update=False,
            metadata={"meta": 42} if i % 2 else None,
            environment_variables={"TEST_ENV_VAR": True} if i % 2 else None,
            success=i != 0,
            handled=True,
            version=i,
            substitute_compile_id=None,
            compile_data=None,
        ).insert()
    return environment, compile_requested_timestamps


@pytest.mark.parametrize(
    "order_by_column, order",
    [
        ("requested", "DESC"),
        ("requested", "ASC"),
    ],
)
@pytest.mark.asyncio
async def test_compile_reports_paging(server, client, env_with_compile_reports, order_by_column, order):
    environment, compile_requested_timestamps = env_with_compile_reports

    result = await client.get_compile_reports(
        environment,
        filter={"success": True, "requested": [f"lt:{compile_requested_timestamps[-1].astimezone(datetime.timezone.utc)}"]},
    )
    assert result.code == 200
    assert len(result.result["data"]) == 6

    all_compiles_in_expected_order = sorted(
        result.result["data"], key=itemgetter(order_by_column, "id"), reverse=order == "DESC"
    )
    all_compile_ids_in_expected_order = compile_ids(all_compiles_in_expected_order)

    result = await client.get_compile_reports(
        environment,
        limit=2,
        sort=f"{order_by_column}.{order}",
        filter={"success": True, "requested": [f"lt:{compile_requested_timestamps[-1].astimezone(datetime.timezone.utc)}"]},
    )
    assert result.code == 200
    assert len(result.result["data"]) == 2

    assert compile_ids(result.result["data"]) == all_compile_ids_in_expected_order[:2]

    assert result.result["metadata"] == {"total": 6, "before": 0, "after": 4, "page_size": 2}
    assert result.result["links"].get("next") is not None
    assert result.result["links"].get("prev") is None

    port = get_bind_port()
    base_url = "http://localhost:%s" % (port,)
    http_client = AsyncHTTPClient()

    # Test link for next page
    url = f"""{base_url}{result.result["links"]["next"]}"""
    assert "limit=2" in url
    assert "filter.success=" in url
    assert "filter.requested=" in url
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": str(environment)},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    assert compile_ids(response["data"]) == all_compile_ids_in_expected_order[2:4]
    assert response["links"].get("prev") is not None
    assert response["links"].get("next") is not None
    assert response["metadata"] == {"total": 6, "before": 2, "after": 2, "page_size": 2}

    # Test link for next page
    url = f"""{base_url}{response["links"]["next"]}"""
    assert "limit=2" in url
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": str(environment)},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    next_page_compile_ids = compile_ids(response["data"])
    assert next_page_compile_ids == all_compile_ids_in_expected_order[4:]
    assert response["links"].get("prev") is not None
    assert response["links"].get("next") is None
    assert response["metadata"] == {"total": 6, "before": 4, "after": 0, "page_size": 2}

    # Test link for previous page
    url = f"""{base_url}{response["links"]["prev"]}"""
    assert "limit=2" in url
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": str(environment)},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    prev_page_compile_ids = compile_ids(response["data"])
    assert prev_page_compile_ids == all_compile_ids_in_expected_order[2:4]
    assert response["links"].get("prev") is not None
    assert response["links"].get("next") is not None
    assert response["metadata"] == {"total": 6, "before": 2, "after": 2, "page_size": 2}

    result = await client.get_compile_reports(
        environment,
        limit=6,
        sort=f"{order_by_column}.{order}",
        filter={"success": True, "requested": [f"lt:{compile_requested_timestamps[-1].astimezone(datetime.timezone.utc)}"]},
    )
    assert result.code == 200
    assert len(result.result["data"]) == 6
    assert compile_ids(result.result["data"]) == all_compile_ids_in_expected_order

    assert result.result["metadata"] == {"total": 6, "before": 0, "after": 0, "page_size": 6}


@pytest.mark.asyncio
async def test_compile_reports_filters(server, client, env_with_compile_reports):
    environment, compile_requested_timestamps = env_with_compile_reports

    result = await client.get_compile_reports(environment, filter={"success": True})
    assert result.code == 200
    assert all([compile["success"] for compile in result.result["data"]])

    result = await client.get_compile_reports(environment, filter={"success": False})
    assert result.code == 200
    assert all([not compile["success"] for compile in result.result["data"]])

    result = await client.get_compile_reports(environment, filter={"completed": True})
    assert result.code == 200
    assert all([compile["completed"] for compile in result.result["data"]])

    result = await client.get_compile_reports(environment, filter={"completed": False})
    assert result.code == 200
    assert all([not compile["completed"] for compile in result.result["data"]])

    result = await client.get_compile_reports(environment, filter={"started": True})
    assert result.code == 200
    assert all([compile["started"] for compile in result.result["data"]])

    result = await client.get_compile_reports(environment, filter={"started": False})
    assert result.code == 200
    assert all([not compile["started"] for compile in result.result["data"]])

    result = await client.get_compile_reports(environment, filter={"started": True, "completed": True, "success": True})
    assert result.code == 200
    assert all([compile["started"] for compile in result.result["data"]])
    assert all([compile["completed"] for compile in result.result["data"]])
    assert all([compile["success"] for compile in result.result["data"]])

    result = await client.get_compile_reports(
        environment,
        sort="requested.asc",
        filter={
            "success": True,
            "requested": [
                f"lt:{compile_requested_timestamps[-1].astimezone(datetime.timezone.utc)}",
                f"gt:{compile_requested_timestamps[3].astimezone(datetime.timezone.utc)}",
            ],
        },
    )
    assert result.code == 200
    assert len(result.result["data"]) == 3
    assert datetime.datetime.strptime(result.result["data"][0]["requested"], "%Y-%m-%dT%H:%M:%S.%f").replace(
        tzinfo=datetime.timezone.utc
    ) == compile_requested_timestamps[4].astimezone(datetime.timezone.utc)
    assert datetime.datetime.strptime(result.result["data"][1]["requested"], "%Y-%m-%dT%H:%M:%S.%f").replace(
        tzinfo=datetime.timezone.utc
    ) == compile_requested_timestamps[5].astimezone(datetime.timezone.utc)
    assert datetime.datetime.strptime(result.result["data"][2]["requested"], "%Y-%m-%dT%H:%M:%S.%f").replace(
        tzinfo=datetime.timezone.utc
    ) == compile_requested_timestamps[6].astimezone(datetime.timezone.utc)


@pytest.mark.parametrize(
    "sort, expected_status",
    [
        ("date.Desc", 400),
        ("timestamp.Desc", 400),
        ("requested.asc", 200),
        ("requested.dsc", 400),
        ("started.desc", 400),
        ("timestamps", 400),
        ("timestamps.DESC", 400),
        ("requested.ASC", 200),
        ("Dates.ASC", 400),
    ],
)
@pytest.mark.asyncio
async def test_sorting_validation(server, client, sort, expected_status, env_with_compile_reports):
    environment, _ = env_with_compile_reports
    result = await client.get_compile_reports(environment, limit=2, sort=sort)
    assert result.code == expected_status


@pytest.mark.parametrize(
    "filter, expected_status",
    [
        ("requested.Desc", 400),
        ({"success": "Not"}, 400),
        ({"success": [True, True]}, 400),
        ({"success": None}, 400),
        ({"completed": datetime.datetime.now()}, 400),
        ({"started": datetime.datetime.now()}, 400),
        ({"started": [True, False]}, 400),
        ({"completed": [False, False]}, 400),
        ({"completed": [None]}, 400),
        ({"requested": f"lt:{datetime.datetime.now()}"}, 200),
        ({"requested": f"{datetime.datetime.now()}"}, 400),
    ],
)
@pytest.mark.asyncio
async def test_filter_validation(server, client, filter, expected_status, env_with_compile_reports):
    environment, _ = env_with_compile_reports
    result = await client.get_compile_reports(environment, filter=filter)
    assert result.code == expected_status
