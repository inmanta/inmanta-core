from inmanta.plugins import plugin

print("#loading inmanta_plugins.submodule#")


@plugin
def test() -> "string":
    return "test"
