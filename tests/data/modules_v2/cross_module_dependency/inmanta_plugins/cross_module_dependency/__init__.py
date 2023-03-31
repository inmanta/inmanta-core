from inmanta.plugins import plugin
from inmanta_plugins.anothermod import triple_string


@plugin("print_message")
def print_message(message: "string"):
    print(message)


@plugin("call_to_triple_from_another_mod")
def call_to_triple_from_another_mod(message: "string"):
    print(triple_string(message))
