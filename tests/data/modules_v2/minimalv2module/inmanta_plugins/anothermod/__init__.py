from inmanta.plugins import plugin


# Dummy change
@plugin("flag_plugin")
def flag_plugin(message: "string"):
    print(message)


def triple_string(message: str) -> str:
    return message * 3
