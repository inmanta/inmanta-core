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
import warnings

import toml

"""
About the use of @parametrize_any and @slowtest:

For parametrized tests:
- if the test is fast and tests different things for each parameter, use @parametrize
- if the parameters only slightly increase the coverage of the test (some different exception path,...), use @parametrize_any.
- if a test is slow, use @parametrize_any

The @slowtest annotation is usually added on test periodically, when the test suite becomes too slow.
We analyze performance and place the @slowtest in the best places.
It is often harder to correctly judge what is slow up front, so we do it in bulk when we have all the (historical) data.
This also allows test to run a few hundred times before being marked as slow.
"""

"""
About venvs in tests (see linked objects' docstrings for more details):
During normal operation the module loader and the compiler work with the following environments:
- inmanta.env.process_env: inmanta.env.ActiveEnv -> presents an interface to interact with the outer (developer's) venv. Used by
    inmanta.module.Project to install v2 modules in.
- inmanta.module.Project.virtualenv: inmanta.env.VirtualEnv -> compiler venv. Used by the compiler to install v1 module
    requirements in. Inherits from the outer venv.

When running the tests we don't want to make changes to the outer environment. So for tests that install Python packages we need
to make sure those are installed in a test environment. This means patching the inmanta.env.process_env to be an interface
to a test environment instead of the outer environment.
The following fixtures manage test environments:
- snippetcompiler_clean: activates the Project's compiler venv and patches inmanta.env.process_env to use this same venv
    as if it were the outer venv. The activation and patch is applied when compiling the first snippet.
- snippetcompiler: same as snippetcompiler_clean but the compiler venv is shared among all tests using the
    fixture.
- tmpvenv: provides a decoupled test environment (does not inherit from the outer environment) but does not activate it and
    does not patch inmanta.env.process_env.
- tmpvenv_active: provides a decoupled test environment, activates it and patches inmanta.env.process_env to point to this
    environment.

The deactive_venv autouse fixture cleans up all venv activation and resets inmanta.env.process_env to point to the outer
environment.
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
import site
import socket
import string
import subprocess
import sys
import tempfile
import time
import traceback
import uuid
import venv
from collections import abc
from configparser import ConfigParser
from typing import AsyncIterator, Awaitable, Callable, Dict, Iterator, List, Optional, Tuple, Union

import asyncpg
import pkg_resources
import psutil
import py
import pyformance
import pytest
from asyncpg.exceptions import DuplicateDatabaseError
from click import testing
from pkg_resources import Requirement
from pyformance.registry import MetricsRegistry
from tornado import netutil
from tornado.platform.asyncio import AnyThreadEventLoopPolicy

import build.env
import inmanta
import inmanta.agent
import inmanta.app
import inmanta.compiler as compiler
import inmanta.compiler.config
import inmanta.main
from inmanta import config, const, data, env, loader, protocol, resources
from inmanta.agent import handler
from inmanta.agent.agent import Agent
from inmanta.ast import CompilerException
from inmanta.data.schema import SCHEMA_VERSION_TABLE
from inmanta.db import util as db_util
from inmanta.env import LocalPackagePath, VirtualEnv, mock_process_env
from inmanta.export import ResourceDict, cfg_env, unknown_parameters
from inmanta.module import InmantaModuleRequirement, InstallMode, Project, RelationPrecedenceRule
from inmanta.moduletool import IsolatedEnvBuilderCached, ModuleTool, V2ModuleBuilder
from inmanta.parser.plyInmantaParser import cache_manager
from inmanta.protocol import VersionMatch
from inmanta.server import SLICE_AGENT_MANAGER, SLICE_COMPILER
from inmanta.server.bootloader import InmantaBootloader
from inmanta.server.protocol import Server, SliceStartupException
from inmanta.server.services.compilerservice import CompilerService, CompileRun
from inmanta.types import JsonType
from inmanta.warnings import WarningsManager
from libpip2pi.commands import dir2pi
from packaging.version import Version

# Import test modules differently when conftest is put into the inmanta_tests packages
PYTEST_PLUGIN_MODE: bool = __file__ and os.path.dirname(__file__).split("/")[-1] == "inmanta_tests"
if PYTEST_PLUGIN_MODE:
    from inmanta_tests import utils  # noqa: F401
else:
    import utils

# These elements were moved to inmanta.db.util to allow them to be used from other extensions.
# This import statement is present to ensure backwards compatibility.
from inmanta.db.util import MODE_READ_COMMAND, MODE_READ_INPUT, AsyncSingleton, PGRestore  # noqa: F401
from inmanta.db.util import clear_database as do_clean_hard  # noqa: F401
from inmanta.db.util import postgres_get_custom_types as postgress_get_custom_types  # noqa: F401

logger = logging.getLogger(__name__)

TABLES_TO_KEEP = [x.table_name() for x in data._classes] + ["resourceaction_resource"]  # Join table

# Save the cwd as early as possible to prevent that it gets overridden by another fixture
# before it's saved.
initial_cwd = os.getcwd()


def _pytest_configure_plugin_mode(config: "pytest.Config") -> None:
    # register custom markers
    config.addinivalue_line(
        "markers",
        "slowtest",
    )
    config.addinivalue_line(
        "markers",
        "parametrize_any: only execute one of the parameterized cases when in fast mode (see documentation in conftest.py)",
    )
    config.addinivalue_line(
        "markers",
        "db_restore_dump(dump): mark the db dump to restore. To be used in conjunction with the `migrate_db_from` fixture.",
    )


def pytest_configure(config: "pytest.Config") -> None:
    if PYTEST_PLUGIN_MODE:
        _pytest_configure_plugin_mode(config)


def pytest_addoption(parser):
    parser.addoption(
        "--fast",
        action="store_true",
        help="Don't run all test, but a representative set",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_generate_tests(metafunc: "pytest.Metafunc") -> None:
    """
    For each test marked as parametrize_any run it either as
    1. if not in fast mode: as if annotated with @parametrize
    2. if in fast mode: with only one parameter combination, chosen randomly
    """

    is_fast = metafunc.config.getoption("fast")
    for marker in metafunc.definition.iter_markers(name="parametrize_any"):
        variations = len(marker.args[1])
        if not is_fast or variations < 2:
            metafunc.definition.add_marker(pytest.mark.parametrize(*marker.args))
        else:
            # select one random item
            args = list(marker.args)
            selected = args[1][random.randrange(0, variations)]
            args[1] = [selected]
            metafunc.definition.add_marker(pytest.mark.parametrize(*args))


def pytest_runtest_setup(item: "pytest.Item"):
    """
    When in fast mode, skip test marked as slow and db_migration tests that are older than 30 days.
    """
    is_fast = item.config.getoption("fast")
    if not is_fast:
        return
    if any(True for mark in item.iter_markers(name="slowtest")):
        pytest.skip("Skipping slow tests")

    file_name: str = item.location[0]
    if file_name.startswith("tests/db/migration_tests"):
        match: Optional[re.Match] = re.fullmatch("tests/db/migration_tests/test_v[0-9]{9}_to_v([0-9]{8})[0-9].py", file_name)
        if not match:
            pytest.fail(
                "The name of the test file might be incorrect: Should be test_v<old_version>_to_v<new_version>.py or the test "
                "should have the @slowtest annotation"
            )
        timestamp: str = match.group(1)
        test_creation_date: datetime.datetime = datetime.datetime(int(timestamp[0:4]), int(timestamp[4:6]), int(timestamp[6:8]))
        elapsed_days: int = (datetime.datetime.today() - test_creation_date).days
        if elapsed_days > 30:
            pytest.skip("Skipping old migration test")


@pytest.fixture(scope="session")
def postgres_db(request: pytest.FixtureRequest):
    """This fixture loads the pytest-postgresql fixture. When --postgresql-host is set, it will use the noproc
    fixture to use an external database. Without this option, an "embedded" postgres is started.
    """
    option_name = "postgresql_host"
    conf = request.config.getoption(option_name)
    if conf:
        fixture = "postgresql_noproc"
    else:
        fixture = "postgresql_proc"

    logger.info("Using database fixture %s", fixture)
    yield request.getfixturevalue(fixture)


@pytest.fixture
async def postgres_db_debug(postgres_db, database_name) -> abc.AsyncIterator[None]:
    """
    Fixture meant for debugging through manual interaction with the database. Run pytest with `-s/--capture=no`.
    """
    yield
    print(
        "Connection to DB will be kept alive for one hour. Connect with"
        f" `psql --host localhost --port {postgres_db.port} {database_name} {postgres_db.user}`"
    )
    await asyncio.sleep(3600)


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
    connection = await asyncpg.connect(
        host=postgres_db.host, port=postgres_db.port, user=postgres_db.user, password=postgres_db.password
    )
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
    client = await asyncpg.connect(
        host=postgres_db.host,
        port=postgres_db.port,
        user=postgres_db.user,
        password=postgres_db.password,
        database=database_name,
    )
    yield client
    await client.close()


@pytest.fixture(scope="function")
async def postgresql_pool(postgres_db, database_name):
    client = await asyncpg.create_pool(
        host=postgres_db.host,
        port=postgres_db.port,
        user=postgres_db.user,
        password=postgres_db.password,
        database=database_name,
    )
    yield client
    await client.close()


@pytest.fixture(scope="function")
async def init_dataclasses_and_load_schema(postgres_db, database_name, clean_reset):
    await data.connect(
        host=postgres_db.host,
        port=postgres_db.port,
        username=postgres_db.user,
        password=postgres_db.password,
        database=database_name,
    )
    yield
    await data.disconnect()


@pytest.fixture(scope="function")
async def hard_clean_db(postgresql_client):
    await db_util.clear_database(postgresql_client)
    yield


@pytest.fixture(scope="function")
async def hard_clean_db_post(postgresql_client):
    yield
    await db_util.clear_database(postgresql_client)


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
    async def _get_columns_in_db_table(table_name: str) -> List[str]:
        result = await postgresql_client.fetch(
            "SELECT column_name "
            "FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='" + table_name + "'"
        )
        return [r["column_name"] for r in result]

    return _get_columns_in_db_table


@pytest.fixture(scope="function")
def get_primary_key_columns_in_db_table(postgresql_client):
    async def _get_primary_key_columns_in_db_table(table_name: str) -> List[str]:
        # Query taken from here: https://wiki.postgresql.org/wiki/Retrieve_primary_key_columns
        result = await postgresql_client.fetch(
            "SELECT a.attname FROM pg_index i "
            "JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
            "WHERE i.indrelid = '" + table_name + "'::regclass "
            "AND i.indisprimary;"
        )
        return [r["attname"] for r in result]

    return _get_primary_key_columns_in_db_table


@pytest.fixture(scope="function")
def get_tables_in_db(postgresql_client):
    async def _get_tables_in_db() -> List[str]:
        result = await postgresql_client.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        return [r["table_name"] for r in result]

    return _get_tables_in_db


@pytest.fixture(scope="function")
def get_custom_postgresql_types(postgresql_client) -> Callable[[], Awaitable[List[str]]]:
    """
    Fixture that returns an async callable that returns all the custom types defined
    in the PostgreSQL database.
    """

    async def f() -> List[str]:
        return await db_util.postgres_get_custom_types(postgresql_client)

    return f


@pytest.fixture(scope="function")
def deactive_venv():
    old_os_path = os.environ.get("PATH", "")
    old_prefix = sys.prefix
    old_path = list(sys.path)
    old_meta_path = sys.meta_path.copy()
    old_path_hooks = sys.path_hooks.copy()
    old_pythonpath = os.environ.get("PYTHONPATH", None)
    old_os_venv: Optional[str] = os.environ.get("VIRTUAL_ENV", None)
    old_process_env: str = env.process_env.python_path
    old_working_set = pkg_resources.working_set
    old_available_extensions = (
        dict(InmantaBootloader.AVAILABLE_EXTENSIONS) if InmantaBootloader.AVAILABLE_EXTENSIONS is not None else None
    )

    yield

    os.environ["PATH"] = old_os_path
    sys.prefix = old_prefix
    sys.path = old_path
    # reset sys.meta_path because it might contain finders for editable installs, make sure to keep the same object
    sys.meta_path.clear()
    sys.meta_path.extend(old_meta_path)
    sys.path_hooks.clear()
    sys.path_hooks.extend(old_path_hooks)
    # Clear cache for sys.path_hooks
    sys.path_importer_cache.clear()
    pkg_resources.working_set = old_working_set
    # Restore PYTHONPATH
    if old_pythonpath is not None:
        os.environ["PYTHONPATH"] = old_pythonpath
    elif "PYTHONPATH" in os.environ:
        del os.environ["PYTHONPATH"]
    # Restore VIRTUAL_ENV
    if old_os_venv is not None:
        os.environ["VIRTUAL_ENV"] = old_os_venv
    elif "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]
    env.mock_process_env(python_path=old_process_env)
    loader.PluginModuleFinder.reset()
    InmantaBootloader.AVAILABLE_EXTENSIONS = old_available_extensions


def reset_metrics():
    pyformance.set_global_registry(MetricsRegistry())


@pytest.fixture(scope="function", autouse=True)
async def clean_reset(create_db, clean_db, deactive_venv):
    reset_all_objects()
    config.Config._reset()
    methods = inmanta.protocol.common.MethodProperties.methods.copy()
    loader.unload_inmanta_plugins()
    default_settings = dict(data.Environment._settings)
    yield
    inmanta.protocol.common.MethodProperties.methods = methods
    config.Config._reset()
    reset_all_objects()
    loader.unload_inmanta_plugins()
    cache_manager.detach_from_project()
    data.Environment._settings = default_settings


@pytest.fixture(scope="session", autouse=True)
def clean_reset_session():
    """
    Execute cleanup tasks that should only run at the end of the test suite.
    """
    yield
    IsolatedEnvBuilderCached.get_instance().destroy()


def reset_all_objects():
    resources.resource.reset()
    asyncio.set_child_watcher(None)
    reset_metrics()
    # No dynamic loading of commands at the moment, so no need to reset/reload
    # command.Commander.reset()
    handler.Commander.reset()
    Project._project = None
    unknown_parameters.clear()
    InmantaBootloader.AVAILABLE_EXTENSIONS = None
    V2ModuleBuilder.DISABLE_ISOLATED_ENV_BUILDER_CACHE = False
    compiler.Finalizers.reset_finalizers()


@pytest.fixture()
def disable_isolated_env_builder_cache() -> None:
    V2ModuleBuilder.DISABLE_ISOLATED_ENV_BUILDER_CACHE = True


@pytest.fixture(scope="function", autouse=True)
def restore_cwd():
    """
    Restore the current working directory after search test.
    """
    yield
    os.chdir(initial_cwd)


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
def inmanta_config() -> Iterator[ConfigParser]:
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
def server_pre_start(server_config):
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

    with tempfile.TemporaryDirectory() as state_dir:
        port = str(unused_tcp_port_factory())

        config.Config.set("database", "name", database_name)
        config.Config.set("database", "host", "localhost")
        config.Config.set("database", "port", str(postgres_db.port))
        config.Config.set("database", "username", postgres_db.user)
        config.Config.set("database", "password", postgres_db.password)
        config.Config.set("database", "connection_timeout", str(3))
        config.Config.set("config", "state-dir", state_dir)
        config.Config.set("config", "log-dir", os.path.join(state_dir, "logs"))
        config.Config.set("agent_rest_transport", "port", port)
        config.Config.set("compiler_rest_transport", "port", port)
        config.Config.set("client_rest_transport", "port", port)
        config.Config.set("cmdline_rest_transport", "port", port)
        config.Config.set("server", "bind-port", port)
        config.Config.set("server", "bind-address", "127.0.0.1")
        config.Config.set("server", "agent-process-purge-interval", "0")
        config.Config.set("config", "executable", os.path.abspath(inmanta.app.__file__))
        config.Config.set("server", "agent-timeout", "2")
        config.Config.set("agent", "agent-repair-interval", "0")
        yield config


@pytest.fixture(scope="function")
async def server(server_pre_start) -> abc.AsyncIterator[Server]:
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
        await ibl.stop(timeout=15)
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
    with tempfile.TemporaryDirectory() as state_dir:
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
        config.Config.set("database", "username", postgres_db.user)
        config.Config.set("database", "password", postgres_db.password)
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
            await ibl.stop(timeout=15)
        except concurrent.futures.TimeoutError:
            logger.exception("Timeout during stop of the server in teardown")


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
    # Ensure that the test suite uses the same config for warnings as the default config used by the CLI tools.
    logging.captureWarnings(True)
    cmd_parser = inmanta.app.cmd_parser()
    WarningsManager.apply_config({"default": cmd_parser.get_default("warnings")})
    yield
    warnings.resetwarnings()
    logging.captureWarnings(False)


@pytest.fixture
async def project_default(server, client) -> AsyncIterator[str]:
    """
    Fixture that creates a new inmanta project called env-test.
    """
    result = await client.create_project("env-test")
    assert result.code == 200
    yield result.result["project"]["id"]


@pytest.fixture
async def project_multi(server_multi, client_multi) -> AsyncIterator[str]:
    """
    Does the same as the project fixture, but this fixture should be used instead when the test case
    uses the server_multi or client_multi fixture.
    """
    result = await client_multi.create_project("env-test")
    assert result.code == 200
    yield result.result["project"]["id"]


@pytest.fixture
async def environment_creator() -> AsyncIterator[Callable[[protocol.Client, str, str, bool], Awaitable[str]]]:
    """
    Fixture to create a new environment in a certain project.
    """

    async def _create_environment(client, project_id: str, env_name: str, use_custom_env_settings: bool = True) -> str:
        """
        :param client: The client that should be used to create the project and environment.
        :param use_custom_env_settings: True iff the auto_deploy features is disabled and the
                                        agent trigger method is set to push_full_deploy.
        :return: The uuid of the newly created environment as a string.
        """
        result = await client.create_environment(project_id=project_id, name=env_name)
        env_id = result.result["environment"]["id"]

        cfg_env.set(env_id)

        if use_custom_env_settings:
            env_obj = await data.Environment.get_by_id(uuid.UUID(env_id))
            await env_obj.set(data.AUTO_DEPLOY, False)
            await env_obj.set(data.PUSH_ON_AUTO_DEPLOY, False)
            await env_obj.set(data.AGENT_TRIGGER_METHOD_ON_AUTO_DEPLOY, const.AgentTriggerMethod.push_full_deploy)
            await env_obj.set(data.RECOMPILE_BACKOFF, 0)

        return env_id

    yield _create_environment


@pytest.fixture(scope="function")
async def environment(
    server, client, project_default: str, environment_creator: Callable[[protocol.Client, str, str, bool], Awaitable[str]]
) -> AsyncIterator[str]:
    """
    Create a project and environment, with auto_deploy turned off and push_full_deploy set to push_full_deploy.
    This fixture returns the uuid of the environment.
    """
    yield await environment_creator(client, project_id=project_default, env_name="dev", use_custom_env_settings=True)


@pytest.fixture(scope="function")
async def environment_default(
    server, client, project_default: str, environment_creator: Callable[[protocol.Client, str, str, bool], Awaitable[str]]
) -> AsyncIterator[str]:
    """
    Create a project and environment with default environment settings.
    This fixture returns the uuid of the environment.
    """
    yield await environment_creator(client, project_id=project_default, env_name="dev", use_custom_env_settings=False)


@pytest.fixture(scope="function")
async def environment_multi(
    client_multi,
    server_multi,
    project_multi: str,
    environment_creator: Callable[[protocol.Client, str, str, bool], Awaitable[str]],
) -> AsyncIterator[str]:
    """
    Create a project and environment, with auto_deploy turned off and the agent trigger method set to push_full_deploy.
    This fixture returns the uuid of the environment.
    """
    yield await environment_creator(client_multi, project_id=project_multi, env_name="dev", use_custom_env_settings=True)


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


class ReentrantVirtualEnv(VirtualEnv):
    """
    A virtual env that can be de-activated and re-activated

    This allows faster reloading due to improved caching of the working set

    This is intended for use in testcases to require a lot of venv switching
    """

    def __init__(self, env_path: str) -> None:
        super(ReentrantVirtualEnv, self).__init__(env_path)
        self.working_set = None

    def deactivate(self):
        if self._using_venv:
            self._using_venv = False
            self.working_set = pkg_resources.working_set

    def use_virtual_env(self) -> None:
        """
        Activate the virtual environment.
        """
        if self._using_venv:
            # We are in use, just ignore double activation
            return

        if not self.working_set:
            # First run
            super().use_virtual_env()
        else:
            # Later run
            self._activate_that()
            mock_process_env(python_path=self.python_path)
            pkg_resources.working_set = self.working_set
            self._using_venv = True


class SnippetCompilationTest(KeepOnFail):
    def setUpClass(self):
        self.libs = tempfile.mkdtemp()
        self.repo = "https://github.com/inmanta/"
        self.env = tempfile.mkdtemp()
        self.venv = ReentrantVirtualEnv(env_path=self.env)
        config.Config.load_config()
        self.keep_shared = False
        self.project = None

    def tearDownClass(self):
        if not self.keep_shared:
            shutil.rmtree(self.libs)
            shutil.rmtree(self.env)

    def setup_func(self, module_dir: Optional[str]):
        # init project
        self._keep = False
        self.project_dir = tempfile.mkdtemp()
        self.modules_dir = module_dir

    def tear_down_func(self):
        loader.unload_modules_for_path(self.env)
        if not self._keep:
            shutil.rmtree(self.project_dir)
        self.project = None
        self.venv.deactivate()

    def keep(self):
        self._keep = True
        self.keep_shared = True
        return {"env": self.env, "libs": self.libs, "project": self.project_dir}

    def setup_for_snippet(
        self,
        snippet: str,
        *,
        autostd: bool = True,
        install_project: bool = True,
        install_v2_modules: Optional[List[LocalPackagePath]] = None,
        add_to_module_path: Optional[List[str]] = None,
        python_package_sources: Optional[List[str]] = None,
        project_requires: Optional[List[InmantaModuleRequirement]] = None,
        python_requires: Optional[List[Requirement]] = None,
        install_mode: Optional[InstallMode] = None,
        relation_precedence_rules: Optional[List[RelationPrecedenceRule]] = None,
        strict_deps_check: Optional[bool] = None,
    ) -> Project:
        """
        Sets up the project to compile a snippet of inmanta DSL. Activates the compiler environment (and patches
        env.process_env).

        :param install_project: Install the project and all its modules. This is required to be able to compile the model.
        :param install_v2_modules: Indicates which V2 modules should be installed in the compiler venv
        :param add_to_module_path: Additional directories that should be added to the module path.
        :param python_package_sources: The python package repository that should be configured on the Inmanta project in order
            to discover V2 modules.
        :param project_requires: The dependencies on other inmanta modules defined in the requires section of the project.yml
                                 file
        :param python_requires: The dependencies on Python packages providing v2 modules.
        :param install_mode: The install mode to configure in the project.yml file of the inmanta project. If None,
                             no install mode is set explicitly in the project.yml file.
        :param relation_precedence_policy: The relation precedence policy that should be stored in the project.yml file of the
                                           Inmanta project.
        :param strict_deps_check: True iff the returned project should have strict dependency checking enabled.
        """
        self.setup_for_snippet_external(
            snippet,
            add_to_module_path,
            python_package_sources,
            project_requires,
            python_requires,
            install_mode,
            relation_precedence_rules,
        )
        return self._load_project(autostd, install_project, install_v2_modules, strict_deps_check=strict_deps_check)

    def _load_project(
        self,
        autostd: bool,
        install_project: bool,
        install_v2_modules: Optional[List[LocalPackagePath]] = None,
        main_file: str = "main.cf",
        strict_deps_check: Optional[bool] = None,
    ):
        loader.PluginModuleFinder.reset()
        self.project = Project(
            self.project_dir, autostd=autostd, main_file=main_file, venv_path=self.venv, strict_deps_check=strict_deps_check
        )
        Project.set(self.project)
        self.project.use_virtual_env()
        self._patch_process_env()
        self._install_v2_modules(install_v2_modules)
        if install_project:
            self.project.install_modules()
        return self.project

    def _patch_process_env(self) -> None:
        """
        Patch env.process_env to accommodate the SnippetCompilationTest's switching between active environments within a single
        running process.
        """
        env.mock_process_env(env_path=self.env)

    def _install_v2_modules(self, install_v2_modules: Optional[List[LocalPackagePath]] = None) -> None:
        install_v2_modules = install_v2_modules if install_v2_modules is not None else []
        module_tool = ModuleTool()
        for mod in install_v2_modules:
            with tempfile.TemporaryDirectory() as build_dir:
                if mod.editable:
                    install_path = mod.path
                else:
                    install_path = module_tool.build(mod.path, build_dir)
                self.project.virtualenv.install_from_source(paths=[LocalPackagePath(path=install_path, editable=mod.editable)])

    def reset(self):
        Project.set(Project(self.project_dir, autostd=Project.get().autostd, venv_path=self.env))
        loader.unload_inmanta_plugins()
        loader.PluginModuleFinder.reset()

    def setup_for_snippet_external(
        self,
        snippet: str,
        add_to_module_path: Optional[List[str]] = None,
        python_package_sources: Optional[List[str]] = None,
        project_requires: Optional[List[InmantaModuleRequirement]] = None,
        python_requires: Optional[List[Requirement]] = None,
        install_mode: Optional[InstallMode] = None,
        relation_precedence_rules: Optional[List[RelationPrecedenceRule]] = None,
    ) -> None:
        add_to_module_path = add_to_module_path if add_to_module_path is not None else []
        python_package_sources = python_package_sources if python_package_sources is not None else []
        project_requires = project_requires if project_requires is not None else []
        python_requires = python_requires if python_requires is not None else []
        relation_precedence_rules = relation_precedence_rules if relation_precedence_rules else []
        with open(os.path.join(self.project_dir, "project.yml"), "w", encoding="utf-8") as cfg:
            cfg.write(
                f"""
            name: snippet test
            modulepath: {self._get_modulepath_for_project_yml_file(add_to_module_path)}
            downloadpath: {self.libs}
            version: 1.0
            repo:
                - {{type: git, url: {self.repo} }}
            """.rstrip()
            )
            if python_package_sources:
                cfg.write(
                    "".join(
                        f"""
                - {{type: package, url: {source} }}
                        """.rstrip()
                        for source in python_package_sources
                    )
                )
            if relation_precedence_rules:
                cfg.write("\n            relation_precedence_policy:\n")
                cfg.write("\n".join(f"                - {rule}" for rule in relation_precedence_rules))
            if project_requires:
                cfg.write("\n            requires:\n")
                cfg.write("\n".join(f"                - {req}" for req in project_requires))
            if install_mode:
                cfg.write(f"\n            install_mode: {install_mode.value}")
        with open(os.path.join(self.project_dir, "requirements.txt"), "w", encoding="utf-8") as fd:
            fd.write("\n".join(str(req) for req in python_requires))
        self.main = os.path.join(self.project_dir, "main.cf")
        with open(self.main, "w", encoding="utf-8") as x:
            x.write(snippet)

    def _get_modulepath_for_project_yml_file(self, add_to_module_path: List[str] = []) -> str:
        dirs = [self.libs]
        if self.modules_dir:
            dirs.append(self.modules_dir)
        if add_to_module_path:
            dirs.extend(add_to_module_path)
        return f"[{', '.join(dirs)}]"

    def do_export(
        self,
        include_status=False,
        do_raise=True,
        partial_compile: bool = False,
        resource_sets_to_remove: Optional[List[str]] = None,
    ) -> Union[tuple[int, ResourceDict], tuple[int, ResourceDict, dict[str, const.ResourceState]]]:
        return self._do_export(
            deploy=False,
            include_status=include_status,
            do_raise=do_raise,
            partial_compile=partial_compile,
            resource_sets_to_remove=resource_sets_to_remove,
        )

    def get_exported_json(self) -> JsonType:
        with open(os.path.join(self.project_dir, "dump.json")) as fh:
            return json.load(fh)

    def _do_export(
        self,
        deploy=False,
        include_status=False,
        do_raise=True,
        partial_compile: bool = False,
        resource_sets_to_remove: Optional[List[str]] = None,
    ) -> Union[tuple[int, ResourceDict], tuple[int, ResourceDict, dict[str, const.ResourceState]]]:
        """
        helper function to allow actual export to be run on a different thread
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

        return export.run(
            types,
            scopes,
            model_export=False,
            include_status=include_status,
            partial_compile=partial_compile,
            resource_sets_to_remove=resource_sets_to_remove,
        )

    async def do_export_and_deploy(
        self,
        include_status=False,
        do_raise=True,
        partial_compile: bool = False,
        resource_sets_to_remove: Optional[List[str]] = None,
    ) -> Union[tuple[int, ResourceDict], tuple[int, ResourceDict, dict[str, const.ResourceState], Optional[dict[str, object]]]]:
        return await off_main_thread(
            lambda: self._do_export(
                deploy=True,
                include_status=include_status,
                do_raise=do_raise,
                partial_compile=partial_compile,
                resource_sets_to_remove=resource_sets_to_remove,
            )
        )

    def setup_for_error(self, snippet, shouldbe, indent_offset=0):
        """
        Set up project to expect an error during compilation or project install.
        """
        try:
            self.setup_for_snippet(snippet)
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

    def setup_for_existing_project(self, folder: str, main_file: str = "main.cf") -> Project:
        shutil.rmtree(self.project_dir)
        shutil.copytree(folder, self.project_dir)
        venv = os.path.join(self.project_dir, ".env")
        if os.path.exists(venv):
            shutil.rmtree(venv)
        os.symlink(self.env, venv)
        return self._load_project(autostd=False, install_project=True, main_file=main_file)


