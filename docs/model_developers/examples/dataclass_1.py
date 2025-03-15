import dataclasses

from inmanta.plugins import plugin

@dataclasses.dataclass(frozen=True)
class Virtualmachine:
    name: str
    ram: int
    cpus: int

@plugin
def make_virtual_machine() -> Virtualmachine:
    return Virtualmachine(name="Test", ram=5, cpus=12)
