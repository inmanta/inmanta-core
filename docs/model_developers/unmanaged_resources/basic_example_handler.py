import re
from collections import abc

import pydantic

from inmanta import resources
from inmanta.types import ResourceIdStr
from inmanta.agent.handler import provider, DiscoveryHandler, HandlerContext
from inmanta.resources import resource, DiscoveryResource


@resource("my_module::InterfaceDiscovery", agent="host.name", id_attribute="host")
class InterfaceDiscovery(DiscoveryResource):
    fields = ("host", "name_filter")

    host: str
    name_filter: str

    @staticmethod
    def get_host(exporter, resource):
        return resource.host.name


class UnmanagedInterface(pydantic.BaseModel):
    """
    Datastructure used by the InterfaceDiscoveryHandler to return the attributes
    of its discovered resources.
    """

    host: str
    interface_name: str
    ip_address: str


@provider("my_module::InterfaceDiscovery", name="interface_discovery_handler")
class InterfaceDiscoveryHandler(DiscoveryHandler[InterfaceDiscovery, UnmanagedInterface]):
    def discover_resources(
        self, ctx: HandlerContext, discovery_resource: InterfaceDiscovery
    ) -> dict[ResourceIdStr, UnmanagedInterface]:
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
        It returns a list of dictionaries where each dictionary contains the attributes of an unmanaged resource.
        """
        raise NotImplementedError()