@pytest.fixture(scope="session")
def snippetcompiler_global() -> Iterator[SnippetCompilationTest]:
    ast = SnippetCompilationTest()
    ast.setUpClass()
    yield ast
    ast.tearDownClass()


@pytest.fixture(scope="function")
def snippetcompiler(
    inmanta_config: ConfigParser, snippetcompiler_global: SnippetCompilationTest, modules_dir: str
) -> Iterator[SnippetCompilationTest]:
    """
    Yields a SnippetCompilationTest instance with shared libs directory and compiler venv.
    """
    snippetcompiler_global.setup_func(modules_dir)
    yield snippetcompiler_global
    snippetcompiler_global.tear_down_func()


@pytest.fixture(scope="function")
def snippetcompiler_clean(modules_dir: str) -> Iterator[SnippetCompilationTest]:
    """
    Yields a SnippetCompilationTest instance with its own libs directory and compiler venv.
    """
    ast = SnippetCompilationTest()
    ast.setUpClass()
    ast.setup_func(modules_dir)
    yield ast
    ast.tear_down_func()
    ast.tearDownClass()


@pytest.fixture(scope="session")
def modules_dir() -> str:
    yield os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "modules")


@pytest.fixture(scope="session")
def modules_v2_dir() -> str:
    yield os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "modules_v2")


