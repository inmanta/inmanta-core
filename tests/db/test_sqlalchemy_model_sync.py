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

from collections import abc

import asyncpg

import inmanta.db.versions
from inmanta.data import CORE_SCHEMA_NAME, schema
from inmanta.data.sqlalchemy import Base
from sqlalchemy import ARRAY, URL, CheckConstraint, Column, Enum, ForeignKeyConstraint, Index, MetaData, Table, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.sql.type_api import TypeEngine

# PostgreSQL truncates identifiers to NAMEDATALEN - 1 bytes, so a longer name in a model or a migration script ends up
# truncated in the database. Both sides are truncated before they are compared, to compare what the database sees.
MAX_IDENTIFIER_LENGTH = 63


def _identifier(name: str | None) -> str | None:
    """The name of a constraint or an index as PostgreSQL stores it."""
    return name if name is None else name[:MAX_IDENTIFIER_LENGTH]


def _type(column_type: TypeEngine[object]) -> str:
    """
    A comparable description of a column type: the type as it appears in DDL, extended with the labels of a native
    enum type, because those are part of the schema as well.
    """
    compiled = column_type.compile(postgresql.dialect())
    element = column_type.item_type if isinstance(column_type, ARRAY) else column_type
    if isinstance(element, Enum) and element.native_enum:
        return f"{compiled} labels=({', '.join(element.enums)})"
    return compiled


def _server_default(column: Column[object]) -> str | None:
    """The default the database fills in for a column, or None if it has none."""
    if column.server_default is None:
        return None
    return str(getattr(column.server_default.arg, "text", column.server_default.arg))


def _predicate(index: Index) -> str | None:
    """The condition of a partial index, or None if the index covers all rows."""
    predicate = index.dialect_options["postgresql"]["where"]
    if predicate is None:
        return None
    # The database reports the condition wrapped in parentheses, a model typically declares it without. Only a pair
    # that encloses the whole condition is dropped: stripping both ends of "((n > 0) AND (name IS NULL))" until they
    # are no longer parentheses would leave the mangled "n > 0) AND (name IS NULL".
    normalized = str(predicate).strip()
    while normalized.startswith("(") and normalized.endswith(")"):
        depth = 0
        for position, character in enumerate(normalized):
            depth += (character == "(") - (character == ")")
            if depth == 0 and position < len(normalized) - 1:
                # The parenthesis opened at the start is closed here, so the pair encloses only part of the condition.
                return normalized
        normalized = normalized[1:-1].strip()
    return normalized


def _column_names(columns: abc.Iterable[Column[object]]) -> str:
    return f"({', '.join(column.name for column in columns)})"


def _columns(table: Table) -> dict[str | None, str]:
    return {
        column.name: f"type={_type(column.type)} nullable={column.nullable} default={_server_default(column)}"
        for column in table.columns
    }


def _primary_key(table: Table) -> dict[str | None, str]:
    return {_identifier(table.primary_key.name): f"columns={_column_names(table.primary_key.columns)}"}


def _indexes(table: Table) -> dict[str | None, str]:
    return {
        _identifier(index.name): (
            f"columns={_column_names(index.columns)} unique={bool(index.unique)} where={_predicate(index)}"
        )
        for index in table.indexes
    }


