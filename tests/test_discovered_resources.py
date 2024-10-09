"""
    Copyright 2023 Inmanta

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
from typing import Sequence
from urllib import parse

import pytest
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from inmanta.data.model import ResourceVersionIdStr
from inmanta.server.config import get_bind_port


async def test_discovery_resource_single(server, client, agent, environment):
    """
    Test that a discovered resource can be created and retrieved successfully for a single resource.
    """
    discovered_resource_id = "test::Resource[agent1,key=key]"
    discovery_resource_id = "test::DiscoveryResource[agent1,key=key]"
    values = {"value1": "test1", "value2": "test2"}
    result = await agent._client.discovered_resource_create(
        tid=environment,
        discovered_resource_id=discovered_resource_id,
        discovery_resource_id=discovery_resource_id,
        values=values,
    )
    assert result.code == 200

    result = await client.discovered_resources_get(environment, discovered_resource_id)
    assert result.code == 200

    assert result.result["data"]["discovered_resource_id"] == discovered_resource_id
    assert result.result["data"]["discovery_resource_id"] == discovery_resource_id
    assert result.result["data"]["values"] == values

    values = {"value1": "test3", "value2": "test4"}
    # try to store the same resource a second time
    result = await agent._client.discovered_resource_create(
        tid=environment,
        discovered_resource_id=discovered_resource_id,
        discovery_resource_id=discovery_resource_id,
        values=values,
    )
    assert result.code == 200

    result = await client.discovered_resources_get(environment, discovered_resource_id)
    assert result.code == 200

    assert result.result["data"]["discovered_resource_id"] == discovered_resource_id
    assert result.result["data"]["discovery_resource_id"] == discovery_resource_id
    assert result.result["data"]["values"] == values


async def test_discovered_resource_create_batch(server, client, agent, environment):
    """
    Test that a batch of discovered resources can be created
    """

    discovery_resource_id = "test::DiscoveryResource[agent1,key=key]"

    resources = [
        {
            "discovery_resource_id": discovery_resource_id,
            "discovered_resource_id": "test::Resource[agent1,key1=key1]",
            "values": {"value1": "test1", "value2": "test2"},
        },
        {
            "discovery_resource_id": discovery_resource_id,
            "discovered_resource_id": "test::Resource[agent1,key2=key2]",
            "values": {"value1": "test3", "value2": "test4"},
        },
        {
            "discovery_resource_id": discovery_resource_id,
            "discovered_resource_id": "test::Resource[agent1,key3=key3]",
            "values": {"value1": "test5", "value2": "test6"},
        },
    ]
    result = await agent._client.discovered_resource_create_batch(environment, resources)
    assert result.code == 200

    for res in resources:
        result = await client.discovered_resources_get(environment, res["discovered_resource_id"])
        assert result.code == 200
        assert result.result["data"]["discovered_resource_id"] == res["discovered_resource_id"]
        assert result.result["data"]["values"] == res["values"]
        assert result.result["data"]["discovery_resource_id"] == discovery_resource_id

    # try to store the same resources a second time
    resources = [
        {
            "discovery_resource_id": discovery_resource_id,
            "discovered_resource_id": "test::Resource[agent1,key1=key1]",
            "values": {"value1": "test7", "value2": "test8"},
        },
        {
            "discovery_resource_id": discovery_resource_id,
            "discovered_resource_id": "test::Resource[agent1,key2=key2]",
            "values": {"value1": "test9", "value2": "test10"},
        },
        {
            "discovery_resource_id": discovery_resource_id,
            "discovered_resource_id": "test::Resource[agent1,key6=key6]",
            "values": {"value1": "test11", "value2": "test12"},
        },
    ]
    result = await agent._client.discovered_resource_create_batch(environment, resources)
    assert result.code == 200

    for res in resources:
        result = await client.discovered_resources_get(environment, res["discovered_resource_id"])
        assert result.code == 200
        assert result.result["data"]["discovered_resource_id"] == res["discovered_resource_id"]
        assert result.result["data"]["values"] == res["values"]
        assert result.result["data"]["discovery_resource_id"] == discovery_resource_id


async def test_discovered_resource_get_paging(server, client, agent, environment, clienthelper):
    """
    Test that discovered resources can be retrieved with paging. The test creates multiple resources, retrieves them
    with various paging options, and verifies that the expected resources are returned.

    Also test the linking between unmanaged and managed resources and correct filtering via the 'managed' filter i.e.:

    - True: Activate filtering and keep only discovered resources that are managed.
    - False: Activate filtering and keep only discovered resources that are NOT managed.
    - None: Disable filtering: return all discovered resources regardless of whether they're managed.
    """

    # Resource repartition and expected filtering results:

    #                                        |              FILTER
    # discovered    managed   orphaned       |  TRUE        FALSE          NONE
    # ---------------------------------------+-------------------------------------
    #     R1            x                    |   x                           x
    #     R2            x                    |   x                           x
    #     R3                      x          |   x                           x
    #     R4                      x          |   x                           x
    #     R5                                 |                x              x
    #     R6                                 |                x              x

    discovered_resources = []
    discovery_resource_id = "test::DiscoveryResource[agent1,key=key]"

    for i in range(1, 7):
        rid = f"test::Resource[agent1,key{i}=key{i}]"
        discovered_resources.append(
            {
                "discovered_resource_id": rid,
                "values": {"value1": f"test{i}", "value2": f"test{i + 1}"},
                "managed_resource_uri": (
                    f"/api/v2/resource/{parse.quote(rid, safe='')}" if i <= 4 else None
                ),  # Last 2 resources are not known to the orchestrator
                "discovery_resource_id": discovery_resource_id,
            }
        )

    result = await agent._client.discovered_resource_create_batch(environment, discovered_resources)
    assert result.code == 200

    version1 = await clienthelper.get_version()
    orphaned_resources = [
        {
            "id": ResourceVersionIdStr(f"{res['discovered_resource_id']},v={version1}"),
            "values": res["values"],
            "requires": [],
            "purged": False,
            "send_event": False,
        }
        for res in discovered_resources[2:-2]
    ]
    resources = orphaned_resources + [
        {
            "id": ResourceVersionIdStr(f"{discovery_resource_id},v={version1}"),
            "values": {},
            "requires": [],
            "purged": False,
            "send_event": False,
        }
    ]
    await clienthelper.put_version_simple(resources=resources, version=version1)

    # Create some Resources that are already managed:
    version2 = await clienthelper.get_version()
    managed_resources = [
        {
            "id": ResourceVersionIdStr(f"{res['discovered_resource_id']},v={version2}"),
            "values": res["values"],
            "requires": [],
            "purged": False,
            "send_event": False,
        }
        for res in discovered_resources[:2]
    ]
    await clienthelper.put_version_simple(resources=managed_resources, version=version2)

    filter_values = [None, {"managed": True}, {"managed": False}]
    expected_results = [discovered_resources, discovered_resources[:-2], discovered_resources[-2:]]

    def check_expected_result(expected_result: Sequence[dict[str, object]], result: Sequence[dict[str, object]]) -> None:
        """
        Utility function to check that two sequences of dicts are identical. Special care is taken to make
        sure the `discovery_resource_uri` field is properly url-escaped.
        """
        expected_copy = []

        for item in expected_result:
            item_copy = item.copy()

            discovery_id = item_copy["discovery_resource_id"]
            discovery_uri = f"/api/v2/resource/{parse.quote(str(discovery_id), safe='')}"
            item_copy["discovery_resource_uri"] = discovery_uri

            expected_copy.append(item_copy)

        assert expected_copy == result

    for filter, expected_result in zip(filter_values, expected_results):
        result = await client.discovered_resources_get_batch(
            environment,
            filter=filter,
        )
        assert result.code == 200, filter

        check_expected_result(expected_result, result.result["data"])

    result = await client.discovered_resources_get_batch(environment, limit=2)
    assert result.code == 200
    assert len(result.result["data"]) == 2
    check_expected_result(discovered_resources[:2], result.result["data"])

    assert result.result["metadata"] == {"total": 6, "before": 0, "after": 4, "page_size": 2}
    assert result.result["links"].get("next") is not None
    assert result.result["links"].get("prev") is None

    port = get_bind_port()
    base_url = f"http://localhost:{port}"
    http_client = AsyncHTTPClient()

    # Test link for next page
    url = f"""{base_url}{result.result["links"]["next"]}"""
    assert "limit=2" in url
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": environment},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    check_expected_result(discovered_resources[2:4], response["data"])

    assert response["links"].get("prev") is not None
    assert response["links"].get("next") is not None
    assert response["metadata"] == {"total": 6, "before": 2, "after": 2, "page_size": 2}

    # Test link for previous page
    url = f"""{base_url}{response["links"]["prev"]}"""
    assert "limit=2" in url
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": environment},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    check_expected_result(discovered_resources[0:2], response["data"])
    assert response["links"].get("prev") is None
    assert response["links"].get("next") is not None
    assert response["metadata"] == {"total": 6, "before": 0, "after": 4, "page_size": 2}


async def test_discovery_resource_bad_res_id(server, client, agent, environment):
    """
    Test that exceptions are raised when creating discovered resources with invalid resource IDs.
    Tests both creation endpoints (`discovered_resource_create` and `discovered_resource_create_batch`)
    """
    result = await agent._client.discovered_resource_create(
        tid=environment,
        discovered_resource_id="invalid_rid",
        values={"value1": "test1", "value2": "test2"},
        discovery_resource_id="test::DiscoveryResource[agent1,key=key]",
    )

    expected_error_message = (
        "Invalid request: Failed to validate argument\n"
        "1 validation error for LinkedDiscoveredResource\n"
        "discovered_resource_id\n"
        "  Value error, Invalid id for resource invalid_rid "
        "[type=value_error, input_value='invalid_rid', input_type=str]\n"
    )

    assert result.code == 400
    assert expected_error_message in result.result["message"]

    # Check that the discovered_resource_create endpoint requires the discovery_resource_id to be provided
    with pytest.raises(TypeError) as e:
        result = await agent._client.discovered_resource_create(
            tid=environment,
            discovered_resource_id="invalid_rid",
            values={"value1": "test1", "value2": "test2"},
        )
    assert "discovered_resource_create() missing 1 required positional argument: 'discovery_resource_id'" in e.value.args

    result = await agent._client.discovered_resource_create(
        tid=environment,
        discovered_resource_id="test::Resource[agent1,key=key]",
        values={"value1": "test1", "value2": "test2"},
        discovery_resource_id="invalid_rid",
    )
    expected_error_message = (
        "Invalid request: Failed to validate argument\n"
        "1 validation error for LinkedDiscoveredResource\n"
        "discovery_resource_id\n"
        "  Value error, Invalid id for resource invalid_rid "
        "[type=value_error, input_value='invalid_rid', input_type=str]\n"
    )

    assert result.code == 400
    assert expected_error_message in result.result["message"]
    resources = [
        {
            "discovery_resource_id": "test::DiscoveryResource[agent1,key1=key1]",
            "discovered_resource_id": "test::Resource[agent1,key1=key1]",
            "values": {"value1": "test1", "value2": "test2"},
        },
        {
            "discovery_resource_id": "test::DiscoveryResource[agent1,key1=key1]",
            "discovered_resource_id": "invalid_rid",
            "values": {"value1": "test5", "value2": "test6"},
        },
    ]
    result = await agent._client.discovered_resource_create_batch(environment, resources)

    assert result.code == 400
    expected_error_message = (
        "Invalid request: Failed to validate argument\n"
        "1 validation error for discovered_resource_create_batch_arguments\n"
        "discovered_resources.1.discovered_resource_id\n"
        "  Value error, Invalid id for resource invalid_rid "
        "[type=value_error, input_value='invalid_rid', input_type=str]\n"
    )
    assert expected_error_message in result.result["message"]

    resources = [
        {
            "discovery_resource_id": "test::DiscoveryResource[agent1,key1=key1]",
            "discovered_resource_id": "test::Resource[agent1,key1=key1]",
            "values": {"value1": "test1", "value2": "test2"},
        },
        {
            "discovery_resource_id": "invalid_rid",
            "discovered_resource_id": "test::Resource[agent1,key1=key2]",
            "values": {"value1": "test5", "value2": "test6"},
        },
    ]
    result = await agent._client.discovered_resource_create_batch(environment, resources)
    expected_error_message = (
        "Invalid request: Failed to validate argument\n"
        "1 validation error for discovered_resource_create_batch_arguments\n"
        "discovered_resources.1.discovery_resource_id\n"
        "  Value error, Invalid id for resource invalid_rid "
        "[type=value_error, input_value='invalid_rid', input_type=str]\n"
    )
    assert result.code == 400
    assert expected_error_message in result.result["message"]

    resources = [
        {
            "discovered_resource_id": "test::Resource[agent1,key1=key1]",
            "values": {"value1": "test1", "value2": "test2"},
        },
        {
            "discovery_resource_id": "invalid_rid",
            "discovered_resource_id": "test::Resource[agent1,key1=key2]",
            "values": {"value1": "test5", "value2": "test6"},
        },
    ]
    result = await agent._client.discovered_resource_create_batch(environment, resources)

    expected_validation_error_1 = (
        "Invalid request: Failed to validate argument\n"
        "2 validation errors for discovered_resource_create_batch_arguments\n"
        "discovered_resources.0.discovery_resource_id\n"
        "  Field required [type=missing, input_value={'discovered_resource_id'...t1', "
        "'value2': 'test2'}}, input_type=dict]\n"
    )
    expected_validation_error_2 = (
        "discovered_resources.1.discovery_resource_id\n"
        "  Value error, Invalid id for resource invalid_rid "
        "[type=value_error, input_value='invalid_rid', input_type=str]\n"
    )
    assert result.code == 400
    assert expected_validation_error_1 in result.result["message"]
    assert expected_validation_error_2 in result.result["message"]
