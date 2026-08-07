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

import textwrap
from abc import ABC, abstractmethod
from collections import abc
from typing import ClassVar

from sqlalchemy import (
    ARRAY,
    URL,
    CheckConstraint,
    Column,
    Constraint,
    Enum,
    ForeignKeyConstraint,
    Index,
    MetaData,
    Table,
    TextClause,
    UniqueConstraint,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.schema import DefaultClause
from sqlalchemy.sql.type_api import TypeEngine

# PostgreSQL truncates identifiers to NAMEDATALEN - 1 bytes, so a longer name in a model or a migration script ends up
# truncated in the database. Both sides are truncated before they are compared, to compare what the database sees.
MAX_IDENTIFIER_LENGTH = 63

# One level of indentation in the report that a comparison produces.
REPORT_INDENT = "\t"

# SQLAlchemy does not annotate the constructor of a dialect.
POSTGRESQL_DIALECT: Dialect = postgresql.dialect()  # type: ignore[no-untyped-call]


def get_truncated_identifier(element: Constraint | Index) -> str | None:
    """
    The name of the given constraint or index as PostgreSQL stores it, or None if it has none.

    A nameless element carries either None or _NoneName, so only a string counts as a name here.
    """
    name = element.name
    return name[:MAX_IDENTIFIER_LENGTH] if isinstance(name, str) else None


def column_names_to_str[T](columns: abc.Iterable[Column[T]]) -> str:
    """The names of the given columns, in the order they are given."""
    return f"({', '.join(column.name for column in columns)})"


class ElementDifference(ABC):
    """
    A single element of a table (a column, an index, a constraint, ...) that the SQLAlchemy model side and the
    database side do not describe the same way.
    """

    def __init__(self, element_kind: str, name: str) -> None:
        """
        :param element_kind: the kind of element this is, as it appears in the report, e.g. "column" or "index".
        :param name: the name the element is compared under.
        """
        self.element_kind = element_kind
        self.name = name

    @abstractmethod
    def format_report(self) -> str:
        """
        This difference as one or more report lines, without a trailing newline.
        """


class ElementOnlyDeclaredByModel(ElementDifference):
    """An element that the model declares but that the database does not have."""

    def format_report(self) -> str:
        return f"{self.element_kind} {self.name}: declared by the model but not present in the database"


class ElementOnlyPresentInDatabase(ElementDifference):
    """An element that the database has but that the model does not declare."""

    def format_report(self) -> str:
        return f"{self.element_kind} {self.name}: present in the database but not declared by the model"


class ElementDescribedDifferently(ElementDifference):
    """An element that both sides have, but that they describe differently."""

    def __init__(self, element_kind: str, name: str, description_in_model: str, description_in_database: str) -> None:
        super().__init__(element_kind, name)
        self.description_in_model = description_in_model
        self.description_in_database = description_in_database

    def format_report(self) -> str:
        return (
            f"{self.element_kind} {self.name}:\n"
            f"{REPORT_INDENT}model:    {self.description_in_model}\n"
            f"{REPORT_INDENT}database: {self.description_in_database}"
        )


class TableDifference(ABC):
    """
    A single table that the SQLAlchemy model side and the database side do not describe the same way.
    """

    def __init__(self, table_name: str) -> None:
        self.table_name = table_name

    @abstractmethod
    def format_report(self) -> str:
        """
        This difference as one or more report lines, without a trailing newline.
        """


class TableOnlyDeclaredByModel(TableDifference):
    """A table that a model declares but that the database does not have."""

    def format_report(self) -> str:
        return f"table {self.table_name}: declared by a model but not present in the database"


class TableOnlyPresentInDatabase(TableDifference):
    """A table that the database has but that no model declares."""

    def format_report(self) -> str:
        return f"table {self.table_name}: present in the database but not declared by a model"


class TableWithDifferingElements(TableDifference):
    """A table that both sides have, but on whose elements they do not agree."""

    def __init__(self, table_name: str, element_differences: abc.Sequence[ElementDifference]) -> None:
        super().__init__(table_name)
        self.element_differences = element_differences

    def format_report(self) -> str:
        elements = "\n".join(difference.format_report() for difference in self.element_differences)
        return f"table {self.table_name}:\n{textwrap.indent(elements, REPORT_INDENT)}"


class TableElementExtractor(ABC):
    """
    Describes one kind of element of a table (its columns, its indexes, ...) in a form that can be compared between
    the SQLAlchemy model side and the database side.

    Everything that is compared about an element goes into its description, so that comparing the two descriptions
    decides whether the two sides agree on that element, and the two read next to each other in the report.
    """

    # The name of the kind of element this extractor handles, as it appears in the report.
    element_kind: ClassVar[str]

    @abstractmethod
    def get_named_elements(self, table: Table) -> abc.Iterator[tuple[str | None, str]]:
        """
        The elements of this kind on the given table, as the name of each element and a description of everything that
        is compared about it. The name is None for an element that a SQLAlchemy model left for SQLAlchemy to name.
        """

    def get_descriptions_by_name(self, table: Table) -> abc.Mapping[str, str]:
        """
        The description of each element of this kind on the given table, keyed by the name it is compared under.

        PostgreSQL names every index and every constraint, so an element without a name can only come from a
        SQLAlchemy model. The description is part of the key of such an element, so that several unnamed elements of
        the same kind on one table do not collapse onto a single key.
        """
        return {
            name if name is not None else f"<unnamed> {description}": description
            for name, description in self.get_named_elements(table)
        }

    def compare(self, model_table: Table, database_table: Table) -> abc.Sequence[ElementDifference]:
        """
        The differences on the elements of this kind, between the table as a model declares it and the same table as
        the database has it, ordered by name within each kind of difference.
        """
        in_model = self.get_descriptions_by_name(model_table)
        in_database = self.get_descriptions_by_name(database_table)
        differences: list[ElementDifference] = [
            ElementOnlyDeclaredByModel(self.element_kind, name) for name in sorted(in_model.keys() - in_database.keys())
        ]
        differences.extend(
            ElementOnlyPresentInDatabase(self.element_kind, name) for name in sorted(in_database.keys() - in_model.keys())
        )
        differences.extend(
            ElementDescribedDifferently(self.element_kind, name, in_model[name], in_database[name])
            for name in sorted(in_model.keys() & in_database.keys())
            if in_model[name] != in_database[name]
        )
        return differences


class ColumnExtractor(TableElementExtractor):
    element_kind = "column"

    @staticmethod
    def get_column_type_def_as_str[T](column_type: TypeEngine[T]) -> str:
        """
        A comparable description of a column type: the type as it appears in DDL, extended with the labels of a native
        enum type, because those are part of the schema as well.
        """
        compiled_type: str = column_type.compile(POSTGRESQL_DIALECT)
        element_type = column_type.item_type if isinstance(column_type, ARRAY) else column_type
        if isinstance(element_type, Enum) and element_type.native_enum:
            return f"{compiled_type} labels=({', '.join(element_type.enums)})"
        return compiled_type

    @staticmethod
    def get_server_default_as_str[T](column: Column[T]) -> str | None:
        """The default the database fills in for the given column, or None if it has none."""
        if not isinstance(column.server_default, DefaultClause):
            # Either no default at all, or one whose value lives outside the schema (a FetchedValue), which neither a
            # model of this schema nor reflection produces.
            return None
        default = column.server_default.arg
        # A text clause is taken apart rather than rendered, because rendering it turns the parameter markers it may
        # hold back into a form that no longer matches what the other side reports.
        return default.text if isinstance(default, TextClause) else str(default)

    def get_named_elements(self, table: Table) -> abc.Iterator[tuple[str | None, str]]:
        for column in table.columns:
            yield (
                column.name,
                f"type={self.get_column_type_def_as_str(column.type)} nullable={column.nullable}"
                f" default={self.get_server_default_as_str(column)}",
            )


class PrimaryKeyExtractor(TableElementExtractor):
    element_kind = "primary key"

    def get_named_elements(self, table: Table) -> abc.Iterator[tuple[str | None, str]]:
        yield (
            get_truncated_identifier(table.primary_key),
            f"columns={column_names_to_str(table.primary_key.columns)}",
        )


class IndexExtractor(TableElementExtractor):
    element_kind = "index"

    @staticmethod
    def get_index_type(index: Index) -> str:
        """The type of an index (btree, gin, ...)."""
        # Reflection only reports the type when it is not the default, and a model only declares one when it deviates
        # from the default, so an absent type on either side means btree.
        index_type: str | None = index.dialect_options["postgresql"]["using"]
        return index_type or "btree"

    @staticmethod
    def get_operator_classes_as_str(index: Index) -> str:
        """
        The operator class of each column of the given index that does not use the default one for its type. The
        columns that do use the default are absent on both sides, because neither a model nor reflection records those.
        """
        operator_classes: abc.Mapping[str, str] = index.dialect_options["postgresql"]["ops"]
        return f"({', '.join(f'{column}={operator_classes[column]}' for column in sorted(operator_classes))})"

    @staticmethod
    def get_condition_for_partial_index(index: Index) -> str | None:
        """
        The condition of a partial index, or None if the index covers all rows.

        A model declares the condition the way a person writes it (``expired IS NULL``), while PostgreSQL reports it
        back with a pair of parentheses around it (``(expired IS NULL)``). That pair is dropped here, so that the two
        sides compare equal.

        Telling the two apart takes walking the condition. The parenthesis it opens with encloses the whole condition
        exactly when it is closed by the very last character. If it is closed earlier, as in ``(n > 0) AND (name IS
        NULL)``, then the condition merely starts with a parenthesized part and nothing may be dropped. Parentheses
        within a string literal (``name <> ')'::text``) belong to the literal rather than to the condition and are
        skipped.
        """
        condition = index.dialect_options["postgresql"]["where"]
        if condition is None:
            return None
        condition_as_str = str(condition).strip()
        while condition_as_str.startswith("(") and condition_as_str.endswith(")"):
            open_parentheses = 0
            within_string_literal = False
            for position, character in enumerate(condition_as_str):
                if character == "'":
                    within_string_literal = not within_string_literal
                    continue
                if within_string_literal:
                    continue
                open_parentheses += (character == "(") - (character == ")")
                if open_parentheses == 0 and position < len(condition_as_str) - 1:
                    # The parenthesis the condition opens with is closed before its last character, so the pair encloses
                    # only part of the condition and neither of the two may be dropped.
                    return condition_as_str
            condition_as_str = condition_as_str[1:-1].strip()
        return condition_as_str

    def get_named_elements(self, table: Table) -> abc.Iterator[tuple[str | None, str]]:
        for index in table.indexes:
            yield (
                get_truncated_identifier(index),
                f"columns={column_names_to_str(index.columns)} unique={bool(index.unique)}"
                f" type={self.get_index_type(index)} operator_classes={self.get_operator_classes_as_str(index)}"
                f" where={self.get_condition_for_partial_index(index)}",
            )


class UniqueConstraintExtractor(TableElementExtractor):
    element_kind = "unique constraint"

    def get_named_elements(self, table: Table) -> abc.Iterator[tuple[str | None, str]]:
        for constraint in table.constraints:
            if isinstance(constraint, UniqueConstraint):
                yield get_truncated_identifier(constraint), f"columns={column_names_to_str(constraint.columns)}"


class ForeignKeyExtractor(TableElementExtractor):
    element_kind = "foreign key"

    def get_named_elements(self, table: Table) -> abc.Iterator[tuple[str | None, str]]:
        for constraint in table.constraints:
            if isinstance(constraint, ForeignKeyConstraint):
                yield (
                    get_truncated_identifier(constraint),
                    f"columns={column_names_to_str(constraint.columns)}"
                    f" references=({', '.join(element.target_fullname for element in constraint.elements)})"
                    f" ondelete={constraint.ondelete} onupdate={constraint.onupdate}",
                )


class CheckConstraintExtractor(TableElementExtractor):
    element_kind = "check constraint"

    def get_named_elements(self, table: Table) -> abc.Iterator[tuple[str | None, str]]:
        for constraint in table.constraints:
            if isinstance(constraint, CheckConstraint):
                yield get_truncated_identifier(constraint), f"condition={constraint.sqltext}"


class DatabaseSchemaComparison:
    """
    Compares the tables that a set of SQLAlchemy models declares against the tables that a database has.

    Compared are: which tables exist, and per table the columns (type, nullability and default), the primary key, the
    indexes (columns, uniqueness, type, operator classes and the condition of a partial one), and the unique, foreign
    key and check constraints. Names are compared as well, because migration scripts refer to constraints and indexes
    by name.

    Not compared, all of which the models can express, so each is a way for a model to be wrong that this comparison
    does not catch:
      - the sort order of the columns of an index, because the indexes are compared on index.columns, which reports the
        columns without the modifier that carries the order.
      - the order of the columns of a table, because the columns are compared by name.
      - the comment on a table or a column.
      - whether a constraint is deferrable, or was added NOT VALID.
    """

    EXTRACTORS: ClassVar[abc.Sequence[TableElementExtractor]] = (
        ColumnExtractor(),
        PrimaryKeyExtractor(),
        IndexExtractor(),
        UniqueConstraintExtractor(),
        ForeignKeyExtractor(),
        CheckConstraintExtractor(),
    )

    def __init__(self, model_tables: abc.Mapping[str, Table], database_tables: abc.Mapping[str, Table]) -> None:
        """
        The two sets of tables are compared here, so that the result describes them as they are at this moment.

        :param model_tables: the tables declared by the SQLAlchemy models, keyed by table name.
        :param database_tables: the tables reflected from the database, keyed by table name.
        """
        self.model_tables = model_tables
        self.database_tables = database_tables
        self.differences: abc.Sequence[TableDifference] = self.compare_tables()

    def compare_tables(self) -> abc.Sequence[TableDifference]:
        """
        The differences between the two sets of tables, ordered by table name within each kind of difference.
        """
        differences: list[TableDifference] = [
            TableOnlyDeclaredByModel(name) for name in sorted(self.model_tables.keys() - self.database_tables.keys())
        ]
        differences.extend(
            TableOnlyPresentInDatabase(name) for name in sorted(self.database_tables.keys() - self.model_tables.keys())
        )
        for name in sorted(self.model_tables.keys() & self.database_tables.keys()):
            element_differences = self.compare_elements(self.model_tables[name], self.database_tables[name])
            if element_differences:
                differences.append(TableWithDifferingElements(name, element_differences))
        return differences

    def compare_elements(self, model_table: Table, database_table: Table) -> abc.Sequence[ElementDifference]:
        """
        The differences on every kind of element of a single table, between the table as a model declares it and the
        same table as the database has it.
        """
        differences: list[ElementDifference] = []
        for extractor in self.EXTRACTORS:
            differences.extend(extractor.compare(model_table, database_table))
        return differences

    def format_report(self) -> str:
        """
        The differences as an indented report, one block per table, empty when the two sides agree.
        """
        return "\n".join(difference.format_report() for difference in self.differences)


async def get_database_schema(host: str, port: int, username: str, password: str | None, database: str) -> MetaData:
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
