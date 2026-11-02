from inmanta.plugins import plugin


@plugin
def test_list(instance: "test_1774::Test") -> "list":
    return [instance]


@plugin
def test_dict(instance: "test_1774::Test") -> "dict":
    return {"instance": instance}
