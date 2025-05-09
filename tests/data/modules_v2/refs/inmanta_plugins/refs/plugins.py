from collections.abc import Sequence
from typing import Annotated, Any

from inmanta.plugins import plugin, ModelType
from inmanta.references import Reference
from inmanta_plugins.refs import dc


type Entity = Annotated[Any, ModelType["std::Entity"]]


@plugin
def takes_obj(v: object) -> None:
    ...


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
def iterates_str_list(l: Sequence[str]) -> None:
    for x in l:
        assert isinstance(x, str), type(x)


@plugin
def iterates_str_ref_list(l: Sequence[str | Reference[str]]) -> None:
    for x in l:
        assert isinstance(x, (str, Reference)), type(x)


@plugin
def takes_entity(instance: Entity) -> None:
    ...


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


# TODO: everything below this: check if used
@plugin
def read_entity_value(instance: Entity) -> str:
    return instance.non_ref_value


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
