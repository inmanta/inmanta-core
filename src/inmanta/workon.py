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


DEFAULT_COLUMN_WIDTH_NAME: int = 20


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
    # TODO implement
    raise NotImplementedError()


def click_list_environments() -> None:
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


# TODO: what if this is called on a non-server machine?
@click.command(no_args_is_help=True)
@click.option("-l", "--list", "l", is_flag=True, default=False, help="List all environments with their ids")
@click.argument("environment", type=str, required=False)
def workon(l: bool, environment: str) -> None:
    """
    Work on an inmanta environment. ENVIRONMENT can be an environment name or id.
    """
    if l:
        click_list_environments()
        return
    # TODO implement
    raise NotImplementedError()


def main() -> None:
    workon()


if __name__ == "__main__":
    main()
