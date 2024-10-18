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

import functools
import operator
import uuid
from collections import abc, defaultdict
from collections.abc import AsyncIterator, Awaitable, Sequence
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional, cast

import asyncpg
import pytest

from inmanta import const, data
from inmanta.server import SLICE_ENVIRONMENT_METRICS, protocol
from inmanta.server.services.environment_metrics_service import (
    DEFAULT_CATEGORY,
    AgentCountMetricsCollector,
    CompileTimeMetricsCollector,
    CompileWaitingTimeMetricsCollector,
    EnvironmentMetricsService,
    MetricsCollector,
    MetricType,
    MetricValue,
    MetricValueTimer,
    ResourceCountMetricsCollector,
)
from inmanta.util import get_compiler_version, parse_timestamp
from utils import ClientHelper, wait_until_version_is_released

env_uuid = uuid.uuid4()


@pytest.fixture
async def env_metrics_service(server_config, init_dataclasses_and_load_schema) -> EnvironmentMetricsService:
    metrics_service = EnvironmentMetricsService()
    yield metrics_service


@pytest.fixture
def server_pre_start(disable_background_jobs, server_config):
    """
    This fixture is called before the server starts and will disable background jobs
    that might interfere with the testing by calling into the disable_background_jobs
    fixture.
    """


@pytest.fixture
async def env_with_uuid():
    project = data.Project(name="test")
    await project.insert()
    projects = await data.Project.get_list(name="test")
    assert len(projects) == 1
    project_id = projects[0].id
    environment: data.Environment = data.Environment(id=env_uuid, project=project_id, name="testenv")
    await environment.insert()
    envs = await data.Environment.get_list(project=project_id)
    assert len(envs) == 1
    assert envs[0].id == env_uuid


class DummyGaugeMetric(MetricsCollector):
    def get_metric_name(self) -> str:
        return "dummy_gauge"

    def get_metric_type(self) -> MetricType:
        return MetricType.GAUGE

    async def get_metric_value(
        self, start_interval: datetime, end_interval: datetime, connection: Optional[asyncpg.connection.Connection]
    ) -> abc.Sequence[MetricValue]:
        a = MetricValue("dummy_gauge", 1, env_uuid)
        return [a]


class DummyGaugeMetricMulti(MetricsCollector):
    def get_metric_name(self) -> str:
        return "dummy_gauge_multi"

    def get_metric_type(self) -> MetricType:
        return MetricType.GAUGE

    async def get_metric_value(
        self, start_interval: datetime, end_interval: datetime, connection: Optional[asyncpg.connection.Connection]
    ) -> abc.Sequence[MetricValue]:
        a = MetricValue("dummy_gauge_multi", 1, env_uuid, "up")
        b = MetricValue("dummy_gauge_multi", 2, env_uuid, "down")
        c = MetricValue("dummy_gauge_multi", 3, env_uuid, "left")
        return [a, b, c]


class DummyTimerMetric(MetricsCollector):
    def get_metric_name(self) -> str:
        return "dummy_timer"

    def get_metric_type(self) -> MetricType:
        return MetricType.TIMER

    async def get_metric_value(
        self, start_interval: datetime, end_interval: datetime, connection: Optional[asyncpg.connection.Connection]
    ) -> abc.Sequence[MetricValueTimer]:
        a = MetricValueTimer("dummy_timer", 3, 50.50, env_uuid)
        return [a]


class DummyTimerMetricMulti(MetricsCollector):
    def get_metric_name(self) -> str:
        return "dummy_timer_multi"

    def get_metric_type(self) -> MetricType:
        return MetricType.TIMER

    async def get_metric_value(
        self, start_interval: datetime, end_interval: datetime, connection: Optional[asyncpg.connection.Connection]
    ) -> abc.Sequence[MetricValueTimer]:
        a = MetricValueTimer("dummy_timer_multi", 3, 50.50 * 1, env_uuid, "up")
        b = MetricValueTimer("dummy_timer_multi", 13, 50.50 * 2, env_uuid, "down")
        c = MetricValueTimer("dummy_timer_multi", 23, 50.50 * 3, env_uuid, "left")
        return [a, b, c]


async def test_register_metrics_collector(env_metrics_service):
    dummy_gauge = DummyGaugeMetric()
    dummy_timer = DummyTimerMetric()
    env_metrics_service.register_metric_collector(metrics_collector=dummy_gauge)
    env_metrics_service.register_metric_collector(metrics_collector=dummy_timer)

    assert len(env_metrics_service.metrics_collectors) == 2


async def test_register_same_metrics_collector(env_metrics_service):
    with pytest.raises(Exception) as e:
        dummy_gauge = DummyGaugeMetric()
        dummy_gauge2 = DummyGaugeMetric()
        env_metrics_service.register_metric_collector(metrics_collector=dummy_gauge)
        env_metrics_service.register_metric_collector(metrics_collector=dummy_gauge2)
    assert "There already is a metric collector with the name dummy_gauge" in str(e.value)


async def test_bad_type_metric(env_metrics_service):
    class BadTypeMetric(MetricsCollector):
        def get_metric_name(self) -> str:
            return "bad_type"

        def get_metric_type(self) -> MetricType:
            return MetricType.TIMER

        async def get_metric_value(
            self, start_interval: datetime, end_interval: datetime, connection: Optional[asyncpg.connection.Connection]
        ) -> abc.Sequence[MetricValue]:
            a = MetricValue(self.get_metric_name(), env_uuid, 10)
            return [a]

    with pytest.raises(Exception):
        bad_name = BadTypeMetric()
        env_metrics_service.register_metric_collector(metrics_collector=bad_name)
        await env_metrics_service.flush_metrics()


async def test_flush_metrics_gauge(env_metrics_service, env_with_uuid):
    dummy_gauge = DummyGaugeMetric()
    env_metrics_service.register_metric_collector(metrics_collector=dummy_gauge)

    previous_timestamp: datetime = env_metrics_service.previous_timestamp
    await env_metrics_service.flush_metrics()
    assert previous_timestamp < env_metrics_service.previous_timestamp
    result = await data.EnvironmentMetricsGauge.get_list()
    assert len(result) == 1
    assert result[0].count == 1
    assert result[0].metric_name == "dummy_gauge"
    assert isinstance(result[0].timestamp, datetime)

    await env_metrics_service.flush_metrics()
    await env_metrics_service.flush_metrics()

    result = await data.EnvironmentMetricsGauge.get_list()
    assert len(result) == 3


async def test_flush_metrics_gauge_multi(env_metrics_service, env_with_uuid):
    dummy_gauge = DummyGaugeMetricMulti()
    env_metrics_service.register_metric_collector(metrics_collector=dummy_gauge)

    previous_timestamp: datetime = env_metrics_service.previous_timestamp
    await env_metrics_service.flush_metrics()
    assert previous_timestamp < env_metrics_service.previous_timestamp
    result = await data.EnvironmentMetricsGauge.get_list()
    assert len(result) == 3
    assert result[0].count == 1
    assert result[0].metric_name == "dummy_gauge_multi"
    assert result[0].category == "up"
    assert isinstance(result[0].timestamp, datetime)
    assert result[1].count == 2
    assert result[1].metric_name == "dummy_gauge_multi"
    assert result[1].category == "down"
    assert isinstance(result[1].timestamp, datetime)
    assert result[2].count == 3
    assert result[2].metric_name == "dummy_gauge_multi"
    assert result[2].category == "left"
    assert isinstance(result[2].timestamp, datetime)

    await env_metrics_service.flush_metrics()
    await env_metrics_service.flush_metrics()

    result = await data.EnvironmentMetricsGauge.get_list()
    assert len(result) == 9


