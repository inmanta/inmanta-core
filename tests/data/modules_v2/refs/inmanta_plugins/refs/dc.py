import dataclasses
from inmanta.agent.handler import LoggerABC
from inmanta.plugins import plugin
from inmanta.references import reference, Reference


@dataclasses.dataclass(frozen=True, kw_only=True)
class DataclassABC: ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class NoRefsDataclass(DataclassABC):
    non_ref_value: str = "Hello World!"


@dataclasses.dataclass(frozen=True, kw_only=True)
class AllRefsDataclass(DataclassABC):
    maybe_ref_value: str | Reference[str]


@dataclasses.dataclass(frozen=True, kw_only=True)
class MixedRefsDataclass(AllRefsDataclass, NoRefsDataclass): ...


@reference("refs::dc::NoRefsDataclassReference")
class NoRefsDataclassReference(Reference[NoRefsDataclass]):
    def __init__(self) -> None:
        """
        :param non_ref_value: The value
        """
        super().__init__()

    def resolve(self, logger: LoggerABC) -> NoRefsDataclass:
        return NoRefsDataclassReference()

    def __repr__(self) -> str:
        return f"NoRefsDataclassReference()"


class AllRefsDataclassReferenceABC[D: AllRefsDataclass](Reference[D]):
    def __init__(self, maybe_ref_value: str | Reference[str], *, dc_type: type[D]) -> None:
        super().__init__()
        self._dc_type: type[D] = dc_type
        self.maybe_ref_value: str | Reference[str] = maybe_ref_value

    def resolve(self, logger: LoggerABC) -> D:
        return self._dc_type(maybe_ref_value=self.resolve_other(self.maybe_ref_value, logger))

    def __repr__(self):
        return f"{self._dc_type.__name__}Reference({self.maybe_ref_value!r})"


@reference("refs::dc::AllRefsDataclassReference")
class AllRefsDataclassReference(AllRefsDataclassReferenceABC[AllRefsDataclass], Reference[AllRefsDataclass]):
    def __init__(self, maybe_ref_value: str | Reference[str]) -> None:
        super().__init__(maybe_ref_value, dc_type=AllRefsDataclass)


@reference("refs::dc::MixedRefsDataclassReference")
class MixedRefsDataclassReference(AllRefsDataclassReferenceABC[MixedRefsDataclass], Reference[MixedRefsDataclass]):
    def __init__(self, maybe_ref_value: str | Reference[str]) -> None:
        super().__init__(maybe_ref_value, dc_type=MixedRefsDataclass)


@plugin
def create_no_refs_dataclass_reference() -> NoRefsDataclassReference:
    return NoRefsDataclassReference()


@plugin
def create_all_refs_dataclass_reference(maybe_ref_value: str | Reference[str]) -> AllRefsDataclassReference:
    return AllRefsDataclassReference(maybe_ref_value)


@plugin
def create_mixed_refs_dataclass_reference(maybe_ref_value: str | Reference[str]) -> MixedRefsDataclassReference:
    return MixedRefsDataclassReference(maybe_ref_value)
