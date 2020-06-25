"""
    Copyright 2017 Inmanta

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
import asyncio
import copy
import datetime
import enum
import hashlib
import json
import logging
import uuid
import warnings
from collections import defaultdict
from configparser import RawConfigParser
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple, Type, TypeVar, Union, cast

import asyncpg
from asyncpg.protocol import Record

import inmanta.db.versions
from inmanta import const, util
from inmanta.const import DONE_STATES, UNDEPLOYABLE_NAMES, AgentStatus, ResourceState
from inmanta.data import model as m
from inmanta.data import schema
from inmanta.resources import Id
from inmanta.server import config
from inmanta.types import JsonType, PrimitiveTypes

LOGGER = logging.getLogger(__name__)

DBLIMIT = 100000


# TODO: disconnect
# TODO: difference between None and not set


def json_encode(value: Any) -> str:
    # see json_encode in tornado.escape
    return json.dumps(value, default=util.custom_json_encoder)


class Field(object):
    def __init__(self, field_type, required=False, unique=False, reference=False, part_of_primary_key=False, **kwargs) -> None:

        self._field_type = field_type
        self._required = required
        self._reference = reference
        self._part_of_primary_key = part_of_primary_key

        if "default" in kwargs:
            self._default = True
            self._default_value = kwargs["default"]
        else:
            self._default = False
            self._default_value = None

        self._unique = unique

    def get_field_type(self):
        return self._field_type

    field_type = property(get_field_type)

    def is_required(self) -> bool:
        return self._required

    required = property(is_required)

    def get_default(self) -> bool:
        return self._default

    default = property(get_default)

    def get_default_value(self) -> Any:
        return copy.copy(self._default_value)

    default_value = property(get_default_value)

    def is_unique(self) -> bool:
        return self._unique

    unique = property(is_unique)

    def is_reference(self) -> bool:
        return self._reference

    reference = property(is_reference)

    def is_part_of_primary_key(self) -> bool:
        return self._part_of_primary_key

    part_of_primary_key = property(is_part_of_primary_key)


class DataDocument(object):
    """
        A baseclass for objects that represent data in inmanta. The main purpose of this baseclass is to group dict creation
        logic. These documents are not stored in the database
        (use BaseDocument for this purpose). It provides a to_dict method that the inmanta rpc can serialize. You can store
        DataDocument childeren in BaseDocument fields, they will be serialized to dict. However, on retrieval this is not
        performed.
    """

    def __init__(self, **kwargs):
        self._data = kwargs

    def to_dict(self) -> JsonType:
        """
            Return a dict representation of this object.
        """
        return self._data


class DocumentMeta(type):
    def __new__(cls, class_name, bases, dct):
        dct["_fields"] = {}
        for name, field in dct.items():
            if isinstance(field, Field):
                dct["_fields"][name] = field

        for base in bases:
            if hasattr(base, "_fields"):
                dct["_fields"].update(base._fields)

        return type.__new__(cls, class_name, bases, dct)


T = TypeVar("T")


class BaseDocument(object, metaclass=DocumentMeta):
    """
        A base document in the database. Subclasses of this document determine collections names. This type is mainly used to
        bundle query methods and generate validate and query methods for optimized DB access. This is not a full ODM.
    """

    _connection_pool: asyncpg.pool.Pool = None

    @classmethod
    def get_connection(cls) -> asyncpg.pool.PoolAcquireContext:
        """
            Returns a PoolAcquireContext that can be either awaited or used in an async with statement to receive a Connection.
        """
        return cls._connection_pool.acquire()

    @classmethod
    def table_name(cls) -> str:
        """
            Return the name of the collection
        """
        return cls.__name__.lower()

    def __init__(self, from_postgres: bool = False, **kwargs: Any) -> None:
        self.__fields = self._create_dict_wrapper(from_postgres, kwargs)

    @classmethod
    def _create_dict(cls, from_postgres: bool, kwargs: Dict[str, Any]) -> JsonType:
        result = {}
        fields = cls._fields.copy()

        if "id" in fields and "id" not in kwargs:
            kwargs["id"] = cls._new_id()

        for name, value in kwargs.items():
            if name not in fields:
                raise AttributeError("%s field is not defined for this document %s" % (name, cls.table_name()))

            if value is None and fields[name].required:
                raise TypeError("%s field is required" % name)

            if (
                not fields[name].reference
                and value is not None
                and not (value.__class__ is fields[name].field_type or isinstance(value, fields[name].field_type))
            ):
                # pgasync does not convert a jsonb field to a dict
                if from_postgres and isinstance(value, str) and fields[name].field_type is dict:
                    value = json.loads(value)
                # pgasync does not convert a enum field to a enum type
                elif from_postgres and isinstance(value, str) and issubclass(fields[name].field_type, enum.Enum):
                    value = fields[name].field_type[value]
                else:
                    raise TypeError(
                        "Field %s should have the correct type (%s instead of %s)"
                        % (name, fields[name].field_type.__name__, type(value).__name__)
                    )

            if from_postgres or value is not None:
                result[name] = value
            elif fields[name].default:
                result[name] = fields[name].default_value

            del fields[name]

        for name in list(fields.keys()):
            if fields[name].default:
                result[name] = fields[name].default_value
                del fields[name]

            elif not fields[name].required:
                del fields[name]

        if len(fields) > 0:
            raise AttributeError("%s fields are required." % ", ".join(fields.keys()))

        return result

    @classmethod
    def _get_names_of_primary_key_fields(cls) -> List[str]:
        fields = cls._fields.copy()
        return [name for name, value in fields.items() if value.is_part_of_primary_key()]

    def _get_filter_on_primary_key_fields(self, offset: int = 1) -> Tuple[str, List[Any]]:
        names_primary_key_fields = self._get_names_of_primary_key_fields()
        query = {field_name: self.__getattribute__(field_name) for field_name in names_primary_key_fields}
        return self._get_composed_filter(offset=offset, **query)

    @classmethod
    def _create_dict_wrapper(cls, from_postgres, kwargs):
        return cls._create_dict(from_postgres, kwargs)

    @classmethod
    def _new_id(cls):
        """
            Generate a new ID. Override to use something else than uuid4
        """
        return uuid.uuid4()

    @classmethod
    def set_connection_pool(cls, pool: asyncpg.pool.Pool) -> None:
        if cls._connection_pool:
            raise Exception(f"Connection already set on {cls} ({cls._connection_pool}!")
        cls._connection_pool = pool

    @classmethod
    async def close_connection_pool(cls) -> None:
        if not cls._connection_pool:
            return
        try:
            await asyncio.wait_for(cls._connection_pool.close(), config.db_connection_timeout.get())
        except asyncio.TimeoutError:
            cls._connection_pool.terminate()
        finally:
            cls._connection_pool = None

    def _get_field(self, name):
        if hasattr(self.__class__, name):
            field = getattr(self.__class__, name)
            if isinstance(field, Field):
                return field

        return None

    def __getattribute__(self, name):
        if name[0] == "_":
            return object.__getattribute__(self, name)

        field = self._get_field(name)
        if field is not None:
            if name in self.__fields:
                return self.__fields[name]
            else:
                return None

        return object.__getattribute__(self, name)

    def __setattr__(self, name, value):
        if name[0] == "_":
            return object.__setattr__(self, name, value)

        field = self._get_field(name)
        if field is not None:
            # validate
            if value is not None and not isinstance(value, field.field_type):
                raise TypeError("Field %s should be of type %s" % (name, field.field_type))

            self.__fields[name] = value
            return

        raise AttributeError(name)

    @classmethod
    def _convert_field_names_to_db_column_names(cls, field_dict: Dict[str, Any]) -> Dict[str, Any]:
        return field_dict

    def _get_column_names_and_values(self) -> Tuple[List[str], List[str]]:
        column_names: List[str] = []
        values: List[str] = []
        for name, typing in self._fields.items():
            if self._fields[name].reference:
                continue
            value = None
            if name in self.__fields:
                value = self.__fields[name]

            if typing.required and value is None:
                raise TypeError("%s should have field '%s'" % (self.__name__, name))

            if value is not None:
                if not isinstance(value, typing.field_type):
                    raise TypeError("Value of field %s does not have the correct type" % name)
            column_names.append(name)
            values.append(self._get_value(value))

        return (column_names, values)

    async def insert(self, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        """
            Insert a new document based on the instance passed. Validation is done based on the defined fields.
        """
        (column_names, values) = self._get_column_names_and_values()
        column_names_as_sql_string = ",".join(column_names)
        values_as_parameterize_sql_string = ",".join(["$" + str(i) for i in range(1, len(values) + 1)])
        query = (
            "INSERT INTO "
            + self.table_name()
            + " ("
            + column_names_as_sql_string
            + ") "
            + "VALUES ("
            + values_as_parameterize_sql_string
            + ")"
        )
        await self._execute_query(query, *values, connection=connection)

    @classmethod
    async def _fetchval(cls, query, *values):
        async with cls._connection_pool.acquire() as con:
            return await con.fetchval(query, *values)

    @classmethod
    async def _fetchrow(cls, query, *values) -> Record:
        async with cls._connection_pool.acquire() as con:
            return await con.fetchrow(query, *values)

    @classmethod
    async def _fetch_query(cls, query, *values, connection: Optional[asyncpg.connection.Connection] = None):
        if connection is None:
            async with cls._connection_pool.acquire() as con:
                return await con.fetch(query, *values)
        return await connection.fetch(query, *values)

    @classmethod
    async def _execute_query(cls, query, *values, connection: Optional[asyncpg.connection.Connection] = None) -> str:
        if connection:
            return await connection.execute(query, *values)
        async with cls._connection_pool.acquire() as con:
            return await con.execute(query, *values)

    @classmethod
    async def insert_many(cls, documents: Sequence["BaseDocument"]) -> None:
        """
            Insert multiple objects at once
        """
        if not documents:
            return

        columns = list(cls._fields.copy().keys())
        records = []
        for doc in documents:
            current_record = []
            for col in columns:
                current_record.append(cls._get_value(doc.__getattribute__(col)))
            current_record = tuple(current_record)
            records.append(current_record)

        async with cls._connection_pool.acquire() as con:
            await con.copy_records_to_table(table_name=cls.table_name(), columns=columns, records=records)

    def add_default_values_when_undefined(self, **kwargs):
        result = dict(kwargs)
        for name, field in self._fields.items():
            if name not in kwargs:
                default_value = field.default_value
                result[name] = default_value
        return result

    async def update(self, **kwargs: Any) -> None:
        """
            Update this document in the database. It will update the fields in this object and send a full update to database.
            Use update_fields to only update specific fields.
        """
        kwargs = self._convert_field_names_to_db_column_names(kwargs)
        for name, value in kwargs.items():
            setattr(self, name, value)
        (column_names, values) = self._get_column_names_and_values()
        values_as_parameterize_sql_string = ",".join([column_names[i - 1] + "=$" + str(i) for i in range(1, len(values) + 1)])
        (filter_statement, values_for_filter) = self._get_filter_on_primary_key_fields(offset=len(column_names) + 1)
        values = values + values_for_filter
        query = "UPDATE " + self.table_name() + " SET " + values_as_parameterize_sql_string + " WHERE " + filter_statement
        await self._execute_query(query, *values)

    def _get_set_statement(self, **kwargs):
        counter = 1
        parts_of_set_statement = []
        values = []
        for name, value in kwargs.items():
            setattr(self, name, value)
            parts_of_set_statement.append(name + "=$" + str(counter))
            values.append(self._get_value(value))
            counter += 1
        set_statement = ",".join(parts_of_set_statement)
        return (set_statement, values)

    async def update_fields(self, connection: Optional[asyncpg.connection.Connection] = None, **kwargs: Any) -> None:
        """
            Update the given fields of this document in the database. It will update the fields in this object and do a specific
            $set in the database on this document.
        """
        if len(kwargs) == 0:
            return
        kwargs = self._convert_field_names_to_db_column_names(kwargs)
        for name, value in kwargs.items():
            setattr(self, name, value)
        (set_statement, values_set_statement) = self._get_set_statement(**kwargs)
        (filter_statement, values_for_filter) = self._get_filter_on_primary_key_fields(offset=len(kwargs) + 1)
        values = values_set_statement + values_for_filter
        query = "UPDATE " + self.table_name() + " SET " + set_statement + " WHERE " + filter_statement
        await self._execute_query(query, *values, connection=connection)

    @classmethod
    async def get_by_id(cls: Type[T], doc_id: uuid.UUID) -> Optional[T]:
        """
            Get a specific document based on its ID

            :return: An instance of this class with its fields filled from the database.
        """
        result = await cls.get_list(id=doc_id)
        if len(result) > 0:
            return result[0]
        return None

    @classmethod
    async def get_one(cls: Type[T], connection: Optional[asyncpg.connection.Connection] = None, **query) -> T:
        results = await cls.get_list(connection=connection, **query)
        if results:
            return results[0]

    @classmethod
    async def get_list(
        cls: Type[T],
        order_by_column: str = None,
        order: str = "ASC",
        limit: int = None,
        offset: int = None,
        no_obj: bool = False,
        connection: Optional[asyncpg.connection.Connection] = None,
        **query: Any,
    ) -> List[T]:
        """
            Get a list of documents matching the filter args
        """
        query = cls._convert_field_names_to_db_column_names(query)
        (filter_statement, values) = cls._get_composed_filter(**query)
        sql_query = "SELECT * FROM " + cls.table_name()
        if filter_statement:
            sql_query += " WHERE " + filter_statement
        if order_by_column is not None:
            sql_query += " ORDER BY " + str(order_by_column) + " " + str(order)
        if limit is not None and limit > 0:
            sql_query += " LIMIT " + str(limit)
        if offset is not None and offset > 0:
            sql_query += " OFFSET " + str(offset)
        result = await cls.select_query(sql_query, values, no_obj=no_obj, connection=connection)
        return result

    @classmethod
    async def delete_all(cls, connection: Optional[asyncpg.connection.Connection] = None, **query):
        """
            Delete all documents that match the given query
        """
        query = cls._convert_field_names_to_db_column_names(query)
        (filter_statement, values) = cls._get_composed_filter(**query)
        query = "DELETE FROM " + cls.table_name()
        if filter_statement:
            query += " WHERE " + filter_statement
        result = await cls._execute_query(query, *values, connection=connection)
        record_count = int(result.split(" ")[1])
        return record_count

    @classmethod
    def _get_composed_filter(cls, offset: int = 1, col_name_prefix: str = None, **query: Any) -> Tuple[str, List[Any]]:
        filter_statements = []
        values = []
        index_count = max(1, offset)
        for key, value in query.items():
            (filter_statement, value) = cls._get_filter(key, value, index_count, col_name_prefix=col_name_prefix)
            filter_statements.append(filter_statement)
            if value is not None:
                values.append(value)
                index_count += 1
        filter_as_string = " AND ".join(filter_statements)
        return (filter_as_string, values)

    @classmethod
    def _get_filter(cls, name: str, value: Any, index: int, col_name_prefix: str = None) -> Tuple[str, Any]:
        if value is None:
            return (name + " IS NULL", None)
        filter_statement = name + "=$" + str(index)
        if col_name_prefix is not None:
            filter_statement = col_name_prefix + "." + filter_statement
        value = cls._get_value(value)
        return (filter_statement, value)

    @classmethod
    def _get_value(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return json_encode(value)

        if isinstance(value, DataDocument) or issubclass(value.__class__, DataDocument):
            return json_encode(value)

        if isinstance(value, list):
            return [cls._get_value(x) for x in value]

        if isinstance(value, enum.Enum):
            return value.name

        if isinstance(value, uuid.UUID):
            return str(value)

        return value

    async def delete(self, connection: asyncpg.connection.Connection = None) -> None:
        """
            Delete this document
        """
        (filter_as_string, values) = self._get_filter_on_primary_key_fields()
        query = "DELETE FROM " + self.table_name() + " WHERE " + filter_as_string
        await self._execute_query(query, *values, connection=connection)

    async def delete_cascade(self) -> None:
        await self.delete()

    @classmethod
    async def select_query(cls, query, values, no_obj=False, connection: Optional[asyncpg.connection.Connection] = None):
        async def perform_query(con: asyncpg.connection.Connection) -> object:
            async with con.transaction():
                result = []
                async for record in con.cursor(query, *values):
                    if no_obj:
                        result.append(record)
                    else:
                        result.append(cls(from_postgres=True, **record))
                return result

        if connection is None:
            async with cls._connection_pool.acquire() as con:
                return await perform_query(con)
        return await perform_query(connection)

    def to_dict(self) -> JsonType:
        """
            Return a dict representing the document
        """
        result = {}
        for name, typing in self._fields.items():
            value = None
            if name in self.__fields:
                value = self.__fields[name]

            if typing.required and value is None:
                raise TypeError("%s should have field '%s'" % (self.__name__, name))

            if value is not None:
                if not isinstance(value, typing.field_type):
                    raise TypeError("Value of field %s does not have the correct type" % name)

                result[name] = value

            elif typing.default:
                result[name] = typing.default_value

        return result


class Project(BaseDocument):
    """
        An inmanta configuration project

        :param name: The name of the configuration project.
    """

    id: uuid.UUID = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)
    name: str = Field(field_type=str, required=True, unique=True)

    def to_dto(self) -> m.Project:
        return m.Project(id=self.id, name=self.name, environments=[])


def convert_boolean(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    if value.lower() not in RawConfigParser.BOOLEAN_STATES:
        raise ValueError("Not a boolean: %s" % value)
    return RawConfigParser.BOOLEAN_STATES[value.lower()]


def convert_int(value: Any) -> Union[int, float]:
    if isinstance(value, (int, float)):
        return value

    f_value = float(value)
    i_value = int(value)

    if i_value == f_value:
        return i_value
    return f_value


def convert_agent_map(value: Dict[str, str]) -> Dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError("Agent map should be a dict")

    for key, v in value.items():
        if not isinstance(key, str):
            raise ValueError("The key of an agent map should be string")

        if not isinstance(v, str):
            raise ValueError("The value of an agent map should be string")

    if "internal" not in value:
        raise ValueError("The internal agent must be present in the autostart_agent_map")

    return value


def translate_to_postgres_type(type):
    if type not in TYPE_MAP:
        raise Exception("Type '" + type + "' is not a valid type for a settings entry")
    return TYPE_MAP[type]


def convert_agent_trigger_method(value):
    if isinstance(value, const.AgentTriggerMethod):
        return value
    value = str(value)
    valid_values = [x.name for x in const.AgentTriggerMethod]
    if value not in valid_values:
        raise ValueError("%s is not a valid agent trigger method. Valid value: %s" % (value, ",".join(valid_values)))
    return value


TYPE_MAP = {"int": "integer", "bool": "boolean", "dict": "jsonb", "str": "varchar", "enum": "varchar"}

AUTO_DEPLOY = "auto_deploy"
PUSH_ON_AUTO_DEPLOY = "push_on_auto_deploy"
AGENT_TRIGGER_METHOD_ON_AUTO_DEPLOY = "agent_trigger_method_on_auto_deploy"
AUTOSTART_SPLAY = "autostart_splay"
AUTOSTART_AGENT_DEPLOY_INTERVAL = "autostart_agent_deploy_interval"
AUTOSTART_AGENT_DEPLOY_SPLAY_TIME = "autostart_agent_deploy_splay_time"
AUTOSTART_AGENT_REPAIR_INTERVAL = "autostart_agent_repair_interval"
AUTOSTART_AGENT_REPAIR_SPLAY_TIME = "autostart_agent_repair_splay_time"
AUTOSTART_ON_START = "autostart_on_start"
AUTOSTART_AGENT_MAP = "autostart_agent_map"
AUTOSTART_AGENT_INTERVAL = "autostart_agent_interval"
AGENT_AUTH = "agent_auth"
SERVER_COMPILE = "server_compile"
RESOURCE_ACTION_LOGS_RETENTION = "resource_action_logs_retention"
PURGE_ON_DELETE = "purge_on_delete"
PROTECTED_ENVIRONMENT = "protected_environment"


class Setting(object):
    """
        A class to define a new environment setting.
    """

    def __init__(
        self,
        name: str,
        typ: str,
        default: m.EnvSettingType = None,
        doc: str = None,
        validator: Callable[[m.EnvSettingType], m.EnvSettingType] = None,
        recompile: bool = False,
        update_model: bool = False,
        agent_restart: bool = False,
        allowed_values: Optional[List[m.EnvSettingType]] = None,
    ):
        """
            :param name: The name of the setting.
            :param type: The type of the value. This type is mainly used for documentation purpose.
            :param default: An optional default value for this setting. When a default is set and the
                            is requested from the database, it will return the default value and also store
                            the default value in the database.
            :param doc: The documentation/help string for this setting
            :param validator: A validation and casting function for input settings.
            :param recompile: Trigger a recompile of the model when a setting is updated?
            :param update_model: Update the configuration model (git pull on project and repos)
            :param agent_restart: Restart autostarted agents when this settings is updated.
            :param allowed_values: list of possible values (if type is enum)
        """
        self.name: str = name
        self.typ: str = typ
        self.default = default
        self.doc = doc
        self.validator = validator
        self.recompile = recompile
        self.update = update_model
        self.agent_restart = agent_restart
        self.allowed_values = allowed_values

    def to_dict(self) -> JsonType:
        return {
            "type": self.typ,
            "default": self.default,
            "doc": self.doc,
            "recompile": self.recompile,
            "update": self.update,
            "agent_restart": self.agent_restart,
            "allowed_values": self.allowed_values,
        }

    def to_dto(self) -> m.EnvironmentSetting:
        return m.EnvironmentSetting(
            name=self.name,
            type=self.typ,
            default=self.default,
            doc=self.doc,
            recompile=self.recompile,
            update_model=self.update,
            agent_restart=self.agent_restart,
            allowed_values=self.allowed_values,
        )


class Environment(BaseDocument):
    """
        A deployment environment of a project

        :param id: A unique, machine generated id
        :param name: The name of the deployment environment.
        :param project: The project this environment belongs to.
        :param repo_url: The repository url that contains the configuration model code for this environment
        :param repo_branch: The repository branch that contains the configuration model code for this environment
        :param settings: Key/value settings for this environment
        :param last_version: The last version number that was reserved for this environment
    """

    id: uuid.UUID = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)
    name: str = Field(field_type=str, required=True)
    project: uuid.UUID = Field(field_type=uuid.UUID, required=True)
    repo_url: str = Field(field_type=str, default="")
    repo_branch: str = Field(field_type=str, default="")
    settings: Dict[str, m.EnvSettingType] = Field(field_type=dict, default={})
    last_version: int = Field(field_type=int, default=0)

    def to_dto(self) -> m.Environment:
        return m.Environment(
            id=self.id,
            name=self.name,
            project_id=self.project,
            repo_url=self.repo_url,
            repo_branch=self.repo_branch,
            settings=self.settings,
        )

    _settings: Dict[str, Setting] = {
        AUTO_DEPLOY: Setting(
            name=AUTO_DEPLOY,
            typ="bool",
            default=True,
            doc="When this boolean is set to true, the orchestrator will automatically release a new version "
            "that was compiled by the orchestrator itself.",
            validator=convert_boolean,
        ),
        PUSH_ON_AUTO_DEPLOY: Setting(
            name=PUSH_ON_AUTO_DEPLOY,
            typ="bool",
            default=True,
            doc="Push a new version when it has been autodeployed.",
            validator=convert_boolean,
        ),
        AGENT_TRIGGER_METHOD_ON_AUTO_DEPLOY: Setting(
            name=AGENT_TRIGGER_METHOD_ON_AUTO_DEPLOY,
            typ="enum",
            default=const.AgentTriggerMethod.push_incremental_deploy.name,
            validator=convert_agent_trigger_method,
            doc="The agent trigger method to use when " + PUSH_ON_AUTO_DEPLOY + " is enabled",
            allowed_values=[opt.name for opt in const.AgentTriggerMethod],
        ),
        AUTOSTART_SPLAY: Setting(
            name=AUTOSTART_SPLAY,
            typ="int",
            default=10,
            doc="[DEPRECATED] Splay time for autostarted agents.",
            validator=convert_int,
        ),
        AUTOSTART_AGENT_DEPLOY_INTERVAL: Setting(
            name=AUTOSTART_AGENT_DEPLOY_INTERVAL,
            typ="int",
            default=600,
            doc="The deployment interval of the autostarted agents."
            " See also: :inmanta.config:option:`config.agent-deploy-interval`",
            validator=convert_int,
            agent_restart=True,
        ),
        AUTOSTART_AGENT_DEPLOY_SPLAY_TIME: Setting(
            name=AUTOSTART_AGENT_DEPLOY_SPLAY_TIME,
            typ="int",
            default=10,
            doc="The splay time on the deployment interval of the autostarted agents."
            " See also: :inmanta.config:option:`config.agent-deploy-splay-time`",
            validator=convert_int,
            agent_restart=True,
        ),
        AUTOSTART_AGENT_REPAIR_INTERVAL: Setting(
            name=AUTOSTART_AGENT_REPAIR_INTERVAL,
            typ="int",
            default=86400,
            doc="The repair interval of the autostarted agents."
            " See also: :inmanta.config:option:`config.agent-repair-interval`",
            validator=convert_int,
            agent_restart=True,
        ),
        AUTOSTART_AGENT_REPAIR_SPLAY_TIME: Setting(
            name=AUTOSTART_AGENT_REPAIR_SPLAY_TIME,
            typ="int",
            default=600,
            doc="The splay time on the repair interval of the autostarted agents."
            " See also: :inmanta.config:option:`config.agent-repair-splay-time`",
            validator=convert_int,
            agent_restart=True,
        ),
        AUTOSTART_ON_START: Setting(
            name=AUTOSTART_ON_START,
            default=True,
            typ="bool",
            validator=convert_boolean,
            doc="Automatically start agents when the server starts instead of only just in time.",
        ),
        AUTOSTART_AGENT_MAP: Setting(
            name=AUTOSTART_AGENT_MAP,
            default={"internal": "local:"},
            typ="dict",
            validator=convert_agent_map,
            doc="A dict with key the name of agents that should be automatically started. The value "
            "is either an empty string or an agent map string. See also: :inmanta.config:option:`config.agent-map`",
            agent_restart=True,
        ),
        AUTOSTART_AGENT_INTERVAL: Setting(
            name=AUTOSTART_AGENT_INTERVAL,
            default=600,
            typ="int",
            validator=convert_int,
            doc="[DEPRECATED] Agent interval for autostarted agents in seconds",
            agent_restart=True,
        ),
        SERVER_COMPILE: Setting(
            name=SERVER_COMPILE,
            default=True,
            typ="bool",
            validator=convert_boolean,
            doc="Allow the server to compile the configuration model.",
        ),
        RESOURCE_ACTION_LOGS_RETENTION: Setting(
            name=RESOURCE_ACTION_LOGS_RETENTION,
            default=7,
            typ="int",
            validator=convert_int,
            doc="The number of days to retain resource-action logs",
        ),
        PURGE_ON_DELETE: Setting(
            name=PURGE_ON_DELETE,
            default=True,
            typ="bool",
            validator=convert_boolean,
            doc="Enable purge on delete. When set to true, the server will detect the absence of resources with purge_on_delete"
            " set to true and automatically purges them.",
        ),
        PROTECTED_ENVIRONMENT: Setting(
            name=PROTECTED_ENVIRONMENT,
            default=False,
            typ="bool",
            validator=convert_boolean,
            doc="When set to true, this environment cannot be cleared or deleted.",
        ),
    }

    _renamed_settings_map = {
        AUTOSTART_AGENT_DEPLOY_INTERVAL: AUTOSTART_AGENT_INTERVAL,
        AUTOSTART_AGENT_DEPLOY_SPLAY_TIME: AUTOSTART_SPLAY,
    }  # name new_option -> name deprecated_option

    async def get(self, key: str, connection: Optional[asyncpg.connection.Connection] = None) -> m.EnvSettingType:
        """
            Get a setting in this environment.

            :param key: The name/key of the setting. It should be defined in _settings otherwise a keyerror will be raised.
        """
        if key not in self._settings:
            raise KeyError()

        if key in self._renamed_settings_map:
            name_deprecated_setting = self._renamed_settings_map[key]
            if name_deprecated_setting in self.settings and key not in self.settings:
                warnings.warn(
                    "Config option %s is deprecated. Use %s instead." % (name_deprecated_setting, key),
                    category=DeprecationWarning,
                )
                return self.settings[name_deprecated_setting]

        if key in self.settings:
            return self.settings[key]

        if self._settings[key].default is None:
            raise KeyError()

        value = self._settings[key].default
        await self.set(key, value, connection=connection)
        return value

    async def set(self, key: str, value: m.EnvSettingType, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        """
            Set a new setting in this environment.

            :param key: The name/key of the setting. It should be defined in _settings otherwise a keyerror will be raised.
            :param value: The value of the settings. The value should be of type as defined in _settings
        """
        if key not in self._settings:
            raise KeyError()
        # TODO: convert this to a string
        if callable(self._settings[key].validator):
            value = self._settings[key].validator(value)

        type = translate_to_postgres_type(self._settings[key].typ)
        (filter_statement, values) = self._get_composed_filter(name=self.name, project=self.project, offset=3)
        query = (
            "UPDATE "
            + self.table_name()
            + " SET settings=jsonb_set(settings, $1::text[], to_jsonb($2::"
            + type
            + "), TRUE)"
            + " WHERE "
            + filter_statement
        )
        values = [self._get_value([key]), self._get_value(value)] + values
        await self._execute_query(query, *values, connection=connection)
        self.settings[key] = value

    async def unset(self, key: str) -> None:
        """
            Unset a setting in this environment. If a default value is provided, this value will replace the current value.

            :param key: The name/key of the setting. It should be defined in _settings otherwise a keyerror will be raised.
        """
        if key not in self._settings:
            raise KeyError()

        if self._settings[key].default is None:
            (filter_statement, values) = self._get_composed_filter(name=self.name, project=self.project, offset=2)
            query = "UPDATE " + self.table_name() + " SET settings=settings - $1" + " WHERE " + filter_statement
            values = [self._get_value(key)] + values
            await self._execute_query(query, *values)
            del self.settings[key]
        else:
            await self.set(key, self._settings[key].default)

    async def delete_cascade(self, only_content: bool = False) -> None:
        if only_content:
            await Agent.delete_all(environment=self.id)

            procs = await AgentProcess.get_list(environment=self.id)
            for proc in procs:
                await proc.delete_cascade()

            compile_list = await Compile.get_list(environment=self.id)
            for cl in compile_list:
                await cl.delete_cascade()

            for model in await ConfigurationModel.get_list(environment=self.id):
                await model.delete_cascade()

            await Parameter.delete_all(environment=self.id)
            await Resource.delete_all(environment=self.id)
            await ResourceAction.delete_all(environment=self.id)
        else:
            # Cascade is done by PostgreSQL
            await self.delete()

    async def get_next_version(self) -> int:
        record = await self._fetchrow(
            f"""
