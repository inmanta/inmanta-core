"""
    Inmanta LSM

    :copyright: 2020 Inmanta
    :contact: code@inmanta.com
    :license: Inmanta EULA
"""

import os
from typing import Optional
from uuid import UUID

import psycopg2
from inmanta.agent import handler
from inmanta.agent.handler import CRUDHandlerGeneric as CRUDHandler
from inmanta.agent.handler import ResourcePurged, provider
from inmanta.resources import PurgeableResource, resource
from inmanta_plugins.lsm.allocation import AllocationSpec, ExternalServiceIdAllocator
from psycopg2.extensions import ISOLATION_LEVEL_SERIALIZABLE


class PGServiceIdAllocator(ExternalServiceIdAllocator[int]):
    def __init__(self, attribute: str) -> None:
        super().__init__(attribute)
        self.conn = None
        self.database = None

    def pre_allocate(self) -> None:
        """Connect to postgresql"""
        host = os.environ.get("db_host", "localhost")
        port = os.environ.get("db_port")
        user = os.environ.get("db_user")
        self.database = os.environ.get("db_name", "allocation_db")
        self.conn = psycopg2.connect(
            host=host, port=port, user=user, dbname=self.database
        )
        self.conn.set_isolation_level(ISOLATION_LEVEL_SERIALIZABLE)

    def post_allocate(self) -> None:
        """Close connection"""
        self.conn.close()

    def _get_value_from_result(self, result: Optional[tuple[int]]) -> Optional[int]:
        if result and result[0]:
            return result[0]
        return None

    def allocate_for_id(self, serviceid: UUID) -> int:
        """Allocate in transaction"""
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT allocated_value FROM allocation WHERE attribute=%s AND owner=%s",
                (self.attribute, serviceid),
            )
            result = cursor.fetchone()
            allocated_value = self._get_value_from_result(result)
            if allocated_value:
                return allocated_value
            cursor.execute(
                "SELECT max(allocated_value) FROM allocation where attribute=%s",
                (self.attribute,),
            )
            result = cursor.fetchone()
            current_max_value = self._get_value_from_result(result)
            allocated_value = current_max_value + 1 if current_max_value else 1
            cursor.execute(
                "INSERT INTO allocation (attribute, owner, allocated_value) VALUES (%s, %s, %s)",
                (self.attribute, serviceid, allocated_value),
            )
            self.conn.commit()
            return allocated_value

    def has_allocation_in_inventory(self, serviceid: UUID) -> bool:
        """
        Check whether a VLAN ID is allocated by the service instance with the given id.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT allocated_value FROM allocation WHERE attribute=%s AND owner=%s",
                (self.attribute, serviceid),
            )
            result = cursor.fetchone()
            allocated_value = self._get_value_from_result(result)
            if allocated_value:
                return True
            return False

    def de_allocate(self, serviceid: UUID) -> None:
        """
        De-allocate the VLAN ID allocated by the service instance with the given id.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM allocation WHERE attribute=%s AND owner=%s",
                (self.attribute, serviceid),
            )
            self.conn.commit()


@resource("vlan_assignment::PGAllocation", agent="agent", id_attribute="service_id")
class PGAllocationResource(PurgeableResource):
    fields = ("attribute", "service_id")


@provider("vlan_assignment::PGAllocation", name="pgallocation")
class PGAllocation(CRUDHandler[PGAllocationResource]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._allocator = PGServiceIdAllocator(attribute="vlan_id")

    def pre(self, ctx: handler.HandlerContext, resource: PGAllocationResource) -> None:
        self._allocator.pre_allocate()

    def post(self, ctx: handler.HandlerContext, resource: PGAllocationResource) -> None:
        self._allocator.post_allocate()

    def read_resource(
        self, ctx: handler.HandlerContext, resource: PGAllocationResource
    ) -> None:
        if not self._allocator.has_allocation_in_inventory(resource.service_id):
            raise ResourcePurged()

    def delete_resource(
        self, ctx: handler.HandlerContext, resource: PGAllocationResource
    ) -> None:
        self._allocator.de_allocate(resource.service_id)


AllocationSpec("allocate_vlan", PGServiceIdAllocator(attribute="vlan_id"))
