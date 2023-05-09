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
import logging
import uuid
from operator import itemgetter

import pytest
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from inmanta import const, data
from inmanta.server.config import get_bind_port


@pytest.fixture
async def env_with_logs(client, server, environment):
    cm_times = []
    for i in range(1, 10):
        cm_times.append(datetime.datetime.strptime(f"2021-07-07T10:1{i}:00.0", "%Y-%m-%dT%H:%M:%S.%f"))
    cm_time_idx = 0
    for i in range(1, 10):
        cm = data.ConfigurationModel(
            environment=uuid.UUID(environment),
            version=i,
            date=cm_times[cm_time_idx],
            total=1,
            released=i != 1 and i != 9,
            version_info={},
        )
        cm_time_idx += 1
        await cm.insert()
    msg_timings = []
    for i in range(1, 30):
        msg_timings.append(
            datetime.datetime.strptime("2021-07-07T10:10:00.0", "%Y-%m-%dT%H:%M:%S.%f")
            .replace(minute=i)
            .astimezone(datetime.timezone.utc)
        )
    msg_timings_idx = 0
    for i in range(1, 10):
        action_id = uuid.uuid4()
        resource_action = data.ResourceAction(
            environment=uuid.UUID(environment),
            version=i,
            resource_version_ids=[
                f"std::File[agent1,path=/tmp/file1.txt],v={i}",
                f"std::Directory[agent1,path=/tmp/dir2],v={i}",
            ],
            action_id=action_id,
            action=const.ResourceAction.deploy if i % 2 else const.ResourceAction.pull,
            started=cm_times[i - 1],
        )
        await resource_action.insert()
        if i % 2:
            resource_action.add_logs(
                [
                    data.LogLine.log(
                        logging.INFO,
                        "Successfully stored version %(version)d",
                        version=i,
                        timestamp=msg_timings[msg_timings_idx],
                    ),
                ]
            )
            msg_timings_idx += 1
        else:
            resource_action.add_logs(
                [
                    data.LogLine.log(
                        logging.INFO,
                        "Resource version pulled by client for agent %(agent)s",
                        agent="admin",
                        timestamp=msg_timings[msg_timings_idx],
                    ),
                    data.LogLine.log(
                        logging.DEBUG, "Setting deployed due to known good status", timestamp=msg_timings[msg_timings_idx + 1]
                    ),
                ]
            )
            msg_timings_idx += 2
        await resource_action.save()

    yield environment, msg_timings


@pytest.mark.asyncio
async def test_resource_action_logs_filtering(client, server, env_with_logs):
    """Test the filters for the resource action logs"""
    environment, msg_timings = env_with_logs

    result = await client.resource_logs(environment, "std::File[agent1,path=/tmp/file1.txt]")
    assert result.code == 200
    assert len(result.result["data"]) == 13

    result = await client.resource_logs(
        environment, "std::File[agent1,path=/tmp/file1.txt]", filter={"action": const.ResourceAction.pull}
    )
    assert result.code == 200
    assert len(result.result["data"]) == 8

    result = await client.resource_logs(
        environment, "std::File[agent1,path=/tmp/file1.txt]", filter={"minimal_log_level": "TRACE"}
    )
    assert result.code == 200
    assert len(result.result["data"]) == 13

    result = await client.resource_logs(
        environment, "std::File[agent1,path=/tmp/file1.txt]", filter={"minimal_log_level": "INFO"}
    )
    assert result.code == 200
    assert len(result.result["data"]) == 9

    result = await client.resource_logs(
        environment, "std::File[agent1,path=/tmp/file1.txt]", limit=2, filter={"minimal_log_level": "ERROR"}
    )
    assert result.code == 200
    assert len(result.result["data"]) == 0

    result = await client.resource_logs(
        environment,
        "std::File[agent1,path=/tmp/file1.txt]",
        filter={"timestamp": [f"lt:{msg_timings[5]}", f"ge:{msg_timings[2]}"]},
    )
    assert result.code == 200
    assert len(result.result["data"]) == 3

    result = await client.resource_logs(
        environment, "std::File[agent1,path=/tmp/file1.txt]", filter={"message": ["successful"]}
    )
    assert result.code == 200
    assert len(result.result["data"]) == 5

    result = await client.resource_logs(
        environment, "std::File[agent1,path=/tmp/file1.txt]", filter={"message": ["successful", "good"]}
    )
    assert result.code == 200
    assert len(result.result["data"]) == 9

    result = await client.resource_logs(environment, "std::File[agent1,path=/tmp/file1.txt]", filter={"message": ["error"]})
    assert result.code == 200
    assert len(result.result["data"]) == 0


