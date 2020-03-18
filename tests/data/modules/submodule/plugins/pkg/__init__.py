from inmanta.plugins import plugin


@plugin
def test_pkg() -> "string":
    return "test_pkg"
