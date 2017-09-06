from inmanta.execute.util import Unknown
from inmanta.plugins import plugin


@plugin
def unknown() -> "any":
    return Unknown(None)

@plugin
def length(string:"string") -> "number":
    return len(string)

@plugin
def empty(string:"string") -> "bool":
    return len(string)==0