def log_messages(resource_log_objects):
    return [resource["msg"] for resource in resource_log_objects]


@pytest.mark.parametrize(
    "order_by_column, order",
    [
        ("timestamp", "DESC"),
        ("timestamp", "ASC"),
    ],
)
@pytest.mark.asyncio
async def test_resource_logs_paging(server, client, order_by_column, order, env_with_logs):
    """ Test querying resource logs with paging, using different sorting parameters."""
    environment, msg_timings = env_with_logs

    result = await client.resource_logs(
        environment,
        "std::File[agent1,path=/tmp/file1.txt]",
        filter={"minimal_log_level": "INFO", "timestamp": [f"ge:{msg_timings[2]}"]},
    )
    assert result.code == 200
    assert len(result.result["data"]) == 7
    all_logs_in_expected_order = sorted(result.result["data"], key=itemgetter(order_by_column), reverse=order == "DESC")
    all_log_messages_in_expected_order = log_messages(all_logs_in_expected_order)

    result = await client.resource_logs(
        environment,
        "std::File[agent1,path=/tmp/file1.txt]",
        limit=2,
        sort=f"{order_by_column}.{order}",
        filter={"minimal_log_level": "INFO", "timestamp": [f"ge:{msg_timings[2]}"]},
    )
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert log_messages(result.result["data"]) == all_log_messages_in_expected_order[:2]

    assert result.result["metadata"] == {"total": 7, "before": 0, "after": 5, "page_size": 2}
    assert result.result["links"].get("next") is not None
    assert result.result["links"].get("prev") is None

    port = get_bind_port()
    base_url = "http://localhost:%s" % (port,)
    http_client = AsyncHTTPClient()

    # Test link for next page
    url = f"""{base_url}{result.result["links"]["next"]}"""
    assert "limit=2" in url
    assert "filter.minimal_log_level=INFO" in url
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": environment},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    assert log_messages(response["data"]) == all_log_messages_in_expected_order[2:4]
    assert response["links"].get("prev") is not None
    assert response["links"].get("next") is not None
    assert response["metadata"] == {"total": 7, "before": 2, "after": 3, "page_size": 2}

    # Test link for next page
    url = f"""{base_url}{response["links"]["next"]}"""
    # The filters should be present for the links as well
    assert "limit=2" in url
    assert "filter.minimal_log_level=INFO" in url
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": environment},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    next_page_log_messages = log_messages(response["data"])
    assert next_page_log_messages == all_log_messages_in_expected_order[4:6]
    assert response["links"].get("prev") is not None
    assert response["links"].get("next") is not None
    assert response["metadata"] == {"total": 7, "before": 4, "after": 1, "page_size": 2}

    # Test link for previous page
    url = f"""{base_url}{response["links"]["prev"]}"""
    assert "limit=2" in url
    assert "filter.minimal_log_level=INFO" in url
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": environment},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    prev_page_log_messages = log_messages(response["data"])
    assert prev_page_log_messages == all_log_messages_in_expected_order[2:4]
    assert response["links"].get("prev") is not None
    assert response["links"].get("next") is not None
    assert response["metadata"] == {"total": 7, "before": 2, "after": 3, "page_size": 2}


