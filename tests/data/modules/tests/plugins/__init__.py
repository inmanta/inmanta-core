from inmanta.execute.util import Unknown
from inmanta.plugins import plugin


@plugin
def unknown() -> "any":
    return Unknown(None)
