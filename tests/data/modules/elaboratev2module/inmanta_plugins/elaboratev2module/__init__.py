from inmanta.plugins import plugin


@plugin("print_message")
def printf(message: "any"):
    print(message)