async def test_flush_metrics_timer(env_metrics_service, env_with_uuid):
    dummy_timer = DummyTimerMetric()
    env_metrics_service.register_metric_collector(metrics_collector=dummy_timer)

    previous_timestamp: datetime = env_metrics_service.previous_timestamp
    await env_metrics_service.flush_metrics()
    assert previous_timestamp < env_metrics_service.previous_timestamp
    result = await data.EnvironmentMetricsTimer.get_list()
    assert len(result) == 1
    assert result[0].count == 3
    assert result[0].value == 50.50
    assert result[0].metric_name == "dummy_timer"
    assert isinstance(result[0].timestamp, datetime)

    await env_metrics_service.flush_metrics()
    await env_metrics_service.flush_metrics()

    result = await data.EnvironmentMetricsTimer.get_list()
    assert len(result) == 3


async def test_flush_metrics_timer_multi(env_metrics_service, env_with_uuid):
    dummy_timer = DummyTimerMetricMulti()
    env_metrics_service.register_metric_collector(metrics_collector=dummy_timer)

    previous_timestamp: datetime = env_metrics_service.previous_timestamp
    await env_metrics_service.flush_metrics()
    assert previous_timestamp < env_metrics_service.previous_timestamp
    result = await data.EnvironmentMetricsTimer.get_list()
    assert len(result) == 3
    assert result[0].count == 3
    assert result[0].value == 50.50
    assert result[0].metric_name == "dummy_timer_multi"
    assert result[0].category == "up"
    assert isinstance(result[0].timestamp, datetime)
    assert result[1].count == 13
    assert result[1].value == 50.50 * 2
    assert result[1].metric_name == "dummy_timer_multi"
    assert result[1].category == "down"
    assert isinstance(result[1].timestamp, datetime)
    assert result[2].count == 23
    assert result[2].value == 50.50 * 3
    assert result[2].metric_name == "dummy_timer_multi"
    assert result[2].category == "left"
    assert isinstance(result[2].timestamp, datetime)

    await env_metrics_service.flush_metrics()
    await env_metrics_service.flush_metrics()

    result = await data.EnvironmentMetricsTimer.get_list()
    assert len(result) == 9


async def test_flush_metrics_mix(env_metrics_service, env_with_uuid):
    dummy_gauge = DummyGaugeMetric()
    dummy_timer = DummyTimerMetricMulti()
    env_metrics_service.register_metric_collector(metrics_collector=dummy_gauge)
    env_metrics_service.register_metric_collector(metrics_collector=dummy_timer)

    await env_metrics_service.flush_metrics()
    result_gauge = await data.EnvironmentMetricsGauge.get_list()
    result_timer = await data.EnvironmentMetricsTimer.get_list()
    assert len(result_gauge) == 1
    assert len(result_timer) == 3

    await env_metrics_service.flush_metrics()
    await env_metrics_service.flush_metrics()

    result_gauge = await data.EnvironmentMetricsGauge.get_list()
    result_timer = await data.EnvironmentMetricsTimer.get_list()
    assert len(result_gauge) == 3
    assert len(result_timer) == 9


async def test_flush_metrics_for_different_envs(env_metrics_service):
    # create a project with 2 Environments
    env_uuid2 = uuid.uuid4()
    project = data.Project(name="test")
    await project.insert()
    projects = await data.Project.get_list(name="test")
    assert len(projects) == 1
    project_id = projects[0].id
    environment: data.Environment = data.Environment(id=env_uuid, project=project_id, name="testenv1")
    await environment.insert()
    environment: data.Environment = data.Environment(id=env_uuid2, project=project_id, name="testenv2")
    await environment.insert()
    envs = await data.Environment.get_list(project=project_id)
    assert len(envs) == 2

    # create a MetricCollector that will push data for the second Environment and register both collectors
    class DummyGaugeMetric2(MetricsCollector):
        def get_metric_name(self) -> str:
            return "dummy_gauge_2"

        def get_metric_type(self) -> MetricType:
            return MetricType.GAUGE

        async def get_metric_value(
            self, start_interval: datetime, end_interval: datetime, connection: Optional[asyncpg.connection.Connection]
        ) -> abc.Sequence[MetricValue]:
            a = MetricValue("dummy_gauge_2", 2, env_uuid2)
            return [a]

    dummy_gauge1 = DummyGaugeMetric()
    dummy_gauge2 = DummyGaugeMetric2()
    env_metrics_service.register_metric_collector(metrics_collector=dummy_gauge1)
    env_metrics_service.register_metric_collector(metrics_collector=dummy_gauge2)

    # flush metrics
    await env_metrics_service.flush_metrics()
    result_gauge = await data.EnvironmentMetricsGauge.get_list()
    assert len(result_gauge) == 2
    envs = [result_gauge[0].environment, result_gauge[1].environment]
    assert env_uuid in envs
    assert env_uuid2 in envs


