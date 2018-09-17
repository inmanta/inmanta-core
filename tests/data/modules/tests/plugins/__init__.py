from inmanta.execute.util import Unknown
from inmanta.plugins import plugin
from _collections import defaultdict


@plugin
def unknown() -> "any":
    return Unknown(None)


@plugin
def length(string: "string") -> "number":
    return len(string)


@plugin
def empty(string: "string") -> "bool":
    return len(string) == 0


counter = defaultdict(lambda: 0)


@plugin
def once(string: "string") -> "number":
    prev = counter[string]
    counter[string] = prev + 1
    return prev
