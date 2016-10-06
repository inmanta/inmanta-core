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

import os

from mongobox import MongoBox
import pytest
import tempfile
from inmanta import config
import random
import string
from inmanta.server import Server

DEFAULT_PORT_ENVVAR = 'MONGOBOX_PORT'


@pytest.fixture(scope="session", autouse=True)
def mongo_db():
    mongobox = MongoBox()
    port_envvar = DEFAULT_PORT_ENVVAR

    mongobox.start()
    os.environ[port_envvar] = str(mongobox.port)

    yield mongobox

    mongobox.stop()
    del os.environ[port_envvar]


@pytest.yield_fixture(scope="function", autouse=True)
def server(io_loop, mongo_db):
    state_dir = tempfile.mkdtemp()

    PORT = "45678"
    config.Config.load_config()
    config.Config.get("database", "name", "inmanta-" + ''.join(random.choice(string.ascii_letters) for _ in range(10)))
    config.Config.set("config", "state-dir", state_dir)
    config.Config.set("config", "log-dir", os.path.join(state_dir, "logs"))
    config.Config.set("server_rest_transport", "port", PORT)
    config.Config.set("agent_rest_transport", "port", PORT)
    config.Config.set("compiler_rest_transport", "port", PORT)
    config.Config.set("client_rest_transport", "port", PORT)
    config.Config.set("cmdline_rest_transport", "port", PORT)
    config.Config.set("main", "executable", os.path.abspath(os.path.join(__file__, "../../src/inmanta/app.py")))
    config.Config.set("server", "agent-timeout", "2")

    server = Server(database_host="localhost", database_port=int(mongo_db.port), io_loop=io_loop)
    server.start()

    yield server

    server.stop()
