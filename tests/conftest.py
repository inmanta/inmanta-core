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
import asyncio
import concurrent
import csv
import datetime
import json
import logging
import os
import queue
import random
import re
import shutil
import socket
import string
import subprocess
import sys
import tempfile
import time
import traceback
import uuid
from typing import Dict, List, Optional, Tuple

import asyncpg
import pkg_resources
import psutil
import pyformance
import pytest
from asyncpg.exceptions import DuplicateDatabaseError
from click import testing
from pyformance.registry import MetricsRegistry
from tornado import netutil
from tornado.platform.asyncio import AnyThreadEventLoopPolicy

import inmanta.agent
import inmanta.app
import inmanta.compiler as compiler
import inmanta.main
from inmanta import config, const, data, loader, protocol, resources
from inmanta.agent import handler
from inmanta.agent.agent import Agent
from inmanta.ast import CompilerException
from inmanta.data.schema import SCHEMA_VERSION_TABLE
from inmanta.export import cfg_env, unknown_parameters
from inmanta.module import Project
from inmanta.postgresproc import PostgresProc
from inmanta.protocol import VersionMatch
from inmanta.server import SLICE_AGENT_MANAGER, SLICE_COMPILER
from inmanta.server.bootloader import InmantaBootloader
from inmanta.server.protocol import SliceStartupException
from inmanta.server.services.compilerservice import CompilerService, CompileRun
from inmanta.types import JsonType

# Import the utils module differently when conftest is put into the inmanta_tests packages
if __file__ and os.path.dirname(__file__).split("/")[-1] == "inmanta_tests":
    from inmanta_tests import utils  # noqa: F401
else:
    import utils

logger = logging.getLogger(__name__)

TABLES_TO_KEEP = [x.table_name() for x in data._classes]


# Database
@pytest.fixture
def postgres_proc(unused_tcp_port_factory):
    proc = PostgresProc(unused_tcp_port_factory())
    yield proc
    proc.stop()


@pytest.fixture(scope="session", autouse=True)
def postgres_db(postgresql_proc):
    yield postgresql_proc


@pytest.fixture
def ensure_running_postgres_db_post(postgres_db):
    yield
    if not postgres_db.running():
        postgres_db.start()


@pytest.fixture(scope="function")
async def create_db(postgres_db, database_name_internal):
    """
    see :py:database_name_internal:
    """
    connection = await asyncpg.connect(host=postgres_db.host, port=postgres_db.port, user=postgres_db.user)
    try:
        await connection.execute(f"CREATE DATABASE {database_name_internal}")
    except DuplicateDatabaseError:
        # Because it is async, this fixture can not be made session scoped.
        # Only the first time it is called, it will actually create a database
        # All other times will drop through here
        pass
    finally:
        await connection.close()
    return database_name_internal


@pytest.fixture(scope="session")
def database_name_internal():
    """
    Internal use only, use database_name instead.

    The database_name fixture is expected to yield the database name to an existing database, and should be session scoped.

    To create the database we need asyncpg. However, async fixtures all depend on the event loop.
    The event loop is function scoped.

    To resolve this, there is a session scoped fixture called database_name_internal that provides a fixed name. create_db
    ensures that the database has been created.
    """
    ten_random_digits = "".join(random.choice(string.digits) for _ in range(10))
    return "inmanta" + ten_random_digits


@pytest.fixture(scope="function")
def database_name(create_db):
    return create_db


@pytest.fixture(scope="function")
async def postgresql_client(postgres_db, database_name):
    client = await asyncpg.connect(host=postgres_db.host, port=postgres_db.port, user=postgres_db.user, database=database_name)
    yield client
    await client.close()


@pytest.fixture(scope="function")
async def postgresql_pool(postgres_db, database_name):
    client = await asyncpg.create_pool(
        host=postgres_db.host, port=postgres_db.port, user=postgres_db.user, database=database_name
    )
    yield client
    await client.close()