@pytest.mark.parametrize(
    "sort, expected_status",
    [
        ("date.Desc", 400),
        ("timestamp.asc", 200),
        ("timestamp.dsc", 400),
        ("timestamps", 400),
        ("timestamps.DESC", 400),
        ("timestamp.ASC", 200),
        ("Dates.ASC", 400),
    ],
)
@pytest.mark.asyncio
async def test_sorting_validation(server, client, sort, expected_status, env_with_logs):
    environment, _ = env_with_logs
    result = await client.resource_logs(environment, "std::File[agent1,path=/tmp/file1.txt]", limit=2, sort=sort)
    assert result.code == expected_status


@pytest.mark.parametrize(
    "filter, expected_status",
    [
        ("agents.Desc", 400),
        ({"minimal_log_level": "DEBUG"}, 200),
        ({"minimal_log_level": "info"}, 200),
        ({"minimal_log_level": ["info", "error"]}, 400),
        ({"minimal_log_level": ["danger"]}, 400),
        ({"action": ["deploy", "pull"]}, 200),
        ({"action": ["deploy", "pull", "redeploy"]}, 400),
        ({"message": ["deployed to", "setting"]}, 200),
    ],
)
@pytest.mark.asyncio
async def test_filter_validation(server, client, filter, expected_status, env_with_logs):
    environment, _ = env_with_logs
    result = await client.resource_logs(environment, "std::File[agent1,path=/tmp/file1.txt]", limit=2, filter=filter)
    assert result.code == expected_status


@pytest.mark.asyncio
async def test_log_without_kwargs(server, client, environment):

    await data.ConfigurationModel(
        environment=uuid.UUID(environment),
        version=1,
        date=datetime.datetime.now(),
        total=1,
        released=True,
        version_info={},
    ).insert()

    resource_action = data.ResourceAction(
        environment=uuid.UUID(environment),
        version=1,
        resource_version_ids=[
            "std::File[agent1,path=/tmp/file1.txt],v=1",
            "std::Directory[agent1,path=/tmp/dir2],v=1",
        ],
        action_id=uuid.uuid4(),
        action=const.ResourceAction.deploy,
        started=datetime.datetime.now(),
    )
    await resource_action.insert()

    resource_action.add_logs(
        [
            {
                "level": "INFO",
                "msg": "Setting deployed due to known good status",
                "timestamp": datetime.datetime.now(),
                "args": [],
            }
        ]
    )
    await resource_action.save()
    result = await client.resource_logs(environment, "std::File[agent1,path=/tmp/file1.txt]")
    assert result.code == 200


@pytest.mark.asyncio
async def test_log_nested_kwargs(server, client, environment):

    await data.ConfigurationModel(
        environment=uuid.UUID(environment),
        version=1,
        date=datetime.datetime.now(),
        total=1,
        released=True,
        version_info={},
    ).insert()

    resource_action = data.ResourceAction(
        environment=uuid.UUID(environment),
        version=1,
        resource_version_ids=[
            "std::File[agent1,path=/tmp/file1.txt],v=1",
            "std::Directory[agent1,path=/tmp/dir2],v=1",
        ],
        action_id=uuid.uuid4(),
        action=const.ResourceAction.deploy,
        started=datetime.datetime.now(),
    )
    await resource_action.insert()

    resource_action.add_logs(
        [
            data.LogLine.log(
                logging.INFO,
                "Calling update_resource ",
                timestamp=datetime.datetime.now(),
                changes={"characteristics": {"current": {"Status": "Planned"}, "desired": {"Status": "In Service"}}},
            ),
        ]
    )
    await resource_action.save()
    result = await client.resource_logs(environment, "std::File[agent1,path=/tmp/file1.txt]")
    assert result.code == 200
    assert result.result["data"][0]["kwargs"]["changes"]["characteristics"] == {
        "current": {"Status": "Planned"},
        "desired": {"Status": "In Service"},
    }
