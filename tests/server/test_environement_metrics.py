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
import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import List, Optional

import asyncpg
import pytest

from inmanta import const, data
from inmanta.server.services.environment_metrics_service import (
    AgentCountMetricsCollector,
    CompileTimeMetricsCollector,
    EnvironmentMetricsService,
    MetricsCollector,
    MetricType,
    MetricValue,
    MetricValueTimer,
    ResourceCountMetricsCollector,
)
from inmanta.util import get_compiler_version
from utils import ClientHelper

env_uuid = uuid.uuid4()


@pytest.fixture
async def env_metrics_service(server_config, init_dataclasses_and_load_schema) -> EnvironmentMetricsService:
    metrics_service = EnvironmentMetricsService()
    yield metrics_service


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
    ) -> Sequence[MetricValue]:
        a = MetricValue("dummy_gauge", 1, env_uuid)
        return [a]


class DummyGaugeMetricMulti(MetricsCollector):
    def get_metric_name(self) -> str:
        return "dummy_gauge_multi"

    def get_metric_type(self) -> MetricType:
        return MetricType.GAUGE

    async def get_metric_value(
        self, start_interval: datetime, end_interval: datetime, connection: Optional[asyncpg.connection.Connection]
    ) -> Sequence[MetricValue]:
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
    ) -> Sequence[MetricValueTimer]:
        a = MetricValueTimer("dummy_timer", 3, 50.50, env_uuid)
        return [a]


class DummyTimerMetricMulti(MetricsCollector):
    def get_metric_name(self) -> str:
        return "dummy_timer_multi"

    def get_metric_type(self) -> MetricType:
        return MetricType.TIMER

    async def get_metric_value(
        self, start_interval: datetime, end_interval: datetime, connection: Optional[asyncpg.connection.Connection]
    ) -> Sequence[MetricValueTimer]:
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


@pytest.mark.parametrize(
    "metric_name, grouped_by, error_msg",
    [
        ("bad#name", "ok", 'The character "#" can not be used in the metric_name (bad#name)'),
        ("ok_name", "not#ok", 'The character "#" can not be used in the grouped_by value (not#ok)'),
    ],
)
async def test_bad_name_metric(env_metrics_service, metric_name, grouped_by, error_msg):
    class BadNameMetric(MetricsCollector):
        def get_metric_name(self) -> str:
            return metric_name

        def get_metric_type(self) -> MetricType:
            return MetricType.GAUGE

        async def get_metric_value(
            self, start_interval: datetime, end_interval: datetime, connection: Optional[asyncpg.connection.Connection]
        ) -> Sequence[MetricValueTimer]:
            a = MetricValue(self.get_metric_name(), 10, env_uuid, grouped_by)
            return [a]

    with pytest.raises(Exception) as e:
        bad_name = BadNameMetric()
        env_metrics_service.register_metric_collector(metrics_collector=bad_name)
        await env_metrics_service.flush_metrics()
    assert error_msg in str(e.value)