@pytest.fixture(scope="function")
async def init_dataclasses_and_load_schema(postgres_db, database_name, clean_reset):
    await data.connect(postgres_db.host, postgres_db.port, database_name, postgres_db.user, None)
    yield
    await data.disconnect()


async def postgress_get_custom_types(postgresql_client):
    # Query extracted from CLI
    # psql -E
    # \dT

    get_custom_types = """
    SELECT n.nspname as "Schema",
      pg_catalog.format_type(t.oid, NULL) AS "Name",
      pg_catalog.obj_description(t.oid, 'pg_type') as "Description"
    FROM pg_catalog.pg_type t
         LEFT JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
    WHERE (t.typrelid = 0 OR (SELECT c.relkind = 'c' FROM pg_catalog.pg_class c WHERE c.oid = t.typrelid))
      AND NOT EXISTS(SELECT 1 FROM pg_catalog.pg_type el WHERE el.oid = t.typelem AND el.typarray = t.oid)
           AND n.nspname <> 'pg_catalog'
          AND n.nspname <> 'information_schema'
      AND pg_catalog.pg_type_is_visible(t.oid)
    ORDER BY 1, 2;
    """

    types_in_db = await postgresql_client.fetch(get_custom_types)
    type_names = [x["Name"] for x in types_in_db]

    return type_names


async def do_clean_hard(postgresql_client):
    assert not postgresql_client.is_in_transaction()
    await postgresql_client.reload_schema_state()
    tables_in_db = await postgresql_client.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    table_names = ["public." + x["table_name"] for x in tables_in_db]
    if table_names:
        drop_query = "DROP TABLE %s CASCADE" % ", ".join(table_names)
        await postgresql_client.execute(drop_query)

    type_names = await postgress_get_custom_types(postgresql_client)
    if type_names:
        drop_query = "DROP TYPE %s" % ", ".join(type_names)
        await postgresql_client.execute(drop_query)
    logger.info("Performed Hard Clean with tables: %s  types: %s", ",".join(table_names), ",".join(type_names))


@pytest.fixture(scope="function")
async def hard_clean_db(postgresql_client):
    await do_clean_hard(postgresql_client)
    yield


@pytest.fixture(scope="function")
async def hard_clean_db_post(postgresql_client):
    yield
    await do_clean_hard(postgresql_client)


@pytest.fixture(scope="function")
async def clean_db(postgresql_pool, create_db, postgres_db):
    """
    1) Truncated tables: All tables which are part of the inmanta schema, except for the schemaversion table. The version
                         number stored in the schemaversion table is read by the Inmanta server during startup.
    2) Dropped tables: All tables which are not part of the inmanta schema. Some tests create additional tables, which are
                       not part of the Inmanta schema. These should be cleaned-up before running a new test.
    """
    yield
    # By using the connection pool, we can make sure that the connection we use is alive
    async with postgresql_pool.acquire() as postgresql_client:
        tables_in_db = await postgresql_client.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
        )
        tables_in_db = [x["table_name"] for x in tables_in_db]
        tables_to_preserve = TABLES_TO_KEEP
        tables_to_preserve.append(SCHEMA_VERSION_TABLE)
        tables_to_truncate = [x for x in tables_in_db if x in tables_to_preserve and x != SCHEMA_VERSION_TABLE]
        tables_to_drop = [x for x in tables_in_db if x not in tables_to_preserve]
        if tables_to_drop:
            drop_query = "DROP TABLE %s CASCADE" % ", ".join(tables_to_drop)
            await postgresql_client.execute(drop_query)
        if tables_to_truncate:
            truncate_query = "TRUNCATE %s CASCADE" % ", ".join(tables_to_truncate)
            await postgresql_client.execute(truncate_query)


