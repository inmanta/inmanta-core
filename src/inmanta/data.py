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

from configparser import RawConfigParser
import copy
import datetime
import enum
import logging
import uuid

from motor import motor_tornado
import pymongo
from tornado import gen

from inmanta import const
from inmanta.resources import Id


LOGGER = logging.getLogger(__name__)

DBLIMIT = 100000

# TODO: disconnect
# TODO: difference between None and not set


class Field(object):

    def __init__(self, field_type, required=False, unique=False, **kwargs):

        self._field_type = field_type
        self._required = required

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

    def is_required(self):
        return self._required

    required = property(is_required)

    def get_default(self):
        return self._default

    default = property(get_default)

    def get_default_value(self):
        return copy.copy(self._default_value)

    default_value = property(get_default_value)

    def is_unique(self):
        return self._unique

    unique = property(is_unique)


ESCAPE_CHARS = {".": "\uff0E", "\\": "\\\\", "$": "\u0024"}
ESCAPE_CHARS_R = {v: k for k, v in ESCAPE_CHARS.items()}


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

    def to_dict(self):
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

        if len(dct["_fields"]) == 0:
            print(class_name, bases, dict)
        return type.__new__(cls, class_name, bases, dct)


class BaseDocument(object, metaclass=DocumentMeta):
    """
        A base document in the mongodb. Subclasses of this document determine collections names. This type is mainly used to
        bundle query methods and generate validate and query methods for optimized DB access. This is not a full ODM.
    """
    id = Field(field_type=uuid.UUID, required=True)

    _coll = None

    @classmethod
    def collection_name(cls):
        """
            Return the name of the collection
        """
        return cls.__name__

    @classmethod
    def set_connection(cls, motor):
        cls._coll = motor[cls.collection_name()]

    @classmethod
    @gen.coroutine
    def create_indexes(cls):
        # first define all unique indexes
        for name, field in cls._fields.items():
            if field.unique:
                yield cls._coll.create_index([(name, pymongo.ASCENDING)], unique=True)

        if hasattr(cls, "__indexes__"):
            for i in cls.__indexes__:
                keys = i["keys"]
                other = i.copy()
                del other["keys"]
                yield cls._coll.create_index(keys, **other)

    def __init__(self, from_mongo=False, **kwargs):
        self.__fields = self._create_dict(from_mongo, kwargs)

    @classmethod
    def _create_dict(cls, from_mongo, kwargs):
        result = {}
        if from_mongo:
            kwargs = BaseDocument._dict_to_value(kwargs)

            if "id" in kwargs:
                raise AttributeError("A mongo document should not contain a field 'id'")

            kwargs["id"] = kwargs["_id"]
            del kwargs["_id"]
        else:
            if "id" in kwargs:
                raise AttributeError("The id attribute is generated per collection by the document class.")

            kwargs["id"] = cls._new_id()

        fields = cls._fields.copy()
        for name, value in kwargs.items():
            if name not in fields:
                raise AttributeError("%s field is not defined for this document %s" % (name, cls.collection_name()))

            if value is None and fields[name].required:
                raise TypeError("%s field is required" % name)

            if from_mongo and issubclass(fields[name].field_type, enum.Enum):
                value = fields[name].field_type[value]

            if value is not None and not (value.__class__ is fields[name].field_type or
                                          isinstance(value, fields[name].field_type)):
                raise TypeError("Field %s should have the correct type (%s instead of %s)" %
                                (name, fields[name].field_type.__name__, type(value).__name__))

            if value is not None:
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
    def mongo_to_dict(cls, **kwargs):
        """
            Validate and transform a dict straight from mongo to a serialization that can be send over rpc
        """
        return cls._create_dict(True, kwargs)

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
    def _value_to_dict(cls, value):
        if isinstance(value, enum.Enum):
            return value.name

        if isinstance(value, DataDocument):
            return cls._encode_keys(value.to_dict())

        if isinstance(value, list):
            return [cls._value_to_dict(x) for x in value]

        if isinstance(value, dict):
            return cls._encode_keys(value)

        return value

    # TODO: make this a generator
    @classmethod
    def _encode_keys(cls, data):
        new_data = {}
        for key, value in data.items():
            new_key = key
            for p, s in ESCAPE_CHARS.items():
                new_key = new_key.replace(p, s)

            new_data[new_key] = cls._value_to_dict(value)

        return new_data

    # TODO: make this a generator
    @classmethod
    def _decode_keys(cls, data):
        new_data = {}
        for key, value in data.items():
            new_key = key
            for p, s in ESCAPE_CHARS_R.items():
                new_key = new_key.replace(p, s)

            new_data[new_key] = cls._dict_to_value(value)

        return new_data

    @classmethod
    def _dict_to_value(cls, value):
        if isinstance(value, list):
            return [cls._dict_to_value(x) for x in value]

        if isinstance(value, dict):
            return cls._decode_keys(value)

        return value

    def to_mongo(self):
        return self._to_dict(True)

    def _to_dict(self, mongo_pk=False):
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

                if mongo_pk and name == "id":
                    result["_id"] = value
                else:
                    result[name] = self._value_to_dict(value) if mongo_pk else value

            elif typing.default:
                result[name] = self._value_to_dict(typing.default_value) if mongo_pk else value

        return result

    def to_dict(self):
        return self._to_dict()

    @classmethod
    def _new_id(cls):
        """
            Generate a new ID. Override to use something else than uuid4
        """
        return uuid.uuid4()

    @gen.coroutine
    def insert(self):
        """
            Insert a new document based on the instance passed. Validation is done based on the defined fields.
        """

        yield self._coll.insert_one(self.to_mongo())

    @classmethod
    @gen.coroutine
    def insert_many(cls, documents):
        """
            Insert multiple objects at once
        """
        if len(documents) > 0:
            yield cls._coll.insert_many((d.to_mongo() for d in documents))

    @gen.coroutine
    def update(self, **kwargs):
        """
            Update this document in the database. It will update the fields in this object and send a full update to mongodb.
            Use update_fields to only update specific fields.
        """
        for name, value in kwargs.items():
            setattr(self, name, value)

        yield self._coll.replace_one({"_id": self.id}, self.to_mongo())

    @gen.coroutine
    def update_fields(self, **kwargs):
        """
            Update the given fields of this document in the database. It will update the fields in this object and do a specific
            $set in the mongodb on this document.
        """
        items = {}
        for name, value in kwargs.items():
            setattr(self, name, value)
            items[name] = self._value_to_dict(value)

        yield self._coll.update_one({"_id": self.id}, {"$set": items})

    @classmethod
    @gen.coroutine
    def get_by_id(cls, doc_id: uuid.UUID):
        """
            Get a specific document based on its ID

            :return: An instance of this class with its fields filled from the database.
        """
        result = yield cls._coll.find_one({"_id": doc_id})
        if result is not None:
            return cls(from_mongo=True, **result)

    @classmethod
    @gen.coroutine
    def get_list(cls, **query):
        """
            Get a list of documents matching the filter args
        """
        result = []
        cursor = cls._coll.find(query)

        while (yield cursor.fetch_next):
            obj = cls(from_mongo=True, **cursor.next_object())
            result.append(obj)

        return result

    @classmethod
    @gen.coroutine
    def delete_all(cls, **query):
        """
            Delete all documents that match the given query
        """
        result = yield cls._coll.delete_many(query)
        return result.deleted_count

    @gen.coroutine
    def delete(self):
        """
            Delete this document
        """
        yield self._coll.delete_one({"_id": self.id})

    @gen.coroutine
    def delete_cascade(self):
        yield self.delete()

    @classmethod
    @gen.coroutine
    def query(cls, query):
        cursor = cls._coll.find(query)
        objects = []
        while (yield cursor.fetch_next):
            objects.append(cls(from_mongo=True, **cursor.next_object()))

        return objects


