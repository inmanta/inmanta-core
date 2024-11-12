import os

from inmanta.references import reference, Reference
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


@plugin
def create_environment_reference(name: "string") -> "bool":
    """Create an environment reference

    :param name: The name of the variable to fetch from the environment
    :return: A reference to what can be resolved to a string
    """
    return BoolReference(name=name)
