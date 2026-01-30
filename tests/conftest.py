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

import copy
import logging.config
import pathlib
import warnings
from concurrent.futures.thread import ThreadPoolExecutor
from glob import glob
from re import Pattern
from threading import Condition

from tornado.httpclient import AsyncHTTPClient

import _pytest.logging
import inmanta.deploy.state
import toml
from inmanta import logging as inmanta_logging
from inmanta.agent.executor import Executor, ExecutorManager
from inmanta.agent.handler import CRUDHandler, HandlerContext, ResourceHandler, SkipResource, TResource, provider
from inmanta.agent.write_barier_executor import WriteBarierExecutorManager
from inmanta.config import log_dir
from inmanta.data.model import EnvSettingType
from inmanta.db.util import PGRestore
from inmanta.logging import InmantaLoggerConfig
from inmanta.protocol import auth
from inmanta.references import mutator, reference
from inmanta.resources import PurgeableResource, Resource, resource
from inmanta.util import ScheduledTask, Scheduler, TaskMethod, TaskSchedule
from packaging.requirements import Requirement

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

"""
About the fixtures that control the behavior related to the scheduler:

* Default behavior: We expect the test case to not (auto)start a scheduler. Any attempt to autostart the scheduler
                    will result in an AssertionError.
* `auto_start_agent` fixture: Indicates we expect scheduler to be autostart.
                    => Usage: Add the `@pytest.mark.parametrize("auto_start_agent", [True])` annotation on the test case.
* `null_agent` fixture: Create an agent that doesn't do anything. The test case just expects the agent to exists and be up.
                    => Usage: Regular fixture instantiation.
* `agent` fixture: Create an full in-process agent that fully works.
                    => Usage: Regular fixture instantiation
* `no_agent` fixture: Disables the scheduler autostart functionality, any attempt to start the scheduler is ignored.
                    => Usage: Add the `@pytest.mark.parametrize("no_agent", [True])` annotation on the test case.
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
import weakref
from collections import abc, defaultdict, namedtuple
from collections.abc import AsyncIterator, Awaitable, Iterator
from configparser import ConfigParser
from typing import Any, Callable, Dict, Generic, Optional, Union

import asyncpg
import psutil
import py
import pytest
from asyncpg.exceptions import DuplicateDatabaseError
from click import testing
from tornado import netutil

import inmanta
import inmanta.agent
import inmanta.app
import inmanta.compiler as compiler
import inmanta.compiler.config
import inmanta.main
import inmanta.server.agentmanager as agentmanager
import inmanta.user_setup
from inmanta import config, const, data, env, loader, protocol, resources
from inmanta.agent import handler
from inmanta.agent.agent_new import Agent
from inmanta.agent.in_process_executor import InProcessExecutorManager
from inmanta.ast import CompilerException
from inmanta.data.schema import SCHEMA_VERSION_TABLE
from inmanta.db import util as db_util
from inmanta.env import ActiveEnv, CommandRunner, LocalPackagePath, VirtualEnv, process_env, store_venv, swap_process_env
from inmanta.export import ResourceDict, cfg_env, unknown_parameters
from inmanta.module import InmantaModuleRequirement, InstallMode, Project, RelationPrecedenceRule
from inmanta.moduletool import DefaultIsolatedEnvCached, ModuleTool, V2ModuleBuilder
from inmanta.parser.plyInmantaParser import cache_manager
from inmanta.protocol import VersionMatch
from inmanta.server import SLICE_AGENT_MANAGER, SLICE_COMPILER
from inmanta.server.bootloader import InmantaBootloader
from inmanta.server.protocol import Server, SliceStartupException
from inmanta.server.services import orchestrationservice
from inmanta.server.services.compilerservice import CompilerService, CompileRun
from inmanta.types import JsonType, ResourceIdStr
from inmanta.vendor import pyformance
from inmanta.vendor.pyformance import MetricsRegistry
from inmanta.warnings import WarningsManager
from libpip2pi.commands import dir2pi
from packaging.version import Version
from pytest_postgresql import factories

# Import test modules differently when conftest is put into the inmanta_tests packages
PYTEST_PLUGIN_MODE: bool = __file__ and os.path.dirname(__file__).split("/")[-1] == "inmanta_tests"
if PYTEST_PLUGIN_MODE:
    from inmanta_tests import utils  # noqa: F401
else:
    import utils

logger = logging.getLogger(__name__)

TABLES_TO_KEEP = [x.table_name() for x in data._classes] + [
    "resourceaction_resource",
]  # Join table

# Save the cwd as early as possible to prevent that it gets overridden by another fixture
# before it's saved.
initial_cwd = os.getcwd()

pg_logfile = os.path.join(initial_cwd, "pg.log")


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


# adds a custom log location for postgres
postgresql_proc_with_log = factories.postgresql_proc(startparams=f"--log='{pg_logfile}'")


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
        fixture = "postgresql_proc_with_log"

    logger.info("Using database fixture %s", fixture)
    pg = request.getfixturevalue(fixture)
    yield pg

    if os.path.exists(pg_logfile):
        has_deadlock = False
        with open(pg_logfile) as fh:
            for line in fh:
                if "deadlock" in line:
                    has_deadlock = True
                    break
            sublogger = logging.getLogger("pytest.postgresql.deadlock")
            for line in fh:
                sublogger.warning("%s", line)
        os.remove(pg_logfile)
        assert not has_deadlock


@pytest.fixture
async def run_without_keeping_psql_logs(postgres_db):
    if os.path.exists(pg_logfile):
        # Store the original content of the logfile
        with open(pg_logfile) as file:
            original_content = file.read()
    yield

    if os.path.exists(pg_logfile):
        # Restore the original content of the logfile
        with open(pg_logfile, "w") as file:
            file.write(original_content)


@pytest.fixture
async def postgres_db_debug(postgres_db, database_name) -> abc.AsyncIterator[None]:
    """
    Fixture meant for debugging through manual interaction with the database. Run pytest with `-s/--capture=no`.
    """
    yield
    print(
        "Connection to DB will be kept alive for one hour. Connect with"
        f" `psql --host {postgres_db.host} --port {postgres_db.port} {database_name} {postgres_db.user}`"
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
    async def _get_columns_in_db_table(table_name: str) -> list[str]:
        result = await postgresql_client.fetch(
            "SELECT column_name "
            "FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='" + table_name + "'"
        )
        return [r["column_name"] for r in result]

    return _get_columns_in_db_table


@pytest.fixture(scope="function")
def get_primary_key_columns_in_db_table(postgresql_client):
    async def _get_primary_key_columns_in_db_table(table_name: str) -> list[str]:
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
    async def _get_tables_in_db() -> list[str]:
        result = await postgresql_client.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        return [r["table_name"] for r in result]

    return _get_tables_in_db


@pytest.fixture(scope="function")
def get_custom_postgresql_types(postgresql_client) -> Callable[[], Awaitable[list[str]]]:
    """
    Fixture that returns an async callable that returns all the custom types defined
    in the PostgreSQL database.
    """

    async def f() -> list[str]:
        return await db_util.postgres_get_custom_types(postgresql_client)

    return f


@pytest.fixture(scope="function")
def get_type_of_column(postgresql_client) -> Callable[[], Awaitable[Optional[str]]]:
    """
    Fixture that returns the type of a column in a table
    """

    async def _get_type_of_column(table_name: str, column_name: str) -> Optional[str]:
        data_type = await postgresql_client.fetchval(
            """
                SELECT data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                    AND table_name = $1
                    AND column_name = $2;
            """,
            table_name,
            column_name,
        )
        return data_type

    return _get_type_of_column


@pytest.fixture(scope="function")
def deactive_venv() -> ActiveEnv:
    snapshot = env.store_venv()
    old_available_extensions = (
        dict(InmantaBootloader.AVAILABLE_EXTENSIONS) if InmantaBootloader.AVAILABLE_EXTENSIONS is not None else None
    )
    yield process_env
    snapshot.restore()
    loader.PluginModuleFinder.reset()
    InmantaBootloader.AVAILABLE_EXTENSIONS = old_available_extensions


def reset_metrics():
    pyformance.set_global_registry(MetricsRegistry())


@pytest.fixture(scope="function")
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
    DefaultIsolatedEnvCached.get_instance().destroy()


def reset_all_objects():
    resources.resource.reset()
    reset_metrics()
    # No dynamic loading of commands at the moment, so no need to reset/reload
    # command.Commander.reset()
    handler.Commander.reset()
    Project._project = None
    unknown_parameters.clear()
    InmantaBootloader.AVAILABLE_EXTENSIONS = None
    V2ModuleBuilder.DISABLE_DEFAULT_ISOLATED_ENV_CACHED = False
    compiler.Finalizers.reset_finalizers()
    auth.AuthJWTConfig.reset()
    InmantaLoggerConfig.clean_instance()
    AsyncHTTPClient.configure(None)
    reference.reset()
    mutator.reset()


@pytest.fixture()
def disable_isolated_env_builder_cache() -> None:
    V2ModuleBuilder.DISABLE_DEFAULT_ISOLATED_ENV_CACHED = True


@pytest.fixture(scope="function", autouse=True)
def restore_cwd():
    """
    Restore the current working directory after each test.
    """
    yield
    os.chdir(initial_cwd)


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
def inmanta_config(clean_reset) -> Iterator[ConfigParser]:
    config.Config.load_config()
    config.Config.set("auth_jwt_default", "algorithm", "HS256")
    config.Config.set("auth_jwt_default", "sign", "true")
    config.Config.set("auth_jwt_default", "client_types", "agent,compiler,api")
    config.Config.set("auth_jwt_default", "key", "rID3kG4OwGpajIsxnGDhat4UFcMkyFZQc1y3oKQTPRs")
    config.Config.set("auth_jwt_default", "expire", "0")
    config.Config.set("auth_jwt_default", "issuer", "https://localhost:8888/")
    config.Config.set("auth_jwt_default", "audience", "https://localhost:8888/")

    yield config.Config.get_instance()


@pytest.fixture
def server_pre_start(server_config):
    """This fixture is called by the server. Override this fixture to influence server config"""


@pytest.fixture
def disable_background_jobs(monkeypatch):
    """
    This fixture disables the scheduling of all background jobs.
    """

    class NoopScheduler(Scheduler):
        def add_action(
            self,
            action: TaskMethod,
            schedule: Union[TaskSchedule, int],
            cancel_on_stop: bool = True,
            quiet_mode: bool = False,
        ) -> Optional[ScheduledTask]:
            pass

    monkeypatch.setattr(inmanta.server.protocol, "Scheduler", NoopScheduler)

    yield None


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
async def server_config(
    inmanta_config, postgres_db, database_name, clean_reset, unused_tcp_port_factory, auto_start_agent, no_agent
):
    reset_metrics()
    agentmanager.assert_no_start_scheduler = not auto_start_agent
    agentmanager.no_start_scheduler = no_agent

    with tempfile.TemporaryDirectory() as state_dir:
        port = str(unused_tcp_port_factory())

        # Config.set() always expects a string value
        pg_password = "" if postgres_db.password is None else postgres_db.password

        config.Config.set("database", "name", database_name)
        config.Config.set("database", "host", postgres_db.host)
        config.Config.set("database", "port", str(postgres_db.port))
        config.Config.set("database", "username", postgres_db.user)
        config.Config.set("database", "password", pg_password)
        config.Config.set("database", "db_connection_timeout", str(3))
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
        config.Config.set("agent", "executor-mode", "forking")
        config.Config.set("agent", "executor-venv-retention-time", "60")
        config.Config.set("agent", "executor-retention-time", "10")
        yield config
    agentmanager.assert_no_start_scheduler = False
    agentmanager.no_start_scheduler = False


@pytest.fixture(scope="function")
async def server(server_pre_start, request, auto_start_agent) -> abc.AsyncIterator[Server]:
    # fix for fact that pytest_tornado never set IOLoop._instance, the IOLoop of the main thread
    # causes handler failure
    tests_failed_before = request.session.testsfailed
    ibl = InmantaBootloader(configure_logging=True)

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
        # This timeout needs to be bigger than the timeout of other components. Otherwise, this would leak sessions and cause
        # problems in other tests
        await ibl.stop(timeout=20)
    except concurrent.futures.TimeoutError:
        logger.exception("Timeout during stop of the server in teardown")
    logger.info("Server clean up done")
    tests_failed_during = request.session.testsfailed - tests_failed_before
    if tests_failed_during and auto_start_agent:
        for file in glob(log_dir.get() + "/*"):
            if not os.path.isdir(file):
                with open(file, "r") as fh:
                    logger.debug("%s\n%s", file, fh.read())


@pytest.fixture(
    scope="function",
    params=[(True, True, False), (True, False, False), (False, True, False), (False, False, False), (True, True, True)],
    ids=["SSL and Auth", "SSL", "Auth", "Normal", "SSL and Auth with not self signed certificate"],
)
async def server_multi(
    server_pre_start, inmanta_config, postgres_db, database_name, request, clean_reset, unused_tcp_port_factory
):
    with tempfile.TemporaryDirectory() as state_dir:
        ssl, auth, ca = request.param

        utils.configure_auth(auth, ca, ssl)

        # Config.set() always expects a string value
        pg_password = "" if postgres_db.password is None else postgres_db.password

        port = str(unused_tcp_port_factory())
        config.Config.set("database", "name", database_name)
        config.Config.set("database", "host", postgres_db.host)
        config.Config.set("database", "port", str(postgres_db.port))
        config.Config.set("database", "username", postgres_db.user)
        config.Config.set("database", "password", pg_password)
        config.Config.set("database", "db_connection_timeout", str(3))
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
        config.Config.set("agent", "executor-mode", "forking")
        config.Config.set("agent", "executor-venv-retention-time", "60")
        config.Config.set("agent", "executor-retention-time", "10")

        ibl = InmantaBootloader(configure_logging=True)

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
            await ibl.stop(timeout=20)
        except concurrent.futures.TimeoutError:
            logger.exception("Timeout during stop of the server in teardown")


@pytest.fixture(scope="function")
async def auto_start_agent() -> bool:
    """Marker fixture, indicates if we expect scheduler autostart.
    If set to False, any attempt to start the scheduler results in failure"""
    return False


@pytest.fixture(scope="function")
async def no_agent() -> bool:
    """Marker fixture, disables scheduler autostart, any attempt to start the scheduler is ignored"""
    return False


@pytest.fixture(scope="function")
async def clienthelper(client, environment):
    return utils.ClientHelper(client, environment)


DISABLE_STATE_CHECK = False


@pytest.fixture(scope="function")
def executor_factory():

    def default_executor(
        environment: uuid.UUID,
        client: inmanta.protocol.SessionClient,
        eventloop: asyncio.AbstractEventLoop,
        parent_logger: logging.Logger,
        thread_pool: ThreadPoolExecutor,
        code_dir: str,
        env_dir: str,
    ):
        executor: ExecutorManager[Executor] = InProcessExecutorManager(
            environment,
            client,
            eventloop,
            parent_logger,
            thread_pool,
            code_dir,
            env_dir,
            False,
        )

        executor = WriteBarierExecutorManager(executor)
        return executor

    return default_executor


@pytest.fixture(scope="function")
async def agent_factory(
    server, client, monkeypatch, executor_factory
) -> AsyncIterator[Callable[[uuid.UUID], Awaitable[Agent]]]:
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)
    agents: list[Agent] = []

    async def create(environment: uuid.UUID) -> Agent:
        # Mock scheduler state-dir: outside of tests this happens
        # when the scheduler config is loaded, before starting the scheduler
        server_state_dir = config.Config.get("config", "state-dir")
        scheduler_state_dir = pathlib.Path(server_state_dir) / "server" / str(environment)
        scheduler_state_dir.mkdir(exist_ok=True)
        config.Config.set("config", "state-dir", str(scheduler_state_dir))
        a = Agent(environment)
        agents.append(a)
        # Restore state-dir
        config.Config.set("config", "state-dir", str(server_state_dir))

        executor = executor_factory(
            environment,
            a._client,
            asyncio.get_running_loop(),
            logger,
            a.thread_pool,
            str(pathlib.Path(a._storage["executors"]) / "code"),
            str(pathlib.Path(a._storage["executors"]) / "venvs"),
        )
        a.executor_manager = executor
        a.scheduler.executor_manager = executor
        a.scheduler.code_manager = utils.DummyCodeManager(a._client)
        await a.start()
        await utils.retry_limited(
            lambda: agentmanager.get_agent_client(tid=environment, endpoint=const.AGENT_SCHEDULER_ID, live_agent_only=True)
            is not None,
            timeout=10,
        )
        return a

    yield create

    global DISABLE_STATE_CHECK
    try:
        if not DISABLE_STATE_CHECK:
            all_environments = {agent.environment for agent in agents}
            for environment in all_environments:
                # Make sure that the scheduler doesn't deploy anything anymore, because this would alter
                # the last_deploy timestamp in the resource_state.
                await client.all_agents_action(tid=environment, action=const.AgentAction.pause.value).value()
                # Set data.RESET_DEPLOY_PROGRESS_ON_START back to False in all of the environments of the created agents
                # Because this teardown asserts that the state is correct on restart and this setting breaks that assertion
                result = await client.set_setting(environment, data.RESET_DEPLOY_PROGRESS_ON_START, False)
                assert result.code == 200, result.result
            for agent in agents:
                await agent.stop_working()
                the_state = copy.deepcopy(dict(agent.scheduler._state.resource_state))
                for r, state in the_state.items():
                    if state.blocked is inmanta.deploy.state.Blocked.TEMPORARILY_BLOCKED:
                        # TODO[#8541]: also persist TEMPORARILY_BLOCKED in database
                        state.blocked = inmanta.deploy.state.Blocked.NOT_BLOCKED
                    print(r, state)
                monkeypatch.setattr(agent.scheduler._work.agent_queues, "_new_agent_notify", lambda x: x)
                await agent.start_working()
                new_state = copy.deepcopy(dict(agent.scheduler._state.resource_state))
                assert the_state == new_state

        await asyncio.gather(*[agent.stop() for agent in agents])
    finally:
        DISABLE_STATE_CHECK = False


@pytest.fixture(scope="function")
async def agent(
    server, environment, agent_factory: Callable[[uuid.UUID], Awaitable[Agent]], monkeypatch
) -> AsyncIterator[Agent]:
    """Construct an agent that can execute using the resource container"""
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    a: Agent = await agent_factory(uuid.UUID(environment))
    await utils.retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    yield a


@pytest.fixture(scope="function")
async def agent_factory_no_state_check(
    agent_factory: Callable[[uuid.UUID], Awaitable[Agent]],
) -> Callable[[uuid.UUID], Awaitable[Agent]]:
    global DISABLE_STATE_CHECK
    DISABLE_STATE_CHECK = True
    yield agent_factory


@pytest.fixture(scope="function")
async def agent_no_state_check(
    server, environment, agent_factory_no_state_check: Callable[[uuid.UUID], Awaitable[Agent]], monkeypatch
):
    """Construct an agent that can execute using the resource container"""
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    a: Agent = await agent_factory_no_state_check(uuid.UUID(environment))
    await utils.retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    yield a


@pytest.fixture(scope="function")
async def null_agent(server, environment):
    """Construct an agent that does nothing"""
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    a = utils.NullAgent(environment)

    await a.start()

    await utils.retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    yield a

    await a.stop()


@pytest.fixture(scope="function")
async def null_agent_multi(server_multi, environment_multi):
    """Construct an agent that does nothing"""
    agentmanager = server_multi.get_slice(SLICE_AGENT_MANAGER)

    a = utils.NullAgent(environment_multi)

    await a.start()

    await utils.retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    yield a

    await a.stop()


@pytest.fixture(scope="function")
async def agent_multi(server_multi, environment_multi):
    """Construct an agent that can execute using the resource container"""
    server = server_multi
    environment = environment_multi
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    a = Agent(environment)

    executor = InProcessExecutorManager(
        environment,
        a._client,
        asyncio.get_event_loop(),
        logger,
        a.thread_pool,
        str(pathlib.Path(a._storage["executors"]) / "code"),
        str(pathlib.Path(a._storage["executors"]) / "venvs"),
        False,
    )
    executor = WriteBarierExecutorManager(executor)
    a.executor_manager = executor
    a.scheduler.executor_manager = executor
    a.scheduler.code_manager = utils.DummyCodeManager(a._client)

    await a.start()

    await utils.retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    yield a

    await a.stop()


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


class KeepOnFail:
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
            rep.sections.append(("Resources Kept", "\n".join([f"{label} {resource}" for label, resource in resources.items()])))


class ReentrantVirtualEnv(VirtualEnv):
    """
    A virtual env that can be de-activated and re-activated

    This allows faster reloading due to improved caching of the working set

    This is intended for use in testcases to require a lot of venv switching
    """

    def __init__(self, env_path: str, re_check: bool = False):
        """
        :param re_check: For performance reasons, we don't check all constraints every time,
            setting re_check makes it check every time
        """
        super().__init__(env_path)
        self.was_checked = False
        self.re_check = re_check
        # The venv we replaced when getting activated
        self.previous_venv = None
        self.snapshot = None

    def deactivate(self):
        if self._using_venv:
            self._using_venv = False
            if self.snapshot:
                self.snapshot.restore()
                self.snapshot = None
                swap_process_env(self.previous_venv)

    def fake_use(self) -> None:
        self._using_venv = True

    def use_virtual_env(self) -> None:
        """
        Activate the virtual environment.
        """
        if self._using_venv:
            # We are in use, just ignore double activation
            return

        self.init_env()
        self._using_venv = True
        self.snapshot = store_venv()
        self.previous_venv = swap_process_env(self)
        self._activate_that()

    def check(
        self,
        strict_scope: Optional[Pattern[str]] = None,
        constraints: Optional[list[Requirement]] = None,
    ) -> None:
        # Avoid re-checking
        if not self.was_checked or self.re_check:
            super().check(strict_scope, constraints)
            self.was_checked = True


class SnippetCompilationTest(KeepOnFail):
    def setUpClass(self, re_check_venv: bool = False):
        """
        :param re_check_venv: For performance reasons, we don't check all constraints every time,
            setting re_check_venv makes it check every time
        """
        self.libs = tempfile.mkdtemp()
        self.repo: str = "https://github.com/inmanta/"
        self.env = tempfile.mkdtemp()
        self.venv = ReentrantVirtualEnv(env_path=self.env, re_check=re_check_venv)
        self.re_check_venv = re_check_venv
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
        sys.path_importer_cache.clear()
        loader.PluginModuleFinder.reset()

    def keep(self):
        self._keep = True
        self.keep_shared = True
        return {"env": self.env, "libs": self.libs, "project": self.project_dir}

    def setup_for_snippet(
        self,
        snippet: str,
        *,
        autostd: bool = False,
        ministd: bool = False,
        install_project: bool = True,
        install_v2_modules: Optional[list[LocalPackagePath]] = None,
        add_to_module_path: Optional[list[str]] = None,
        python_package_sources: Optional[list[str]] = None,
        project_requires: Optional[list[InmantaModuleRequirement]] = None,
        python_requires: Optional[list[Requirement]] = None,
        install_mode: Optional[InstallMode] = None,
        relation_precedence_rules: Optional[list[RelationPrecedenceRule]] = None,
        use_pip_config_file: bool = False,
        index_url: Optional[str] = None,
        extra_index_url: list[str] = [],
        main_file: str = "main.cf",
        pre: bool | None = None,
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
        :param use_pip_config_file: True iff the pip config file should be used and no source is required for v2 to work
                                    False if a package source is needed for v2 modules to work
        :param main_file: Path to the .cf file to use as main entry point. A relative or an absolute path can be provided.
            If a relative path is used, it's interpreted relative to the root of the project directory.
        :param autostd: do we automatically import std? This does have a performance impact!
            it is small on individual test cases, (100 ms) but it adds up quickly (as this is 50% of the run time)
        :param ministd: if we need some of std, but not everything, this loads a small, embedded version of std, that has less
            overhead
        """
        self.setup_for_snippet_external(
            snippet,
            add_to_module_path,
            python_package_sources,
            project_requires,
            python_requires,
            install_mode,
            relation_precedence_rules,
            use_pip_config_file,
            index_url,
            extra_index_url,
            main_file,
            pre=pre,
        )

        dirty_venv = autostd or install_project or install_v2_modules or self.re_check_venv or python_requires

        return self._load_project(
            autostd or ministd,
            install_project,
            install_v2_modules,
            main_file=main_file,
            dirty_venv=dirty_venv,
        )

    def _load_project(
        self,
        autostd: bool,
        install_project: bool,
        install_v2_modules: Optional[list[LocalPackagePath]] = None,
        main_file: str = "main.cf",
        dirty_venv: bool = True,
    ):
        loader.PluginModuleFinder.reset()
        self.project = Project(self.project_dir, autostd=autostd, main_file=main_file, venv_path=self.venv)
        Project.set(self.project)

        if dirty_venv:
            # Don't bother loading the venv if we don't need to
            self.project.use_virtual_env()
            self._install_v2_modules(install_v2_modules)
            if install_project:
                self.project.install_modules()
        else:
            self.venv.fake_use()
        return self.project

    def _install_v2_modules(self, install_v2_modules: Optional[list[LocalPackagePath]] = None) -> None:
        """Assumes we have a project set"""
        install_v2_modules = install_v2_modules if install_v2_modules is not None else []
        module_tool = ModuleTool()
        for mod in install_v2_modules:
            with tempfile.TemporaryDirectory() as build_dir:
                if mod.editable:
                    install_path = mod.path
                else:
                    install_path = module_tool.build(mod.path, build_dir, wheel=True)[0]
                self.project.virtualenv.install_for_config(
                    requirements=[],
                    paths=[LocalPackagePath(path=install_path, editable=mod.editable)],
                    config=self.project.metadata.pip,
                )

    def reset(self):
        Project.set(Project(self.project_dir, autostd=Project.get().autostd, venv_path=self.env))
        loader.unload_inmanta_plugins()
        loader.PluginModuleFinder.reset()

    def setup_for_snippet_external(
        self,
        snippet: str,
        add_to_module_path: Optional[list[str]] = None,
        python_package_sources: Optional[list[str]] = None,
        project_requires: Optional[list[InmantaModuleRequirement]] = None,
        python_requires: Optional[list[Requirement]] = None,
        install_mode: Optional[InstallMode] = None,
        relation_precedence_rules: Optional[list[RelationPrecedenceRule]] = None,
        use_pip_config_file: bool = False,
        index_url: Optional[str] = None,
        extra_index_url: list[str] = [],
        main_file: str = "main.cf",
        ministd: bool = False,
        environment_settings: dict[str, EnvSettingType] | None = None,
        pre: bool | None = None,
    ) -> None:
        add_to_module_path = add_to_module_path if add_to_module_path is not None else []
        python_package_sources = python_package_sources if python_package_sources is not None else []

        project_requires = project_requires if project_requires is not None else []
        python_requires = python_requires if python_requires is not None else []
        relation_precedence_rules = relation_precedence_rules if relation_precedence_rules else []
        ministd_path = os.path.join(__file__, "..", "data/mini_std_container")
        if ministd:
            add_to_module_path += ministd_path
        with open(os.path.join(self.project_dir, "project.yml"), "w", encoding="utf-8") as cfg:
            cfg.write(f"""
            name: snippet test
            modulepath: {self._get_modulepath_for_project_yml_file(add_to_module_path)}
            downloadpath: {self.libs}
            version: 1.0
            repo:
                - {{type: git, url: {self.repo} }}
            """.rstrip())

            if relation_precedence_rules:
                cfg.write("\n            relation_precedence_policy:\n")
                cfg.write("\n".join(f"                - {rule}" for rule in relation_precedence_rules))
            if project_requires:
                cfg.write("\n            requires:\n")
                cfg.write("\n".join(f"                - {req}" for req in project_requires))
            if install_mode:
                cfg.write(f"\n            install_mode: {install_mode.value}")

            cfg.write(f"""
            pip:
                use_system_config: {use_pip_config_file}
""")
            if index_url:
                cfg.write(f"""                index_url: {index_url}
""")
            if extra_index_url:
                cfg.write(f"""                extra_index_url: [{", ".join(url for url in extra_index_url)}]
""")
            if pre is not None:
                cfg.write(f"""                pre: {str(pre).lower()}
""")
            if environment_settings:
                cfg.write("\n            environment_settings:\n")
                cfg.write("\n".join(f"                {name}: {value}" for name, value in environment_settings.items()))
        with open(os.path.join(self.project_dir, "requirements.txt"), "w", encoding="utf-8") as fd:
            fd.write("\n".join(str(req) for req in python_requires))
        self.main = os.path.join(self.project_dir, main_file)
        with open(self.main, "w", encoding="utf-8") as x:
            x.write(snippet)

    def _get_modulepath_for_project_yml_file(self, add_to_module_path: list[str] = []) -> str:
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
        resource_sets_to_remove: Optional[list[str]] = None,
        soft_delete=False,
    ) -> Union[tuple[int, ResourceDict], tuple[int, ResourceDict, dict[str, const.ResourceState]]]:
        return self._do_export(
            deploy=False,
            include_status=include_status,
            do_raise=do_raise,
            partial_compile=partial_compile,
            resource_sets_to_remove=resource_sets_to_remove,
            soft_delete=soft_delete,
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
        resource_sets_to_remove: Optional[list[str]] = None,
        soft_delete=False,
    ) -> Union[tuple[int, ResourceDict], tuple[int, ResourceDict, dict[str, const.ResourceState]]]:
        """
        helper function to allow actual export to be run on a different thread
        i.e. export.run must run off main thread to allow it to start a new ioloop for run_sync
        """

        class Options:
            pass

        options = Options()
        options.json = os.path.join(self.project_dir, "dump.json") if not deploy else None
        options.depgraph = False
        options.deploy = deploy
        options.ssl = False
        options.soft_delete = soft_delete

        from inmanta.export import Exporter  # noqa: H307

        try:
            types, scopes = compiler.do_compile()
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
            export_env_var_settings=deploy,
        )

    async def do_export_and_deploy(
        self,
        include_status=False,
        do_raise=True,
        partial_compile: bool = False,
        resource_sets_to_remove: Optional[list[str]] = None,
        soft_delete: bool = False,
    ) -> Union[tuple[int, ResourceDict], tuple[int, ResourceDict, dict[str, const.ResourceState], Optional[dict[str, object]]]]:
        """Export to an actual server"""
        return await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: self._do_export(
                deploy=True,
                include_status=include_status,
                do_raise=do_raise,
                partial_compile=partial_compile,
                resource_sets_to_remove=resource_sets_to_remove,
                soft_delete=soft_delete,
            ),
        )

    def setup_for_error(
        self,
        snippet,
        shouldbe,
        indent_offset=0,
        ministd: bool = False,
        autostd: bool = False,
    ):
        """
        Set up project to expect an error during compilation or project install.
        """
        try:
            self.setup_for_snippet(snippet, ministd=ministd, autostd=autostd)
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

    def create_module(self, name: str, initcf: str = "", initpy: str = "") -> None:
        module_dir = os.path.join(self.libs, name)
        os.mkdir(module_dir)
        os.mkdir(os.path.join(module_dir, "model"))
        os.mkdir(os.path.join(module_dir, "files"))
        os.mkdir(os.path.join(module_dir, "templates"))
        os.mkdir(os.path.join(module_dir, "plugins"))

        with open(os.path.join(module_dir, "model", "_init.cf"), "w+") as fd:
            fd.write(initcf)

        with open(os.path.join(module_dir, "plugins", "__init__.py"), "w+") as fd:
            fd.write(initpy)

        with open(os.path.join(module_dir, "module.yml"), "w+") as fd:
            fd.write(f"""name: {name}
version: 0.1
license: Test License
                """)


