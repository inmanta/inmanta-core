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

import enum
import logging
import warnings
from typing import Optional

from inmanta.config import Config, Option, is_bool, is_float, is_int, is_list, is_map, is_str, is_str_opt, is_time

LOGGER = logging.getLogger(__name__)

# flake8: noqa: H904

#############################
# Database
#############################

db_wait_time = Option(
    "database",
    "wait_time",
    0,
    "For how long the server should wait for the DB to be up before starting. "
    "If set to 0, the server won't wait for the DB. "
    "If set to a negative value, the server will wait forever.",
    is_time,
)
db_host = Option("database", "host", "localhost", "Hostname or IP of the postgresql server", is_str)
db_port = Option("database", "port", 5432, "The port of the postgresql server", is_int)
db_name = Option("database", "name", "inmanta", "The name of the database on the postgresql server", is_str)
db_username = Option("database", "username", "postgres", "The username to access the database in the PostgreSQL server", is_str)
db_password = Option("database", "password", None, "The password that belong to the database user", is_str)

db_connection_pool_min_size = Option(
    "database",
    "connection_pool_min_size",
    10,
    "[DEPRECATED, USE :inmanta.config:option:`server.db_connection_pool_min_size` INSTEAD] Number of connections the database connection pool will be initialized with",
    is_int,
)
db_connection_pool_max_size = Option(
    "database",
    "connection_pool_max_size",
    70,
    "[DEPRECATED, USE :inmanta.config:option:`server.db_connection_pool_max_size` INSTEAD] Max number of connections in the database connection pool",
    is_int,
)
db_connection_timeout = Option(
    "database",
    "connection_timeout",
    60.0,
    "[DEPRECATED, USE :inmanta.config:option:`server.db_connection_timeout` INSTEAD] Connection timeout in seconds when the server communicates with the database",
    is_float,
)


def default_db_pool_min_size() -> int:
    """:inmanta.config:option:`database.connection-pool-min-size` / 2"""
    return int(db_connection_pool_min_size.get() / 2)


def default_db_pool_max_size() -> int:
    """:inmanta.config:option:`database.connection-pool-max-size` / 2"""
    return int(db_connection_pool_max_size.get() / 2)


server_db_connection_pool_min_size = Option(
    section="server",
    name="db_connection_pool_min_size",
    default=default_db_pool_min_size,
    documentation="Number of connections the server's database connection pool will be initialized with.",
    validator=is_int,
    predecessor_option=db_connection_pool_min_size,
)
server_db_connection_pool_max_size = Option(
    section="server",
    name="db_connection_pool_max_size",
    default=default_db_pool_max_size,
    documentation="Max number of connections in the server's database connection pool.",
    validator=is_int,
    predecessor_option=db_connection_pool_max_size,
)

server_db_connection_timeout = Option(
    section="server",
    name="db_connection_timeout",
    default=60.0,
    documentation="Connection timeout in seconds when the server communicates with the database.",
    validator=is_float,
    predecessor_option=db_connection_timeout,
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
    "A list of addresses on which the server will listen for connections.",
    is_list,
)
server_bind_port = Option(
    "server",
    "bind-port",
    8888,
    "The port on which the server will listen for connections.",
    is_int,
)

server_tz_aware_timestamps = Option(
    "server",
    "tz_aware_timestamps",
    True,
    "Whether the server should return timezone aware timestamps. "
    "If False, the server will serialize timestamps in a time zone naive way (in implicit UTC). "
    "If True, timestamps are serialized as time zone aware objects.",
    is_bool,
)

server_enable_auth = Option("server", "auth", False, "Enable authentication on the server API", is_bool)
server_auth_method = Option("server", "auth_method", "oidc", "The authentication method to use: oidc, database or jwt", is_str)
server_additional_auth_header = Option(
    "server", "auth_additional_header", None, "An additional header to look for authentication tokens", is_str_opt
)

server_ssl_key = Option(
    "server", "ssl_key_file", None, "Server private key to use for this server Leave blank to disable SSL", is_str_opt
)

server_ssl_cert = Option(
    "server", "ssl_cert_file", None, "SSL certificate file for the server key. Leave blank to disable SSL", is_str_opt
)

