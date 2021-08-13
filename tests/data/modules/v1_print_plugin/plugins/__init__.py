from inmanta.plugins import plugin


@plugin("print_message")
def print_message(message: "string"):
    print(message)
