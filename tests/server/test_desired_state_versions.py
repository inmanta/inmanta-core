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
from typing import Dict, List, Tuple

import pytest
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from inmanta import data
from inmanta.data.model import DesiredStateLabel, PromoteTriggerMethod
from inmanta.server import SLICE_AGENT_MANAGER
from inmanta.server.config import get_bind_port


@pytest.fixture
async def environments_with_versions(server, client) -> Tuple[Dict[str, uuid.UUID], List[datetime.datetime]]:
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    cm_timestamps = []
    for i in range(0, 10):
        cm_timestamps.append(datetime.datetime.strptime(f"2021-12-06T11:{i}:00.0", "%Y-%m-%dT%H:%M:%S.%f"))

    # Add multiple versions of model
    # 1: skipped_candidate, 2,3: retired, 4,5,6: skipped_candidate, 7: active, 8,9: candidate
    for i in range(1, 10):
        cm = data.ConfigurationModel(
            environment=env.id,
            version=i,
            date=cm_timestamps[i - 1],
            total=1,
            released=i in {2, 3, 7},
            version_info={"export_metadata": {"message": "Recompile model because state transition", "type": "lsm_export"}}
            if i % 2
            else {
                "export_metadata": {"message": "Recompile model because one or more parameters were updated", "type": "param"}
            },
        )
        await cm.insert()
    env2 = data.Environment(name="dev-test2", project=project.id, repo_url="", repo_branch="")
    await env2.insert()
    cm = data.ConfigurationModel(
        environment=env2.id,
        version=11,
        date=datetime.datetime.now(),
        total=1,
        released=True,
        version_info={},
    )
    await cm.insert()

    env3 = data.Environment(name="dev-test3", project=project.id, repo_url="", repo_branch="")
    await env3.insert()
    cm = data.ConfigurationModel(
        environment=env3.id,
        version=7,
        date=datetime.datetime.now(),
        total=1,
        released=False,
        version_info={},
    )
    await cm.insert()

    env4 = data.Environment(name="dev-test4", project=project.id, repo_url="", repo_branch="")
    await env4.insert()
    environments = {
        "multiple_versions": env.id,
        "single_released_version": env2.id,
        "no_released_version": env3.id,
        "no_versions": env4.id,
    }

    yield environments, cm_timestamps


