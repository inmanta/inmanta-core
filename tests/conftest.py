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
import logging


import pytest

import utils
from inmanta import config, data, mongoproc
import inmanta.compiler as compiler
import pymongo
from motor import motor_asyncio
from inmanta.module import Project
from inmanta import resources, export
from inmanta.agent import handler, agent
from inmanta.ast import CompilerException
from click import testing
import inmanta.main
import re
from inmanta.server.bootloader import InmantaBootloader
from inmanta.server import SLICE_AGENT_MANAGER
from inmanta.export import cfg_env, unknown_parameters
import traceback
from tornado import process
import asyncio
from tornado.platform.asyncio import AnyThreadEventLoopPolicy
import sys
import pkg_resources
from typing import Optional, Dict
from inmanta import protocol


asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())

DEFAULT_PORT_ENVVAR = 'MONGOBOX_PORT'


@pytest.fixture(scope="session", autouse=True)
def mongo_db():
    db_path = tempfile.mkdtemp(dir="/dev/shm")
    mproc = mongoproc.MongoProc(db_path=db_path, port=get_free_tcp_port())
    port_envvar = DEFAULT_PORT_ENVVAR

    mproc.start()
    os.environ[port_envvar] = str(mproc.port)

    yield mproc

    mproc.stop()
    del os.environ[port_envvar]
    shutil.rmtree(db_path)


@pytest.fixture(scope="function", autouse=True)
def deactive_venv():
    old_os_path = os.environ.get("PATH", "")
    old_prefix = sys.prefix
    old_path = sys.path

    yield

    os.environ["PATH"] = old_os_path
    sys.prefix = old_prefix
    sys.path = old_path
    pkg_resources.working_set = pkg_resources.WorkingSet._build_master()


def reset_all():
    resources.resource.reset()
    export.Exporter.reset()
    process.Subprocess.uninitialize()
    asyncio.set_child_watcher(None)
    # No dynamic loading of commands at the moment, so no need to reset/reload
    # command.Commander.reset()
    handler.Commander.reset()
    Project._project = None
    unknown_parameters.clear()


@pytest.fixture(scope="function", autouse=True)
def clean_reset(mongo_client):
    cwd = os.getcwd()

    reset_all()
    yield
    reset_all()

    # reset cwd
    os.chdir(cwd)

    for db_name in mongo_client.list_database_names():
        if db_name != "admin":
            try:
                mongo_client.drop_database(db_name)
            except Exception:
                pass


@pytest.fixture(scope="session")
def mongo_client(mongo_db):
    '''Returns an instance of :class:`pymongo.MongoClient` connected
    to MongoBox database instance.
    '''
    port = int(mongo_db.port)
    return pymongo.MongoClient(port=port)


@pytest.fixture(scope="function")
def motor(mongo_db, mongo_client, event_loop):
    """
    Event_loop argument ensures this fixture is started after the eventloop is started
    """
    client = motor_asyncio.AsyncIOMotorClient('localhost', int(mongo_db.port))
    db = client["inmanta"]
    yield db


@pytest.fixture(scope="function")
async def data_module(motor):
    data.use_motor(motor)
    await data.create_indexes()


@pytest.fixture(scope="function")
def no_agent_backoff():
    backoff = agent.GET_RESOURCE_BACKOFF
    agent.GET_RESOURCE_BACKOFF = 0
    yield
    agent.GET_RESOURCE_BACKOFF = backoff


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
async def agent_multi(server_multi, environment_multi):
    agentmanager = server_multi.get_slice(SLICE_AGENT_MANAGER)

    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    a = agent.Agent(hostname="node1", environment=environment_multi, agent_map={"agent1": "localhost"}, code_loader=False)
    a.add_end_point_name("agent1")
    await a.start()
    await utils.retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    yield a

    await a.stop()


@pytest.fixture(scope="function")
async def server(inmanta_config, mongo_db, mongo_client, motor):
    # fix for fact that pytest_tornado never set IOLoop._instance, the IOLoop of the main thread
    # causes handler failure

    state_dir = tempfile.mkdtemp()

    port = get_free_tcp_port()
    config.Config.set("database", "name", "inmanta-" + ''.join(random.choice(string.ascii_letters) for _ in range(10)))
    config.Config.set("database", "host", "localhost")
    config.Config.set("database", "port", str(mongo_db.port))
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
    await data.create_indexes()

    ibl = InmantaBootloader()
    await ibl.start()

    yield ibl.restserver

    await ibl.stop()
    shutil.rmtree(state_dir)


