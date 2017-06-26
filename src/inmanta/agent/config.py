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

from inmanta.config import *
import logging

LOGGER = logging.getLogger(__name__)

# flake8: noqa: H904

agent_map = \
    Option("config", "agent-map", None,
           """By default the agent assumes that all agent names map to the host on which the process is executed. With the
agent map it can be mapped to other hosts. This value consists of a list of key/value pairs. The key is the name of the
agent and the format of the value is described in :inmanta:entity:`std::AgentConfig`

example: iaas_openstack=localhost,vm1=192.16.13.2""", is_map)

environment = \
    Option("config", "environment", None,
           "The environment this agent or compile belongs to", is_uuid_opt)

agent_names = \
    Option("config", "agent-names", "$node-name",
           "Names of the agents this instance should deploy configuration for", is_str)

agent_interval = \
    Option("config", "agent-interval", 600, """The run interval of the agent.
Every run-interval seconds, the agent will check the current state of its resources against to desired state model""", is_time)

agent_splay = \
    Option("config", "agent-splay", 600,
                     """The splaytime added to the runinterval.
Set this to 0 to disable splaytime.

At startup the agent will choose a random number between 0 and "agent_splay.
It will wait this number of second before performing the first deploy.
Each subsequent deploy will start agent-interval seconds after the previous one.""", is_time)

agent_antisplay = \
    Option("config", "agent-run-at-start", False,
           "run the agent at startup, even if a splay time is set", is_bool)


agent_reconnect_delay = \
    Option("config", "agent-reconnect-delay", 5,
           "Time to wait after a failed heartbeat message. DO NOT SET TO 0 ", is_int)

server_timeout = \
    Option("config", "server-timeout", 125,
           "Amount of time to wait for a response from the server before we try to reconnect, must be smaller than server.agent-hold", is_time)


##############################
# agent_rest_transport
##############################

agent_transport = TransportConfig("agent")
