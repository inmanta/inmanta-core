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
import logging
from datetime import datetime

import pytest

from inmanta import data
from inmanta.server.protocol import Server
from inmanta.server.services.environment_metrics_service import EnvironmentMetricsService, MetricsCollector, MetricType
from utils import log_contains


@pytest.fixture
async def env_metrics_service(server_config, init_dataclasses_and_load_schema):
    metrics_service = EnvironmentMetricsService()
    yield metrics_service


class DummyCountMetric(MetricsCollector):
    async def get_metric_value(self, start_interval: datetime, end_interval: datetime) -> object:
        return {"count": 1}


class DummyNonCountMetric(MetricsCollector):
    async def get_metric_value(self, start_interval: datetime, end_interval: datetime) -> object:
        return {"count": 2, "value": 100}


async def test_register_metrics_collector(env_metrics_service):
    dummy_count = DummyCountMetric("dummy_count", MetricType.count)
    dummy_non_count = DummyNonCountMetric("dummy_non_count", MetricType.non_count)
    env_metrics_service.register_metric_collector(metrics_collector=dummy_count)
    env_metrics_service.register_metric_collector(metrics_collector=dummy_non_count)

    assert len(EnvironmentMetricsService.metrics_collectors) == 2


async def test_register_same_metrics_collector(env_metrics_service, caplog):
    dummy_count = DummyCountMetric("dummy_count", MetricType.count)
    dummy_count2 = DummyCountMetric("dummy_count", MetricType.count)
    env_metrics_service.register_metric_collector(metrics_collector=dummy_count)
    env_metrics_service.register_metric_collector(metrics_collector=dummy_count2)
    log_contains(
        caplog,
        "inmanta.server.services.environment_metrics_service",
        logging.WARNING,
        "There already is a metric collector with the name dummy_count",
    )


async def test_flush_metrics_count(env_metrics_service):
    dummy_count = DummyCountMetric("dummy_count", MetricType.count)
    env_metrics_service.register_metric_collector(metrics_collector=dummy_count)

    await env_metrics_service.flush_metrics()
    result = await data.EnvironmentMetricsCounter.get_list()
    assert len(result) == 1
    assert result[0].count == 1
    assert result[0].metric_name == "dummy_count"
    assert isinstance(result[0].timestamp, datetime)

    await env_metrics_service.flush_metrics()
    await env_metrics_service.flush_metrics()

    result = await data.EnvironmentMetricsCounter.get_list()
    assert len(result) == 3


async def test_flush_metrics_non_count(env_metrics_service):
    dummy_non_count = DummyNonCountMetric("dummy_non_count", MetricType.non_count)
    env_metrics_service.register_metric_collector(metrics_collector=dummy_non_count)

    await env_metrics_service.flush_metrics()
    result = await data.EnvironmentMetricsNonCounter.get_list()
    assert len(result) == 1
    assert result[0].count == 2
    assert result[0].value == 100
    assert result[0].metric_name == "dummy_non_count"
    assert isinstance(result[0].timestamp, datetime)

    await env_metrics_service.flush_metrics()
    await env_metrics_service.flush_metrics()

    result = await data.EnvironmentMetricsNonCounter.get_list()
    assert len(result) == 3


async def test_flush_metrics_mix(env_metrics_service):
    dummy_count = DummyCountMetric("dummy_count", MetricType.count)
    dummy_non_count = DummyNonCountMetric("dummy_non_count", MetricType.non_count)
    env_metrics_service.register_metric_collector(metrics_collector=dummy_count)
    env_metrics_service.register_metric_collector(metrics_collector=dummy_non_count)

    await env_metrics_service.flush_metrics()
    result_non_count = await data.EnvironmentMetricsNonCounter.get_list()
    result_count = await data.EnvironmentMetricsCounter.get_list()
    assert len(result_non_count) == 1
    assert len(result_count) == 1

    await env_metrics_service.flush_metrics()
    await env_metrics_service.flush_metrics()

    result_non_count = await data.EnvironmentMetricsNonCounter.get_list()
    result_count = await data.EnvironmentMetricsCounter.get_list()
    assert len(result_non_count) == 3
    assert len(result_count) == 3