@pytest.fixture(scope="session")
def snippetcompiler_global() -> Iterator[SnippetCompilationTest]:
    ast = SnippetCompilationTest()
    ast.setUpClass()
    yield ast
    ast.tearDownClass()


@pytest.fixture(scope="function")
def snippetcompiler(
    inmanta_config: ConfigParser, snippetcompiler_global: SnippetCompilationTest, modules_dir: str, clean_reset
) -> Iterator[SnippetCompilationTest]:
    """
    Yields a SnippetCompilationTest instance with shared libs directory and compiler venv.
    """
    snippetcompiler_global.setup_func(modules_dir)
    yield snippetcompiler_global
    snippetcompiler_global.tear_down_func()


@pytest.fixture(scope="function")
def snippetcompiler_clean(modules_dir: str, clean_reset, deactive_venv) -> Iterator[SnippetCompilationTest]:
    """
    Yields a SnippetCompilationTest instance with its own libs directory and compiler venv.
    """
    ast = SnippetCompilationTest()
    ast.setUpClass(re_check_venv=True)
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


class CLI:
    async def run(self, *args, **kwargs):
        # set column width very wide so lines are not wrapped
        os.environ["COLUMNS"] = "1000"
        runner = testing.CliRunner()
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
        yield CLI()


class AsyncCleaner:
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


