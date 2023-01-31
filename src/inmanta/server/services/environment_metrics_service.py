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
import math
import textwrap
import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Union

import asyncpg

from inmanta.data import (
    ENVIRONMENT_METRICS_RETENTION,
    Agent,
    Compile,
    ConfigurationModel,
    Environment,
    EnvironmentMetricsGauge,
    EnvironmentMetricsTimer,
    Resource,
    Setting,
)
from inmanta.data.model import EnvironmentMetricsResult
from inmanta.protocol import methods_v2
from inmanta.protocol.decorators import handle
from inmanta.protocol.exceptions import BadRequest
from inmanta.server import SLICE_DATABASE, SLICE_ENVIRONMENT_METRICS, SLICE_TRANSPORT, protocol

LOGGER = logging.getLogger(__name__)

COLLECTION_INTERVAL_IN_SEC = 60
# This variable can be updated by the test suite to disable all actions done by the server on the metric-related database
# tables.
DISABLE_ENV_METRICS_SERVICE = False

# The category fields needs a default value in the DB as it is part of the PRIMARY KEY and can therefore not be NULL.
DEFAULT_CATEGORY = "__None__"


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

    def __init__(self, metric_name: str, count: int, environment: uuid.UUID, category: Optional[str] = None) -> None:
        self.metric_name = metric_name
        self.category = category
        self.count = count
        self.environment = environment


class MetricValueTimer(MetricValue):
    """
    the Metric values as they should be returned by a MetricsCollector of type timer
    """

    def __init__(
        self, metric_name: str, count: int, value: float, environment: uuid.UUID, category: Optional[str] = None
    ) -> None:
        super().__init__(metric_name, count, environment, category)
        self.value = value


LATEST_RELEASED_MODELS_SUBQUERY: str = textwrap.dedent(
    f"""
    latest_released_models AS (
        SELECT cm.environment, MAX(cm.version) AS version
        FROM {ConfigurationModel.table_name()} AS cm
        WHERE cm.released = TRUE
        GROUP BY cm.environment
    )
    """.strip(
        "\n"
    )
).strip()
"""
Subquery to get the latest released version for each environment. Environments with no released versions are absent.
To be used like f"WITH {LATEST_RELEASED_MODELS_SUBQUERY} <main_query>". The main query can use the name 'latest_released_models'
to refer to this table.
"""

LATEST_RELEASED_RESOURCES_SUBQUERY: str = (
    LATEST_RELEASED_MODELS_SUBQUERY
    + textwrap.dedent(
        f"""
        , latest_released_resources AS (
            SELECT r.*
            FROM {Resource.table_name()} AS r
            INNER JOIN latest_released_models as cm
                ON r.environment = cm.environment AND r.model = cm.version
        )
        """.strip(
            "\n"
        )
    ).strip()
)
"""
Subquery to get the resources for latest released version for each environment. Environments with no released versions are
absent. Includes LATEST_RELEASED_MODELS_SUBQUERY.
To be used like f"WITH {LATEST_RELEASED_RESOURCES_SUBQUERY} <main_query>. The main query can use the name
'latest_released_resources' to refer to this table.
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

        If, at the time of collection, no metric data exists for an environment and/or category,
        the implementation should return a meaningful default (e.g. 0 for count metrics).
        If no meaningful default exists (e.g. for some time metrics), the data may be left out.

        :param start_interval: The timezone-aware start time of the metrics collection interval (inclusive).
        :param end_interval: The timezone-aware end time of the metrics collection interval (exclusive).
        :param connection: An optional connection
        :result: The metrics collected by this MetricCollector within the past metrics collection interval.
        """
        raise NotImplementedError()


