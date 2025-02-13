import dataclasses

from inmanta.execute.proxy import DynamicProxy
from inmanta.plugins import plugin

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
def is_dynamic_proxy(vm: "Virtualmachine") -> None:
    # The declared type is an inmanta type, so we receive a DynamicProxy
    assert isinstance(vm, DynamicProxy)
