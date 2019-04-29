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
from inmanta import data, config
import inmanta.compiler as compiler
from inmanta.module import Project
from inmanta import resources
import inmanta.agent
from inmanta.agent import handler
from inmanta.agent.agent import Agent
from inmanta.ast import CompilerException
from click import testing
import inmanta.main
import re
from inmanta.server.bootloader import InmantaBootloader
from inmanta.server import SLICE_AGENT_MANAGER
from inmanta.export import cfg_env, unknown_parameters
import traceback
from tornado import process, netutil
import asyncio
from tornado.platform.asyncio import AnyThreadEventLoopPolicy
import asyncpg
from asyncpg.exceptions import DuplicateDatabaseError
from inmanta.postgresproc import PostgresProc
import sys
import pkg_resources
from typing import Optional, Dict
from inmanta import protocol
import pyformance
from pyformance.registry import MetricsRegistry

from inmanta.util import get_free_tcp_port

asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())


@pytest.fixture(scope="session", autouse=True)
def postgres_db(postgresql_proc):
    yield postgresql_proc


@pytest.fixture(scope="function")
async def postgresql_client(postgres_db, database_name):
    client = await asyncpg.connect(host=postgres_db.host, port=postgres_db.port, user=postgres_db.user, database=database_name)
    try:
        yield client
    finally:
        await client.close()


@pytest.fixture(scope="function")
async def init_dataclasses_and_load_schema(postgres_db, database_name, clean_reset):
    await data.connect(postgres_db.host, postgres_db.port, database_name, postgres_db.user, None)
    yield
    await data.disconnect()


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


def reset_metrics():
    pyformance.set_global_registry(MetricsRegistry())


@pytest.fixture(scope="function", autouse=True)
async def clean_reset(create_db, clean_db):
    reset_all_objects()
    config.Config._reset()
    yield
    config.Config._reset()
    reset_all_objects()


def reset_all_objects():
    resources.resource.reset()
    process.Subprocess.uninitialize()
    asyncio.set_child_watcher(None)
    reset_metrics()
    # No dynamic loading of commands at the moment, so no need to reset/reload
    # command.Commander.reset()
    handler.Commander.reset()
    Project._project = None
    unknown_parameters.clear()


@pytest.fixture(scope="function")
async def create_db(postgres_db, database_name):
    connection = await asyncpg.connect(host=postgres_db.host, port=postgres_db.port, user=postgres_db.user)
    try:
        await connection.execute("CREATE DATABASE " + database_name)
    except DuplicateDatabaseError:
        pass
    finally:
        await connection.close()


@pytest.fixture(scope="function")
async def clean_db(postgresql_client, create_db):
    """
        1) Truncated tables: All tables which are part of the inmanta schema, except for the schemaversion table. The version
                             number stored in the schemaversion table is read by the Inmanta server during startup.
        2) Dropped tables: All tables which are not part of the inmanta schema. Some tests create additional tables, which are
                           not part of the Inmanta schema. These should be cleaned-up before running a new test.
    """
    tables_in_db = await postgresql_client.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    tables_in_db = [x["table_name"] for x in tables_in_db]
    tables_to_preserve = [x.table_name() for x in data._classes]
    tables_to_truncate = [x for x in tables_in_db if x != data.SchemaVersion.table_name() and x in tables_to_preserve]
    tables_to_drop = [x for x in tables_in_db if x not in tables_to_preserve]
    if tables_to_drop:
        drop_query = "DROP TABLE %s CASCADE" % ', '.join(tables_to_drop)
        await postgresql_client.execute(drop_query)
    if tables_to_truncate:
        truncate_query = "TRUNCATE %s CASCADE" % ', '.join(tables_to_truncate)
        await postgresql_client.execute(truncate_query)


@pytest.fixture(scope="function", autouse=True)
def restore_cwd():
    """
        Restore the current working directory after search test.
    """
    cwd = os.getcwd()
    yield
    os.chdir(cwd)


@pytest.fixture(scope="function")
def no_agent_backoff():
    backoff = inmanta.agent.agent.GET_RESOURCE_BACKOFF
    inmanta.agent.agent.GET_RESOURCE_BACKOFF = 0
    yield
    inmanta.agent.agent.GET_RESOURCE_BACKOFF = backoff


@pytest.fixture()
def free_socket():
    sock = netutil.bind_sockets(0, "127.0.0.1", family=socket.AF_INET)[0]
    yield sock
    sock.close()


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


@pytest.fixture(scope="session")
def database_name():
    ten_random_digits = ''.join(random.choice(string.digits) for _ in range(10))
    yield "inmanta" + ten_random_digits


@pytest.fixture(scope="function")
async def agent_multi(server_multi, environment_multi):
    agentmanager = server_multi.get_slice(SLICE_AGENT_MANAGER)

    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    a = Agent(hostname="node1", environment=environment_multi, agent_map={"agent1": "localhost"}, code_loader=False)
    a.add_end_point_name("agent1")
    await a.start()
    await utils.retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    yield a

    await a.stop()


@pytest.fixture(scope="function")
async def agent(server, environment):
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    a = Agent(hostname="node1", environment=environment, agent_map={"agent1": "localhost"}, code_loader=False)
    a.add_end_point_name("agent1")
    await a.start()
    await utils.retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    yield a

    await a.stop()


