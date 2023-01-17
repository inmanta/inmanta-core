"""
    Copyright 2018 Inmanta

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
import warnings

from inmanta.config import (
    Config,
    Option,
    is_bool,
    is_float,
    is_int,
    is_list,
    is_map,
    is_str,
    is_str_opt,
    is_time,
    log_dir,
    state_dir,
)

LOGGER = logging.getLogger(__name__)

# flake8: noqa: H904

#############################
# Database
#############################

db_host = Option("database", "host", "localhost", "Hostname or IP of the postgresql server", is_str)
db_port = Option("database", "port", 5432, "The port of the postgresql server", is_int)
db_name = Option("database", "name", "inmanta", "The name of the database on the postgresql server", is_str)
db_username = Option("database", "username", "postgres", "The username to access the database in the PostgreSQL server", is_str)
db_password = Option("database", "password", None, "The password that belong to the database user", is_str)
db_connection_pool_min_size = Option(
    "database", "connection_pool_min_size", 10, "Number of connections the pool will be initialized with", is_int
)
db_connection_pool_max_size = Option(
    "database", "connection_pool_max_size", 10, "Max number of connections in the pool", is_int
)
db_connection_timeout = Option("database", "connection_timeout", 60, "Connection timeout in seconds", is_float)

#############################
# server_rest_transport
#############################
transport_port = Option(
    "server_rest_transport",
    "port",
    8888,
    "[DEPRECATED USE :inmanta.config:option:`server.bind-port`] The port on which the server listens for connections",
    is_int,
)

#############################
# Influxdb
#############################
influxdb_host = Option("influxdb", "host", "", "Hostname or IP of the influxdb server to send reports to", is_str)
influxdb_port = Option("influxdb", "port", 8086, "The port of the influxdb server", is_int)
influxdb_name = Option("influxdb", "name", "inmanta", "The name of the database on the influxdb server", is_str)
influxdb_username = Option("influxdb", "username", None, "The username to access the database in the influxdb server", is_str)
influxdb_password = Option("influxdb", "password", None, "The password that belong to the influxdb user", is_str)

influxdb_interval = Option("influxdb", "interval", 30, "Interval with which to report to influxdb", is_int)
influxdb_tags = Option(
    "influxdb", "tags", "", "a dict of tags to attach to all influxdb records in the form tag=value,tag=value", is_map
)

#############################
# server
#############################
server_bind_address = Option(
    "server",
    "bind-address",
    "127.0.0.1",
    "A list of addresses on which the server will listen for connections. If this option is set, the "
    ":inmanta.config:option:`server_rest_transport.port` option is ignored.",
    is_list,
)
server_bind_port = Option(
    "server",
    "bind-port",
    8888,
    "The port on which the server will listen for connections. If this option is set, the "
    ":inmanta.config:option:`server_rest_transport.port` option is ignored.",
    is_int,
)


def get_bind_port() -> int:
    if Config.is_set("server", "bind-port") or Config.is_set("server", "bind-address"):
        # Use new bind-port option
        if Config.is_set("server_rest_transport", "port"):
            warnings.warn(
                "Ignoring the server_rest_transport.port config option since the new config options "
                "server.bind-port/server.bind-address are used.",
            )
        return server_bind_port.get()
    else:
        # Fallback to old option
        warnings.warn(
            "The server_rest_transport.port config option is deprecated in favour of the server.bind-port option.",
            category=DeprecationWarning,
        )
        return Config.get("server_rest_transport", "port", 8888)


server_enable_auth = Option("server", "auth", False, "Enable authentication on the server API", is_bool)

server_ssl_key = Option(
    "server", "ssl_key_file", None, "Server private key to use for this server Leave blank to disable SSL", is_str_opt
)

server_ssl_cert = Option(
    "server", "ssl_cert_file", None, "SSL certificate file for the server key. Leave blank to disable SSL", is_str_opt
)

server_ssl_ca_cert: Option[str] = Option(
    "server",
    "ssl_ca_cert_file",
    None,
    "The CA cert file required to validate the server ssl cert. This setting is used by the server"
    "to correctly configure the compiler and agents that the server starts itself. If not set and "
    "SSL is enabled, the server cert should be verifiable with the CAs installed in the OS.",
    is_str_opt,
)

server_fact_expire = Option(
    "server", "fact-expire", 3600, "After how many seconds will discovered facts/parameters expire", is_time
)


def default_fact_renew() -> int:
    """:inmanta.config:option:`server.fact-expire` /3"""
    return int(server_fact_expire.get() / 3)


def validate_fact_renew(value: object) -> int:
    """time; < :inmanta.config:option:`server.fact-expire`"""
    out = int(value)
    if not out < server_fact_expire.get():
        LOGGER.warn(
            "can not set fact_renew to %d, must be smaller than fact-expire (%d), using %d instead"
            % (out, server_fact_expire.get(), default_fact_renew())
        )
        out = default_fact_renew()
    return out


server_fact_renew = Option(
    "server",
    "fact-renew",
    default_fact_renew,
    """After how many seconds will discovered facts/parameters be renewed?
                              This value needs to be lower than fact-expire""",
    validate_fact_renew,
)

server_fact_resource_block = Option(
    "server", "fact-resource-block", 60, "Minimal time between subsequent requests for the same fact", is_time
)

server_autrecompile_wait = Option(
    "server",
    "auto-recompile-wait",
    10,
    """DEPRECATED: The number of seconds to wait before the server may attempt to do a new recompile.
                                     Recompiles are triggered after facts updates for example.""",
    is_time,
)

server_purge_version_interval = Option(
    "server",
    "purge-versions-interval",
    3600,
    """The number of seconds between version purging,
                                          see :inmanta.environment-settings:setting:`available_versions_to_keep`.""",
    is_time,
)

server_compiler_report_retention = Option(
    "server",
    "compiler-report-retention",
    604800,
    """The server regularly cleans up old compiler reports.
    This options specifies the number of seconds to keep old compiler reports for. The default is seven days.""",
    is_time,
)

server_cleanup_compiler_reports_interval = Option(
    "server",
    "cleanup-compiler-reports-interval",
    3600,
    """Number of seconds between old compile report cleanups.
    see :inmanta.config:option:`server.compiler-report-retention`""",
    is_time,
)

server_address: Option[str] = Option(
    "server",
    "server_address",
    "localhost",
    """The public ip address of the server.
                           This is required for example to inject the inmanta agent in virtual machines at boot time.""",
)

server_wait_after_param = Option(
    "server", "wait-after-param", 5, "Time to wait before recompile after new paramters have been received", is_time
)

agent_timeout = Option("server", "agent-timeout", 30, "Time before an agent is considered to be offline", is_time)

server_delete_currupt_files = Option(
    "server",
    "delete_currupt_files",
    True,
    "The server logs an error when it detects a file got corrupted. When set to true, the "
    "server will also delete the file, so on subsequent compiles the missing file will be "
    "recreated.",
    is_bool,
)

server_purge_resource_action_logs_interval = Option(
    "server", "purge-resource-action-logs-interval", 3600, "The number of seconds between resource-action log purging", is_time
)

server_resource_action_log_prefix = Option(
    "server",
    "resource_action_log_prefix",
    "resource-actions-",
    "File prefix in log-dir, containing the resource-action logs. The after the prefix the environment uuid and .log is added",
    is_str,
)

server_enabled_extensions = Option(
    "server",
    "enabled_extensions",
    "",
    "A list of extensions the server must load. Core is always loaded."
    "If an extension listed in this list is not available, the server will refuse to start.",
    is_list,
)

server_access_control_allow_origin = Option(
    "server",
    "access-control-allow-origin",
    None,
    "Configures the Access-Control-Allow-Origin setting of the http server."
    "Defaults to not sending an Access-Control-Allow-Origin header.",
    is_str_opt,
)


def default_hangtime() -> str:
    """:inmanta.config:option:`server.agent-timeout` *3/4"""
    return str(int(agent_timeout.get() * 3 / 4))


agent_hangtime = Option(
    "server", "agent-hold", default_hangtime, "Maximal time the server will hold an agent heartbeat call", is_time
)

agent_process_purge_interval = Option(
    "server",
    "agent-process-purge-interval",
    3600,
    """The number of seconds between two purges of old and expired agent processes.
       Set to zero to disable the cleanup. see :inmanta.config:option:`server.agent-processes-to-keep`""",
    is_time,
)

agent_processes_to_keep = Option(
    "server",
    "agent-processes-to-keep",
    5,
    """Keep this amount of expired agent processes for a certain hostname""",
    is_int,
)