class CompileRunnerMock:
    def __init__(
        self, request: data.Compile, make_compile_fail: bool = False, runner_queue: Optional[queue.Queue] = None
    ) -> None:
        self.request = request
        self.version: Optional[int] = None
        self._make_compile_fail = make_compile_fail
        self._make_pull_fail = False
        self._runner_queue = runner_queue
        self.block = False

    async def run(self, force_update: Optional[bool] = False) -> tuple[bool, None]:
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
def tmpvenv(tmpdir: py.path.local, deactive_venv) -> Iterator[tuple[py.path.local, py.path.local]]:
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


# Capture early, while loading code
real_prefix = sys.prefix


@pytest.fixture
def tmpvenv_active(
    deactive_venv, tmpvenv: tuple[py.path.local, py.path.local]
) -> Iterator[tuple[py.path.local, py.path.local]]:
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

    this_source_root = os.path.dirname(os.path.dirname(__file__))

    def keep_path_element(element: str) -> bool:
        # old venv paths are dropped
        if element.startswith(real_prefix):
            return False
        # exclude source install of the module
        if element.startswith(this_source_root):
            return False
        return True

    # prepend bin to PATH (this file is inside the bin directory), exclude old venv path
    os.environ["PATH"] = os.pathsep.join(
        [binpath] + [elem for elem in os.environ.get("PATH", "").split(os.pathsep) if keep_path_element(elem)]
    )
    os.environ["VIRTUAL_ENV"] = base  # virtual env is right above bin directory

    # add the virtual environments libraries to the host python import mechanism
    prev_length = len(sys.path)
    site.addsitedir(site_packages)
    # exclude old venv path
    sys.path[:] = sys.path[prev_length:] + [elem for elem in sys.path[0:prev_length] if keep_path_element(elem)]

    sys.real_prefix = sys.prefix
    sys.prefix = base

    # patch env.process_env to recognize this environment as the active one, deactive_venv restores it
    env.mock_process_env(python_path=str(python_path))
    env.process_env.notify_change()

    yield tmpvenv

    loader.unload_modules_for_path(site_packages)


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


