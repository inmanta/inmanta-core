"""
    Inmanta LSM

    :copyright: 2020 Inmanta
    :contact: code@inmanta.com
    :license: Inmanta EULA
"""

import os
from typing import Optional
from uuid import UUID

import inmanta_plugins.lsm.allocation as lsm
import psycopg2
from inmanta_plugins.lsm.allocation import ExternalServiceIdAllocator, T
from psycopg2.extensions import ISOLATION_LEVEL_SERIALIZABLE


class PGServiceIdAllocator(ExternalServiceIdAllocator[T]):
    def __init__(self, attribute: str) -> None:
        super().__init__(attribute)
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
        self.conn.set_isolation_level(ISOLATION_LEVEL_SERIALIZABLE)

    def post_allocate(self) -> None:
        """Close connection"""
        self.conn.close()

    def _get_value_from_result(self, result: Optional[tuple[T]]) -> Optional[T]:
        if result and result[0]:
            return result[0]
        return None

    def allocate_for_id(self, serviceid: UUID) -> T:
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


lsm.AllocationSpec(
    "allocate_vlan",
    PGServiceIdAllocator(
        attribute="vlan_id",
    ),
)
