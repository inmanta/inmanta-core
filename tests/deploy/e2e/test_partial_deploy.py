"""
Copyright 2025 Inmanta

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
from collections import defaultdict
from collections.abc import Callable

import pytest

from deploy.scheduler_mocks import DummyManager
from inmanta.util import get_compiler_version
from utils import ClientHelper


def make_shared_set(resource_version=0, size=2, revision=0):
    """
    Helper to build up the shared set resources

    :param resource_version: the version to use in the resource ids
    :param size: number of resources
    :param revision: changing this number changes the resource hash
    """
    return [
        {
            "key": "shared1",
            "value": f"{revision}",
            "id": f"test::Resource[agent1,key=shared1],v={resource_version}",
            "version": resource_version,
            "send_event": True,
            "purged": False,
            "requires": [],
        },
    ] + [
        {
            "key": f"shared{i}",
            "value": f"{i * revision}",
            "id": f"test::Resource[agent1,key=shared{i}],v={resource_version}",
            "version": resource_version,
            "send_event": True,
            "purged": False,
            "requires": [f"test::Resource[agent1,key=shared{i - 1}],v={resource_version}"],
        }
        for i in range(2, size + 1)
    ]


def make_set(
    set_collector: dict[str, object],
    reverse_set_collector: dict[str, set[str]],
    set_id: str,
    resource_version=0,
    revision=0,
    size=5,
):
    """
    Helper to build up the a regular set of resources

    :param set_collector: a dict where all resource will be registed as resourceid->setid
    :param set_id: the name of the resource set
    :param resource_version: the version to use in the resource ids
    :param size: number of resources
    :param revision: changing this number changes the resource hash
    """

    resources = [
        {
            "key": f"{set_id}-{i}",
            "value": f"{revision}",
            "id": f"test::Resource[agent1,key={set_id}-{i}],v={resource_version}",
            "version": resource_version,
            "send_event": True,
            "purged": False,
            "requires": [f"test::Resource[agent1,key={set_id}-{i - 1}],v={resource_version}"] if i != 0 else [],
        }
        for i in range(size)
    ]

    ids = set()

    for i in range(size):
        set_collector[f"test::Resource[agent1,key={set_id}-{i}]"] = set_id
        ids.add(f"test::Resource[agent1,key={set_id}-{i}]")

    reverse_set_collector[set_id] = ids

    return resources


@pytest.fixture(scope="function")
def executor_factory() -> Callable[[uuid.UUID], DummyManager]:
    "mock out the excutor"
    dm_cache = defaultdict(DummyManager)

    def default_executor(environment: uuid.UUID, *args):
        return dm_cache[environment]

    return default_executor


async def test_partial_compile_scenarios_end_to_end(
    agent,
    server,
    project_default,
    executor_factory: Callable[[uuid.UUID], DummyManager],
    environment,
    clienthelper: ClientHelper,
    client,
) -> None:
    # set up a secondary env to detect resource leaking
    result = await client.create_environment(project_id=project_default, name="secondary")
    assert result.code == 200, result
    secondary_env_id = result.result["environment"]["id"]
    secondary_client_helper = ClientHelper(client, secondary_env_id)
    await secondary_client_helper.set_auto_deploy(False)

    # Add one resourceset to secondary
    version = await secondary_client_helper.get_version()
    resources = make_set({}, {}, "all", version, 0)
    await secondary_client_helper.put_version_simple(resources, version)

    async def assert_secondary():
        versions = await client.list_versions(tid=secondary_env_id)
        assert versions.code == 200
        assert len(versions.result["versions"]) == 1
        assert versions.result["versions"][0]["total"] == 5

    await assert_secondary()

    async def put_full(
        version,
        resources,
        set_collector,
        expected_deploy_count,
    ):
        # Put a full version and assert size and nr of resources deployed
        res = await client.put_version(
            tid=environment,
            version=version,
            resources=resources,
            unknowns=[],
            version_info={},
            compiler_version=get_compiler_version(),
            module_version_info={},
            resource_sets=set_collector,
        )
        assert res.code == 200, res.result
        await clienthelper.wait_for_released(version)
        await clienthelper.wait_for_deployed(version)
        executor = executor_factory(uuid.UUID(environment))
        assert executor.executors["agent1"].execute_count == expected_deploy_count
        executor.executors["agent1"].reset_counters()

    async def put_partial(
        resources,
        set_collector,
        expected_deploy_count,
        total_size,
        resource_ids: set[str],
        remove=[],
    ):
        # Put a partial version and assert size and nr of resources deployed
        res = await client.put_partial(
            tid=environment,
            resources=resources,
            unknowns=[],
            version_info={},
            module_version_info={},
            resource_sets=set_collector,
            removed_resource_sets=remove,
        )
        assert res.code == 200, res.result
        version = res.result["data"]
        await clienthelper.wait_for_deployed(version)
        executor = executor_factory(uuid.UUID(environment))
        assert executor.executors["agent1"].execute_count == expected_deploy_count
        for rd in executor.executors["agent1"].seen:
            assert rd.model_version == version

        executor.executors["agent1"].reset_counters()
        # assert total size
        result = await client.resource_list(environment, deploy_summary=True, filter={"status": "!orphaned"})
        assert result.code == 200
        summary = result.result["metadata"]["deploy_summary"]
        assert summary["total"] == total_size

        rids = {r.resource_id for r in result.value()}
        assert resource_ids == rids

    # Put full (with shared set)
    version = await clienthelper.get_version()
    await clienthelper.set_auto_deploy(True)

    set_collector = {}
    all_sets = {}

    resources = (
        make_shared_set(version)
        + make_set(set_collector, all_sets, "set1", version)
        + make_set(set_collector, all_sets, "set2", version)
    )
    # set1 : 5
    # set2 : 5
    # shared : 2
    await put_full(version, resources, set_collector, expected_deploy_count=12)

    # # Update 1 set and push shared
    set_collector = {}
    version = 0
    resources = make_shared_set(version) + make_set(set_collector, all_sets, "set1", version, size=6)
    shared = {"test::Resource[agent1,key=shared1]", "test::Resource[agent1,key=shared2]"}

    # set1 : 6
    # set2 : 5
    # shared : 2
    await put_partial(
        resources,
        set_collector,
        expected_deploy_count=1,
        total_size=13,
        resource_ids=shared.union(all_sets["set1"]).union(all_sets["set2"]),
    )

    # Update 1 set  and push part of shared
    set_collector = {}
    version = 0
    resources = make_shared_set(version, 1) + make_set(set_collector, all_sets, "set2", version, size=6)
    # set1 : 6
    # set2 : 6
    # shared : 2
    await put_partial(
        resources,
        set_collector,
        expected_deploy_count=1,
        total_size=14,
        resource_ids=shared.union(all_sets["set1"]).union(all_sets["set2"]),
    )

    # Update 1 set and add to shared
    set_collector = {}
    version = 0
    shared.add("test::Resource[agent1,key=shared3]")
    resources = make_shared_set(version, 3) + make_set(set_collector, all_sets, "set2", version, size=7)
    # Added one resource to shared, one to set2
    # set1 : 6
    # set2 : 7
    # shared : 3
    await put_partial(
        resources,
        set_collector,
        expected_deploy_count=2,
        total_size=16,
        resource_ids=shared.union(all_sets["set1"]).union(all_sets["set2"]),
    )

    # Update 1 set
    set_collector = {}
    version = 0
    resources = make_set(set_collector, all_sets, "set2", version, size=3, revision=1)
    # set1 : 6
    # set2 : 3
    # shared : 3
    await put_partial(
        resources,
        set_collector,
        expected_deploy_count=3,
        total_size=12,
        resource_ids=shared.union(all_sets["set1"]).union(all_sets["set2"]),
    )

    # put full (remove 1 set, remove from shared )
    set_collector = {}
    version = await clienthelper.get_version()
    resources = make_shared_set(version) + make_set(set_collector, all_sets, "set1", version)
    await put_full(version, resources, set_collector, 0)
    shared = {"test::Resource[agent1,key=shared1]", "test::Resource[agent1,key=shared2]"}
    # set1 : 5
    # shared : 2

    # Update 2 sets / remove 1
    set_collector = {}
    version = 0
    resources = make_set(set_collector, all_sets, "set2", version, revision=1) + make_set(set_collector, all_sets, "set3")
    # set1 : 0
    # set2 : 5
    # set3 : 5
    # shared : 2
    await put_partial(
        resources,
        set_collector,
        expected_deploy_count=10,
        total_size=12,
        remove=["set1"],
        resource_ids=shared.union(all_sets["set3"]).union(all_sets["set2"]),
    )

    await assert_secondary()
