from inmanta.plugins import plugin


@plugin
def list_id(listin: "test::Item[]") -> "test::Item[]":
    return listin


@plugin
def unwrap_list(listin: "test::Item[]") -> "test::Item[]":
    return [x for x in listin]


@plugin
def makelist(ins: "string") -> "string[]":
    return [ins]


@plugin
def badtype(listin: "test::Item[]") -> "test::Item[]":
    return ["a", "b", "c"]