async def test_bad_type_metric(env_metrics_service):
    class BadTypeMetric(MetricsCollector):
        def get_metric_name(self) -> str:
            return "bad_type"

        def get_metric_type(self) -> MetricType:
            return MetricType.TIMER

        async def get_metric_value(
            self, start_interval: datetime, end_interval: datetime, connection: Optional[asyncpg.connection.Connection]
        ) -> Sequence[MetricValue]:
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
    assert result[0].metric_name == "dummy_gauge_multi#up"
    assert isinstance(result[0].timestamp, datetime)
    assert result[1].count == 2
    assert result[1].metric_name == "dummy_gauge_multi#down"
    assert isinstance(result[1].timestamp, datetime)
    assert result[2].count == 3
    assert result[2].metric_name == "dummy_gauge_multi#left"
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
    assert result[0].metric_name == "dummy_timer_multi#up"
    assert isinstance(result[0].timestamp, datetime)
    assert result[1].count == 13
    assert result[1].value == 50.50 * 2
    assert result[1].metric_name == "dummy_timer_multi#down"
    assert isinstance(result[1].timestamp, datetime)
    assert result[2].count == 23
    assert result[2].value == 50.50 * 3
    assert result[2].metric_name == "dummy_timer_multi#left"
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
        ) -> Sequence[MetricValue]:
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
    It then flushes the resource_count metric a first time. This creates 2 records in EnvironmentMetricsGauge:
    - one for the first environment with 3 resources in the latest version in the available state.
    - one for the second environment with 2 resources in the latest version in the available state.
    following this, the state of one resource in the first environment is updated and the metrics are flushed again.
    This creates 3 records in EnvironmentMetricsGauge:
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

    # adds the ResourceCountMetricsCollector
    rcmc = ResourceCountMetricsCollector()
    metrics_service.register_metric_collector(metrics_collector=rcmc)

    # flush the metrics for the first time: 2 record (3 resources in available state for the first
    # environment and 2 for the second)
    await metrics_service.flush_metrics()
    result_gauge = await data.EnvironmentMetricsGauge.get_list()
    assert len(result_gauge) == 2
    assert any(
        x.count == 3 and x.metric_name == "resource.resource_count#available" and x.environment == env_uuid1
        for x in result_gauge
    )
    assert any(
        x.count == 2 and x.metric_name == "resource.resource_count#available" and x.environment == env_uuid2
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

    # flush the metrics for the second time: 2 old record +
    # + 3 new records (1 for available state and one for the deployed state for the first environment
    # and one for the available state for the second environment)
    await metrics_service.flush_metrics()
    result_gauge = await data.EnvironmentMetricsGauge.get_list()
    assert len(result_gauge) == 5
    assert any(
        x.count == 3 and x.metric_name == "resource.resource_count#available" and x.environment == env_uuid1
        for x in result_gauge
    )
    assert any(
        x.count == 2 and x.metric_name == "resource.resource_count#available" and x.environment == env_uuid1
        for x in result_gauge
    )
    assert any(
        x.count == 1 and x.metric_name == "resource.resource_count#deployed" and x.environment == env_uuid1
        for x in result_gauge
    )

    env_uuid2_records = [
        r
        for r in result_gauge
        if r.environment == env_uuid2 and r.metric_name == "resource.resource_count#available" and r.count == 2
    ]

    assert len(env_uuid2_records) == 2


async def test_resource_count_metric_released(clienthelper, client, server, agent):
    """
    test that only the latest released version is used for the metrics:
    - adds a first version with 3 resources and a second one with one resource but don't deploy them
    - deploy only the first one
    - verify the flushed data comes from the first version
    """
    env_uuid1 = uuid.uuid4()
    project = data.Project(name="test")
    await project.insert()
    projects = await data.Project.get_list(name="test")
    assert len(projects) == 1
    project_id = projects[0].id
    environment1: data.Environment = data.Environment(id=env_uuid1, project=project_id, name="testenv1")
    await environment1.insert()
    envs = await data.Environment.get_list(project=project_id)
    assert len(envs) == 1
    version1 = str(await ClientHelper(client, env_uuid1).get_version())

    result = await client.set_setting(tid=env_uuid1, id="auto_deploy", value=False)
    assert result.code == 200

    resources_env1_v1 = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=" + version1,
            "send_event": False,
            "requires": [],
            "purged": False,
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Resource[agent1,key=key2],v=" + version1,
            "send_event": False,
            "requires": [],
            "purged": True,
        },
        {
            "key": "key3",
            "value": "value3",
            "id": "test::Resource[agent1,key=key3],v=" + version1,
            "send_event": False,
            "requires": [],
            "purged": True,
        },
    ]
    result = await client.put_version(
        tid=env_uuid1,
        version=version1,
        resources=resources_env1_v1,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200
    version2 = str(await ClientHelper(client, env_uuid1).get_version())
    resources_env1_v2 = [
        {
            "key": "key5",
            "value": "value5",
            "id": "test::Resource[agent1,key=key5],v=" + version2,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]
    result = await client.put_version(
        tid=env_uuid1,
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

    result = await client.release_version(env_uuid1, version1, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    await metrics_service.flush_metrics()
    result_gauge = await data.EnvironmentMetricsGauge.get_list()
    assert len(result_gauge) == 1
    assert any(
        x.count == 3 and x.metric_name == "resource.resource_count#available" and x.environment == env_uuid1
        for x in result_gauge
    )


async def test_agent_count_metric(clienthelper, client, agent):
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

    agents = await data.Agent.get_list()
    assert len(agents) == 2

    # adds the AgentCountMetricsCollector
    acmc = AgentCountMetricsCollector()
    metrics_service.register_metric_collector(metrics_collector=acmc)

    # flush the metrics for the first time: 2 record (1 agent in paused state for the first
    # environment and 1 for the second)
    await metrics_service.flush_metrics()
    result_gauge = await data.EnvironmentMetricsGauge.get_list()
    assert len(result_gauge) == 2
    assert any(
        x.count == 1 and x.metric_name == "resource.agent_count#paused" and x.environment == env1.id for x in result_gauge
    )
    assert any(
        x.count == 1 and x.metric_name == "resource.agent_count#paused" and x.environment == env2.id for x in result_gauge
    )


async def test_compile_time_metric(clienthelper, client, agent):
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

    async def add_compiles(environment: uuid.UUID, compile_times: Sequence[float]):
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
    compile_times: List[float] = [1.2, 2.3, 3.4]
    await add_compiles(env_uuid1, compile_times)

    await metrics_service.flush_metrics()

    result_gauge = await data.EnvironmentMetricsTimer.get_list()

    expected_count = len(compile_times)
    expected_total_compile_time = sum(compile_times)

    assert len(result_gauge) == 1
    assert any(
        x.count == expected_count
        and x.metric_name == "orchestrator.compile_time"
        and x.environment == environment1.id
        and x.value == expected_total_compile_time
        for x in result_gauge
    )

    # Create another environment and insert a few compiles in it.
    env_uuid2 = uuid.uuid4()
    environment2: data.Environment = data.Environment(id=env_uuid2, project=project_id, name="testenv2")
    await environment2.insert()

    envs = await data.Environment.get_list(project=project_id)
    assert len(envs) == 2

    compile_times: List[float] = [2.1, 4.3]
    await add_compiles(env_uuid2, compile_times)

    await metrics_service.flush_metrics()

    result_gauge = await data.EnvironmentMetricsTimer.get_list()

    expected_count = len(compile_times)
    expected_total_compile_time = sum(compile_times)

    assert len(result_gauge) == 2
    assert any(
        x.count == expected_count
        and x.metric_name == "orchestrator.compile_time"
        and x.environment == environment2.id
        and x.value == expected_total_compile_time
        for x in result_gauge
    )

    # Add another set of compiles to the first environment.
    compile_times: List[float] = [1.1, 2.2, 3.3, 4.4]
    await add_compiles(env_uuid1, compile_times)

    await metrics_service.flush_metrics()

    result_gauge = await data.EnvironmentMetricsTimer.get_list()

    expected_count = len(compile_times)
    expected_total_compile_time = sum(compile_times)

    assert len(result_gauge) == 3
    assert any(
        x.count == expected_count
        and x.metric_name == "orchestrator.compile_time"
        and x.environment == environment1.id
        and x.value == expected_total_compile_time
        for x in result_gauge
    )