UPDATE {self.table_name()}
SET last_version = last_version + 1
WHERE id = $1
RETURNING last_version;
""",
            self.id,
        )
        version = cast(int, record[0])
        self.last_version = version
        return version


class Parameter(BaseDocument):
    """
        A parameter that can be used in the configuration model
        Any transactions that update Parameter should adhere to the locking order described in
        :py:class:`inmanta.data.ConfigurationModel`.

        :param name: The name of the parameter
        :param value: The value of the parameter
        :param environment: The environment this parameter belongs to
        :param source: The source of the parameter
        :param resource_id: An optional resource id
        :param updated: When was the parameter updated last

        :todo Add history
    """

    id: uuid.UUID = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)
    name: str = Field(field_type=str, required=True, part_of_primary_key=True)
    value: str = Field(field_type=str, default="", required=True)
    environment: uuid.UUID = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)
    source: str = Field(field_type=str, required=True)
    resource_id: m.ResourceIdStr = Field(field_type=str, default="")
    updated: datetime.datetime = Field(field_type=datetime.datetime)
    metadata: Dict[str, Any] = Field(field_type=dict)

    @classmethod
    async def get_updated_before(cls, updated_before: datetime.datetime) -> List["Parameter"]:
        query = "SELECT * FROM " + cls.table_name() + " WHERE updated < $1"
        values = [cls._get_value(updated_before)]
        result = await cls.select_query(query, values)
        return result

    @classmethod
    async def list_parameters(cls, env_id: uuid.UUID, **metadata_constraints: str) -> List["Parameter"]:
        query = "SELECT * FROM " + cls.table_name() + " WHERE environment=$1"
        values = [cls._get_value(env_id)]
        for key, value in metadata_constraints.items():
            query_param_index = len(values) + 1
            query += " AND metadata @> $" + str(query_param_index) + "::jsonb"
            dict_value = {key: value}
            values.append(cls._get_value(dict_value))
        result = await cls.select_query(query, values)
        return result


class UnknownParameter(BaseDocument):
    """
        A parameter that the compiler indicated that was unknown. This parameter causes the configuration model to be
        incomplete for a specific environment.

        :param name:
        :param resource_id:
        :param source:
        :param environment:
        :param version: The version id of the configuration model on which this parameter was reported
    """

    id: uuid.UUID = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)
    name: str = Field(field_type=str, required=True)
    environment: uuid.UUID = Field(field_type=uuid.UUID, required=True)
    source: str = Field(field_type=str, required=True)
    resource_id: m.ResourceIdStr = Field(field_type=str, default="")
    version: int = Field(field_type=int, required=True)
    metadata: Dict[str, Any] = Field(field_type=dict)
    resolved: bool = Field(field_type=bool, default=False)


class AgentProcess(BaseDocument):
    """
        A process in the infrastructure that has (had) a session as an agent.

        :param hostname: The hostname of the device.
        :param environment: To what environment is this process bound
        :param last_seen: When did the server receive data from the node for the last time.
    """

    hostname: str = Field(field_type=str, required=True)
    environment: uuid.UUID = Field(field_type=uuid.UUID, required=True)
    first_seen: datetime.datetime = Field(field_type=datetime.datetime, default=None)
    last_seen: datetime.datetime = Field(field_type=datetime.datetime, default=None)
    expired: datetime.datetime = Field(field_type=datetime.datetime, default=None)
    sid: uuid.UUID = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)

    @classmethod
    async def get_live(cls, environment: Optional[uuid.UUID] = None) -> List["AgentProcess"]:
        if environment is not None:
            result = await cls.get_list(
                limit=DBLIMIT, environment=environment, expired=None, order_by_column="last_seen", order="ASC NULLS LAST"
            )
        else:
            result = await cls.get_list(limit=DBLIMIT, expired=None, order_by_column="last_seen", order="ASC NULLS LAST")
        return result

    @classmethod
    async def get_live_by_env(cls, env: uuid.UUID) -> List["AgentProcess"]:
        result = await cls.get_live(env)
        return result

    @classmethod
    async def get_by_env(cls, env: uuid.UUID) -> List["AgentProcess"]:
        nodes = await cls.get_list(environment=env, order_by_column="last_seen", order="ASC NULLS LAST")
        return nodes

    @classmethod
    async def get_by_sid(cls, sid: uuid.UUID) -> Optional["AgentProcess"]:
        objects = await cls.get_list(limit=DBLIMIT, expired=None, sid=sid)
        if len(objects) == 0:
            return None
        elif len(objects) > 1:
            LOGGER.exception("Multiple objects with the same unique id found!")
            return objects[0]
        else:
            return objects[0]

    @classmethod
    async def seen(cls, env: uuid.UUID, nodename: str, sid: uuid.UUID, now: datetime.datetime):
        """
            Update the last_seen parameter of the process and mark as not expired.
        """
        proc = await cls.get_one(sid=sid)
        if proc is None:
            proc = cls(hostname=nodename, environment=env, first_seen=now, last_seen=now, sid=sid)
            await proc.insert()
        else:
            await proc.update_fields(last_seen=now, expired=None)

    @classmethod
    async def update_last_seen(cls, sid: uuid.UUID, last_seen: datetime.datetime) -> None:
        aps = await cls.get_by_sid(sid=sid)
        if aps:
            await aps.update_fields(last_seen=last_seen)

    @classmethod
    async def expire_process(cls, sid: uuid.UUID, now: datetime.datetime) -> None:
        aps = await cls.get_by_sid(sid=sid)
        if aps is not None:
            await aps.update_fields(expired=now)

    def to_dict(self) -> JsonType:
        result = super(AgentProcess, self).to_dict()
        # Ensure backward compatibility API
        result["id"] = result["sid"]
        return result


class AgentInstance(BaseDocument):
    """
        A physical server/node in the infrastructure that reports to the management server.

        :param hostname: The hostname of the device.
        :param last_seen: When did the server receive data from the node for the last time.
    """

    # TODO: add env to speed up cleanup
    id = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)
    process = Field(field_type=uuid.UUID, required=True)
    name = Field(field_type=str, required=True)
    expired = Field(field_type=datetime.datetime)
    tid = Field(field_type=uuid.UUID, required=True)

    @classmethod
    async def active_for(cls, tid, endpoint, process: uuid.UUID = None):
        if process is not None:
            objects = await cls.get_list(expired=None, tid=tid, name=endpoint, process=process)
        else:
            objects = await cls.get_list(expired=None, tid=tid, name=endpoint)
        return objects

    @classmethod
    async def active(cls):
        objects = await cls.get_list(expired=None)
        return objects

    @classmethod
    async def _expire_endpoints_for_process(
        cls, tid: uuid.UUID, process: uuid.UUID, endpoints: Set[str], now: datetime.datetime
    ) -> None:
        """
            Expire the agent instances for the given endpoints if they are not expired yet.
        """
        if not endpoints:
            return
        names_subquery = ",".join([f"${i}" for i in range(4, 4 + len(endpoints))])
        query = f"""UPDATE {cls.table_name()}
                    SET expired=$1
                    WHERE tid=$2 AND process=$3 AND name IN ({names_subquery}) AND expired IS NULL
                 """
        values = [cls._get_value(now), cls._get_value(tid), cls._get_value(process)] + [cls._get_value(e) for e in endpoints]
        await cls._execute_query(query, *values)

    @classmethod
    async def log_instance_creation(
        cls, tid: uuid.UUID, process: uuid.UUID, endpoints: Set[str], now: datetime.datetime
    ) -> None:
        """
            Create new agent instances for a given session.
        """
        if not endpoints:
            return
        # Fix database corruption when database was down
        await cls._expire_endpoints_for_process(tid, process, endpoints, now)
        for nh in endpoints:
            await cls(tid=tid, process=process, name=nh).insert()

    @classmethod
    async def log_instance_expiry(cls, sid: uuid.UUID, endpoints: Set[str], now: datetime.datetime) -> None:
        """
            Expire specific instances for a given session id.
        """
        if not endpoints:
            return
        instances = await cls.get_list(process=sid)
        for ai in instances:
            if ai.name in endpoints:
                await ai.update_fields(expired=now)


class Agent(BaseDocument):
    """
        An inmanta agent

        :param environment: The environment this resource is defined in
        :param name: The name of this agent
        :param last_failover: Moment at which the primary was last changed
        :param paused: is this agent paused (if so, skip it)
        :param primary: what is the current active instance (if none, state is down)
    """

    environment: uuid.UUID = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)
    name: str = Field(field_type=str, required=True, part_of_primary_key=True)
    last_failover: datetime.datetime = Field(field_type=datetime.datetime)
    paused: bool = Field(field_type=bool, default=False)
    id_primary: Optional[uuid.UUID] = Field(field_type=uuid.UUID)  # AgentInstance

    def set_primary(self, primary: uuid.UUID) -> None:
        self.id_primary = primary

    def get_primary(self) -> Optional[uuid.UUID]:
        return self.id_primary

    def del_primary(self) -> None:
        del self.id_primary

    primary = property(get_primary, set_primary, del_primary)

    @classmethod
    async def get_statuses(cls, env_id: uuid.UUID, agent_names: Set[str]) -> Dict[str, Optional[AgentStatus]]:
        result: Dict[str, Optional[AgentStatus]] = {}
        for agent_name in agent_names:
            agent = await cls.get_one(environment=env_id, name=agent_name)
            if agent:
                result[agent_name] = agent.get_status()
            else:
                result[agent_name] = None
        return result

    def get_status(self) -> AgentStatus:
        if self.paused:
            return AgentStatus.paused
        if self.primary is not None:
            return AgentStatus.up
        return AgentStatus.down

    def to_dict(self) -> JsonType:
        base = BaseDocument.to_dict(self)
        if self.last_failover is None:
            base["last_failover"] = ""

        if self.primary is None:
            base["primary"] = ""
        else:
            base["primary"] = base["id_primary"]
            del base["id_primary"]

        base["state"] = self.get_status().value

        return base

    @classmethod
    def _convert_field_names_to_db_column_names(cls, field_dict):
        if "primary" in field_dict:
            field_dict["id_primary"] = field_dict["primary"]
            del field_dict["primary"]
        return field_dict

    @classmethod
    def _create_dict_wrapper(cls, from_postgres, kwargs):
        kwargs = cls._convert_field_names_to_db_column_names(kwargs)
        return cls._create_dict(from_postgres, kwargs)

    @classmethod
    async def get(cls, env: uuid.UUID, endpoint: str, connection: Optional[asyncpg.connection.Connection] = None) -> "Agent":
        obj = await cls.get_one(environment=env, name=endpoint, connection=connection)
        return obj

    @classmethod
    async def pause(cls, env: uuid.UUID, endpoint: Optional[str], paused: bool) -> List[str]:
        """
            Pause a specific agent or all agents in an environment when endpoint is set to None.

            :return A list of agent names that have been paused/unpaused by this method.
        """
        if endpoint is None:
            query = f"UPDATE {cls.table_name()} SET paused=$1 WHERE environment=$2 RETURNING name"
            values = [cls._get_value(paused), cls._get_value(env)]
        else:
            query = f"UPDATE {cls.table_name()} SET paused=$1 WHERE environment=$2 AND name=$3 RETURNING name"
            values = [cls._get_value(paused), cls._get_value(env), cls._get_value(endpoint)]
        result = await cls._fetch_query(query, *values)
        return sorted([r["name"] for r in result])

    @classmethod
    async def update_primary(
        cls, env: uuid.UUID, endpoints_with_new_primary: Sequence[Tuple[str, Optional[uuid.UUID]]], now: datetime.datetime
    ) -> None:
        """
            Update the primary agent instance for agents present in the database.

            :param env: The environment of the agent
            :param endpoints_with_new_primary: Contains a tuple (agent-name, sid) for each agent that has got a new
                                               primary agent instance. The sid in the tuple is the session id of the new
                                               primary. If the session id is None, the Agent doesn't have a primary anymore.
            :param now: Timestamp of this failover
        """
        for (endpoint, sid) in endpoints_with_new_primary:
            agent = await cls.get(env, endpoint)
            if agent is None:
                continue

            if sid is None:
                await agent.update_fields(last_failover=now, primary=None)
            else:
                instances = await AgentInstance.active_for(tid=env, endpoint=agent.name, process=sid)
                if instances:
                    await agent.update_fields(last_failover=now, primary=instances[0].id)
                else:
                    await agent.update_fields(last_failover=now, primary=None)


class Report(BaseDocument):
    """
        A report of a substep of compilation

        :param started: when the substep started
        :param completed: when it ended
        :param command: the command that was executed
        :param name: The name of this step
        :param errstream: what was reported on system err
        :param outstream: what was reported on system out
    """

    id: uuid.UUID = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)
    started: datetime.datetime = Field(field_type=datetime.datetime, required=True)
    completed: Optional[datetime.datetime] = Field(field_type=datetime.datetime)
    command: str = Field(field_type=str, required=True)
    name: str = Field(field_type=str, required=True)
    errstream: str = Field(field_type=str, default="")
    outstream: str = Field(field_type=str, default="")
    returncode: Optional[int] = Field(field_type=int)
    compile: uuid.UUID = Field(field_type=uuid.UUID, required=True)

    async def update_streams(self, out: str = "", err: str = "") -> None:
        if not out and not err:
            return
        await self._execute_query(
            f"UPDATE {self.table_name()} SET outstream = outstream || $1, errstream = errstream || $2 WHERE id = $3",
            self._get_value(out),
            self._get_value(err),
            self._get_value(self.id),
        )


class Compile(BaseDocument):
    """
        A run of the compiler

        :param environment: The environment this resource is defined in
        :param requested: Time the compile was requested
        :param started: Time the compile started
        :param completed: Time to compile was completed
        :param do_export: should this compiler perform an export
        :param force_update: should this compile definitely update
        :param metadata: exporter metadata to be passed to the compiler
        :param environment_variable: environment variables to be passed to the compiler
        :param succes: was the compile successful
        :param handled: were all registered handlers executed?
        :param version: version exported by this compile
        :param remote_id: id as given by the requestor, used by the requestor to distinguish between different requests
    """

    id: uuid.UUID = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)
    remote_id: Optional[uuid.UUID] = Field(field_type=uuid.UUID)
    environment: uuid.UUID = Field(field_type=uuid.UUID, required=True)
    requested: Optional[datetime.datetime] = Field(field_type=datetime.datetime)
    started: Optional[datetime.datetime] = Field(field_type=datetime.datetime)
    completed: Optional[datetime.datetime] = Field(field_type=datetime.datetime)

    do_export: bool = Field(field_type=bool, default=False)
    force_update: bool = Field(field_type=bool, default=False)
    metadata: dict = Field(field_type=dict, default={})
    environment_variables: dict = Field(field_type=dict)

    success: Optional[bool] = Field(field_type=bool)
    handled: bool = Field(field_type=bool, default=False)
    version: Optional[int] = Field(field_type=int)

    @classmethod
    async def get_reports(
        cls,
        environment_id: uuid.UUID,
        limit: Optional[int] = None,
        start: Optional[datetime.datetime] = None,
        end: Optional[datetime.datetime] = None,
    ) -> List[JsonType]:
        query = "SELECT * FROM " + cls.table_name()
        conditions_in_where_clause = ["environment=$1"]
        values = [cls._get_value(environment_id)]
        if start:
            conditions_in_where_clause.append("started > $" + str(len(values) + 1))
            values.append(cls._get_value(start))
        if end:
            conditions_in_where_clause.append("started < $" + str(len(values) + 1))
            values.append(cls._get_value(end))
        if len(conditions_in_where_clause) > 0:
            query += " WHERE " + " AND ".join(conditions_in_where_clause)
        query += " ORDER BY started DESC"
        if limit:
            query += " LIMIT $" + str(len(values) + 1)
            values.append(cls._get_value(limit))

        return [m.to_dict() for m in await cls.select_query(query, values)]

    @classmethod
    # TODO: Use join
    async def get_report(cls, compile_id: uuid.UUID) -> "Compile":
        """
            Get the compile and the associated reports from the database
        """
        result = await cls.get_by_id(compile_id)
        if result is None:
            return None

        dict_model = result.to_dict()
        reports = await Report.get_list(compile=result.id)
        dict_model["reports"] = [r.to_dict() for r in reports]

        return dict_model

    @classmethod
    async def get_last_run(cls, environment_id: uuid.UUID) -> "Compile":
        """ Get the last run for the given environment
        """
        results = await cls.select_query(
            f"SELECT * FROM {cls.table_name()} where environment=$1 AND completed IS NOT NULL ORDER BY completed DESC LIMIT 1",
            [cls._get_value(environment_id)],
        )
        if not results:
            return None
        return results[0]

    @classmethod
    async def get_next_run(cls, environment_id: uuid.UUID) -> "Compile":
        """ Get the next compile in the queue for the given environment
        """
        results = await cls.select_query(
            f"SELECT * FROM {cls.table_name()} WHERE environment=$1 AND completed IS NULL ORDER BY requested ASC LIMIT 1",
            [cls._get_value(environment_id)],
        )
        if not results:
            return None
        return results[0]

    @classmethod
    async def get_next_run_all(cls) -> "List[Compile]":
        """ Get the next compile in the queue for each environment
        """
        results = await cls.select_query(
            f"SELECT DISTINCT ON (environment) * FROM {cls.table_name()} WHERE completed IS NULL ORDER BY environment, "
            f"requested ASC",
            [],
        )
        return results

    @classmethod
    async def get_unhandled_compiles(cls) -> "List[Compile]":
        """ Get all compiles that have completed but for which listeners have not been notified yet.
        """
        results = await cls.select_query(
            f"SELECT * FROM {cls.table_name()} WHERE NOT handled and completed IS NOT NULL ORDER BY requested ASC", []
        )
        return results

    @classmethod
    async def get_next_compiles_for_environment(cls, environment_id: uuid.UUID) -> "List[Compile]":
        """ Get the queue of compiles that are scheduled in FIFO order.
        """
        results = await cls.select_query(
            f"SELECT * FROM {cls.table_name()} WHERE environment=$1 AND NOT handled and completed IS NULL "
            "ORDER BY requested ASC",
            [cls._get_value(environment_id)],
        )
        return results

    @classmethod
    async def get_next_compiles_count(cls) -> int:
        """ Get the number of compiles in the queue for ALL environments
        """
        result = await cls._fetchval(f"SELECT count(*) FROM {cls.table_name()} WHERE NOT handled and completed IS NOT NULL")
        return result

    @classmethod
    async def get_by_remote_id(cls, environment_id: uuid.UUID, remote_id: uuid.UUID) -> "List[Compile]":
        results = await cls.select_query(
            f"SELECT * FROM {cls.table_name()} WHERE environment=$1 AND remote_id=$2",
            [cls._get_value(environment_id), cls._get_value(remote_id)],
        )
        return results

    @classmethod
    async def delete_older_than(
        cls, oldest_retained_date: datetime.datetime, connection: Optional[asyncpg.Connection] = None
    ) -> None:
        query = "DELETE FROM " + cls.table_name() + " WHERE completed <= $1::timestamp"
        await cls._execute_query(query, oldest_retained_date, connection=connection)

    def to_dto(self) -> m.CompileRun:
        return m.CompileRun(
            id=self.id,
            remote_id=self.remote_id,
            environment=self.environment,
            requested=self.requested,
            started=self.started,
            do_export=self.do_export,
            force_update=self.force_update,
            metadata=self.metadata,
            environment_variables=self.environment_variables,
        )


class LogLine(DataDocument):
    @property
    def msg(self):
        return self._data["msg"]

    @property
    def args(self):
        return self._data["args"]

    def get_log_level_as_int(self):
        return self._data["level"].value

    def write_to_logger(self, logger):
        logger.log(self.get_log_level_as_int(), self.msg, *self.args)

    @classmethod
    def log(cls, level, msg, timestamp=None, **kwargs):
        if timestamp is None:
            timestamp = datetime.datetime.now()

        log_line = msg % kwargs
        return cls(level=const.LogLevel(level), msg=log_line, args=[], kwargs=kwargs, timestamp=timestamp)


class ResourceAction(BaseDocument):
    """
        Log related to actions performed on a specific resource version by Inmanta.
        Any transactions that update ResourceAction should adhere to the locking order described in
        :py:class:`inmanta.data.ConfigurationModel

        :param environment: The environment this action belongs to.
        :param version: The version of the configuration model this action belongs to.
        :param resource_version_ids: The resource version ids of the resources this action relates to.
        :param action_id: This id distinguishes the actions from each other. Action ids have to be unique per environment.
        :param action: The action performed on the resource
        :param started: When did the action start
        :param finished: When did the action finish
        :param messages: The log messages associated with this action
        :param status: The status of the resource when this action was finished
        :param changes: A dict with key the resource id and value a dict of fields -> value. Value is a dict that can
                       contain old and current keys and the associated values. An empty dict indicates that the field
                       was changed but not data was provided by the agent.
        :param change: The change result of an action
    """

    environment: uuid.UUID = Field(field_type=uuid.UUID, required=True)
    version: int = Field(field_type=int, required=True)
    resource_version_ids: List[m.ResourceVersionIdStr] = Field(field_type=list, required=True)

    action_id: uuid.UUID = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)
    action: const.ResourceAction = Field(field_type=const.ResourceAction, required=True)

    started: datetime.datetime = Field(field_type=datetime.datetime, required=True)
    finished: datetime.datetime = Field(field_type=datetime.datetime)

    messages = Field(field_type=list)
    status = Field(field_type=const.ResourceState)
    changes = Field(field_type=dict)
    change = Field(field_type=const.Change)
    send_event = Field(field_type=bool)

    def __init__(self, from_postgres=False, **kwargs):
        super().__init__(from_postgres, **kwargs)
        self._updates = {}

    @classmethod
    async def get_by_id(cls, doc_id: uuid.UUID):
        return await cls.get_one(action_id=doc_id)

    @classmethod
    def _create_dict_wrapper(cls, from_postgres, kwargs):
        result = cls._create_dict(from_postgres, kwargs)
        new_messages = []
        if from_postgres and result.get("messages"):
            for message in result["messages"]:
                message = json.loads(message)
                if "timestamp" in message:
                    message["timestamp"] = datetime.datetime.strptime(message["timestamp"], "%Y-%m-%dT%H:%M:%S.%f")
                new_messages.append(message)
            result["messages"] = new_messages
        if "changes" in result and result["changes"] == {}:
            result["changes"] = None
        return result

    @classmethod
    async def get_log(
        cls, environment: uuid.UUID, resource_version_id: m.ResourceVersionIdStr, action: Optional[str] = None, limit: int = 0
    ) -> List["ResourceAction"]:
        # The @> operator is required to use the GIN index on the resource_version_ids column
        query = f"""SELECT *
                    FROM {cls.table_name()}
                    WHERE environment=$1 AND resource_version_ids::varchar[] @> ARRAY[$2]::varchar[]
                 """
        values = [cls._get_value(environment), cls._get_value(resource_version_id)]
        if action is not None:
            query += " AND action=$3"
            values.append(cls._get_value(action))
        query += " ORDER BY started DESC"
        if limit is not None and limit > 0:
            query += " LIMIT $%d" % (len(values) + 1)
            values.append(cls._get_value(limit))
        async with cls._connection_pool.acquire() as con:
            async with con.transaction():
                return [cls(**dict(record), from_postgres=True) async for record in con.cursor(query, *values)]

    @classmethod
    async def get(cls, action_id, connection: Optional[asyncpg.connection.Connection] = None):
        return await cls.get_one(action_id=action_id, connection=connection)

    def set_field(self, name, value):
        self._updates[name] = value

    def add_logs(self, messages):
        if not messages:
            return
        if "messages" not in self._updates:
            self._updates["messages"] = []
        self._updates["messages"] += messages

    def add_changes(self, changes):
        for resource, values in changes.items():
            for field, change in values.items():
                if "changes" not in self._updates:
                    self._updates["changes"] = {}
                if resource not in self._updates["changes"]:
                    self._updates["changes"][resource] = {}
                self._updates["changes"][resource][field] = change

    async def save(self, connection: Optional[asyncpg.connection.Connection] = None):
        """
            Save the changes
        """
        if len(self._updates) == 0:
            return
        await self.update_fields(connection=connection, **self._updates)
        self._updates = {}

    @classmethod
    async def purge_logs(cls):
        environments = await Environment.get_list()
        for env in environments:
            time_to_retain_logs = await env.get(RESOURCE_ACTION_LOGS_RETENTION)
            keep_logs_until = datetime.datetime.now() - datetime.timedelta(days=time_to_retain_logs)
            query = "DELETE FROM " + cls.table_name() + " WHERE started < $1"
            value = cls._get_value(keep_logs_until)
            await cls._execute_query(query, value)


class Resource(BaseDocument):
    """
        A specific version of a resource. This entity contains the desired state of a resource.
        Any transactions that update Resource should adhere to the locking order described in
        :py:class:`inmanta.data.ConfigurationModel`.

        :param environment: The environment this resource version is defined in
        :param rid: The id of the resource and its version
        :param resource: The resource for which this defines the state
        :param model: The configuration model (versioned) this resource state is associated with
        :param attributes: The state of this version of the resource
        :param attribute_hash: hash of the attributes, excluding requires, provides and version,
                               used to determine if a resource describes the same state across versions
    """

    environment: uuid.UUID = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)
    model: int = Field(field_type=int, required=True)

    # ID related
    resource_id: m.ResourceVersionIdStr = Field(field_type=str, required=True)
    resource_type: m.ResourceType = Field(field_type=str, required=True)
    resource_version_id: m.ResourceVersionIdStr = Field(field_type=str, required=True, part_of_primary_key=True)

    agent: str = Field(field_type=str, required=True)

    # Field based on content from the resource actions
    last_deploy: datetime.datetime = Field(field_type=datetime.datetime)

    # State related
    attributes: Dict[str, Any] = Field(field_type=dict)
    attribute_hash: str = Field(field_type=str)
    status: const.ResourceState = Field(field_type=const.ResourceState, default=const.ResourceState.available)

    # internal field to handle cross agent dependencies
    # if this resource is updated, it must notify all RV's in this list
    # the list contains full rv id's
    provides: List[m.ResourceVersionIdStr] = Field(field_type=list, default=[])  # List of resource versions

    def make_hash(self):
        character = "|".join(
            sorted([str(k) + "||" + str(v) for k, v in self.attributes.items() if k not in ["requires", "provides", "version"]])
        )
        m = hashlib.md5()
        m.update(self.resource_id.encode())
        m.update(character.encode())
        self.attribute_hash = m.hexdigest()

    @classmethod
    async def get_resources_for_attribute_hash(cls, environment, hashes):
        """
            Get all resources listed in resource_version_ids
        """
        hashes_as_str = "(" + ",".join(["$" + str(i) for i in range(2, len(hashes) + 2)]) + ")"
        query = "SELECT * FROM " + cls.table_name() + " WHERE environment=$1 AND attribute_hash IN " + hashes_as_str
        values = [cls._get_value(environment)] + [cls._get_value(h) for h in hashes]
        result = await cls._fetch_query(query, *values)
        resources = []
        for res in result:
            resources.append(cls(from_postgres=True, **res))
        return resources

    @classmethod
    async def get_resources(
        cls,
        environment: uuid.UUID,
        resource_version_ids: List[m.ResourceVersionIdStr],
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> List["Resource"]:
        """
            Get all resources listed in resource_version_ids
        """
        if not resource_version_ids:
            return []
        resource_version_ids_statement = ", ".join(["$" + str(i) for i in range(2, len(resource_version_ids) + 2)])
        (filter_statement, values) = cls._get_composed_filter(environment=environment)
        values = values + cls._get_value(resource_version_ids)
        query = (
            "SELECT * FROM "
            + cls.table_name()
            + " WHERE "
            + filter_statement
            + " AND resource_version_id IN ("
            + resource_version_ids_statement
            + ")"
        )
        resources = await cls.select_query(query, values, connection=connection)
        return resources

    @classmethod
    async def get_undeployable(cls, environment, version):
        """
            Returns a list of resources with an undeployable state
        """
        (filter_statement, values) = cls._get_composed_filter(environment=environment, model=version)
        undeployable_states = ", ".join(["$" + str(i + 3) for i in range(len(const.UNDEPLOYABLE_STATES))])
        values = values + [cls._get_value(s) for s in const.UNDEPLOYABLE_STATES]
        query = (
            "SELECT * FROM " + cls.table_name() + " WHERE " + filter_statement + " AND status IN (" + undeployable_states + ")"
        )
        resources = await cls.select_query(query, values)
        return resources

    @classmethod
    async def get_resources_in_latest_version(
        cls,
        environment: uuid.UUID,
        resource_type: Optional[m.ResourceType] = None,
        attributes: Dict[PrimitiveTypes, PrimitiveTypes] = {},
    ) -> List["Resource"]:
        """
        Returns the resources in the latest version of the configuration model of the given environment, that satisfy the
        given constraints.

        :param environment: The resources should belong to this environment.
        :param resource_type: The environment should have this resource_type.
        :param attributes: The resource should contain these key-value pairs in its attributes list.
        """
        values = [cls._get_value(environment)]
        query = f"""
            SELECT *
            FROM {Resource.table_name()} AS r1
            WHERE r1.environment=$1 AND r1.model=(SELECT MAX(r2.model)
                                                  FROM {Resource.table_name()} AS r2
                                                  WHERE r2.environment=$1)
        """
        if resource_type:
            query += " AND r1.resource_type=$2"
            values.append(cls._get_value(resource_type))

        result = []
        async with cls._connection_pool.acquire() as con:
            async with con.transaction():
                async for record in con.cursor(query, *values):
                    resource = cls(from_postgres=True, **record)
                    # The constraints on the attributes field are checked in memory.
                    # This prevents injection attacks.
                    if util.is_sub_dict(attributes, resource.attributes):
                        result.append(resource)
        return result

    @classmethod
    async def get_resources_report(cls, environment: uuid.UUID) -> List[JsonType]:
        """
            This method generates a report of all resources in the given environment,
            with their latest version and when they are last deployed.
        """
        query_resource_ids = f"""
                SELECT DISTINCT resource_id
                FROM {Resource.table_name()}
                WHERE environment=$1
        """
        query_latest_version = f"""
                SELECT resource_id, model AS latest_version, agent AS latest_agent
                FROM {Resource.table_name()}
                WHERE environment=$1 AND
                      resource_id=r1.resource_id
                ORDER BY model DESC
                LIMIT 1
        """
        query_latest_deployed_version = f"""
                SELECT resource_id, model AS deployed_version, last_deploy AS last_deploy
                FROM {Resource.table_name()}
                WHERE environment=$1 AND
                      resource_id=r1.resource_id AND
                      status != $2
                ORDER BY model DESC
                LIMIT 1
        """
        query = f"""
                SELECT r1.resource_id, r2.latest_version, r2.latest_agent, r3.deployed_version, r3.last_deploy
                FROM ({query_resource_ids}) AS r1 INNER JOIN LATERAL ({query_latest_version}) AS r2
                      ON (r1.resource_id = r2.resource_id)
                      LEFT OUTER JOIN LATERAL ({query_latest_deployed_version}) AS r3
                      ON (r1.resource_id = r3.resource_id)
        """
        values = [cls._get_value(environment), cls._get_value(const.ResourceState.available)]
        result = []
        async with cls._connection_pool.acquire() as con:
            async with con.transaction():
                async for record in con.cursor(query, *values):
                    resource_id = record["resource_id"]
                    parsed_id = Id.parse_id(resource_id)
                    result.append(
                        {
                            "resource_id": resource_id,
                            "resource_type": parsed_id.entity_type,
                            "agent": record["latest_agent"],
                            "latest_version": record["latest_version"],
                            "deployed_version": record["deployed_version"] if "deployed_version" in record else None,
                            "last_deploy": record["last_deploy"] if "last_deploy" in record else None,
                        }
                    )
        return result

    @classmethod
    async def get_resources_for_version(
        cls, environment: uuid.UUID, version: int, agent: str = None, no_obj: bool = False
    ) -> List["Resource"]:
        if agent:
            (filter_statement, values) = cls._get_composed_filter(environment=environment, model=version, agent=agent)
        else:
            (filter_statement, values) = cls._get_composed_filter(environment=environment, model=version)

        query = f"SELECT * FROM {Resource.table_name()} WHERE {filter_statement}"
        resources = []
        async with cls._connection_pool.acquire() as con:
            async with con.transaction():
                async for record in con.cursor(query, *values):
                    if no_obj:
                        record = dict(record)
                        record["attributes"] = json.loads(record["attributes"])
                        record["id"] = record["resource_version_id"]
                        parsed_id = Id.parse_id(record["resource_version_id"])
                        record["resource_type"] = parsed_id.entity_type
                        resources.append(record)
                    else:
                        resources.append(cls(from_postgres=True, **record))
        return resources

    @classmethod
    async def get_resources_for_version_raw(cls, environment, version, projection):
        if not projection:
            projection = "*"
        else:
            projection = ",".join(projection)
        (filter_statement, values) = cls._get_composed_filter(environment=environment, model=version)
        query = "SELECT " + projection + " FROM " + cls.table_name() + " WHERE " + filter_statement
        resource_records = await cls._fetch_query(query, *values)
        resources = [dict(record) for record in resource_records]
        for res in resources:
            if "attributes" in res:
                res["attributes"] = json.loads(res["attributes"])
        return resources

    @classmethod
    async def get_latest_version(cls, environment, resource_id):
        resources = await cls.get_list(
            order_by_column="model", order="DESC", limit=1, environment=environment, resource_id=resource_id
        )
        if len(resources) > 0:
            return resources[0]

    @classmethod
    async def get(
        cls,
        environment: uuid.UUID,
        resource_version_id: m.ResourceVersionIdStr,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> Optional["Resource"]:
        """
            Get a resource with the given resource version id
        """
        value = await cls.get_one(environment=environment, resource_version_id=resource_version_id, connection=connection)
        return value

    @classmethod
    def new(cls, environment: uuid.UUID, resource_version_id: m.ResourceVersionIdStr, **kwargs: Any) -> "Resource":
        vid = Id.parse_id(resource_version_id)

        attr = dict(
            environment=environment,
            model=vid.version,
            resource_id=vid.resource_str(),
            resource_type=vid.entity_type,
            resource_version_id=resource_version_id,
            agent=vid.agent_name,
        )

        attr.update(kwargs)

        return cls(**attr)

    @classmethod
    async def get_deleted_resources(cls, environment, current_version, current_resources):
        """
            This method returns all resources that have been deleted from the model and are not yet marked as purged. It returns
            the latest version of the resource from a released model.

            :param environment:
            :param current_version:
            :param current_resources: A set of all resource ids in the current version.
        """
        LOGGER.debug("Starting purge_on_delete queries")

        # get all models that have been released
        query = (
            "SELECT version FROM "
            + ConfigurationModel.table_name()
            + " WHERE environment=$1 AND released=TRUE ORDER BY version DESC LIMIT "
            + str(DBLIMIT)
        )
        versions = set()
        latest_version = None
        async with cls._connection_pool.acquire() as con:
            async with con.transaction():
                async for record in con.cursor(query, cls._get_value(environment)):
                    version = record["version"]
                    versions.add(version)
                    if latest_version is None:
                        latest_version = version

        LOGGER.debug("  All released versions: %s", versions)
        LOGGER.debug("  Latest released version: %s", latest_version)

        # find all resources in previous versions that have "purge_on_delete" set
        (filter_statement, values) = cls._get_composed_filter(environment=environment, model=latest_version)
        query = (
            "SELECT DISTINCT resource_id FROM "
            + cls.table_name()
            + " WHERE "
            + filter_statement
            + " AND attributes @> $"
            + str(len(values) + 1)
        )
        values.append(cls._get_value({"purge_on_delete": True}))
        resources = await cls._fetch_query(query, *values)
        resources = [r["resource_id"] for r in resources]

        LOGGER.debug("  Resource with purge_on_delete true: %s", resources)

        # all resources on current model
        LOGGER.debug("  All resource in current version (%s): %s", current_version, current_resources)

        # determined deleted resources

        deleted = set(resources) - current_resources
        LOGGER.debug("  These resources are no longer present in current model: %s", deleted)

        # filter out resources that should not be purged:
        # 1- resources from versions that have not been deployed
        # 2- resources that are already recorded as purged (purged and deployed)
        should_purge = []
        for deleted_resource in deleted:
            # get the full resource history, and determine the purge status of this resource
            (filter_statement, values) = cls._get_composed_filter(environment=environment, resource_id=deleted_resource)
            query = (
                "SELECT *"
                + " FROM "
                + cls.table_name()
                + " WHERE "
                + filter_statement
                + " AND model < $"
                + str(len(values) + 1)
                + " ORDER BY model DESC"
            )
            values.append(cls._get_value(current_version))

            async with cls._connection_pool.acquire() as con:
                async with con.transaction():
                    async for obj in con.cursor(query, *values):
                        # if a resource is part of a released version and it is deployed (this last condition is actually enough
                        # at the moment), we have found the last status of the resource. If it was not purged in that version,
                        # add it to the should purge list.
                        if obj["model"] in versions and obj["status"] == const.ResourceState.deployed.name:
                            attributes = json.loads(obj["attributes"])
                            if not attributes["purged"]:
                                should_purge.append(cls(from_postgres=True, **obj))
                            break

        return should_purge

    async def insert(self, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        self.make_hash()
        await super(Resource, self).insert(connection=connection)

    @classmethod
    async def insert_many(cls, documents: Iterable["Resource"]) -> None:
        for doc in documents:
            doc.make_hash()
        await super(Resource, cls).insert_many(documents)

    async def update(self, **kwargs: Any) -> None:
        self.make_hash()
        await super(Resource, self).update(**kwargs)

    async def update_fields(self, connection: Optional[asyncpg.connection.Connection] = None, **kwargs: Any) -> None:
        self.make_hash()
        await super(Resource, self).update_fields(connection=connection, **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        self.make_hash()
        dct = super(Resource, self).to_dict()
        dct["id"] = dct["resource_version_id"]
        return dct

    def to_dto(self) -> m.Resource:
        return m.Resource(
            environment=self.environment,
            model=self.model,
            resource_id=self.resource_id,
            resource_type=self.resource_type,
            resource_version_id=self.resource_version_id,
            agent=self.agent,
            last_deploy=self.last_deploy,
            attributes=self.attributes,
            status=self.status,
        )


class ConfigurationModel(BaseDocument):
    """
        A specific version of the configuration model.
        Any transactions that update ResourceAction, Resource, Parameter and/or ConfigurationModel
        should acquire their locks in that order.

        :param version: The version of the configuration model, represented by a unix timestamp.
        :param environment: The environment this configuration model is defined in
        :param date: The date this configuration model was created
        :param released: Is this model released and available for deployment?
        :param deployed: Is this model deployed?
        :param result: The result of the deployment. Success or error.
        :param version_info: Version metadata
        :param total: The total number of resources
    """

    version: int = Field(field_type=int, required=True, part_of_primary_key=True)
    environment: uuid.UUID = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)
    date: datetime.datetime = Field(field_type=datetime.datetime)

    released: bool = Field(field_type=bool, default=False)
    deployed: bool = Field(field_type=bool, default=False)
    result: const.VersionState = Field(field_type=const.VersionState, default=const.VersionState.pending)
    version_info: Dict[str, Any] = Field(field_type=dict)

    total: int = Field(field_type=int, default=0)

    # cached state for release
    undeployable: List[m.ResourceIdStr] = Field(field_type=list, required=False)
    skipped_for_undeployable: List[m.ResourceIdStr] = Field(field_type=list, required=False)

    def __init__(self, **kwargs):
        super(ConfigurationModel, self).__init__(**kwargs)
        self._status = {}
        self._done = 0

    @property
    def done(self) -> int:
        # Keep resources which are deployed in done, even when a repair operation
        # changes its state to deploying again.
        if self.deployed:
            return self.total
        return self._done

    @classmethod
    async def _get_status_field(cls, environment: uuid.UUID, values: str) -> dict:
        """
            This field is required to ensure backward compatibility on the API.
        """
        result = {}
        values = json.loads(values)
        for value_entry in values:
            entry_uuid = str(uuid.uuid5(environment, value_entry["id"]))
            result[entry_uuid] = value_entry
        return result

    @classmethod
    async def get_list(
        cls,
        order_by_column: str = None,
        order: str = "ASC",
        limit: int = None,
        offset: int = None,
        no_obj: bool = False,
        connection: Optional[asyncpg.connection.Connection] = None,
        **query: Any,
    ) -> List["ConfigurationModel"]:
        transient_states = ",".join(["$" + str(i) for i in range(1, len(const.TRANSIENT_STATES) + 1)])
        transient_states_values = [cls._get_value(s) for s in const.TRANSIENT_STATES]
        (filterstr, values) = cls._get_composed_filter(col_name_prefix="c", offset=len(transient_states_values) + 1, **query)
        values = transient_states_values + values
        where_statement = f"WHERE {filterstr} " if filterstr else ""
        order_by_statement = f"ORDER BY {order_by_column} {order} " if order_by_column else ""
        limit_statement = f"LIMIT {limit} " if limit is not None and limit > 0 else ""
        offset_statement = f"OFFSET {offset} " if offset is not None and offset > 0 else ""
        query = f"""SELECT c.*,
                           SUM(CASE WHEN r.status NOT IN({transient_states}) THEN 1 ELSE 0 END) AS done,
                           to_json(array(SELECT jsonb_build_object('status', r2.status, 'id', r2.resource_id)
                                         FROM {Resource.table_name()} AS r2
                                         WHERE c.environment=r2.environment AND c.version=r2.model
                                        )
                           ) AS status
                    FROM {cls.table_name()} AS c LEFT OUTER JOIN {Resource.table_name()} AS r
                    ON c.environment = r.environment AND c.version = r.model
                    {where_statement}
                    GROUP BY c.environment, c.version
                    {order_by_statement}
                    {limit_statement}
                    {offset_statement}"""
        query_result = await cls._fetch_query(query, *values, connection=connection)
        result = []
        for record in query_result:
            record = dict(record)
            if no_obj:
                record["status"] = await cls._get_status_field(record["environment"], record["status"])
                result.append(record)
            else:
                done = record.pop("done")
                status = await cls._get_status_field(record["environment"], record.pop("status"))
                obj = cls(from_postgres=True, **record)
                obj._done = done
                obj._status = status
                result.append(obj)
        return result

    def to_dict(self) -> JsonType:
        dct = BaseDocument.to_dict(self)
        dct["status"] = dict(self._status)
        dct["done"] = self._done
        return dct

    @classmethod
    async def version_exists(cls, environment: uuid.UUID, version: int) -> bool:
        query = f"""SELECT 1
                            FROM {ConfigurationModel.table_name()}
                            WHERE environment=$1 AND version=$2"""
        result = await cls._fetchrow(query, cls._get_value(environment), cls._get_value(version))
        if not result:
            return False
        return True

    @classmethod
    async def get_version(cls, environment: uuid.UUID, version: int) -> "ConfigurationModel":
        """
            Get a specific version
        """
        result = await cls.get_one(environment=environment, version=version)
        return result

    @classmethod
    async def get_latest_version(cls, environment: uuid.UUID) -> "ConfigurationModel":
        """
            Get the latest released (most recent) version for the given environment
        """
        versions = await cls.get_list(order_by_column="version", order="DESC", limit=1, environment=environment, released=True)
        if len(versions) == 0:
            return None

        return versions[0]

    @classmethod
    async def get_version_nr_latest_version(cls, environment: uuid.UUID) -> Optional[int]:
        """
            Get the version number of the latest released version in the given environment.
        """
        query = f"""SELECT version
                    FROM {ConfigurationModel.table_name()}
                    WHERE environment=$1 AND released=true
                    ORDER BY version DESC
                    LIMIT 1
                    """
        result = await cls._fetchrow(query, cls._get_value(environment))
        if not result:
            return None
        return result["version"]

    @classmethod
    async def get_agents(cls, environment: uuid.UUID, version: int) -> List[str]:
        """
            Returns a list of all agents that have resources defined in this configuration model
        """
        (filter_statement, values) = cls._get_composed_filter(environment=environment, model=version)
        query = "SELECT DISTINCT agent FROM " + Resource.table_name() + " WHERE " + filter_statement
        result = []
        async with cls._connection_pool.acquire() as con:
            async with con.transaction():
                async for record in con.cursor(query, *values):
                    result.append(record["agent"])
        return result

    @classmethod
    async def get_versions(cls, environment: uuid.UUID, start: int = 0, limit: int = DBLIMIT) -> List["ConfigurationModel"]:
        """
            Get all versions for an environment ordered descending
        """
        versions = await cls.get_list(
            order_by_column="version", order="DESC", limit=limit, offset=start, environment=environment
        )
        return versions

    async def delete_cascade(self) -> None:
        async with self._connection_pool.acquire() as con:
            async with con.transaction():
                # Delete all code associated with this version
                await Code.delete_all(connection=con, environment=self.environment, version=self.version)

                # Acquire explicit lock to avoid deadlock. See ConfigurationModel docstring
                await self._execute_query(f"LOCK TABLE {ResourceAction.table_name()} IN SHARE MODE", connection=con)
                await Resource.delete_all(connection=con, environment=self.environment, model=self.version)

                # Delete facts when the resources in this version are the only
                await con.execute(
                    f"DELETE FROM {Parameter.table_name()} p WHERE environment=$1 AND NOT EXISTS "
                    f"(SELECT * FROM {Resource.table_name()} r WHERE p.resource_id=r.resource_id)",
                    self.environment,
                )

                # Delete ConfigurationModel and cascade delete on connected tables
                await self.delete(connection=con)

    async def get_undeployable(self) -> List[m.ResourceIdStr]:
        """
            Returns a list of resource ids (NOT resource version ids) of resources with an undeployable state
        """
        return self.undeployable

    async def get_skipped_for_undeployable(self) -> List[m.ResourceIdStr]:
        """
            Returns a list of resource ids (NOT resource version ids)
            of resources which should get a skipped_for_undeployable state
        """
        return self.skipped_for_undeployable

    async def mark_done(self) -> None:
        """ mark this deploy as done """
        subquery = (
            f"(EXISTS("
            + f"SELECT 1 "
            + f"FROM {Resource.table_name()} "
            + f"WHERE environment=$1 AND model=$2 AND status != $3"
            + f"))::boolean"
        )
        query = (
            f"UPDATE {self.table_name()} "
            + f"SET "
            + f"deployed=True, result=(CASE WHEN {subquery} THEN $4::versionstate ELSE $5::versionstate END) "
            f"WHERE environment=$1 AND version=$2 RETURNING result"
        )
        values = [
            self._get_value(self.environment),
            self._get_value(self.version),
            self._get_value(const.ResourceState.deployed),
            self._get_value(const.VersionState.failed),
            self._get_value(const.VersionState.success),
        ]
        result = await self._fetchval(query, *values)
        self.result = const.VersionState[result]
        self.deployed = True

    @classmethod
    async def mark_done_if_done(cls, environment, version, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        async def do_query_exclusive(con: asyncpg.connection.Connection) -> None:
            """
                Performs the query to mark done if done. Acquires a lock that blocks execution until other transactions holding
                this lock have committed. This makes sure that once a transaction performs this query, it needs to commit before
                another transaction is able to perform it. This way no race condition is possible where the deployed state is
                not set: when a transaction A is in this part of its lifecycle, either all other related (possibly conflicting)
                transactions have committed already, or they will only start this part of their lifecycle when A has committed
                itself.
            """
            async with con.transaction():
                # SHARE UPDATE EXCLUSIVE is self-conflicting
                # and does not conflict with the ROW EXCLUSIVE lock acquired by UPDATE
                await cls._execute_query(f"LOCK TABLE {Resource.table_name()} IN SHARE UPDATE EXCLUSIVE MODE", connection=con)
                query = f"""UPDATE {ConfigurationModel.table_name()}
                                SET deployed=True,
                                    result=(CASE WHEN (
                                                 EXISTS(SELECT 1
                                                        FROM {Resource.table_name()}
                                                        WHERE environment=$1 AND model=$2 AND status != $3)
                                                 )::boolean
                                            THEN $4::versionstate
                                            ELSE $5::versionstate END
                                    )
                                WHERE environment=$1 AND version=$2 AND
                                      total=(SELECT COUNT(*)
                                             FROM {Resource.table_name()}
                                             WHERE environment=$1 AND model=$2 AND status = any($6::resourcestate[])
                            )"""
                values = [
                    cls._get_value(environment),
                    cls._get_value(version),
                    cls._get_value(ResourceState.deployed),
                    cls._get_value(const.VersionState.failed),
                    cls._get_value(const.VersionState.success),
                    cls._get_value(DONE_STATES),
                ]
                await cls._execute_query(query, *values, connection=con)

        if connection is None:
            async with cls._connection_pool.acquire() as con:
                await do_query_exclusive(con)
        else:
            await do_query_exclusive(connection)

    @classmethod
    async def get_increment(
        cls, environment: uuid.UUID, version: int
    ) -> Tuple[Set[m.ResourceVersionIdStr], List[m.ResourceVersionIdStr]]:
        """
        Find resources incremented by this version compared to deployment state transitions per resource

        :param negative: find deployable resources not in the increment

        available/skipped/unavailable -> next version
        not present -> increment
        error -> increment
        Deployed and same hash -> not increment
        deployed and different hash -> increment
         """
        projection_a = ["resource_version_id", "resource_id", "status", "attribute_hash", "attributes"]
        projection = ["resource_version_id", "resource_id", "status", "attribute_hash"]

        # get resources for agent
        resources = await Resource.get_resources_for_version_raw(environment, version, projection_a)

        # to increment
        increment = []
        not_incrememt = []
        # todo in this verions
        work = [r for r in resources if r["status"] not in UNDEPLOYABLE_NAMES]

        # get versions
        query = f"SELECT version FROM {cls.table_name()} WHERE environment=$1 AND released=true ORDER BY version DESC"
        values = [cls._get_value(environment)]
        version_records = await cls._fetch_query(query, *values)

        versions = [record["version"] for record in version_records]

        for version in versions:
            # todo in next verion
            next = []

            vresources = await Resource.get_resources_for_version_raw(environment, version, projection)
            id_to_resource = {r["resource_id"]: r for r in vresources}

            for res in work:
                # not present -> increment
                if res["resource_id"] not in id_to_resource:
                    increment.append(res)
                    continue

                ores = id_to_resource[res["resource_id"]]

                status = ores["status"]
                # available/skipped/unavailable -> next version
                if status in [ResourceState.available.name, ResourceState.skipped.name, ResourceState.unavailable.name]:
                    next.append(res)

                # error/undeployable -> increment
                elif status in [
                    ResourceState.failed.name,
                    ResourceState.cancelled.name,
                    ResourceState.deploying.name,
                    ResourceState.processing_events.name,
                    ResourceState.skipped_for_undefined.name,
                    ResourceState.undefined.name,
                ]:
                    increment.append(res)
                # undefined -> not in increment

                elif status == ResourceState.deployed.name:
                    if res["attribute_hash"] == ores["attribute_hash"]:
                        #  Deployed and same hash -> not increment
                        not_incrememt.append(res)
                    else:
                        # Deployed and different hash -> increment
                        increment.append(res)
                else:
                    LOGGER.warning("Resource in unexpected state: %s, %s", ores["status"], ores["resource_version_id"])
                    increment.append(res)

            work = next
            if not work:
                break
        if work:
            increment.extend(work)

        negative = [res["resource_version_id"] for res in not_incrememt]

        # patch up the graph
        # 1-include stuff for send-events.
        # 2-adapt requires/provides to get closured set

        outset = set((res["resource_version_id"] for res in increment))  # type: Set[str]
        original_provides = defaultdict(lambda: [])  # type: Dict[str,List[str]]
        send_events = []  # type: List[str]

        # build lookup tables
        for res in resources:
            for req in res["attributes"]["requires"]:
                original_provides[req].append(res["resource_version_id"])
            if "send_event" in res["attributes"] and res["attributes"]["send_event"]:
                send_events.append(res["resource_version_id"])

        # recursively include stuff potentially receiving events from nodes in the increment
        work = list(outset)
        done = set()
        while work:
            current = work.pop()
            if current not in send_events:
                # not sending events, so no receivers
                continue

            if current in done:
                continue
            done.add(current)

            provides = original_provides[current]
            work.extend(provides)
            outset.update(provides)

        return set(outset), negative


class Code(BaseDocument):
    """
        A code deployment

        :param environment: The environment this code belongs to
        :param version: The version of configuration model it belongs to
        :param resource: The resource type this code belongs to
        :param sources: The source code of plugins (phasing out)  form:
            {code_hash:(file_name, provider.__module__, source_code, [req])}
        :param requires: Python requires for the source code above
        :param source_refs: file hashes refering to files in the file store
            {code_hash:(file_name, provider.__module__, [req])}
    """

    environment: uuid.UUID = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)
    resource: str = Field(field_type=str, required=True, part_of_primary_key=True)
    version: int = Field(field_type=int, required=True, part_of_primary_key=True)
    source_refs: Dict[str, Tuple[str, str, List[str]]] = Field(field_type=dict)

    @classmethod
    async def get_version(cls, environment: uuid.UUID, version: int, resource: str) -> Optional["Code"]:
        codes = await cls.get_list(environment=environment, version=version, resource=resource)
        if len(codes) == 0:
            return None

        return codes[0]

    @classmethod
    async def get_versions(cls, environment: uuid.UUID, version: int) -> List["Code"]:
        codes = await cls.get_list(environment=environment, version=version)
        return codes


class DryRun(BaseDocument):
    """
        A dryrun of a model version

        :param id: The id of this dryrun
        :param environment: The environment this code belongs to
        :param model: The configuration model
        :param date: The date the run was requested
        :param resource_total: The number of resources that do a dryrun for
        :param resource_todo: The number of resources left to do
        :param resources: Changes for each of the resources in the version
    """

    id: uuid.UUID = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)
    environment: uuid.UUID = Field(field_type=uuid.UUID, required=True)
    model: int = Field(field_type=int, required=True)
    date: datetime.datetime = Field(field_type=datetime.datetime)
    total: int = Field(field_type=int, default=0)
    todo: int = Field(field_type=int, default=0)
    resources: Dict[str, Any] = Field(field_type=dict, default={})

    @classmethod
    async def update_resource(cls, dryrun_id, resource_id, dryrun_data):
        """
            Register a resource update with a specific query that sets the dryrun_data and decrements the todo counter, only
            if the resource has not been saved yet.
        """
        jsonb_key = uuid.uuid5(dryrun_id, resource_id)
        query = (
            "UPDATE "
            + cls.table_name()
            + " SET todo = todo - 1, resources=jsonb_set(resources, $1::text[], $2) "
            + "WHERE id=$3 and NOT resources ? $4"
        )
        values = [
            cls._get_value([jsonb_key]),
            cls._get_value(dryrun_data),
            cls._get_value(dryrun_id),
            cls._get_value(jsonb_key),
        ]
        await cls._execute_query(query, *values)

    @classmethod
    async def create(cls, environment, model, total, todo):
        obj = cls(environment=environment, model=model, date=datetime.datetime.now(), resources={}, total=total, todo=todo)
        await obj.insert()
        return obj

    def to_dict(self):
        dict_result = BaseDocument.to_dict(self)
        resources = {r["id"]: r for r in dict_result["resources"].values()}
        dict_result["resources"] = resources
        return dict_result


_classes = [
    Project,
    Environment,
    UnknownParameter,
    AgentProcess,
    AgentInstance,
    Agent,
    Resource,
    ResourceAction,
    ConfigurationModel,
    Code,
    Parameter,
    DryRun,
    Compile,
    Report,
]


def set_connection_pool(pool: asyncpg.pool.Pool) -> None:
    LOGGER.debug("Connecting data classes")
    for cls in _classes:
        cls.set_connection_pool(pool)


async def disconnect() -> None:
    LOGGER.debug("Disconnecting data classes")
    await asyncio.gather(*[cls.close_connection_pool() for cls in _classes])


PACKAGE_WITH_UPDATE_FILES = inmanta.db.versions

# Name of core schema in the DB schema verions
# prevent import loop
CORE_SCHEMA_NAME = schema.CORE_SCHEMA_NAME


async def connect(
    host: str,
    port: int,
    database: str,
    username: str,
    password: str,
    create_db_schema: bool = True,
    connection_pool_min_size: int = 10,
    connection_pool_max_size: int = 10,
    connection_timeout: float = 60,
) -> asyncpg.pool.Pool:
    pool = await asyncpg.create_pool(
        host=host,
        port=port,
        database=database,
        user=username,
        password=password,
        min_size=connection_pool_min_size,
        max_size=connection_pool_max_size,
        timeout=connection_timeout,
    )
    try:
        set_connection_pool(pool)
        if create_db_schema:
            async with pool.acquire() as con:
                await schema.DBSchema(CORE_SCHEMA_NAME, PACKAGE_WITH_UPDATE_FILES, con).ensure_db_schema()
        return pool
    except Exception as e:
        await pool.close()
        await disconnect()
        raise e
