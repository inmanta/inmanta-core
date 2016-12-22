"""
    Copyright 2016 Inmanta

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

import logging
import uuid

from inmanta.resources import Id
from tornado import gen, ioloop
from motor import motor_tornado
import datetime
import pymongo


LOGGER = logging.getLogger(__name__)

DBLIMIT = 100000

# TODO: Add embedded document key sanitation
# TODO: Add env id validation to protocol
# TODO: add document ser to protocol
# TODO: disconnect
# TODO: do not created indexes with unit tests
# TODO: difference between None and not set
# TODO: add to_json


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
        return self._default_value

    default_value = property(get_default_value)

    def is_unique(self):
        return self._unique

    unique = property(is_unique)


class BaseDocument(object):
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
    @gen.coroutine
    def set_connection(cls, motor):
        cls._coll = motor[cls.collection_name()]
        io = ioloop.IOLoop.current()

        def ready(fut):
            # TODO: add logging
            pass

        # first define all unique indexes
        for name, field in cls._get_all_fields().items():
            if field.unique:
                f = cls._coll.create_index([(name, pymongo.ASCENDING)], unique=True, background=True)
                io.add_future(f, ready)

        if hasattr(cls, "__indexes__"):
            for i in cls.__indexes__:
                keys = i["keys"]
                other = i.copy()
                del other["keys"]
                f = cls._coll.create_index(keys, background=True, **other)
                io.add_future(f, ready)

    def __init__(self, from_mongo=False, **kwargs):
        self.__fields = {}

        if from_mongo:
            if "id" in kwargs:
                raise AttributeError("A mongo document should not contain a field 'id'")

            kwargs["id"] = kwargs["_id"]
            del kwargs["_id"]
        else:
            if "id" in kwargs:
                raise AttributeError("The id attribute is generated per collection by the document class.")

            kwargs["id"] = self.__class__._new_id()

        fields = self.__class__._get_all_fields()
        for name, value in kwargs.items():
            if name not in fields:
                raise AttributeError("%s field is not defined for this document %s" % (name, self.__class__.collection_name()))

            if value is None and fields[name].required:
                raise TypeError("%s field is required" % name)

            if value is not None and not isinstance(value, fields[name].field_type):
                raise TypeError("Field %s should have the correct type (%s instead of %s)" %
                                (name, fields[name].field_type.__name__, type(value).__name__))


            if value is not None:
                setattr(self, name, value)

            elif fields[name].default:
                setattr(self, name, value)

            del fields[name]

        for name in list(fields.keys()):
            if not fields[name].required:
                del fields[name]

        if len(fields) > 0:
            raise AttributeError("%s fields are required." % ", ".join(fields.keys()))

    def _get_field(self, name):
        if hasattr(self.__class__, name):
            field = getattr(self.__class__, name)
            if isinstance(field, Field):
                return field

        return None

    @classmethod
    def _get_all_fields(cls):
        fields = {}
        for attr in dir(cls):
            value = getattr(cls, attr)
            if isinstance(value, Field):
                fields[attr] = value
        return fields

    def __getattribute__(self, name):
        if name.startswith("_"):
            return object.__getattribute__(self, name)

        field = self._get_field(name)
        if field is not None:
            if name in self.__fields:
                return self.__fields[name]
            else:
                return None

        return object.__getattribute__(self, name)

    def __setattr__(self, name, value):
        if name.startswith("_"):
            return object.__setattr__(self, name, value)

        field = self._get_field(name)
        if field is not None:
            # validate
            if value is not None and not isinstance(value, field.field_type):
                raise TypeError("Field %s should be of type %s" % (name, field.field_type))

            self.__fields[name] = value
            return

        raise AttributeError(name)

    def to_dict(self, mongo_pk=False):
        """
            Return a dict representing the document
        """
        result = {}
        for name, typing in self.__class__._get_all_fields().items():
            value = None
            if name in self.__fields:
                value = self.__fields[name]

            if typing.required and value is None:
                raise TypeError("%s should have field '%s'" % (self.__class__.__name__, name))

            if value is not None:
                if not isinstance(value, typing.field_type):
                    raise TypeError("Value of field %s does not have the correct type" % name)

                if mongo_pk and name == "id":
                    result["_id"] = value
                else:
                    result[name] = value

            elif typing.default:
                result[name] = typing.default_value

        return result

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
        yield self._coll.insert(self.to_dict(mongo_pk=True))

    @gen.coroutine
    def update(self, **kwargs):
        """
            Update this document in the database. It will update the fields in this object and send a full update to mongodb.
            Use update_fields to only update specific fields.
        """
        for name, value in kwargs.items():
            setattr(self, name, value)

        yield self._coll.update({"_id": self.id}, self.to_dict(mongo_pk=True))

    @gen.coroutine
    def update_fields(self, **kwargs):
        """
            Update the given fields of this document in the database. It will update the fields in this object and do a specific
            $set in the mongodb on this document.
        """
        for name, value in kwargs.items():
            setattr(self, name, value)

        yield self._coll.update({"_id": self.id}, {"$set": kwargs})

    @classmethod
    @gen.coroutine
    def get_by_id(cls, doc_id: uuid.UUID):
        """
            Get a specific document based on its ID

            :return An instance of this class with its fields filled from the database.
        """
        result = yield cls._coll.find_one({"_id": doc_id})
        if result is not None:
            return cls(from_mongo=True, **result)

    @classmethod
    @gen.coroutine
    def get_list(cls, limit=DBLIMIT, **query):
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
        yield self._coll.remove({"_id": self.id})

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


class Environment(BaseDocument):
    """
        A deployment environment of a project

        :param id A unique, machine generated id
        :param name The name of the deployment environment.
        :param project The project this environment belongs to.
        :param repo_url The repository url that contains the configuration model code for this environment
        :param repo_url The repository branch that contains the configuration model code for this environment
    """
    name = Field(field_type=str, required=True)
    project = Field(field_type=uuid.UUID, required=True)
    repo_url = Field(field_type=str, default="")
    repo_branch = Field(field_type=str, default="")

    __indexes__ = [
        dict(keys=[("name", pymongo.ASCENDING), ("project", pymongo.ASCENDING)], unique=True)
    ]

    @gen.coroutine
    def delete_cascade(self):
        yield Agent.delete_all(environment=self.id)
        yield Compile.delete_all(environment=self.id)
        yield ConfigurationModel.delete_all(environment=self.id)
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


class AgentInstance(BaseDocument):
    """
        A physical server/node in the infrastructure that reports to the management server.

        :param hostname The hostname of the device.
        :param last_seen When did the server receive data from the node for the last time.
    """
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

    def to_dict(self, mongo_pk=False):
        base = BaseDocument.to_dict(self, mongo_pk)

        if not mongo_pk:
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

    @classmethod
    @gen.coroutine
    def by_env(cls, env):
        nodes = yield cls.get_list(environment=env)
        return nodes


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
    # compile = ReferenceField(reference_document_type="inmanta.data.Compile")


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
    reports = Field(field_type=list)  # Report UUID

    @gen.coroutine
    def to_dict(self, mongo_pk=False):
        # TODO: let report refrence to this compile so this can be done in one query
        result = BaseDocument.to_dict(self, mongo_pk)

        reports = []
        for report_id in result["reports"]:
            report = yield Report.get_by_id(report_id)
            reports.append(report.to_dict())

        return reports


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

    def to_dict(self):
        return {"form_id": self.uuid,
                "form_type": self.form_type,
                "fields": self.fields,
                "defaults": self.defaults,
                "options": self.options,
                "field_options": self.field_options,
                }

    @classmethod
    @gen.coroutine
    def get_form(cls, environment, form_type):
        """
            Get a form based on its typed and environment
        """
        forms = yield cls.objects.filter(environment=environment, form_type=form_type).find_all()
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

    @gen.coroutine
    def to_dict(self):
        yield self.load_references()
        return {"record_id": self.uuid,
                "form_id": self.form.uuid,
                "form_type": self.form.form_type,
                "changed": self.changed,
                "fields": self.fields
                }


ACTIONS = ("store", "push", "pull", "deploy", "dryrun", "other")
LOGLEVEL = ("INFO", "ERROR", "WARNING", "DEBUG", "TRACE")


class ResourceAction(BaseDocument):
    # TODO: add environment here!
    """
        Log related to actions performed on a specific resource version by Inmanta.

        :param resource_version The resource on which the actions are performed
        :param action The action performed on the resource
        :param timestamp When did the action occur
        :param message The log message associated with this action
        :param level The "urgency" of this action
        :param data A python dictionary that can be serialized to json with additional data
    """
    resource_version_id = Field(field_type=str, required=True)
    action = Field(field_type=str, required=True)
    timestamp = Field(field_type=datetime.datetime, required=True)
    message = Field(field_type=str)
    level = Field(field_type=str, default="INFO")
    data = Field(field_type=dict)
    status = Field(field_type=str)

    @classmethod
    @gen.coroutine
    def get_log(cls, resource_version_id, action, limit=0):
        if action is not None:
            cursor = yield cls._coll.filter(resource_version_id=resource_version_id,
                                            action=action).sort("timestamp", direction=pymongo.DESCENDING)
        else:
            cursor = yield cls._coll.filter(resource_version_id=resource_version_id,
                                            action=action).sort("timestamp", direction=pymongo.DESCENDING)

        if limit > 0:
            cursor = cursor.limit(limit)

        log = []
        while (yield cursor.fetch_next):
            log.append(from_mongo=True, **cursor.next_object())

        return log


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
    status = Field(field_type=str, default="")
    hold_state = Field(field_type=bool, default=False)

    # internal field to handle cross agent dependencies
    # if this resource is updated, it must notify all RV's in this list
    # the list contains full rv id's
    provides = Field(field_type=list, default=[])  # List of resource versions

    __indexes__ = [
        dict(keys=[("environment", pymongo.ASCENDING), ("model", pymongo.ASCENDING)]),
        dict(keys=[("environment", pymongo.ASCENDING), ("resource_id", pymongo.ASCENDING)]),
        dict(keys=[("environment", pymongo.ASCENDING), ("resource_version_id", pymongo.ASCENDING)], unique=True),
    ]

    @gen.coroutine
    def delete_cascade(self):
        yield ResourceAction.delete_all(resource=self.id)
        yield self.delete()

    @classmethod
    @gen.coroutine
    def get_resources_for_version(cls, environment, version, agent=None):
        if agent is not None:
            resources = yield cls.get_list(environment=environment, model=version, agent=agent)
        else:
            resources = yield cls.get_list(environment=environment, model=version)
        return resources

    @classmethod
    @gen.coroutine
    def get_latest_version(cls, environment, resource_id):
        cursor = cls.find({"environment": environment, "resource_id": resource_id}).sort("model", pymongo.DESCENDING).limit(1)
        resource = yield cursor.to_list(1)

        return cls(from_mongo=True, **resource)

    @classmethod
    @gen.coroutine
    def get(cls, environment, resource_version_id):
        """
            Get a resource with the given resource version id
        """
        value = yield cls._coll.find_one({"environment": environment, "resource_version_id": resource_version_id})
        return cls(from_mongo=True, **value)

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
    def get_deleted_resources(cls, environment, current_version):
        """
            This method returns all resources that have been deleted from the model and are not yet marked as purged. It returns
            the latest version of the resource from a released model.
        """
        # find all resources in previous version that have "purge_on_delete" set
        resources = yield cls._coll.find({"model": {"$lt": current_version}, "environment": environment,
                                          "$or": [{"attributes.purge_on_delete": {"$exists": True}},
                                                  {"attributes.purge_on_delete": True}]},
                                         ["resource_id"]).distinct("resource_id")

        # get all models that have been released
        models = yield ConfigurationModel._coll.find({"environment": environment, "released": True},
                                                     {"version": True, "_id": False}).to_list(DBLIMIT)
        versions = set()
        for model in models:
            versions.add(model["version"])

        # all resources on current model
        current_resources = yield cls._coll.find({"model": current_version, "environment": environment},
                                                 ["resource_id"]).to_list(DBLIMIT)

        # determined deleted resources
        deleted = set(resources) - set([x["resource_id"] for x in current_resources])

        # filter out resources that should not be purged:
        # 1- resources from versions that have not been deployed
        # 2- resources that are already recorded as purged (purged and deployed)
        should_purge = []
        for deleted_resource in deleted:
            # get the full resource history, and determine the purge status of this resource
            cursor = cls._coll.find({"environment": environment, "model": {"$lt": current_version},
                                     "resource_id": deleted_resource}).sort("version", pymongo.DESCENDING)
            while (yield cursor.fetch_next):
                obj = cursor.next_object()

                # check filter cases
                if obj["model"] not in versions:
                    # ignore because not in a deployed version
                    break

                if obj["attributes"]["purged"]:
                    # it has already been deleted
                    break

                should_purge.append(cls(from_mongo=True, **obj))
                break

        return should_purge


class ConfigurationModel(BaseDocument):
    """
        A specific version of the configuration model.

        :param version The version of the configuration model, represented by a unix timestamp.
        :param environment The environment this configuration model is defined in
        :param date The date this configuration model was created
        :param released Is this model released and available for deployment?
        :param deployed Is this model deployed?
        :param result The result of the deployment. Success or error.
    """
    version = Field(field_type=int, required=True)
    environment = Field(field_type=uuid.UUID, required=True)
    date = Field(field_type=datetime.datetime)

    released = Field(field_type=bool, default=False)
    deployed = Field(field_type=bool, default=False)
    result = Field(field_type=str, default="pending")
    status = Field(field_type=dict, default={})
    version_info = Field(field_type=dict)

    total = Field(field_type=int, default=0)

    __indexes__ = [
        dict(keys=[("environment", pymongo.ASCENDING), ("version", pymongo.ASCENDING)], unique=True)
    ]

    @property
    def done(self):
        return len(self.status)

    def to_dict(self, mongo_pk=False):
        dct = BaseDocument.to_dict(self, mongo_pk=mongo_pk)
        if not mongo_pk:
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
        yield cls._coll.update({"environment": environment, "version": version},
                               {"$set": {resource_key: {"status": status, "id": resource_id}}})

    @gen.coroutine
    def delete_cascade(self):
        yield Resource.delete_all(environment=self.environment, model=self.version)
        yield Snapshot.delete_all(environment=self.environment, model=self.version)
        yield UnknownParameter.delete_all(environment=self.environment, model=self.version)
        yield Code.delete_all(environment=self.environment, model=self.version)
        yield DryRun.delete_all(environment=self.environment, model=self.version)
        yield self.delete()


class Code(BaseDocument):
    """
        A code deployment

        :param environment The environment this code belongs to
        :param version The version of configuration model it belongs to
        :param sources The source code of plugins
        :param requires Python requires for the source code above
    """
    environment = Field(field_type=uuid.UUID, required=True)
    resource = Field(field_type=str, required=True)
    version = Field(field_type=int, required=True)
    sources = Field(field_type=dict)

    @classmethod
    @gen.coroutine
    def get_version(cls, environment, version, resource):
        codes = yield cls.get_list(environment=environment, version=version, resource=resource)
        if len(codes) == 0:
            return None

        return codes[0]


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
        dict(keys=[("environment", pymongo.ASCENDING), ("model", pymongo.DESCENDING)], unique=True)
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
        update = {"$inc": {"todo":-1}, "$set": {resource_key: dryrun_data}}

        yield cls._coll.update(query, update)

    @classmethod
    @gen.coroutine
    def create(cls, environment, model, total, todo):
        obj = cls(environment=environment, model=model, date=datetime.datetime.now(), resources={}, total=total, todo=todo)
        obj.insert()
        return obj

    def to_dict(self, mongo_pk=False):
        dict_result = BaseDocument.to_dict(self, mongo_pk=mongo_pk)
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
    resource_id = Field(field_type=str)
    state_id = Field(field_type=str)
    started = Field(field_type=datetime.datetime)
    finished = Field(field_type=datetime.datetime)
    content_hash = Field(field_type=str)
    success = Field(field_type=bool)
    error = Field(field_type=bool)
    msg = Field(field_type=str)
    size = Field(field_type=int)

    @gen.coroutine
    def to_dict(self):
        yield self.load_references()
        return {"snapshot_id": self.snapshot.uuid,
                "state_id": self.state_id,
                "started": self.started,
                "finished": self.finished,
                "content_hash": self.content_hash,
                "success": self.success,
                "error": self.error,
                "msg": self.msg,
                "size": self.size,
                }


class ResourceRestore(BaseDocument):
    """
        A restore of a resource from a snapshot
    """
    environment = Field(field_type=uuid.UUID, required=True)
    restore = Field(field_type=uuid.UUID, required=True)
    state_id = Field(field_type=str)
    resource_id = Field(field_type=str)
    started = Field(field_type=datetime.datetime)
    finished = Field(field_type=datetime.datetime)
    success = Field(field_type=bool)
    error = Field(field_type=bool)
    msg = Field(field_type=str)

    @gen.coroutine
    def to_dict(self):
        yield self.load_references()
        return {"restore_id": self.restore.uuid,
                "state_id": self.state_id,
                "resource_id": self.resource_id,
                "started": self.started,
                "finished": self.finished,
                "success": self.success,
                "error": self.error,
                "msg": self.msg
                }


class SnapshotRestore(BaseDocument):
    """
        Information about a snapshot restore
    """
    environment = Field(field_type=uuid.UUID, required=True)
    snapshot = Field(field_type=uuid.UUID, required=True)
    started = Field(field_type=datetime.datetime)
    finished = Field(field_type=datetime.datetime)
    resources_todo = Field(field_type=int, default=0)

    @gen.coroutine
    def to_dict(self):
        yield self.load_references()
        return {"id": self.uuid,
                "snapshot": self.snapshot.uuid,
                "started": self.started,
                "finished": self.finished,
                "resources_todo": self.resources_todo,
                }

    @gen.coroutine
    def delete_cascade(self):
        restores = yield ResourceRestore.objects.filter(restore=self).find_all()
        for restore in restores:
            yield restore.delete()

        yield self.delete()


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
    started = Field(field_type=datetime.datetime)
    finished = Field(field_type=datetime.datetime)
    total_size = Field(field_type=int, default=0)
    resources_todo = Field(field_type=int, default=0)

    @gen.coroutine
    def to_dict(self):
        yield self.load_references()
        return {"id": self.uuid,
                "model": self.model.version,
                "name": self.name,
                "started": self.started,
                "finished": self.finished,
                "total_size": self.total_size,
                "resources_todo": self.resources_todo,
                }

    @gen.coroutine
    def delete_cascade(self):
        snapshots = yield ResourceSnapshot.objects.filter(snapshot=self).find_all()
        for snap in snapshots:
            yield snap.delete()

        restores = yield SnapshotRestore.objects.filter(snapshot=self).find_all()
        for restore in restores:
            yield restore.delete_cascade()

        yield self.delete()


@gen.coroutine
def use_motor(motor):
    for cls in [Project, Environment, Parameter, UnknownParameter, AgentProcess, AgentInstance, Agent, Report, Compile, Form,
                FormRecord, Resource, ResourceAction, ConfigurationModel, Code, DryRun, ResourceSnapshot,
                ResourceRestore, SnapshotRestore, Snapshot]:
        yield cls.set_connection(motor)

@gen.coroutine
def connect(host, port, database, io_loop):
    client = motor_tornado.MotorClient(host, port, io_loop=io_loop)
    db = client[database]

    yield use_motor(db)