@pytest.fixture(scope="session")
def projects_dir() -> str:
    yield os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


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
def cli(caplog):
    # caplog will break this code when emitting any log line to cli
    # due to mysterious interference when juggling with sys.stdout
    # https://github.com/pytest-dev/pytest/issues/10553
    with caplog.at_level(logging.FATAL):
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
        self._make_pull_fail = False
        self._runner_queue = runner_queue
        self.block = False

    async def run(self, force_update: Optional[bool] = False) -> Tuple[bool, None]:
        now = datetime.datetime.now()

        if self._runner_queue is not None:
            self._runner_queue.put(self)
            self.block = True
            while self.block:
                await asyncio.sleep(0.1)

        returncode = 1 if self._make_compile_fail else 0
        report = data.Report(
            compile=self.request.id, started=now, name="CompileRunnerMock", command="", completed=now, returncode=returncode
        )
        await report.insert()

        if self._make_pull_fail:
            report = data.Report(
                compile=self.request.id, started=now, name="Pulling updates", command="", completed=now, returncode=1
            )
            await report.insert()

        self.version = int(time.time())
        success = not self._make_compile_fail

        return success, None


def monkey_patch_compiler_service(monkeypatch, server, make_compile_fail, runner_queue: Optional[queue.Queue] = None):
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


