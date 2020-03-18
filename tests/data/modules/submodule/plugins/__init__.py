from inmanta.plugins import plugin


@plugin
def test() -> "string":
    return "test"
