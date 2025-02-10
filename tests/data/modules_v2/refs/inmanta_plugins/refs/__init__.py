import os
import dataclasses

from inmanta.references import reference, Reference, DataclassReference
from inmanta.plugins import plugin


@reference("refs::Bool")
class BoolReference(Reference[bool]):
    """A reference to fetch environment variables"""

    def __init__(self, name: str) -> None:
        """
        :param name: The name of the environment variable.
        """
        super().__init__(name=name)
        self.name = name

    def resolve(self) -> bool:
        """Resolve the reference"""
        return os.getenv(self.name) == "true"


@reference("refs::String")
class StringReference(Reference[str]):
    """A reference to fetch environment variables"""

    def __init__(self, name: str) -> None:
        """
        :param name: The name of the environment variable.
        """
        super().__init__(name=name)
        self.name = name

    def resolve(self) -> str:
        """Resolve the reference"""
        return self.name


@plugin
def create_bool_reference(name: Reference[str] | str) -> Reference[bool]:
    return BoolReference(name=name)


@plugin
def create_string_reference(name: Reference[str] | str) -> Reference[str]:
    return StringReference(name=name)


@plugin
def create_bool_reference_cycle(name: "any") -> "bool":
    # create a reference with a cycle
    ref_cycle = StringReference(name)
    ref_cycle._arguments["name"] = ref_cycle

    return BoolReference(name=ref_cycle)


@dataclasses.dataclass(frozen=True)
class Test:
    value: str | Reference[str]


@reference("refs::TestReference")
class TestReference(DataclassReference[Test]):
    """A reference that returns a dataclass"""

    def __init__(self, value: str) -> None:
        """
        :param value: The value
        """
        super().__init__(value=value)
        self._value = value

    def resolve(self) -> Test:
        """Resolve test references"""
        return Test(value=self._value)


@plugin
def create_test(value: str | Reference[str]) -> TestReference:
    return TestReference(value=value)
