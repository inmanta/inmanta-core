from inmanta.plugins import plugin


@plugin
def test(file: "std::WrongName") -> bool:
    return False