@pytest.fixture
def create_empty_local_package_index_factory() -> Callable[[str], str]:
    """
    A fixture that acts as a factory to create empty local pip package indexes.
    Each call creates a new index in a different temporary directory.
    """

    created_directories: list[str] = []

    def _create_local_package_index(prefix: str = "test"):
        """
        Creates an empty pip index. The prefix argument is used as a prefix for the temporary directory name
        for clarity and debugging purposes. The 'dir2pi' tool will then create a 'simple' directory inside
        this temporary directory, which contains the index files.
        """
        tmpdir = tempfile.mkdtemp(prefix=f"{prefix}-")
        created_directories.append(tmpdir)  # Keep track of the tempdir for cleanup
        dir2pi(argv=["dir2pi", tmpdir])
        index_dir = os.path.join(tmpdir, "simple")  # The 'simple' directory is created inside the tmpdir by dir2pi
        return index_dir

    yield _create_local_package_index

    # Cleanup after the session ends
    for directory in created_directories:
        shutil.rmtree(directory)


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
        if len(os.listdir(index_dir)) != len(os.listdir(modules_v2_dir)) + 3:  # #modules + index.html + setuptools + wheel
            # Modules were added/removed from the build_dir
            return True
        # Cache is dirty
        return any(
            os.path.getmtime(os.path.join(root, f)) > os.path.getmtime(timestamp_file)
            for root, _, files in os.walk(modules_v2_dir)
            for f in files
            if "egg-info" not in root  # we write egg info in some test, messing up the tests
        )

    if _should_rebuild_cache():
        logger.info("Cache %s is dirty. Rebuilding cache.", cache_dir)  # Remove cache
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
        os.makedirs(build_dir)
        # Build modules
        for module_dir in os.listdir(modules_v2_dir):
            path: str = os.path.join(modules_v2_dir, module_dir)
            ModuleTool().build(path=path, output_dir=build_dir, wheel=True)
        # Download bare necessities
        CommandRunner(logging.getLogger(__name__)).run_command_and_log_output(
            [sys.executable, "-m", "pip", "download", "setuptools", "wheel"], cwd=build_dir
        )

        # Build python package repository
        dir2pi(argv=["dir2pi", build_dir])
        # Update timestamp file
        open(timestamp_file, "w").close()
    else:
        logger.info("Using cache %s", cache_dir)

    yield index_dir


