import dataclasses
from typing import Annotated

from inmanta.execute.proxy import DynamicProxy
from inmanta.plugins import plugin, ModelType


@dataclasses.dataclass(frozen=True)
class Virtualmachine:
    name: str
    ram: int
    cpus: int


@plugin
def is_virtual_machine(vm: Virtualmachine) -> None:
    # The declared type is a python type, so we receive an actual python object
    assert isinstance(vm, Virtualmachine)

@plugin
def is_dynamic_proxy(vm: Annotated[DynamicProxy, ModelType["Virtualmachine"]]) -> None:
    # Explicitly request DynamicProxy to prevent the dataclass from being converted
    assert isinstance(vm, DynamicProxy)