@pytest.fixture
def tmpvenv(tmpdir: py.path.local) -> Iterator[Tuple[py.path.local, py.path.local]]:
    """
    Creates a venv with the latest pip in `${tmpdir}/.venv` where `${tmpdir}` is the directory returned by the `tmpdir`
    fixture. This venv is completely decoupled from the active development venv.

    :return: A tuple of the paths to the venv and the Python executable respectively.
    """
    venv_dir: py.path.local = tmpdir.join(".venv")
    python_path: py.path.local = venv_dir.join("bin", "python")
    venv.create(venv_dir, with_pip=True)
    subprocess.check_output([str(python_path), "-m", "pip", "install", "-U", "pip"])
    yield (venv_dir, python_path)


@pytest.fixture
def tmpvenv_active(
    deactive_venv, tmpvenv: Tuple[py.path.local, py.path.local]
) -> Iterator[Tuple[py.path.local, py.path.local]]:
    """
    Activates the venv created by the `tmpvenv` fixture within the currently running process. This venv is completely decoupled
    from the active development venv. As a result, any attempts to load new modules from the development venv will fail until
    cleanup. If using this fixture, it should always be listed before other fixtures that are expected to live in this
    environment context because its setup and teardown will then wrap the dependent setup and teardown. This works because
    pytest fixture setup and teardown use LIFO semantics
    (https://docs.pytest.org/en/6.2.x/fixture.html#yield-fixtures-recommended). The snippetcompiler fixture in particular should
    always come after this one.

    This fixture has a huge side effect that affects the running Python process. For a venv fixture that does not affect the
    running process, check out tmpvenv.

    :return: A tuple of the paths to the venv and the Python executable respectively.
    """
    venv_dir, python_path = tmpvenv

    # adapted from
    # https://github.com/pypa/virtualenv/blob/9569493453a39d63064ed7c20653987ba15c99e5/src/virtualenv/activation/python/activate_this.py
    # MIT license
    # Copyright (c) 2007 Ian Bicking and Contributors
    # Copyright (c) 2009 Ian Bicking, The Open Planning Project
    # Copyright (c) 2011-2016 The virtualenv developers
    # Copyright (c) 2020-202x The virtualenv developers
    binpath: str
    base: str
    site_packages: str
    if sys.platform == "win32":
        binpath = os.path.abspath(os.path.join(str(venv_dir), "Scripts"))
        base = os.path.dirname(binpath)
        site_packages = os.path.join(base, "Lib", "site-packages")
    else:
        binpath = os.path.abspath(os.path.join(str(venv_dir), "bin"))
        base = os.path.dirname(binpath)
        site_packages = os.path.join(
            base, "lib", "python%s" % ".".join(str(digit) for digit in sys.version_info[:2]), "site-packages"
        )

    # prepend bin to PATH (this file is inside the bin directory), exclude old venv path
    os.environ["PATH"] = os.pathsep.join(
        [binpath] + [elem for elem in os.environ.get("PATH", "").split(os.pathsep) if not elem.startswith(sys.prefix)]
    )
    os.environ["VIRTUAL_ENV"] = base  # virtual env is right above bin directory

    # add the virtual environments libraries to the host python import mechanism
    prev_length = len(sys.path)
    site.addsitedir(site_packages)
    # exclude old venv path
    sys.path[:] = sys.path[prev_length:] + [elem for elem in sys.path[0:prev_length] if not elem.startswith(sys.prefix)]

    sys.real_prefix = sys.prefix
    sys.prefix = base

    # patch env.process_env to recognize this environment as the active one, deactive_venv restores it
    env.mock_process_env(python_path=str(python_path))
    env.process_env.notify_change()

    # Force refresh build's decision on whether it should use virtualenv or venv. This decision is made based on the active
    # environment, which we're changing now.
    build.env._should_use_virtualenv.cache_clear()

    yield tmpvenv

    loader.unload_modules_for_path(site_packages)
    # Force refresh build's cache once more
    build.env._should_use_virtualenv.cache_clear()


