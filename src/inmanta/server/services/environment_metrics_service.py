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
import textwrap
import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

import asyncpg

from inmanta.data import Agent, Compile, ConfigurationModel, EnvironmentMetricsGauge, EnvironmentMetricsTimer, Resource
from inmanta.server import SLICE_DATABASE, SLICE_ENVIRONMENT_METRICS, SLICE_TRANSPORT, protocol

LOGGER = logging.getLogger(__name__)

COLLECTION_INTERVAL_IN_SEC = 60

# The grouped_by fields needs a default value in the DB as it is part of the PRIMARY KEY and can therefore not be NULL.
DEFAULT_GROUPED_BY = "__None__"


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
    """

    def __init__(self, metric_name: str, count: int, environment: uuid.UUID, grouped_by: Optional[str] = None) -> None:
        self.metric_name = metric_name
        self.grouped_by = grouped_by
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


# TODO: version -> latest_version?
LATEST_RELEASED_MODELS_SUBQUERY: str = textwrap.dedent(
    f"""
    latest_released_models AS (
        SELECT cm.environment, MAX(cm.version) AS version
        FROM {ConfigurationModel.table_name()} AS cm
        WHERE cm.released = TRUE
        GROUP BY cm.environment
    )
    """.strip("\n")
).strip()
"""
Subquery to get the latest released version for each environment. Environments with no released versions are absent.
To be used like f"WITH {LATEST_RELEASED_MODELS_SUBQUERY} <main_query>". The main query can use the name 'latest_released_models'
to refer to this table.
"""

LATEST_RELEASED_RESOURCES_SUBQUERY: str = textwrap.dedent(
    f"""
    {LATEST_RELEASED_MODELS_SUBQUERY}, latest_released_resources AS (
        SELECT *
        FROM {Resource.table_name()} AS r
        INNER JOIN latest_released_models as cm
            ON r.environment = cm.environment AND r.model = cm.version
    )
    """.strip("\n")
).strip()
"""
Subquery to get the resources for latest released version for each environment. Environments with no released versions are absent.
Includes LATEST_RELEASED_MODELS_SUBQUERY.
To be used like f"WITH {LATEST_RELEASED_RESOURCES_SUBQUERY} <main_query>. The main query use the name 'latest_released_models'
to refer to this table.
"""


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
        self, start_interval: datetime, end_interval: datetime, connection: asyncpg.connection.Connection
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
        self.register_metric_collector(CompileWaitingTimeMetricsCollector())
        self.register_metric_collector(AgentCountMetricsCollector())
        self.register_metric_collector(CompileTimeMetricsCollector())
        self.schedule(
            self.flush_metrics, COLLECTION_INTERVAL_IN_SEC, initial_delay=COLLECTION_INTERVAL_IN_SEC, cancel_on_stop=True
        )

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
                        metric_name=mv.metric_name,
                        grouped_by=mv.grouped_by if mv.grouped_by else DEFAULT_GROUPED_BY,
                        timestamp=timestamp,
                        count=mv.count,
                        environment=mv.environment,
                    )
                )

        def create_metrics_timer(metric_values_timer: Sequence[MetricValueTimer], timestamp: datetime):
            for mv in metric_values_timer:
                metric_timer.append(
                    EnvironmentMetricsTimer(
                        metric_name=mv.metric_name,
                        grouped_by=mv.grouped_by if mv.grouped_by else DEFAULT_GROUPED_BY,
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
        return "resource.resource_count"

    def get_metric_type(self) -> MetricType:
        return MetricType.GAUGE

    async def get_metric_value(
        self, start_interval: datetime, end_interval: datetime, connection: asyncpg.connection.Connection
    ) -> Sequence[MetricValue]:
        query: str = f"""
            WITH {LATEST_RELEASED_MODELS_SUBQUERY}
            SELECT r.environment, r.status, COUNT(*)
            FROM {Resource.table_name()} AS r
            INNER JOIN latest_models AS cm
                ON r.environment = cm.environment AND r.model = cm.version
            GROUP BY r.environment, r.status
            ORDER BY r.environment, r.status
        """
        metric_values: List[MetricValue] = []
        result: Sequence[asyncpg.Record] = await connection.fetch(query)
        for record in result:
            assert isinstance(record["count"], int)
            assert isinstance(record["environment"], uuid.UUID)
            assert isinstance(record["status"], str)
            metric_values.append(MetricValue(self.get_metric_name(), record["count"], record["environment"], record["status"]))
        return metric_values


class AgentCountMetricsCollector(MetricsCollector):
    """
    This Metric will track the number of agents (grouped by agent status).
    """

    def get_metric_name(self) -> str:
        return "resource.agent_count"

    def get_metric_type(self) -> MetricType:
        return MetricType.GAUGE

    async def get_metric_value(
        self, start_interval: datetime, end_interval: datetime, connection: asyncpg.connection.Connection
    ) -> Sequence[MetricValue]:
        query: str = f"""
