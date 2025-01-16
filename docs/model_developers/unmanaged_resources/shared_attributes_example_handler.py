import re
from collections import abc
from typing import Optional

import pydantic

from inmanta import resources
from inmanta.types import ResourceIdStr
from inmanta.agent.handler import provider, DiscoveryHandler, HandlerContext, CRUDHandler
from inmanta.resources import resource, DiscoveryResource, PurgeableResource


class InterfaceBase:
    fields = ("host", "username", "password")

    host: str
    username: str
    password: str

    @staticmethod
    def get_host(exporter, resource):
        return resource.host.name

    @staticmethod
    def get_username(exporter, resource):
        return resource.credentials.username

    @staticmethod
    def get_password(exporter, resource):
        return resource.credentials.password


@resource("my_module::Interface", agent="host.name", id_attribute="name")
class Interface(InterfaceBase, PurgeableResource):
    fields = ("name", "ip_address")

    name: str
    ip_address: str


@resource("my_module::InterfaceDiscovery", agent="host.name", id_attribute="host")
class InterfaceDiscovery(InterfaceBase, DiscoveryResource):
    fields = ("name_filter",)

    name_filter: Optional[str]


class UnmanagedInterface(pydantic.BaseModel):
    """
    Datastructure used by the InterfaceDiscoveryHandler to return the attributes
    of the discovered resources.
    """

    host: str
    interface_name: str
    ip_address: str


class Authenticator:
    """
    Helper class that handles the authentication to the remote host.
    """

    def login(self, credentials: InterfaceBase) -> None:
        raise NotImplementedError()

    def logout(self, credentials: InterfaceBase) -> None:
        raise NotImplementedError()


@provider("my_module::Interface", name="interface_handler")
class InterfaceHandler(Authenticator, CRUDHandler[Interface]):
    """
    Handler for the interfaces managed by the orchestrator.
    """

    def pre(self, ctx: HandlerContext, resource: Interface) -> None:
        self.login(resource)

    def post(self, ctx: HandlerContext, resource: Interface) -> None:
        self.logout(resource)

    def read_resource(self, ctx: HandlerContext, resource: Interface) -> None:
        raise NotImplementedError()

    def create_resource(self, ctx: HandlerContext, resource: Interface) -> None:
        raise NotImplementedError()

    def delete_resource(self, ctx: HandlerContext, resource: Interface) -> None:
        raise NotImplementedError()

    def update_resource(self, ctx: HandlerContext, changes: dict, resource: Interface) -> None:
        raise NotImplementedError()


@provider("my_module::InterfaceDiscovery", name="interface_discovery_handler")
class InterfaceDiscoveryHandler(Authenticator, DiscoveryHandler[InterfaceDiscovery, UnmanagedInterface]):

    def pre(self, ctx: HandlerContext, resource: InterfaceDiscovery) -> None:
        self.login(resource)

    def post(self, ctx: HandlerContext, resource: InterfaceDiscovery) -> None:
        self.logout(resource)

    def discover_resources(
        self, ctx: HandlerContext, discovery_resource: InterfaceDiscovery
    ) -> abc.Mapping[ResourceIdStr, UnmanagedInterface]:
        """
        Entrypoint that is called by the agent when the discovery resource is deployed.
        """
        discovered: abc.Iterator[UnmanagedInterface] = (
            UnmanagedInterface(**attributes)
            for attributes in self._get_discovered_interfaces(discovery_resource)
            if discovery_resource.name_filter is None or re.match(discovery_resource.name_filter, attributes["interface_name"])
        )
        return {
            resources.Id(
                entity_type="my_module::Interface",
                agent_name=res.host,
                attribute="interface_name",
                attribute_value=res.interface_name,
            ).resource_str(): res
            for res in discovered
        }

    def _get_discovered_interfaces(self, discovery_resource: InterfaceDiscovery) -> list[dict[str, object]]:
        """
        A helper method that contains the logic to discover the unmanaged interfaces in the network.
        It returns a list of dictionaries where each dictionary contains the attributes of a discovered interface.
        """
        raise NotImplementedError()