@pytest.fixture
async def migrate_db_from(
    request: pytest.FixtureRequest,
    hard_clean_db,
    hard_clean_db_post,
    postgresql_client: asyncpg.Connection,
    disable_background_jobs,
    server_pre_start,
) -> AsyncIterator[Callable[[], Awaitable[None]]]:
    """
    Restores a db dump and yields a function that starts the server and migrates the database schema to the latest version.

    :param db_restore_dump: The db version dump file to restore (set via `@pytest.mark.db_restore_dump(<file>)`.
    """
    marker: Optional[pytest.mark.Mark] = request.node.get_closest_marker("db_restore_dump")
    if marker is None or len(marker.args) != 1:
        raise ValueError("Please set the db version to restore using `@pytest.mark.db_restore_dump(<file>)`")
    # restore old version
    with open(marker.args[0]) as fh:
        await PGRestore(fh.readlines(), postgresql_client).run()
        logger.debug("Restored %s", marker.args[0])

    bootloader: InmantaBootloader = InmantaBootloader(configure_logging=True)

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
    When the test suite runs, the python environment used to build V2 modules is cached using the DefaultIsolatedEnvCached
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
        with open(pyproject_toml_path, encoding="utf-8") as fh:
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


def is_caplog_handler(handler: logging.Handler) -> bool:
    return isinstance(
        handler,
        (
            _pytest.logging._FileHandler,
            _pytest.logging._LiveLoggingStreamHandler,
            _pytest.logging._LiveLoggingNullHandler,
            _pytest.logging.LogCaptureHandler,
        ),
    )