@pytest.mark.asyncio
async def test_filter_versions(
    server, client, environments_with_versions: Tuple[Dict[str, uuid.UUID], List[datetime.datetime]]
):
    """ Test querying desired state versions."""
    environments, cm_timestamps = environments_with_versions
    env = environments["multiple_versions"]

    result = await client.list_desired_state_versions(env)
    assert result.code == 200
    assert len(result.result["data"]) == 9

    result = await client.list_desired_state_versions(env, filter={"version": ["ge:3", "le:5"]})
    assert result.code == 200
    assert len(result.result["data"]) == 3

    result = await client.list_desired_state_versions(env, filter={"version": ["gt:10"]})
    assert result.code == 200
    assert len(result.result["data"]) == 0

    result = await client.list_desired_state_versions(
        env, filter={"date": [f"le:{cm_timestamps[3].astimezone(datetime.timezone.utc)}"]}
    )
    assert result.code == 200
    assert len(result.result["data"]) == 4

    # Make sure the status is determined correctly
    result = await client.list_desired_state_versions(env, filter={"status": ["active"]})
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert result.result["data"][0]["version"] == 7
    # Check the labels
    assert len(result.result["data"][0]["labels"]) == 1
    assert DesiredStateLabel(**result.result["data"][0]["labels"][0]) == DesiredStateLabel(
        name="lsm_export", message="Recompile model because state transition"
    )

    result = await client.list_desired_state_versions(env, filter={"status": ["skipped_candidate"]}, sort="version.asc")
    assert result.code == 200
    assert len(result.result["data"]) == 4
    assert version_numbers(result.result["data"]) == [1, 4, 5, 6]

    result = await client.list_desired_state_versions(env, filter={"status": ["retired"]}, sort="version.asc")
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert version_numbers(result.result["data"]) == [2, 3]

    result = await client.list_desired_state_versions(env, filter={"status": ["candidate"]}, sort="version.asc")
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert version_numbers(result.result["data"]) == [8, 9]

    result = await client.list_desired_state_versions(
        env, filter={"status": ["active"], "date": [f"le:{cm_timestamps[3].astimezone(datetime.timezone.utc)}"]}
    )
    assert result.code == 200
    assert len(result.result["data"]) == 0

    result = await client.list_desired_state_versions(
        env, limit=2, filter={"date": [f"le:{cm_timestamps[3].astimezone(datetime.timezone.utc)}"]}
    )
    assert result.code == 200
    assert len(result.result["data"]) == 2

    result = await client.list_desired_state_versions(environments["single_released_version"])
    assert result.code == 200
    assert result.result["data"][0]["version"] == 11
    assert result.result["data"][0]["status"] == "active"

    result = await client.list_desired_state_versions(environments["no_released_version"])
    assert result.code == 200
    assert result.result["data"][0]["version"] == 7
    assert result.result["data"][0]["status"] == "candidate"
    # The version_info field of this ConfigurationModel is empty, which should result in an empty label list
    assert result.result["data"][0]["labels"] == []

    result = await client.list_desired_state_versions(environments["no_versions"])
    assert result.code == 200
    assert len(result.result["data"]) == 0

    # Querying with a not existing environment should result in 404
    result = await client.list_desired_state_versions(uuid.uuid4())
    assert result.code == 404


def version_numbers(desired_state_objects):
    return [desired_state["version"] for desired_state in desired_state_objects]


@pytest.mark.parametrize(
    "order",
    [
        ("DESC"),
        ("ASC"),
    ],
)
@pytest.mark.asyncio
async def test_desired_state_versions_paging(
    server, client, order: str, environments_with_versions: Tuple[Dict[str, uuid.UUID], List[datetime.datetime]]
):
    """ Test querying desired state versions with paging, using different sorting parameters."""
    environments, timestamps = environments_with_versions
    env = environments["multiple_versions"]
    order_by_column = "version"

    result = await client.list_desired_state_versions(
        env,
        filter={"date": [f"gt:{timestamps[1].astimezone(datetime.timezone.utc)}"]},
    )
    assert result.code == 200
    assert len(result.result["data"]) == 7
    all_versions_in_expected_order = sorted(result.result["data"], key=itemgetter(order_by_column), reverse=order == "DESC")
    all_versions_in_expected_order = version_numbers(all_versions_in_expected_order)

    result = await client.list_desired_state_versions(
        env,
        limit=2,
        sort=f"{order_by_column}.{order}",
        filter={"date": [f"gt:{timestamps[1].astimezone(datetime.timezone.utc)}"]},
    )
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert version_numbers(result.result["data"]) == all_versions_in_expected_order[:2]

    assert result.result["metadata"] == {"total": 7, "before": 0, "after": 5, "page_size": 2}
    assert result.result["links"].get("next") is not None
    assert result.result["links"].get("prev") is None

    port = get_bind_port()
    base_url = "http://localhost:%s" % (port,)
    http_client = AsyncHTTPClient()

    # Test link for next page
    url = f"""{base_url}{result.result["links"]["next"]}"""
    assert "limit=2" in url
    assert "filter.date=" in url
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": str(env)},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    assert version_numbers(response["data"]) == all_versions_in_expected_order[2:4]
    assert response["links"].get("prev") is not None
    assert response["links"].get("next") is not None
    assert response["metadata"] == {"total": 7, "before": 2, "after": 3, "page_size": 2}

    # Test link for next page
    url = f"""{base_url}{response["links"]["next"]}"""
    # The filters should be present for the links as well
    assert "limit=2" in url
    assert "filter.date=" in url
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": str(env)},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    next_page_versions = version_numbers(response["data"])
    assert next_page_versions == all_versions_in_expected_order[4:6]
    assert response["links"].get("prev") is not None
    assert response["links"].get("next") is not None
    assert response["metadata"] == {"total": 7, "before": 4, "after": 1, "page_size": 2}

    # Test link for previous page
    url = f"""{base_url}{response["links"]["prev"]}"""
    assert "limit=2" in url
    assert "filter.date=" in url
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": str(env)},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    prev_page_versions = version_numbers(response["data"])
    assert prev_page_versions == all_versions_in_expected_order[2:4]
    assert response["links"].get("prev") is not None
    assert response["links"].get("next") is not None
    assert response["metadata"] == {"total": 7, "before": 2, "after": 3, "page_size": 2}

    result = await client.list_desired_state_versions(
        env,
        limit=100,
        sort=f"{order_by_column}.{order}",
        filter={"date": [f"gt:{timestamps[1].astimezone(datetime.timezone.utc)}"]},
    )
    assert result.code == 200
    assert len(result.result["data"]) == 7
    assert version_numbers(result.result["data"]) == all_versions_in_expected_order

    assert result.result["metadata"] == {"total": 7, "before": 0, "after": 0, "page_size": 100}


