from collections.abc import Mapping, Sequence
from typing import Annotated, Any, Optional, Protocol

from inmanta import plugins
from inmanta.execute.proxy import DynamicProxy, SequenceProxy, DictProxy
from inmanta.plugins import plugin, ModelType
from inmanta.references import Reference
from inmanta_plugins.refs import dc

type Entity = Annotated[Any, ModelType["std::Entity"]]


class Container[T](Protocol):
    value: T


type ListContainer = Annotated[Container[Sequence[str]], ModelType["refs::ListContainer"]]
type DictContainer = Annotated[Container[Mapping[str, object]], ModelType["refs::DictContainer"]]


@plugin
def takes_obj(v: object) -> None: ...


@plugin
def iterates_obj(v: object) -> None:
    for x in v:  # type: ignore
        ...


@plugin
def takes_obj_ref(v: object | Reference) -> None: ...


@plugin
def takes_obj_ref_only(v: Reference) -> None:
    assert isinstance(v, Reference)


@plugin
def takes_str(v: str) -> None: ...


@plugin
def takes_str_ref(v: str | Reference[str]) -> None: ...


@plugin
def takes_complex_union_or_ref(v: int | str | None | Reference[str | None]) -> None:
    """
    Takes a complex union that allows references, but not to the exact same types.
    """
    ...


@plugin
def takes_union_with_dc(v: Entity | Sequence[Optional[Entity]] | Mapping[str, Entity] | dc.AllRefsDataclass) -> None:
    """
    Takes a union that includes a dataclass (i.e. the union has a custom to_python)
    """
    all_values = v if isinstance(v, SequenceProxy) else v.values() if isinstance(v, DictProxy) else [v]
    for x in all_values:
        x.non_ref_value


@plugin
def takes_union_of_refs(v: Reference[bool] | Reference[str]) -> None: ...


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
def iterates_object_ref_dict(l: Mapping[str, object | Reference]) -> None:
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
    assert isinstance(instance.maybe_ref_value, str), type(instance.maybe_ref_value)


@plugin
def read_entity_ref_value(instance: Entity) -> None:
    plugins.allow_reference_values(instance).maybe_ref_value


@plugin
def read_list_entity_value(instances: Sequence[Entity]) -> None:
    for instance in instances:
        assert isinstance(instance.maybe_ref_value, str), type(instance.maybe_ref_value)


@plugin
def read_list_entity_ref_value(instances: Sequence[Entity]) -> None:
    for instance in instances:
        plugins.allow_reference_values(instance).maybe_ref_value


@plugin
def read_entity_list_value(instance: ListContainer) -> None:
    for x in instance.value:
        assert isinstance(x, str), type(x)
    for i in range(len(instance.value)):
        assert isinstance(instance.value[i], str), type(instance.value[i])


@plugin
def read_entity_list_value_or_ref(instance: ListContainer) -> None:
    with_refs = plugins.allow_reference_values(instance.value)
    for x in with_refs:
        ...
    for i in range(len(instance.value)):
        with_refs[i]


@plugin
def read_entity_list_value_allow_references_single_level(instance: ListContainer) -> None:
    """
    Sets allow_reference_values() on the instance level.
    Test should assert that this does not allow references on the level below it
    """
    with_refs = plugins.allow_reference_values(instance)
    for x in with_refs.value:
        assert isinstance(x, str), type(x)
    for i in range(len(instance.value)):
        assert isinstance(with_refs.value[i], str), type(with_refs.value[i])


@plugin
def read_entity_list_head(instance: ListContainer) -> None:
    assert isinstance(instance.value[0], str), type(instance.value[0])


@plugin
def read_entity_dict_value(instance: DictContainer) -> None:
    for v in instance.value.values():
        assert isinstance(v, str), type(v)
    for k in instance.value.keys():
        assert isinstance(instance.value[k], str), type(instance.value[k])


@plugin
def read_entity_dict_value_or_ref(instance: DictContainer) -> None:
    with_refs = plugins.allow_reference_values(instance.value)
    for v in with_refs.values():
        ...
    for k in instance.value.keys():
        with_refs[k]


@plugin
def read_entity_dict_mykey(instance: DictContainer) -> None:
    assert isinstance(instance.value["mykey"], str), type(instance.value["mykey"])


@plugin
def inheritance_return_specific() -> dc.DataclassABC:
    return dc.NoRefsDataclass()


@plugin
def inheritance_return_specific_ref() -> Reference[dc.DataclassABC]:
    return dc.NoRefsDataclassReference()


@plugin
def returns_entity_list(instance: ListContainer) -> list[str]:
    return instance.value


@plugin
def returns_entity_ref_list(instance: ListContainer) -> list[str | Reference[str]]:
    return instance.value


@plugin
def allow_references_on_non_proxy() -> None:
    plugins.allow_reference_values([])


@plugin
def bool_on_reference(v: Reference) -> None:
    if v:
        ...


@plugin
def str_on_reference(v: Reference) -> str:
    # test references all override __str__, defeating the purpose of this test if we call str() directly
    return Reference.__str__(v)


@plugin
def repr_on_reference(v: Reference) -> str:
    # test references all override __str__, defeating the purpose of this test if we call str() directly
    return Reference.__repr__(v)