class Project(BaseDocument):
    """
        An inmanta configuration project

        :param name The name of the configuration project.
    """
    name = Field(field_type=str, required=True, unique=True)

    @gen.coroutine
    def delete_cascade(self):
        yield Environment.delete_all(project=self.id)
        yield self.delete()


def convert_boolean(value):
    if isinstance(value, bool):
        return value

    if value.lower() not in RawConfigParser.BOOLEAN_STATES:
        raise ValueError('Not a boolean: %s' % value)
    return RawConfigParser.BOOLEAN_STATES[value.lower()]


def convert_int(value):
    if isinstance(value, (int, float)):
        return value

    f_value = float(value)
    i_value = int(value)

    if i_value == f_value:
        return i_value
    return f_value


def convert_agent_map(value):
    if not isinstance(value, dict):
        raise ValueError("Agent map should be a dict")

    for key, v in value.items():
        if not isinstance(key, str):
            raise ValueError("The key of an agent map should be string")

        if not isinstance(v, str):
            raise ValueError("The value of an agent map should be string")

    return value


AUTO_DEPLOY = "auto_deploy"
PUSH_ON_AUTO_DEPLOY = "push_on_auto_deploy"
AUTOSTART_SPLAY = "autostart_splay"
AUTOSTART_ON_START = "autostart_on_start"
AUTOSTART_AGENT_MAP = "autostart_agent_map"
AUTOSTART_AGENT_INTERVAL = "autostart_agent_interval"
AGENT_AUTH = "agent_auth"
SERVER_COMPILE = "server_compile"


