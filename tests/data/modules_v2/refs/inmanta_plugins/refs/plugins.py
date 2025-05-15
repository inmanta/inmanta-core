from collections.abc import Mapping, Sequence
from typing import Annotated, Any

from inmanta import plugins
from inmanta.execute.proxy import DynamicProxy
from inmanta.plugins import plugin, ModelType
from inmanta.references import Reference
from inmanta_plugins.refs import dc


type Entity = Annotated[Any, ModelType["std::Entity"]]


@plugin
def takes_obj(v: object) -> None:
    ...


@plugin
def takes_obj_ref(v: object | Reference[object]) -> None:
    ...


@plugin
def takes_obj_ref_only(v: Reference[object]) -> None:
    assert isinstance(v, Reference)


@plugin
def takes_str(v: str) -> None:
    ...


@plugin
def takes_str_ref(v: str | Reference[str]) -> None:
    ...


@plugin
def iterates_obj_list(l: Sequence[object]) -> None:
    for x in l:
        ...


@plugin
def iterates_obj_list(l: Sequence[object]) -> None:
    for x in l:
        ...


@plugin
def iterates_str_list(l: Sequence[str]) -> None:
    for x in l:
        assert isinstance(x, str), type(x)


@plugin
def iterates_str_ref_list(l: Sequence[str | Reference[str]]) -> None:
    for x in l:
        assert isinstance(x, (str, Reference)), type(x)


@plugin
def iterates_object_dict(l: Mapping[str, object]) -> None:
    for x in l.values():
        ...


@plugin
def iterates_object_ref_dict(l: Mapping[str, object | Reference[object]]) -> None:
    for x in l.values():
        ...


@plugin
def takes_entity(instance: Entity) -> None:
    assert isinstance(instance, DynamicProxy)


@plugin
def takes_all_refs_dataclass(instance: dc.AllRefsDataclass) -> None:
    assert isinstance(instance, dc.AllRefsDataclass)


@plugin
def takes_no_refs_dataclass(instance: dc.NoRefsDataclass) -> None:
    assert isinstance(instance, dc.NoRefsDataclass)


@plugin
def takes_mixed_refs_dataclass(instance: dc.MixedRefsDataclass) -> None:
    assert isinstance(instance, dc.MixedRefsDataclass)


@plugin
def takes_all_refs_dataclass_ref(instance: Reference[dc.AllRefsDataclass]) -> None:
    assert isinstance(instance, Reference)


@plugin
def takes_no_refs_dataclass_ref(instance: Reference[dc.NoRefsDataclass]) -> None:
    assert isinstance(instance, Reference)


@plugin
def takes_mixed_refs_dataclass_ref(instance: Reference[dc.MixedRefsDataclass]) -> None:
    assert isinstance(instance, Reference)


@plugin
def takes_all_refs_dataclass_or_ref(instance: dc.AllRefsDataclass | Reference[dc.AllRefsDataclass]) -> None:
    assert isinstance(instance, (dc.AllRefsDataclass, Reference))


@plugin
def takes_no_refs_dataclass_or_ref(instance: dc.NoRefsDataclass | Reference[dc.NoRefsDataclass]) -> None:
    assert isinstance(instance, (dc.NoRefsDataclass, Reference))


@plugin
def takes_mixed_refs_dataclass_or_ref(instance: dc.MixedRefsDataclass | Reference[dc.MixedRefsDataclass]) -> None:
    assert isinstance(instance, (dc.MixedRefsDataclass, Reference))


@plugin
def read_entity_value(instance: Entity) -> None:
    instance.maybe_ref_value  # expected to fail iff it's a reference
    return None


@plugin
def read_entity_ref_value(instance: Entity) -> None:
    plugins.allow_reference_attributes(instance).maybe_ref_value
    return None


# TODO: everything below this: check if used
#@plugin
#def read_dataclass_value(instance: refs.Test) -> None:
#    failed_read = instance.non_ref_value
#    return None


#@plugin
#def read_dataclass_ref_value(instance: refs.Test | Reference[refs.Test]) -> None:
#    breakpoint()
#    instance.value
#    instance.non_ref_value
#    # TODO
#    ...
#    #failed_read = instance.non_ref_value
#    #return None
