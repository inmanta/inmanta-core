"""
Copyright 2019 Inmanta

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Contact: code@inmanta.com
"""

from typing import Mapping

from inmanta import const
from inmanta.types import BaseModel as BaseModel
from inmanta.types import ResourceIdStr as ResourceIdStr


class Discrepancy(BaseModel):
    """
    Records a discrepancy between the state as persisted in the database and
    the in-memory state in the scheduler. Either model-wide when no
    resource id is specified (e.g. when model versions are mismatched)
    or for a specific resource.

    :param rid: If set, this discrepancy is specific to this resource.
        If left unset, this discrepancy is not specific to any particular resource.
    :param field: If set, specifies on which field this discrepancy was detected.
        If left unset, and a rid is specified, the discrepancy was detected on the
        resource level i.e. it is missing from either the db or the scheduler.
    :param expected: User-facing message denoting the expected state (i.e. as persisted
        in the DB).
    :param actual: User-facing message denoting the actual state (i.e. in-memory state
        in the scheduler).

    """

    rid: ResourceIdStr | None
    field: str | None
    expected: str
    actual: str


class SchedulerStatusReport(BaseModel):
    """
    Status report for the scheduler self-check

    :param scheduler_state: In-memory representation of the resources in the scheduler
    :param db_state: Desired state of the resources as persisted in the database
    :param discrepancies: Discrepancies between the in-memory representation of the resources
        and their state in the database.
    """

    # Can't type properly because of current module structure
    scheduler_state: Mapping[ResourceIdStr, object]  # "True" type is deploy.state.ResourceState
    db_state: Mapping[ResourceIdStr, object]  # "True" type is deploy.state.ResourceIntent
    resource_states: Mapping[ResourceIdStr, const.ResourceState]
    discrepancies: list[Discrepancy] | dict[ResourceIdStr, list[Discrepancy]]


class DataBaseReport(BaseModel):
    """
    :param max_pool: maximal pool size
    :param free_pool: number of connections not in use in the pool
    :param open_connections: number of connections currently open
    :param free_connections: number of connections currently open and not in use
    :param pool_exhaustion_time: nr of seconds since start we observed the pool to be exhausted
    """

    connected: bool
    database: str
    host: str
    max_pool: int
    free_pool: int
    open_connections: int
    free_connections: int
    pool_exhaustion_time: float

    def __add__(self, other: "DataBaseReport") -> "DataBaseReport":
        if not isinstance(other, DataBaseReport):
            return NotImplemented
        if other.database != self.database:
            return NotImplemented
        if other.host != self.host:
            return NotImplemented
        return DataBaseReport(
            connected=self.connected and other.connected,
            database=self.database,
            host=self.host,
            max_pool=self.max_pool + other.max_pool,
            free_pool=self.free_pool + other.free_pool,
            open_connections=self.open_connections + other.open_connections,
            free_connections=self.free_connections + other.free_connections,
            pool_exhaustion_time=self.pool_exhaustion_time + other.pool_exhaustion_time,
        )