@pytest.mark.asyncio
async def test_sorting_validation(
    server, client, environments_with_versions: Tuple[Dict[str, uuid.UUID], List[datetime.datetime]]
):
    environments, _ = environments_with_versions
    env = environments["multiple_versions"]
    sort_status_map = {
        "date.desc": 400,
        "date.asc": 400,
        "version.desc": 200,
        "state.desc": 400,
        "total.asc": 400,
        "version": 400,
    }
    for sort, expected_status in sort_status_map.items():
        result = await client.list_desired_state_versions(env, sort=sort)
        assert result.code == expected_status


@pytest.mark.asyncio
async def test_filter_validation(
    server, client, environments_with_versions: Tuple[Dict[str, uuid.UUID], List[datetime.datetime]]
):
    environments, _ = environments_with_versions
    env = environments["multiple_versions"]
    filter_status_map = [
        ("version.desc", 400),
        ({"version": "gt:9000"}, 200),
        ({"version": "le:42", "total": 1}, 400),
        ({"date": "le:42"}, 400),
        ({"version": ["le:42", "gt: 1"]}, 200),
        ({"released": True}, 400),
    ]
    for filter, expected_status in filter_status_map:
        result = await client.list_desired_state_versions(env, filter=filter)
        assert result.code == expected_status


@pytest.mark.asyncio
async def test_promote_no_versions(server, client, environment: str):
    result = await client.promote_desired_state_version(environment, version=1)
    assert result.code == 404


@pytest.mark.parametrize(
    "trigger_method",
    [None, PromoteTriggerMethod.no_push, PromoteTriggerMethod.push_incremental_deploy, PromoteTriggerMethod.push_full_deploy],
)
@pytest.mark.asyncio
async def test_promote_version(server, client, clienthelper, agent, environment: str, trigger_method):
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)
    env_obj = await data.Environment.get_by_id(uuid.UUID(environment))
    await agentmanager.ensure_agent_registered(env=env_obj, nodename="agent1")
    version = await clienthelper.get_version()
    resource_id_wov = "test::Resource[agent1,key=key]"
    resource_id = "%s,v=%d" % (resource_id_wov, version)

    resources = [{"key": "key", "value": "value", "id": resource_id, "requires": [], "purged": False, "send_event": False}]

    await clienthelper.put_version_simple(resources, version)
    result = await client.promote_desired_state_version(environment, version=version, trigger_method=trigger_method)
    assert result.code == 200
    result = await client.list_desired_state_versions(environment)
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert result.result["data"][0]["status"] == "active"
