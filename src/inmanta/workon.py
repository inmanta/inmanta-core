"""
    Copyright 2022 Inmanta

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
# TODO: ADR
import click
import typing
import uuid
from collections import abc
from typing import Optional, Union
from dataclasses import dataclass

from inmanta.protocol.common import Result
from inmanta.protocol.endpoints import SyncClient


DEFAULT_COLUMN_WIDTH_NAME: int = 20

# TODO: config.Config.set("cmdline_rest_transport", "port", 8888), config.Config.set("cmdline_rest_transport", "host", "localhost")? Or use config file?

@dataclass(frozen=True)
class EnvironmentABC:
    id: uuid.UUID


# name may not always be available because it requires an API call
@dataclass(frozen=True)
class NamelessEnvironment(EnvironmentABC):
    pass


@dataclass(frozen=True)
class NamedEnvironment(EnvironmentABC):
    name: str


EnvironmentSequence = Union[abc.Sequence[NamelessEnvironment], abc.Sequence[NamedEnvironment]]


def get_environments() -> EnvironmentSequence:
    # TODO docstring
    client = SyncClient("cmdline")
    result: Result = client.list_environments()
    if result.code == 200:
        assert "environments" in result.result
        environments: object = result.result["environments"]
        print(environments)
        # TODO implement
        raise NotImplementedError()
    else:
        reason: str = f" Reason: {result.result['message']}" if "message" in result.result else ""
        click.echo(
            (
                "Failed to fetch environments details from the server, falling back to basic nameless environment discovery."
                f"{reason}"
            ),
            err=True,
        )
        # TODO implement
        raise NotImplementedError()


def echo_environments() -> None:
    # TODO docstring
    environments: EnvironmentSequence = get_environments()
    if not environments:
        return
    if isinstance(environments[0], NamedEnvironment):
        named_envs: abc.Sequence[NamedEnvironment] = typing.cast(abc.Sequence[NamedEnvironment], environments)
        name_length: int = max(DEFAULT_COLUMN_WIDTH_NAME, max(len(named.name) for named in named_envs))
        for named in named_envs:
            click.echo(f"{named.name:<{name_length}} {named.id}")
    else:
        for nameless in environments:
            click.echo(str(nameless.id))


def echo_environments_callback(ctx: click.Context, param: click.Parameter, value: bool) -> None:
    if not value or ctx.resilient_parsing:
        return
    echo_environments()
    ctx.exit()


# TODO: what if this is called on a non-server machine?
@click.command(no_args_is_help=True)
@click.option(
    "-l",
    "--list",
    "l",
    is_flag=True,
    default=False,
    help="List all environments with their ids",
    # different execution flow for --list: use eager parameter with callback
    is_eager=True,
    expose_value=False,
    callback=echo_environments_callback,
)
@click.argument("environment", type=str)
def workon(l: bool, environment: str) -> None:
    """
    Work on an inmanta environment. ENVIRONMENT can be an environment name or id.
    """
    # TODO implement
    raise NotImplementedError()


def main() -> None:
    workon()


if __name__ == "__main__":
    main()
