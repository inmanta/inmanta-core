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
import abc
import logging
import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

import asyncpg

from inmanta.data import EnvironmentMetricsGauge, EnvironmentMetricsTimer
from inmanta.server import SLICE_DATABASE, SLICE_ENVIRONMENT_METRICS, SLICE_TRANSPORT, protocol

LOGGER = logging.getLogger(__name__)

COLLECTION_INTERVAL_IN_SEC = 60
METRIC_NAME_SEPARATOR = "."


class MetricType(str, Enum):
    """
    There are 3 types of metrics: gauge, timer and meter metrics.

    gauge: will do instantaneous readings of particular values at timestamps
    timer: will count the number of time events occurred and the total time the events took.
    meter: will measure the rate of events over time.
    """

    GAUGE = "gauge"
    TIMER = "timer"
    METER = "meter"


class MetricValue:
    """
    the Metric values as they should be returned by a MetricsCollector of type gauge

    The name of a metric as stored in the DB is the concatenation of metric_name and a field on which the data is grouped by.
    The METRIC_NAME_SEPARATOR '.' is used as separator and should not be used in the name itself.
    For example, a metric collected by for the agent_count collector and grouped for the state "up",
    will have agent_count.up as metric.
    if the metric is not grouped by anything the name of the collector is used as metric_name
    """

    def __init__(self, metric_name: str, count: int, environment: uuid.UUID, grouped_by: Optional[str] = None) -> None:
        if METRIC_NAME_SEPARATOR in metric_name:
            raise Exception('The character "%s" can not be used in the metric_name (%s)' % (METRIC_NAME_SEPARATOR, metric_name))
        if grouped_by and METRIC_NAME_SEPARATOR in grouped_by:
            raise Exception(
                'The character "%s" can not be used in the grouped_by value (%s)' % (METRIC_NAME_SEPARATOR, grouped_by)
            )
        self.metric_name = ".".join([metric_name, grouped_by]) if grouped_by else metric_name
        self.count = count
        self.environment = environment


class MetricValueTimer(MetricValue):
    """
    the Metric values as they should be returned by a MetricsCollector of type timer
    """

    def __init__(
        self, metric_name: str, count: int, value: float, environment: uuid.UUID, grouped_by: Optional[str] = None
    ) -> None:
        super().__init__(metric_name, count, environment, grouped_by)
        self.value = value


class MetricsCollector(abc.ABC):
    @abc.abstractmethod
    def get_metric_name(self) -> str:
        """
        Returns the name of the metric collected by this MetricsCollector.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_metric_type(self) -> MetricType:
        """
        Returns the type of Metric collected by this metrics collector (gauge, timer).
        This information is required by the `EnvironmentMetricsService` to know how the data
        should be aggregated.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    async def get_metric_value(
        self, start_interval: datetime, end_interval: datetime, connection: asyncpg.connection.Connection]
    ) -> Sequence[MetricValue]:
        """
        Invoked by the `EnvironmentMetricsService` at the end of the metrics collection interval.
        Returns the metrics collected by this MetricCollector within the past metrics collection interval.

        The *_interval arguments are present, because this method is intended to perform a query on
        the database. No in-memory state is being stored by this metrics collector. The provided interval
        should be interpreted as [start_interval, end_interval[

        :param start_interval: The start time of the metrics collection interval (inclusive).
        :param end_interval: The end time of the metrics collection interval (exclusive).
        :param connection: An optional connection
        :result: The metrics collected by this MetricCollector within the past metrics collection interval.
        """
        raise NotImplementedError()


