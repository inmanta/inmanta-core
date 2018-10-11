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


@plugin(allow_unknown=True)
def is_uknown(inp: "any") -> "bool":
    return isinstance(inp, Unknown)


@plugin(allow_unknown=True)
def do_uknown(inp: "any") -> "string":
    return "XX"


counter = defaultdict(lambda: 0)


@plugin
def once(string: "string") -> "number":
    prev = counter[string]
    counter[string] = prev + 1
    return prev
