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
from inmanta import config, data, command
import inmanta.compiler as compiler
import pymongo
from motor import motor_tornado
from inmanta.module import Project
from inmanta import resources, export
from inmanta.agent import handler
from inmanta.ast import CompilerException
from click import testing
import inmanta.main
from concurrent.futures.thread import ThreadPoolExecutor
from tornado import gen
import re
from tornado.ioloop import IOLoop


DEFAULT_PORT_ENVVAR = 'MONGOBOX_PORT'


@pytest.fixture(scope="session", autouse=True)
def mongo_db():
    db_path = tempfile.mkdtemp(dir="/dev/shm")
    mongobox = MongoBox(db_path=db_path)
    port_envvar = DEFAULT_PORT_ENVVAR

    mongobox.start()
    os.environ[port_envvar] = str(mongobox.port)

    yield mongobox

    mongobox.stop()
    del os.environ[port_envvar]
    shutil.rmtree(db_path)


def reset_all():
    resources.resource.reset()
    export.Exporter.reset()
    command.Commander.reset()
    handler.Commander.reset()


@pytest.fixture(scope="function", autouse=True)
def clean_reset(mongo_client):
    reset_all()
    yield
    reset_all()

    for db_name in mongo_client.database_names():
        mongo_client.drop_database(db_name)


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


@pytest.fixture()
def free_port():
    port = get_free_tcp_port()
    yield port


@pytest.fixture(scope="function", autouse=True)
def inmanta_config():
    config.Config.load_config()
    config.Config.set("auth_jwt_default", "algorithm", "HS256")
    config.Config.set("auth_jwt_default", "sign", "true")
    config.Config.set("auth_jwt_default", "client_types", "agent,compiler")
    config.Config.set("auth_jwt_default", "key", "rID3kG4OwGpajIsxnGDhat4UFcMkyFZQc1y3oKQTPRs")
    config.Config.set("auth_jwt_default", "expire", "0")
    config.Config.set("auth_jwt_default", "issuer", "https://localhost:8888/")
    config.Config.set("auth_jwt_default", "audience", "https://localhost:8888/")

    yield config.Config._get_instance()
    config.Config._reset()


@pytest.fixture(scope="function")
def server(inmanta_config, io_loop, mongo_db, mongo_client, motor):
    # fix for fact that pytest_tornado never set IOLoop._instance, the IOLoop of the main thread
    # causes handler failure
    IOLoop._instance = io_loop

    from inmanta.server import Server
    state_dir = tempfile.mkdtemp()

    port = get_free_tcp_port()
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

    del IOLoop._instance
    server.stop()
    shutil.rmtree(state_dir)


@pytest.fixture(scope="function",
                params=[(True, True, False), (True, False, False), (False, True, False),
                        (False, False, False), (True, True, True)],
                ids=["SSL and Auth", "SSL", "Auth", "Normal", "SSL and Auth with not self signed certificate"])
def server_multi(inmanta_config, io_loop, mongo_db, mongo_client, request):
    from inmanta.server import Server
    state_dir = tempfile.mkdtemp()

    ssl, auth, ca = request.param

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

    if auth:
        config.Config.set("server", "auth", "true")
        from inmanta import protocol

    for x, ct in [("server", None),
                  ("server_rest_transport", None),
                  ("agent_rest_transport", ["agent"]),
                  ("compiler_rest_transport", ["compiler"]),
                  ("client_rest_transport", ["api", "compiler"]),
                  ("cmdline_rest_transport", ["api"])]:
        if ssl and not ca:
            config.Config.set(x, "ssl_cert_file", os.path.join(path, "server.crt"))
            config.Config.set(x, "ssl_key_file", os.path.join(path, "server.open.key"))
            config.Config.set(x, "ssl_ca_cert_file", os.path.join(path, "server.crt"))
            config.Config.set(x, "ssl", "True")
        if ssl and ca:
            capath = os.path.join(path, "ca", "enduser-certs")

            config.Config.set(x, "ssl_cert_file", os.path.join(capath, "server.crt"))
            config.Config.set(x, "ssl_key_file", os.path.join(capath, "server.key.open"))
            config.Config.set(x, "ssl_ca_cert_file", os.path.join(capath, "server.chain"))
            config.Config.set(x, "ssl", "True")
        if auth and ct is not None:
            token = protocol.encode_token(ct)
            config.Config.set(x, "token", token)

    port = get_free_tcp_port()
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
    shutil.rmtree(state_dir)


@pytest.fixture(scope="function")
def client(server):
    from inmanta import protocol

    client = protocol.Client("client")

    yield client


@pytest.fixture(scope="function")
def client_multi(server_multi):
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


@pytest.fixture(scope="function")
def environment_multi(client_multi, server_multi, io_loop):
    """
        Create a project and environment. This fixture returns the uuid of the environment
    """
    def create_project():
        return client_multi.create_project("env-test")

    result = io_loop.run_sync(create_project)
    assert(result.code == 200)
    project_id = result.result["project"]["id"]

    def create_env():
        return client_multi.create_environment(project_id=project_id, name="dev")

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

        self.main = os.path.join(self.project_dir, "main.cf")
        with open(self.main, "w") as x:
            x.write(snippet)

        Project.set(Project(self.project_dir, autostd=autostd))

    def do_export(self, deploy=False, include_status=False):
        templfile = mktemp("json", "dump", self.project_dir)

        from inmanta.export import Exporter

        (types, scopes) = compiler.do_compile()

        class Options(object):
            pass
        options = Options()
        options.json = templfile if not deploy else None
        options.depgraph = False
        options.deploy = deploy
        options.ssl = False

        export = Exporter(options=options)
        return export.run(types, scopes, include_status=include_status)

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

    def setup_for_error_re(self, snippet, shouldbe):
        self.setup_for_snippet(snippet)
        try:
            compiler.do_compile()
            assert False, "Should get exception"
        except CompilerException as e:
            text = str(e)
            print(text)
            shouldbe = shouldbe.format(dir=self.project_dir)
            assert re.search(shouldbe, text) is not None


@pytest.fixture(scope="session")
def snippetcompiler():
    ast = SnippetCompilationTest()
    ast.setUpClass()
    yield ast
    shutil.rmtree(ast.project_dir)
    ast.tearDownClass()


class CLI(object):

    def __init__(self, io_loop):
        self.io_loop = io_loop
        self._thread_pool = ThreadPoolExecutor(1)

    @gen.coroutine
    def run(self, *args):
        os.environ["COLUMNS"] = "1000"
        runner = testing.CliRunner()
        cmd_args = ["--host", "localhost", "--port", config.Config.get("cmdline_rest_transport", "port")]
        cmd_args.extend(args)
        result = yield self._thread_pool.submit(runner.invoke, cli=inmanta.main.cmd, args=cmd_args, obj=self.io_loop,
                                                catch_exceptions=False)
        return result


@pytest.fixture
def cli(io_loop):
    o = CLI(io_loop)
    yield o
