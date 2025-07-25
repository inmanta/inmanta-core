"""
Copyright 2019 Inmanta

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

import datetime
import typing
from collections import abc
from enum import Enum
from typing import Optional

from inmanta.stable_api import stable_api

# This query assumes that the resource_persistent_state table is present in the query as rps.
# It returns the status of the resource in the "status" field.
SQL_RESOURCE_STATUS_SELECTOR: typing.LiteralString = """
(
    CASE
        WHEN rps.is_orphan
            THEN 'orphaned'
        WHEN rps.is_deploying
            THEN 'deploying'
        WHEN rps.is_undefined
            THEN 'undefined'
        WHEN rps.blocked = 'BLOCKED'
            THEN 'skipped_for_undefined'
        WHEN rps.current_intent_attribute_hash <> rps.last_deployed_attribute_hash
            THEN 'available'
        ELSE
            rps.last_non_deploying_status::text
    END
)
"""


class ResourceState(str, Enum):
    unavailable = "unavailable"  # This state is set by the agent when no handler is available for the resource
    skipped = "skipped"
    dry = "dry"
    deployed = "deployed"
    failed = "failed"
    deploying = "deploying"
    available = "available"
    cancelled = "cancelled"  # When a new version is pushed, in progress deploys are cancelled
    undefined = "undefined"  # The state of this resource is unknown at this moment in the orchestration process
    skipped_for_undefined = "skipped_for_undefined"  # This resource depends on an undefined resource


class HandlerResourceState(str, Enum):
    """
    The resource states that the resource handler may report via the HandlerContext (with the set_resource_state method)
    when it performs a resource action.
    """

    # A resource indicates it wants to skip its deployment.
    skipped = "skipped"
    deployed = "deployed"
    failed = "failed"
    dry = "dry"
    # A resource indicates it wants to skip its deployment, because one of its dependencies wasn't deployed
    # and that it should only be redeployed once its dependencies are deployed successfully. Resources with this
    # HandlerResourceState will get the TEMPORARILY_BLOCKED blocked status.
    skipped_for_dependency = "skipped_for_dependency"
    unavailable = "unavailable"


class NonDeployingResourceState(str, Enum):
    unavailable = ResourceState.unavailable.value
    skipped = ResourceState.skipped.value
    dry = ResourceState.dry.value
    deployed = ResourceState.deployed.value
    failed = ResourceState.failed.value
    available = ResourceState.available.value
    cancelled = ResourceState.cancelled.value
    undefined = ResourceState.undefined.value
    skipped_for_undefined = ResourceState.skipped_for_undefined.value


class DeprecatedResourceState(str, Enum):
    """
    Deprecated resource states kept for backwards compatibility.
    """

    # deprecated in iso5
    processing_events = "processing_events"


"""
The following consts are considered to be part of the stable API.
Modifying them may break some libraries:
    - UNDEPLOYABLE_STATES
    - TRANSIENT_STATES
    - NOT_DONE_STATES
    - DONE_STATES
"""
# undeployable
UNDEPLOYABLE_STATES = [ResourceState.undefined, ResourceState.skipped_for_undefined]
UNDEPLOYABLE_NAMES = [s.name for s in UNDEPLOYABLE_STATES]
# this resource action is not complete, resource is in transient state
TRANSIENT_STATES = [ResourceState.available, ResourceState.deploying]
# not counting as done
NOT_DONE_STATES = TRANSIENT_STATES
# counts as done
DONE_STATES = [
    ResourceState.unavailable,
    ResourceState.skipped,
    ResourceState.deployed,
    ResourceState.failed,
    ResourceState.cancelled,
] + UNDEPLOYABLE_STATES

# starting states
INITIAL_STATES = [ResourceState.available]
# states one can't transition out off
TERMINAL_STATES = UNDEPLOYABLE_STATES
# states on can transition to
VALID_STATES_ON_STATE_UPDATE = [
    ResourceState.unavailable,
    ResourceState.skipped,
    ResourceState.deployed,
    ResourceState.failed,
    ResourceState.deploying,
    ResourceState.cancelled,
    ResourceState.undefined,
    ResourceState.skipped_for_undefined,
]

UNKNOWN_STRING = "<<undefined>>"

"""
States set by server upon upload

