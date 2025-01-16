"""
    Inmanta LSM, example for custom partial compile

    :copyright: 2024 Inmanta
    :contact: code@inmanta.com
    :license: Inmanta EULA
"""

from inmanta_plugins import lsm
from inmanta_plugins.lsm import partial


class TunnelSelector(partial.AbstractSelector):

    def select_all(self) -> dict[str, list[dict]]:
        # Collect all port ids we need
        port_ids = set()
        # Collect all tunnel ids we need
        tunnel_ids = set()
        # Go over all instances requested
        for current_instance_id in self.requested_instances:
            # Find the actual instance to find its type
            service_instance = lsm.global_cache.get_instance(
                env=self.env,
                service_entity_name=None,  # We don't know yet
                instance_id=current_instance_id,
                include_terminated=True,
            )
            if service_instance is None:
                raise RuntimeError(
                    f"Can not find any instance with id {current_instance_id} in"
                    f"environment {self.env}"
                )

            # Now we know which service it is
            service_entity_name = service_instance["service_entity"]

            # Make sure our instance is cached
            lsm.global_cache.get_all_instances(
                self.env,
                service_entity_name=service_entity_name,
            )

            if service_entity_name == "tunnel":
                # Get all ports we need now
                for port in self._get_attribute(service_instance, "ports"):
                    port_ids.add(port)
                tunnel_ids.add(current_instance_id)
            elif service_entity_name == "port":
                port_ids.add(current_instance_id)
            else:
                raise Exception(
                    f"This selector is only intended to handle ports and tunnels, but got: {service_entity_name}"
                )
        # Convert ids to instances
        all_selected = {}
        all_selected["port"] = [
            lsm.global_cache.get_instance(
                env=self.env,
                service_entity_name="port",
                instance_id=port_id,
            )
            for port_id in port_ids
        ]
        all_selected["tunnel"] = [
            lsm.global_cache.get_instance(
                env=self.env,
                service_entity_name="tunnel",
                instance_id=tunnel_id,
            )
            for tunnel_id in tunnel_ids
        ]

        return all_selected


lsm.global_cache.set_selector_factory(TunnelSelector)