@pytest.fixture
def tmpvenv_active_inherit(deactive_venv, tmpdir: py.path.local) -> Iterator[env.VirtualEnv]:
    """
    Creates and activates a venv similar to tmpvenv_active with the difference that this venv inherits from the previously
    active one.
    """
    venv_dir: py.path.local = tmpdir.join(".venv")
    venv: env.VirtualEnv = env.VirtualEnv(str(venv_dir))
    venv.use_virtual_env()
    yield venv
    loader.unload_modules_for_path(venv.site_packages_dir)


@pytest.fixture(scope="session")
def local_module_package_index(modules_v2_dir: str) -> Iterator[str]:
    """
    Creates a local pip index for all v2 modules in the modules v2 dir. The modules are built and published to the index.
    :return: The path to the index
    """
    cache_dir = os.path.abspath(os.path.join(os.path.dirname(modules_v2_dir), f"{os.path.basename(modules_v2_dir)}.cache"))
    build_dir = os.path.join(cache_dir, "build")
    index_dir = os.path.join(build_dir, "simple")
    timestamp_file = os.path.join(cache_dir, "cache_creation_timestamp")

    def _should_rebuild_cache() -> bool:
        if any(not os.path.exists(f) for f in [build_dir, index_dir, timestamp_file]):
            # Cache doesn't exist
            return True
        if len(os.listdir(index_dir)) != len(os.listdir(modules_v2_dir)) + 1:  # #modules + index.html
            # Modules were added/removed from the build_dir
            return True
        # Cache is dirty
        return any(
            os.path.getmtime(os.path.join(root, f)) > os.path.getmtime(timestamp_file)
            for root, _, files in os.walk(modules_v2_dir)
            for f in files
        )

    if _should_rebuild_cache():
        logger.info(f"Cache {cache_dir} is dirty. Rebuilding cache.")
        # Remove cache
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
        os.makedirs(build_dir)
        # Build modules
        for module_dir in os.listdir(modules_v2_dir):
            path: str = os.path.join(modules_v2_dir, module_dir)
            ModuleTool().build(path=path, output_dir=build_dir)
        # Build python package repository
        dir2pi(argv=["dir2pi", build_dir])
        # Update timestamp file
        open(timestamp_file, "w").close()
    else:
        logger.info(f"Using cache {cache_dir}")

    yield index_dir


