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
import tempfile
import random
import string
import shutil

from mongobox import MongoBox
import pytest
from inmanta import config
import pymongo
from motorengine.connection import connect, disconnect

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


@pytest.fixture(scope="session")
def mongo_client(mongo_db):
    '''Returns an instance of :class:`pymongo.MongoClient` connected
    to MongoBox database instance.
    '''

    port = int(mongo_db.port)
    return pymongo.MongoClient(port=port)


@pytest.fixture(scope="function")
def motorengine(mongo_db, mongo_client, io_loop):
    c = connect(db="inmanta", host="localhost", port=int(mongo_db.port), io_loop=io_loop)
    yield c
    disconnect()
    for db_name in mongo_client.database_names():
        mongo_client.drop_database(db_name)


@pytest.fixture(scope="function")
def server(io_loop, mongo_db, mongo_client):
    from inmanta.server import Server
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
    config.Config.set("config", "executable", os.path.abspath(os.path.join(__file__, "../../src/inmanta/app.py")))
    config.Config.set("server", "agent-timeout", "10")

    server = Server(database_host="localhost", database_port=int(mongo_db.port), io_loop=io_loop)
    server.start()

    yield server

    server.stop()
    # does not work with current pymongo
    for db_name in mongo_client.database_names():
        mongo_client.drop_database(db_name)
    # end fix
    shutil.rmtree(state_dir)


@pytest.fixture(scope="function",
                params=[(True, True), (True, False), (False, True), (False, False)],
                ids=["SSL and Auth", "SSL", "Auth", "Normal"])
def server_multi(io_loop, mongo_db, mongo_client, request):
    from inmanta.server import Server
    state_dir = tempfile.mkdtemp()

    ssl, auth = request.param

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    testuser = ''.join(random.choice(string.ascii_lowercase) for _ in range(5))
    testpass = ''.join(random.choice(string.ascii_lowercase) for _ in range(5))

    for x in ["server",
              "server_rest_transport",
              "agent_rest_transport",
              "compiler_rest_transport",
              "client_rest_transport",
              "cmdline_rest_transport"]:
        if ssl:
            config.Config.set(x, "ssl_cert_file", os.path.join(path, "server.crt"))
            config.Config.set(x, "ssl_key_file", os.path.join(path, "server.open.key"))
            config.Config.set(x, "ssl_ca_cert_file", os.path.join(path, "server.crt"))
            config.Config.set(x, "ssl", "True")
        if auth:
            config.Config.set(x, "username", testuser)
            config.Config.set(x, "password", testpass)

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
    config.Config.set("config", "executable", os.path.abspath(os.path.join(__file__, "../../src/inmanta/app.py")))
    config.Config.set("server", "agent-timeout", "2")

    server = Server(database_host="localhost", database_port=int(mongo_db.port), io_loop=io_loop)
    server.start()

    yield server

    server.stop()
    # does not work with current pymongo
    for db_name in mongo_client.database_names():
        mongo_client.drop_database(db_name)
    # end fix
    shutil.rmtree(state_dir)


@pytest.fixture(scope="function")
def client(server):
    from inmanta import protocol

    client = protocol.Client("client")

    yield client