ALLOW_OVERRIDING_ROOT_LOG_LEVEL: bool = False


@pytest.fixture(scope="function")
def allow_overriding_root_log_level() -> None:
    """
    Fixture that allows a test case to indicate that the root log level, specified in a call to
    `inmanta_logging.FullLoggingConfig.apply_config()`, should be taken into account. By default,
    it's ignored to make sure that pytest logging works correctly. This fixture is mainly intended
    for the test cases that test the logging framework itself.
    """
    global ALLOW_OVERRIDING_ROOT_LOG_LEVEL
    ALLOW_OVERRIDING_ROOT_LOG_LEVEL = True
    yield
    ALLOW_OVERRIDING_ROOT_LOG_LEVEL = False


@pytest.fixture(scope="function", autouse=True)
async def dont_remove_caplog_handlers(request, monkeypatch):
    """
    Caplog captures log messages by attaching handlers to the root logger. Applying a logging config with
    `inmanta_logging.FullLoggingConfig.apply_config()` removes any existing logging configuration.
    As such, this fixture puts a wrapper around the `apply_config()` method to make sure that:

     * The pytest handlers are not removed/closed after the execution of the apply_config() method.
     * The configured root log level is not altered by the call to apply_config().
    """
    original_apply_config = inmanta_logging.FullLoggingConfig.apply_config

    def apply_config_wrapper(self) -> None:
        # Make sure the root log level is not altered.
        root_log_level: int = logging.root.level
        # Save the caplog root handlers so that we can restore them after.
        caplog_root_handler: list[logging.Handler] = [h for h in logging.root.handlers if is_caplog_handler(h)]
        for current_handler in caplog_root_handler:
            logging.root.removeHandler(current_handler)
        # When the `apply_config()` method is called, the `logging._handlerList` is used to find all the handlers
        # that should be closed. We remove the handlers from that list to prevent the handlers from being closed.
        #
        # This `logging._handlerList` is used to tear down the handlers in the reverse order with respect to the setup order.
        # As such, this method should not alter the order. We assume the caplog handlers are entirely independent
        # from any other handler. Like that the order only matters within the set of caplog handlers.
        re_add_to_handler_list: list[weakref.ReferenceType] = [
            weak_ref for weak_ref in logging._handlerList if is_caplog_handler(weak_ref())
        ]
        for weak_ref in re_add_to_handler_list:
            logging._handlerList.remove(weak_ref)

        original_apply_config(self)

        for weak_ref in re_add_to_handler_list:
            logging._handlerList.append(weak_ref)
        for current_handler in caplog_root_handler:
            logging.root.addHandler(current_handler)
        if not ALLOW_OVERRIDING_ROOT_LOG_LEVEL:
            logging.root.setLevel(root_log_level)

    monkeypatch.setattr(inmanta_logging.FullLoggingConfig, "apply_config", apply_config_wrapper)


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
                "optional-a": [inmanta.util.parse_requirement(requirement="dep-a")],
                "optional-b": [
                    inmanta.util.parse_requirement(requirement="dep-b"),
                    inmanta.util.parse_requirement(requirement="dep-c"),
                ],
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


@pytest.fixture(scope="session", autouse=True)
def disable_version_and_agent_cleanup_job():
    """
    Disable the cleanup job ran by the Inmanta server that cleans up old model version and agent records that are no longer
    used. Enabling this cleanup for the test suite causes race conditions in tests cases that create agent records without an
    associated model version.
    """
    old_perform_cleanup = orchestrationservice.PERFORM_CLEANUP
    orchestrationservice.PERFORM_CLEANUP = False
    yield
    orchestrationservice.PERFORM_CLEANUP = old_perform_cleanup


ResourceContainer = namedtuple(
    "ResourceContainer", ["Provider", "waiter", "wait_for_done_with_waiters", "wait_for_condition_with_waiters"]
)


