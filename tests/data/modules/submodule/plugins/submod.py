from inmanta.plugins import plugin


@plugin
def test_submod() -> "string":
    return "test_submod"
