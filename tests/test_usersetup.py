"""
    Copyright 2023 Inmanta

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
import logging
import os

from click import testing

from inmanta import data
from inmanta.db.util import PGRestore
from inmanta.server.bootloader import InmantaBootloader
from inmanta.user_setup import cmd, get_connection_pool

logger = logging.getLogger(__name__)


class CLI_user_setup:
    async def run(self, run_locally, username, password, *args, **kwargs):
        # set column width very wide so lines are not wrapped
        os.environ["COLUMNS"] = "1000"
        runner = testing.CliRunner(mix_stderr=False)

        def invoke():
            return runner.invoke(cli=cmd, input=f"{run_locally}\n{username}\n{password}")

        result = await asyncio.get_event_loop().run_in_executor(None, invoke)
        # reset to default again
        del os.environ["COLUMNS"]
        return result


def setup_config(tmpdir, postgres_db, database_name):
    """
    set up the needed config to use usersetup
    """
    dot_inmanta_cfg_file = os.path.join(tmpdir, ".inmanta.cfg")
    with open(dot_inmanta_cfg_file, "w", encoding="utf-8") as f:
        f.write(
            f"""
    [server]
    auth=true
    auth_method=database

    [auth_jwt_default]
    algorithm=HS256
    sign=true
    client_types=agent,compiler,api
    key=eciwliGyqECVmXtIkNpfVrtBLutZiITZKSKYhogeHMM
    expire=0
    issuer=https://localhost:8888/
    audience=https://localhost:8888/

    [database]
    name={database_name}
    host=localhost
    port={str(postgres_db.port)}
    username={postgres_db.user}
    password={postgres_db.password}
    connection_timeout=3
            """
        )
    os.chdir(tmpdir)


async def test_user_setup(tmpdir, server_pre_start, postgres_db, database_name, hard_clean_db, hard_clean_db_post):
    ibl = InmantaBootloader()
    # we need the server to start so that all the migrations scripts are applied, but the server needs
    # to be shut down afterwards, otherwise the call to get_connection_pool() will result in an exception saying
    # that the connection pool is already set in the database layer.
    await ibl.start()
    await ibl.stop(timeout=15)

    setup_config(tmpdir, postgres_db, database_name)
    cli = CLI_user_setup()
    result = await cli.run("yes", "new_user", "pw")
    assert result.exit_code == 1
    assert result.stderr == "Error: the password should be at least 8 characters long\n"

    result = await cli.run("yes", "new_user", "password")
    assert result.exit_code == 0
    try:
        # Because the setup command calls data.disconnect(), we cannot use the init_dataclasses_and_load_schema fixture here.
        # After calling into cli.run(), the connection to the database, which was setup by the init_dataclasses_and_load_schema
        # fixture, will be no longer active.
        connection = await get_connection_pool()
        users = await data.User.get_list()
        assert len(users) == 1
        assert users[0].username == "new_user"

    finally:
        if connection is not None:
            await data.disconnect()


async def test_user_setup_empty_username(
    tmpdir, server_pre_start, postgres_db, database_name, hard_clean_db, hard_clean_db_post
):
    """test that if no username is provided to the user setup tool, the username will default to admin"""
    ibl = InmantaBootloader()
    # we need the server to start so that all the migrations scripts are applied, but the server needs
    # to be shut down afterwards, otherwise the call to get_connection_pool() will result in an exception saying
    # that the connection pool is already set in the database layer.
    await ibl.start()
    await ibl.stop(timeout=15)

    setup_config(tmpdir, postgres_db, database_name)
    cli = CLI_user_setup()

    result = await cli.run("yes", "", "password")
    assert result.exit_code == 0
    try:
        # Because the setup command calls data.disconnect(), we cannot use the init_dataclasses_and_load_schema fixture here.
        # After calling into cli.run(), the connection to the database, which was setup by the init_dataclasses_and_load_schema
        # fixture, will be no longer active.
        connection = await get_connection_pool()
        users = await data.User.get_list()
        assert len(users) == 1
        assert users[0].username == "admin"

    finally:
        if connection is not None:
            await data.disconnect()


async def test_user_setup_schema_outdated(
    tmpdir, postgres_db, database_name, postgresql_client, hard_clean_db, hard_clean_db_post
):
    setup_config(tmpdir, postgres_db, database_name)

    dump_path = os.path.join(os.path.dirname(__file__), "db/migration_tests/dumps/v202211230.sql")
    with open(dump_path) as fh:
        await PGRestore(fh.readlines(), postgresql_client).run()

    cli = CLI_user_setup()
    result = await cli.run("yes", "new_user", "password")
    assert result.exit_code == 1
    assert (
        result.stderr == "Error: The version of the database is out of date: start the server"
        " to upgrade the database schema to the lastest version.\n"
    )
