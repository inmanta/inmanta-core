from inmanta.plugins import plugin


@plugin
def list_id(listin: "plugin_typing::Item[]") -> "plugin_typing::Item[]":
    return listin


@plugin
def unwrap_list(listin: "plugin_typing::Item[]") -> "plugin_typing::Item[]":
    return [x for x in listin]


@plugin
def makelist(ins: "string") -> "string[]":
    return [ins]


@plugin
def badtype(listin: "plugin_typing::Item[]") -> "plugin_typing::Item[]":
    return ["a", "b", "c"]
