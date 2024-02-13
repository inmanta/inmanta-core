"""
    Inmanta LSM

    :copyright: 2020 Inmanta
    :contact: code@inmanta.com
    :license: Inmanta EULA
"""

import os
from typing import Any, Optional

import inmanta_plugins.lsm.allocation as lsm
import psycopg2
from inmanta_plugins.lsm.allocation import (
    AllocationContext,
    ExternalAttributeAllocator,
    T,
)
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


class PGRouterResolver(ExternalAttributeAllocator[T]):
    def __init__(self, attribute: str, id_attribute: str) -> None:
        super().__init__(attribute, id_attribute)
        self.conn = None
        self.database = None

    def pre_allocate(self):
        """Connect to postgresql"""
        host = os.environ.get("db_host", "localhost")
        port = os.environ.get("db_port")
        user = os.environ.get("db_user")
        self.database = os.environ.get("db_name", "allocation_db")
        self.conn = psycopg2.connect(
            host=host, port=port, user=user, dbname=self.database
        )
        self.conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    def post_allocate(self) -> None:
        """Close connection"""
        self.conn.close()

    def needs_allocation(
        self, ctx: AllocationContext, instance: dict[str, Any]
    ) -> bool:
        attribute_not_yet_allocated = super().needs_allocation(ctx, instance)
        id_attribute_changed = self._id_attribute_changed(instance)
        return attribute_not_yet_allocated or id_attribute_changed

    def _id_attribute_changed(self, instance: dict[str, Any]) -> bool:
        if instance["candidate_attributes"] and instance["active_attributes"]:
            return instance["candidate_attributes"].get(self.id_attribute) != instance[
                "active_attributes"
            ].get(self.id_attribute)
        return False

    def _get_value_from_result(self, result: Optional[tuple[T]]) -> Optional[T]:
        if result and result[0]:
            return result[0]
        return None

    def allocate_for_attribute(self, id_attribute_value: Any) -> T:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT mgmt_ip FROM routers WHERE name=%s", (id_attribute_value,)
            )
            result = cursor.fetchone()
            allocated_value = self._get_value_from_result(result)
            if allocated_value:
                return allocated_value
            raise Exception("No ip address found for %s", str(id_attribute_value))


lsm.AllocationSpec(
    "allocate_for_virtualwire",
    PGRouterResolver(id_attribute="router_a", attribute="router_a_mgmt_ip"),
    PGRouterResolver(id_attribute="router_z", attribute="router_z_mgmt_ip"),
    lsm.LSM_Allocator(
        attribute="vni", strategy=lsm.AnyUniqueInt(lower=50000, upper=70000)
    ),
)
