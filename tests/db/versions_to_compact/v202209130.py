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

import typing
from collections import abc
from dataclasses import dataclass
from typing import Optional

from asyncpg import Connection


async def update(connection: Connection) -> None:
    """
    Recreate resource state types without the processing_events state.
    """
    resource_state_values: abc.Sequence[str] = [
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
    ]
    await replace_enum_type(
        EnumDefinition(
            name="resourcestate",
            values=resource_state_values,
            deleted_values={"processing_events": "deploying"},
            columns={
                "public.resource": [ColumnDefinition(name="status", default="available")],
                "public.resourceaction": [ColumnDefinition(name="status", default="available")],
            },
        ),
        connection=connection,
    )
    await replace_enum_type(
        EnumDefinition(
            name="non_deploying_resource_state",
            values=[v for v in resource_state_values if v != "deploying"],
            # migrate values to be safe even though processing_events state was actually unreachable in practice for this type
            deleted_values={"processing_events": "available"},
            columns={"public.resource": [ColumnDefinition(name="last_non_deploying_status", default="available")]},
        ),
        connection=connection,
    )


class ColumnDefinition(typing.NamedTuple):
    name: str
    default: Optional[str]


@dataclass(frozen=True)
class EnumDefinition:
    name: str
    values: abc.Sequence[str]
    deleted_values: abc.Mapping[str, Optional[str]]  # deleted values mapped to new value if any currently exist
    columns: abc.Mapping[str, abc.Sequence[ColumnDefinition]]  # columns with defaults


async def replace_enum_type(new_type: EnumDefinition, *, connection: Connection) -> None:
    """
    Completely replaces an enum type with a new definition with the same name.

    :param new_type: The definition of the new type. Assumed to be an internal construct, this method is not safe against
        injections via this object's attributes.
    """
    temp_name: str = f"_old_{new_type.name}"
    await connection.execute(
        f"""
        ALTER TYPE {new_type.name} RENAME TO {temp_name};
        CREATE TYPE {new_type.name} AS ENUM(%s);
        """
        % (", ".join(f"'{v}'" for v in new_type.values))
    )
    for table, columns in new_type.columns.items():
        for column, default in columns:
            for old_value, new_value in new_type.deleted_values.items():
                await connection.execute(f"UPDATE {table} SET {column}=$1 WHERE {column}=$2", new_value, old_value)
            await connection.execute(f"ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT")
            await connection.execute(
                # can't cast directly between enums -> go via varchar
                f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {new_type.name} USING {column}::varchar::{new_type.name}"
            )
            await connection.execute(f"ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT '{default}'")
    await connection.execute(f"DROP TYPE {temp_name}")