@pytest.fixture(scope="function")
def get_columns_in_db_table(postgresql_client):
    async def _get_columns_in_db_table(table_name):
        result = await postgresql_client.fetch(
            "SELECT column_name "
            "FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='" + table_name + "'"
        )
        return [r["column_name"] for r in result]

    return _get_columns_in_db_table


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
    methods = inmanta.protocol.common.MethodProperties.methods.copy()
    loader.unload_inmanta_plugins()
    yield
    inmanta.protocol.common.MethodProperties.methods = methods
    config.Config._reset()
    reset_all_objects()
    loader.unload_inmanta_plugins()


def reset_all_objects():
    resources.resource.reset()
    asyncio.set_child_watcher(None)
    reset_metrics()
    # No dynamic loading of commands at the moment, so no need to reset/reload
    # command.Commander.reset()
    handler.Commander.reset()
    Project._project = None
    unknown_parameters.clear()


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
    bound_sockets = []

    def _free_socket():
        sock = netutil.bind_sockets(0, "127.0.0.1", family=socket.AF_INET)[0]
        bound_sockets.append(sock)
        return sock

    yield _free_socket
    for s in bound_sockets:
        s.close()


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


@pytest.fixture
def server_pre_start():
    """This fixture is called by the server. Override this fixture to influence server config"""


@pytest.fixture(scope="function")
async def agent_multi(server_multi, environment_multi):
    agentmanager = server_multi.get_slice(SLICE_AGENT_MANAGER)

    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    a = Agent(hostname="node1", environment=environment_multi, agent_map={"agent1": "localhost"}, code_loader=False)
    await a.add_end_point_name("agent1")
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
    await a.add_end_point_name("agent1")
    await a.start()
    await utils.retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    yield a

    await a.stop()


@pytest.fixture(scope="function")
async def agent_factory(server):
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")

    started_agents = []

    async def create_agent(
        environment: uuid.UUID,
        hostname: Optional[str] = None,
        agent_map: Optional[Dict[str, str]] = None,
        code_loader: bool = False,
        agent_names: List[str] = [],
    ) -> None:
        a = Agent(hostname=hostname, environment=environment, agent_map=agent_map, code_loader=code_loader)
        for agent_name in agent_names:
            await a.add_end_point_name(agent_name)
        await a.start()
        started_agents.append(a)
        await utils.retry_limited(lambda: a.sessionid in agentmanager.sessions, 10)
        return a

    yield create_agent
    await asyncio.gather(*[agent.stop() for agent in started_agents])


@pytest.fixture(scope="function")
async def autostarted_agent(server, environment):
    """Configure agent1 as an autostarted agent."""
    env = await data.Environment.get_by_id(uuid.UUID(environment))
    await env.set(data.AUTOSTART_AGENT_MAP, {"internal": "", "agent1": ""})
    await env.set(data.AUTO_DEPLOY, True)
    await env.set(data.PUSH_ON_AUTO_DEPLOY, True)
    # disable deploy and repair intervals
    await env.set(data.AUTOSTART_AGENT_DEPLOY_INTERVAL, 0)
    await env.set(data.AUTOSTART_AGENT_REPAIR_INTERVAL, 0)
    await env.set(data.AUTOSTART_ON_START, True)


@pytest.fixture(scope="function")
def client_v2(server):
    client = protocol.Client("client", version_match=VersionMatch.exact, exact_version=2)
    yield client


@pytest.fixture(scope="session")
def log_file():
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    output_file = os.path.join(output_dir, "log.txt")
    with open(output_file, "w", encoding="utf-8") as f:
        yield f


@pytest.fixture(scope="function", autouse="DEBUG_TCP_PORTS" in os.environ)
def log_state_tcp_ports(request, log_file):
    def _write_log_line(title):
        connections = psutil.net_connections()
        writer = csv.writer(log_file, dialect="unix")

        def map_data_line(line):
            out = [
                title,
                line.fd,
                str(line.family),
                str(line.type),
                f"{line.laddr.ip}|{line.laddr.port}" if line.laddr else None,
                f"{line.raddr.ip}|{line.raddr.port}" if line.raddr else None,
                line.status,
                None if "pid" not in line else line.pid,
            ]
            return out

        for con in connections:
            writer.writerow(map_data_line(con))

    _write_log_line(f"Before run test case {request.function.__name__}:")
    yield
    _write_log_line(f"After run test case {request.function.__name__}:")


