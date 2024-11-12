import os

from inmanta.ast.type import String
from inmanta.references import reference, Reference
from inmanta.plugins import plugin


@reference("refs::Bool")
class BoolReference(Reference[bool]):
    """A reference to fetch environment variables"""

    def __init__(self, name: str | Reference[str]) -> None:
        """
        :param name: The name of the environment variable.
        """
        super().__init__(name=name)
        self.name = name

    def resolve(self) -> bool:
        """Resolve the reference"""
        return os.getenv(self.get_argument("name")) == "true"

@reference("refs::String")
class StringReference(Reference[str]):
    """A reference to fetch environment variables"""

    def __init__(self, name: str | Reference[str]) -> None:
        """
        :param name: The name of the environment variable.
        """
        super().__init__(name=name)

    def resolve(self) -> str:
        """Resolve the reference"""
        return self.get_argument("name")

@plugin
def create_bool_reference(name: "any") -> "bool":
    return BoolReference(name=name)

@plugin
def create_string_reference(name: "any") -> "string":
    return StringReference(name=name)