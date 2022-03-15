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

from inmanta import const, data
from inmanta.server import SLICE_NOTIFICATION
from inmanta.server.config import get_bind_port


@pytest.fixture
async def environment_with_notifications(server, environment: str):
    env_id = uuid.UUID(environment)

    for i in range(8):
        created = (datetime.datetime.now().astimezone() - datetime.timedelta(days=1)).replace(hour=i)
        await data.Notification(
            title="Notification" if i % 2 else "Error",
            message="Something happened" if i % 2 else "Something bad happened",
            environment=env_id,
            severity=const.NotificationSeverity.message if i % 2 else const.NotificationSeverity.error,
            uri="/api/v2/notification",
            created=created.astimezone(),
            read=i in {2, 4},
            cleared=i in {4, 5},
        ).insert()

    yield environment


async def test_filters(environment_with_notifications, client):
    environment = environment_with_notifications
    result = await client.list_notifications(uuid.uuid4())
    assert result.code == 404

    result = await client.list_notifications(environment)
    assert result.code == 200
    assert len(result.result["data"]) == 8

    result = await client.list_notifications(environment, filter={"read": False})
    assert result.code == 200
    assert len(result.result["data"]) == 6
    assert all(not notification["read"] for notification in result.result["data"])

    result = await client.list_notifications(environment, filter={"read": True})
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert all(notification["read"] for notification in result.result["data"])

    result = await client.list_notifications(environment, filter={"read": False, "cleared": False})
    assert result.code == 200
    assert len(result.result["data"]) == 5
    assert all(not notification["read"] for notification in result.result["data"])
    assert all(not notification["cleared"] for notification in result.result["data"])

    result = await client.list_notifications(environment, filter={"title": "Error"})
    assert result.code == 200
    assert len(result.result["data"]) == 4

    result = await client.list_notifications(environment, filter={"message": "Bad"})
    assert result.code == 200
    assert len(result.result["data"]) == 4

    result = await client.list_notifications(environment, filter={"severity": "message"})
    assert result.code == 200
    assert len(result.result["data"]) == 4
    assert all(notification["severity"] == "message" for notification in result.result["data"])

    result = await client.list_notifications(environment, filter={"severity": "error"})
    assert result.code == 200
    assert len(result.result["data"]) == 4
    assert all(notification["severity"] == "error" for notification in result.result["data"])


def notification_ids(notification_objects):
    return [notification["id"] for notification in notification_objects]


@pytest.mark.parametrize(
    "order",
    [
        "DESC",
        "ASC",
    ],
)
async def test_notifications_paging(server, client, environment_with_notifications, order):
    environment = environment_with_notifications
    order_by_column = "created"

    result = await client.list_notifications(
        environment,
        filter={
            "read": False,
        },
    )
    assert result.code == 200
    assert len(result.result["data"]) == 6

    all_notifications_in_expected_order = sorted(
        result.result["data"], key=itemgetter(order_by_column, "id"), reverse=order == "DESC"
    )
    all_notification_ids_in_expected_order = notification_ids(all_notifications_in_expected_order)

    result = await client.list_notifications(
        environment,
        limit=2,
        sort=f"{order_by_column}.{order}",
        filter={
            "read": False,
        },
    )
    assert result.code == 200
    assert len(result.result["data"]) == 2

    assert notification_ids(result.result["data"]) == all_notification_ids_in_expected_order[:2]

    assert result.result["metadata"] == {"total": 6, "before": 0, "after": 4, "page_size": 2}
    assert result.result["links"].get("next") is not None
    assert result.result["links"].get("prev") is None

    port = get_bind_port()
    base_url = "http://localhost:%s" % (port,)
    http_client = AsyncHTTPClient()

    # Test link for next page
    url = f"""{base_url}{result.result["links"]["next"]}"""
    assert "limit=2" in url
    assert "filter.read=" in url
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": str(environment)},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    assert notification_ids(response["data"]) == all_notification_ids_in_expected_order[2:4]
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
    assert notification_ids(response["data"]) == all_notification_ids_in_expected_order[4:]
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
    assert notification_ids(response["data"]) == all_notification_ids_in_expected_order[2:4]
    assert response["links"].get("prev") is not None
    assert response["links"].get("next") is not None
    assert response["metadata"] == {"total": 6, "before": 2, "after": 2, "page_size": 2}

    result = await client.list_notifications(
        environment,
        limit=6,
        sort=f"{order_by_column}.{order}",
        filter={
            "read": False,
        },
    )
    assert result.code == 200
    assert len(result.result["data"]) == 6
    assert notification_ids(result.result["data"]) == all_notification_ids_in_expected_order

    assert result.result["metadata"] == {"total": 6, "before": 0, "after": 0, "page_size": 6}