@pytest.fixture(scope="function")
async def server_config(event_loop, inmanta_config, postgres_db, database_name, clean_reset, unused_tcp_port_factory):
    reset_metrics()

    state_dir = tempfile.mkdtemp()

    port = str(unused_tcp_port_factory())

    config.Config.set("database", "name", database_name)
    config.Config.set("database", "host", "localhost")
    config.Config.set("database", "port", str(postgres_db.port))
    config.Config.set("database", "connection_timeout", str(3))
    config.Config.set("config", "state-dir", state_dir)
    config.Config.set("config", "log-dir", os.path.join(state_dir, "logs"))
    config.Config.set("agent_rest_transport", "port", port)
    config.Config.set("compiler_rest_transport", "port", port)
    config.Config.set("client_rest_transport", "port", port)
    config.Config.set("cmdline_rest_transport", "port", port)
    config.Config.set("server", "bind-port", port)
    config.Config.set("server", "bind-address", "127.0.0.1")
    config.Config.set("config", "executable", os.path.abspath(inmanta.app.__file__))
    config.Config.set("server", "agent-timeout", "2")
    config.Config.set("server", "auto-recompile-wait", "0")
    config.Config.set("agent", "agent-repair-interval", "0")
    yield config
    shutil.rmtree(state_dir)


@pytest.fixture(scope="function")
async def server(server_pre_start, server_config):
    """
    :param event_loop: explicitly include event_loop to make sure event loop started before and closed after this fixture.
    May not be required
    """
    # fix for fact that pytest_tornado never set IOLoop._instance, the IOLoop of the main thread
    # causes handler failure

    ibl = InmantaBootloader()

    try:
        await ibl.start()
    except SliceStartupException as e:
        port = config.Config.get("server", "bind-port")
        output = subprocess.check_output(["ss", "-antp"])
        output = output.decode("utf-8")
        logger.debug(f"Port: {port}")
        logger.debug(f"Port usage: \n {output}")
        raise e

    yield ibl.restserver

    try:
        await asyncio.wait_for(ibl.stop(), 15)
    except concurrent.futures.TimeoutError:
        logger.exception("Timeout during stop of the server in teardown")

    logger.info("Server clean up done")


@pytest.fixture(
    scope="function",
    params=[(True, True, False), (True, False, False), (False, True, False), (False, False, False), (True, True, True)],
    ids=["SSL and Auth", "SSL", "Auth", "Normal", "SSL and Auth with not self signed certificate"],
)
async def server_multi(
    server_pre_start, event_loop, inmanta_config, postgres_db, database_name, request, clean_reset, unused_tcp_port_factory
):
    """
    :param event_loop: explicitly include event_loop to make sure event loop started before and closed after this fixture.
    May not be required
    """
    state_dir = tempfile.mkdtemp()

    ssl, auth, ca = request.param

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

    if auth:
        config.Config.set("server", "auth", "true")

    for x, ct in [
        ("server", None),
        ("agent_rest_transport", ["agent"]),
        ("compiler_rest_transport", ["compiler"]),
        ("client_rest_transport", ["api", "compiler"]),
        ("cmdline_rest_transport", ["api"]),
    ]:
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

    port = str(unused_tcp_port_factory())
    config.Config.set("database", "name", database_name)
    config.Config.set("database", "host", "localhost")
    config.Config.set("database", "port", str(postgres_db.port))
    config.Config.set("database", "connection_timeout", str(3))
    config.Config.set("config", "state-dir", state_dir)
    config.Config.set("config", "log-dir", os.path.join(state_dir, "logs"))
    config.Config.set("agent_rest_transport", "port", port)
    config.Config.set("compiler_rest_transport", "port", port)
    config.Config.set("client_rest_transport", "port", port)
    config.Config.set("cmdline_rest_transport", "port", port)
    config.Config.set("server", "bind-port", port)
    config.Config.set("server", "bind-address", "127.0.0.1")
    config.Config.set("config", "executable", os.path.abspath(inmanta.app.__file__))
    config.Config.set("server", "agent-timeout", "2")
    config.Config.set("agent", "agent-repair-interval", "0")
    config.Config.set("server", "auto-recompile-wait", "0")

    ibl = InmantaBootloader()

    try:
        await ibl.start()
    except SliceStartupException as e:
        port = config.Config.get("server", "bind-port")
        output = subprocess.check_output(["ss", "-antp"])
        output = output.decode("utf-8")
        logger.debug(f"Port: {port}")
        logger.debug(f"Port usage: \n {output}")
        raise e

    yield ibl.restserver
    try:
        await asyncio.wait_for(ibl.stop(), 15)
    except concurrent.futures.TimeoutError:
        logger.exception("Timeout during stop of the server in teardown")

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


