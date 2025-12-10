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

import itertools
import json
from collections.abc import Mapping, Sequence
from urllib import parse

from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from inmanta.server import config
from inmanta.types import ResourceVersionIdStr


async def test_discovery_resource_single(server, client, agent, environment):
    """
    Test that a discovered resource can be created/retrieved and deleted successfully for a single resource.
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

    result = await client.discovered_resource_delete(environment, discovered_resource_id)
    assert result.code == 200

    result = await client.discovered_resources_get(environment, discovered_resource_id)
    assert result.code == 404

    result = await client.discovered_resource_delete(environment, discovered_resource_id)
    assert result.code == 404
    assert f"Discovered Resource with id {discovered_resource_id} not found in env {environment}" in result.result["message"]


async def test_discovered_resource_batch(server, client, agent, environment):
    """
    Test that a batch of discovered resources can be created and deleted
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

    resources_to_delete = ["test::Resource[agent1,key1=key1]", "test::Resource[agent1,key2=key2]"]

    result = await client.discovered_resource_delete_batch(environment, resources_to_delete)
    assert result.code == 200

    for res in resources_to_delete:
        result = await client.discovered_resources_get(environment, res)
        assert result.code == 404

    # Assert that not all resources were deleted
    result = await client.discovered_resources_get(environment, "test::Resource[agent1,key6=key6]")
    assert result.code == 200

    # Deleting non-existent resources will not cause an error
    result = await client.discovered_resource_delete_batch(environment, resources_to_delete)
    assert result.code == 200

    resources_to_delete.append("test::Resource[agent1,key6=key6]")

    # test::Resource[agent1,key6=key6] will still get deleted
    result = await client.discovered_resource_delete_batch(environment, resources_to_delete)
    assert result.code == 200

    result = await client.discovered_resources_get(environment, "test::Resource[agent1,key6=key6]")
    assert result.code == 404


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

    #                                        |          FILTER.managed
    # discovered    managed   orphaned       |  TRUE        FALSE          NONE
    # ---------------------------------------+-------------------------------------
    #     R1            x                    |   x                           x
    #     R2            x                    |   x                           x
    #     R3                      x          |   x                           x
    #     R4                      x          |   x                           x
    #     R5                                 |                x              x
    #     R6                                 |                x              x
    #     O1            x                    |   x                           x
    #     O2            x                    |   x                           x
    #     O3                      x          |   x                           x
    #     O4                      x          |   x                           x
    #     O5                                 |                x              x
    #     O6                                 |                x              x

    await clienthelper.set_auto_deploy(auto=True)
    discovery_resource_id: str = "test::DiscoveryResource[agent1,key=key]"
    discovered_resources: list[Mapping[str, object]] = []
    orphan_version = await clienthelper.get_version()
    managed_version = orphan_version + 1
    orphaned_resources: list[Mapping[str, object]] = [
        {
            "id": ResourceVersionIdStr(f"{discovery_resource_id},v={orphan_version}"),
            "values": {},
            "requires": [],
            "purged": False,
            "send_event": False,
        }
    ]
    managed_resources: list[Mapping[str, object]] = [
        {**orphaned_resources[0], "id": ResourceVersionIdStr(f"{discovery_resource_id},v={managed_version}")}
    ]

    for res_type, i in itertools.product(("OtherResource", "Resource"), range(1, 7)):
        agent_name: str = "agent1" if i <= 3 else "agent2"
        rid = f"test::{res_type}[{agent_name},key{i}=key{i}]"
        values = {"value1": f"test{i}", "value2": f"test{i + 1}"}
        discovered_resources.append(
            {
                "discovered_resource_id": rid,
                "resource_type": f"test::{res_type}",
                "agent": agent_name,
                "resource_id_value": f"key{i}",
                "values": values,
                "managed_resource_uri": (
                    f"/api/v2/resource/{parse.quote(rid, safe='')}" if i <= 4 else None
                ),  # Last 2 resources are not known to the orchestrator
                "discovery_resource_id": discovery_resource_id,
            }
        )
        if i <= 2:
            managed_resources.append(
                {
                    "id": ResourceVersionIdStr(f"{rid},v={managed_version}"),
                    "values": values,
                    "requires": [],
                    "purged": False,
                    "send_event": False,
                }
            )
        elif i <= 4:
            orphaned_resources.append(
                {
                    "id": ResourceVersionIdStr(f"{rid},v={orphan_version}"),
                    "values": {},
                    "requires": [],
                    "purged": False,
                    "send_event": False,
                }
            )

    # report the discovered resources
    await agent._client.discovered_resource_create_batch(environment, discovered_resources).value()
    # create the to-orphan version
    await clienthelper.put_version_simple(resources=orphaned_resources, version=orphan_version, wait_for_released=True)
    # Create the new version with the managed resources
    version2 = await clienthelper.get_version()
    assert managed_version == version2  # assert assumption made above to construct rvids
    await clienthelper.put_version_simple(resources=managed_resources, version=managed_version, wait_for_released=True)

    filter_values = [
        # managed
        None,
        {"managed": True},
        {"managed": False},
        # resource type
        {"resource_type": "Resource"},  # partial match => all
        {"resource_type": "t::Resource"},
        {"resource_type": "OtherResource"},
        # agent
        {"agent": "agent"},  # partial match => all
        {"agent": "agent1"},
        {"agent": "agent2"},
        # rid value
        {"resource_id_value": "key"},  # partial match => all
        {"resource_id_value": "2"},
    ]
    expected_results = [
        # managed
        discovered_resources,
        discovered_resources[:4] + discovered_resources[6:-2],
        discovered_resources[4:6] + discovered_resources[-2:],
        # resource type
        discovered_resources,
        discovered_resources[6:],
        discovered_resources[:6],
        # agent
        discovered_resources,
        discovered_resources[:3] + discovered_resources[6:-3],
        discovered_resources[3:6] + discovered_resources[-3:],
        # rid value
        discovered_resources,
        [discovered_resources[1], discovered_resources[7]],
    ]

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

    assert result.result["metadata"] == {"total": 12, "before": 0, "after": 10, "page_size": 2}
    assert result.result["links"].get("next") is not None
    assert result.result["links"].get("prev") is None

    port = config.server_bind_port.get()
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
    assert response["metadata"] == {"total": 12, "before": 2, "after": 8, "page_size": 2}

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
    assert response["metadata"] == {"total": 12, "before": 0, "after": 10, "page_size": 2}


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
        "1 validation error for DiscoveredResourceInput\n"
        "discovered_resource_id\n"
        "  Value error, Invalid id for resource invalid_rid "
        "[type=value_error, input_value='invalid_rid', input_type=str]\n"
    )

    assert result.code == 400
    assert expected_error_message in result.result["message"]

    # Check that the discovered_resource_create endpoint requires the discovery_resource_id to be provided
    result = await agent._client.discovered_resource_create(
        tid=environment,
        discovered_resource_id="invalid_rid",
        values={"value1": "test1", "value2": "test2"},
    )
    assert result.code == 400
    assert "Invalid request: Field 'discovery_resource_id' is required." in result.result["message"]

    result = await agent._client.discovered_resource_create(
        tid=environment,
        discovered_resource_id="test::Resource[agent1,key=key]",
        values={"value1": "test1", "value2": "test2"},
        discovery_resource_id="invalid_rid",
    )
    expected_error_message = (
        "Invalid request: Failed to validate argument\n"
        "1 validation error for DiscoveredResourceInput\n"
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