@pytest.fixture(scope="function")
def resource_container(clean_reset):
    @resource("test::Resource", agent="agent", id_attribute="key")
    class MyResource(Resource):
        """
        A file on a filesystem
        """

        fields = ("key", "value", "purged")

    @resource("test::Resourcex", agent="agent", id_attribute="key")
    class MyResourcex(Resource):
        """
        A file on a filesystem
        """

        fields = ("key", "value", "purged", "attributes")

    @resource("test::Fact", agent="agent", id_attribute="key")
    class FactResource(Resource):
        """
        A file on a filesystem
        """

        fields = ("key", "value", "purged", "skip", "factvalue", "skipFact")

    @resource("test::SetFact", agent="agent", id_attribute="key")
    class SetFactResource(PurgeableResource):
        """
        A file on a filesystem
        """

        fields = ("key", "value", "purged", "purge_on_delete")

    @resource("test::SetNonExpiringFact", agent="agent", id_attribute="key")
    class SetNonExpiringFactResource(PurgeableResource):
        """
        A file on a filesystem
        """

        fields = ("key", "value", "purged", "purge_on_delete")

    @resource("test::Fail", agent="agent", id_attribute="key")
    class FailR(Resource):
        """
        A file on a filesystem
        """

        fields = ("key", "value", "purged")

    @resource("test::Wait", agent="agent", id_attribute="key")
    class WaitR(Resource):
        """
        A file on a filesystem
        """

        fields = ("key", "value", "purged")

    @resource("test::Noprov", agent="agent", id_attribute="key")
    class NoProv(Resource):
        """
        A file on a filesystem
        """

        fields = ("key", "value", "purged")

    @resource("test::FailFast", agent="agent", id_attribute="key")
    class FailFastR(Resource):
        """
        Raise an exception in the check_resource() method.
        """

        fields = ("key", "value", "purged")

    @resource("test::FailFastCRUD", agent="agent", id_attribute="key")
    class FailFastPR(PurgeableResource):
        """
        Raise an exception at the beginning of the read_resource() method
        """

        fields = ("key", "value", "purged", "purge_on_delete")

    @resource("test::BadPost", agent="agent", id_attribute="key")
    class BadPostR(Resource):
        """
        Raise an exception in the post() method of the ResourceHandler.
        """

        fields = ("key", "value", "purged")

    @resource("test::BadPostCRUD", agent="agent", id_attribute="key")
    class BadPostPR(PurgeableResource):
        """
        Raise an exception in the post() method of the CRUDHandlerGeneric.
        """

        fields = ("key", "value", "purged", "purge_on_delete")

    @resource("test::BadLogging", agent="agent", id_attribute="key")
    class BadLoggingR(Resource):
        """
        Raises an exception when trying to log a message that's not serializable.
        """

        fields = ("key", "value", "purged")

    @resource("test::Deploy", agent="agent", id_attribute="key")
    class DeployR(Resource):
        """
        Raise a SkipResource exception in the deploy() handler method.
        """

        fields = ("key", "value", "set_state_to_deployed", "purged")

    @resource("test::LSMLike", agent="agent", id_attribute="key")
    class LsmLike(Resource):
        """
        Raise a SkipResource exception in the deploy() handler method.
        """

        fields = ("key", "value", "purged")

    @resource("test::EventResource", agent="agent", id_attribute="key")
    class EventResource(PurgeableResource):
        """
        Raise a SkipResource exception in the deploy() handler method.
        """

        fields = ("key", "value", "change", "purged")

        @classmethod
        def get_change(cls, _, r):
            return False

    # Remote control state, shared over all resources
    _STATE = defaultdict(dict)
    _WRITE_COUNT = defaultdict(lambda: defaultdict(int))
    _RELOAD_COUNT = defaultdict(lambda: defaultdict(int))
    _READ_COUNT = defaultdict(lambda: defaultdict(int))
    _TO_SKIP = defaultdict(lambda: defaultdict(int))
    _TO_FAIL = defaultdict(lambda: defaultdict(int))

    class Provider(ResourceHandler[TResource], Generic[TResource]):
        def check_resource(self, ctx, resource):
            self.read(resource.id.get_agent_name(), resource.key)
            assert resource.value != const.UNKNOWN_STRING
            current = resource.clone()
            current.purged = not self.isset(resource.id.get_agent_name(), resource.key)

            if not current.purged:
                current.value = self.get(resource.id.get_agent_name(), resource.key)
            else:
                current.value = None

            return current

        def do_changes(self, ctx, resource, changes):
            if self.skip(resource.id.get_agent_name(), resource.key):
                raise SkipResource()

            if self.fail(resource.id.get_agent_name(), resource.key):
                raise Exception("Failed")

            if "purged" in changes:
                self.touch(resource.id.get_agent_name(), resource.key)
                if changes["purged"]["desired"]:
                    self.delete(resource.id.get_agent_name(), resource.key)
                    ctx.set_purged()
                else:
                    self.set(resource.id.get_agent_name(), resource.key, resource.value)
                    ctx.set_created()

            elif "value" in changes:
                ctx.info("Set key '%(key)s' to value '%(value)s'", key=resource.key, value=resource.value)
                self.touch(resource.id.get_agent_name(), resource.key)
                self.set(resource.id.get_agent_name(), resource.key, resource.value)
                ctx.set_updated()

            return changes

        def facts(self, ctx, resource):
            return {"length": len(self.get(resource.id.get_agent_name(), resource.key)), "key1": "value1", "key2": "value2"}

        def can_reload(self) -> bool:
            return True

        def do_reload(self, ctx, resource):
            _RELOAD_COUNT[resource.id.get_agent_name()][resource.key] += 1

        @classmethod
        def set_skip(cls, agent, key, skip):
            _TO_SKIP[agent][key] = skip

        @classmethod
        def set_fail(cls, agent, key, failcount):
            _TO_FAIL[agent][key] = failcount

        @classmethod
        def skip(cls, agent, key):
            doskip = _TO_SKIP[agent][key]
            if doskip == 0:
                return False
            _TO_SKIP[agent][key] -= 1
            return True

        @classmethod
        def fail(cls, agent, key):
            doskip = _TO_FAIL[agent][key]
            if doskip == 0:
                return False
            _TO_FAIL[agent][key] -= 1
            return True

        @classmethod
        def touch(cls, agent, key):
            _WRITE_COUNT[agent][key] += 1

        @classmethod
        def read(cls, agent, key):
            _READ_COUNT[agent][key] += 1

        @classmethod
        def set(cls, agent, key, value):
            _STATE[agent][key] = value

        @classmethod
        def get(cls, agent, key):
            if key in _STATE[agent]:
                return _STATE[agent][key]
            return None

        @classmethod
        def isset(cls, agent, key):
            return key in _STATE[agent]

        @classmethod
        def delete(cls, agent, key):
            if cls.isset(agent, key):
                del _STATE[agent][key]

        @classmethod
        def changecount(cls, agent, key):
            return _WRITE_COUNT[agent][key]

        @classmethod
        def readcount(cls, agent, key):
            return _READ_COUNT[agent][key]

        @classmethod
        def reloadcount(cls, agent, key):
            return _RELOAD_COUNT[agent][key]

        @classmethod
        def reset(cls):
            _STATE.clear()
            _WRITE_COUNT.clear()
            _READ_COUNT.clear()
            _TO_SKIP.clear()
            _TO_FAIL.clear()
            _RELOAD_COUNT.clear()

    @provider("test::Resource", name="test_resource")
    class ResourceProvider(Provider[MyResource]):
        pass

    @provider("test::Resourcex", name="test_resource")
    class ResourceProviderX(Provider[MyResource]):

        def check_resource(self, ctx, resource):
            # This resource checks that the executor can withstand mutating the resources
            assert resource.attributes == {"A": "B"}
            resource.attributes.clear()
            return super().check_resource(ctx, resource)

    @provider("test::Fail", name="test_fail")
    class Fail(ResourceHandler[FailR]):
        def check_resource(self, ctx, resource):
            current = resource.clone()
            current.purged = not Provider.isset(resource.id.get_agent_name(), resource.key)

            if not current.purged:
                current.value = Provider.get(resource.id.get_agent_name(), resource.key)
            else:
                current.value = None

            return current

        def do_changes(self, ctx, resource, changes):
            raise Exception()

    @provider("test::FailFast", name="test_failfast")
    class FailFast(ResourceHandler[FailFastR]):
        def check_resource(self, ctx: HandlerContext, resource: Resource) -> Resource:
            raise Exception("An\nError\tMessage")

    @provider("test::FailFastCRUD", name="test_failfast_crud")
    class FailFastCRUD(CRUDHandler[FailFastPR]):
        def read_resource(self, ctx: HandlerContext, resource: FailFastPR) -> None:
            raise Exception("An\nError\tMessage")

    @provider("test::Fact", name="test_fact")
    class Fact(ResourceHandler[FactResource]):
        def check_resource(self, ctx, resource):
            current = resource.clone()
            current.purged = not Provider.isset(resource.id.get_agent_name(), resource.key)

            current.value = "that"

            return current

        def do_changes(self, ctx, resource, changes):
            if resource.skip:
                raise SkipResource("can not deploy")
            if "purged" in changes:
                if changes["purged"]["desired"]:
                    Provider.delete(resource.id.get_agent_name(), resource.key)
                    ctx.set_purged()
                else:
                    Provider.set(resource.id.get_agent_name(), resource.key, "x")
                    ctx.set_created()
            else:
                ctx.set_updated()

        def facts(self, ctx: HandlerContext, resource: Resource) -> dict:
            if not Provider.isset(resource.id.get_agent_name(), resource.key):
                return {}
            elif resource.skipFact:
                raise SkipResource("Not ready")
            return {"fact": resource.factvalue}

    @provider("test::SetFact", name="test_set_fact")
    class SetFact(CRUDHandler[SetFactResource]):
        def read_resource(self, ctx: HandlerContext, resource: SetFactResource) -> None:
            self._do_set_fact(ctx, resource)

        def create_resource(self, ctx: HandlerContext, resource: SetFactResource) -> None:
            pass

        def delete_resource(self, ctx: HandlerContext, resource: SetFactResource) -> None:
            pass

        def update_resource(self, ctx: HandlerContext, changes: dict, resource: SetFactResource) -> None:
            pass

        def facts(self, ctx: HandlerContext, resource: Resource) -> dict:
            self._do_set_fact(ctx, resource)
            return {f"returned_fact_{resource.key}": "test"}

        def _do_set_fact(self, ctx: HandlerContext, resource: SetFactResource) -> None:
            ctx.set_fact(fact_id=resource.key, value=resource.value)

    @provider("test::SetNonExpiringFact", name="test_set_non_expiring_fact")
    class SetNonExpiringFact(CRUDHandler[SetNonExpiringFactResource]):
        def read_resource(self, ctx: HandlerContext, resource: SetNonExpiringFactResource) -> None:
            self._do_set_fact(ctx, resource)

        def create_resource(self, ctx: HandlerContext, resource: SetNonExpiringFactResource) -> None:
            pass

        def delete_resource(self, ctx: HandlerContext, resource: SetNonExpiringFactResource) -> None:
            pass

        def update_resource(self, ctx: HandlerContext, changes: dict, resource: SetNonExpiringFactResource) -> None:
            pass

        def facts(self, ctx: HandlerContext, resource: Resource) -> dict:
            self._do_set_fact(ctx, resource)
            return {}

        def _do_set_fact(self, ctx: HandlerContext, resource: SetNonExpiringFactResource) -> None:
            expires = resource.key == "expiring"
            ctx.set_fact(fact_id=resource.key, value=resource.value, expires=expires)

    @provider("test::BadPost", name="test_bad_posts")
    class BadPost(Provider):
        def post(self, ctx: HandlerContext, resource: Resource) -> None:
            raise Exception("An\nError\tMessage")

    @provider("test::BadPostCRUD", name="test_bad_posts_crud")
    class BadPostCRUD(CRUDHandler[BadPostPR]):
        def post(self, ctx: HandlerContext, resource: PurgeableResource) -> None:
            raise Exception("An\nError\tMessage")

    class Empty:
        pass

    @provider("test::BadLogging", name="test_bad_logging")
    class BadLogging(ResourceHandler[BadLoggingR]):
        def check_resource(self, ctx, resource):
            current = resource.clone()
            return current

        def do_changes(self, ctx, resource, changes):
            ctx.info("This is not JSON serializable: %(val)s", val=Empty())

    @provider("test::LSMLike", name="lsmlike")
    class LSMLikeHandler(CRUDHandler[LsmLike]):
        def deploy(
            self,
            ctx: handler.HandlerContext,
            resource: LsmLike,
            requires: dict[ResourceIdStr, const.ResourceState],
        ) -> None:
            self.pre(ctx, resource)
            try:
                all_resources_are_deployed_successfully = self._send_current_state(ctx, resource, requires)
                if all_resources_are_deployed_successfully:
                    ctx.set_status(const.ResourceState.deployed)
                else:
                    ctx.set_status(const.ResourceState.failed)
            finally:
                self.post(ctx, resource)

        def _send_current_state(
            self,
            ctx: handler.HandlerContext,
            resource: LsmLike,
            fine_grained_resource_states: dict[ResourceIdStr, const.ResourceState],
        ) -> bool:
            # If a resource is not in events, it means that it was deployed before so we can mark it as success
            is_failed = False
            skipped_resources = []
            # Convert inmanta.const.ResourceState to inmanta_lsm.model.ResourceState
            for resource_id, state in fine_grained_resource_states.items():
                if state == const.ResourceState.failed:
                    is_failed = True
                elif state == const.ResourceState.deployed:
                    pass
                else:
                    # some transient state that is not failed and not success, so lets skip
                    skipped_resources.append(f"skipped because the `{resource_id}` is `{state.value}`")

            # failure takes precedence over transient
            # transient takes precedence over success
            if len(skipped_resources) > 0 and not is_failed:
                raise SkipResource("\n".join(skipped_resources))

            return not is_failed

    waiter = Condition()

    async def wait_for_done_with_waiters(client, env_id, version, wait_for_this_amount_of_resources_in_done=None, timeout=10):
        def log_progress(done: int, total: int) -> None:
            logger.info(
                "waiting with waiters, %s/%s resources done",
                done,
                (wait_for_this_amount_of_resources_in_done if wait_for_this_amount_of_resources_in_done else total),
            )

        # unhang waiters
        now = time.time()
        done, total = await utils.get_done_and_total(client, env_id)

        log_progress(done, total)
        while (total - done) > 0:
            if now + timeout < time.time():
                raise Exception("Timeout")
            if wait_for_this_amount_of_resources_in_done and done - wait_for_this_amount_of_resources_in_done >= 0:
                break
            done, total = await utils.get_done_and_total(client, env_id)
            log_progress(done, total)
            waiter.acquire()
            waiter.notify_all()
            waiter.release()
            await asyncio.sleep(0.1)

    async def wait_for_condition_with_waiters(wait_condition, timeout=10):
        """
        Wait until wait_condition() returns false
        """
        now = time.time()
        while await wait_condition():
            if now + timeout < time.time():
                raise Exception("Timeout")
            logger.info("waiting with waiters")
            waiter.acquire()
            waiter.notify_all()
            waiter.release()
            await asyncio.sleep(0.1)

    @provider("test::Wait", name="test_wait")
    class Wait(Provider[WaitR]):
        def __init__(self, agent, io=None):
            super().__init__(agent, io)
            self.traceid = uuid.uuid4()

        def deploy(self, ctx, resource, requires) -> None:
            # Hang even when skipped
            logger.info("Hanging waiter %s", self.traceid)
            waiter.acquire()
            notified_before_timeout = waiter.wait(timeout=10)
            waiter.release()
            if not notified_before_timeout:
                raise Exception("Timeout occurred")
            logger.info("Releasing waiter %s", self.traceid)
            super().deploy(ctx, resource, requires)

    @provider("test::EventResource", name="test_event_processing")
    class EventResourceProvider(CRUDHandler[EventResource]):
        def __init__(self, agent, io=None):
            super().__init__(agent, io)
            self.traceid = uuid.uuid4()

        def read_resource(self, ctx: HandlerContext, resource: EventResource) -> None:
            logger.info("Hanging waiter %s", self.traceid)
            waiter.acquire()
            notified_before_timeout = waiter.wait(timeout=10)
            waiter.release()
            if not notified_before_timeout:
                raise Exception("Timeout occurred")
            logger.info("Releasing waiter %s", self.traceid)

            Provider.read(resource.id.get_agent_name(), resource.key)
            environment = self._agent.environment

            async def should_redeploy() -> bool:
                client = self.get_client()
                result = await client.get_resource_events(
                    environment,
                    resource.id.resource_version_str(),
                    const.Change.nochange,
                )
                if result.code != 200:
                    raise RuntimeError(
                        f"Unexpected response code when checking for events: received {result.code} "
                        f"(expected 200): {result.result}"
                    )
                changed_dependencies = result.result["data"]
                assert isinstance(changed_dependencies, dict)

                actual_changes = {k: v for k, v in changed_dependencies.items() if v}
                if actual_changes:
                    ctx.debug("Change found: %(changes)s, deploying", changes=actual_changes)
                else:
                    ctx.debug("No changes, not deploying")

                return bool(actual_changes)

            resource.change = self.run_sync(should_redeploy)

        def create_resource(self, ctx: HandlerContext, resource: EventResource) -> None:
            Provider.touch(resource.id.get_agent_name(), resource.key)
            ctx.set_created()

        def update_resource(self, ctx: HandlerContext, changes: dict[str, dict[str, Any]], resource: EventResource) -> None:
            Provider.touch(resource.id.get_agent_name(), resource.key)
            ctx.set_updated()

        def delete_resource(self, ctx: HandlerContext, resource: EventResource) -> None:
            Provider.touch(resource.id.get_agent_name(), resource.key)
            ctx.set_purged()

    @provider("test::Deploy", name="test_wait")
    class Deploy(Provider):
        def deploy(
            self,
            ctx: HandlerContext,
            resource: Resource,
            requires: dict[ResourceIdStr, const.ResourceState],
        ) -> None:
            if self.skip(resource.id.agent_name, resource.key):
                raise SkipResource()
            elif self.fail(resource.id.agent_name, resource.key):
                raise Exception()
            elif resource.set_state_to_deployed:
                ctx.set_status(const.ResourceState.deployed)

    yield ResourceContainer(
        Provider=Provider,
        wait_for_done_with_waiters=wait_for_done_with_waiters,
        waiter=waiter,
        wait_for_condition_with_waiters=wait_for_condition_with_waiters,
    )
    Provider.reset()
