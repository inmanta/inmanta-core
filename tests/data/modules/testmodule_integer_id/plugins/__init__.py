"""
    Copyright 2023 Inmanta
    Contact: code@inmanta.com
    License: Apache 2.0
"""

from inmanta.agent.handler import (
    CRUDHandler,
    HandlerContext,
    provider,
)
from inmanta.resources import (
    PurgeableResource,
    resource,
)


@resource("testmodule_integer_id::Test", agent="agent", id_attribute="id_attr")
class TestResource(PurgeableResource):
    fields = ("id_attr",)


@provider("testmodule_integer_id::Test", name="null")
class TestHandler(CRUDHandler):
    def read_resource(self, ctx: HandlerContext, resource: PurgeableResource) -> None:
        return

    def create_resource(self, ctx: HandlerContext, resource: PurgeableResource) -> None:
        ctx.set_created()

    def delete_resource(self, ctx: HandlerContext, resource: PurgeableResource) -> None:
        ctx.set_purged()

    def update_resource(self, ctx: HandlerContext, changes: dict, resource: PurgeableResource) -> None:
        ctx.set_updated()
