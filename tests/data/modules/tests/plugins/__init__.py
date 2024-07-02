from _collections import defaultdict
from inmanta import resources
from inmanta.execute.proxy import UnknownException
from inmanta.execute.util import Unknown
from inmanta.plugins import PluginException, plugin, Context


@plugin
def unknown() -> "any":
    return Unknown(None)


@plugin
def length(string: "string") -> "int":
    """returns the length of the string"""
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


@plugin
def convert_unknowns(inp: "list", replace: "any") -> "list":
    def convert():
        iterator = iter(inp)
        while True:
            try:
                yield next(iterator)
            except UnknownException:
                yield replace
            except StopIteration:
                break

    return list(convert())


counter = defaultdict(lambda: 0)


@plugin
def resolve_rule_purged_status(
    sources: "list",
) -> "bool":
    for source in sources:
        if len(source.effective_services) == 0:
            return True

    return False


@plugin
def once(string: "string") -> "int":
    prev = counter[string]
    counter[string] = prev + 1
    return prev


@plugin
def get_id(instance: "std::Entity") -> "string":
    return resources.to_id(instance)


class TestPluginException(PluginException):
    def __init__(self, msg):
        super().__init__("Test: " + msg)


@plugin
def raise_exception(message: "string") -> None:
    raise TestPluginException(message)


@plugin
def sum(x: "int", y: "int") -> "int":
    return x + y


@plugin
def context_tester(
    resource: "std::Entity",
    context: Context,
) -> "string":
    # force reschedule
    resource.requires
    # return
    return "test"
