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
from collections import defaultdict
import time
import json
from threading import Condition


from tornado.testing import gen_test
from tornado import gen

from inmanta import protocol, agent, data
from inmanta.agent.handler import provider, ResourceHandler
from inmanta.resources import resource, Resource
from server_test import ServerTest
import pytest


@pytest.mark.slowtest
@pytest.mark.gen_test
def testagent_get_status(io_loop, server):
    client = protocol.Client("client")
    result = yield client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = yield client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    agent = agent.Agent(io_loop, hostname="node1", env_id=env_id, agent_map="agent1=localhost",
                        code_loader=False)
    agent.add_end_point_name("agent1")
    agent.start()

    assert(server.agentmanager._sessions.values()[0].get_status()) == {}
