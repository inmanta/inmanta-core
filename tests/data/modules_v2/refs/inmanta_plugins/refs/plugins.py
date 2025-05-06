from collections.abc import Sequence
from typing import Annotated, Any

from inmanta.plugins import plugin, ModelType
from inmanta.references import Reference
from inmanta_plugins import refs


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
        assert isinstance(x, str)


@plugin
def iterates_str_ref_list(l: Sequence[str | Reference[str]]) -> None:
    for x in l:
        assert isinstance(x, (str, Reference))


# TODO: naming etc
@plugin
def read_entity_value(instance: Entity) -> str:
    breakpoint()
    return instance.non_ref_value


@plugin
def read_dataclass_value(instance: refs.Test) -> None:
    failed_read = instance.non_ref_value
    return None


@plugin
def read_dataclass_ref_value(instance: refs.Test | Reference[refs.Test]) -> None:
    # TODO
    ...
    #failed_read = instance.non_ref_value
    #return None
