"""
Copyright 2019 Inmanta

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

import logging

import pytest

import inmanta.graphql.graphql
from inmanta import const, data
from inmanta.const import AgentAction
from inmanta.server import SLICE_GRAPHQL
from inmanta.types import ResourceIdStr
from utils import get_resource, log_contains, log_doesnt_contain, resource_action_consistency_check, retry_limited


async def test_deploy_trigger(server, client, clienthelper, resource_container, environment, caplog, agent):
    """
    Test deployment of empty model
    """
    caplog.set_level(logging.INFO)

    version = await clienthelper.get_version()

    resources = [
        get_resource(version, agent="agent1"),
        get_resource(version, agent="agent2"),
        get_resource(version, agent="agent3"),
    ]

    await clienthelper.put_version_simple(resources, version)

    result = await client.release_version(environment, version, False)
    assert result.code == 200

    await clienthelper.wait_for_deployed(version)

    # Pause agent3
    result = await client.agent_action(tid=environment, name="agent3", action=AgentAction.pause.name)
    assert result.code == 200

    async def verify(result, a1=0, code=200, warnings=[], agents=None):
        assert result.code == code

        def is_deployed():
            return resource_container.Provider.readcount("agent1", "key1") == a1

        await retry_limited(is_deployed, 1)
        if not agents:
            log_contains(
                caplog,
                "inmanta.scheduler",
                logging.INFO,
                f"All agents got a trigger to run repair for all resources in environment {environment}",
            )
            agents = ["agent1", "agent2", "agent3"]  # this also includes paused agents
        else:
            log_contains(
                caplog,
                "inmanta.scheduler",
                logging.INFO,
                f"Agent agent1 got a trigger to run repair for all resources in environment {environment}",
            )
        log_doesnt_contain(
            caplog,
            "inmanta.scheduler",
            logging.INFO,
            f"Agent agent5 got a trigger to run repair for all resources in environment {environment}",
        )

        assert result.result["agents"] == agents
        if warnings:
            assert sorted(result.result["metadata"]["warnings"]) == sorted(warnings)
        caplog.clear()

    async def verify_failed(result, code=400, message="", warnings=["Could not reach agents named [agent2,agent3]"]):
        assert result.code == code

        log_doesnt_contain(caplog, "agent", logging.INFO, "got a trigger to update")
        if warnings:
            assert sorted(result.result["metadata"]["warnings"]) == sorted(warnings)
        assert result.result["message"] == message
        caplog.clear()

    # normal
    result = await client.deploy(environment)
    await verify(result, a1=2)

    # only agent1
    result = await client.deploy(environment, agents=["agent1"])
    await verify(result, agents=["agent1"], a1=3)

    # only agent5 (not in model)
    result = await client.deploy(environment, agents=["agent5"])
    await verify_failed(result, 404, "No agent could be reached", warnings=[])

    # All of it
    result = await client.deploy(environment, agents=["agent1", "agent2", "agent5"])
    await verify(
        result,
        a1=4,
        agents=["agent1", "agent2"],
        warnings=["Model version 1 does not contain agents named [agent5]"],
    )


@pytest.mark.parametrize(
    "agent_repair_interval",
    [
        "2",
        "*/2 * * * * * *",
    ],
)
async def test_spontaneous_repair(server, client, agent, resource_container, environment, clienthelper, agent_repair_interval):
    """
    Test that a repair run is executed every 2 seconds in the new agent
     as specified in the agent_repair_interval (using a cron or not)
    """
    resource_container.Provider.reset()
    env_id = environment

    result = await client.set_setting(environment, data.AUTOSTART_AGENT_REPAIR_INTERVAL, agent_repair_interval)
    assert result.code == 200
    # Disable deploys
    result = await client.set_setting(environment, data.AUTOSTART_AGENT_DEPLOY_INTERVAL, 0)
    assert result.code == 200

    timer_manager = agent.scheduler._timer_manager
    await timer_manager.initialize()

    version = await clienthelper.get_version()

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "purged": False,
            "send_event": False,
            "requires": [],
        },
    ]

    await clienthelper.put_version_simple(resources, version)

    # do a deploy
    result = await client.release_version(
        tid=env_id, id=version, agent_trigger_method=const.AgentTriggerMethod.push_full_deploy
    )
    assert result.code == 200
    assert result.result["model"]["released"]

    result = await client.get_version(env_id, version)
    assert result.code == 200

    await clienthelper.wait_full_success()

    async def verify_deployment_result():
        # A repair run may put one resource from the deployed state to the deploying state.
        assert len(resources) - 1 <= await clienthelper.done_count() <= len(resources)

        assert resource_container.Provider.isset("agent1", "key1")
        assert resource_container.Provider.get("agent1", "key1") == "value1"

    await verify_deployment_result()

    # Manual change
    resource_container.Provider.set("agent1", "key1", "another_value")

    # Wait until repair restores the state
    def repaired() -> bool:
        return resource_container.Provider.get("agent1", "key1") == "value1"

    await retry_limited(repaired, 10)

    await verify_deployment_result()
    await resource_action_consistency_check()


async def test_deploy_filtered(server, client, clienthelper, resource_container, environment, agent):
    """
    End-to-end test of the deploy_filtered endpoint: a deploy/repair triggered on a resource filter operates on
    exactly the resources matching the filter (the same set the GraphQL `resources` query returns). Covers a repair
    (full deploy) on a filter, targeting a single resource, incremental-deploy semantics, and validation errors.
    """
    version = await clienthelper.get_version()
    resources = [
        get_resource(version, key="key1", agent="agent1"),
        get_resource(version, key="key2", agent="agent1"),
        get_resource(version, key="key1", agent="agent2"),
        get_resource(version, key="key2", agent="agent2"),
    ]
    await clienthelper.put_version_simple(resources, version)
    result = await client.release_version(environment, version, True)
    assert result.code == 200
    await clienthelper.wait_for_deployed(version)

    r_a1_k1 = ResourceIdStr("test::Resource[agent1,key=key1]")
    r_a1_k2 = ResourceIdStr("test::Resource[agent1,key=key2]")
    r_a2_k1 = ResourceIdStr("test::Resource[agent2,key=key1]")

    for agent_name in ("agent1", "agent2"):
        for key in ("key1", "key2"):
            assert resource_container.Provider.readcount(agent_name, key) == 1

    # repair (full deploy) filtered by agent1: both agent1 resources redeploy even though compliant; agent2 untouched
    result = await client.deploy_filtered(
        environment, filter={"agent": {"eq": ["agent1"]}}, agent_trigger_method=const.AgentTriggerMethod.push_full_deploy
    )
    assert result.code == 200, result.result
    assert sorted(result.result["data"]) == sorted([r_a1_k1, r_a1_k2])
    await retry_limited(
        lambda: resource_container.Provider.readcount("agent1", "key1") == 2
        and resource_container.Provider.readcount("agent1", "key2") == 2,
        10,
    )
    assert resource_container.Provider.readcount("agent2", "key1") == 1
    assert resource_container.Provider.readcount("agent2", "key2") == 1

    # target a single resource: resourceType + agent + resourceIdValue uniquely identify test::Resource[agent2,key=key1]
    result = await client.deploy_filtered(
        environment,
        filter={
            "resourceType": {"eq": ["test::Resource"]},
            "agent": {"eq": ["agent2"]},
            "resourceIdValue": {"eq": ["key1"]},
        },
        agent_trigger_method=const.AgentTriggerMethod.push_full_deploy,
    )
    assert result.code == 200, result.result
    assert result.result["data"] == [r_a2_k1]
    await retry_limited(lambda: resource_container.Provider.readcount("agent2", "key1") == 2, 10)
    assert resource_container.Provider.readcount("agent2", "key2") == 1  # not matched by the filter

    # make agent1/key1 fail its next deploy so it becomes dirty (non-compliant)
    resource_container.Provider.set_fail("agent1", "key1", 1)
    result = await client.deploy_filtered(
        environment, filter={"agent": {"eq": ["agent1"]}}, agent_trigger_method=const.AgentTriggerMethod.push_full_deploy
    )
    assert result.code == 200
    await retry_limited(
        lambda: resource_container.Provider.readcount("agent1", "key1") == 3  # attempted, failed -> dirty
        and resource_container.Provider.readcount("agent1", "key2") == 3,  # repaired, compliant
        10,
    )

    # incremental deploy filtered by agent1: only the dirty resource (key1) is redeployed, not the compliant key2
    result = await client.deploy_filtered(
        environment,
        filter={"agent": {"eq": ["agent1"]}},
        agent_trigger_method=const.AgentTriggerMethod.push_incremental_deploy,
    )
    assert result.code == 200
    assert sorted(result.result["data"]) == sorted([r_a1_k1, r_a1_k2])  # the matched set is reported regardless
    await retry_limited(lambda: resource_container.Provider.readcount("agent1", "key1") == 4, 10)
    assert resource_container.Provider.readcount("agent1", "key2") == 3  # compliant, not dirty -> not redeployed

    # enum filter
    result = await client.deploy_filtered(environment, filter={"blocked": {"eq": ["NOT_BLOCKED"]}})
    assert result.code == 200, result.result
    assert sorted(result.result["data"]) == sorted(
        [r_a1_k1, r_a1_k2, r_a2_k1, ResourceIdStr("test::Resource[agent2,key=key2]")]
    )

    # StrFilter contains
    result = await client.deploy_filtered(environment, filter={"agent": {"contains": ["%1"]}})
    assert result.code == 200, result.result
    assert sorted(result.result["data"]) == sorted([r_a1_k1, r_a1_k2])

    # null values allowed
    all_resources = sorted([r_a1_k1, r_a1_k2, r_a2_k1, ResourceIdStr("test::Resource[agent2,key=key2]")])
    result = await client.deploy_filtered(environment, filter={"agent": None})
    assert result.code == 200, result.result
    assert sorted(result.result["data"]) == all_resources

    # the same one level down, on an operator object
    result = await client.deploy_filtered(environment, filter={"agent": {"eq": None}})
    assert result.code == 200, result.result
    assert sorted(result.result["data"]) == all_resources

    # validation: the list items are the only non-nullable position in the filter -> 400
    result = await client.deploy_filtered(environment, filter={"agent": {"eq": [None]}})
    assert result.code == 400, result.result

    # validation: an enum value that does not exist -> 400
    result = await client.deploy_filtered(environment, filter={"blocked": {"eq": ["NOT_AN_ENUM_VALUE"]}})
    assert result.code == 400, result.result

    # validation: unknown filter field -> 400 (rejected by GraphQL input coercion)
    result = await client.deploy_filtered(environment, filter={"doesNotExist": {"eq": ["x"]}})
    assert result.code == 400, result.result

    # validation: bad operator on a string filter -> 400 (rejected by GraphQL input coercion)
    result = await client.deploy_filtered(environment, filter={"agent": {"badOp": ["x"]}})
    assert result.code == 400, result.result

    # validation: a string where a boolean is expected -> 400
    result = await client.deploy_filtered(environment, filter={"purged": "yes"})
    assert result.code == 400, result.result

    # validation: a scalar where a nested operator object is expected -> 400
    result = await client.deploy_filtered(environment, filter={"agent": "agent1"})
    assert result.code == 400, result.result

    # validation: environment must not be in the body (it is the tid) -> 400
    result = await client.deploy_filtered(environment, filter={"environment": environment})
    assert result.code == 400, result.result

    # validation: deploy acts on the current desired state, so orphans and a pinned version are rejected -> 400
    result = await client.deploy_filtered(environment, filter={"isOrphan": True})
    assert result.code == 400, result.result
    assert "orphan" in result.result["message"].lower()
    result = await client.deploy_filtered(environment, filter={"modelVersion": 1})
    assert result.code == 400, result.result


async def test_deploy_filtered_pages(server, client, clienthelper, resource_container, environment, agent, monkeypatch) -> None:
    """
    The GraphQL query behind deploy_filtered is paged. With a page size below the number of matching resources, every
    match is still reported exactly once, i.e. the cursor is threaded correctly and the loop terminates.
    """
    # force real paging: 4 matching resources over pages of 2
    monkeypatch.setattr(inmanta.graphql.graphql, "RESOURCE_PAGE_SIZE_INTERNAL", 2)

    # count the queries, so that this test fails if the endpoint ever stops paging rather than silently passing
    graphql_slice = server.get_slice(SLICE_GRAPHQL)
    execute_query = graphql_slice._execute_query
    queries: list[str] = []

    async def counting_execute_query(query, variables=None, operation_name=None):
        queries.append(query)
        return await execute_query(query, variables=variables, operation_name=operation_name)

    monkeypatch.setattr(graphql_slice, "_execute_query", counting_execute_query)

    version = await clienthelper.get_version()
    resources = [
        get_resource(version, key="key1", agent="agent1"),
        get_resource(version, key="key2", agent="agent1"),
        get_resource(version, key="key3", agent="agent1"),
        get_resource(version, key="key1", agent="agent2"),
        get_resource(version, key="key2", agent="agent2"),
    ]
    await clienthelper.put_version_simple(resources, version)
    result = await client.release_version(environment, version, True)
    assert result.code == 200
    await clienthelper.wait_for_deployed(version)

    all_resources = [
        ResourceIdStr("test::Resource[agent1,key=key1]"),
        ResourceIdStr("test::Resource[agent1,key=key2]"),
        ResourceIdStr("test::Resource[agent1,key=key3]"),
        ResourceIdStr("test::Resource[agent2,key=key1]"),
        ResourceIdStr("test::Resource[agent2,key=key2]"),
    ]

    # an empty filter matches everything, so this spans more than one page
    queries.clear()
    result = await client.deploy_filtered(environment)
    assert result.code == 200, result.result
    assert sorted(result.result["data"]) == sorted(all_resources)
    # no duplicates: the ids are collected in a set, but a mis-threaded cursor would re-report the first page
    assert len(result.result["data"]) == len(all_resources)
    assert len(queries) == 3, "expected the endpoint to page through the results"

    # a filter matching a subset pages as well: 2 matches over pages of 3
    queries.clear()
    result = await client.deploy_filtered(environment, filter={"agent": {"eq": ["agent1"]}})
    assert result.code == 200, result.result
    assert sorted(result.result["data"]) == sorted(all_resources[:3])
    assert len(queries) == 2, "expected the endpoint to page through the results"


async def test_deploy_filtered_excludes_orphans(server, client, clienthelper, resource_container, environment, agent) -> None:
    """
    A deploy acts on the current desired state, so orphaned resources are never selected, not even by a filter that
    does not mention `isOrphan` at all. deploy_filtered pins the filter to non-orphans on the caller's behalf.
    """
    # version 1 manages both resources
    version = await clienthelper.get_version()
    await clienthelper.put_version_simple(
        [get_resource(version, key="key1", agent="agent1"), get_resource(version, key="key2", agent="agent1")], version
    )
    result = await client.release_version(environment, version, True)
    assert result.code == 200
    await clienthelper.wait_for_deployed(version)

    # version 2 drops key2, which makes it an orphan once the scheduler has processed the new version
    version = await clienthelper.get_version()
    await clienthelper.put_version_simple([get_resource(version, key="key1", agent="agent1")], version)
    result = await client.release_version(environment, version, True)
    assert result.code == 200
    await clienthelper.wait_for_deployed(version)

    managed = ResourceIdStr("test::Resource[agent1,key=key1]")

    # no filter at all: the orphan is excluded regardless
    result = await client.deploy_filtered(environment)
    assert result.code == 200, result.result
    assert result.result["data"] == [managed]

    # an explicit isOrphan: false says the same thing and is accepted
    result = await client.deploy_filtered(environment, filter={"isOrphan": False})
    assert result.code == 200, result.result
    assert result.result["data"] == [managed]


async def test_deploy_filtered_openapi(server, client):
    """
    The deploy_filtered filter body is documented in OpenAPI from the GraphQL ResourceFilter: an object with the
    filter fields (camelCase, including the extension-composed `modelVersion`), and without `environment` (the tid).
    """
    result = await client.get_api_docs(format=const.ApiDocsFormat.openapi)
    assert result.code == 200
    openapi = result.result["data"]
    operation = openapi["paths"]["/api/v2/deploy_filtered"]["post"]
    body_schema = operation["requestBody"]["content"]["application/json"]["schema"]
    filter_schema = body_schema["properties"]["filter"]
    # filter is Optional -> anyOf[object, null]; pick the object branch
    variants = filter_schema.get("anyOf", [filter_schema])
    object_schema = next(variant for variant in variants if variant.get("type") == "object")
    properties = object_schema["properties"]
    assert "agent" in properties
    assert "resourceType" in properties
    assert "isOrphan" in properties
    assert "modelVersion" in properties  # composed into ResourceFilter by #10530, surfaces without any endpoint change
    assert "environment" not in properties  # supplied as the tid, not in the body
