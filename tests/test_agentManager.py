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

import time

from utils import retry_limited
from tornado.gen import sleep
import pytest
from unittest.mock import Mock
from inmanta.server.agentmanager import AgentManager
from datetime import date, datetime
from uuid import uuid4
from motorengine.connection import connect
from conftest import DEFAULT_PORT_ENVVAR
from inmanta.data import Environment, Agent


class Collector():

    def __init__(self):
        self.values = []

    def __call__(self, arg):
        self.values.append(arg)


class TestSession(object):
    """
        An environment that segments agents connected to the server
    """

    def __init__(self, sid, tid, endpoint_names, nodename):
        self._sid = sid
        self.tid = tid
        self.endpoint_names = endpoint_names
        self.nodename = nodename
        self.client = Mock()

    def get_id(self):
        return self._sid

    id = property(get_id)

    def get_client(self):
        return self.client


@pytest.mark.gen_test(timeout=30)
def test_primary_selection(mongo_db):
    connect("test_inmanta", host="127.0.0.1", port=mongo_db.port)
    server = Mock()

    futures = Collector()
    server.add_future.side_effect = futures
    am = AgentManager(server, False)

    env = Environment(uuid=uuid4(), name="testenv", project_id=uuid4())
    env = yield env.save()

    agent1 = yield Agent(environment=env, name="agent1", paused=True).save()
    agent2 = yield Agent(environment=env, name="agent2", paused=False).save()

    ts1 = TestSession(uuid4(), env.uuid, ["agent1", "agent2"], "ts1")
    am.new_session(ts1)
    assert 1 == server.add_future.call_count
    yield futures.values
    futures.values = []

    assert len(am.sessions) == 1
    assert ts1.get_client().set_state.assert_called_with("agent2", True, 0)
