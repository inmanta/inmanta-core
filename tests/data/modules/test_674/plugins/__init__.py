from inmanta.plugins import plugin


@plugin
def test_nullable(param: "string?") -> "bool":
    return True


@plugin
def test_not_nullable(param: "string") -> "bool":
    return True


@plugin
def test_nullable_list(param: "number[]?") -> "bool":
    return True


@plugin
def test_not_nullable_list(param: "number[]") -> "bool":
    return True


@plugin
def test_returns_none() -> "string?":
    return None
