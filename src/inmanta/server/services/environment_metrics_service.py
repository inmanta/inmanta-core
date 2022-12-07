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
from typing import Dict, List

from inmanta.data import EnvironmentMetricsCounter, EnvironmentMetricsNonCounter
from inmanta.protocol.exceptions import ServerError
from inmanta.server import SLICE_DATABASE, SLICE_ENVIRONMENT_METRICS, SLICE_TRANSPORT, protocol

LOGGER = logging.getLogger(__name__)

COLLECTION_INTERVAL_IN_SEC = 60


class MetricType(str, Enum):
    COUNT = "count"
    NON_COUNT = "non_count"
    COMPILE_RATE = "compile_rate"


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
        Returns the type of Metric collected by this metrics collector (count, non-count, etc.).
        This information is required by the `EnvironmentMetricsService` to know how the data
        should be aggregated.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    async def get_metric_value(self, start_interval: datetime, end_interval: datetime) -> dict[str, int]:
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
        self.schedule(self.flush_metrics, COLLECTION_INTERVAL_IN_SEC, initial_delay=0, cancel_on_stop=True)

    def register_metric_collector(self, metrics_collector: MetricsCollector) -> None:
        """
        Register the given metrics_collector.
        """
        if not metrics_collector.get_metric_name() in self.metrics_collectors:
            self.metrics_collectors[metrics_collector.get_metric_name()] = metrics_collector
        else:
            raise ServerError(f"There already is a metric collector with the name {metrics_collector.get_metric_name()}")

    async def flush_metrics(self) -> None:
        """
        Invoked at the end of the metrics collection interval. Writes the metrics
        collected by the MetricsCollectors in the past metrics collection interval
        to the database.
        """
        now: datetime = datetime.now()
        metric_count: List[EnvironmentMetricsCounter] = []
        metric_non_count: List[EnvironmentMetricsNonCounter] = []
        for mc in self.metrics_collectors:
            metrics_collector: MetricsCollector = self.metrics_collectors[mc]
            metric_name: str = metrics_collector.get_metric_name()
            metric_type: str = metrics_collector.get_metric_type()
            metric_value: dict[str, int] = await metrics_collector.get_metric_value(self.previous_timestamp, now)
            self.previous_timestamp = now
            if metric_type == MetricType.COUNT:
                metric_count.append(
                    EnvironmentMetricsCounter(metric_name=metric_name, timestamp=now, count=metric_value["count"])
                )
            if metric_type == MetricType.NON_COUNT:
                metric_non_count.append(
                    EnvironmentMetricsNonCounter(
                        metric_name=metric_name, timestamp=now, count=metric_value["count"], value=metric_value["value"]
                    )
                )

        await EnvironmentMetricsCounter.insert_many(metric_count)
        await EnvironmentMetricsNonCounter.insert_many(metric_non_count)

        if datetime.now() - now > timedelta(seconds=COLLECTION_INTERVAL_IN_SEC):
            LOGGER.warning("flush_metrics method took more than 1 minute")
