from inmanta import resources


@resources.resource("many_dependencies::Test", agent="agent", id_attribute="name")
class Test(resources.PurgeableResource):
    """
    This class represents a service on a system.
    """

    fields = ("name", "agent")