class EnvironmentMetricsService(protocol.ServerSlice):
    """Slice for the management of metrics"""

    def __init__(self) -> None:
        super(EnvironmentMetricsService, self).__init__(SLICE_ENVIRONMENT_METRICS)
        self.metrics_collectors: Dict[str, MetricsCollector] = {}
        self.previous_timestamp = datetime.now()

    def get_dependencies(self) -> List[str]:
        return [SLICE_DATABASE]

    def get_depended_by(self) -> List[str]:
        return [SLICE_TRANSPORT]

    async def start(self) -> None:
        await super().start()
        self.register_metric_collector(ResourceCountMetricsCollector())
        self.schedule(self.flush_metrics, COLLECTION_INTERVAL_IN_SEC, initial_delay=0, cancel_on_stop=True)

    def register_metric_collector(self, metrics_collector: MetricsCollector) -> None:
        """
        Register the given metrics_collector.
        """
        if metrics_collector.get_metric_name() not in self.metrics_collectors:
            self.metrics_collectors[metrics_collector.get_metric_name()] = metrics_collector
        else:
            raise Exception(f"There already is a metric collector with the name {metrics_collector.get_metric_name()}")

    async def flush_metrics(self) -> None:
        """
        Invoked at the end of the metrics collection interval. Writes the metrics
        collected by the MetricsCollectors in the past metrics collection interval
        to the database.
        """
        now: datetime = datetime.now()
        old_previous_timestamp = self.previous_timestamp
        self.previous_timestamp = now
        metric_gauge: Sequence[EnvironmentMetricsGauge] = []
        metric_timer: Sequence[EnvironmentMetricsTimer] = []

        def create_metrics_gauge(metric_values_gauge: Sequence[MetricValue], timestamp: datetime):
            for mv in metric_values_gauge:
                metric_gauge.append(
                    EnvironmentMetricsGauge(
                        metric_name=mv.metric_name, timestamp=timestamp, count=mv.count, environment=mv.environment
                    )
                )

        def create_metrics_timer(metric_values_timer: Sequence[MetricValueTimer], timestamp: datetime):
            for mv in metric_values_timer:
                metric_timer.append(
                    EnvironmentMetricsTimer(
                        metric_name=mv.metric_name,
                        timestamp=timestamp,
                        count=mv.count,
                        value=mv.value,
                        environment=mv.environment,
                    )
                )

        async with EnvironmentMetricsGauge.get_connection() as con:
            for mc in self.metrics_collectors:
                metrics_collector: MetricsCollector = self.metrics_collectors[mc]
                metric_type: str = metrics_collector.get_metric_type()
                metric_values: Sequence[MetricValue] = await metrics_collector.get_metric_value(
                    old_previous_timestamp, now, connection=con
                )
                if metric_type == MetricType.GAUGE:
                    create_metrics_gauge(metric_values, now)
                elif metric_type == MetricType.TIMER:
                    assert all(isinstance(x, MetricValueTimer) for x in metric_values)
                    create_metrics_timer(metric_values, now)
                elif metric_type == MetricType.METER:
                    raise Exception(
                        f"Metric type {metric_type.value} is a derived quantity and can not be the type of a MetricsCollector"
                    )
                else:
                    raise Exception(f"Metric type {metric_type.value} is unknown.")

            await EnvironmentMetricsGauge.insert_many(metric_gauge, connection=con)
            await EnvironmentMetricsTimer.insert_many(metric_timer, connection=con)

        if datetime.now() - now > timedelta(seconds=COLLECTION_INTERVAL_IN_SEC):
            LOGGER.warning(
                "flush_metrics method took more than %d seconds: "
                "new attempts to flush metrics are fired faster than they resolve. "
                "Verify the load on the Database and the available connection pool size.",
                COLLECTION_INTERVAL_IN_SEC,
            )


class ResourceCountMetricsCollector(MetricsCollector):
    """
    This Metric will track the number of resources (grouped by resources state).
    """

    def get_metric_name(self) -> str:
        return "resource_count"

    def get_metric_type(self) -> MetricType:
        return MetricType.GAUGE

    async def get_metric_value(
        self, start_interval: datetime, end_interval: datetime, connection: asyncpg.connection.Connection
    ) -> Sequence[MetricValue]:
        query: str = """
            SELECT status,environment,count(*)
            FROM resource
            GROUP BY (status, environment)
        """
        metric_values: List[MetricValue] = []
        result: Sequence[asyncpg.Record] = await connection.fetch(query)
        for record in result:
            metric_values.append(MetricValue(self.get_metric_name(), record["count"], record["environment"], record["status"]))
        return metric_values