@pytest.fixture(scope="function",
                params=[(True, True, False), (True, False, False), (False, True, False),
                        (False, False, False), (True, True, True)],
                ids=["SSL and Auth", "SSL", "Auth", "Normal", "SSL and Auth with not self signed certificate"])
async def server_multi(inmanta_config, mongo_db, mongo_client, request, motor):
    state_dir = tempfile.mkdtemp()

    ssl, auth, ca = request.param

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

    if auth:
        config.Config.set("server", "auth", "true")

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
    config.Config.set("database", "name", "inmanta-" + ''.join(random.choice(string.ascii_letters) for _ in range(10)))
    config.Config.set("database", "host", "localhost")
    config.Config.set("database", "port", str(mongo_db.port))
    config.Config.set("config", "state-dir", state_dir)
    config.Config.set("config", "log-dir", os.path.join(state_dir, "logs"))
    config.Config.set("server_rest_transport", "port", port)
    config.Config.set("agent_rest_transport", "port", port)
    config.Config.set("compiler_rest_transport", "port", port)
    config.Config.set("client_rest_transport", "port", port)
    config.Config.set("cmdline_rest_transport", "port", port)
    config.Config.set("config", "executable", os.path.abspath(os.path.join(__file__, "../../src/inmanta/app.py")))
    config.Config.set("server", "agent-timeout", "2")

    data.use_motor(motor)
    await data.create_indexes()

    ibl = InmantaBootloader()
    await ibl.start()

    yield ibl.restserver

    await ibl.stop()

    shutil.rmtree(state_dir)


@pytest.fixture(scope="function")
def client(server):
    client = protocol.Client("client")
    yield client


@pytest.fixture(scope="function")
def client_multi(server_multi):
    client = protocol.Client("client")
    yield client


@pytest.fixture(scope="function")
def sync_client_multi(server_multi):
    client = protocol.SyncClient("client")
    yield client


@pytest.fixture(scope="function", autouse=True)
def capture_warnings():
    logging.captureWarnings(True)
    yield
    logging.captureWarnings(False)


@pytest.fixture(scope="function")
async def environment(client, server):
    """
        Create a project and environment. This fixture returns the uuid of the environment
    """
    def create_project():
        return client.create_project("env-test")

    result = await create_project()
    assert(result.code == 200)
    project_id = result.result["project"]["id"]

    def create_env():
        return client.create_environment(project_id=project_id, name="dev")

    result = await create_env()
    env_id = result.result["environment"]["id"]

    cfg_env.set(env_id)

    yield env_id


@pytest.fixture(scope="function")
async def environment_multi(client_multi, server_multi):
    """
        Create a project and environment. This fixture returns the uuid of the environment
    """
    def create_project():
        return client_multi.create_project("env-test")

    result = await create_project()
    assert(result.code == 200)
    project_id = result.result["project"]["id"]

    def create_env():
        return client_multi.create_environment(project_id=project_id, name="dev")

    result = await create_env()
    env_id = result.result["environment"]["id"]

    yield env_id


class KeepOnFail(object):

    def keep(self) -> "Optional[Dict[str, str]]":
        pass


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # execute all other hooks to obtain the report object
    outcome = yield
    rep = outcome.get_result()

    # we only look at actual failing test calls, not setup/teardown
    resources = {}
    if rep.when == "call" and rep.failed:
        for fixture in item.funcargs.values():
            if isinstance(fixture, KeepOnFail):
                msg = fixture.keep()
                if msg:
                    for label, res in msg.items():
                        resources[label] = res

        if resources:
            # we are behind report formatting, so write to report, not item
            rep.sections.append(("Resources Kept", "\n".join(
                ["%s %s" % (label, resource) for label, resource in resources.items()])))


async def off_main_thread(func):
    return await asyncio.get_event_loop().run_in_executor(None, func)


