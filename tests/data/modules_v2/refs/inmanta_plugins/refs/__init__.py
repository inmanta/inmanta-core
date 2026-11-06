import os
from typing import Annotated, Any

import inmanta.plugins
from inmanta.agent.handler import LoggerABC, provider, CRUDHandler, HandlerContext
from inmanta.references import get_value, lazy, reference, Reference, is_reference_of
from inmanta.plugins import plugin, ModelType
from inmanta.resources import resource, ManagedResource, PurgeableResource


@reference("refs::Bool")
class BoolReference(Reference[bool]):

    def __init__(self, name: str | Reference[str]) -> None:
        """
        :param name: The name of the environment variable.
        """
        super().__init__()
        self.name = name

    def resolve(self, logger: LoggerABC) -> bool:
        """Resolve the reference"""
        self.resolve_other(self.name, logger)
        return False

    def __repr__(self) -> str:
        return f"BoolReference({self.name!r})"


@reference("refs::Int")
class IntReference(Reference[int]):

    def __init__(self, name: str | Reference[str]) -> None:
        """
        :param name: The name of the environment variable.
        """
        super().__init__()
        self.name = name

    def resolve(self, logger: LoggerABC) -> int:
        """Resolve the reference"""
        self.resolve_other(self.name, logger)
        return 42

    def __repr__(self) -> str:
        return f"IntReference({self.name!r})"


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

    def __repr__(self) -> str:
        return f"StringReference()"


@plugin
def create_bool_reference(name: Reference[str] | str) -> Reference[bool]:
    return BoolReference(name=name)


@plugin
def create_int_reference(name: Reference[str] | str) -> Reference[int]:
    return IntReference(name=name)


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

    def __repr__(self) -> str:
        return f"BadReference({self.name!r})"


@plugin
def create_bad_reference(name: Reference[str] | str) -> Reference[str]:
    return BadReference(name=name)


@reference("refs::DictMade")
class DictMade(Reference[str]):
    """A dummy reference to a string"""

    def __init__(self, name: dict[str, list[str | Reference[str]]]) -> None:
        """
        :param name: The name of the environment variable.
        """
        super().__init__()
        self.name = name

    def resolve(self, logger: LoggerABC) -> str:
        """Resolve the reference"""
        # name accepts lazy references: the references nested in it are passed unresolved
        return get_value(self.name["name"], logger)

    def __repr__(self) -> str:
        return f"DictMade({self.name!r})"


@plugin
def create_DictRef(value: str | Reference[str]) -> DictMade:
    return DictMade(name={"name": [value]})


@resource("refs::DeepResource", agent="agentname", id_attribute="name")
class Deep(ManagedResource, PurgeableResource):
    fields = ("name", "agentname", "value")

    @classmethod
    def get_value(cls, _, resource) -> dict[str, object | Reference[object]]:
        # use a . to ensure proper escaping
        return {"inner.something": inmanta.plugins.allow_reference_values(resource).value}


@resource("refs::DeepResourceNoReferences", agent="agentname", id_attribute="name")
class DeepNoReferences(Deep):
    @classmethod
    def get_value(cls, _, resource) -> dict[str, object | Reference[object]]:
        # same as Deep.get_value but don't declare that references are allowed => test should fail
        return {"inner.something": [resource.value]}


@resource("refs::DictResource", agent="agentname", id_attribute="name")
class DictResource(ManagedResource, PurgeableResource):
    fields = ("name", "agentname", "value")


class NullProvider[R: NullResource](CRUDHandler[R]):
    """Does nothing at all"""

    def read_resource(self, ctx: HandlerContext, resource: R) -> None:
        ctx.debug("Observed value: %(value)s", value=resource.value)
        return

    def create_resource(self, ctx: HandlerContext, resource: R) -> None:
        ctx.set_created()

    def delete_resource(self, ctx: HandlerContext, resource: R) -> None:
        ctx.set_purged()

    def update_resource(self, ctx: HandlerContext, changes: dict, resource: R) -> None:
        ctx.set_updated()


@provider("refs::DeepResource", name="null")
class DeepProvider(NullProvider[Deep]): ...


@provider("refs::DictResource", name="null")
class DictProvider(NullProvider[DictResource]): ...


@resource("refs::LazyReferenceResource", agent="agentname", id_attribute="name")
class LazyReferenceResource(ManagedResource, PurgeableResource):
    fields = ("name", "agentname", "maybe_ref", "ref", "eager", "specific", "nested")
    maybe_ref: str | Reference[str]
    ref: Reference[str]
    eager: str
    specific: StringReference | None
    nested: dict[str, str | Reference[str]]


@resource("refs::InheritedLazyReferenceResource", agent="agentname", id_attribute="name")
class InheritedLazyReferenceResource(LazyReferenceResource):
    """Inherits the annotations of its fields"""


@resource("refs::LazyMarkerResource", agent="agentname", id_attribute="name")
class LazyMarkerResource(ManagedResource, PurgeableResource):
    fields = ("name", "agentname", "data")
    data: dict  # eager: the annotation doesn't mention Reference, get_data marks one reference lazy

    @classmethod
    def get_data(cls, _, entity) -> dict[str, object]:
        entity = inmanta.plugins.allow_reference_values(entity)
        return {"lazy": lazy(entity.lazy_value), "eager": entity.eager_value, "plain": lazy(entity.plain_value)}


@provider("refs::LazyMarkerResource", name="null")
class LazyMarkerProvider(NullProvider[LazyMarkerResource]): ...


@plugin
def create_lazy_in_argument(value: str | Reference[str]) -> DictMade:
    """lazy() is only for resource getters: the exporter rejects it in a reference argument"""
    return DictMade(name={"name": [lazy(value)]})


@reference("refs::Concat")
class ConcatReference(Reference[str]):
    """Concatenates two strings, the left one is passed to the constructor unresolved, the right one resolved"""

    def __init__(self, left: str | Reference[str], right: str) -> None:
        super().__init__()
        self.left = left
        self.right = right

    def resolve(self, logger: LoggerABC) -> str:
        return self.resolve_other(self.left, logger) + self.right

    def __repr__(self) -> str:
        return f"ConcatReference({self.left!r}, {self.right!r})"


@plugin
def create_concat_reference(left: Reference[str] | str, right: Reference[str] | str) -> Reference[str]:
    return ConcatReference(left=left, right=right)
