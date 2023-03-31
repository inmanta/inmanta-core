from inmanta.plugins import plugin


@plugin("print_message")
def print_message(message: "string"):
    print(message)


# TODO remove
@plugin("second_plugin")
def second_plugin(message: "string"):
    print(message)
