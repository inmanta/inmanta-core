from inmanta.plugins import plugin


@plugin
def some_name() -> "bool":
    return False
