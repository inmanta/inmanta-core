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

import collections
import difflib
from collections.abc import Mapping
from pathlib import Path

import inmanta.data
import sqlalchemy
from sqlacodegen.generators import DeclarativeGenerator
from sqlacodegen.models import RelationshipAttribute

# src/inmanta/data/sqlalchemy_generated.py holds the sqlacodegen output for the current database schema. It is imported
# by src/inmanta/data/sqlalchemy_new.py, which adds the manual modifications (helper methods, hybrid properties and the
# Resource.state relationship) on top of it. This test regenerates the models from the live database and compares them
# against this committed file, so any schema drift that is not yet reflected in the generated models shows up as a
# failure.
GENERATED_MODELS_REFERENCE: Path = Path(inmanta.data.__file__).parent / "sqlalchemy_generated.py"


class ViewonlyDeclarativeGenerator(DeclarativeGenerator):
    """
    A sqlacodegen declarative generator that marks the relationships involved in an ambiguous write target as
    viewonly=True.

    Some tables (agent_modules, unknownparameter) reach their parents through composite foreign keys that all embed the
    `environment` column. As a result multiple relationships claim authorship of that same column, which makes the write
    target ambiguous and causes SQLAlchemy to emit overlap warnings. Marking those relationships viewonly resolves this
    the fail-safe way: they stay usable for reading and joining, but an inconsistent assignment is dropped at flush time
    instead of silently persisting an unpredictable value (which is what the overlaps= alternative would do).

    Only the relationships that actually participate in such a shared-column overlap are marked viewonly; all other
    (unambiguous) relationships stay writable.
    """

    def _ambiguous_foreign_key_columns(self) -> frozenset[sqlalchemy.Column[object]]:
        """
        Return the columns that take part in more than one foreign key constraint on their table. These are the columns
        for which the write target is ambiguous (e.g. the `environment` column on agent_modules and unknownparameter).
        """
        cached: frozenset[sqlalchemy.Column[object]] | None = getattr(self, "_ambiguous_columns_cache", None)
        if cached is not None:
            return cached
        counts: collections.Counter[sqlalchemy.Column[object]] = collections.Counter()
        for table in self.metadata.tables.values():
            for foreign_key_constraint in table.foreign_key_constraints:
                counts.update(foreign_key_constraint.columns)
        cached = frozenset(column for column, count in counts.items() if count > 1)
        self._ambiguous_columns_cache = cached
        return cached

    def render_relationship_arguments(self, relationship: RelationshipAttribute) -> Mapping[str, object]:
        kwargs = dict(super().render_relationship_arguments(relationship))
        # Many-to-many relationships persist through the association table (handled by `secondary`), not through a
        # shared column on either side, so they are never part of an ambiguous-write overlap.
        if relationship.association_table is None and relationship.constraint is not None:
            ambiguous_columns = self._ambiguous_foreign_key_columns()
            if any(column in ambiguous_columns for column in relationship.constraint.columns):
                kwargs["viewonly"] = True
        return kwargs


def generate_sqlalchemy_models(db_url: str) -> str:
    """
    Generate the SQLAlchemy models for the database reachable at `db_url` using sqlacodegen.

    :param db_url: A synchronous SQLAlchemy database URL (e.g. postgresql+psycopg://user:pass@host:port/dbname).
    """
    engine = sqlalchemy.create_engine(db_url)
    try:
        metadata = sqlalchemy.MetaData()
        generator = ViewonlyDeclarativeGenerator(metadata, engine, options=set())
        metadata.reflect(bind=engine, views=generator.views_supported)
        return generator.generate()
    finally:
        engine.dispose()


def verify_sqlalchemy_models(db_url: str, *, overwrite: bool = False) -> None:
    """
    Generate the SQLAlchemy models from the live database schema using sqlacodegen and compare them against the
    committed reference snapshot.

    :param db_url: A synchronous SQLAlchemy database URL pointing to a database with the current Inmanta schema applied.
    :param overwrite: When True, (re)write the reference snapshot with the freshly generated models instead of comparing.
                      Use this after an intentional database schema change, then reconcile
                      src/inmanta/data/sqlalchemy.py with the new reference by hand.
    """
    generated: str = generate_sqlalchemy_models(db_url)

    if overwrite:
        GENERATED_MODELS_REFERENCE.write_text(generated)
        return

    expected: str = GENERATED_MODELS_REFERENCE.read_text()
    if generated != expected:
        diff: str = "".join(
            difflib.unified_diff(
                expected.splitlines(keepends=True),
                generated.splitlines(keepends=True),
                fromfile=str(GENERATED_MODELS_REFERENCE),
                tofile="sqlacodegen output",
            )
        )
        raise AssertionError(
            "The SQLAlchemy models generated from the database no longer match the committed reference "
            f"({GENERATED_MODELS_REFERENCE}).\n"
            "If this is the result of an intentional schema change, regenerate the reference by running this test "
            "with overwrite=True and update src/inmanta/data/sqlalchemy.py accordingly.\n\n"
            f"{diff}"
        )


async def test_sqlalchemy_models_up_to_date(postgres_db, database_name, init_dataclasses_and_load_schema) -> None:
    """
    Verify that the SQLAlchemy models generated from the current database schema match the committed reference snapshot.

    The init_dataclasses_and_load_schema fixture applies the full Inmanta database schema to the test database, so the
    models generated here reflect the latest schema version.
    """
    db_url: str = sqlalchemy.engine.URL.create(
        drivername="postgresql+psycopg",
        username=postgres_db.user,
        password=postgres_db.password or None,
        host=postgres_db.host,
        port=postgres_db.port,
        database=database_name,
    ).render_as_string(hide_password=False)

    verify_sqlalchemy_models(db_url, overwrite=False)
