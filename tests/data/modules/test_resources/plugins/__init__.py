from inmanta.resources import (
    Resource,
    resource,
)


@resource("test_resources::Resource", agent="agent", id_attribute="key")
class Res(Resource):
    fields = ("agent", "key", "value")
