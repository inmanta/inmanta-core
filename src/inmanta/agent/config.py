"""
Copyright 2017 Inmanta

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

import enum
import functools
import logging
import typing
import uuid

from inmanta.config import *
from inmanta.server.config import db_connection_pool_max_size, db_connection_pool_min_size

LOGGER = logging.getLogger(__name__)

# flake8: noqa: H904
environment: Option[typing.Optional[uuid.UUID]] = Option(
    "config", "environment", None, "The environment this agent or compile belongs to", is_uuid_opt
)

agent_reconnect_delay: Option[int] = Option(
    "config", "agent-reconnect-delay", 5, "Time to wait after a failed heartbeat message. DO NOT SET TO 0 ", is_int
)

server_timeout = Option(
    "config",
    "server-timeout",
    125,
    "Amount of time to wait for a response from the server before we try to reconnect, must be larger than server.agent-hold",
    is_time,
)

agent_deploy_interval: Option[int | str] = Option(
    "config",
    "agent-deploy-interval",
    0,
    "Set the frequency and the granularity of deploy runs (i.e. only trigger a deploy for resources that have a "
    " known divergence with their desired state)."
    " When specified as an integer, this will set the wait time (in seconds) before attempting to redeploy a resource"
    " after an unsuccessful deployment, on a per-resource basis."
    " When specified as a cron-like expression, a global deploy (i.e. for all resources that have a known divergence with their"
    " desired state) will be run following a cron-like time-to-run specification,"
    " interpreted in UTC. The expected format is ``[sec] min hour dom month dow [year]`` (If only 6 values are provided, they"
    " are interpreted as ``min hour dom month dow year``)."
    " A deploy will be requested at the scheduled time."
    " Set this to 0 to disable the scheduled deploy runs.",
    is_time_or_cron,
)

agent_repair_interval = Option(
    "config",
    "agent-repair-interval",
    600,
    "Set the frequency and the granularity of repair runs (i.e. trigger a deploy regardless of the assumed"
    " state of the resource(s))."
    " When specified as an integer, this will set the wait time (in seconds) before re-scheduling a resource for deployment"
    " after the previous deployment has ended, regardless of success or failure, on a per-resource basis."
    " When specified as a cron-like expression, a global repair (i.e. a full deploy for all resources, regardless of their"
    " assumed desired state and regardless of their actual state) will be run following a cron-like"
    " time-to-run specification,"
    " interpreted in UTC. The expected format is `[sec] min hour dom month dow [year]` ( If only 6 values are provided, they"
    " are interpreted as `min hour dom month dow year`)."
    " A repair will be requested at the scheduled time."
    " Setting this to 0 to disable the scheduled repair runs.",
    is_time_or_cron,
)

executor_venv_retention_time: Option[int] = Option(
    "agent",
    "executor-venv-retention-time",
    3600,
    "This is the number of seconds to wait before unused Python virtual environments of an executor are removed from "
    "the inmanta server. Setting this option too low may result in a high load on the Inmanta server. Setting it too high"
    " may result in increased disk usage.",
    # We know that the .inmanta venv status file is touched every minute, so `60` seconds is the lowest default we can use
    is_lower_bounded_int(60),
)


def default_db_pool_min_size() -> int:
    """:inmanta.config:option:`database.connection-pool-min-size` / 10"""
    return int(db_connection_pool_min_size.get() / 10)


def default_db_pool_max_size() -> int:
    """:inmanta.config:option:`database.connection-pool-max-size` / 10"""
    return int(db_connection_pool_max_size.get() / 10)


scheduler_db_connection_pool_min_size: Option[int] = Option(
    "scheduler",
    "db-connection-pool-min-size",
    default_db_pool_min_size,
    "In each environment, the database connection pool will be initialized with this number of connections for "
    "the resource scheduler.",
    is_lower_bounded_int(0),
)
scheduler_db_connection_pool_max_size: Option[int] = Option(
    "scheduler",
    "db-connection-pool-max-size",
    default_db_pool_max_size,
    "In each environment, limit the size of the database connection pool to this number of connections for "
    "the resource scheduler.",
    is_lower_bounded_int(1),
)
scheduler_db_connection_timeout: Option[float] = Option(
    "scheduler",
    "db-connection-timeout",
    60.0,
    "In each environment, set the database connection timeout for interactions of the scheduler with the database"
    " (in seconds).",
    is_float,
)


class AgentExecutorMode(str, enum.Enum):
    threaded = "threaded"
    forking = "forking"


def is_executor_mode(value: str | AgentExecutorMode) -> AgentExecutorMode:
    """threaded | forking"""
    if isinstance(value, AgentExecutorMode):
        return value
    return AgentExecutorMode(value)


agent_executor_cap = Option[int](
    "agent",
    "executor-cap",
    3,
    "Maximum number of concurrent executors to keep per environment, per agent. If this limit is already reached "
    "when creating a new executor, the oldest one will be stopped first.",
    is_lower_bounded_int(1),
)

agent_executor_retention_time = Option[int](
    "agent",
    "executor-retention-time",
    60,
    "Amount of time (in seconds) to wait before cleaning up inactive executors.",
    is_time,
)

agent_cache_cleanup_tick_rate = Option[int](
    "agent",
    "cache-cleanup-tick-rate",
    1,
    "The rate (in seconds) at which the agent will periodically attempt to remove stale entries from the cache when idle.",
    is_time,
)

##############################
# agent_rest_transport
##############################

agent_transport = TransportConfig("agent")
