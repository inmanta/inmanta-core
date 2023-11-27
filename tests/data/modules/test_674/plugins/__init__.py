from inmanta.plugins import plugin


@plugin
def test_nullable(param: "string?") -> "bool":
    return True


@plugin
def test_not_nullable(param: "string") -> "bool":
    return True


@plugin
def test_nullable_list(param: "int[]?") -> "bool":
    return True


@plugin
def test_not_nullable_list(param: "int[]") -> "bool":
    return True


@plugin
def test_returns_none() -> "string?":
    return None


@plugin
def test_float_to_int(val1: "float") -> "int":
    return int(val1)


@plugin
def test_int_to_float(val1: "int") -> "float":
    return float(val1)


@plugin
def test_error_float() -> "float":
    return 1