@pytest.fixture(scope="function")
async def server(event_loop, inmanta_config, postgres_db, database_name, clean_reset):
    """
    :param event_loop: explicitly include event_loop to make sure event loop started before and closed after this fixture.
    May not be required
    """
    # fix for fact that pytest_tornado never set IOLoop._instance, the IOLoop of the main thread
    # causes handler failure

    reset_metrics()

    state_dir = tempfile.mkdtemp()

    port = get_free_tcp_port()
    config.Config.set("database", "name", database_name)
    config.Config.set("database", "host", "localhost")
    config.Config.set("database", "port", str(postgres_db.port))
    config.Config.set("config", "state-dir", state_dir)
    config.Config.set("config", "log-dir", os.path.join(state_dir, "logs"))
    config.Config.set("server_rest_transport", "port", port)
    config.Config.set("agent_rest_transport", "port", port)
    config.Config.set("compiler_rest_transport", "port", port)
    config.Config.set("client_rest_transport", "port", port)
    config.Config.set("cmdline_rest_transport", "port", port)
    config.Config.set("config", "executable", os.path.abspath(os.path.join(__file__, "../../src/inmanta/app.py")))
    config.Config.set("server", "agent-timeout", "10")
    config.Config.set("server", "auto-recompile-wait", "0")
    config.Config.set("agent", "agent-repair-interval", "0")

    ibl = InmantaBootloader()
    await ibl.start()

    yield ibl.restserver

    await asyncio.wait_for(ibl.stop(), 10)
    shutil.rmtree(state_dir)


@pytest.fixture(scope="function",
                params=[(True, True, False), (True, False, False), (False, True, False),
                        (False, False, False), (True, True, True)],
                ids=["SSL and Auth", "SSL", "Auth", "Normal", "SSL and Auth with not self signed certificate"])
async def server_multi(event_loop, inmanta_config, postgres_db, database_name, request, clean_reset):
    """
    :param event_loop: explicitly include event_loop to make sure event loop started before and closed after this fixture.
    May not be required
    """
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
    config.Config.set("database", "name", database_name)
    config.Config.set("database", "host", "localhost")
    config.Config.set("database", "port", str(postgres_db.port))
    config.Config.set("config", "state-dir", state_dir)
    config.Config.set("config", "log-dir", os.path.join(state_dir, "logs"))
    config.Config.set("server_rest_transport", "port", port)
    config.Config.set("agent_rest_transport", "port", port)
    config.Config.set("compiler_rest_transport", "port", port)
    config.Config.set("client_rest_transport", "port", port)
    config.Config.set("cmdline_rest_transport", "port", port)
    config.Config.set("config", "executable", os.path.abspath(os.path.join(__file__, "../../src/inmanta/app.py")))
    config.Config.set("server", "agent-timeout", "2")
    config.Config.set("agent", "agent-repair-interval", "0")
    config.Config.set("server", "auto-recompile-wait", "0")

    ibl = InmantaBootloader()
    await ibl.start()

    yield ibl.restserver

    await asyncio.wait_for(ibl.stop(), 10)

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
    result = await client.create_project("env-test")
    assert(result.code == 200)
    project_id = result.result["project"]["id"]

    result = await client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    cfg_env.set(env_id)

    yield env_id


@pytest.fixture(scope="function")
async def environment_multi(client_multi, server_multi):
    """
        Create a project and environment. This fixture returns the uuid of the environment
    """
    result = await client_multi.create_project("env-test")
    assert(result.code == 200)
    project_id = result.result["project"]["id"]

    result = await client_multi.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    cfg_env.set(env_id)

    yield env_id


@pytest.fixture(scope="session")
def write_db_update_file():

    def _write_db_update_file(schema_dir, schema_version, content_file):
        schema_updates_dir = os.path.join(schema_dir, data.DBSchema.DIR_NAME_INCREMENTAL_UPDATES)
        if not os.path.exists(schema_updates_dir):
            os.mkdir(schema_updates_dir)
        schema_update_file = os.path.join(schema_updates_dir, str(schema_version) + ".sql")
        with open(schema_update_file, 'w+') as f:
            f.write(content_file)
    yield _write_db_update_file


@pytest.fixture(scope="function")
def get_columns_in_db_table(postgresql_client):
    async def _get_columns_in_db_table(table_name):
        result = await postgresql_client.fetch("SELECT column_name "
                                               "FROM information_schema.columns "
                                               "WHERE table_schema='public' AND table_name='" + table_name + "'")
        return [r["column_name"] for r in result]
    return _get_columns_in_db_table


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
        self.setup_for_snippet_external(snippet)

        Project.set(Project(self.project_dir, autostd=autostd))

    def setup_for_snippet_external(self, snippet):
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


@pytest.fixture
def postgres_proc(free_port):
    proc = PostgresProc(int(free_port))
    yield proc
    proc.stop()


class AsyncCleaner(object):

    def __init__(self):
        self.register = []

    def add(self, method):
        self.register.append(method)

    def __call__(self, method):
        self.add(method)


@pytest.fixture
async def async_finalizer():
    cleaner = AsyncCleaner()
    yield cleaner
    await asyncio.gather(*[item() for item in cleaner.register])
