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
)


@pytest.fixture
async def env_metrics_service(server_config, init_dataclasses_and_load_schema) -> EnvironmentMetricsService:
    metrics_service = EnvironmentMetricsService()
    yield metrics_service


class DummyGaugeMetric(MetricsCollector):
    def get_metric_name(self) -> str:
        return "dummy_gauge"

    def get_metric_type(self) -> MetricType:
        return MetricType.GAUGE

    async def get_metric_value(
        self, start_interval: datetime, end_interval: datetime, connection: Optional[asyncpg.connection.Connection]
    ) -> Sequence[MetricValue]:
        a = MetricValue("dummy_gauge", 1)
        return [a]


class DummyGaugeMetricMulti(MetricsCollector):
    def get_metric_name(self) -> str:
        return "dummy_gauge_multi"

    def get_metric_type(self) -> MetricType:
        return MetricType.GAUGE

    async def get_metric_value(
        self, start_interval: datetime, end_interval: datetime, connection: Optional[asyncpg.connection.Connection]
    ) -> Sequence[MetricValue]:
        a = MetricValue("dummy_gauge_up", 1)
        b = MetricValue("dummy_gauge_down", 2)
        c = MetricValue("dummy_gauge_left", 3)
        return [a, b, c]


class DummyTimerMetric(MetricsCollector):
    def get_metric_name(self) -> str:
        return "dummy_timer"

    def get_metric_type(self) -> MetricType:
        return MetricType.TIMER

    async def get_metric_value(
        self, start_interval: datetime, end_interval: datetime, connection: Optional[asyncpg.connection.Connection]
    ) -> Sequence[MetricValueTimer]:
        a = MetricValueTimer("dummy_timer", 3, 50.50)
        return [a]


class DummyTimerMetricMulti(MetricsCollector):
    def get_metric_name(self) -> str:
        return "dummy_timer"

    def get_metric_type(self) -> MetricType:
        return MetricType.TIMER

    async def get_metric_value(
        self, start_interval: datetime, end_interval: datetime, connection: Optional[asyncpg.connection.Connection]
    ) -> Sequence[MetricValueTimer]:
        a = MetricValueTimer("dummy_timer_up", 3, 50.50 * 1)
        b = MetricValueTimer("dummy_timer_down", 13, 50.50 * 2)
        c = MetricValueTimer("dummy_timer_left", 23, 50.50 * 3)
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


async def test_flush_metrics_gauge(env_metrics_service):
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


async def test_flush_metrics_gauge_multi(env_metrics_service):
    dummy_gauge = DummyGaugeMetricMulti()
    env_metrics_service.register_metric_collector(metrics_collector=dummy_gauge)

    previous_timestamp: datetime = env_metrics_service.previous_timestamp
    await env_metrics_service.flush_metrics()
    assert previous_timestamp < env_metrics_service.previous_timestamp
    result = await data.EnvironmentMetricsGauge.get_list()
    assert len(result) == 3
    assert result[0].count == 1
    assert result[0].metric_name == "dummy_gauge_up"
    assert isinstance(result[0].timestamp, datetime)
    assert result[1].count == 2
    assert result[1].metric_name == "dummy_gauge_down"
    assert isinstance(result[1].timestamp, datetime)
    assert result[2].count == 3
    assert result[2].metric_name == "dummy_gauge_left"
    assert isinstance(result[2].timestamp, datetime)

    await env_metrics_service.flush_metrics()
    await env_metrics_service.flush_metrics()

    result = await data.EnvironmentMetricsGauge.get_list()
    assert len(result) == 9


async def test_flush_metrics_timer(env_metrics_service):
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


async def test_flush_metrics_timer_multi(env_metrics_service):
    dummy_timer = DummyTimerMetricMulti()
    env_metrics_service.register_metric_collector(metrics_collector=dummy_timer)

    previous_timestamp: datetime = env_metrics_service.previous_timestamp
    await env_metrics_service.flush_metrics()
    assert previous_timestamp < env_metrics_service.previous_timestamp
    result = await data.EnvironmentMetricsTimer.get_list()
    assert len(result) == 3
    assert result[0].count == 3
    assert result[0].value == 50.50
    assert result[0].metric_name == "dummy_timer_up"
    assert isinstance(result[0].timestamp, datetime)
    assert result[1].count == 13
    assert result[1].value == 50.50 * 2
    assert result[1].metric_name == "dummy_timer_down"
    assert isinstance(result[1].timestamp, datetime)
    assert result[2].count == 23
    assert result[2].value == 50.50 * 3
    assert result[2].metric_name == "dummy_timer_left"
    assert isinstance(result[2].timestamp, datetime)

    await env_metrics_service.flush_metrics()
    await env_metrics_service.flush_metrics()

    result = await data.EnvironmentMetricsTimer.get_list()
    assert len(result) == 9


async def test_flush_metrics_mix(env_metrics_service):
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
