from collections.abc import Mapping, Sequence
from typing import Annotated, Any, Protocol

from inmanta import plugins
from inmanta.execute.proxy import DynamicProxy
from inmanta.plugins import plugin, ModelType
from inmanta.references import Reference
from inmanta_plugins.refs import dc


type Entity = Annotated[Any, ModelType["std::Entity"]]


class Container[T](Protocol):
    value: T


type ListContainer = Annotated[Container[Sequence[str]], ModelType["refs::ListContainer"]]
type DictContainer = Annotated[Container[Mapping[str, object]], ModelType["refs::DictContainer"]]


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
    for i in range(len(l)):
        l[i]


@plugin
def iterates_obj_list(l: Sequence[object]) -> None:
    for x in l:
        ...
    for i in range(len(l)):
        l[i]


@plugin
def iterates_str_list(l: Sequence[str]) -> None:
    for x in l:
        assert isinstance(x, str), type(x)
    for i in range(len(l)):
        assert isinstance(l[i], str), type(l[i])


@plugin
def iterates_str_ref_list(l: Sequence[str | Reference[str]]) -> None:
    for x in l:
        assert isinstance(x, (str, Reference)), type(x)
    for i in range(len(l)):
        assert isinstance(l[i], (str, Reference)), type(l[i])


@plugin
def iterates_object_dict(l: Mapping[str, object]) -> None:
    for v in l.values():
        ...
    for k in l.keys():
        l[k]

@plugin
def iterates_object_ref_dict(l: Mapping[str, object | Reference[object]]) -> None:
    for v in l.values():
        ...
    for k in l.keys():
        ...


@plugin
def takes_entity(instance: Entity) -> None:
    assert isinstance(instance, DynamicProxy), type(instance)


@plugin
def takes_dataclass(instance: dc.DataclassABC) -> None:
    assert isinstance(instance, (dc.AllRefsDataclass, dc.NoRefsDataclass, dc.MixedRefsDataclass)), type(instance)


@plugin
def takes_all_refs_dataclass(instance: dc.AllRefsDataclass) -> None:
    assert isinstance(instance, dc.AllRefsDataclass), type(instance)
    assert isinstance(instance.maybe_ref_value, (Reference, str)), type(instance.maybe_ref_value)


@plugin
def takes_no_refs_dataclass(instance: dc.NoRefsDataclass) -> None:
    assert isinstance(instance, dc.NoRefsDataclass), type(instance)
    assert isinstance(instance.non_ref_value, str), type(instance.non_ref_value)


@plugin
def takes_mixed_refs_dataclass(instance: dc.MixedRefsDataclass) -> None:
    assert isinstance(instance, dc.MixedRefsDataclass), type(instance)
    assert isinstance(instance.maybe_ref_value, (Reference, str)), type(instance.maybe_ref_value)
    assert isinstance(instance.non_ref_value, str), type(instance.non_ref_value)


@plugin
def takes_all_refs_dataclass_ref(instance: Reference[dc.AllRefsDataclass]) -> None:
    assert isinstance(instance, Reference), type(instance)


@plugin
def takes_no_refs_dataclass_ref(instance: Reference[dc.NoRefsDataclass]) -> None:
    assert isinstance(instance, Reference), type(instance)


@plugin
def takes_mixed_refs_dataclass_ref(instance: Reference[dc.MixedRefsDataclass]) -> None:
    assert isinstance(instance, Reference), type(instance)


@plugin
def takes_all_refs_dataclass_or_ref(instance: dc.AllRefsDataclass | Reference[dc.AllRefsDataclass]) -> None:
    assert isinstance(instance, (dc.AllRefsDataclass, Reference)), type(instance)


@plugin
def takes_no_refs_dataclass_or_ref(instance: dc.NoRefsDataclass | Reference[dc.NoRefsDataclass]) -> None:
    assert isinstance(instance, (dc.NoRefsDataclass, Reference)), type(instance)


@plugin
def takes_mixed_refs_dataclass_or_ref(instance: dc.MixedRefsDataclass | Reference[dc.MixedRefsDataclass]) -> None:
    assert isinstance(instance, (dc.MixedRefsDataclass, Reference)), type(instance)


@plugin
def read_entity_value(instance: Entity) -> None:
    instance.maybe_ref_value  # expected to fail iff it's a reference
    return None


@plugin
def read_entity_ref_value(instance: Entity) -> None:
    plugins.allow_reference_attributes(instance).maybe_ref_value
    return None


# TODO: add a test case
# TODO: same with dict
# TODO: same with allow_references()
@plugin
def read_entity_list_value(instance: ListContainer) -> None:
    for x in instance.value:
        assert isinstance(x, str), type(x)
    for i in range(len(instance.value)):
        assert isinstance(instance.value[i], str), type(instance.value[i])


@plugin
def read_entity_list_head(instance: ListContainer) -> None:
    assert isinstance(instance.value[0], str), type(instance.value[i])


@plugin
def read_entity_dict_value(instance: DictContainer) -> None:
    for v in instance.value.values():
        assert isinstance(v, str), type(v)
    for k in instance.value.keys():
        assert isinstance(instance.value[k], str), type(instance.value[k])


@plugin
def read_entity_dict_mykey(instance: DictContainer) -> None:
    assert isinstance(instance.value["mykey"], str), type(instance.value["mykey"])
