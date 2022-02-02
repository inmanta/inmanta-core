import click
from typing import Any, Callable, Generator

from pkg_resources import EntryPoint

def with_plugins(plugins: Generator[EntryPoint, None, None]) -> Callable[[click.Group], click.Group]: ...
