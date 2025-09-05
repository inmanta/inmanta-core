from inmanta import resources


@resources.resource("many_dependencies::Test", agent="agent", id_attribute="name")
class Test(resources.PurgeableResource):
    """
    Dummy test resource.
    """

    fields = ("name", "agent")