@pytest.fixture(scope="function")
def clienthelper(client, environment):
    return utils.ClientHelper(client, environment)


@pytest.fixture(scope="function", autouse=True)
def capture_warnings():
    logging.captureWarnings(True)
    yield
    logging.captureWarnings(False)


@pytest.fixture(scope="function")
async def environment(client, server, environment_default):
    """
    Create a project and environment, with auto_deploy turned off. This fixture returns the uuid of the environment
    """

    env = await data.Environment.get_by_id(uuid.UUID(environment_default))
    await env.set(data.AUTO_DEPLOY, False)
    await env.set(data.PUSH_ON_AUTO_DEPLOY, False)
    await env.set(data.AGENT_TRIGGER_METHOD_ON_AUTO_DEPLOY, const.AgentTriggerMethod.push_full_deploy)

    yield environment_default


@pytest.fixture(scope="function")
async def environment_default(client, server):
    """
    Create a project and environment. This fixture returns the uuid of the environment
    """
    result = await client.create_project("env-test")
    assert result.code == 200
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
    assert result.code == 200
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
        with open(schema_update_file, "w+", encoding="utf-8") as f:
            f.write(content_file)

    yield _write_db_update_file


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
            rep.sections.append(
                ("Resources Kept", "\n".join(["%s %s" % (label, resource) for label, resource in resources.items()]))
            )


async def off_main_thread(func):
    # work around for https://github.com/pytest-dev/pytest-asyncio/issues/168
    asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
    return await asyncio.get_event_loop().run_in_executor(None, func)


class SnippetCompilationTest(KeepOnFail):
    def setUpClass(self):
        self.libs = tempfile.mkdtemp()
        self.repo = "https://github.com/inmanta/"
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

    def setup_func(self, module_dir):
        # init project
        self._keep = False
        self.project_dir = tempfile.mkdtemp()
        self.modules_dir = module_dir
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
        loader.unload_inmanta_plugins()

    def reset(self):
        Project.set(Project(self.project_dir, autostd=Project.get().autostd))
        loader.unload_inmanta_plugins()

    def setup_for_snippet_external(self, snippet):
        if self.modules_dir:
            module_path = f"[{self.libs}, {self.modules_dir}]"
        else:
            module_path = f"{self.libs}"
        with open(os.path.join(self.project_dir, "project.yml"), "w", encoding="utf-8") as cfg:
            cfg.write(
                """
            name: snippet test
            modulepath: %s
            downloadpath: %s
            version: 1.0
            repo: ['%s']"""
                % (module_path, self.libs, self.repo)
            )
        self.main = os.path.join(self.project_dir, "main.cf")
        with open(self.main, "w", encoding="utf-8") as x:
            x.write(snippet)

    def do_export(self, include_status=False, do_raise=True):
        return self._do_export(deploy=False, include_status=include_status, do_raise=do_raise)

    def get_exported_json(self) -> JsonType:
        with open(os.path.join(self.project_dir, "dump.json")) as fh:
            return json.load(fh)

    def _do_export(self, deploy=False, include_status=False, do_raise=True):
        """
        helper function to allow actual export to be run an a different thread
        i.e. export.run must run off main thread to allow it to start a new ioloop for run_sync
        """

        class Options(object):
            pass

        options = Options()
        options.json = os.path.join(self.project_dir, "dump.json") if not deploy else None
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

    def setup_for_error(self, snippet, shouldbe, indent_offset=0):
        self.setup_for_snippet(snippet)
        try:
            compiler.do_compile()
            assert False, "Should get exception"
        except CompilerException as e:
            text = e.format_trace(indent="  ", indent_level=indent_offset)
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
def snippetcompiler(snippetcompiler_global, modules_dir):
    snippetcompiler_global.setup_func(modules_dir)
    yield snippetcompiler_global
    snippetcompiler_global.tear_down_func()