class Setting(object):
    """
        A class to define a new environment setting.
    """
    def __init__(self, name, typ, default=None, doc=None, validator=None, recompile=False, update_model=False,
                 agent_restart=False):
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
        """
        self.typ = typ
        self.default = default
        self.doc = doc
        self.validator = validator
        self.recompile = recompile
        self.update = update_model
        self.agent_restart = agent_restart

    def to_dict(self):
        return {"type": self.typ, "default": self.default, "doc": self.doc, "recompile": self.recompile, "update": self.update,
                "agent_restart": self.agent_restart}


class Environment(BaseDocument):
    """
        A deployment environment of a project

        :param id A unique, machine generated id
        :param name The name of the deployment environment.
        :param project The project this environment belongs to.
        :param repo_url The repository url that contains the configuration model code for this environment
        :param repo_url The repository branch that contains the configuration model code for this environment
        :param settings Key/value settings for this environment
    """
    name = Field(field_type=str, required=True)
    project = Field(field_type=uuid.UUID, required=True)
    repo_url = Field(field_type=str, default="")
    repo_branch = Field(field_type=str, default="")
    settings = Field(field_type=dict, default={})

    _settings = {
        AUTO_DEPLOY: Setting(name=AUTO_DEPLOY, typ="bool", default=False,
                             doc="When this boolean is set to true, the orchestrator will automatically release a new version "
                                 "that was compiled by the orchestrator itself.", validator=convert_boolean),
        PUSH_ON_AUTO_DEPLOY: Setting(name=PUSH_ON_AUTO_DEPLOY, typ="bool", default=False,
                                     doc="Push a new version when it has been autodeployed.", validator=convert_boolean),
        AUTOSTART_SPLAY: Setting(name=AUTOSTART_SPLAY, typ="int", default=10,
                                 doc="Splay time for autostarted agents.", validator=convert_int),
        AUTOSTART_ON_START: Setting(name=AUTOSTART_ON_START, default=True, typ="bool", validator=convert_boolean,
                                    doc="Automatically start agents when the server starts instead of only just in time."),
        AUTOSTART_AGENT_MAP: Setting(name=AUTOSTART_AGENT_MAP, default={"internal": "local:"}, typ="dict",
                                     validator=convert_agent_map,
                                     doc="A dict with key the name of agents that should be automatically started. The value "
                                     "is either an empty string or an agent map string.", agent_restart=True),
        AUTOSTART_AGENT_INTERVAL: Setting(name=AUTOSTART_AGENT_INTERVAL, default=600, typ="int",
                                          validator=convert_int,
                                          doc="Agent interval for autostarted agents in seconds", agent_restart=True),
        SERVER_COMPILE: Setting(name=SERVER_COMPILE, default=True, typ="bool",
                                validator=convert_boolean, doc="Allow the server to compile the configuration model."),
    }

    __indexes__ = [
        dict(keys=[("name", pymongo.ASCENDING), ("project", pymongo.ASCENDING)], unique=True)
    ]

    @gen.coroutine
    def get(self, key):
        """
            Get a setting in this environment.

            :param key: The name/key of the setting. It should be defined in _settings otherwise a keyerror will be raised.
        """
        if key not in self._settings:
            raise KeyError()

        if key in self.settings:
            return self.settings[key]

        if self._settings[key].default is None:
            raise KeyError()

        value = self._settings[key].default
        yield self.set(key, value)
        return value

    @gen.coroutine
    def set(self, key, value):
        """
            Set a new setting in this environment.

            :param key: The name/key of the setting. It should be defined in _settings otherwise a keyerror will be raised.
            :param value: The value of the settings. The value should be of type as defined in _settings
        """
        if key not in self._settings:
            raise KeyError()
        if callable(self._settings[key].validator):
            value = self._settings[key].validator(value)
        yield self._coll.update_one({"_id": self.id}, {"$set": {"settings." + key: self._value_to_dict(value)}})
        self.settings[key] = value

    @gen.coroutine
    def unset(self, key):
        """
            Unset a setting in this environment. If a default value is provided, this value will replace the current value.

            :param key: The name/key of the setting. It should be defined in _settings otherwise a keyerror will be raised.
        """
        if key not in self._settings:
            raise KeyError()

        if self._settings[key].default is None:
            yield self._coll.update_one({"_id": self.id}, {"$unset": {"settings." + key: ""}})
            del self.settings[key]
        else:
            yield self.set(key, self._settings[key].default)

    @gen.coroutine
    def delete_cascade(self, only_content=False):
        yield Agent.delete_all(environment=self.id)

        procs = yield AgentProcess.get_list(environment=self.id)
        for proc in procs:
            yield proc.delete_cascade()

        compile_list = yield Compile.get_list(environment=self.id)
        for cl in compile_list:
            yield cl.delete_cascade()

        models = yield ConfigurationModel.get_list(environment=self.id)
        for model in models:
            yield model.delete_cascade()

        yield Parameter.delete_all(environment=self.id)
        yield Form.delete_all(environment=self.id)
        yield FormRecord.delete_all(environment=self.id)

        if not only_content:
            yield self.delete()


SOURCE = ("fact", "plugin", "user", "form", "report")


class Parameter(BaseDocument):
    """
        A parameter that can be used in the configuration model

        :param name The name of the parameter
        :param value The value of the parameter
        :param environment The environment this parameter belongs to
        :param source The source of the parameter
        :param resource_id An optional resource id
        :param updated When was the parameter updated last

        :todo Add history
    """
    name = Field(field_type=str, required=True)
    value = Field(field_type=str, default="", required=True)
    environment = Field(field_type=uuid.UUID, required=True)
    source = Field(field_type=str, required=True)
    resource_id = Field(field_type=str, default="")
    updated = Field(field_type=datetime.datetime)
    metadata = Field(field_type=dict)

    @classmethod
    @gen.coroutine
    def get_updated_before(cls, updated_before):
        cursor = cls._coll.find({"updated": {"$lt": updated_before}})

        params = []
        while (yield cursor.fetch_next):
            params.append(cls(from_mongo=True, **cursor.next_object()))

        return params


class UnknownParameter(BaseDocument):
    """
        A parameter that the compiler indicated that was unknown. This parameter causes the configuration model to be
        incomplete for a specific environment.

        :param name
        :param resource_id
        :param source
        :param environment
        :param version The version id of the configuration model on which this parameter was reported
    """
    name = Field(field_type=str, required=True)
    environment = Field(field_type=uuid.UUID, required=True)
    source = Field(field_type=str, required=True)
    resource_id = Field(field_type=str, default="")
    version = Field(field_type=int, required=True)
    metadata = Field(field_type=dict)
    resolved = Field(field_type=bool, default=False)

    __indexes__ = [
        dict(keys=[("environment", pymongo.ASCENDING), ("version", pymongo.ASCENDING)])
    ]


class AgentProcess(BaseDocument):
    """
        A process in the infrastructure that has (had) a session as an agent.

        :param hostname The hostname of the device.
        :prama environment To what environment is this process bound
        :param last_seen When did the server receive data from the node for the last time.
    """
    hostname = Field(field_type=str, required=True)
    environment = Field(field_type=uuid.UUID, required=True)
    first_seen = Field(field_type=datetime.datetime, default=None)
    last_seen = Field(field_type=datetime.datetime, default=None)
    expired = Field(field_type=datetime.datetime, default=None)
    sid = Field(field_type=uuid.UUID, required=True)

    @classmethod
    @gen.coroutine
    def get_live(cls, environment=None):
        query = {"$or": [{"expired": {"$exists": False}}, {"expired": None}]}
        if environment is not None:
            query["environment"] = environment

        cursor = cls._coll.find(query)
        nodes = yield cursor.to_list(DBLIMIT)
        return [cls(from_mongo=True, **node) for node in nodes]

    @classmethod
    @gen.coroutine
    def get_live_by_env(cls, env):
        result = yield cls.get_live(env)
        return result

    @classmethod
    @gen.coroutine
    def get_by_env(cls, env):
        nodes = yield cls.get_list(environment=env)
        return nodes

    @classmethod
    @gen.coroutine
    def get_by_sid(cls, sid):
        # TODO: unique index?
        cursor = cls._coll.find({"$or": [{"expired": {"$exists": False}}, {"expired": None}], "sid": sid})
        objects = yield cursor.to_list(DBLIMIT)

        if len(objects) == 0:
            return None
        elif len(objects) > 1:
            LOGGER.exception("Multiple objects with the same unique id found!")
            return cls(from_mongo=True, **objects[0])
        else:
            return cls(from_mongo=True, **objects[0])

    @gen.coroutine
    def delete_cascade(self):
        yield AgentInstance.delete_all(process=self.id)
        yield self.delete()


class AgentInstance(BaseDocument):
    """
        A physical server/node in the infrastructure that reports to the management server.

        :param hostname The hostname of the device.
        :param last_seen When did the server receive data from the node for the last time.
    """
    # TODO: add env to speed up cleanup
    process = Field(field_type=uuid.UUID, required=True)
    name = Field(field_type=str, required=True)
    expired = Field(field_type=datetime.datetime)
    tid = Field(field_type=uuid.UUID, required=True)

    @classmethod
    @gen.coroutine
    def active_for(cls, tid, endpoint):
        objects = yield cls.query({"$or": [{"expired": {"$exists": False}}, {"expired": None}], "tid": tid, "name": endpoint})
        return objects

    @classmethod
    @gen.coroutine
    def active(cls):
        objects = yield cls.query({"$or": [{"expired": {"$exists": False}}, {"expired": None}]})
        return objects


class Agent(BaseDocument):
    """
        An inmanta agent

        :param environment The environment this resource is defined in
        :param name The name of this agent
        :param last_failover Moment at which the primary was last changed
        :param paused is this agent paused (if so, skip it)
        :param primary what is the current active instance (if none, state is down)
    """
    environment = Field(field_type=uuid.UUID, required=True)
    name = Field(field_type=str, required=True)
    last_failover = Field(field_type=datetime.datetime)
    paused = Field(field_type=bool, default=False)
    primary = Field(field_type=uuid.UUID)  # AgentInstance

    __indexes__ = [
        dict(keys=[("environment", pymongo.ASCENDING), ("name", pymongo.ASCENDING)], unique=True)
    ]

    def get_status(self):
        if self.paused:
            return "paused"
        if self.primary is not None:
            return "up"
        return "down"

    def to_dict(self):
        base = BaseDocument.to_dict(self)
        if self.last_failover is None:
            base["last_failover"] = ""

        if self.primary is None:
            base["primary"] = ""

        base["state"] = self.get_status()

        return base

    @classmethod
    @gen.coroutine
    def get(cls, env, endpoint):
        obj = yield cls._coll.find_one({"environment": env, "name": endpoint})

        if obj is not None:
            return cls(from_mongo=True, **obj)


class Report(BaseDocument):
    """
        A report of a substep of compilation

        :param started when the substep started
        :param completed when it ended
        :param command the command that was executed
        :param name The name of this step
        :param errstream what was reported on system err
        :param outstream what was reported on system out
    """
    started = Field(field_type=datetime.datetime, required=True)
    completed = Field(field_type=datetime.datetime, required=True)
    command = Field(field_type=str, required=True)
    name = Field(field_type=str, required=True)
    errstream = Field(field_type=str, default="")
    outstream = Field(field_type=str, default="")
    returncode = Field(field_type=int)

    compile = Field(field_type=uuid.UUID)

    __indexes__ = [
        dict(keys=[("compile", pymongo.ASCENDING)])
    ]


class Compile(BaseDocument):
    """
        A run of the compiler

        :param environment The environment this resource is defined in
        :param started Time the compile started
        :param completed Time to compile was completed
        :param reports Per stage reports
    """
    environment = Field(field_type=uuid.UUID, required=True)
    started = Field(field_type=datetime.datetime)
    completed = Field(field_type=datetime.datetime)

    __indexes__ = [
        dict(keys=[("environment", pymongo.ASCENDING), ("started", pymongo.ASCENDING)])
    ]

    @classmethod
    @gen.coroutine
    def get_reports(cls, queryparts, limit, start, end):
        if limit is not None and end is not None:
            cursor = Compile._coll.find(queryparts).sort("started").limit(int(limit))
            models = []
            while (yield cursor.fetch_next):
                models.append(cls(from_mongo=True, **cursor.next_object()))

            models.reverse()
        else:
            cursor = Compile._coll.find(queryparts).sort("started", pymongo.DESCENDING)
            if limit is not None:
                cursor = cursor.limit(int(limit))
            models = []
            while (yield cursor.fetch_next):
                models.append(cls(from_mongo=True, **cursor.next_object()))

        # load the report stages
        result = []
        for model in models:
            dict_model = model.to_dict()
            result.append(dict_model)

        return result

    @classmethod
    @gen.coroutine
    def get_report(cls, compile_id: uuid.UUID) -> "Compile":
        """
            Get the compile and the associated reports from the database
        """
        result = yield cls.get_by_id(compile_id)
        if result is None:
            return None

        dict_model = result.to_dict()
        cursor = Report._coll.find({"compile": result.id})

        dict_model["reports"] = []
        while (yield cursor.fetch_next):
            obj = Report(from_mongo=True, **cursor.next_object())
            dict_model["reports"].append(obj.to_dict())

        return dict_model

    @gen.coroutine
    def delete_cascade(self):
        yield Report.delete_all(compile=self.id)
        yield self.delete()


class Form(BaseDocument):
    """
        A form in the dashboard defined by the configuration model
    """
    environment = Field(field_type=uuid.UUID, required=True)
    form_type = Field(field_type=str, required=True)
    options = Field(field_type=dict)
    fields = Field(field_type=dict)
    defaults = Field(field_type=dict)
    field_options = Field(field_type=dict)

    @classmethod
    @gen.coroutine
    def get_form(cls, environment, form_type):
        """
            Get a form based on its typed and environment
        """
        forms = yield cls.get_list(environment=environment, form_type=form_type)
        if len(forms) == 0:
            return None
        else:
            return forms[0]


class FormRecord(BaseDocument):
    """
        A form record
    """
    form = Field(field_type=uuid.UUID, required=True)
    environment = Field(field_type=uuid.UUID, required=True)
    fields = Field(field_type=dict)
    changed = Field(field_type=datetime.datetime)


class LogLine(DataDocument):
    @property
    def msg(self):
        return self._data["msg"]

    @classmethod
    def log(cls, level, msg, timestamp=None, **kwargs):
        if timestamp is None:
            timestamp = datetime.datetime.now()

        log_line = msg % kwargs
        return cls(level=const.LogLevel(level), msg=log_line, args=[], kwargs=kwargs, timestamp=timestamp)


class ResourceAction(BaseDocument):
    """
        Log related to actions performed on a specific resource version by Inmanta.

        :param resource_version The resource on which the actions are performed
        :param environment The environment this action belongs to.
        :param action_id This is id distinguishes action from each other. Action ids have to be unique per environment.
        :param action The action performed on the resource
        :param started When did the action start
        :param finished When did the action finish
        :param messages The log messages associated with this action
        :param status The status of the resource when this action was finished
        :param changes A dict with key the resource id and value a dict of fields -> value. Value is a dict that can
                       contain old and current keys and the associated values. An empty dict indicates that the field
                       was changed but not data was provided by the agent.
        :param change The change result of an action
    """
    resource_version_ids = Field(field_type=list, required=True)
    environment = Field(field_type=uuid.UUID, required=True)

    action_id = Field(field_type=uuid.UUID, required=True)
    action = Field(field_type=const.ResourceAction, required=True)

    started = Field(field_type=datetime.datetime, required=True)
    finished = Field(field_type=datetime.datetime)

    messages = Field(field_type=list)
    status = Field(field_type=const.ResourceState)
    changes = Field(field_type=dict)
    change = Field(field_type=const.Change)
    send_event = Field(field_type=bool)

    __indexes__ = [
        dict(keys=[("environment", pymongo.ASCENDING), ("action_id", pymongo.ASCENDING)], unique=True),
        dict(keys=[("environment", pymongo.ASCENDING), ("resource_version_ids", pymongo.ASCENDING)]),
    ]

    def __init__(self, from_mongo=False, **kwargs):
        super().__init__(from_mongo, **kwargs)
        self._updates = {}

    @classmethod
    @gen.coroutine
    def get_log(cls, environment, resource_version_id, action=None, limit=0):
        if action is not None:
            cursor = cls._coll.find({"environment": environment, "resource_version_ids": resource_version_id,
                                     "action": action}).sort("started", direction=pymongo.DESCENDING)
        else:
            cursor = cls._coll.find({"environment": environment, "resource_version_ids": resource_version_id
                                     }).sort("started", direction=pymongo.DESCENDING)

        if limit is not None and limit > 0:
            cursor = cursor.limit(limit)

        log = []
        while (yield cursor.fetch_next):
            log.append(cls(from_mongo=True, **cursor.next_object()))

        return log

    @classmethod
    @gen.coroutine
    def get(cls, environment, action_id):
        resources = yield ResourceAction.get_list(environment=environment, action_id=action_id)
        if len(resources) == 0:
            return None
        return resources[0]

    def set_field(self, name, value):
        if "$set" not in self._updates:
            self._updates["$set"] = {}

        self._updates["$set"][name] = self._value_to_dict(value)

    def add_logs(self, messages):
        if "$push" not in self._updates:
            self._updates["$push"] = {}

        self._updates["$push"]["messages"] = {"$each": self._value_to_dict(messages)}

    def add_changes(self, changes):
        if "$set" not in self._updates:
            self._updates["$set"] = {}

        for resource, values in changes.items():
            for field, change in values.items():
                self._updates["$set"]["changes.%s.%s" % (resource, field)] = self._value_to_dict(change)

    @gen.coroutine
    def save(self):
        """
            Save the accumulated changes
        """
        query = {"environment": self.environment, "action_id": self.action_id}
        if len(self._updates) > 0:
            yield ResourceAction._coll.update_one(query, self._updates)
            self._updates = {}


class Resource(BaseDocument):
    """
        A specific version of a resource. This entity contains the desired state of a resource.

        :param environment The environment this resource version is defined in
        :param rid The id of the resource and its version
        :param resource The resource for which this defines the state
        :param model The configuration model (versioned) this resource state is associated with
        :param attributes The state of this version of the resource
    """
    environment = Field(field_type=uuid.UUID, required=True)
    model = Field(field_type=int, required=True)

    # ID related
    resource_id = Field(field_type=str, required=True)
    resource_version_id = Field(field_type=str, required=True)

    resource_type = Field(field_type=str, required=True)
    agent = Field(field_type=str, required=True)
    id_attribute_name = Field(field_type=str, required=True)
    id_attribute_value = Field(field_type=str, required=True)

    # Field based on content from the resource actions
    last_deploy = Field(field_type=datetime.datetime)

    # State related
    attributes = Field(field_type=dict)
    status = Field(field_type=const.ResourceState, default=const.ResourceState.available)

    # internal field to handle cross agent dependencies
    # if this resource is updated, it must notify all RV's in this list
    # the list contains full rv id's
    provides = Field(field_type=list, default=[])  # List of resource versions

    __indexes__ = [
        dict(keys=[("environment", pymongo.ASCENDING), ("model", pymongo.ASCENDING)]),
        dict(keys=[("environment", pymongo.ASCENDING), ("resource_id", pymongo.ASCENDING)]),
        dict(keys=[("environment", pymongo.ASCENDING), ("resource_version_id", pymongo.ASCENDING)], unique=True),
    ]

    @classmethod
    @gen.coroutine
    def get_resources(cls, environment, resource_version_ids):
        """
            Get all resources listed in resource_version_ids
        """
        cursor = cls._coll.find({"environment": environment, "resource_version_id": {"$in": resource_version_ids}})
        resources = []
        while (yield cursor.fetch_next):
            resources.append(cls(from_mongo=True, **cursor.next_object()))

        return resources

    @gen.coroutine
    def delete_cascade(self):
        yield ResourceAction.delete_all(environment=self.environment, resource_version_ids=self.resource_version_id)
        yield self.delete()

    @classmethod
    @gen.coroutine
    def get_undeployable(cls, environment, version):
        """
            Returns a list of resources with an undeployable state
        """
        cursor = cls._coll.find({"environment": environment, "model": version,
                                 "status": {"$in": [x.name for x in const.UNDEPLOYABLE_STATES]}})
        resources = []
        while (yield cursor.fetch_next):
            resources.append(cls(from_mongo=True, **cursor.next_object()))

        return resources

    @classmethod
    @gen.coroutine
    def get_requires(cls, environment, version, resource_version_id):
        """
            Return all resource that have the given resource_verison_id as requires
        """
        cursor = cls._coll.find({"environment": environment, "model": version,
                                 "attributes.requires": resource_version_id})
        resources = []
        while (yield cursor.fetch_next):
            resources.append(cls(from_mongo=True, **cursor.next_object()))

        return resources

    @classmethod
    @gen.coroutine
    def get_resources_report(cls, environment):
        """
            This method generates a report of all resources in the database, with their latest version, if they are deleted
            and when they are last deployed.
                    return {"id": self.resource_id,
                "id_fields": {"type": self.resource_type,
                              "agent": self.agent,
                              "attribute": self.attribute_name,
                              "value": self.attribute_value,
                              },
                "latest_version": self.version_latest,
                "deployed_version": self.version_deployed,
                "last_deploy": self.last_deploy,
                "holds_state": self.holds_state,
                }
        """
        resources = yield cls._coll.find({"environment": environment}, ["resource_id"]).distinct("resource_id")
        result = []
        for res in resources:
            latest = (yield cls._coll.find({"environment": environment,
                                            "resource_id": res}).sort("version", pymongo.DESCENDING).limit(1).to_list(1))[0]
            if latest["status"] != const.ResourceState.available.name:
                cursor = cls._coll.find({"environment": environment, "resource_id": res,
                                         "status": {"$ne": const.ResourceState.available.name}})
                deployed = (yield cursor.sort("version", pymongo.DESCENDING).limit(1).to_list(1))[0]

            else:
                deployed = latest

            result.append({"resource_id": res,
                           "resource_type": latest["resource_type"],
                           "agent": latest["agent"],
                           "id_attribute_name": latest["id_attribute_name"],
                           "id_attribute_value": latest["id_attribute_value"],
                           "latest_version": latest["model"],
                           "deployed_version": deployed["model"] if "last_deploy" in deployed else None,
                           "last_deploy": deployed["last_deploy"] if "last_deploy" in deployed else None})

        return result

    @classmethod
    @gen.coroutine
    def get_resources_for_version(cls, environment, version, agent=None, include_attributes=True, no_obj=False):
        projection = None
        if not include_attributes:
            projection = {"attributes": False}

        if agent is not None:
            cursor = cls._coll.find({"environment": environment, "model": version, "agent": agent}, projection)
        else:
            cursor = cls._coll.find({"environment": environment, "model": version}, projection)

        resources = []
        while (yield cursor.fetch_next):
            if no_obj:
                resources.append(cls.mongo_to_dict(**cursor.next_object()))
            else:
                resources.append(cls(from_mongo=True, **cursor.next_object()))

        return resources

    @classmethod
    @gen.coroutine
    def get_latest_version(cls, environment, resource_id):
        cursor = cls._coll.find({"environment": environment,
                                 "resource_id": resource_id}).sort("model", pymongo.DESCENDING).limit(1)
        resource = yield cursor.to_list(1)

        if resource is not None and len(resource) > 0:
            return cls(from_mongo=True, **resource[0])

    @classmethod
    @gen.coroutine
    def get(cls, environment, resource_version_id):
        """
            Get a resource with the given resource version id
        """
        value = yield cls._coll.find_one({"environment": environment, "resource_version_id": resource_version_id})
        if value is not None:
            return cls(from_mongo=True, **value)

    @classmethod
    @gen.coroutine
    def get_with_state(cls, environment, version):
        """
            Get all resources from the given version that have "state_id" defined
        """
        cursor = cls._coll.find({"environment": environment, "model": version, "attributes.state_id": {"$exists": True}})

        resources = []
        while (yield cursor.fetch_next):
            resources.append(cls(from_mongo=True, **cursor.next_object()))

        return resources

    @classmethod
    def new(cls, environment, resource_version_id, **kwargs):
        vid = Id.parse_id(resource_version_id)

        attr = dict(environment=environment, model=vid.version, resource_id=vid.resource_str(),
                    resource_version_id=resource_version_id, resource_type=vid.entity_type, agent=vid.agent_name,
                    id_attribute_name=vid.attribute, id_attribute_value=vid.attribute_value)
        attr.update(kwargs)

        return cls(**attr)

    @classmethod
    @gen.coroutine
    def get_deleted_resources(cls, environment, current_version, current_resources):
        """
            This method returns all resources that have been deleted from the model and are not yet marked as purged. It returns
            the latest version of the resource from a released model.

            :param environment:
            :param current_version:
            :param current_resources: A set of all resource ids in the current version.
        """
        LOGGER.debug("Starting purge_on_delete queries")

        # get all models that have been released
        models = yield ConfigurationModel._coll.find({"environment": environment, "released": True},
                                                     {"version": True, "_id": False}
                                                     ).sort("version", pymongo.DESCENDING).to_list(DBLIMIT)
        versions = set()
        latest_version = None
        for model in models:
            versions.add(model["version"])
            if latest_version is None:
                latest_version = model["version"]

        LOGGER.debug("  All released versions: %s", versions)
        LOGGER.debug("  Latest released version: %s", latest_version)

        # find all resources in previous versions that have "purge_on_delete" set
        resources = yield cls._coll.find({"model": latest_version, "environment": environment,
                                          "$and": [{"attributes.purge_on_delete": {"$exists": True}},
                                                   {"attributes.purge_on_delete": True}]},
                                         ["resource_id"]).distinct("resource_id")
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
            cursor = cls._coll.find({"environment": environment, "model": {"$lt": current_version},
                                     "resource_id": deleted_resource}).sort("model", pymongo.DESCENDING)

            while (yield cursor.fetch_next):
                obj = cursor.next_object()

                # if a resource is part of a released version and it is deployed (this last condition is actually enough
                # at the moment), we have found the last status of the resource. If it was not purged in that version,
                # add it to the should purge list.
                if obj["model"] in versions and obj["status"] == const.ResourceState.deployed.name:
                    if not obj["attributes"]["purged"]:
                        should_purge.append(cls(from_mongo=True, **obj))
                    break

        return should_purge

    @classmethod
    def mongo_to_dict(cls, **kwargs):
        dct = super(Resource, cls).mongo_to_dict(**kwargs)
        dct["id"] = dct["resource_version_id"]
        return dct

    def to_dict(self):
        dct = BaseDocument.to_dict(self)
        dct["id"] = dct["resource_version_id"]
        return dct


class ConfigurationModel(BaseDocument):
    """
        A specific version of the configuration model.

        :param version: The version of the configuration model, represented by a unix timestamp.
        :param environment: The environment this configuration model is defined in
        :param date: The date this configuration model was created
        :param released: Is this model released and available for deployment?
        :param deployed: Is this model deployed?
        :param result: The result of the deployment. Success or error.
        :param status: The deployment status of all included resources
        :param version_info: Version metadata
        :param total: The total number of resources
    """
    version = Field(field_type=int, required=True)
    environment = Field(field_type=uuid.UUID, required=True)
    date = Field(field_type=datetime.datetime)

    released = Field(field_type=bool, default=False)
    deployed = Field(field_type=bool, default=False)
    result = Field(field_type=const.VersionState, default=const.VersionState.pending)
    status = Field(field_type=dict, default={})
    version_info = Field(field_type=dict)

    total = Field(field_type=int, default=0)

    __indexes__ = [
        dict(keys=[("environment", pymongo.ASCENDING), ("version", pymongo.ASCENDING)], unique=True)
    ]

    @property
    def done(self):
        return len(self.status)

    @classmethod
    def mongo_to_dict(cls, **kwargs):
        dct = super(DryRun, cls).mongo_to_dict(**kwargs)
        dct["done"] = len(dct["status"])
        return dct

    def to_dict(self):
        dct = BaseDocument.to_dict(self)
        dct["done"] = self.done
        return dct

    @classmethod
    @gen.coroutine
    def get_version(cls, environment, version):
        """
            Get a specific version
        """
        result = yield cls._coll.find_one({"environment": environment, "version": version})
        if result is not None:
            return cls(from_mongo=True, **result)

        return None

    @classmethod
    @gen.coroutine
    def get_latest_version(cls, environment):
        """
            Get the latest released (most recent) version for the given environment
        """
        cursor = cls._coll.find({"environment": environment, "released": True}).sort("version", pymongo.DESCENDING).limit(1)

        versions = yield cursor.to_list(1)

        if len(versions) == 0:
            return None

        return cls(from_mongo=True, **versions[0])

    @classmethod
    @gen.coroutine
    def get_agents(cls, environment, version):
        """
            Returns a list of all agents that have resources defined in this configuration model
        """
        agents = yield Resource._coll.find({"environment": environment, "model": version},
                                           projection={"_id": False, "agent": True}).distinct("agent")

        return agents

    @classmethod
    @gen.coroutine
    def get_versions(cls, environment, start=0, limit=DBLIMIT):
        """
            Get all versions for an environment ordered descending
        """
        cursor = cls._coll.find({"environment": environment}).sort("version", pymongo.DESCENDING).skip(start).limit(limit)

        versions = []
        while (yield cursor.fetch_next):
            versions.append(cls(from_mongo=True, **cursor.next_object()))

        return versions

    @classmethod
    @gen.coroutine
    def set_ready(cls, environment, version, resource_uuid, resource_id, status):
        """
            Mark a resource as deployed in the configuration model status
        """
        entry_uuid = uuid.uuid5(resource_uuid, resource_id)
        resource_key = "status.%s" % entry_uuid
        yield cls._coll.update_one({"environment": environment, "version": version},
                                   {"$set": {resource_key: {"status": cls._value_to_dict(status), "id": resource_id}}})

    @gen.coroutine
    def delete_cascade(self):
        resources = yield Resource.get_list(environment=self.environment, model=self.version)
        for res in resources:
            yield res.delete_cascade()
        snaps = yield Snapshot.get_list(environment=self.environment, model=self.version)
        for snap in snaps:
            yield snap.delete_cascade()
        yield UnknownParameter.delete_all(environment=self.environment, model=self.version)
        yield Code.delete_all(environment=self.environment, model=self.version)
        yield DryRun.delete_all(environment=self.environment, model=self.version)
        yield self.delete()


class Code(BaseDocument):
    """
        A code deployment

        :param environment The environment this code belongs to
        :param version The version of configuration model it belongs to
        :param sources The source code of plugins (phasing out)  form:
            {code_hash:(file_name, provider.__module__, source_code, [req])}
        :param requires Python requires for the source code above
        :param source_refs file hashes refering to files in the file store
            {code_hash:(file_name, provider.__module__, [req])}
    """
    environment = Field(field_type=uuid.UUID, required=True)
    resource = Field(field_type=str, required=True)
    version = Field(field_type=int, required=True)
    sources = Field(field_type=dict)
    source_refs = Field(field_type=dict)

    __indexes__ = [
        dict(keys=[("environment", pymongo.ASCENDING), ("version", pymongo.ASCENDING), ("resource", pymongo.ASCENDING)])
    ]

    @classmethod
    @gen.coroutine
    def get_version(cls, environment, version, resource):
        codes = yield cls.get_list(environment=environment, version=version, resource=resource)
        if len(codes) == 0:
            return None

        return codes[0]

    @classmethod
    @gen.coroutine
    def get_versions(cls, environment, version):
        codes = yield cls.get_list(environment=environment, version=version)
        return codes


class DryRun(BaseDocument):
    """
        A dryrun of a model version

        :param id The id of this dryrun
        :param environment The environment this code belongs to
        :param model The configuration model
        :param date The date the run was requested
        :param resource_total The number of resources that do a dryrun for
        :param resource_todo The number of resources left to do
        :param resources Changes for each of the resources in the version
    """
    environment = Field(field_type=uuid.UUID, required=True)
    model = Field(field_type=int, required=True)
    date = Field(field_type=datetime.datetime)
    total = Field(field_type=int, default=0)
    todo = Field(field_type=int, default=0)
    resources = Field(field_type=dict, default={})

    __indexes__ = [
        dict(keys=[("environment", pymongo.ASCENDING), ("model", pymongo.DESCENDING)])
    ]

    @classmethod
    @gen.coroutine
    def update_resource(cls, dryrun_id, resource_id, dryrun_data):
        """
            Register a resource update with a specific query that sets the dryrun_data and decrements the todo counter, only
            if the resource has not been saved yet.
        """
        entry_uuid = uuid.uuid5(dryrun_id, resource_id)
        resource_key = "resources.%s" % entry_uuid

        query = {"_id": dryrun_id, resource_key: {"$exists": False}}
        update = {"$inc": {"todo": int(-1)}, "$set": {resource_key: cls._value_to_dict(dryrun_data)}}

        yield cls._coll.update_one(query, update)

    @classmethod
    @gen.coroutine
    def create(cls, environment, model, total, todo):
        obj = cls(environment=environment, model=model, date=datetime.datetime.now(), resources={}, total=total, todo=todo)
        obj.insert()
        return obj

    @classmethod
    def mongo_to_dict(cls, **kwargs):
        dct = super(DryRun, cls).mongo_to_dict(**kwargs)
        resources = {r["id"]: r for r in dct["resources"].values()}
        dct["resources"] = resources
        return dct

    def to_dict(self):
        dict_result = BaseDocument.to_dict(self)
        resources = {r["id"]: r for r in dict_result["resources"].values()}
        dict_result["resources"] = resources
        return dict_result


class ResourceSnapshot(BaseDocument):
    """
        Snapshot of a resource

        :param error Indicates if an error made the snapshot fail
    """
    environment = Field(field_type=uuid.UUID, required=True)
    snapshot = Field(field_type=uuid.UUID, required=True)
    resource_id = Field(field_type=str, required=True)
    state_id = Field(field_type=str, required=True)
    started = Field(field_type=datetime.datetime, default=None)
    finished = Field(field_type=datetime.datetime, default=None)
    content_hash = Field(field_type=str)
    success = Field(field_type=bool)
    error = Field(field_type=bool)
    msg = Field(field_type=str)
    size = Field(field_type=int)


class ResourceRestore(BaseDocument):
    """
        A restore of a resource from a snapshot
    """
    environment = Field(field_type=uuid.UUID, required=True)
    restore = Field(field_type=uuid.UUID, required=True)
    state_id = Field(field_type=str)
    resource_id = Field(field_type=str)
    started = Field(field_type=datetime.datetime, default=None)
    finished = Field(field_type=datetime.datetime, default=None)
    success = Field(field_type=bool)
    error = Field(field_type=bool)
    msg = Field(field_type=str)


class SnapshotRestore(BaseDocument):
    """
        Information about a snapshot restore
    """
    environment = Field(field_type=uuid.UUID, required=True)
    snapshot = Field(field_type=uuid.UUID, required=True)
    started = Field(field_type=datetime.datetime, default=None)
    finished = Field(field_type=datetime.datetime, default=None)
    resources_todo = Field(field_type=int, default=0)

    @gen.coroutine
    def delete_cascade(self):
        yield ResourceRestore.delete_all(restore=self.id)
        yield self.delete()

    @gen.coroutine
    def resource_updated(self):
        yield SnapshotRestore._coll.update_one({"_id": self.id}, {"$inc": {"resources_todo": int(-1)}})
        self.resources_todo -= 1

        now = datetime.datetime.now()
        result = yield SnapshotRestore._coll.update_one({"_id": self.id, "resources_todo": 0}, {"$set": {"finished": now}})
        if result.matched_count == 1 and (result.modified_count == 1 or result.modified_count is None):
            # modified_count is None for mongodb < 2.6
            self.finished = now


class Snapshot(BaseDocument):
    """
        A snapshot of an environment

        :param id The id of the snapshot
        :param environment A reference to the environment
        :param started When was this snapshot started
        :param finished When was this snapshot finished
        :param total_size The total size of this snapshot
    """
    environment = Field(field_type=uuid.UUID, required=True)
    model = Field(field_type=int, required=True)
    name = Field(field_type=str)
    started = Field(field_type=datetime.datetime, default=None)
    finished = Field(field_type=datetime.datetime, default=None)
    total_size = Field(field_type=int, default=0)
    resources_todo = Field(field_type=int, default=0)

    @gen.coroutine
    def delete_cascade(self):
        yield ResourceSnapshot.delete_all(snapshot=self.id)
        restores = yield SnapshotRestore.get_list(snapshot=self.id)
        for restore in restores:
            yield restore.delete_cascade()

        yield self.delete()

    @gen.coroutine
    def resource_updated(self, size):
        yield Snapshot._coll.update_one({"_id": self.id},
                                        {"$inc": {"resources_todo": int(-1), "total_size": size}})
        self.total_size += size
        self.resources_todo -= 1

        now = datetime.datetime.now()
        result = yield Snapshot._coll.update_one({"_id": self.id, "resources_todo": 0}, {"$set": {"finished": now}})
        if result.matched_count == 1 and (result.modified_count == 1 or result.modified_count is None):
            # modified_count is None for mongodb < 2.6
            self.finished = now


_classes = [Project, Environment, Parameter, UnknownParameter, AgentProcess, AgentInstance, Agent, Report, Compile, Form,
            FormRecord, Resource, ResourceAction, ConfigurationModel, Code, DryRun, ResourceSnapshot, ResourceRestore,
            SnapshotRestore, Snapshot]


def use_motor(motor):
    for cls in _classes:
        cls.set_connection(motor)


@gen.coroutine
def create_indexes():
    for cls in _classes:
        yield cls.create_indexes()


def connect(host, port, database, io_loop):
    client = motor_tornado.MotorClient(host, port, io_loop=io_loop)
    db = client[database]

    use_motor(db)