1. available
2. undefined (terminal state)
3. skipped_for_undefined (terminal state)

States set by agent
1. skipped
2. failed
3. deployed
4. unavailable
5. cancelled
6. deploying

Each deploy sets the agent state again, all agent states can transition to all agent states

States that are in the action log, but not actual states
1. dry



                                           +-----> deploying        -<--------+
                                           |                                  |
                                           +-----> skipped          -<--------+
                                           |                                  |
                                           +-----> failed           -<--------+
                                           |                                  |
    +---------------->  available  +-------------> unavailable      -<--------+
    |                                      |                                  |
    |                                      +-----> deployed         -<--------+
    |                                      |                                  |
+---+---------+                            +-----> cancelled        -<--------+
| compiler    +------> undefined
+---+---------+
    |
    |
    +----------------> skipped_for_undefined

"""


class Change(str, Enum):
    nochange = "nochange"
    created = "created"
    purged = "purged"
    updated = "updated"


class VersionState(str, Enum):
    success = "success"
    failed = "failed"
    deploying = "deploying"
    pending = "pending"


@stable_api
class ResourceAction(str, Enum):
    """
    Enumeration of all resource actions.
    """

    store = "store"
    push = "push"
    pull = "pull"
    deploy = "deploy"
    dryrun = "dryrun"
    getfact = "getfact"
    other = "other"


STATE_UPDATE = [ResourceAction.deploy]


class AgentTriggerMethod(str, Enum):
    push_incremental_deploy = "push_incremental_deploy"
    push_full_deploy = "push_full_deploy"

    @classmethod
    def get_agent_trigger_method(cls, is_full_deploy: bool) -> "AgentTriggerMethod":
        if is_full_deploy:
            return cls.push_full_deploy
        else:
            return cls.push_incremental_deploy


@stable_api
class LogLevel(str, Enum):
    """
    Log levels used for various parts of the inmanta orchestrator.
    """

    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"
    TRACE = "TRACE"

    @property
    def to_int(self) -> int:
        return LOG_LEVEL_AS_INTEGER[self]

    @classmethod
    def _missing_(cls, value: object) -> Optional["LogLevel"]:
        return INTEGER_AS_LOG_LEVEL.get(value, None) if isinstance(value, int) else None


# Mapping each log level to its integer value
LOG_LEVEL_AS_INTEGER: abc.Mapping[LogLevel, int] = {
    LogLevel.CRITICAL: 50,
    LogLevel.ERROR: 40,
    LogLevel.WARNING: 30,
    LogLevel.INFO: 20,
    LogLevel.DEBUG: 10,
    LogLevel.TRACE: 3,
}

INTEGER_AS_LOG_LEVEL: abc.Mapping[int, LogLevel] = {value: log_level for log_level, value in LOG_LEVEL_AS_INTEGER.items()}

INMANTA_URN = "urn:inmanta:"
INMANTA_IS_ADMIN_URN = f"{INMANTA_URN}is_admin"
INMANTA_ROLES_URN = f"{INMANTA_URN}roles"


class Compilestate(str, Enum):
    """
    Compile state, whether the compile did succeed or not
    """

    success = "success"
    failed = "failed"


EXPORT_META_DATA = "export_metadata"
META_DATA_COMPILE_STATE = "inmanta:compile:state"
INMANTA_MT_HEADER = "X-Inmanta-tid"


class ClientType(str, Enum):
    # api: The method with this client type can be used by external clients like the Web-console, cli or 3rd party services
    # compiler: The method with this client type is called by the compiler to communicate with the server
    # agent: The method with this client type is called by the agent to communicate with the server
    api = "api"
    agent = "agent"
    compiler = "compiler"


# For testing

# assume we are running in a tty
ENVIRON_FORCE_TTY = "FORCE_TTY"

LOG_LEVEL_TRACE = 3

NAME_RESOURCE_ACTION_LOGGER = "inmanta.resource_action"

# Time we give the server/agent to shutdown gracefully, before we force stop the ioloop
SHUTDOWN_GRACE_IOLOOP = 10
# Time we give the server/agent to shutdown gracefully, before we execute sys.exit(3)
SHUTDOWN_GRACE_HARD = 15
# Time we give the executor to shutdown gracefully, before we execute sys.exit(3)
EXECUTOR_GRACE_HARD = 3
# Time we give the policy engine to shutdown gracefully (in seconds).
POLICY_ENGINE_GRACE_HARD = 3
# Time we give the policy engine to startup (in seconds).
POLICY_ENGINE_STARTUP_TIMEOUT = 10

# Hard shutdown exit code
EXIT_HARD = 3
# Startup failed exit code
EXIT_START_FAILED = 4

TIME_ISOFMT = "%Y-%m-%dT%H:%M:%S.%f"
TIME_LOGFMT = "%Y-%m-%d %H:%M:%S%z"

PLUGINS_PACKAGE = "inmanta_plugins"

# namespace in which extensions are discovered
EXTENSION_NAMESPACE = "inmanta_ext"
# module inside the extension package that contains the setup function
EXTENSION_MODULE = "extension"

# Default envelope key
ENVELOPE_KEY = "data"

# Minimum password length
MIN_PASSWORD_LENGTH = 8


class AgentAction(str, Enum):
    pause = "pause"
    unpause = "unpause"
    keep_paused_on_resume = "keep_paused_on_resume"
    unpause_on_resume = "unpause_on_resume"


class AgentStatus(str, Enum):
    paused = "paused"
    up = "up"
    down = "down"


class ParameterSource(str, Enum):
    fact = "fact"
    plugin = "plugin"
    user = "user"
    report = "report"


class ApiDocsFormat(str, Enum):
    # openapi: the api docs in json format, according to the OpenAPI v3 specification
    # swagger: the api docs in html, using a Swagger-UI view
    openapi = "openapi"
    swagger = "swagger"


class DesiredStateVersionStatus(str, Enum):
    active = "active"
    candidate = "candidate"
    retired = "retired"
    skipped_candidate = "skipped_candidate"


class NotificationSeverity(str, Enum):
    """
    The possible values determine the styling used by the frontend to show them,
    so notifications with severity 'info' will be shown as informational messages,
    the ones with 'error' as error messages and so on.
    The 'message' category corresponds to a generic message, which
    is shown without extra styling on the frontend.
    """

    message = "message"
    info = "info"
    success = "success"
    warning = "warning"
    error = "error"


CF_CACHE_DIR = ".cfcache"

PG_ADVISORY_KEY_PUT_VERSION = 1
PG_ADVISORY_KEY_RELEASE_VERSION = 2
""" lock against releasing a version in an environment, to prevent release races"""


# The filename of the changelog file in an Inmanta module
MODULE_CHANGELOG_FILE = "CHANGELOG.md"


DATETIME_MIN_UTC = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)

MODULE_PKG_NAME_PREFIX = "inmanta-module-"
STD_PACKAGE = f"{MODULE_PKG_NAME_PREFIX}std"

TRACEPARENT = "traceparent"

# Resource sets marked for deletion during a partial export can be passed via this env
# variable as a space separated list of set ids.
INMANTA_REMOVED_SET_ID = "INMANTA_REMOVED_RESOURCE_SET_ID"


# File present in the root of a virtual environment of an executor.
# This file is created after the venv is correctly created and touched at regular intervals while it's actively used.
# It's used to determine whether a venv is only partially created (due to a server crash for example) or to determine when the
# venv was last used.
INMANTA_VENV_STATUS_FILENAME = ".inmanta_venv_status"


# File present in the root of the state dir to indicate the version of disk layout that this orchestrator uses.
INMANTA_DISK_LAYOUT_VERSION = ".inmanta_disk_layout_version"
# If no file is present, create it with this version
DEFAULT_INMANTA_DISK_LAYOUT_VERSION = 2


# ID to represent the new scheduler as an agent
AGENT_SCHEDULER_ID = "$__scheduler"

# resource attributes for event propagation
RESOURCE_ATTRIBUTE_SEND_EVENTS: typing.Final[str] = "send_event"
RESOURCE_ATTRIBUTE_RECEIVE_EVENTS: typing.Final[str] = "receive_events"

# resource attributes for references
RESOURCE_ATTRIBUTE_REFERENCES: typing.Final[str] = "references"
RESOURCE_ATTRIBUTE_MUTATORS: typing.Final[str] = "mutators"

# Per component log variables
LOG_CONTEXT_VAR_ENVIRONMENT = "environment"

ALL_LOG_CONTEXT_VARS = [LOG_CONTEXT_VAR_ENVIRONMENT]


# Logger namespace
LOGGER_NAME_EXECUTOR = "inmanta.executor"


class AuthorizationLabel(Enum):
    """
    Base class for AuthorizationLabel enums, so that extensions
    can create their own AuthorizationLabel enums that are compatible
    with the API of core.
    """

    pass


class CoreAuthorizationLabel(AuthorizationLabel):
    AGENT_READ = "agent.read"
    AGENT_WRITE = "agent.write"
    USER_READ = "user.read"
    USER_WRITE = "user.write"
    USER_CHANGE_PASSWORD = "user.change-password"
    COMPILE_REPORT_READ = "compile-report.read"
    COMPILER_EXECUTE = "compiler.execute"
    COMPILER_STATUS_READ = "compiler.status.read"
    DEPLOY = "deploy"
    DESIRED_STATE_READ = "desired-state.read"
    DESIRED_STATE_WRITE = "desired-state.write"
    DISCOVERED_RESOURCES_READ = "discovered-resources.read"
    DOCS_READ = "docs.read"
    DRYRUN_READ = "dryrun.read"
    DRYRUN_WRITE = "dryrun.write"
    AGENT_PAUSE_RESUME = "agent.pause-resume"
    ENVIRONMENT_HALT_RESUME = "environment.halt-resume"
    ENVIRONMENT_READ = "environment.read"
    ENVIRONMENT_CREATE = "environment.create"
    ENVIRONMENT_MODIFY = "environment.modify"
    ENVIRONMENT_DELETE = "environment.delete"
    ENVIRONMENT_CLEAR = "environment.clear"
    ENVIRONMENT_SETTING_READ = "environment.setting.read"
    ENVIRONMENT_SETTING_WRITE = "environment.setting.write"
    FACT_READ = "fact.read"
    FACT_WRITE = "fact.write"
    FILE_READ = "file.read"
    FILE_WRITE = "file.write"
    GRAPHQL_READ = "graphql.read"
    METRICS_READ = "metrics.read"
    NOTIFICATION_READ = "notification.read"
    NOTIFICATION_WRITE = "notification.write"
    PARAMETER_READ = "parameter.read"
    PARAMETER_WRITE = "parameter.write"
    PIP_CONFIG_READ = "pip-config.read"
    PROJECT_READ = "project.read"
    PROJECT_CREATE = "project.create"
    PROJECT_MODIFY = "project.modify"
    PROJECT_DELETE = "project.delete"
    RESOURCE_READ = "resource.read"
    STATUS_READ = "status.read"
    TOKEN = "token"
    ROLE_READ = "role.read"
    ROLE_WRITE = "role.write"
    ROLE_ASSIGNMENT_READ = "role-assignment.read"
    ROLE_ASSIGNMENT_WRITE = "role-assignment.write"
    ROLE_IS_ADMIN = "role.is-admin"
    # These labels should only be used in tests
    TEST = "test"
    TEST_2 = "test2"
    TEST_3 = "test3"
    TEST_4 = "test4"
