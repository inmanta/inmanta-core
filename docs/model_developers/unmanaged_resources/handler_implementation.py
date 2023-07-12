from collections import abc

import pydantic

from inmanta import resources
from inmanta.agent.handler import provider, DiscoveryHandler, HandlerContext, CRUDHandler
from inmanta.resources import PurgeableResource, resource


class MyResourceProvider:
    fields = ("username", "password")

    username: str
    password: str


@resource("test_model::MyResource", agent="host.name", id_attribute="my_id")
class MyResource(MyResourceProvider, PurgeableResource):
    fields = ("my_id", "value")

    my_id: int
    value: int


# PoC: in practice this id_attribute would require a custom mapping or attribute
@resource("test_model::MyDiscoveryResource", agent="host.name", id_attribute="host.name")
class MyDiscoveryResource(MyResourceProvider):
    fields = ()


class MyHelper:
    """
    Helper class for shared behavior between managed resource handler and discovery handler.
    Since this is a shared class, it doesn't operate on `MyResource` or `MyDiscoveryResource`
    but on their shared parent `MyResourceProvider`.
    """
    def authenticate(self, provider: MyResourceProvider) -> None:
        if provider.password == "4dm1n":
            print(f"hello {provider.username}")

    def complex_transformation(self, x: int) -> int:
        return 2 * x


@provider("test_model::MyResource", name="my_resource_handler")
class MyHandler(MyHelper, CRUDHandler[MyResource]):
    """
    Normal CRUD handler for the already managed MyResource instances.
    """
    def _read_value_for_id(self, my_id: int) -> int:
        ...

    def read_resource(self, ctx: HandlerContext, resource: MyResource) -> None:
        # in practice this would likely be called in `pre`
        self.authenticate(resource)
        resource.value = self.complex_transformation(
            self._read_value_for_id(resource.my_id)
        )

    def create_resource(self, ctx: HandlerContext, resource: MyResource) -> None:
        ...

    def delete_resource(self, ctx: HandlerContext, resource: MyResource) -> None:
        ...

    def update_resource(
        self, ctx: HandlerContext, changes: dict, resource: MyResource
    ) -> None:
        ...


class MyUnmanagedResource(pydantic.BaseModel):
    my_id: int
    value: int


@provider("test_model::MyDiscoveryResource", name="my_discoveryresource_handler")
class MyDiscoveryHandler(MyHelper, DiscoveryHandler[MyDiscoveryResource, MyUnmanagedResource]):
    """
    DiscoveryHandler: deploys instances of MyDiscoveryResource and reports found MyUnmanagedResource to the server.

    The DiscoveryHandler ABC is generic in both the handler's resource type and the type it reports to the server.
    The second has to be serializable.
    """
    def _list_resources(self) -> list[tuple[int, int]]:
        ...

    def discover_resources(
        self, ctx: HandlerContext, discovery_resource: MyDiscoveryResource
    ) -> abc.Mapping[str, MyUnmanagedResource]:
        # in practice this would likely be called in `pre`
        self.authenticate(discovery_resource)
        discovered: abc.Iterator[MyUnmanagedResource] = (
            MyUnmanagedResource(my_id=my_id, value=self.complex_transformation(value))
            for my_id, value in self._list_resources()
        )
        return {
            resources.Id(
                entity_type="my_resource",
                agent_name=self.id.agent_name,
                attribute="my_id",
                attribute_value=str(res.my_id),
            ).resource_str(): res
            for res in discovered
        }
