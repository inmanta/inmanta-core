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

import datetime
import logging
import uuid

import pytest

import inmanta.data.sqlalchemy as models
from inmanta import const, data
from inmanta.data import model
from inmanta.deploy import state
from inmanta.graphql.schema import to_snake_case
from inmanta.server import SLICE_COMPILER
from inmanta.server.services.compilerservice import CompilerService
from inmanta.util import retry_limited
from utils import insert_with_link_to_configuration_model, run_compile_and_wait_until_compile_is_done


@pytest.fixture
async def setup_database(project_default, server, client):
    id_env_1 = uuid.UUID("11111111-1234-5678-1234-000000000001")
    result = await client.environment_create(
        project_id=project_default,
        name="test-env-b",
        environment_id=id_env_1,
    )
    assert result.code == 200

    id_env_2 = uuid.UUID("11111111-1234-5678-1234-000000000002")
    result = await client.environment_create(
        project_id=project_default,
        name="test-env-c",
        environment_id=id_env_2,
    )
    assert result.code == 200

    id_env_3 = uuid.UUID("11111111-1234-5678-1234-000000000003")
    result = await client.environment_create(
        project_id=project_default,
        name="test-env-a",
        environment_id=id_env_3,
    )
    assert result.code == 200
    result = await client.halt_environment(id_env_3)
    assert result.code == 200

    def add_notifications(env_id: uuid.UUID) -> list[models.Notification]:
        notifications = []
        for i in range(8):
            created = (datetime.datetime.now().astimezone() - datetime.timedelta(days=1)).replace(hour=i)
            notifications.append(
                models.Notification(
                    id=uuid.uuid4(),
                    title="Notification" if i % 2 else "Error",
                    message="Something happened" if i % 2 else "Something bad happened",
                    environment=env_id,
                    severity=const.NotificationSeverity.message if i % 2 else const.NotificationSeverity.error,
                    uri="/api/v2/notification",
                    created=created.astimezone(),
                    read=i in {2, 4},
                    cleared=i in {4, 5},
                )
            )
        return notifications

    # Add notifications
    async with data.get_session() as session:
        session.add_all([*add_notifications(id_env_1), *add_notifications(id_env_2)])
        await session.commit()
        await session.flush()

    resource_set_per_version: dict[int, data.ResourceSet] = {}
    cm_times = {}
    for i in range(1, 10):
        cm_times[i] = datetime.datetime.strptime(f"2021-07-07T10:1{i}:00.0", "%Y-%m-%dT%H:%M:%S.%f")
        cm = data.ConfigurationModel(
            environment=id_env_1,
            version=i,
            date=cm_times[i],
            total=1,
            released=i != 1 and i != 9,
            version_info={},
            is_suitable_for_partial_compiles=False,
        )
        await cm.insert()

        resource_set = data.ResourceSet(environment=id_env_1, id=uuid.uuid4())
        await insert_with_link_to_configuration_model(resource_set, versions=[i])
        resource_set_per_version[i] = resource_set

    msg_timings = {
        i: datetime.datetime.strptime("2021-07-07T10:10:00.0", "%Y-%m-%dT%H:%M:%S.%f")
        .replace(minute=i)
        .astimezone(datetime.timezone.utc)
        for i in range(0, 14)
    }

    msg_timings_idx = 0
    for i in range(1, 10):
        action_id = uuid.uuid4()
        res1 = data.Resource.new(
            environment=id_env_1,
            resource_version_id=f"std::testing::NullResource[agent1,name=dir1],v={i}",
            resource_set=resource_set_per_version[i],
            attributes={"name": "file2", "purged": True},
        )
        await res1.insert()

        res2 = data.Resource.new(
            environment=id_env_1,
            resource_version_id=f"std::testing::NullResource[agent1,name=dir2],v={i}",
            resource_set=resource_set_per_version[i],
            attributes={"name": "dir2", "purged": False},
        )
        await res2.insert()

        resource_action = data.ResourceAction(
            environment=id_env_1,
            version=i,
            resource_version_ids=[
                f"std::testing::NullResource[agent1,name=dir1],v={i}",
                f"std::testing::NullResource[agent1,name=dir2],v={i}",
            ],
            action_id=action_id,
            action=const.ResourceAction.deploy if i % 2 else const.ResourceAction.pull,
            started=cm_times[i],
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
        await data.ResourcePersistentState.populate_for_version(environment=id_env_1, model_version=i)


@pytest.mark.parametrize(
    "input, output",
    [
        ("isDeploying", "is_deploying"),
        ("lastHandlerRun", "last_handler_run"),
        ("resourceIdValue", "resource_id_value"),
        ("blocked", "blocked"),
    ],
)
async def test_to_snake_case(input, output):
    """
    Check that the to_snake_case function works as expected for our intended use.
    """
    assert to_snake_case(input) == output


async def test_graphql_schema(server, client):
    """
    Tests to see if the graphql schema endpoint is working
    """
    result = await client.graphql_schema()
    assert result.code == 200
    assert result.result["data"]["__schema"]


async def test_query_environment_settings(server, client, setup_database):
    """
    Assert that the settings returned are correct
    """
    env_id = "11111111-1234-5678-1234-000000000002"
    modified_settings = {data.AUTO_DEPLOY: False, data.RESOURCE_ACTION_LOGS_RETENTION: 12}
    result = await client.protected_environment_settings_set_batch(
        tid=env_id,
        settings=modified_settings,
        protected_by=model.ProtectedBy.project_yml,
    )
    assert result.code == 200
    query = """
{
    environments(filter:{id: "%s"}) {
        edges {
            node {
              id
              settings
            }
        }
    }
}

""" % env_id

    result = await client.graphql(query=query)
    assert result.code == 200
    # Result settings
    settings = result.result["data"]["data"]["environments"]["edges"][0]["node"]["settings"]
    # Expected settings
    api_result = await client.list_settings(tid=env_id)
    assert api_result.code == 200
    assert settings["definition"] == api_result.result["metadata"]
    for setting_name in data.Environment._settings.keys():
        setting_value = settings["settings"][setting_name]
        if setting_name in modified_settings:
            assert setting_value["value"] == modified_settings[setting_name]
            assert setting_value["protected"]
            assert setting_value["protected_by"] == model.ProtectedBy.project_yml
        else:
            assert setting_value["value"] == api_result.result["metadata"][setting_name]["default"]
            assert setting_value["protected"] is False
            assert setting_value["protected_by"] is None


async def test_query_environments_with_filtering(server, client, setup_database):
    """
    Display basic filtering capabilities
    """
    query = """
{
    environments(filter:{id: "11111111-1234-5678-1234-000000000002"}) {
        edges {
            node {
              id
              halted
              isExpertMode
            }
        }
    }
}
"""
    result = await client.graphql(query=query)
    assert result.code == 200
    assert result.result["data"] == {
        "data": {
            "environments": {
                "edges": [
                    {
                        "node": {
                            "halted": False,
                            "id": "11111111-1234-5678-1234-000000000002",
                            "isExpertMode": False,
                        }
                    }
                ]
            }
        },
        "errors": None,
        "extensions": {},
    }


async def test_query_environments_with_sorting(server, client, setup_database):
    """
    Display basic sorting capabilities
    """
    query = """
{
    environments(%s){
        edges {
            node {
              id
              name
            }
        }
    }
}
"""
    test_cases = [
        ('orderBy:[{key: "name", order:"asc"}]', ["test-env-a", "test-env-b", "test-env-c"]),
        ('orderBy:[{key: "name", order:"desc"}]', ["test-env-c", "test-env-b", "test-env-a"]),
        ('orderBy:[{key: "id", order:"asc"}]', ["test-env-b", "test-env-c", "test-env-a"]),
        ('orderBy:[{key: "id", order:"desc"}]', ["test-env-a", "test-env-c", "test-env-b"]),
    ]

    for test_case in test_cases:
        result = await client.graphql(query=query % test_case[0])
        assert result.code == 200
        results = result.result["data"]["data"]["environments"]["edges"]
        assert [node["node"]["name"] for node in results] == test_case[1]


async def test_query_environments_with_paging(server, client, setup_database):
    """
    Display basic paging capabilities
    """
    # Create second project
    id_project_2 = uuid.UUID("00000000-1234-5678-1234-000000000002")
    result = await client.project_create(name="test-proj-2", project_id=id_project_2)
    assert result.code == 200
    # Create environments in project
    for i in range(6):
        result = await client.environment_create(
            project_id=id_project_2,
            name=f"test-env-{i}",
            environment_id=uuid.UUID(f"21111111-1234-5678-1234-00000000000{i}"),
        )
        assert result.code == 200

    # env-ids -> [b, c, a, 0, 1, 2, 3, 4, 5]
    query = """
{
    environments(%s){
        pageInfo{
            startCursor,
            endCursor,
            hasPreviousPage,
            hasNextPage
        }
        edges {
            cursor
            node {
              id
              name
            }
        }
    }
}
"""
    test_cases = [
        ("first: 3", ["test-env-b", "test-env-c", "test-env-a"]),
        ("first: 5", ["test-env-b", "test-env-c", "test-env-a", "test-env-0", "test-env-1"]),
    ]

    for test_case in test_cases:
        result = await client.graphql(query=query % test_case[0])
        assert result.code == 200
        results = result.result["data"]["data"]["environments"]["edges"]
        assert [node["node"]["name"] for node in results] == test_case[1]

    # Get the first 5 elements
    # [b, c, a, 0, 1]
    result = await client.graphql(query=query % "first: 5")
    assert result.code == 200
    environments = result.result["data"]["data"]["environments"]
    results = environments["edges"]
    assert len(results) == 5
    first_cursor = results[0]["cursor"]
    last_cursor = results[4]["cursor"]
    # Assert that the paging information is correct
    assert environments["pageInfo"]["startCursor"] == first_cursor
    assert environments["pageInfo"]["endCursor"] == last_cursor
    assert environments["pageInfo"]["hasNextPage"] is True
    assert environments["pageInfo"]["hasPreviousPage"] is False

    # Get 5 environments starting from the second to last cursor of the previous result
    second_to_last_cursor = results[-2]["cursor"]
    result = await client.graphql(query=query % f'first: 5, after:"{second_to_last_cursor}"')
    assert result.code == 200
    environments = result.result["data"]["data"]["environments"]
    results = environments["edges"]
    assert len(results) == 5
    # Assert that the first cursor of these results is the last from the previous results
    first_cursor = results[0]["cursor"]
    assert first_cursor == last_cursor
    new_last_cursor = results[4]["cursor"]
    assert environments["pageInfo"]["startCursor"] == first_cursor
    assert environments["pageInfo"]["endCursor"] == new_last_cursor
    assert environments["pageInfo"]["hasNextPage"] is False
    assert environments["pageInfo"]["hasPreviousPage"] is True
    expected_ids = [1, 2, 3, 4, 5]
    for i in range(len(results)):
        assert results[i]["node"]["name"] == f"test-env-{expected_ids[i]}"

    # Get the last 5 elements before last_cursor
    previous_second_to_last_cursor = results[3]["cursor"]
    previous_first_cursor = first_cursor
    result = await client.graphql(query=query % f'last: 5, before:"{new_last_cursor}"')
    assert result.code == 200
    environments = result.result["data"]["data"]["environments"]
    results = environments["edges"]
    assert len(results) == 5
    assert results[1]["cursor"] == previous_first_cursor
    assert results[4]["cursor"] == previous_second_to_last_cursor
    assert environments["pageInfo"]["endCursor"] == previous_second_to_last_cursor
    assert environments["pageInfo"]["hasNextPage"] is True
    assert environments["pageInfo"]["hasPreviousPage"] is True
    expected_ids = [0, 1, 2, 3, 4]
    for i in range(len(results)):
        assert results[i]["node"]["name"] == f"test-env-{expected_ids[i]}"

    # Error cases

    # last by itself
    result = await client.graphql(query=query % "last: 5")
    assert result.code == 200
    data = result.result["data"]
    assert data
    assert data["data"] is None
    assert len(data["errors"]) == 1
    assert data["errors"][0] == "`last` is only allowed in conjunction with `before`"

    # first + last
    result = await client.graphql(query=query % "first: 5, last: 5")
    assert result.code == 200
    data = result.result["data"]
    assert data
    assert data["data"] is None
    assert len(data["errors"]) == 1
    assert data["errors"][0] == "`first` is not allowed in conjunction with `last` or `before`"

    # first + before
    result = await client.graphql(query=query % f'first: 5, before: "{new_last_cursor}"')
    assert result.code == 200
    data = result.result["data"]
    assert data
    assert data["data"] is None
    assert len(data["errors"]) == 1
    assert data["errors"][0] == "`first` is not allowed in conjunction with `last` or `before`"

    # last + after
    result = await client.graphql(query=query % f'last: 5, after: "{first_cursor}"')
    assert result.code == 200
    data = result.result["data"]
    assert data
    assert data["data"] is None
    assert len(data["errors"]) == 1
    assert data["errors"][0] == "`last` is only allowed in conjunction with `before`"

    # before + after
    result = await client.graphql(query=query % f'before: "{new_last_cursor}", after: "{first_cursor}"')
    assert result.code == 200
    data = result.result["data"]
    assert data
    assert data["data"] is None
    assert len(data["errors"]) == 1
    assert data["errors"][0] == "`after` is not allowed in conjunction with `before`"


async def test_is_environment_compiling(server, client, clienthelper, environment, mocked_compiler_service_block):

    compilerslice = server.get_slice(SLICE_COMPILER)
    assert isinstance(compilerslice, CompilerService)
    env = await data.Environment.get_by_id(environment)

    query = """
    {
        environments {
            edges {
                node {
                  id
                  isCompiling
                }
            }
        }
    }
        """

    def get_response(is_compiling: bool) -> dict:
        return {
            "data": {
                "environments": {
                    "edges": [
                        {
                            "node": {
                                "id": environment,
                                "isCompiling": is_compiling,
                            }
                        },
                    ]
                }
            },
            "errors": None,
            "extensions": {},
        }

    result = await client.graphql(query=query)
    assert result.code == 200
    assert result.result["data"] == get_response(is_compiling=False)

    # Trigger compile
    await compilerslice.request_recompile(env=env, force_update=False, do_export=False, remote_id=uuid.uuid4())
    # prevent race conditions where compile request is not yet in queue
    await retry_limited(lambda: compilerslice._env_to_compile_task.get(uuid.UUID(environment), None) is not None, timeout=10)

    # Assert that GraphQL reports that environment is compiling
    result = await client.graphql(query=query)
    assert result.code == 200
    # Check if regular endpoint confirms that it is compiling
    regular_check = await client.is_compiling(environment)
    assert regular_check.code == 200
    assert result.result["data"] == get_response(is_compiling=True)

    # Finish compile
    await run_compile_and_wait_until_compile_is_done(compilerslice, mocked_compiler_service_block, env.id)

    # Assert that GraphQL reports that environment is no longer compiling
    result = await client.graphql(query=query)
    assert result.code == 200
    assert result.result["data"] == get_response(is_compiling=False)


async def test_notifications(server, client, setup_database):
    """
    Assert that the notifications query works with filtering and sorting
    """

    query = """
        {
          notifications %s {
              pageInfo{
                startCursor,
                endCursor,
                hasPreviousPage,
                hasNextPage
            }
            edges {
              cursor
              node {
                title
                environment
                created
                cleared
              }
            }
          }
        }
    """
    # Try to get the full list of notifications without filter
    result = await client.graphql(query=query % "")
    assert result.code == 200
    assert len(result.result["data"]["errors"]) == 1
    assert (
        result.result["data"]["errors"][0]
        == "Field 'notifications' argument 'filter' of type 'NotificationFilter!' is required, but it was not provided."
    )
    # Get list of notifications filtered by cleared
    result = await client.graphql(query=query % """
            (filter: {
              cleared: false
              environment: "11111111-1234-5678-1234-000000000001"
            },
            orderBy: [
                {key: "created" order: "desc"}
            ])
    """)
    assert result.code == 200
    edges = result.result["data"]["data"]["notifications"]["edges"]
    # Environments 1 has 6 uncleared notifications
    assert len(edges) == 6
    # Assert that each notification is uncleared and that the most recent notifications appear first
    # Arbitrary date that is more recent than any of the created notifications
    previous_time = datetime.datetime.now().astimezone()
    for edge in edges:
        assert edge["node"]["cleared"] is False
        assert edge["node"]["environment"] == "11111111-1234-5678-1234-000000000001"
        created = datetime.datetime.fromisoformat(edge["node"]["created"])
        assert created < previous_time
        previous_time = created

    # Get first page of notifications
    result = await client.graphql(query=query % """
            (filter: {
              cleared: false
              environment: "11111111-1234-5678-1234-000000000001"
            },
            orderBy: [
                {key: "created" order: "desc"}
            ],
            first: 3)
    """)
    assert result.code == 200
    notifications = result.result["data"]["data"]["notifications"]
    pageInfo = notifications["pageInfo"]
    assert pageInfo["hasPreviousPage"] is False
    assert pageInfo["hasNextPage"] is True
    edges = notifications["edges"]
    assert len(edges) == 3
    assert edges[0]["cursor"] == pageInfo["startCursor"]
    assert edges[-1]["cursor"] == pageInfo["endCursor"]
    # Assert that each notification is uncleared and that the most recent notifications appear first
    # Arbitrary date that is more recent than any of the created notifications
    previous_time = datetime.datetime.now().astimezone()
    for edge in edges:
        assert edge["node"]["cleared"] is False
        assert edge["node"]["environment"] == "11111111-1234-5678-1234-000000000001"
        created = datetime.datetime.fromisoformat(edge["node"]["created"])
        assert created < previous_time
        previous_time = created

    # Get first page of notifications
    next_page_filter = """
            (filter: {
              cleared: false
              environment: "11111111-1234-5678-1234-000000000001"
            },
            orderBy: [
                {key: "created" order: "desc"}
            ],
            first: 3, after: "%s")
    """ % pageInfo["endCursor"]
    result = await client.graphql(query=query % next_page_filter)
    assert result.code == 200
    notifications = result.result["data"]["data"]["notifications"]
    pageInfo = notifications["pageInfo"]
    assert pageInfo["hasPreviousPage"] is True
    assert pageInfo["hasNextPage"] is False
    edges = notifications["edges"]
    assert len(edges) == 3
    assert edges[0]["cursor"] == pageInfo["startCursor"]
    assert edges[-1]["cursor"] == pageInfo["endCursor"]

    # previous_time is the created time of the last result of the first page
    for edge in edges:
        assert edge["node"]["cleared"] is False
        assert edge["node"]["environment"] == "11111111-1234-5678-1234-000000000001"
        created = datetime.datetime.fromisoformat(edge["node"]["created"])
        assert created < previous_time
        previous_time = created


async def test_query_resources(server, client, environment, mixed_resource_generator):
    def is_subset_dict(expected: dict, actual: dict) -> bool:
        """
        Checks if a dict is a subset of another dict.
        Allows for nested dicts.
        """
        for key, val in expected.items():
            if key not in actual:
                return False
            if isinstance(val, dict) and isinstance(actual[key], dict):
                if not is_subset_dict(val, actual[key]):
                    return False
            elif actual[key] != val:
                return False
        return True

    instances = 2
    resources_per_version = 10
    orphans = resources_per_version / 2
    total_resources_in_latest_version = resources_per_version * instances
    total_resources = total_resources_in_latest_version + (orphans * instances)
    await mixed_resource_generator(environment, instances, resources_per_version)

    # Quick way of simulating a non-compliant report
    # It has to be non-orphan otherwise the complianceState returned will be None
    rps = await data.ResourcePersistentState.get_one(
        environment=environment, last_handler_run=state.HandlerResult.SUCCESSFUL, is_orphan=False
    )
    assert rps
    await rps.update_fields(last_handler_run_compliant=False)

    filters = [
        # (1 undefined, 1 skipped for undefined) * <instances>
        {
            "query": "blocked: {eq: BLOCKED}",
            "result": 2 * instances,
            "assertion": {"state": {"blocked": state.Blocked.BLOCKED.name}},
        },
        {"query": "blocked: {eq: BLOCKED, neq: BLOCKED}", "result": 0},
        {"query": 'agent: {eq: ["agent1"]}', "result": resources_per_version + orphans, "assertion": {"agent": "agent1"}},
        {
            "query": 'agent: {eq: ["agent1"]} isOrphan: false',
            "result": resources_per_version,
            "assertion": {"agent": "agent1", "state": {"isOrphan": False}},
        },
        {
            "query": 'agent: {eq: ["agent1"]} isOrphan: true',
            "result": orphans,
            "assertion": {"agent": "agent1", "state": {"isOrphan": True}},
        },
        {"query": 'agent: {contains: ["%agent%"]}', "result": total_resources},
        {"query": 'agent: {notContains: ["%agent%"]}', "result": 0},
        {
            "query": 'agent: {notContains: ["%1"]}',
            "result": resources_per_version + orphans,
            "assertion": {"agent": "agent0"},
        },
        {
            "query": 'agent: {notContains: ["%1"]} isOrphan: false',
            "result": resources_per_version,
            "assertion": {"agent": "agent0", "state": {"isOrphan": False}},
        },
        {"query": 'agent: {contains: ["agent_"]}', "result": total_resources},
        {"query": 'agent: {contains: ["1", "2"]}', "result": 0},
        {"query": 'resourceType: {notContains: ["%XResource%"]}', "result": 0},
        {"query": 'resourceType: {notContains: ["%xresource%"]}', "result": 0},
        {"query": 'resourceIdValue: {notContains: ["1"]}', "result": (resources_per_version - 1 + orphans) * instances},
        {"query": 'resourceIdValue: {notContains: ["1"]} isOrphan: false', "result": (resources_per_version - 1) * instances},
        {"query": 'resourceIdValue: {eq: ["0"]}', "result": instances, "assertion": {"resourceIdValue": "0"}},
        {"query": "purged: true", "result": 0},
        {"query": "purged: false", "result": total_resources},
        # skipped for undefined
        {
            "query": "complianceState: {eq: HAS_UPDATE} blocked: {eq: BLOCKED}",
            "result": instances,
            "assertion": {
                "state": {"blocked": state.Blocked.BLOCKED.name, "complianceState": state.Compliance.HAS_UPDATE.name}
            },
        },
        # 1 undefined, 1 skipped for undefined, 1 still deploying
        {
            "query": "lastHandlerRun: {eq: NEW}",
            "result": 3 * instances,
            "assertion": {"state": {"lastHandlerRun": state.HandlerResult.NEW.name}},
        },
        {"query": "isDeploying: true", "result": instances, "assertion": {"state": {"isDeploying": True}}},
        {
            "query": "isDeploying: false",
            "result": total_resources - instances,
            "assertion": {"state": {"isDeploying": False}},
        },
        # 1 undefined, 1 skipped for undefined
        {
            "query": "lastHandlerRun: {eq: NEW} isDeploying: false",
            "result": 2 * instances,
            "assertion": {"state": {"lastHandlerRun": state.HandlerResult.NEW.name, "isDeploying": False}},
        },
        #  1 skipped for undefined
        {
            "query": "lastHandlerRun: {eq: NEW} isDeploying: false complianceState: {neq: UNDEFINED}",
            "result": instances,
            "assertion": {
                "state": {
                    "lastHandlerRun": state.HandlerResult.NEW.name,
                    "isDeploying": False,
                    "complianceState": state.Compliance.HAS_UPDATE.name,
                }
            },
        },
        # Non-compliant report
        {
            "query": "lastHandlerRun: {eq: SUCCESSFUL} isDeploying: false complianceState: {eq: NON_COMPLIANT}",
            "result": 1,
            "assertion": {
                "state": {
                    "lastHandlerRun": state.HandlerResult.SUCCESSFUL.name,
                    "isDeploying": False,
                    "complianceState": state.Compliance.NON_COMPLIANT.name,
                }
            },
        },
    ]
    for f in filters:
        query = """
        {
            resources (filter: {environment: "%s" %s}) {
                edges {
                    node {
                      resourceId
                      agent
                      resourceIdValue
                      resourceType
                      attributes
                      purged
                      state{
                        isOrphan
                        isUndefined
                        blocked
                        isDeploying
                        lastHandlerRun
                        lastHandlerRunAt
                        complianceState
                        currentIntentAttributeHash
                      }
                      requiresLength
                    }
                }
            }
        }
        """ % (
            environment,
            f["query"],
        )
        result = await client.graphql(query=query)
        assert result.code == 200
        assert result.result["data"]["errors"] is None
        assert len(result.result["data"]["data"]["resources"]["edges"]) == f["result"], f["query"]
        assertion = f.get("assertion", None)
        if assertion:
            for res in result.result["data"]["data"]["resources"]["edges"]:
                assert is_subset_dict(assertion, res["node"])

    query = """
    {
        resources ( filter: {environment: "%s" lastHandlerRun: {eq: NEW}}
            orderBy: [{key: "complianceState" order: "asc"}]) {
            edges {
                node {
                  state{
                    complianceState
                  }
                }
            }
        }
    }
    """ % environment
    result = await client.graphql(query=query)
    assert result.code == 200
    assert result.result["data"]["errors"] is None
    result_resources = result.result["data"]["data"]["resources"]["edges"]
    assert len(result_resources) == 3 * instances
    for i in range(0, len(result_resources)):
        assert (
            result_resources[i]["node"]["state"]["complianceState"] == state.Compliance.HAS_UPDATE.name
            if i < 2 * instances
            else state.Compliance.UNDEFINED.name
        )

    query = """
    {
        resources (filter: {environment: "%s" lastHandlerRun: {eq: NEW}}
            orderBy: [{key: "complianceState" order: "desc"}, {key: "isDeploying" order: "asc"}]) {
            edges {
                node {
                  state{
                    complianceState
                    isDeploying
                  }
                }
            }
        }
    }
    """ % environment
    result = await client.graphql(query=query)
    assert result.code == 200
    assert result.result["data"]["errors"] is None
    result_resources = result.result["data"]["data"]["resources"]["edges"]
    assert len(result_resources) == 3 * instances
    for i in range(0, len(result_resources)):
        # [{UNDEFINED, False}, {HAS_UPDATE, False}, {HAS_UPDATE, True}]
        assert (
            result_resources[i]["node"]["state"]["complianceState"] == state.Compliance.UNDEFINED.name
            if i < instances
            else state.Compliance.HAS_UPDATE.name
        )
        assert result_resources[i]["node"]["state"]["isDeploying"] == (False if i < 2 * instances else True)

    query = """
       {
           resources (filter: {environment: "%s" lastHandlerRun: {eq: NEW}}
                    orderBy: [{key: "complianceState" order: "desc"}, {key: "isDeploying" order: "desc"}]) {
               edges {
                   node {
                     state{
                       complianceState
                       isDeploying
                     }
                   }
               }
           }
       }
       """ % environment
    result = await client.graphql(query=query)
    assert result.code == 200
    assert result.result["data"]["errors"] is None
    result_resources = result.result["data"]["data"]["resources"]["edges"]
    assert len(result_resources) == 3 * instances
    for i in range(0, len(result_resources)):
        # [{UNDEFINED, False}, {HAS_UPDATE, True}, {HAS_UPDATE, False}]
        assert (
            result_resources[i]["node"]["state"]["complianceState"] == state.Compliance.UNDEFINED.name
            if i < instances
            else state.Compliance.HAS_UPDATE.name
        )
        assert result_resources[i]["node"]["state"]["isDeploying"] == (False if i < instances or i >= 2 * instances else True)
