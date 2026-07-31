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
from inmanta.db.schema_compare import MAX_IDENTIFIER_LENGTH, DatabaseConnectionDetails, compare_schemas, reflect_database_schema
from sqlalchemy import (
    ARRAY,
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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.schema import SchemaItem


def _drift(model_elements: abc.Sequence[SchemaItem], db_elements: abc.Sequence[SchemaItem]) -> list[str]:
    """
    Compare one table as the sqlalchemy model side declares it against the same table as the postgres database side declares it.

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
    return compare_schemas(model.tables, database.tables)


def test_detects_table_drift() -> None:
    """
    Verify that a table that only one side has is reported.
    """
    model, database = MetaData(), MetaData()
    Table("only_in_model", model, Column("id", Integer, primary_key=True))
    Table("only_in_db", database, Column("id", Integer, primary_key=True))
    assert compare_schemas(model.tables, database.tables) == [
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
    # and the labels of a native enum that an array holds, which sit on the element type
    assert _drift(
        [Column("val", ARRAY(Enum("a", "b", name="my_enum")))],
        [Column("val", ARRAY(Enum("a", "b", "c", name="my_enum")))],
    ) == [
        "table tab: column val: model has type=my_enum[] labels=(a, b) nullable=True default=None,"
        " database has type=my_enum[] labels=(a, b, c) nullable=True default=None"
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
        "table tab: index tab_index: model has columns=(a) unique=False method=btree operator_classes=() where=None,"
        " database has columns=(a, b) unique=False method=btree operator_classes=() where=None"
    ]
    # the order of the columns of an index, which decides the queries it serves
    assert _drift(
        [Column("a", Integer), Column("b", Integer), Index("tab_index", "a", "b")],
        [Column("a", Integer), Column("b", Integer), Index("tab_index", "b", "a")],
    ) == [
        "table tab: index tab_index: model has columns=(a, b) unique=False method=btree operator_classes=() where=None,"
        " database has columns=(b, a) unique=False method=btree operator_classes=() where=None"
    ]
    # whether an index is unique
    assert _drift(
        [Column("a", Integer), Index("tab_index", "a")],
        [Column("a", Integer), Index("tab_index", "a", unique=True)],
    ) == [
        "table tab: index tab_index: model has columns=(a) unique=False method=btree operator_classes=() where=None,"
        " database has columns=(a) unique=True method=btree operator_classes=() where=None"
    ]
    # the condition of a partial index
    assert _drift(
        [Column("a", Integer), Index("tab_index", "a", postgresql_where=text("a IS NULL"))],
        [Column("a", Integer), Index("tab_index", "a", postgresql_where=text("a IS NOT NULL"))],
    ) == [
        "table tab: index tab_index: model has columns=(a) unique=False method=btree operator_classes=() where=a IS NULL,"
        " database has columns=(a) unique=False method=btree operator_classes=() where=a IS NOT NULL"
    ]
    # a condition that only one side has, so an index covers all rows on one side and some on the other
    assert _drift(
        [Column("a", Integer), Index("tab_index", "a")],
        [Column("a", Integer), Index("tab_index", "a", postgresql_where=text("a IS NULL"))],
    ) == [
        "table tab: index tab_index: model has columns=(a) unique=False method=btree operator_classes=() where=None,"
        " database has columns=(a) unique=False method=btree operator_classes=() where=a IS NULL"
    ]
    # the method of an index, which decides which operators it can serve at all
    assert _drift(
        [Column("a", JSONB), Index("tab_index", "a")],
        [Column("a", JSONB), Index("tab_index", "a", postgresql_using="gin")],
    ) == [
        "table tab: index tab_index: model has columns=(a) unique=False method=btree operator_classes=() where=None,"
        " database has columns=(a) unique=False method=gin operator_classes=() where=None"
    ]
    # the operator class of a column of an index, which decides which operators it serves and what it costs
    assert _drift(
        [Column("a", JSONB), Index("tab_index", "a", postgresql_using="gin")],
        [Column("a", JSONB), Index("tab_index", "a", postgresql_using="gin", postgresql_ops={"a": "jsonb_path_ops"})],
    ) == [
        "table tab: index tab_index: model has columns=(a) unique=False method=gin operator_classes=() where=None,"
        " database has columns=(a) unique=False method=gin operator_classes=(a=jsonb_path_ops) where=None"
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
    # a parenthesis within a string literal, which closes no pair, so the pair around the whole condition is still
    # the one that is dropped
    assert (
        _drift(
            [Column("name", String), Index("tab_index", "name", postgresql_where=text("name <> ')'::text"))],
            [Column("name", String), Index("tab_index", "name", postgresql_where=text("(name <> ')'::text)"))],
        )
        == []
    )
    # the default method of an index, which the database only reports when it is not the default
    assert (
        _drift(
            [Column("a", Integer), Index("tab_index", "a", postgresql_using="btree")],
            [Column("a", Integer), Index("tab_index", "a")],
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
    # the labels of a native enum in an array, which the database reports on the element type
    assert (
        _drift(
            [Column("val", ARRAY(Enum("a", "b", name="my_enum")))],
            [Column("val", ARRAY(Enum("a", "b", name="my_enum")))],
        )
        == []
    )


async def test_sqlalchemy_models_in_sync_with_database_schema(
    postgres_db: DatabaseConnectionDetails,
    database_name_internal: str,
    postgresql_client: asyncpg.Connection,
    hard_clean_db,
    hard_clean_db_post,
) -> None:
    """
    Verify that the SQLAlchemy models in inmanta.data.sqlalchemy describe the schema that the database migration
    scripts produce. A migration that changes a table has to be accompanied by a change to the model of that table,
    and this test fails until it is.

    What is and is not compared is documented on inmanta.db.schema_compare.compare_schemas.
    """
    await schema.DBSchema(CORE_SCHEMA_NAME, inmanta.db.versions, postgresql_client).ensure_db_schema()
    database_schema: MetaData = await reflect_database_schema(postgres_db, database_name_internal)

    differences: list[str] = compare_schemas(Base.metadata.tables, database_schema.tables)

    assert not differences, (
        "The SQLAlchemy models in inmanta.data.sqlalchemy are out of sync with the schema created by the database "
        "migration scripts. Update the models to match the database:\n  " + "\n  ".join(differences)
    )