@pytest.fixture(scope="function")
def snippetcompiler_clean(modules_dir):
    ast = SnippetCompilationTest()
    ast.setUpClass()
    ast.setup_func(modules_dir)
    yield ast
    ast.tear_down_func()
    ast.tearDownClass()


@pytest.fixture(scope="session")
def modules_dir():
    yield os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "modules")


class CLI(object):
    async def run(self, *args, **kwargs):
        # set column width very wide so lines are not wrapped
        os.environ["COLUMNS"] = "1000"
        runner = testing.CliRunner(mix_stderr=False)
        cmd_args = ["--host", "localhost", "--port", config.Config.get("cmdline_rest_transport", "port")]
        cmd_args.extend(args)

        def invoke():
            return runner.invoke(cli=inmanta.main.cmd, args=cmd_args, catch_exceptions=False, **kwargs)

        result = await asyncio.get_event_loop().run_in_executor(None, invoke)
        # reset to default again
        del os.environ["COLUMNS"]
        return result


@pytest.fixture
def cli():
    # work around for https://github.com/pytest-dev/pytest-asyncio/issues/168
    asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
    o = CLI()
    yield o


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


class CompileRunnerMock(object):
    def __init__(
        self, request: data.Compile, make_compile_fail: bool = False, runner_queue: Optional[queue.Queue] = None
    ) -> None:
        self.request = request
        self.version: Optional[int] = None
        self._make_compile_fail = make_compile_fail
        self._runner_queue = runner_queue
        self.block = False

    async def run(self, force_update: Optional[bool] = False) -> Tuple[bool, None]:
        now = datetime.datetime.now()
        returncode = 1 if self._make_compile_fail else 0
        report = data.Report(
            compile=self.request.id, started=now, name="CompileRunnerMock", command="", completed=now, returncode=returncode
        )
        await report.insert()
        self.version = int(time.time())
        success = not self._make_compile_fail

        if self._runner_queue is not None:
            self._runner_queue.put(self)
            self.block = True
            while self.block:
                await asyncio.sleep(0.1)

        return success, None


def monkey_patch_compiler_service(monkeypatch, server, make_compile_fail, runner_queue=None):
    compilerslice: CompilerService = server.get_slice(SLICE_COMPILER)

    def patch(compile: data.Compile, project_dir: str) -> CompileRun:
        return CompileRunnerMock(compile, make_compile_fail, runner_queue)

    monkeypatch.setattr(compilerslice, "_get_compile_runner", patch, raising=True)


@pytest.fixture
async def mocked_compiler_service(server, monkeypatch):
    monkey_patch_compiler_service(monkeypatch, server, False)


@pytest.fixture
async def mocked_compiler_service_failing_compile(server, monkeypatch):
    monkey_patch_compiler_service(monkeypatch, server, True)


@pytest.fixture
async def mocked_compiler_service_block(server, monkeypatch):
    runner_queue = queue.Queue()
    monkey_patch_compiler_service(monkeypatch, server, True, runner_queue)

    yield runner_queue
