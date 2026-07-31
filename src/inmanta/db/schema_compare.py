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

from sqlalchemy import ARRAY, URL, CheckConstraint, Column, Enum, ForeignKeyConstraint, Index, MetaData, Table, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.schema import DefaultClause
from sqlalchemy.sql.type_api import TypeEngine

# PostgreSQL truncates identifiers to NAMEDATALEN - 1 bytes, so a longer name in a model or a migration script ends up
# truncated in the database. Both sides are truncated before they are compared, to compare what the database sees.
MAX_IDENTIFIER_LENGTH = 63


def _identifier(name: object) -> str | None:
    """
    The name of a constraint or an index as PostgreSQL stores it, or None if it has none.

    A constraint that was never given a name reports None, while one whose name was computed but resolved to nothing
    reports SQLAlchemy's _NONE_NAME sentinel, which is not a string (here we resolve it as None anyway).
    """
    return name[:MAX_IDENTIFIER_LENGTH] if isinstance(name, str) else None


def _type(column_type: TypeEngine[object]) -> str:
    """
    A comparable description of a column type: the type as it appears in DDL, extended with the labels of a native
    enum type, because those are part of the schema as well.
    """
    # SQLAlchemy does not annotate the constructor of a dialect
    compiled = column_type.compile(postgresql.dialect())  # type: ignore[no-untyped-call]
    element = column_type.item_type if isinstance(column_type, ARRAY) else column_type
    if isinstance(element, Enum) and element.native_enum:
        return f"{compiled} labels=({', '.join(element.enums)})"
    return compiled


def _server_default(column: Column[object]) -> str | None:
    """The default the database fills in for a column, or None if it has none."""
    if not isinstance(column.server_default, DefaultClause):
        # Either no default at all, or one whose value lives outside the schema (a FetchedValue), which neither a
        # model of this schema nor reflection produces.
        return None
    return str(getattr(column.server_default.arg, "text", column.server_default.arg))


def _predicate(index: Index) -> str | None:
    """The condition of a partial index, or None if the index covers all rows."""
    predicate = index.dialect_options["postgresql"]["where"]
    if predicate is None:
        return None
    # Normalize and parse the entire predicate (e.g. ((n > 0) AND (name IS NULL)))
    normalized = str(predicate).strip()
    while normalized.startswith("(") and normalized.endswith(")"):
        depth = 0
        in_literal = False
        for position, character in enumerate(normalized):
            if character == "'":
                in_literal = not in_literal
                continue
            if in_literal:
                continue
            depth += (character == "(") - (character == ")")
            if depth == 0 and position < len(normalized) - 1:
                # The parenthesis opened at the start is closed here, so the pair encloses only part of the condition.
                return normalized
        normalized = normalized[1:-1].strip()
    return normalized


def _method(index: Index) -> str:
    """The method of an index (btree, gin, ...)."""
    # Reflection only reports the method when it is not the default, and a model only declares one when it deviates
    # from the default, so an absent method on either side means btree.
    return index.dialect_options["postgresql"]["using"] or "btree"


def _operator_classes(index: Index) -> str:
    """
    The operator class of each column of an index that does not use the default one for its type.
    """
    operator_classes: abc.Mapping[str, str] = index.dialect_options["postgresql"]["ops"]
    return f"({', '.join(f'{column}={operator_classes[column]}' for column in sorted(operator_classes))})"


def _column_names(columns: abc.Iterable[Column[object]]) -> str:
    return f"({', '.join(column.name for column in columns)})"


def _by_name(elements: abc.Iterable[tuple[str | None, str]]) -> dict[str, str]:
    """
    Key the elements of one kind, of a single table by their name.

    PostgreSQL names every index and constraint, so an element without a name can only come from a sqlalchemy model.
    We add the description to the key so that multiple unnamed elements can appear in the dictionary
    """
    return {name if name is not None else f"<unnamed> {description}": description for name, description in elements}


def _columns(table: Table) -> dict[str, str]:
    return _by_name(
        (column.name, f"type={_type(column.type)} nullable={column.nullable} default={_server_default(column)}")
        for column in table.columns
    )


def _primary_key(table: Table) -> dict[str, str]:
    return _by_name([(_identifier(table.primary_key.name), f"columns={_column_names(table.primary_key.columns)}")])


def _indexes(table: Table) -> dict[str, str]:
    return _by_name(
        (
            _identifier(index.name),
            (
                f"columns={_column_names(index.columns)} unique={bool(index.unique)}"
                f" method={_method(index)} operator_classes={_operator_classes(index)} where={_predicate(index)}"
            ),
        )
        for index in table.indexes
    )


def _unique_constraints(table: Table) -> dict[str, str]:
    return _by_name(
        (_identifier(constraint.name), f"columns={_column_names(constraint.columns)}")
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    )


def _foreign_keys(table: Table) -> dict[str, str]:
    return _by_name(
        (
            _identifier(constraint.name),
            (
                f"columns={_column_names(constraint.columns)}"
                f" references=({', '.join(element.target_fullname for element in constraint.elements)})"
                f" ondelete={constraint.ondelete} onupdate={constraint.onupdate}"
            ),
        )
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    )


def _check_constraints(table: Table) -> dict[str, str]:
    return _by_name(
        (_identifier(constraint.name), f"condition={constraint.sqltext}")
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    )


def _compare(kind: str, in_model: abc.Mapping[str, str], in_db: abc.Mapping[str, str]) -> list[str]:
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


def compare_schemas(model_tables: abc.Mapping[str, Table], db_tables: abc.Mapping[str, Table]) -> list[str]:
    """
    Compare the tables the models declare against the tables the database has.

    Compared are: which tables exist, and per table the columns (type, nullability and default), the primary key, the
    indexes (columns, uniqueness, method, operator classes and the condition of a partial one), and the unique, foreign
    key and check constraints. Names are compared as well, because migration scripts refer to constraints and indexes
    by name.

    Not compared, all of which the models can express, so each is a way for a model to be wrong that this comparison
    does not catch:
      - the sort order of the columns of an index, because the indexes are compared on index.columns, which reports the
        columns without the modifier that carries the order.
      - the order of the columns of a table, because the columns are compared by name.
      - the comment on a table or a column.
      - whether a constraint is deferrable, or was added NOT VALID.

    :param model_tables: the tables declared by the SQLAlchemy models, keyed by table name.
    :param db_tables: the tables reflected from the database, keyed by table name.
    :return: a human-readable description of each difference between the two.
    """
    differences: list[str] = []
    for name in sorted(model_tables.keys() - db_tables.keys()):
        differences.append(f"table {name}: declared by a model but not present in the database")
    for name in sorted(db_tables.keys() - model_tables.keys()):
        differences.append(f"table {name}: present in the database but not declared by a model")
    for name in sorted(model_tables.keys() & db_tables.keys()):
        differences.extend(f"table {name}: {difference}" for difference in _compare_tables(model_tables[name], db_tables[name]))
    return differences


async def reflect_database_schema(host: str, port: int, username: str, password: str | None, database: str) -> MetaData:
    """
    Load the schema of the given database into a new MetaData object.
    """
    url = URL.create(
        drivername="postgresql+asyncpg",
        username=username,
        password=password or None,
        host=host,
        port=port,
        database=database,
    )
    engine = create_async_engine(url)
    try:
        metadata = MetaData()
        async with engine.connect() as connection:
            await connection.run_sync(metadata.reflect)
        return metadata
    finally:
        await engine.dispose()
