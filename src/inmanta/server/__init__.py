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

"""
The server has as purpose to manage and orchestrate the deployments.
To do so, it stores the state of all projects and resources and keeps track of all agents in a Postgresql DB.
This way if an agent or the server itself get restarted or restarted, nothing get lost:
It can recover by getting all the information back from the database.
To interact with the Database in a completely asynchronous way, the asyncpg library is used.

The server exposes it API in the inmanta/protocol/methods.py and inmanta/protocol/methods_v2.py files.
Using the API endpoints in methods.py is the old way of doing things: the benefit of method_v2 is that everything is typed using
Pydantic.

The server is divided in multiple slices. Each slice is associated with a different service that the server can offer.
The different slices are created to be able to define the startup order of the different services, to keep the code more
readable and to allow the ability to add server extensions. Starting the different slices and extensions
is the responsibility of the bootloader (inmanta/server/bootloader.py). Core is an extensions of itself:
all the slices used by core a registered in the setup function of (inmanta_ext/core/extension.py)

To be able to define to start order of the slices,each slice has some lifecycle methods
(see class ServerSlice in inmanta/server/protocol.py)
"""

# flake8: noqa: F401

SLICE_SERVER = "core.server"
SLICE_AGENT_MANAGER = "core.agentmanager"
SLICE_AUTOSTARTED_AGENT_MANAGER = "core.autostarted_agent_manager"
SLICE_SESSION_MANAGER = "core.session"
SLICE_DATABASE = "core.database"
SLICE_TRANSPORT = "core.transport"
SLICE_COMPILER = "core.compiler"
SLICE_FORM = "core.forms"
SLICE_PROJECT = "core.project"
SLICE_ENVIRONMENT = "core.environment"
SLICE_FILE = "core.file"
SLICE_CODE = "core.code"
SLICE_METRICS = "core.metrics"
SLICE_PARAM = "core.parameters"
SLICE_RESOURCE = "core.resource"
SLICE_ORCHESTRATION = "core.orchestration"
SLICE_DRYRUN = "core.dryrun"
SLICE_NOTIFICATION = "core.notification"
SLICE_ENVIRONMENT_METRICS = "core.environment-metrics"
SLICE_USER = "core.user"
