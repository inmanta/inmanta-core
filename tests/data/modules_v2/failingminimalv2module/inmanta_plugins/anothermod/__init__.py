from inmanta.plugins import plugin


@plugin("flag_plugin")
def flag_plugin(message: "string"):
    print(message)


def triple_string(message: str) -> str:
    return message * 3
