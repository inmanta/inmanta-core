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

from enum import Enum


class ResourceState(str, Enum):
    unavailable = "unavailable"  # This state is set by the agent when no handler is available for the resource
    skipped = "skipped"  #
    dry = "dry"
    deployed = "deployed"
    failed = "failed"
    deploying = "deploying"
    available = "available"
    cancelled = "cancelled"  # When a new version is pushed, in progress deploys are cancelled
    undefined = "undefined"  # The state of this resource is unknown at this moment in the orchestration process
    skipped_for_undefined = "skipped_for_undefined"  # This resource depends on an undefined resource
    processing_events = "processing_events"


# undeployable
UNDEPLOYABLE_STATES = [ResourceState.undefined, ResourceState.skipped_for_undefined]
UNDEPLOYABLE_NAMES = [s.name for s in UNDEPLOYABLE_STATES]
# this resource action is not complete, resource is in transient state
TRANSIENT_STATES = [ResourceState.available, ResourceState.deploying, ResourceState.processing_events]
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
    ResourceState.processing_events,
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
7. processing_events

Each deploy sets the agent state again, all agent states can transition to all agent states

States that are in the action log, but not actual states
1. dry



                                           +-----> deploying        -<--------+
                                           |                                  |
                                           +-----> processing_events-<--------+
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


class ResourceAction(str, Enum):
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
    def get_agent_trigger_method(cls, is_full_deploy):
        if is_full_deploy:
            return cls.push_full_deploy
        else:
            return cls.push_incremental_deploy


class LogLevel(Enum):
    CRITICAL = 50
    ERROR = 40
    WARNING = 30
    INFO = 20
    DEBUG = 10
    TRACE = 3
    NOTSET = 0


INMANTA_URN = "urn:inmanta:"


class Compilestate(Enum):
    success = 1
    failed = 2


EXPORT_META_DATA = "export_metadata"
META_DATA_COMPILE_STATE = "inmanta:compile:state"
INMANTA_MT_HEADER = "X-Inmanta-tid"


class ClientType(str, Enum):
    # api: The method with this client type can be used by external clients like the Dashboard, cli or 3rd party services
    # compiler: The method with this client type is called by the compiler to communicate with the server
    # agent: The method with this client type is called by the agent to communicate with the server
    api = "api"
    agent = "agent"
    compiler = "compiler"


# For testing

# assume we are running in a tty
ENVIRON_FORCE_TTY = "FORCE_TTY"


LOG_LEVEL_TRACE = 3

NAME_RESOURCE_ACTION_LOGGER = "resource_action_logger"


# Time we give the server/agent to shutdown gracefully, before we force stop the ioloop
SHUTDOWN_GRACE_IOLOOP = 10
# Time we give the server/agent to shutdown gracefully, before we execute sys.exit(3)
SHUTDOWN_GRACE_HARD = 15
# Hard shutdown exit code
EXIT_HARD = 3
# Startup failed exit code
EXIT_START_FAILED = 4


TIME_ISOFMT = "%Y-%m-%dT%H:%M:%S.%f"
TIME_LOGFMT = "%Y-%m-%d %H:%M:%S"

PLUGINS_PACKAGE = "inmanta_plugins"

# namespace in which extensions are discovered
EXTENSION_NAMESPACE = "inmanta_ext"
# module inside the extension package that contains the setup function
EXTENSION_MODULE = "extension"

# Default envelope key
ENVELOPE_KEY = "data"

# Max number of attempts when updating modules
MAX_UPDATE_ATTEMPT = 5


class AgentAction(str, Enum):
    pause = "pause"
    unpause = "unpause"


class AgentStatus(str, Enum):
    paused = "paused"
    up = "up"
    down = "down"


class ParameterSource(str, Enum):
    fact = "fact"
    plugin = "plugin"
    user = "user"
    report = "report"
