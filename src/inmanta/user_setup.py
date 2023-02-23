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
import secrets
import socket

import asyncpg
import click

import nacl.pwhash
from inmanta import config, data
from inmanta.server import config as server_config


def generate_signing_config() -> str:
    hostname = socket.gethostname()
    return f"""[auth_jwt_default]
algorithm=HS256
sign=true
client_types=agent,compiler,api
key={secrets.token_urlsafe(32)}
expire=0
issuer=https://{hostname}:{server_config.server_bind_port.get()}/
audience=https://{hostname}:{server_config.server_bind_port.get()}/
"""


def validate_server_setup() -> None:
    """Validate the server configuration so that authentication is setup correctly."""
    config.Config.load_config()

    # make sure auth is on
    if not server_config.server_enable_auth.get():
        raise click.ClickException(
            "Server authentication should be enabled before running the initial user setup. "
            "The option auth in the server section should be enabled."
        )

    click.echo(f"{'Server authentication: ' : <50}{click.style('enabled', fg='green')}")

    # make sure the method is set to database
    if server_config.server_auth_method.get() != "database":
        raise click.ClickException(
            "The server authentication method should be set to database to continue. Make sure auth_method in the server "
            "section is set to database"
        )

    click.echo(f"{'Server authentication method: ' : <50}{click.style('database', fg='green')}")

    # make sure there is auth config that supports signing tokens
    cfg = config.AuthJWTConfig.get_sign_config()
    if cfg is None:
        click.echo("Error: No signing config available in the configuration.")

        value = None
        while value not in ["yes", "no"]:
            value = click.prompt("Do you want to generate a new configuration? yes/no")

        if value == "yes":
            click.echo("Add the following to the configuration in /etc/inmanta/inmanta.d/auth.cfg:\n")
            click.echo(generate_signing_config())

        raise click.ClickException("Make sure signing configuration is added to the config. See the documentation for details.")

    click.echo(f"{'Authentication signing config: ' : <50}{click.style('enabled', fg='green')}")

    # TODO: verify web-console config (if any)


async def get_database_connection() -> asyncpg.Pool:
    database_host = server_config.db_host.get()
    database_port = server_config.db_port.get()

    database_username = server_config.db_username.get()
    database_password = server_config.db_password.get()
    connection_pool_min_size = server_config.db_connection_pool_min_size.get()
    connection_pool_max_size = server_config.db_connection_pool_max_size.get()
    connection_timeout = server_config.db_connection_timeout.get()
    return await data.connect(
        database_host,
        database_port,
        server_config.db_name.get(),
        database_username,
        database_password,
        connection_pool_min_size=connection_pool_min_size,
        connection_pool_max_size=connection_pool_max_size,
        connection_timeout=connection_timeout,
    )


async def do_user_setup() -> None:
    """Perform the user setup that requires the database interaction"""
    connection = None
    try:
        connection = await get_database_connection()
        users = await data.User.get_list(connection=connection)

        if len(users):
            raise click.ClickException(
                "There are already users in the database. If you want to reset the password, use the --reset option."
            )

        username = click.prompt("What username do you want to use?", default="admin")
        password = click.prompt("What password do you want to use?", hide_input=True)

        pw_hash = nacl.pwhash.str(password.encode())

        # insert the user
        user = data.User(
            username=username,
            password_hash=pw_hash.decode(),
            enabled=True,
            auth_method="password",
        )
        await user.insert(connection=connection)

        click.echo(f"{'User %s: ' %username <50}{click.style('created', fg='green')}")
    finally:
        if connection is not None:
            await data.disconnect()

    click.echo("Make sure to (re)start the orchestrator to activate all changes.")


@click.command(help="Do the initial user setup")
@click.option("--reset", help="Reset the password to recover a lost password", is_flag=True)
def cmd(reset: bool) -> None:
    try:
        # validate the setup so that we can setup a new user
        validate_server_setup()
    except Exception as e:
        print(e)
    # check if there are already users

    asyncio.run(do_user_setup())
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(do_user_setup())


def main() -> None:
    cmd()


if __name__ == "__main__":
    main()
