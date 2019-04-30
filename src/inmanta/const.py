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


class ResourceState(Enum):
    unavailable = 1  # This state is set by the agent when no handler is available for the resource
    skipped = 2  #
    dry = 3
    deployed = 4
    failed = 5
    deploying = 6
    available = 7
    cancelled = 8  # When a new version is pushed, in progress deploys are cancelled
    undefined = 9  # The state of this resource is unknown at this moment in the orchestration process
    skipped_for_undefined = 10  # This resource depends on an undefined resource
    processing_events = 11


# undeployable
UNDEPLOYABLE_STATES = [ResourceState.undefined, ResourceState.skipped_for_undefined]
# this resource action is not complete, resource is in transient state
TRANSIENT_STATES = [ResourceState.available, ResourceState.deploying, ResourceState.processing_events]
# not counting as done
NOT_DONE_STATES = TRANSIENT_STATES
# counts as done
DONE_STATES = [ResourceState.unavailable, ResourceState.skipped, ResourceState.deployed, ResourceState.failed,
               ResourceState.cancelled] + UNDEPLOYABLE_STATES

# starting states
INITIAL_STATES = [ResourceState.available]
# states one can't transition out off
TERMINAL_STATES = UNDEPLOYABLE_STATES
# states on can transition to
VALID_STATES_ON_STATE_UPDATE = [ResourceState.unavailable, ResourceState.skipped, ResourceState.deployed,
                                ResourceState.failed, ResourceState.deploying, ResourceState.cancelled, ResourceState.undefined,
                                ResourceState.skipped_for_undefined, ResourceState.processing_events]

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


class Change(Enum):
    nochange = 0
    created = 1
    purged = 2
    updated = 3


class VersionState(Enum):
    success = 1
    failed = 2
    deploying = 3
    pending = 4


class ResourceAction(Enum):
    store = 1
    push = 2
    pull = 3
    deploy = 4
    dryrun = 5
    getfact = 6
    other = 8


STATE_UPDATE = [ResourceAction.deploy]


class AgentTriggerMethod(Enum):
    push_incremental_deploy = 1
    push_full_deploy = 2

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
VALID_CLIENT_TYPES = ["api", "agent", "compiler", "public"]

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

TIME_ISOFMT = "%Y-%m-%dT%H:%M:%S.%f"
TIME_LOGFMT = "%Y-%m-%d %H:%M:%S"

PLUGINS_PACKAGE = "inmanta_plugins"
