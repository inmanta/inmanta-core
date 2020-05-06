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

import logging

from inmanta.config import *

LOGGER = logging.getLogger(__name__)

# flake8: noqa: H904

agent_map = Option(
    "config",
    "agent-map",
    None,
    """By default the agent assumes that all agent names map to the host on which the process is executed. With the
agent map it can be mapped to other hosts. This value consists of a list of key/value pairs. The key is the name of the
agent and the format of the value is described in :inmanta:entity:`std::AgentConfig`. When the configuration option
config.use_autostart_agent_map is set to true, this option will be ignored.


example: iaas_openstack=localhost,vm1=192.16.13.2""",
    is_map,
)

use_autostart_agent_map = Option(
    "config",
    "use_autostart_agent_map",
    False,
    """If this option is set to true, the agent-map of this agent will be set the the autostart_agent_map configured on the
    server. The agent_map will be kept up-to-date automatically.""",
    is_bool,
)

environment = Option("config", "environment", None, "The environment this agent or compile belongs to", is_uuid_opt)

agent_names = Option(
    "config",
    "agent-names",
    "$node-name",
    """Names of the agents this instance should deploy configuration for. When the configuration option
config.use_autostart_agent_map is set to true, this option will be ignored.""",
    is_list,
)

agent_interval = Option(
    "config",
    "agent-interval",
    600,
    """[DEPRECATED] The run interval of the agent.
Every run-interval seconds, the agent will check the current state of its resources against to desired state model""",
    is_time,
)

agent_splay = Option(
    "config",
    "agent-splay",
    600,
    """[DEPRECATED] The splaytime added to the runinterval.
Set this to 0 to disable splaytime.
 At startup the agent will choose a random number between 0 and "agent_splay.
It will wait this number of second before performing the first deploy.
Each subsequent deploy will start agent-interval seconds after the previous one.""",
    is_time,
)

agent_reconnect_delay = Option(
    "config", "agent-reconnect-delay", 5, "Time to wait after a failed heartbeat message. DO NOT SET TO 0 ", is_int
)

server_timeout = Option(
    "config",
    "server-timeout",
    125,
    "Amount of time to wait for a response from the server before we try to reconnect, must be larger than server.agent-hold",
    is_time,
)

agent_deploy_interval = Option(
    "config",
    "agent-deploy-interval",
    0,
    "The number of seconds between two (incremental) deployment runs of the agent. Set this to 0 to disable the scheduled deploy runs.",
    is_time,
    predecessor_option=agent_interval,
)
agent_deploy_splay_time = Option(
    "config",
    "agent-deploy-splay-time",
    600,
    """The splaytime added to the agent-deploy-interval. Set this to 0 to disable the splaytime.

At startup the agent will choose a random number between 0 and agent-deploy-splay-time.
It will wait this number of second before performing the first deployment run.
Each subsequent repair deployment will start agent-deploy-interval seconds after the previous one.""",
    is_time,
    predecessor_option=agent_splay,
)

agent_repair_interval = Option(
    "config",
    "agent-repair-interval",
    600,
    "The number of seconds between two repair runs (full deploy) of the agent. "
    + "Set this to 0 to disable the scheduled repair runs.",
    is_time,
)
agent_repair_splay_time = Option(
    "config",
    "agent-repair-splay-time",
    600,
    """The splaytime added to the agent-repair-interval. Set this to 0 to disable the splaytime.

At startup the agent will choose a random number between 0 and agent-repair-splay-time.
It will wait this number of second before performing the first repair run.
Each subsequent repair deployment will start agent-repair-interval seconds after the previous one.""",
    is_time,
)


##############################
# agent_rest_transport
##############################

agent_transport = TransportConfig("agent")