class EnvironmentMetricsService(protocol.ServerSlice):
    """Slice for the management of metrics"""

    def __init__(self) -> None:
        super(EnvironmentMetricsService, self).__init__(SLICE_ENVIRONMENT_METRICS)
        self.metrics_collectors: Dict[str, MetricsCollector] = {}
        self.previous_timestamp = datetime.now().astimezone()

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
        if not DISABLE_ENV_METRICS_SERVICE:
            self.schedule(
                self.flush_metrics, COLLECTION_INTERVAL_IN_SEC, initial_delay=COLLECTION_INTERVAL_IN_SEC, cancel_on_stop=True
            )
            # Cleanup metrics once per hour
            self.schedule(self._cleanup_old_metrics, interval=3600, initial_delay=0, cancel_on_stop=True)

    async def _cleanup_old_metrics(self) -> None:
        """
        Clean up metrics that are older than the retention time specified in the environment_metrics_retention
        environment setting.
        """
        async with Environment.get_connection() as con:
            query = f"""
            WITH env_and_retention_time_in_hours AS (
                SELECT id, (CASE WHEN e.settings ? $1 THEN (e.settings->>$1)::integer ELSE $2 END) AS retention_time_in_hours
                FROM {Environment.table_name()} AS e
                WHERE e.halted IS FALSE
            ), env_and_delete_before_timestamp AS (
                SELECT e.id, ($3::timestamptz - make_interval(hours => e.retention_time_in_hours)) AS delete_before_timestamp
                FROM env_and_retention_time_in_hours AS e
                WHERE e.retention_time_in_hours > 0
            ), delete_gauge AS (
                DELETE FROM {EnvironmentMetricsGauge.table_name()} AS emg
                USING env_and_delete_before_timestamp as e_to_dt
                WHERE emg.environment=e_to_dt.id AND emg.timestamp < e_to_dt.delete_before_timestamp
            )
            DELETE FROM {EnvironmentMetricsTimer.table_name()} AS emt
            USING env_and_delete_before_timestamp AS e_to_dt
            WHERE emt.environment=e_to_dt.id AND emt.timestamp < e_to_dt.delete_before_timestamp
            """
            environment_metrics_retention_setting: Setting = Environment.get_setting_definition(ENVIRONMENT_METRICS_RETENTION)
            values = [
                ENVIRONMENT_METRICS_RETENTION,
                environment_metrics_retention_setting.default,
                datetime.now().astimezone(),
            ]
            await con.execute(query, *values)

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
        now: datetime = datetime.now().astimezone()
        old_previous_timestamp = self.previous_timestamp
        self.previous_timestamp = now
        metric_gauge: Sequence[EnvironmentMetricsGauge] = []
        metric_timer: Sequence[EnvironmentMetricsTimer] = []

        def create_metrics_gauge(metric_values_gauge: Sequence[MetricValue], timestamp: datetime):
            for mv in metric_values_gauge:
                metric_gauge.append(
                    EnvironmentMetricsGauge(
                        metric_name=mv.metric_name,
                        category=mv.category if mv.category else DEFAULT_CATEGORY,
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
                        category=mv.category if mv.category else DEFAULT_CATEGORY,
                        timestamp=timestamp,
                        count=mv.count,
                        value=mv.value,
                        environment=mv.environment,
                    )
                )

        async with EnvironmentMetricsGauge.get_connection() as con:
            metrics_collector: MetricsCollector
            for metrics_collector in self.metrics_collectors.values():
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

        if datetime.now().astimezone() - now > timedelta(seconds=COLLECTION_INTERVAL_IN_SEC):
            LOGGER.warning(
                "flush_metrics method took more than %d seconds: "
                "new attempts to flush metrics are fired faster than they resolve. "
                "Verify the load on the Database and the available connection pool size.",
                COLLECTION_INTERVAL_IN_SEC,
            )

    def _divide_time_interval_in_time_windows(
        self, start_interval: datetime, end_interval: datetime, nb_time_windows: int
    ) -> list[datetime]:
        """
        This method divides the given time interval into the given number of time windows.
        The result is a list of timestamps that represent the end time of each window. This list of timestamps
        is sorted in ASC order.
        """
        total_seconds_in_interval = (end_interval - start_interval).total_seconds()
        seconds_per_window = math.floor(total_seconds_in_interval / nb_time_windows)
        result = [end_interval - timedelta(seconds=seconds_per_window) * i for i in range(nb_time_windows)]
        result.reverse()
        return result

    @handle(method=methods_v2.get_environment_metrics, env="tid")
    async def get_environment_metrics(
        self,
        env: Environment,
        metrics: List[str],
        start_interval: datetime,
        end_interval: datetime,
        nb_datapoints: int,
    ) -> EnvironmentMetricsResult:
        if start_interval >= end_interval:
            raise BadRequest("start_interval should be strictly smaller than end_interval.")
        if start_interval + timedelta(minutes=1) * nb_datapoints >= end_interval:
            raise BadRequest(
                "start_interval and end_interval should be at least <nb_datapoints> minutes separated from each other."
            )
        if nb_datapoints <= 0:
            raise BadRequest("nb_datapoints should be larger than 0")
        if not metrics:
            raise BadRequest("The 'metrics' argument should contain the name of at least one metric.")
        unknown_metric_names = [
            m for m in metrics if m not in self.metrics_collectors.keys() and m != "orchestrator.compile_rate"
        ]
        if unknown_metric_names:
            raise BadRequest(f"The following metrics given in the metrics parameter are unknown: {unknown_metric_names}")

        def _get_sub_query(metric: str, group_by: str, table_name: str, aggregation_function: str, metrics_list: str) -> str:
            return textwrap.dedent(
                f"""
                SELECT
                    {metric},
                    {group_by},
                    width_bucket(
                        EXTRACT(EPOCH FROM timestamp),
                        EXTRACT(EPOCH FROM $2::timestamp with time zone),
                        EXTRACT(EPOCH FROM $3::timestamp with time zone),
                        $4
                    ) as bucket_nr,
                    {aggregation_function} as value
                FROM {table_name}
                WHERE
                    environment=$1
                    AND timestamp >= $2::timestamp with time zone
                    AND timestamp < $3::timestamp with time zone
                    AND metric_name=ANY({metrics_list}::varchar[])
                GROUP BY metric_name, category, bucket_nr
            """
            ).strip()

        query_on_gauge_table = _get_sub_query(
            metric="metric_name",
            group_by="category",
            table_name=EnvironmentMetricsGauge.table_name(),
            aggregation_function="(sum(count)::float)/(count(*)::float)",
            metrics_list="$5",
        )
        query_on_timer_table = _get_sub_query(
            metric="metric_name",
            group_by="category",
            table_name=EnvironmentMetricsTimer.table_name(),
            aggregation_function="(sum(value)::float)/NULLIF(sum(count)::float, 0)",
            metrics_list="$5",
        )
        query_for_compiler_rate = _get_sub_query(
            metric="'orchestrator.compile_rate'",
            group_by=f"'{DEFAULT_CATEGORY}'",
            table_name=EnvironmentMetricsTimer.table_name(),
            aggregation_function=(
                "(sum(count)::float) / ((EXTRACT(epoch FROM ($3::timestamp - $2::timestamp)))::float / 3600 / $4)::float"
            ),
            metrics_list="'{ orchestrator.compile_time }'",
        )
        query = f"""
            ({query_on_gauge_table})
            UNION ALL
            ({query_on_timer_table})
            {f"UNION ALL ({query_for_compiler_rate})" if "orchestrator.compile_rate" in metrics else ""}
        """.strip()

        # Initialize everything with default values
        result_metrics: Dict[str, List[Union[float, Dict[str, float], None]]] = {
            m: [0 if m == "orchestrator.compile_rate" else None for _ in range(nb_datapoints)] for m in metrics
        }
        async with EnvironmentMetricsGauge.get_connection() as con:
            values = [env.id, start_interval, end_interval, nb_datapoints, metrics]
            records = await con.fetch(query, *values)
            for r in records:
                if r["value"] is None:
                    continue
                metric_name = r["metric_name"]
                assert isinstance(metric_name, str)
                category = r["category"]
                assert isinstance(category, str)
                bucket_nr = r["bucket_nr"]
                assert isinstance(bucket_nr, int)
                value = r["value"]
                assert isinstance(value, float) or isinstance(value, int)
                index_in_list = bucket_nr - 1
                assert 0 <= index_in_list < nb_datapoints
                if category == DEFAULT_CATEGORY:
                    result_metrics[metric_name][index_in_list] = value
                else:
                    if result_metrics[metric_name][index_in_list] is None:
                        result_metrics[metric_name][index_in_list] = {category: value}
                    else:
                        result_metrics[metric_name][index_in_list][category] = value

        # Convert to naive timestamps
        return EnvironmentMetricsResult(
            start=start_interval,
            end=end_interval,
            timestamps=self._divide_time_interval_in_time_windows(start_interval, end_interval, nb_datapoints),
            metrics=result_metrics,
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
            WITH {LATEST_RELEASED_RESOURCES_SUBQUERY}, nonzero_statuses AS (
                SELECT r.environment, r.status, COUNT(*) AS count
                FROM latest_released_resources AS r
                GROUP BY r.environment, r.status
            )
            SELECT e.id as environment, s.name as status, COALESCE(r.count, 0) as count
            FROM {Environment.table_name()} AS e
            CROSS JOIN unnest(enum_range(NULL::resourcestate)) AS s(name)
            LEFT JOIN nonzero_statuses AS r
            ON r.environment = e.id AND r.status = s.name
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
WITH agent_counts AS (
    SELECT
        environment,
        CASE
            WHEN paused THEN 'paused'
            WHEN id_primary IS NOT NULL THEN 'up'
            ELSE 'down'
        END AS status,
        COUNT(*)
    FROM {Agent.table_name()} AS a
    GROUP BY environment, status
)
-- inject zeroes for missing values in the environment - status matrix
SELECT e.id AS environment, s.status, COALESCE(a.count, 0) AS count
FROM {Environment.table_name()} AS e
CROSS JOIN (VALUES ('paused'), ('up'), ('down')) AS s(status)
LEFT JOIN agent_counts AS a
    ON a.environment = e.id AND a.status = s.status
ORDER BY environment, s.status
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