@pytest.fixture
async def migrate_db_from(
    request: pytest.FixtureRequest, hard_clean_db, hard_clean_db_post, postgresql_client: asyncpg.Connection, server_pre_start
) -> AsyncIterator[Callable[[], Awaitable[None]]]:
    """
    Restores a db dump and yields a function that starts the server and migrates the database schema to the latest version.

    :param db_restore_dump: The db version dump file to restore (set via `@pytest.mark.db_restore_dump(<file>)`.
    """
    marker: Optional[pytest.mark.Mark] = request.node.get_closest_marker("db_restore_dump")
    if marker is None or len(marker.args) != 1:
        raise ValueError("Please set the db version to restore using `@pytest.mark.db_restore_dump(<file>)`")
    # restore old version
    with open(marker.args[0], "r") as fh:
        await PGRestore(fh.readlines(), postgresql_client).run()

    bootloader: InmantaBootloader = InmantaBootloader()

    async def migrate() -> None:
        # start boatloader, triggering db migration
        await bootloader.start()
        # inform asyncpg of any type changes so it knows to refresh its caches
        await postgresql_client.reload_schema_state()

    yield migrate

    await bootloader.stop(timeout=15)


@pytest.fixture(scope="session", autouse=not PYTEST_PLUGIN_MODE)
def guard_invariant_on_v2_modules_in_data_dir(modules_v2_dir: str) -> None:
    """
    When the test suite runs, the python environment used to build V2 modules is cached using the IsolatedEnvBuilderCached
    class. This cache relies on the fact that all modules in the tests/data/modules_v2 directory use the same build-backand
    and build requirements. This guard verifies whether that assumption is fulfilled and raises an exception if it's not.
    """
    for dir_name in os.listdir(modules_v2_dir):
        module_path = os.path.join(modules_v2_dir, dir_name)
        pyproject_toml_path = os.path.join(module_path, "pyproject.toml")
        error_message = f"""
Module {module_path} has a pyproject.toml file that is incompatible with the requirements of this test suite.
The build-backend and the build requirements should be set as follows:

[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"

All modules present in the tests/data/module_v2 directory should satisfy the above-mentioned requirements, because
the test suite caches the python environment used to build the V2 modules. This cache relies on the assumption that all modules
use the same build-backend and build requirements.
        """.strip()
        with open(pyproject_toml_path, "r", encoding="utf-8") as fh:
            pyproject_toml_as_dct = toml.load(fh)
            try:
                if pyproject_toml_as_dct["build-system"]["build-backend"] != "setuptools.build_meta" or set(
                    pyproject_toml_as_dct["build-system"]["requires"]
                ) != {"setuptools", "wheel"}:
                    raise Exception(error_message)
            except (KeyError, TypeError):
                raise Exception(error_message)


