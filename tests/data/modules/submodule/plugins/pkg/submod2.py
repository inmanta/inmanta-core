from inmanta.plugins import plugin


@plugin
def test_submod2() -> "string":
    return "test_submod2"
