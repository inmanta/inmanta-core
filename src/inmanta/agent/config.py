"""
    Copyright 2016 Inmanta

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

python_binary = \
    Option("config", "python_binary", "python",
           "Python binary used to run the remote agent")

agent_map = \
    Option("config", "agent-map", None,
           """mapping between agent names and host names.
    If an agent is autostarted, its hostname is looked up in this map.
    If it is not found, the agent name is used as hostname.
    If the hostname is not localhost or :inmanta.config:option:`config.node-name`, ssh is used to start the agent on the appropriate machine
    
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


##############################
# agent_rest_transport
##############################

agent_transport = TransportConfig("agent")