server_compatibility_file = Option(
    "server",
    "compatibility_file",
    None,
    """Path to the compatibility.json file. If set, the server will perform the following checks:
       1) During startup, the server will perform a version compatibility check for the PostgreSQL version being used.
          The Inmanta server will fail to start if it runs against a PostgreSQL version lower than the minimal
          PostgreSQL version defined in the compatibility file.
       2) The constraints defined in the `python_package_constraints` field of the compatibility file will be
          enforced both during project install and during agent install.
       The Inmanta Docker container comes with a compatibility file at /usr/share/inmanta/compatibility/compatibility.json.
       The container sets the INMANTA_SERVER_COMPATIBILITY_FILE environment variable to this file by default.
       For more information about this compatibility file, please refer to the compatibility page in the Inmanta documentation.
       Leave blank to disable the version compatibility check and the enforcement of the constraints during installation.
    """,
    is_str_opt,
)


class AuthorizationProviderName(enum.Enum):
    """
    An enum that contains the possible values for the server.authorization_provider config option.
    """

    legacy = "legacy"
    policy_engine = "policy-engine"

    @classmethod
    def get_valid_values_str(cls) -> str:
        """
        Returns a human readable string containing the valid values for
        the server.authorization_provider config option.
        """
        valid_values = [e.value for e in cls]
        assert len(valid_values) > 1
        return ", ".join(valid_values[0:-1]) + " or " + valid_values[-1]


def _is_authorization_provider(value: str) -> str:
    f"""
    str, valid values: {AuthorizationProviderName.get_valid_values_str()}
    """
    value = value.lower()
    try:
        AuthorizationProviderName(value)
    except ValueError:
        raise ValueError(
            f"Invalid value for config option {authorization_provider.get_full_name()}: {value}."
            f" Valid values: {AuthorizationProviderName.get_valid_values_str()}"
        )
    else:
        return value


authorization_provider = Option(
    "server",
    "authorization-provider",
    AuthorizationProviderName.legacy.value,
    f"The authorization provider that should be used if authentication is enabled: {AuthorizationProviderName.get_valid_values_str()}",
    _is_authorization_provider,
)


def ssl_enabled():
    """Is ssl enabled on the server, given the current server config"""
    ssl_key: Optional[str] = server_ssl_key.get()
    ssl_cert: Optional[str] = server_ssl_cert.get()
    return ssl_key is not None and ssl_cert is not None


server_ssl_ca_cert = Option(
    "server",
    "ssl_ca_cert_file",
    None,
    "The CA cert file required to validate the server ssl cert. This setting is used by the server "
    "to correctly configure the compiler and agents that the server starts itself. If not set and "
    "SSL is enabled, the server cert should be verifiable with the CAs installed in the OS.",
    is_str_opt,
)

server_fact_expire = Option(
    "server", "fact-expire", 3600, "After how many seconds will discovered facts/parameters expire.", is_time
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

internal_server_address: Option[str] = Option(
    "server",
    "internal_server_address",
    "localhost",
    """The internal ip address of the server.
       This address is used by processes started by the server (e.g. compilers and schedulers) to connect back to the Inmanta server.""",
)

server_wait_after_param = Option(
    "server", "wait-after-param", 5, "Time to wait before recompile after new paramters have been received", is_time
)

agent_timeout = Option("server", "agent-timeout", 30, "Time before an agent is considered to be offline", is_time)

server_purge_resource_action_logs_interval = Option(
    "server", "purge-resource-action-logs-interval", 3600, "The number of seconds between resource-action log purging", is_time
)

server_resource_action_log_prefix: Option[str] = Option(
    "server",
    "resource_action_log_prefix",
    "resource-actions-",
    "File prefix in log-dir, containing the resource-action logs. The after the prefix the environment uuid and .log is added",
    is_str,
)

server_enabled_extensions: Option[list[str]] = Option(
    "server",
    "enabled_extensions",
    list,
    "A list of extensions the server must load. Core is always loaded."
    " If an extension listed in this list is not available, the server will refuse to start.",
    is_list,
)

server_access_control_allow_origin = Option(
    "server",
    "access-control-allow-origin",
    None,
    "Configures the Access-Control-Allow-Origin setting of the http server."
    " Defaults to not sending an Access-Control-Allow-Origin header.",
    is_str_opt,
)


def default_hangtime() -> int:
    """:inmanta.config:option:`server.agent-timeout` *3/4"""
    return int(agent_timeout.get() * 3 / 4)


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