async def test_update_read_cleared(environment_with_notifications, client) -> None:
    environment = environment_with_notifications

    result = await client.list_notifications(environment, filter={"read": False})
    assert result.code == 200
    assert len(result.result["data"]) == 6
    notification_id = result.result["data"][0]["id"]

    result = await client.update_notification(uuid.uuid4(), notification_id, read=True)
    assert result.code == 404
    result = await client.update_notification(environment, uuid.uuid4(), read=True)
    assert result.code == 404

    result = await client.update_notification(environment, notification_id, read=True)
    assert result.code == 200
    assert result.result["data"]["read"]
    result = await client.list_notifications(environment, filter={"read": False})
    assert result.code == 200
    assert len(result.result["data"]) == 5
    assert notification_id not in notification_ids(result.result["data"])

    result = await client.update_notification(environment, notification_id, cleared=True)
    assert result.code == 200
    result = await client.get_notification(environment, notification_id)
    assert result.code == 200
    assert result.result["data"]["cleared"]

    result = await client.list_notifications(environment, filter={"cleared": False})
    assert result.code == 200
    assert notification_id not in notification_ids(result.result["data"])

    result = await client.update_notification(environment, notification_id, read=False)
    assert result.code == 200
    assert not result.result["data"]["read"]
    result = await client.list_notifications(environment, filter={"read": False})
    assert result.code == 200
    assert len(result.result["data"]) == 6
    assert notification_id in notification_ids(result.result["data"])

    result = await client.update_notification(environment, notification_id, read=True, cleared=False)
    assert result.code == 200
    assert result.result["data"]["read"]
    assert not result.result["data"]["cleared"]
    result = await client.list_notifications(environment, filter={"read": False})
    assert result.code == 200
    assert notification_id not in notification_ids(result.result["data"])
    result = await client.list_notifications(environment, filter={"cleared": False})
    assert result.code == 200
    assert notification_id in notification_ids(result.result["data"])

    result = await client.get_notification(environment, uuid.uuid4())
    assert result.code == 404

    # Empty update is invalid
    result = await client.update_notification(environment, notification_id)
    assert result.code == 400


async def test_internal_api(environment: str, server, client) -> None:
    notificationservice = server.get_slice(SLICE_NOTIFICATION)
    result = await client.list_notifications(environment)
    assert result.code == 200
    assert len(result.result["data"]) == 0

    await notificationservice.notify(uuid.UUID(environment), title="Title", message="test message", uri="/api/v2/notification")
    result = await client.list_notifications(environment)
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert result.result["data"][0]["severity"] == "message"
    assert not result.result["data"][0]["read"]
    assert not result.result["data"][0]["cleared"]
    await notificationservice.notify(
        uuid.UUID(environment),
        title="Title",
        message="warning message",
        severity=const.NotificationSeverity.warning,
        uri="/api/v2/notification",
    )
    result = await client.list_notifications(environment)
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert result.result["data"][0]["severity"] == "warning"
    assert not result.result["data"][0]["read"]
    assert not result.result["data"][0]["cleared"]


async def test_notifications_deleted_when_env_deleted(environment_with_notifications, client) -> None:
    environment = environment_with_notifications

    result = await client.list_notifications(environment)
    assert result.code == 200
    assert len(result.result["data"]) == 8
    result = await client.environment_delete(environment)
    assert result.code == 200
    result = await client.list_notifications(environment)
    assert result.code == 404
    notifications_in_db = await data.Notification.get_list()
    assert len(notifications_in_db) == 0


async def test_notifications_deleted_when_env_cleared(environment_with_notifications, client) -> None:
    environment = environment_with_notifications

    result = await client.list_notifications(environment)
    assert result.code == 200
    assert len(result.result["data"]) == 8
    result = await client.environment_clear(environment)
    assert result.code == 200
    result = await client.list_notifications(environment)
    assert result.code == 200
    assert len(result.result["data"]) == 0