class SnippetCompilationTest(KeepOnFail):

    def setUpClass(self):
        self.libs = tempfile.mkdtemp()
        self.env = tempfile.mkdtemp()
        config.Config.load_config()
        self.cwd = os.getcwd()
        self.keep_shared = False

    def tearDownClass(self):
        if not self.keep_shared:
            shutil.rmtree(self.libs)
            shutil.rmtree(self.env)
        # reset cwd
        os.chdir(self.cwd)

    def setup_func(self):
        # init project
        self._keep = False
        self.project_dir = tempfile.mkdtemp()
        os.symlink(self.env, os.path.join(self.project_dir, ".env"))

    def tear_down_func(self):
        if not self._keep:
            shutil.rmtree(self.project_dir)

    def keep(self):
        self._keep = True
        self.keep_shared = True
        return {"env": self.env, "libs": self.libs, "project": self.project_dir}

    def setup_for_snippet(self, snippet, autostd=True):
        with open(os.path.join(self.project_dir, "project.yml"), "w") as cfg:
            cfg.write(
                """
            name: snippet test
            modulepath: [%s, %s]
            downloadpath: %s
            version: 1.0
            repo: ['https://github.com/inmanta/']"""
                % (self.libs,
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "modules"),
                    self.libs))

        self.main = os.path.join(self.project_dir, "main.cf")
        with open(self.main, "w") as x:
            x.write(snippet)

        Project.set(Project(self.project_dir, autostd=autostd))

    def do_export(self, include_status=False, do_raise=True):
        return self._do_export(deploy=False, include_status=include_status, do_raise=do_raise)

    def _do_export(self, deploy=False, include_status=False, do_raise=True):
        """
        helper function to allow actual export to be run an a different thread
        i.e. export.run must run off main thread to allow it to start a new ioloop for run_sync
        """
        templfile = mktemp("json", "dump", self.project_dir)

        class Options(object):
            pass

        options = Options()
        options.json = templfile if not deploy else None
        options.depgraph = False
        options.deploy = deploy
        options.ssl = False

        from inmanta.export import Exporter  # noqa: H307

        try:
            (types, scopes) = compiler.do_compile()
        except Exception:
            types, scopes = (None, None)
            if do_raise:
                raise
            else:
                traceback.print_exc()

        # Even if the compile failed we might have collected additional data such as unknowns. So
        # continue the export
        export = Exporter(options)

        return export.run(types, scopes, model_export=False, include_status=include_status)

    async def do_export_and_deploy(self, include_status=False, do_raise=True):
        return await off_main_thread(lambda: self._do_export(deploy=True, include_status=include_status, do_raise=do_raise))

    def setup_for_error(self, snippet, shouldbe):
        self.setup_for_snippet(snippet)
        try:
            compiler.do_compile()
            assert False, "Should get exception"
        except CompilerException as e:
            text = e.format_trace(indent="  ")
            print(text)
            shouldbe = shouldbe.format(dir=self.project_dir)
            assert shouldbe == text

    def setup_for_error_re(self, snippet, shouldbe):
        self.setup_for_snippet(snippet)
        try:
            compiler.do_compile()
            assert False, "Should get exception"
        except CompilerException as e:
            text = e.format_trace(indent="  ")
            print(text)
            shouldbe = shouldbe.format(dir=self.project_dir)
            assert re.search(shouldbe, text) is not None


@pytest.fixture(scope="session")
def snippetcompiler_global():
    ast = SnippetCompilationTest()
    ast.setUpClass()
    yield ast
    ast.tearDownClass()


@pytest.fixture(scope="function")
def snippetcompiler(snippetcompiler_global):
    snippetcompiler_global.setup_func()
    yield snippetcompiler_global
    snippetcompiler_global.tear_down_func()


class CLI(object):
    async def run(self, *args):
        # set column width very wide so lines are not wrapped
        os.environ["COLUMNS"] = "1000"
        runner = testing.CliRunner()
        cmd_args = ["--host", "localhost", "--port", config.Config.get("cmdline_rest_transport", "port")]
        cmd_args.extend(args)

        def invoke():
            return runner.invoke(
                cli=inmanta.main.cmd,
                args=cmd_args,
                catch_exceptions=False
            )

        result = await asyncio.get_event_loop().run_in_executor(None, invoke)
        # reset to default again
        del os.environ["COLUMNS"]
        return result


@pytest.fixture
def cli():
    o = CLI()
    yield o
