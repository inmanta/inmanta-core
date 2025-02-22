import os
import dataclasses

from inmanta.references import reference, Reference, is_reference_of
from inmanta.plugins import plugin
from inmanta.resources import resource, ManagedResource, PurgeableResource


@reference("refs::Bool")
class BoolReference(Reference[bool]):
    """A reference to fetch environment variables"""

    def __init__(self, name: str | Reference[str]) -> None:
        """
        :param name: The name of the environment variable.
        """
        super().__init__()
        self.name = name

    def resolve(self) -> bool:
        """Resolve the reference"""
        return os.getenv(self.resolve_other(self.name)) == "true"


@reference("refs::String")
class StringReference(Reference[str]):
    """A dummy reference to a string"""

    def __init__(self, name: str | Reference[str]) -> None:
        """
        :param name: The name of the environment variable.
        """
        super().__init__()
        self.name = name

    def resolve(self) -> str:
        """Resolve the reference"""
        return self.resolve_other(self.name)

    def __str__(self) -> str:
        return f"StringReference"


@plugin
def create_bool_reference(name: Reference[str] | str) -> Reference[bool]:
    return BoolReference(name=name)


@plugin
def create_string_reference(name: Reference[str] | str) -> Reference[str]:
    return StringReference(name=name)


@plugin
def create_bool_reference_cycle(name: str) -> Reference[bool]:
    # create a reference with a cycle
    ref_cycle = StringReference(name)

    assert is_reference_of(ref_cycle, str)
    assert not is_reference_of(None, str)
    assert not is_reference_of(ref_cycle, int)

    ref_cycle.name = ref_cycle

    return BoolReference(name=ref_cycle)


@dataclasses.dataclass(frozen=True)
class Test:
    value: str | Reference[str]


@reference("refs::TestReference")
class TestReference(Reference[Test]):
    """A reference that returns a dataclass"""

    def __init__(self, value: str | Reference[str]) -> None:
        """
        :param value: The value
        """
        super().__init__()
        self.value = value

    def resolve(self) -> Test:
        """Resolve test references"""
        return Test(value=self.resolve_other(self.value))


@plugin
def create_test(value: str | Reference[str]) -> TestReference:
    return TestReference(value=value)


@resource("refs::NullResource", agent="agentname", id_attribute="name")
class Null(ManagedResource, PurgeableResource):
    fields = ("name", "agentname", "fail")

    @classmethod
    def get_fail(cls, exporter, instance) -> object:
        # Return a reference to the wrong resource!!!
        if instance.fail:
            if exporter._resources:
                return StringReference(next(iter(exporter._resources.values())))
            return False
        else:
            return False
