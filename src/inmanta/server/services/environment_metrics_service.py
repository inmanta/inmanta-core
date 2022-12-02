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
from datetime import datetime, timedelta
from enum import Enum
from typing import List

from inmanta.data import BaseDocument
from inmanta.server import SLICE_DATABASE, SLICE_ENVIRONMENT_METRICS, SLICE_TRANSPORT, protocol

LOGGER = logging.getLogger(__name__)


class MetricType(str, Enum):
    count = "count"
    non_count = "non_count"
    compile_rate = "compile_rate"


class MetricsCollector(abc.ABC):
    def __init__(
        self,
        metric_name: str,
        metric_type: MetricType,
    ) -> None:
        """
        :param metric_name: The name of the metric collected by this MetricsCollector
        :param metric_type: The metric type of Metric collected by this metrics collector (count, non-count, etc.)
        """
        self.metric_name = metric_name
        self.metric_type = metric_type

    def get_metric_name(self) -> str:
        """
        Returns the name of the metric collected by this MetricsCollector.
        """
        return self.metric_name

    def get_metric_type(self) -> MetricType:
        """
        Returns the type of Metric collected by this metrics collector (count, non-count, etc.).
        This information is required by the `EnvironmentMetricsService` to know how the data
        should be aggregated.
        """
        raise self.metric_type

    @abc.abstractmethod
    async def get_metric_value(self, start_interval: datetime, end_interval: datetime) -> object:
        """
        Invoked by the `EnvironmentMetricsService` at the end of the metrics collection interval.
        Returns the metrics collected by this MetricCollector within the past metrics collection interval.

        The *_interval arguments are present, because this method is intended to perform a query on
        the database. No in-memory state is being stored by this metrics collector. The provided interval
        should be interpreted as [start_interval, end_interval[

        :param start_interval: The start time of the metrics collection interval (inclusive).
        :param end_interval: The end time of the metrics collection interval (exclusive).
        :result: The metrics collected by this MetricCollector within the past metrics collection interval.
        """
        raise NotImplementedError()


class EnvironmentMetricsService(protocol.ServerSlice):
    """Slice for the management of metrics"""

    metrics_collectors: List[MetricsCollector]

    def __init__(self) -> None:
        super(EnvironmentMetricsService, self).__init__(SLICE_ENVIRONMENT_METRICS)

    def get_dependencies(self) -> List[str]:
        return [SLICE_DATABASE]

    def get_depended_by(self) -> List[str]:
        return [SLICE_TRANSPORT]

    async def start(self) -> None:
        await super().start()
        self.schedule(self.flush_metrics, 60, initial_delay=0, cancel_on_stop=True)

    def register_metric_collector(self, metrics_collector: MetricsCollector) -> None:
        """
        Register the given metrics_collector.
        """
        self.metrics_collectors.append(metrics_collector)

    async def flush_metrics(self) -> None:
        """
        Invoked at the end of the metrics collection interval. Writes the metrics
        collected by the MetricsCollectors in the past metrics collection interval
        to the database.
        """
        now: datetime = datetime.now()
        metric_count: List[EnvironmentMetricsCounter] = []
        metric_non_count: List[EnvironmentMetricsNonCounter] = []
        for metrics_collector in self.metrics_collectors:
            metric_name: str = metrics_collector.get_metric_name()
            metric_type: str = metrics_collector.get_metric_type()
            metric_value: object = metrics_collector.get_metric_value(now - timedelta(seconds=60), now)
            if metric_type == MetricType.count:
                metric_count.append(EnvironmentMetricsCounter.new(metric_name, now, metric_value.count))
            if metric_type == MetricType.non_count:
                metric_non_count.append(
                    EnvironmentMetricsNonCounter.new(metric_name, now, metric_value.count, metric_value.value)
                )

        await EnvironmentMetricsCounter.insert_many(metric_count)
        await EnvironmentMetricsNonCounter.insert_many(metric_non_count)

        if datetime.now() - now > timedelta(seconds=60):
            LOGGER.warning("flush_metrics method took more than 1 minute")


class EnvironmentMetricsCounter(BaseDocument):
    """
    A metrics that is a counter

    :param metric_name: The name of the metric
    :param timestamp: The timestamps at witch a new record is created
    :param count: the counter for the metric in the last timestamp
    """

    metric_name: str
    timestamp: datetime.datetime
    count: int

    __primary_key__ = ("metric_name", "timestamp")

    def table_name(cls) -> str:
        """
        Return the name of the collection #todo changer ca
        """
        return cls.__name__.lower()

    @classmethod
    def new(cls, metric_name: str, timestamp: datetime.datetime, count: int) -> "EnvironmentMetricsCounter":
        attr = dict(
            metric_name=metric_name,
            timestamp=timestamp,
            count=count,
        )
        return cls(**attr)


class EnvironmentMetricsNonCounter(BaseDocument):
    """
    A metrics that is not a counter

    :param metric_name: The name of the metric
    :param timestamp: The timestamps at witch a new record is created
    :param count: the number of occurrences in the last timestamp
    :param value: the value of the metric for the last timestamp
    """

    metric_name: str
    timestamp: datetime.datetime
    count: int
    value: int

    __primary_key__ = ("metric_name", "timestamp")

    @classmethod
    def new(cls, metric_name: str, timestamp: datetime.datetime, count: int, value: int) -> "EnvironmentMetricsCounter":
        attr = dict(
            metric_name=metric_name,
            timestamp=timestamp,
            count=count,
        )
        return cls(**attr)
