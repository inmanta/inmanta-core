from inmanta.plugins import plugin
from inmanta.references import Reference, reference

@reference("references::Concat")
class ConcatReference(Reference[str]):

    def __init__(self, one: str | Reference[str], other: str | Reference[str]) -> None:
        super().__init__()
        self.one = one
        self.other = other

    def resolve(self, logger) -> str:
        # do the actual resolution
        # First resolve the arguments, then concat them
        return self.resolve_other(self.one, logger) + self.resolve_other(self.other, logger)

@plugin
def concat(one: str | Reference[str], other: str | Reference[str]) -> str | Reference[str]:
    # Allow either str or Reference[str]
    # These types are enforced when entering the plugin, so it would not work with just str

    # Only construct the reference when required
    if isinstance(one, Reference) or isinstance(other, Reference):
        return ConcatReference(one, other)

    return one + other