def _unique_constraints(table: Table) -> dict[str | None, str]:
    return {
        _identifier(constraint.name): f"columns={_column_names(constraint.columns)}"
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def _foreign_keys(table: Table) -> dict[str | None, str]:
    return {
        _identifier(constraint.name): (
            f"columns={_column_names(constraint.columns)}"
            f" references=({', '.join(element.target_fullname for element in constraint.elements)})"
            f" ondelete={constraint.ondelete} onupdate={constraint.onupdate}"
        )
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }


def _check_constraints(table: Table) -> dict[str | None, str]:
    return {
        _identifier(constraint.name): f"condition={constraint.sqltext}"
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }


def _compare(kind: str, in_model: dict[str | None, str], in_db: dict[str | None, str]) -> list[str]:
    """
    Compare one kind of schema element (columns, indexes, ...) of a single table.

    :param kind: the name of the kind of element that is compared, used in the reported differences.
    :param in_model: the elements declared by the SQLAlchemy model, keyed by name.
    :param in_db: the elements found in the database, keyed by name.
    :return: a human-readable description of each difference between the two.
    """
    differences: list[str] = []
    for name in sorted(in_model.keys() - in_db.keys()):
        differences.append(f"{kind} {name}: declared by the model but not present in the database")
    for name in sorted(in_db.keys() - in_model.keys()):
        differences.append(f"{kind} {name}: present in the database but not declared by the model")
    for name in sorted(in_model.keys() & in_db.keys()):
        if in_model[name] != in_db[name]:
            differences.append(f"{kind} {name}: model has {in_model[name]}, database has {in_db[name]}")
    return differences


def _compare_tables(model_table: Table, db_table: Table) -> list[str]:
    """
    Compare a single table as the model declares it against the table as it exists in the database.

    :return: a human-readable description of each difference between the two.
    """
    return [
        difference
        for kind, aspect in (
            ("column", _columns),
            ("primary key", _primary_key),
            ("index", _indexes),
            ("unique constraint", _unique_constraints),
            ("foreign key", _foreign_keys),
            ("check constraint", _check_constraints),
        )
        for difference in _compare(kind, aspect(model_table), aspect(db_table))
    ]


async def _reflect_database_schema(postgres_db, database_name: str) -> MetaData:
    """
    Load the schema of the given database into a new MetaData object.
    """
    url = URL.create(
        drivername="postgresql+asyncpg",
        username=postgres_db.user,
        password=postgres_db.password or None,
        host=postgres_db.host,
        port=postgres_db.port,
        database=database_name,
    )
    engine = create_async_engine(url)
    try:
        metadata = MetaData()
        async with engine.connect() as connection:
            await connection.run_sync(metadata.reflect)
        return metadata
    finally:
        await engine.dispose()


async def test_sqlalchemy_models_in_sync_with_database_schema(
    postgres_db,
    database_name_internal: str,
    postgresql_client: asyncpg.Connection,
    hard_clean_db,
    hard_clean_db_post,
) -> None:
    """
    Verify that the SQLAlchemy models in inmanta.data.sqlalchemy describe the schema that the database migration
    scripts produce. A migration that changes a table has to be accompanied by a change to the model of that table,
    and this test fails until it is.

    Everything the models express is compared: which tables exist, and per table the columns (type, nullability and
    default), the primary key, the indexes, and the unique, foreign key and check constraints. Names are compared as
    well, because migration scripts refer to constraints and indexes by name.

    Details that the models do not express are out of scope: the index method (btree, gin, ...), operator classes and
    the sort order of an index are not compared.
    """
    await schema.DBSchema(CORE_SCHEMA_NAME, inmanta.db.versions, postgresql_client).ensure_db_schema()
    database_schema: MetaData = await _reflect_database_schema(postgres_db, database_name_internal)

    model_tables: dict[str, Table] = Base.metadata.tables
    db_tables: dict[str, Table] = database_schema.tables

    differences: list[str] = []
    for name in sorted(model_tables.keys() - db_tables.keys()):
        differences.append(f"table {name}: declared by a model but not present in the database")
    for name in sorted(db_tables.keys() - model_tables.keys()):
        differences.append(f"table {name}: present in the database but not declared by a model")
    for name in sorted(model_tables.keys() & db_tables.keys()):
        differences.extend(f"table {name}: {difference}" for difference in _compare_tables(model_tables[name], db_tables[name]))

    assert not differences, (
        "The SQLAlchemy models in inmanta.data.sqlalchemy are out of sync with the schema created by the database "
        "migration scripts. Update the models to match the database:\n  " + "\n  ".join(differences)
    )
