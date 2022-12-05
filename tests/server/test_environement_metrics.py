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
from datetime import datetime

import pytest

from inmanta.server.protocol import Server
from inmanta.server.services.environment_metrics_service import EnvironmentMetricsService, MetricsCollector, MetricType


@pytest.fixture
async def env_metrics_service(server_config, init_dataclasses_and_load_schema):
    server = Server()
    metrics_service = EnvironmentMetricsService()
    await metrics_service.prestart(server)
    await metrics_service.start()
    server.add_slice(metrics_service)
    yield metrics_service
    await metrics_service.prestop()
    await metrics_service.stop()


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


async def test_flush_metrics(env_metrics_service):
    dummy_count = DummyCountMetric("dummy_count", MetricType.count)
    env_metrics_service.register_metric_collector(metrics_collector=dummy_count)

    test = await env_metrics_service.flush_metrics()
    print(test)