@pytest.fixture(scope="session", autouse=not PYTEST_PLUGIN_MODE)
def guard_testing_venv():
    """
    Ensure that the tests don't install packages into the venv that runs the tests.
    """
    venv = env.PythonEnvironment(python_path=sys.executable)
    installed_packages_before = venv.get_installed_packages()
    yield
    installed_packages_after = venv.get_installed_packages()

    venv_was_altered = False
    error_message = "The venv running the tests was altered by the tests:\n"
    all_pkgs = set(list(installed_packages_before.keys()) + list(installed_packages_after.keys()))
    for pkg in all_pkgs:
        version_before_tests = installed_packages_before.get(pkg)
        version_after_tests = installed_packages_after.get(pkg)
        if version_before_tests != version_after_tests:
            venv_was_altered = True
            error_message += f"\t* {pkg}: initial version={version_before_tests} --> after tests={version_after_tests}\n"
    assert not venv_was_altered, error_message


@pytest.fixture(scope="function", autouse=True)
async def set_running_tests():
    """
    Ensure the RUNNING_TESTS variable is True when running tests
    """
    inmanta.RUNNING_TESTS = True


@pytest.fixture(scope="session")
def index_with_pkgs_containing_optional_deps() -> str:
    """
    This fixture creates a python package repository containing packages with optional dependencies.
    These packages are NOT inmanta modules but regular python packages. This fixture returns the URL
    to the created python package repository.
    """
    with tempfile.TemporaryDirectory() as tmpdirname:
        pip_index = utils.PipIndex(artifact_dir=tmpdirname)
        utils.create_python_package(
            name="pkg",
            pkg_version=Version("1.0.0"),
            path=os.path.join(tmpdirname, "pkg"),
            publish_index=pip_index,
            optional_dependencies={
                "optional-a": [Requirement.parse("dep-a")],
                "optional-b": [Requirement.parse("dep-b"), Requirement.parse("dep-c")],
            },
        )
        for pkg_name in ["dep-a", "dep-b", "dep-c"]:
            utils.create_python_package(
                name=pkg_name,
                pkg_version=Version("1.0.0"),
                path=os.path.join(tmpdirname, pkg_name),
                publish_index=pip_index,
            )
        yield pip_index.url
