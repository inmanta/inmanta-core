import os
from typing import Annotated, Any

from inmanta.agent.handler import LoggerABC, provider, CRUDHandler, HandlerContext
from inmanta.references import reference, Reference, is_reference_of
from inmanta.plugins import plugin, ModelType
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

    def resolve(self, logger: LoggerABC) -> bool:
        """Resolve the reference"""
        return os.getenv(self.resolve_other(self.name, logger)) == "true"

    def __str__(self) -> str:
        return f"BoolReference {self.name}"


@reference("refs::String")
class StringReference(Reference[str]):
    """A dummy reference to a string"""

    def __init__(self, name: str | Reference[str]) -> None:
        """
        :param name: The name of the environment variable.
        """
        super().__init__()
        self.name = name

    def resolve(self, logger: LoggerABC) -> str:
        """Resolve the reference"""
        return self.resolve_other(self.name, logger)

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


@reference("refs::BAD")
class BadReference(Reference[str]):
    """A dummy reference to a string"""

    def __init__(self, name: str | Reference[str]) -> None:
        """
        :param name: The name of the environment variable.
        """
        super().__init__()
        self.name = name

    def resolve(self, logger: LoggerABC) -> str:
        """Resolve the reference"""
        raise Exception("BAD")

    def __str__(self) -> str:
        return f"BadReference"


@plugin
def create_bad_reference(name: Reference[str] | str) -> Reference[str]:
    return BadReference(name=name)


@resource("refs::DeepResource", agent="agentname", id_attribute="name")
class Deep(ManagedResource, PurgeableResource):
    fields = ("name", "agentname", "value")

    @classmethod
    def get_value(cls, _, resource) -> dict[str, object]:
        return {"inner": resource.value}


@provider("refs::DeepResource", name="null")
class NullProvider(CRUDHandler[Deep]):
    """Does nothing at all"""

    def read_resource(self, ctx: HandlerContext, resource: Deep) -> None:
        ctx.debug("Observed value: %(value)s", value=resource.value)
        return

    def create_resource(self, ctx: HandlerContext, resource: Deep) -> None:
        ctx.set_created()

    def delete_resource(self, ctx: HandlerContext, resource: Deep) -> None:
        ctx.set_purged()

    def update_resource(self, ctx: HandlerContext, changes: dict, resource: Deep) -> None:
        ctx.set_updated()
