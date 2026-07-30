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
from sqlalchemy import (
    ARRAY,
    URL,
    CheckConstraint,
    Column,
    Enum,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    PrimaryKeyConstraint,
    String,
    Table,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.schema import SchemaItem
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


def _compare_schemas(model_tables: abc.Mapping[str, Table], db_tables: abc.Mapping[str, Table]) -> list[str]:
    """
    Compare the tables the models declare against the tables the database has.

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


def _drift(model_elements: abc.Sequence[SchemaItem], db_elements: abc.Sequence[SchemaItem]) -> list[str]:
    """
    Compare one table as the model side declares it against the same table as the database side declares it.

    Both sides are declared by hand instead of one of them being reflected, so that a case can set up a single
    difference and nothing else. That the database really reports a given property the way a model declares it is
    covered by test_sqlalchemy_models_in_sync_with_database_schema, which compares the two for real.

    :param model_elements: the columns and constraints of the table on the model side.
    :param db_elements: the columns and constraints of the same table on the database side.
    :return: the differences reported between the two.
    """
    model, database = MetaData(), MetaData()
    Table("tab", model, *model_elements)
    Table("tab", database, *db_elements)
    return _compare_schemas(model.tables, database.tables)


def test_detects_table_drift() -> None:
    """
    Verify that a table that only one side has is reported.
    """
    model, database = MetaData(), MetaData()
    Table("only_in_model", model, Column("id", Integer, primary_key=True))
    Table("only_in_db", database, Column("id", Integer, primary_key=True))
    assert _compare_schemas(model.tables, database.tables) == [
        "table only_in_model: declared by a model but not present in the database",
        "table only_in_db: present in the database but not declared by a model",
    ]


def test_detects_column_drift() -> None:
    """
    Verify that every property of a column that the models express is reported when it differs.
    """
    # a column that only one side has
    assert _drift([], [Column("extra", String)]) == [
        "table tab: column extra: present in the database but not declared by the model"
    ]
    assert _drift([Column("extra", String)], []) == [
        "table tab: column extra: declared by the model but not present in the database"
    ]
    # the type of a column
    assert _drift([Column("val", String)], [Column("val", Integer)]) == [
        "table tab: column val: model has type=VARCHAR nullable=True default=None,"
        " database has type=INTEGER nullable=True default=None"
    ]
    # the length of a varchar
    assert _drift([Column("val", String(8))], [Column("val", String)]) == [
        "table tab: column val: model has type=VARCHAR(8) nullable=True default=None,"
        " database has type=VARCHAR nullable=True default=None"
    ]
    # the labels of a native enum type
    assert _drift([Column("val", Enum("a", "b", name="my_enum"))], [Column("val", Enum("a", "b", "c", name="my_enum"))]) == [
        "table tab: column val: model has type=my_enum labels=(a, b) nullable=True default=None,"
        " database has type=my_enum labels=(a, b, c) nullable=True default=None"
    ]
    # whether a column accepts NULL
    assert _drift([Column("val", String, nullable=False)], [Column("val", String)]) == [
        "table tab: column val: model has type=VARCHAR nullable=False default=None,"
        " database has type=VARCHAR nullable=True default=None"
    ]
    # the default the database fills in
    assert _drift(
        [Column("val", String, server_default=text("'a'::character varying"))],
        [Column("val", String, server_default=text("'b'::character varying"))],
    ) == [
        "table tab: column val: model has type=VARCHAR nullable=True default='a'::character varying,"
        " database has type=VARCHAR nullable=True default='b'::character varying"
    ]
    # a default that only one side has
    assert _drift([Column("val", String)], [Column("val", String, server_default=text("''::character varying"))]) == [
        "table tab: column val: model has type=VARCHAR nullable=True default=None,"
        " database has type=VARCHAR nullable=True default=''::character varying"
    ]


def test_detects_primary_key_drift() -> None:
    """
    Verify that the columns and the name of a primary key are reported when they differ.
    """
    # the columns of the primary key. Both columns are declared NOT NULL on both sides, because a column being part
    # of the primary key makes it NOT NULL, which would be a second difference.
    assert _drift(
        [Column("a", Integer), Column("b", Integer, nullable=False), PrimaryKeyConstraint("a", name="tab_pkey")],
        [Column("a", Integer), Column("b", Integer, nullable=False), PrimaryKeyConstraint("a", "b", name="tab_pkey")],
    ) == ["table tab: primary key tab_pkey: model has columns=(a), database has columns=(a, b)"]
    # the name of the primary key, which a migration script needs to address it
    assert _drift(
        [Column("a", Integer), PrimaryKeyConstraint("a", name="tab_pkey")],
        [Column("a", Integer), PrimaryKeyConstraint("a", name="old_name_pkey")],
    ) == [
        "table tab: primary key tab_pkey: declared by the model but not present in the database",
        "table tab: primary key old_name_pkey: present in the database but not declared by the model",
    ]


def test_detects_index_drift() -> None:
    """
    Verify that every property of an index that the models express is reported when it differs.
    """
    # an index that only one side has
    assert _drift([Column("a", Integer)], [Column("a", Integer), Index("tab_a_index", "a")]) == [
        "table tab: index tab_a_index: present in the database but not declared by the model"
    ]
    # the name of an index
    assert _drift(
        [Column("a", Integer), Index("tab_new_name_index", "a")],
        [Column("a", Integer), Index("tab_old_name_index", "a")],
    ) == [
        "table tab: index tab_new_name_index: declared by the model but not present in the database",
        "table tab: index tab_old_name_index: present in the database but not declared by the model",
    ]
    # the columns of an index
    assert _drift(
        [Column("a", Integer), Column("b", Integer), Index("tab_index", "a")],
        [Column("a", Integer), Column("b", Integer), Index("tab_index", "a", "b")],
    ) == [
        "table tab: index tab_index: model has columns=(a) unique=False where=None,"
        " database has columns=(a, b) unique=False where=None"
    ]
    # the order of the columns of an index, which decides the queries it serves
    assert _drift(
        [Column("a", Integer), Column("b", Integer), Index("tab_index", "a", "b")],
        [Column("a", Integer), Column("b", Integer), Index("tab_index", "b", "a")],
    ) == [
        "table tab: index tab_index: model has columns=(a, b) unique=False where=None,"
        " database has columns=(b, a) unique=False where=None"
    ]
    # whether an index is unique
    assert _drift(
        [Column("a", Integer), Index("tab_index", "a")],
        [Column("a", Integer), Index("tab_index", "a", unique=True)],
    ) == [
        "table tab: index tab_index: model has columns=(a) unique=False where=None,"
        " database has columns=(a) unique=True where=None"
    ]
    # the condition of a partial index
    assert _drift(
        [Column("a", Integer), Index("tab_index", "a", postgresql_where=text("a IS NULL"))],
        [Column("a", Integer), Index("tab_index", "a", postgresql_where=text("a IS NOT NULL"))],
    ) == [
        "table tab: index tab_index: model has columns=(a) unique=False where=a IS NULL,"
        " database has columns=(a) unique=False where=a IS NOT NULL"
    ]
    # a condition that only one side has, so an index covers all rows on one side and some on the other
    assert _drift(
        [Column("a", Integer), Index("tab_index", "a")],
        [Column("a", Integer), Index("tab_index", "a", postgresql_where=text("a IS NULL"))],
    ) == [
        "table tab: index tab_index: model has columns=(a) unique=False where=None,"
        " database has columns=(a) unique=False where=a IS NULL"
    ]


def test_detects_unique_constraint_drift() -> None:
    """
    Verify that the columns and the name of a unique constraint are reported when they differ.
    """
    # a unique constraint that only one side has
    assert _drift([Column("a", Integer)], [Column("a", Integer), UniqueConstraint("a", name="tab_a_key")]) == [
        "table tab: unique constraint tab_a_key: present in the database but not declared by the model"
    ]
    # the columns of a unique constraint
    assert _drift(
        [Column("a", Integer), Column("b", Integer), UniqueConstraint("a", name="tab_key")],
        [Column("a", Integer), Column("b", Integer), UniqueConstraint("a", "b", name="tab_key")],
    ) == ["table tab: unique constraint tab_key: model has columns=(a), database has columns=(a, b)"]


def test_detects_foreign_key_drift() -> None:
    """
    Verify that every property of a foreign key that the models express is reported when it differs.
    """
    # a foreign key that only one side has
    assert _drift(
        [Column("a", Integer)],
        [Column("a", Integer), ForeignKeyConstraint(["a"], ["other.id"], name="tab_a_fkey")],
    ) == ["table tab: foreign key tab_a_fkey: present in the database but not declared by the model"]
    # the columns a foreign key is on
    assert _drift(
        [Column("a", Integer), Column("b", Integer), ForeignKeyConstraint(["a"], ["other.id"], name="tab_fkey")],
        [Column("a", Integer), Column("b", Integer), ForeignKeyConstraint(["b"], ["other.id"], name="tab_fkey")],
    ) == [
        "table tab: foreign key tab_fkey: model has columns=(a) references=(other.id) ondelete=None onupdate=None,"
        " database has columns=(b) references=(other.id) ondelete=None onupdate=None"
    ]
    # the columns a foreign key references
    assert _drift(
        [Column("a", Integer), ForeignKeyConstraint(["a"], ["other.id"], name="tab_fkey")],
        [Column("a", Integer), ForeignKeyConstraint(["a"], ["other.name"], name="tab_fkey")],
    ) == [
        "table tab: foreign key tab_fkey: model has columns=(a) references=(other.id) ondelete=None onupdate=None,"
        " database has columns=(a) references=(other.name) ondelete=None onupdate=None"
    ]
    # what happens to a referencing row when the row it references is deleted
    assert _drift(
        [Column("a", Integer), ForeignKeyConstraint(["a"], ["other.id"], ondelete="CASCADE", name="tab_fkey")],
        [Column("a", Integer), ForeignKeyConstraint(["a"], ["other.id"], ondelete="RESTRICT", name="tab_fkey")],
    ) == [
        "table tab: foreign key tab_fkey: model has columns=(a) references=(other.id) ondelete=CASCADE onupdate=None,"
        " database has columns=(a) references=(other.id) ondelete=RESTRICT onupdate=None"
    ]
    # and when it is updated
    assert _drift(
        [Column("a", Integer), ForeignKeyConstraint(["a"], ["other.id"], name="tab_fkey")],
        [Column("a", Integer), ForeignKeyConstraint(["a"], ["other.id"], onupdate="CASCADE", name="tab_fkey")],
    ) == [
        "table tab: foreign key tab_fkey: model has columns=(a) references=(other.id) ondelete=None onupdate=None,"
        " database has columns=(a) references=(other.id) ondelete=None onupdate=CASCADE"
    ]


def test_detects_check_constraint_drift() -> None:
    """
    Verify that the condition and the name of a check constraint are reported when they differ.
    """
    # a check constraint that only one side has
    assert _drift([Column("n", Integer)], [Column("n", Integer), CheckConstraint(text("n > 0"), name="tab_n_check")]) == [
        "table tab: check constraint tab_n_check: present in the database but not declared by the model"
    ]
    # the condition of a check constraint
    assert _drift(
        [Column("n", Integer), CheckConstraint(text("n > 0"), name="tab_check")],
        [Column("n", Integer), CheckConstraint(text("n > 1"), name="tab_check")],
    ) == ["table tab: check constraint tab_check: model has condition=n > 0, database has condition=n > 1"]


def test_reports_no_drift_for_equal_declarations() -> None:
    """
    Verify the other side of the comparison: a model that describes the same table as the database is not reported,
    including where the two sides spell the same thing differently and the comparison normalizes it.
    """
    # the same table, declared the same way
    assert (
        _drift(
            [Column("a", Integer), PrimaryKeyConstraint("a", name="tab_pkey"), Index("tab_a_index", "a")],
            [Column("a", Integer), PrimaryKeyConstraint("a", name="tab_pkey"), Index("tab_a_index", "a")],
        )
        == []
    )
    # a name longer than PostgreSQL keeps, against the truncated name the database ends up with
    long_name = "tab_" + "x" * 60
    assert len(long_name) == MAX_IDENTIFIER_LENGTH + 1
    assert (
        _drift(
            [Column("a", Integer), Index(long_name, "a")],
            [Column("a", Integer), Index(long_name[:MAX_IDENTIFIER_LENGTH], "a")],
        )
        == []
    )
    # the parentheses PostgreSQL puts around the condition of a partial index
    assert (
        _drift(
            [Column("a", Integer), Index("tab_index", "a", postgresql_where=text("a IS NULL"))],
            [Column("a", Integer), Index("tab_index", "a", postgresql_where=text("(a IS NULL)"))],
        )
        == []
    )
    # only those, the parentheses within a compound condition are part of it and are kept on both sides
    assert (
        _drift(
            [Column("a", Integer), Index("tab_index", "a", postgresql_where=text("(n > 0) AND (a IS NULL)"))],
            [Column("a", Integer), Index("tab_index", "a", postgresql_where=text("((n > 0) AND (a IS NULL))"))],
        )
        == []
    )
    # the labels of a non-native enum, which the database holds as the varchar it is
    assert (
        _drift(
            [Column("val", ARRAY(Enum("a", "b", name="my_enum", native_enum=False, create_constraint=False, length=None)))],
            [Column("val", ARRAY(String))],
        )
        == []
    )


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

    differences: list[str] = _compare_schemas(Base.metadata.tables, database_schema.tables)

    assert not differences, (
        "The SQLAlchemy models in inmanta.data.sqlalchemy are out of sync with the schema created by the database "
        "migration scripts. Update the models to match the database:\n  " + "\n  ".join(differences)
    )
