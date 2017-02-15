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
from tempfile import mktemp
import socket


from mongobox import MongoBox
import pytest
from inmanta import config, data
import inmanta.compiler as compiler
import pymongo
from motor import motor_tornado
from inmanta.module import Project
from inmanta.ast import CompilerException

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
def motor(mongo_db, mongo_client, io_loop):
    client = motor_tornado.MotorClient('localhost', int(mongo_db.port), io_loop=io_loop)
    db = client["inmanta"]
    yield db

    for db_name in mongo_client.database_names():
        mongo_client.drop_database(db_name)


@pytest.fixture(scope="function")
def data_module(io_loop, motor):
    data.use_motor(motor)
    io_loop.run_sync(data.create_indexes)


def get_free_tcp_port():
    """
        Semi safe method for getting a random port. This may contain a race condition.
    """
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.bind(('', 0))
    _addr, port = tcp.getsockname()
    tcp.close()
    return str(port)


@pytest.fixture(scope="function")
def server(io_loop, mongo_db, mongo_client, motor):
    from inmanta.server import Server
    state_dir = tempfile.mkdtemp()

    port = get_free_tcp_port()
    config.Config.load_config()
    config.Config.get("database", "name", "inmanta-" + ''.join(random.choice(string.ascii_letters) for _ in range(10)))
    config.Config.set("config", "state-dir", state_dir)
    config.Config.set("config", "log-dir", os.path.join(state_dir, "logs"))
    config.Config.set("server_rest_transport", "port", port)
    config.Config.set("agent_rest_transport", "port", port)
    config.Config.set("compiler_rest_transport", "port", port)
    config.Config.set("client_rest_transport", "port", port)
    config.Config.set("cmdline_rest_transport", "port", port)
    config.Config.set("config", "executable", os.path.abspath(os.path.join(__file__, "../../src/inmanta/app.py")))
    config.Config.set("server", "agent-timeout", "10")

    data.use_motor(motor)

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

    port = get_free_tcp_port()
    config.Config.load_config()
    config.Config.get("database", "name", "inmanta-" + ''.join(random.choice(string.ascii_letters) for _ in range(10)))
    config.Config.set("config", "state-dir", state_dir)
    config.Config.set("config", "log-dir", os.path.join(state_dir, "logs"))
    config.Config.set("server_rest_transport", "port", port)
    config.Config.set("agent_rest_transport", "port", port)
    config.Config.set("compiler_rest_transport", "port", port)
    config.Config.set("client_rest_transport", "port", port)
    config.Config.set("cmdline_rest_transport", "port", port)
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


@pytest.fixture(scope="function")
def environment(client, server, io_loop):
    """
        Create a project and environment. This fixture returns the uuid of the environment
    """
    def create_project():
        return client.create_project("env-test")

    result = io_loop.run_sync(create_project)
    assert(result.code == 200)
    project_id = result.result["project"]["id"]

    def create_env():
        return client.create_environment(project_id=project_id, name="dev")

    result = io_loop.run_sync(create_env)
    env_id = result.result["environment"]["id"]

    yield env_id


class SnippetCompilationTest(object):
    libs = None
    env = None

    @classmethod
    def setUpClass(cls):
        cls.libs = tempfile.mkdtemp()
        cls.env = tempfile.mkdtemp()
        config.Config.load_config()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.libs)
        shutil.rmtree(cls.env)

    def setup_for_snippet(self, snippet, autostd=True):
        # init project
        self.project_dir = tempfile.mkdtemp()
        os.symlink(self.__class__.env, os.path.join(self.project_dir, ".env"))

        with open(os.path.join(self.project_dir, "project.yml"), "w") as cfg:
            cfg.write(
                """
            name: snippet test
            modulepath: [%s, %s]
            downloadpath: %s
            version: 1.0
            repo: ['https://github.com/inmanta/']"""
                % (self.__class__.libs,
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "modules"),
                    self.__class__.libs))

        with open(os.path.join(self.project_dir, "main.cf"), "w") as x:
            x.write(snippet)

        Project.set(Project(self.project_dir, autostd=autostd))

    def do_export(self):
        templfile = mktemp("json", "dump", self.project_dir)

        from inmanta.export import Exporter

        (types, scopes) = compiler.do_compile()

        class Options(object):
            pass
        options = Options()
        options.json = templfile
        options.depgraph = False
        options.deploy = False
        options.ssl = False

        export = Exporter(options=options)
        return export.run(types, scopes)

    def setup_for_error(self, snippet, shouldbe):
        self.setup_for_snippet(snippet)
        try:
            compiler.do_compile()
            assert False, "Should get exception"
        except CompilerException as e:
            text = str(e)
            print(text)
            shouldbe = shouldbe.format(dir=self.project_dir)
            assert shouldbe == text


@pytest.fixture(scope="session")
def snippetcompiler():
    ast = SnippetCompilationTest()
    ast.setUpClass()
    yield ast
    ast.tearDownClass()
