"""
Copyright 2026 Inmanta

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

import uuid
from collections import abc

import asyncpg

from inmanta.server import SLICE_ORCHESTRATION
from inmanta.server.services.orchestrationservice import OrchestrationService
from inmanta.server.services.resourcesetlistener import ResourceSetListener


def resource(key: str, version: int) -> dict[str, object]:
    return {
        "id": f"test::Resource[agent1,key={key}],v={version}",
        "att": "val",
        "send_event": False,
        "purged": False,
        "requires": [],
    }


async def sets_in_version(postgresql_client: asyncpg.Connection, environment: str, version: int) -> dict[str | None, uuid.UUID]:
    records = await postgresql_client.fetch(
        """
        SELECT rs.name, rs.id
        FROM public.resource_set_configuration_model AS rscm
        INNER JOIN public.resource_set AS rs
            ON rs.environment = rscm.environment AND rs.id = rscm.resource_set
        WHERE rscm.environment = $1 AND rscm.model = $2
        """,
        uuid.UUID(environment),
        version,
    )
    return {record["name"]: record["id"] for record in records}


async def test_listener_is_told_which_resource_sets_were_written(
    server, client, environment, clienthelper, postgresql_client: asyncpg.Connection
) -> None:
    """
    A listener is notified of the ids the resource sets were inserted under, and on a partial export only of the sets
    that were actually written.
    """

    class RecordingListener(ResourceSetListener):
        """
        Records every notification, and asserts on the way in that it is handed a usable connection.
        """

        def __init__(self) -> None:
            self.calls: list[tuple[uuid.UUID, int, abc.Set[uuid.UUID]]] = []

        async def resource_sets_written(
            self,
            environment: uuid.UUID,
            model_version: int,
            resource_sets: abc.Set[uuid.UUID],
            *,
            connection: asyncpg.connection.Connection,
        ) -> None:
            assert connection.is_in_transaction()
            self.calls.append((environment, model_version, set(resource_sets)))

    orchestration_service: OrchestrationService = server.get_slice(SLICE_ORCHESTRATION)
    listener = RecordingListener()
    orchestration_service.add_resource_set_listener(listener)

    version = await clienthelper.get_version()
    result = await client.put_version(
        tid=environment,
        version=version,
        # in_shared is left out of resource_sets, which puts it in the shared set
        resources=[resource("in_a", version), resource("in_b", version), resource("in_shared", version)],
        resource_sets={
            "test::Resource[agent1,key=in_a]": "set_a",
            "test::Resource[agent1,key=in_b]": "set_b",
        },
        unknowns=[],
        version_info={},
        module_version_info={},
    )
    assert result.code == 200

    full_sets = await sets_in_version(postgresql_client, environment, version)
    # the shared set, the one without a name, is reported like any other
    assert full_sets.keys() == {None, "set_a", "set_b"}
    assert listener.calls == [(uuid.UUID(environment), version, set(full_sets.values()))]

    result = await client.put_partial(
        tid=environment,
        resources=[resource("in_a", 0)],
        resource_sets={"test::Resource[agent1,key=in_a]": "set_a"},
        unknowns=[],
        version_info={},
        module_version_info={},
    )
    assert result.code == 200
    partial_version = result.result["data"]

    partial_sets = await sets_in_version(postgresql_client, environment, partial_version)
    # set_b was linked to the new version unchanged, so it keeps its id and is not reported.
    assert partial_sets["set_b"] == full_sets["set_b"]
    assert partial_sets["set_a"] != full_sets["set_a"]
    # a partial export carries the shared resources over by exporting them again, so the shared set is written
    # under a new id and reported, even though in_shared did not change.
    assert partial_sets[None] != full_sets[None]
    assert listener.calls[-1] == (
        uuid.UUID(environment),
        partial_version,
        {partial_sets["set_a"], partial_sets[None]},
    )


async def test_failing_listener_aborts_the_export(
    server, client, environment, clienthelper, postgresql_client: asyncpg.Connection
) -> None:
    """
    A listener maintains data derived from the resources, so it is committed with them or not at all: a listener that
    raises takes the export down and leaves no version behind.
    """

    class FailingListener(ResourceSetListener):
        async def resource_sets_written(
            self,
            environment: uuid.UUID,
            model_version: int,
            resource_sets: abc.Set[uuid.UUID],
            *,
            connection: asyncpg.connection.Connection,
        ) -> None:
            raise Exception("this listener cannot do its work")

    orchestration_service: OrchestrationService = server.get_slice(SLICE_ORCHESTRATION)
    orchestration_service.add_resource_set_listener(FailingListener())

    version = await clienthelper.get_version()
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=[resource("in_a", version)],
        resource_sets={"test::Resource[agent1,key=in_a]": "set_a"},
        unknowns=[],
        version_info={},
        module_version_info={},
    )
    assert result.code == 500, result.result

    assert await sets_in_version(postgresql_client, environment, version) == {}
    assert (
        await postgresql_client.fetchval(
            "SELECT count(*) FROM public.configurationmodel WHERE environment = $1 AND version = $2",
            uuid.UUID(environment),
            version,
        )
        == 0
    )
