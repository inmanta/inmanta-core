"""
    Copyright 2022 Inmanta

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
import datetime
import os
import uuid
from collections import abc
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Type

import asyncpg
import pytest

from inmanta import const, data
from inmanta.data import model


@dataclass
class MockEnum:
    name: object
    value: object


def mock_enum(monkeypatch) -> None:
    enum_meta: Type[Type[Enum]] = type(Enum)
    old_instancecheck: abc.Callable[[Type[Type[Enum]], object], bool] = enum_meta.__instancecheck__
    monkeypatch.setattr(
        # accept MockEnum anywhere any specific enum is expected
        enum_meta,
        "__instancecheck__",
        lambda cls, instance: old_instancecheck(cls, instance) or isinstance(instance, MockEnum),
    )


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), "dumps", "v202208180.sql"))
async def test_enum_shrink(
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]],
    postgresql_client: asyncpg.connection.Connection,
    get_columns_in_db_table: abc.Callable[[str], abc.Awaitable[list[str]]],
    db_environment: data.Environment,
    db_model: data.ConfigurationModel,
    monkeypatch,
) -> None:
    """
    Test the database migration script that removes the `processing_events` value from the resource state enums.
    """

    all_states_pre: abc.Set[str] = {
        "unavailable",
        "skipped",
        "dry",
        "deployed",
        "failed",
        "deploying",
        "available",
        "cancelled",
        "undefined",
        "skipped_for_undefined",
        # include processing_events to verify it gets converted correctly
        "processing_events",
    }
    non_deploying_states_pre = all_states_pre - {"deploying"}

    # allow values not defined in the Python enum
    mock_enum(monkeypatch)
    # simplified ResourceAction insert: allow empty resource_version_id
    monkeypatch.setattr(data.ResourceAction, "insert", data.BaseDocument.insert)

    # inject resource_version_id field for db dump pre-removal
    _get_column_names_and_values = data.Resource._get_column_names_and_values

    def get_column_names_and_values(self):
        result = _get_column_names_and_values(self)
        return ([*result[0], "resource_version_id"], [*result[1], str(uuid.uuid4())])

    monkeypatch.setattr(data.Resource, "_get_column_names_and_values", get_column_names_and_values)

    # Insert some known documents so we can verify correct conversion of existing values
    pre_actions: abc.Mapping[str, uuid.UUID] = {state: uuid.uuid4() for state in all_states_pre}
    pre_resources: abc.Mapping[str, uuid.UUID] = {state: uuid.uuid4() for state in all_states_pre}
    for state, action_id in pre_actions.items():
        action: data.ResourceAction = data.ResourceAction(
            environment=db_environment.id,
            version=db_model.version,
            resource_version_ids=[],
            action_id=action_id,
            action=const.ResourceAction.other,
            started=datetime.datetime.now(),
            status=MockEnum(name=state, value=state),
        )
        await action.insert(connection=postgresql_client)
    for state, resource_id in pre_resources.items():
        non_deploying_state: str = state if state in non_deploying_states_pre else "available"
        resource: data.Resource = data.Resource(
            environment=db_environment.id,
            model=db_model.version,
            # these are only mock resources: use uuid instead of actual valid resource version id
            resource_id=str(resource_id),
            resource_type=model.ResourceType("myresource"),
            resource_id_value=model.ResourceVersionIdStr("notarealidvalue"),
            agent="myagent",
            attribute_hash=None,
            status=MockEnum(name=state, value=state),
            last_non_deploying_status=MockEnum(name=non_deploying_state, value=non_deploying_state),
        )
        await resource.insert(connection=postgresql_client)

    old_enum_id_records_pre: abc.Sequence[asyncpg.Record] = await postgresql_client.fetch(
        """
        SELECT oid as id
        FROM pg_type
        WHERE typname=ANY('{"resourcestate", "non_deploying_resource_state"}')
        """
    )
    assert len(old_enum_id_records_pre) == 2

    # Migrate DB schema
    await migrate_db_from()

    # Assert value conversion after running the DB migration script
    for state, action_id in pre_actions.items():
        action = await data.ResourceAction.get_by_id(action_id, connection=postgresql_client)
        assert action.status == (state if state != "processing_events" else "deploying")
    for state, resource_id in pre_resources.items():
        resource = await data.Resource.get_one(resource_id=str(resource_id), connection=postgresql_client)
        assert resource is not None
        assert resource.status == (state if state != "processing_events" else "deploying")
        assert resource.last_non_deploying_status == (
            state if state in (non_deploying_states_pre - {"processing_events"}) else "available"
        )

    # verify old enum types no longer exist
    old_enums_exist_post: Optional[asyncpg.Record] = await postgresql_client.fetchrow(
        """
        SELECT EXISTS(
            SELECT 1
            FROM pg_type
            WHERE oid=ANY($1::oid[])
        )
        """,
        [record["id"] for record in old_enum_id_records_pre],
    )
    assert old_enums_exist_post is not None
    assert not old_enums_exist_post["exists"]
