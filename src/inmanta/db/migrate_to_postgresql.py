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
import sys
import asyncio
import click
import logging
from pymongo import MongoClient
from inmanta import data


LOGGER = logging.getLogger()

TABLES_TO_MIGRATE = [
    data.Project,
    data.Environment,
    data.Parameter,
    data.Form,
    data.FormRecord,
]


@click.command()
@click.option(
    "--mongo-host", help="Host running the MongoDB database.", default="127.0.0.1"
)
@click.option(
    "--mongo-port",
    help="The port on which the MongoDB server is listening.",
    default=27017,
    type=int,
)
@click.option(
    "--mongo-database", help="The name of the MongoDB database.", default="inmanta"
)
@click.option(
    "--pg-host", help="Host running the PostgreSQL database.", default="127.0.0.1"
)
@click.option(
    "--pg-port",
    help="The port on which the PostgreSQL database is listening.",
    default=5432,
    type=int,
)
@click.option(
    "--pg-database", help="The name of the PostgreSQL database.", default="inmanta"
)
@click.option(
    "--pg-username",
    help="The username to use to login on the PostgreSQL database",
    default="inmanta",
)
@click.option(
    "--pg-password",
    help="The password that belongs to user specified with --pg-username",
    prompt=True,
    hide_input=True,
)
def main(
    mongo_host,
    mongo_port,
    mongo_database,
    pg_host,
    pg_port,
    pg_database,
    pg_username,
    pg_password,
):
    """
        Migrate the database of the Inmanta server from MongoDB to PostgreSQL.

        Note: This script only migrates the collections: Project, Environment, Parameter, Form andFormRecord.
    """
    logging.root.handlers = []
    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setLevel(logging.INFO)
    logging.root.addHandler(stream_handler)
    logging.root.setLevel(0)

    loop = asyncio.get_event_loop()
    future = migrate_mongo_to_postgres(
        mongo_host,
        mongo_port,
        mongo_database,
        pg_host,
        pg_port,
        pg_database,
        pg_username,
        pg_password,
    )
    loop.run_until_complete(future)
    loop.close()


async def migrate_mongo_to_postgres(
    mongo_host,
    mongo_port,
    mongo_database,
    pg_host,
    pg_port,
    pg_database,
    pg_username,
    pg_password,
):
    try:
        LOGGER.info(
            "Connecting to MongoDB database %s on %s:%s",
            mongo_database,
            mongo_host,
            mongo_port,
        )
        mongo_client = MongoClient(mongo_host, mongo_port)
        mongo_connection = mongo_client[mongo_database]
        LOGGER.info(
            "Connecting to PostgreSQL database %s on %s:%s",
            pg_database,
            pg_host,
            pg_port,
        )
        await data.connect(
            host=pg_host,
            port=pg_port,
            database=pg_database,
            username=pg_username,
            password=pg_password,
            create_db_schema=True,
        )
        await do_migration(mongo_connection)
    finally:
        if mongo_client:
            mongo_client.close()
        await data.disconnect()

    LOGGER.info("Database migration completed successfully")


async def do_migration(mongo_connection):
    for cls in TABLES_TO_MIGRATE:
        LOGGER.info(f"Migrating collection {cls.__name__} ...")
        records = mongo_connection[cls.__name__].find()
        for record in records:
            # Don't migrate parameters which have a resource_id associated
            if (
                cls == data.Parameter
                and "resource_id" in record
                and record["resource_id"]
            ):
                continue
            args = {}
            for field_name in cls._fields.copy().keys():
                # The _id record in MongoDB is the id record in PostgreSQL
                record_name = "_id" if field_name == "id" else field_name
                if record_name in record:
                    # In the MongoDB database schema, the form field of FormRecord referred to the _id field of the associated
                    # Form. In the PostgreSQL database schema, the form field of FormRecord refers to the form_type field of
                    # Form instead.
                    if cls == data.FormRecord and record_name == "form":
                        record_value = mongo_connection[data.Form.__name__].find_one(
                            {"_id": record["form"]}, {"form_type": True}
                        )["form_type"]
                    else:
                        record_value = record[record_name]
                    args[field_name] = record_value
            await cls(**args).insert()


if __name__ == "__main__":
    main()