-- fetch actual counts
WITH {LATEST_RELEASED_RESOURCES_SUBQUERY}, agent_counts AS (
    SELECT
        environment,
        CASE
            WHEN paused THEN 'paused'
            WHEN id_primary IS NOT NULL THEN 'up'
            ELSE 'down'
        END AS status,
        COUNT(*)
    FROM public.agent AS a
    -- only count agents that are relevant for the latest model
    WHERE EXISTS (
        SELECT *
        FROM latest_released_resources AS r
        WHERE r.environment = a.environment AND r.agent = a.name
    )
    GROUP BY environment, status
)
-- inject zeroes for missing values in the environment - status matrix
SELECT e.id, s.status, COALESCE(a.count, 0)
FROM {Environment.table_name()} AS e
CROSS JOIN (VALUES ('paused'), ('up'), ('down')) AS s(status)
LEFT JOIN agent_counts AS a
    ON a.environment = e.id AND a.status = s.status
ORDER BY e.id, s.status
        """
        metric_values: List[MetricValue] = []
        result: Sequence[asyncpg.Record] = await connection.fetch(query)
        for record in result:
            assert isinstance(record["count"], int)
            assert isinstance(record["environment"], uuid.UUID)
            assert isinstance(record["status"], str)
            metric_values.append(MetricValue(self.get_metric_name(), record["count"], record["environment"], record["status"]))
        return metric_values


class CompileTimeMetricsCollector(MetricsCollector):
    """
    This Metric will track the duration of compiles executed on the server.
    """

    def get_metric_name(self) -> str:
        return "orchestrator.compile_time"

    def get_metric_type(self) -> MetricType:
        return MetricType.TIMER

    async def get_metric_value(
        self, start_interval: datetime, end_interval: datetime, connection: asyncpg.connection.Connection
    ) -> Sequence[MetricValueTimer]:
        query: str = f"""
            SELECT count(*) as count, environment, sum(completed-started) as compile_time
            FROM {Compile.table_name()}
            WHERE completed >= $1
            AND completed < $2
            GROUP BY environment
        """
        values = [start_interval, end_interval]
        result: Sequence[asyncpg.Record] = await connection.fetch(query, *values)

        metric_values: List[MetricValueTimer] = []
        for record in result:
            assert isinstance(record["count"], int)
            assert isinstance(record["environment"], uuid.UUID)
            assert isinstance(record["compile_time"], timedelta)

            total_compile_time = record["compile_time"].total_seconds()  # Convert compile_time to float
            assert isinstance(total_compile_time, float)

            metric_values.append(
                MetricValueTimer(self.get_metric_name(), record["count"], total_compile_time, record["environment"])
            )

        return metric_values


class CompileWaitingTimeMetricsCollector(MetricsCollector):
    """
    This Metric will track the amount of time compile requests spend waiting in the compile queue before being executed.
    """

    def get_metric_name(self) -> str:
        return "orchestrator.compile_waiting_time"

    def get_metric_type(self) -> MetricType:
        return MetricType.TIMER

    async def get_metric_value(
        self, start_interval: datetime, end_interval: datetime, connection: asyncpg.connection.Connection
    ) -> Sequence[MetricValueTimer]:
        query: str = f"""
            SELECT count(*)  as count,environment,sum(started-requested) as compile_waiting_time
            FROM {Compile.table_name()}
            WHERE started >= $1
            AND started < $2
            GROUP BY environment
        """
        values = [start_interval, end_interval]
        result: Sequence[asyncpg.Record] = await connection.fetch(query, *values)

        metric_values: List[MetricValueTimer] = []
        for record in result:
            assert isinstance(record["count"], int)
            assert isinstance(record["environment"], uuid.UUID)
            assert isinstance(record["compile_waiting_time"], timedelta)

            compile_waiting_time = record["compile_waiting_time"].total_seconds()  # Convert compile_waiting_time to float
            assert isinstance(compile_waiting_time, float)

            metric_values.append(
                MetricValueTimer(self.get_metric_name(), record["count"], compile_waiting_time, record["environment"])
            )

        return metric_values
