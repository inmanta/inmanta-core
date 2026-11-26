from inmanta.plugins import plugin

print("#loading inmanta_plugins.submodule.submod#")


@plugin
def test_submod() -> "string":
    return "test_submod"
