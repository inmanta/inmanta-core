from inmanta.plugins import Context, deprecated, plugin


@plugin("print")
def printf(message: "any"):
    """
    Print the given message to stdout
    """
    print(message)