async def test_resource_count_metric(clienthelper, client, agent):
    """
    This test will create 2 environments and start by adding 1 resource to the first. then It will create a second version
    with 3 other resources. It also adds two resources to the second environment.
    It then flushes the resource_count metric a first time. This creates 2 records with counts different from zero
    in EnvironmentMetricsGauge:
    - one for the first environment with 3 resources in the latest version in the available state.
    - one for the second environment with 2 resources in the latest version in the available state.
    following this, the state of one resource in the first environment is updated and the metrics are flushed again.
    This creates 3 records with counts different from zero in EnvironmentMetricsGauge:
    - one for the first environment with 2 resources in the latest version in the available state.
    - one for the first environment with 1 resource in the latest version in the deployed state.
    - one for the second environment with 2 resources in the latest version in the available state.
    """
    env_uuid1 = uuid.uuid4()
    env_uuid2 = uuid.uuid4()
    project = data.Project(name="test")
    await project.insert()
    projects = await data.Project.get_list(name="test")
    assert len(projects) == 1
    project_id = projects[0].id
    environment1: data.Environment = data.Environment(id=env_uuid1, project=project_id, name="testenv1")
    await environment1.insert()
    environment2: data.Environment = data.Environment(id=env_uuid2, project=project_id, name="testenv2")
    await environment2.insert()
    envs = await data.Environment.get_list(project=project_id)
    assert len(envs) == 2

    metrics_service = EnvironmentMetricsService()
    version_env1 = str(await ClientHelper(client, env_uuid1).get_version())
    assert version_env1 == "1"
    version_env2 = str(await ClientHelper(client, env_uuid2).get_version())
    resources_env1_v1 = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=" + version_env1,
            "send_event": False,
            "purged": False,
            "requires": [],
        }
    ]
    result = await client.put_version(
        tid=env_uuid1,
        version=version_env1,
        resources=resources_env1_v1,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200
    version_env1 = str(await ClientHelper(client, env_uuid1).get_version())
    assert version_env1 == "2"
    resources_env1_v2 = [
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Resource[agent1,key=key2],v=" + version_env1,
            "send_event": False,
            "requires": [],
            "purged": False,
        },
        {
            "key": "key3",
            "value": "value3",
            "id": "test::Resource[agent1,key=key3],v=" + version_env1,
            "send_event": False,
            "requires": [],
            "purged": True,
        },
        {
            "key": "key4",
            "value": "value4",
            "id": "test::Resource[agent1,key=key4],v=" + version_env1,
            "send_event": False,
            "requires": [],
            "purged": True,
        },
    ]
    result = await client.put_version(
        tid=env_uuid1,
        version=version_env1,
        resources=resources_env1_v2,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200
    resources_env2 = [
        {
            "key": "key5",
            "value": "value5",
            "id": "test::Resource[agent1,key=key5],v=" + version_env2,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key6",
            "value": "value6",
            "id": "test::Resource[agent1,key=key6],v=" + version_env2,
            "send_event": False,
            "requires": [],
            "purged": False,
        },
    ]
    result = await client.put_version(
        tid=env_uuid2,
        version=version_env2,
        resources=resources_env2,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200
    assert len(await data.Resource.get_list()) == 6

    # Wait until the latest version in each environment is released
    await wait_until_version_is_released(client, environment=env_uuid1, version=version_env1)
    await wait_until_version_is_released(client, environment=env_uuid2, version=version_env2)

    # adds the ResourceCountMetricsCollector
    rcmc = ResourceCountMetricsCollector()
    metrics_service.register_metric_collector(metrics_collector=rcmc)

    # flush the metrics for the first time:
    # create 30 records: (3 envs * 10 statuses)
    # 2 records with count different from 0 (3 resources in available state for the first environment and 2 for the second)
    await metrics_service.flush_metrics()
    result_gauge = await data.EnvironmentMetricsGauge.get_list()
    assert len(result_gauge) == 30
    assert any(
        x.count == 3 and x.metric_name == "resource.resource_count" and x.category == "available" and x.environment == env_uuid1
        for x in result_gauge
    )
    assert any(
        x.count == 2 and x.metric_name == "resource.resource_count" and x.category == "available" and x.environment == env_uuid2
        for x in result_gauge
    )

    # change the state of one of the resources
    now = datetime.now()
    action_id = uuid.uuid4()
    aclient = agent._client
    result = await aclient.resource_action_update(
        env_uuid1,
        ["test::Resource[agent1,key=key2],v=" + version_env1],
        action_id,
        "deploy",
        now,
        now,
        "deployed",
        [],
        {},
    )

    assert result.code == 200

    # flush the metrics for the second time:
    # 60 records in total and 5 with a count different from 0
    # the 2 old record +
    # 3 new records (1 for available state and one for the deployed state for the first environment
    # and one for the available state for the second environment)
    await metrics_service.flush_metrics()
    result_gauge = await data.EnvironmentMetricsGauge.get_list()
    assert len(result_gauge) == 60
    assert any(
        x.count == 3 and x.metric_name == "resource.resource_count" and x.category == "available" and x.environment == env_uuid1
        for x in result_gauge
    )
    assert any(
        x.count == 2 and x.metric_name == "resource.resource_count" and x.category == "available" and x.environment == env_uuid1
        for x in result_gauge
    )
    assert any(
        x.count == 1 and x.metric_name == "resource.resource_count" and x.category == "deployed" and x.environment == env_uuid1
        for x in result_gauge
    )

    env_uuid2_records = [
        r
        for r in result_gauge
        if r.environment == env_uuid2
        and r.metric_name == "resource.resource_count"
        and r.category == "available"
        and r.count == 2
    ]

    assert len(env_uuid2_records) == 2


async def test_resource_count_metric_released(client, server, agent, clienthelper: ClientHelper, environment):
    """
    test that only the latest released version is used for the metrics:
    - adds a first version with 3 resources and a second one with one resource but don't deploy them
    - deploy only the first one
    - verify the flushed data comes from the first version
    """

    version1 = await clienthelper.get_version()

    result = await client.set_setting(tid=environment, id="auto_deploy", value=False)
    assert result.code == 200

    resources_env1_v1 = [
        {
            "key": "key1",
            "value": "value1",
            "id": f"test::Resource[agent1,key=key1],v={version1}",
            "send_event": False,
            "requires": [],
            "purged": False,
        },
        {
            "key": "key2",
            "value": "value2",
            "id": f"test::Resource[agent1,key=key2],v={version1}",
            "send_event": False,
            "requires": [],
            "purged": True,
        },
        {
            "key": "key3",
            "value": "value3",
            "id": f"test::Resource[agent1,key=key3],v={version1}",
            "send_event": False,
            "requires": [],
            "purged": True,
        },
    ]
    result = await client.put_version(
        tid=environment,
        version=version1,
        resources=resources_env1_v1,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    version2 = await clienthelper.get_version()
    resources_env1_v2 = [
        {
            "key": "key5",
            "value": "value5",
            "id": f"test::Resource[agent1,key=key5],v={version2}",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]
    result = await client.put_version(
        tid=environment,
        version=version2,
        resources=resources_env1_v2,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    metrics_service = EnvironmentMetricsService()
    rcmc = ResourceCountMetricsCollector()
    metrics_service.register_metric_collector(metrics_collector=rcmc)

    result = await client.release_version(environment, version1, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    await clienthelper.wait_for_deployed(version1)

    await metrics_service.flush_metrics()
    result_gauge = await data.EnvironmentMetricsGauge.get_list()
    assert len(result_gauge) == 10
    assert any(
        x.count == 3
        and x.metric_name == "resource.resource_count"
        and x.category == "unavailable"
        and str(x.environment) == environment
        for x in result_gauge
    )
    assert 9 == len([obj for obj in result_gauge if obj.count == 0])


async def test_resource_count_empty_datapoint(client, server):
    project = data.Project(name="test")
    await project.insert()
    projects = await data.Project.get_list(name="test")
    assert len(projects) == 1
    project_id = projects[0].id

    env_uuid1 = uuid.uuid4()
    environment1: data.Environment = data.Environment(id=env_uuid1, project=project_id, name="testenv1")
    await environment1.insert()
    env_uuid2 = uuid.uuid4()
    environment2: data.Environment = data.Environment(id=env_uuid2, project=project_id, name="testenv2")
    await environment2.insert()
    envs = await data.Environment.get_list(project=project_id)
    assert len(envs) == 2

    metrics_service = EnvironmentMetricsService()
    rcmc = ResourceCountMetricsCollector()
    metrics_service.register_metric_collector(metrics_collector=rcmc)

    await metrics_service.flush_metrics()
    result_gauge = await data.EnvironmentMetricsGauge.get_list()
    # 2 envs with each 10 statuses with count 0
    assert len(result_gauge) == 20
    assert all(hasattr(res, "category") and res.category != "__None__" and res.count == 0 for res in result_gauge)


@pytest.mark.skip("To be fixed with agent view")
async def test_agent_count_metric(clienthelper, client, server):
    project = data.Project(name="test")
    await project.insert()

    env1 = data.Environment(name="env1", project=project.id)
    await env1.insert()

    env2 = data.Environment(name="env2", project=project.id)
    await env2.insert()

    envs = await data.Environment.get_list(project=project.id)
    assert len(envs) == 2

    metrics_service = EnvironmentMetricsService()

    agent1 = data.Agent(environment=env1.id, name="agent1", paused=True)
    await agent1.insert()
    agent2 = data.Agent(environment=env2.id, name="agent2", paused=True)
    await agent2.insert()
    agent3 = data.Agent(environment=env2.id, name="agent3", paused=True)
    await agent3.insert()

    agents = await data.Agent.get_list()
    assert len(agents) == 3

    # Add dummy resources that use some (but not all) of the agents
    model1 = data.ConfigurationModel(environment=env1.id, version=1, released=True, is_suitable_for_partial_compiles=False)
    await model1.insert()
    model2 = data.ConfigurationModel(environment=env2.id, version=1, released=True, is_suitable_for_partial_compiles=False)
    await model2.insert()
    resource1 = data.Resource(
        environment=env1.id, model=1, agent="agent1", resource_id="", resource_type="", resource_id_value=""
    )
    await resource1.insert()
    resource2 = data.Resource(
        environment=env2.id, model=1, agent="agent2", resource_id="", resource_type="", resource_id_value=""
    )
    await resource2.insert()

    # adds the AgentCountMetricsCollector
    acmc = AgentCountMetricsCollector()
    metrics_service.register_metric_collector(metrics_collector=acmc)
    # flush the metrics for the first time: 2 record (1 agent in paused state for the first
    # environment and 1 for the second)
    await metrics_service.flush_metrics()
    result_gauge = await data.EnvironmentMetricsGauge.get_list()
    assert all(gauge.metric_name == "resource.agent_count" for gauge in result_gauge)
    gauges_by_status: dict[uuid.UUID, dict[str, data.EnvironmentMetricsGauge]] = defaultdict(dict)
    for gauge in result_gauge:
        gauges_by_status[gauge.environment][gauge.category] = gauge
    # 3 environments: one created by the environment fixture (dependency of agent fixture), two created above
    assert len(gauges_by_status) == 3
    # 3 states for each environment => 9 rows in matrix
    assert all(statuses.keys() == {"paused", "up", "down"} for _, statuses in gauges_by_status.items())
    # verify counts
    assert gauges_by_status[env1.id]["paused"].count == 1
    assert gauges_by_status[env2.id]["paused"].count == 2  # agent3 is not used by any resource but it should still be counted
    # verify that all other counts are 0
    assert sum(abs(gauge.count) for gauge in result_gauge) == 3


async def test_agent_count_metric_empty_datapoint(client, server):
    project = data.Project(name="test")
    await project.insert()

    env1 = data.Environment(name="env1", project=project.id)
    await env1.insert()

    env2 = data.Environment(name="env2", project=project.id)
    await env2.insert()

    envs = await data.Environment.get_list(project=project.id)
    assert len(envs) == 2

    metrics_service = EnvironmentMetricsService()

    # adds the AgentCountMetricsCollector
    acmc = AgentCountMetricsCollector()
    metrics_service.register_metric_collector(metrics_collector=acmc)

    # flush the metrics for the first time: 2 record (1 agent in paused state for the first
    # environment and 1 for the second)
    await metrics_service.flush_metrics()
    result_gauge = await data.EnvironmentMetricsGauge.get_list()
    assert len(result_gauge) == 6
    assert all(gauge.metric_name == "resource.agent_count" and gauge.count == 0 for gauge in result_gauge)


async def test_compile_time_metric(client, server):
    async def _add_compile(
        environment: uuid.UUID,
        time_origin: datetime,
        requested_delta: timedelta = timedelta(),
        started_delta: timedelta = timedelta(),
        completed_delta: timedelta = timedelta(),
    ):
        """
        Add a new compile to the database. All timestamps are relative to the time_origin parameter
        """
        compile = data.Compile(
            id=uuid.uuid4(),
            remote_id=uuid.uuid4(),
            environment=environment,
            requested=time_origin + requested_delta,
            started=time_origin + started_delta,
            completed=time_origin + completed_delta,
            do_export=True,
            force_update=False,
            success=True,
            handled=True,
            version=1,
        )
        await compile.insert()

    async def add_compiles(environment: uuid.UUID, compile_times: abc.Sequence[float]):
        """
        These compiles are anchored in time around their COMPLETION time to make sure they are picked
        up by the next call to flush_metrics()
        """
        time_origin = datetime.now()
        requested_offset = timedelta(seconds=-1 * max(compile_times))

        for compile_time in compile_times:
            started_offset = timedelta(seconds=-1 * compile_time)
            await _add_compile(environment, time_origin, requested_delta=requested_offset, started_delta=started_offset)

    project = data.Project(name="test")
    await project.insert()
    projects = await data.Project.get_list(name="test")
    assert len(projects) == 1
    project_id = projects[0].id

    env_uuid1 = uuid.uuid4()
    environment1: data.Environment = data.Environment(id=env_uuid1, project=project_id, name="testenv1")
    await environment1.insert()
    envs = await data.Environment.get_list(project=project_id)
    assert len(envs) == 1

    metrics_service = EnvironmentMetricsService()
    ctmc = CompileTimeMetricsCollector()
    metrics_service.register_metric_collector(metrics_collector=ctmc)

    # Insert a few compiles.
    compile_times: list[float] = [1.2, 2.3, 3.4]
    await add_compiles(env_uuid1, compile_times)

    await metrics_service.flush_metrics()

    result_timer = await data.EnvironmentMetricsTimer.get_list()

    expected_count = len(compile_times)
    expected_total_compile_time = functools.reduce(operator.add, compile_times)

    assert len(result_timer) == 1
    assert any(
        x.count == expected_count
        and x.metric_name == "orchestrator.compile_time"
        and x.environment == environment1.id
        and x.value == expected_total_compile_time
        for x in result_timer
    )

    # Create another environment and insert a few compiles in it.
    env_uuid2 = uuid.uuid4()
    environment2: data.Environment = data.Environment(id=env_uuid2, project=project_id, name="testenv2")
    await environment2.insert()

    envs = await data.Environment.get_list(project=project_id)
    assert len(envs) == 2

    compile_times: list[float] = [2.1, 4.3]
    await add_compiles(env_uuid2, compile_times)

    await metrics_service.flush_metrics()

    result_timer = await data.EnvironmentMetricsTimer.get_list()

    expected_count = len(compile_times)
    expected_total_compile_time = functools.reduce(operator.add, compile_times)

    # 1 new entry
    assert len(result_timer) == 2
    assert any(
        x.count == expected_count
        and x.metric_name == "orchestrator.compile_time"
        and x.environment == environment2.id
        and x.value == expected_total_compile_time
        for x in result_timer
    )

    # Add another set of compiles to the first environment.
    compile_times: list[float] = [1.1, 2.2, 3.3, 4.4]
    await add_compiles(env_uuid1, compile_times)

    await metrics_service.flush_metrics()

    result_timer = await data.EnvironmentMetricsTimer.get_list()

    expected_count = len(compile_times)
    expected_total_compile_time = sum(compile_times)

    # 1 new entry
    assert len(result_timer) == 3
    assert any(
        x.count == expected_count
        and x.metric_name == "orchestrator.compile_time"
        and x.environment == environment1.id
        and x.value == expected_total_compile_time
        for x in result_timer
    )


async def test_compile_time_metric_no_empty_datapoint(client, server):
    project = data.Project(name="test")
    await project.insert()

    env1 = data.Environment(name="env1", project=project.id)
    await env1.insert()

    env2 = data.Environment(name="env2", project=project.id)
    await env2.insert()

    envs = await data.Environment.get_list(project=project.id)
    assert len(envs) == 2

    metrics_service = EnvironmentMetricsService()
    collector = CompileTimeMetricsCollector()
    metrics_service.register_metric_collector(metrics_collector=collector)

    await metrics_service.flush_metrics()
    result_timer = await data.EnvironmentMetricsTimer.get_list()
    assert len(result_timer) == 0


async def test_compile_wait_time_metric(client, server):
    async def _add_compile(
        environment: uuid.UUID,
        time_origin: datetime,
        requested_delta: timedelta,
    ):
        """
        Add a new compile to the database. All timestamps are relative to the time_origin parameter
        The requested_delta will be used to create a compile: it is used to calculate "requested" by adding
        the "requested_delta" to "started".
        """
        started = time_origin
        requested = started - requested_delta
        completed = started + timedelta(seconds=1)
        compile = data.Compile(
            id=uuid.uuid4(),
            remote_id=uuid.uuid4(),
            environment=environment,
            requested=requested,
            started=started,
            completed=completed,
            do_export=True,
            force_update=False,
            success=True,
            handled=True,
            version=1,
        )
        await compile.insert()

    async def add_compiles(environment: uuid.UUID, wait_times: abc.Sequence[float]):
        time_origin = datetime.now()
        for wait_time in wait_times:
            requested_offset = timedelta(seconds=wait_time)
            await _add_compile(environment, time_origin, requested_delta=requested_offset)

    project = data.Project(name="test")
    await project.insert()
    projects = await data.Project.get_list(name="test")
    assert len(projects) == 1
    project_id = projects[0].id

    env_uuid1 = uuid.uuid4()
    environment1: data.Environment = data.Environment(id=env_uuid1, project=project_id, name="testenv1")
    await environment1.insert()
    envs = await data.Environment.get_list(project=project_id)
    assert len(envs) == 1

    metrics_service = EnvironmentMetricsService()
    cwtmc = CompileWaitingTimeMetricsCollector()
    metrics_service.register_metric_collector(metrics_collector=cwtmc)

    # Insert a few compiles.
    wait_times: list[float] = [1.2, 2.3, 3.4]
    await add_compiles(env_uuid1, wait_times)
    await metrics_service.flush_metrics()

    result_timer = await data.EnvironmentMetricsTimer.get_list()

    expected_count = len(wait_times)
    expected_total_wait_time = functools.reduce(operator.add, wait_times)

    assert len(result_timer) == 1
    assert any(
        x.count == expected_count
        and x.metric_name == "orchestrator.compile_waiting_time"
        and x.environment == environment1.id
        and x.value == expected_total_wait_time
        for x in result_timer
    )

    # Create another environment and insert a few compiles in it.
    env_uuid2 = uuid.uuid4()
    environment2: data.Environment = data.Environment(id=env_uuid2, project=project_id, name="testenv2")
    await environment2.insert()

    envs = await data.Environment.get_list(project=project_id)
    assert len(envs) == 2

    wait_times: list[float] = [2.1, 4.3]
    await add_compiles(env_uuid2, wait_times)
    await metrics_service.flush_metrics()

    result_timer = await data.EnvironmentMetricsTimer.get_list()

    expected_count = len(wait_times)
    expected_total_wait_time = functools.reduce(operator.add, wait_times)

    # 1 new entry
    assert len(result_timer) == 2
    assert any(
        x.count == expected_count
        and x.metric_name == "orchestrator.compile_waiting_time"
        and x.environment == environment2.id
        and x.value == expected_total_wait_time
        for x in result_timer
    )

    # Add another set of compiles to the first environment.
    wait_times: list[float] = [1.1, 2.2, 3.3, 4.4]
    await add_compiles(env_uuid1, wait_times)

    await metrics_service.flush_metrics()

    result_timer = await data.EnvironmentMetricsTimer.get_list()

    expected_count = len(wait_times)
    expected_total_wait_time = functools.reduce(operator.add, wait_times)

    # 1 new entry
    assert len(result_timer) == 3
    assert any(
        x.count == expected_count
        and x.metric_name == "orchestrator.compile_waiting_time"
        and x.environment == environment1.id
        and x.value == expected_total_wait_time
        for x in result_timer
    )


async def test_compile_wait_time_metric_no_empty_datapoint(client, server):
    project = data.Project(name="test")
    await project.insert()

    env1 = data.Environment(name="env1", project=project.id)
    await env1.insert()

    env2 = data.Environment(name="env2", project=project.id)
    await env2.insert()

    envs = await data.Environment.get_list(project=project.id)
    assert len(envs) == 2

    metrics_service = EnvironmentMetricsService()
    collector = CompileWaitingTimeMetricsCollector()
    metrics_service.register_metric_collector(metrics_collector=collector)

    await metrics_service.flush_metrics()
    result_timer = await data.EnvironmentMetricsTimer.get_list()
    assert len(result_timer) == 0


@pytest.fixture
def server_with_dummy_metric_collectors(server: protocol.Server) -> AsyncIterator[protocol.Server]:
    class GaugeCollector1(MetricsCollector):
        def get_metric_name(self) -> str:
            return "gauge_metric1"

        def get_metric_type(self) -> MetricType:
            return MetricType.GAUGE

        async def get_metric_value(
            self, start_interval: datetime, end_interval: datetime, connection: asyncpg.connection.Connection
        ) -> Sequence[MetricValue]:
            return []

    class GaugeCollector2(MetricsCollector):
        def get_metric_name(self) -> str:
            return "gauge_metric2"

        def get_metric_type(self) -> MetricType:
            return MetricType.GAUGE

        async def get_metric_value(
            self, start_interval: datetime, end_interval: datetime, connection: asyncpg.connection.Connection
        ) -> Sequence[MetricValue]:
            return []

    class TimerCollector1(MetricsCollector):
        def get_metric_name(self) -> str:
            return "timer_metric1"

        def get_metric_type(self) -> MetricType:
            return MetricType.TIMER

        async def get_metric_value(
            self, start_interval: datetime, end_interval: datetime, connection: asyncpg.connection.Connection
        ) -> Sequence[MetricValue]:
            return []

    class TimerCollector2(MetricsCollector):
        def get_metric_name(self) -> str:
            return "timer_metric2"

        def get_metric_type(self) -> MetricType:
            return MetricType.TIMER

        async def get_metric_value(
            self, start_interval: datetime, end_interval: datetime, connection: asyncpg.connection.Connection
        ) -> Sequence[MetricValue]:
            return []

    env_metrics_service = cast(EnvironmentMetricsService, server.get_slice(SLICE_ENVIRONMENT_METRICS))
    env_metrics_service.register_metric_collector(GaugeCollector1())
    env_metrics_service.register_metric_collector(GaugeCollector2())
    env_metrics_service.register_metric_collector(TimerCollector1())
    env_metrics_service.register_metric_collector(TimerCollector2())
    yield server


async def test_get_environment_metrics_input_validation(server_with_dummy_metric_collectors, client, environment) -> None:
    """
    Verify that the input validation of the get_environment_metrics endpoint works as expected.
    """
    now = datetime.now()
    ten_hours_ago = now - timedelta(hours=10)
    # Unknown metric in metrics list
    result = await client.get_environment_metrics(
        tid=environment,
        metrics=["test"],
        start_interval=ten_hours_ago,
        end_interval=now,
        nb_datapoints=10,
    )
    assert result.code == 400
    assert "The following metrics given in the metrics parameter are unknown: ['test']" in result.result["message"]

    # start_interval and end_interval are the same
    result = await client.get_environment_metrics(
        tid=environment,
        metrics=["gauge_metric1", "timer_metric1"],
        start_interval=now,
        end_interval=now,
        nb_datapoints=10,
    )
    assert result.code == 400
    assert "start_interval should be strictly smaller than end_interval." in result.result["message"]

    # Number of datapoint is negative
    result = await client.get_environment_metrics(
        tid=environment,
        metrics=["gauge_metric1", "timer_metric1"],
        start_interval=ten_hours_ago,
        end_interval=now,
        nb_datapoints=0,
    )
    assert result.code == 400
    assert "nb_datapoints should be larger than 0" in result.result["message"]

    # Too much datapoints requested for time interval. Collection interval is only once every minute.
    result = await client.get_environment_metrics(
        tid=environment,
        metrics=["gauge_metric1", "timer_metric1"],
        start_interval=now - timedelta(minutes=5),
        end_interval=now,
        nb_datapoints=100,
    )
    assert result.code == 400
    assert (
        "start_interval and end_interval should be at least <nb_datapoints> minutes separated from each other."
        in result.result["message"]
    )


async def test_get_environment_metrics_api_endpoint(
    server_with_dummy_metric_collectors,
    client,
    project_default,
    environment_creator: Callable[[protocol.Client, str, str, bool], Awaitable[str]],
):
    """
    Verify whether the get_environment_metrics() endpoint correctly aggregates the data.
    """
    env1_id = await environment_creator(client, project_default, env_name="env1")
    env2_id = await environment_creator(client, project_default, env_name="env2")

    start_interval = datetime(year=2023, month=1, day=1, hour=9, minute=0).astimezone()
    await data.EnvironmentMetricsGauge.insert_many(
        [
            # Add 60 metrics within the aggregation interval requested later on in the test case
            # (2023-01-01 9:00 -> 2023-01-01 9:59). And one measurement at 2023-01-01 10:00 to verify that we do a correct
            # boundary check.
            data.EnvironmentMetricsGauge(
                environment=uuid.UUID(env1_id),
                metric_name="gauge_metric1",
                category=DEFAULT_CATEGORY,
                timestamp=start_interval + timedelta(minutes=i),
                # Add +3 to make sure we end up with a floating point number after aggregating the data.
                count=int(i / 6) if i % 6 != 0 else int(i / 6) + 3,
            )
            for i in range(61)
        ]
        + [
            # Add a value for a metric with a different name to make sure that the filtering works correctly.
            data.EnvironmentMetricsGauge(
                environment=uuid.UUID(env1_id),
                metric_name="gauge_metric2",
                category=DEFAULT_CATEGORY,
                timestamp=start_interval + timedelta(minutes=5),
                count=33,
            ),
        ]
        + [
            # Insert metric in a different environment to verify that the aggregations function respects the
            # environment boundary.
            data.EnvironmentMetricsGauge(
                environment=uuid.UUID(env2_id),
                metric_name="gauge_metric1",
                category=DEFAULT_CATEGORY,
                timestamp=start_interval + timedelta(minutes=5),
                count=44,
            ),
        ]
    )
    await data.EnvironmentMetricsTimer.insert_many(
        [
            # Add 60 metrics within the aggregation interval requested later on in the test case
            # (2023-01-01 9:00 -> 2023-01-01 9:59). And one measurement at 2023-01-01 10:00 to verify that we do a correct
            # boundary check.
            data.EnvironmentMetricsTimer(
                environment=uuid.UUID(env1_id),
                metric_name="timer_metric1",
                category=DEFAULT_CATEGORY,
                timestamp=start_interval + timedelta(minutes=i),
                count=2,
                # Add 0.25 to make sure we end up with a floating point number after aggregating the data.
                value=int(i / 6) + 0.25,
            )
            for i in range(61)
        ]
        + [
            # Add a value for a metric with a different name to make sure that the filtering works correctly.
            data.EnvironmentMetricsTimer(
                environment=uuid.UUID(env1_id),
                metric_name="timer_metric2",
                category=DEFAULT_CATEGORY,
                timestamp=start_interval + timedelta(minutes=5),
                count=33,
                value=66.6,
            ),
        ]
        + [
            # Insert metric in a different environment to verify that the aggregations function respects the
            # environment boundary.
            data.EnvironmentMetricsTimer(
                environment=uuid.UUID(env2_id),
                metric_name="timer_metric1",
                category=DEFAULT_CATEGORY,
                timestamp=start_interval + timedelta(minutes=5),
                count=44,
                value=77.7,
            ),
        ]
    )

    nb_datapoints = 10
    start_interval_plus_1h = start_interval + timedelta(hours=1)
    result = await client.get_environment_metrics(
        tid=env1_id,
        metrics=["gauge_metric1", "timer_metric1"],
        start_interval=start_interval,
        end_interval=start_interval_plus_1h,
        nb_datapoints=nb_datapoints,
    )
    assert result.code == 200, result.result
    assert parse_timestamp(result.result["data"]["start"]) == start_interval
    assert parse_timestamp(result.result["data"]["end"]) == start_interval_plus_1h
    expected_timestamps = [start_interval + timedelta(minutes=(i + 1) * 6) for i in range(nb_datapoints)]
    assert [parse_timestamp(timestamp) for timestamp in result.result["data"]["timestamps"]] == expected_timestamps
    assert len(result.result["data"]["metrics"]) == 2
    assert result.result["data"]["metrics"]["gauge_metric1"] == [sum(i for _ in range(6)) / 6 + 0.5 for i in range(10)]
    assert result.result["data"]["metrics"]["timer_metric1"] == [(sum(i for _ in range(6)) + 1.5) / (2 * 6) for i in range(10)]

    # Verify behavior when no data is available in the time window
    nb_datapoints = 2
    start_interval_min_6_min = start_interval - timedelta(minutes=6)
    start_interval_plus_6_min = start_interval + timedelta(minutes=6)
    result = await client.get_environment_metrics(
        tid=env1_id,
        metrics=["gauge_metric1"],
        start_interval=start_interval_min_6_min,
        end_interval=start_interval_plus_6_min,
        nb_datapoints=nb_datapoints,
    )
    assert result.code == 200, result.result
    assert parse_timestamp(result.result["data"]["start"]) == start_interval_min_6_min
    assert parse_timestamp(result.result["data"]["end"]) == start_interval_plus_6_min
    expected_timestamps = [start_interval, start_interval_plus_6_min]
    assert [parse_timestamp(timestamp) for timestamp in result.result["data"]["timestamps"]] == expected_timestamps
    assert len(result.result["data"]["metrics"]) == 1
    assert result.result["data"]["metrics"]["gauge_metric1"] == [None, 0.5]

    # Verify behavior when partial data is available in the time window
    nb_datapoints = 1
    result = await client.get_environment_metrics(
        tid=env1_id,
        metrics=["gauge_metric1"],
        start_interval=start_interval_min_6_min,
        end_interval=start_interval_plus_6_min,
        nb_datapoints=nb_datapoints,
    )
    assert result.code == 200, result.result
    assert parse_timestamp(result.result["data"]["start"]) == start_interval_min_6_min
    assert parse_timestamp(result.result["data"]["end"]) == start_interval_plus_6_min
    expected_timestamps = [start_interval_plus_6_min]
    assert [parse_timestamp(timestamp) for timestamp in result.result["data"]["timestamps"]] == expected_timestamps
    assert len(result.result["data"]["metrics"]) == 1
    assert result.result["data"]["metrics"]["gauge_metric1"] == [0.5]


async def test_compile_rate_metric(
    server_with_dummy_metric_collectors,
    client,
    project_default,
    environment_creator: Callable[[protocol.Client, str, str, bool], Awaitable[str]],
) -> None:
    """
    Verify whether the compile_rate metric is aggregated correctly.
    """
    env1_id = await environment_creator(client, project_default, env_name="env1")
    env2_id = await environment_creator(client, project_default, env_name="env2")

    start_interval = datetime(year=2023, month=1, day=1, hour=9, minute=0).astimezone()
    await data.EnvironmentMetricsTimer.insert_many(
        [
            # Add 60 metrics within the aggregation interval requested later on in the test case
            # (2023-01-01 9:00 -> 2023-01-01 9:59). And one measurement at 2023-01-01 10:00 to verify that we do a correct
            # boundary check.
            data.EnvironmentMetricsTimer(
                environment=uuid.UUID(env1_id),
                metric_name="orchestrator.compile_time",
                category=DEFAULT_CATEGORY,
                timestamp=start_interval + timedelta(minutes=i),
                count=i,
                value=float(i),
            )
            for i in range(61)
        ]
        + [
            # Add a value for a metric with a different name to make sure that the filtering works correctly.
            data.EnvironmentMetricsTimer(
                environment=uuid.UUID(env1_id),
                metric_name="timer_metric1",
                category=DEFAULT_CATEGORY,
                timestamp=start_interval + timedelta(minutes=5),
                count=33,
                value=float(22),
            ),
        ]
        + [
            # Insert metric in a different environment to verify that the aggregations function respects the
            # environment boundary.
            data.EnvironmentMetricsTimer(
                environment=uuid.UUID(env2_id),
                metric_name="orchestrator.compile_time",
                category=DEFAULT_CATEGORY,
                timestamp=start_interval + timedelta(minutes=5),
                count=44,
                value=float(211),
            ),
        ]
    )

    start_interval = datetime(year=2023, month=1, day=1, hour=9, minute=0).astimezone()
    end_interval = start_interval + timedelta(hours=1)
    nb_datapoints = 10
    result = await client.get_environment_metrics(
        tid=env1_id,
        metrics=["orchestrator.compile_rate"],
        start_interval=start_interval,
        end_interval=end_interval,
        nb_datapoints=nb_datapoints,
    )
    assert result.code == 200, result.result

    assert parse_timestamp(result.result["data"]["start"]) == start_interval
    assert parse_timestamp(result.result["data"]["end"]) == end_interval
    expected_timestamps = [start_interval + timedelta(minutes=(i + 1) * 6) for i in range(nb_datapoints)]
    assert [parse_timestamp(timestamp) for timestamp in result.result["data"]["timestamps"]] == expected_timestamps
    assert len(result.result["data"]["metrics"]) == 1
    assert result.result["data"]["metrics"]["orchestrator.compile_rate"] == [
        sum((i * 6) + j for j in range(6)) * nb_datapoints for i in range(nb_datapoints)
    ]

    # The value 0 should be returned when no data is available
    start_interval = datetime(year=2023, month=1, day=2, hour=9, minute=0).astimezone()
    end_interval = start_interval + timedelta(hours=1)
    nb_datapoints = 10
    result = await client.get_environment_metrics(
        tid=env1_id,
        metrics=["orchestrator.compile_rate"],
        start_interval=start_interval,
        end_interval=end_interval,
        nb_datapoints=nb_datapoints,
    )
    assert result.code == 200
    assert parse_timestamp(result.result["data"]["start"]) == start_interval
    assert parse_timestamp(result.result["data"]["end"]) == end_interval
    expected_timestamps = [start_interval + timedelta(minutes=(i + 1) * 6) for i in range(nb_datapoints)]
    assert [parse_timestamp(timestamp) for timestamp in result.result["data"]["timestamps"]] == expected_timestamps
    assert len(result.result["data"]["metrics"]) == 1
    assert all(m == 0 for m in result.result["data"]["metrics"]["orchestrator.compile_rate"])


async def test_metric_aggregation_no_date(
    server_with_dummy_metric_collectors,
    client,
    project_default,
    environment_creator: Callable[[protocol.Client, str, str, bool], Awaitable[str]],
):
    """
    Verify the behavior of the `get_environment_metrics` endpoint when no datapoints are present in the database.
    """
    env1_id = await environment_creator(client, project_default, env_name="env1")

    start_interval = datetime.now().astimezone()
    end_interval = start_interval + timedelta(hours=1)
    nb_datapoints = 10
    result = await client.get_environment_metrics(
        tid=env1_id,
        metrics=["gauge_metric1"],
        start_interval=start_interval,
        end_interval=end_interval,
        nb_datapoints=nb_datapoints,
    )
    assert result.code == 200, result.result
    assert parse_timestamp(result.result["data"]["start"]) == start_interval
    assert parse_timestamp(result.result["data"]["end"]) == end_interval
    expected_timestamps = [start_interval + timedelta(minutes=(i + 1) * 6) for i in range(nb_datapoints)]
    assert [parse_timestamp(timestamp) for timestamp in result.result["data"]["timestamps"]] == expected_timestamps
    assert len(result.result["data"]["metrics"]) == 1
    assert result.result["data"]["metrics"]["gauge_metric1"] == [None for _ in range(10)]


@pytest.mark.parametrize("env1_halted", [True, False])
@pytest.mark.parametrize("env2_halted", [True, False])
async def test_cleanup_environment_metrics(init_dataclasses_and_load_schema, env1_halted, env2_halted) -> None:
    """
    Verify that the query to clean up old environment metrics is working correctly.
    """
    project = data.Project(name="test")
    await project.insert()

    # Do cleanup operation when there are no environments
    environment_metrics_service = EnvironmentMetricsService()
    await environment_metrics_service._cleanup_old_metrics()

    env1 = data.Environment(name="dev1", project=project.id, repo_url="", repo_branch="")
    await env1.insert()
    await env1.set(data.ENVIRONMENT_METRICS_RETENTION, 1)
    env2 = data.Environment(name="dev2", project=project.id, repo_url="", repo_branch="")
    await env2.insert()
    await env2.set(data.ENVIRONMENT_METRICS_RETENTION, 3)

    if env1_halted:
        await env1.update_fields(halted=True)
    if env2_halted:
        await env2.update_fields(halted=True)

    now = datetime.now().astimezone(tz=timezone.utc)
    timestamps_metrics = [
        now,
        now - timedelta(minutes=30),
        now - timedelta(hours=1, minutes=1),
        now - timedelta(days=1),
    ]
    for env_id in [env1.id, env2.id]:
        for timestamp in timestamps_metrics:
            await data.EnvironmentMetricsGauge(
                environment=env_id,
                metric_name="test1",
                category="group1",
                timestamp=timestamp,
                count=54,
            ).insert(),
            await data.EnvironmentMetricsTimer(
                environment=env_id,
                metric_name="test2",
                category="group2",
                timestamp=timestamp,
                count=11,
                value=22.0,
            ).insert(),

    assert len(await data.EnvironmentMetricsGauge.get_list()) == 8
    assert len(await data.EnvironmentMetricsTimer.get_list()) == 8

    # Do cleanup operation
    environment_metrics_service = EnvironmentMetricsService()
    await environment_metrics_service._cleanup_old_metrics()

    nmbr_environment_metricsgauge_after_cleanup_env1 = 4 if env1_halted else 2
    nmbr_environment_metricsgauge_after_cleanup_env2 = 4 if env2_halted else 3
    nmbr_environment_metricstimer_after_cleanup_env1 = 4 if env1_halted else 2
    nmbr_environment_metricstimer_after_cleanup_env2 = 4 if env2_halted else 3

    env_metrics_gauge = await data.EnvironmentMetricsGauge.get_list()
    env_metrics_timer = await data.EnvironmentMetricsTimer.get_list()

    assert (
        len(env_metrics_gauge)
        == nmbr_environment_metricsgauge_after_cleanup_env1 + nmbr_environment_metricsgauge_after_cleanup_env2
    )
    assert (
        len(env_metrics_timer)
        == nmbr_environment_metricstimer_after_cleanup_env1 + nmbr_environment_metricstimer_after_cleanup_env2
    )

    # verify that the right metrics are cleaned up

    if not (env2_halted or env1_halted):
        # 2 metrics are removed from env1 per table
        for data_cls in [data.EnvironmentMetricsGauge, data.EnvironmentMetricsTimer]:
            result = await data_cls.get_list(environment=env1.id)
            assert sorted([r.timestamp for r in result], reverse=True) == timestamps_metrics[0:2]
        # 1 metric is removed from env2 per table
        for data_cls in [data.EnvironmentMetricsGauge, data.EnvironmentMetricsTimer]:
            result = await data_cls.get_list(environment=env2.id)
            assert sorted([r.timestamp for r in result], reverse=True) == timestamps_metrics[0:3]


@pytest.mark.parametrize(
    "start_interval_request, end_interval_request, nb_datapoints_request",
    [
        # Verify that the rounding works correctly
        (
            datetime(year=2023, month=1, day=1, hour=2, minute=16, second=52, microsecond=33, tzinfo=timezone.utc),
            datetime(year=2023, month=1, day=2, hour=15, minute=12, second=22, microsecond=44, tzinfo=timezone.utc),
            10,
        ),
        # Verify that no rounding is done when the given parameters are already rounded
        (
            datetime(year=2023, month=1, day=1, hour=0, tzinfo=timezone.utc),
            datetime(year=2023, month=1, day=2, hour=18, tzinfo=timezone.utc),
            14,
        ),
    ],
)
async def test_get_environment_metrics_api_endpoint_round_timestamp(
    server_with_dummy_metric_collectors,
    client,
    project_default,
    environment_creator: Callable[[protocol.Client, str, str, bool], Awaitable[str]],
    start_interval_request: datetime,
    end_interval_request: datetime,
    nb_datapoints_request: int,
):
    """
    Verify whether the get_environment_metrics() endpoint rounds the timestamps correctly when the
    round_timestamps option is set to True.
    """
    env_id = await environment_creator(client, project_default, env_name="env1")

    # The expected parameters after rounding
    start_interval_reply = datetime(year=2023, month=1, day=1, hour=0, tzinfo=timezone.utc)
    end_interval_reply = datetime(year=2023, month=1, day=2, hour=18, tzinfo=timezone.utc)
    nb_datapoints_reply = 14

    # Insert one metric every hour
    timestamp = datetime(year=2023, month=1, day=1, hour=0, minute=33, second=42, tzinfo=timezone.utc)
    while timestamp < end_interval_reply:
        await data.EnvironmentMetricsGauge(
            environment=uuid.UUID(env_id),
            metric_name="gauge_metric1",
            category=DEFAULT_CATEGORY,
            timestamp=timestamp,
            count=5,
        ).insert()
        timestamp += timedelta(hours=1)

    # Insert additional metrics on the boundary of the first time window to verify that the aggregation logic respects
    # the time window boundaries correctly.
    await data.EnvironmentMetricsGauge(
        environment=uuid.UUID(env_id),
        metric_name="gauge_metric1",
        category=DEFAULT_CATEGORY,
        timestamp=start_interval_reply + timedelta(hours=3) - timedelta(seconds=1),
        count=1,
    ).insert()
    await data.EnvironmentMetricsGauge(
        environment=uuid.UUID(env_id),
        metric_name="gauge_metric1",
        category=DEFAULT_CATEGORY,
        timestamp=start_interval_reply + timedelta(hours=3),
        count=2,
    ).insert()
    await data.EnvironmentMetricsGauge(
        environment=uuid.UUID(env_id),
        metric_name="gauge_metric1",
        category=DEFAULT_CATEGORY,
        timestamp=start_interval_reply + timedelta(hours=3) + timedelta(seconds=1),
        count=3,
    ).insert()

    result = await client.get_environment_metrics(
        tid=env_id,
        metrics=["gauge_metric1"],
        start_interval=start_interval_request,
        end_interval=end_interval_request,
        nb_datapoints=nb_datapoints_request,
        round_timestamps=True,
    )

    assert result.code == 200, result.result
    assert start_interval_reply == parse_timestamp(result.result["data"]["start"])
    assert end_interval_reply == parse_timestamp(result.result["data"]["end"])
    timestamps = [parse_timestamp(t) for t in result.result["data"]["timestamps"]]
    assert len(timestamps) == nb_datapoints_reply
    assert timestamps == [start_interval_reply + timedelta(hours=3) * (i + 1) for i in range(nb_datapoints_reply)]
    expected_metrics = [5.0 for _ in range(nb_datapoints_reply)]
    # Take the additional datapoints on the boundary of the first two time windows into account
    expected_metrics[0] = (3 * 5 + 1) / 4
    expected_metrics[1] = (3 * 5 + 2 + 3) / 5
    assert result.result["data"]["metrics"]["gauge_metric1"] == expected_metrics


async def test_get_environment_metrics_interval_too_short(server_with_dummy_metric_collectors, client, environment):
    """
    Verify that an exception is raised when the get_environment_metrics() endpoint is called with the
    round_timestamps set to True and the provided interval is too short with respect to the
    number of requested datapoints.
    """
    result = await client.get_environment_metrics(
        tid=environment,
        metrics=["gauge_metric1"],
        start_interval=datetime(year=2023, month=1, day=1, hour=6, minute=33).astimezone(),
        end_interval=datetime(year=2023, month=1, day=1, hour=7, minute=22).astimezone(),
        nb_datapoints=2,
        round_timestamps=True,
    )
    assert result.code == 400
    assert (
        "Invalid request: When round_timestamps is set to True, the number of hours between"
        " start_interval and end_interval should be at least the amount of hours equal to"
        " nb_datapoints." in result.result["message"]
    )
