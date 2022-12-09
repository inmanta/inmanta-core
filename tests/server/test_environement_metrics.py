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
from datetime import datetime
from typing import Optional

import asyncpg
import pytest

from inmanta import data
from inmanta.server.services.environment_metrics_service import (
    EnvironmentMetricsService,
    MetricsCollector,
    MetricType,
    MetricValue,
    MetricValueTimer,
    ResourceCountMetricsCollector,
)
from inmanta.util import get_compiler_version

env_uuid = uuid.uuid4()

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
        ("bad.name", "ok", 'The character "." can not be used in the metric_name (bad.name)'),
        ("ok_name", "not.ok", 'The character "." can not be used in the grouped_by value (not.ok)'),
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
    assert result[0].metric_name == "dummy_gauge_multi.up"
    assert isinstance(result[0].timestamp, datetime)
    assert result[1].count == 2
    assert result[1].metric_name == "dummy_gauge_multi.down"
    assert isinstance(result[1].timestamp, datetime)
    assert result[2].count == 3
    assert result[2].metric_name == "dummy_gauge_multi.left"
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
    assert result[0].metric_name == "dummy_timer_multi.up"
    assert isinstance(result[0].timestamp, datetime)
    assert result[1].count == 13
    assert result[1].value == 50.50 * 2
    assert result[1].metric_name == "dummy_timer_multi.down"
    assert isinstance(result[1].timestamp, datetime)
    assert result[2].count == 23
    assert result[2].value == 50.50 * 3
    assert result[2].metric_name == "dummy_timer_multi.left"
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


async def test_resource_count_metric(clienthelper, environment, client, agent):
    metrics_service = EnvironmentMetricsService()
    version = str(await clienthelper.get_version())
    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=" + version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Resource[agent1,key=key2],v=" + version,
            "send_event": False,
            "requires": [],
            "purged": False,
        },
        {
            "key": "key3",
            "value": "value3",
            "id": "test::Resource[agent1,key=key3],v=" + version,
            "send_event": False,
            "requires": [],
            "purged": True,
        },
    ]

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    test = await data.Resource.get_list()
    print(test)
    rcmc = ResourceCountMetricsCollector()
    metrics_service.register_metric_collector(metrics_collector=rcmc)

    # flush the metrics for the first time: 1 record (3 resources in available state)
    await metrics_service.flush_metrics()
    result_gauge = await data.EnvironmentMetricsGauge.get_list()
    assert len(result_gauge) == 1
    assert result_gauge[0].metric_name == "resource_count.available"
    assert result_gauge[0].count == 3

    # change the state of one of the resources
    now = datetime.now()
    action_id = uuid.uuid4()
    aclient = agent._client
    result = await aclient.resource_action_update(
        environment,
        ["test::Resource[agent1,key=key1],v=" + version],
        action_id,
        "deploy",
        now,
        now,
        "deployed",
        [],
        {},
    )

    assert result.code == 200

    # flush the metrics for the second time: 1 old record (3 resources in available state)
    # + 2 new records (2 resources in available state, 1 in the deployed state)
    await metrics_service.flush_metrics()
    result_gauge = await data.EnvironmentMetricsGauge.get_list()
    assert len(result_gauge) == 3
    assert result_gauge[0].metric_name == "resource_count.available"
    assert result_gauge[0].count == 3
    assert result_gauge[1].metric_name == "resource_count.available"
    assert result_gauge[1].count == 2
    assert result_gauge[2].metric_name == "resource_count.deployed"
    assert result_gauge[2].count == 1
    assert result_gauge[2].timestamp == result_gauge[1].timestamp
    assert result_gauge[0].timestamp < result_gauge[1].timestamp
