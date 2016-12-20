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

import json
import logging
import uuid

from motorengine import Document, DESCENDING
from motorengine.fields import (StringField, ReferenceField, DateTimeField, IntField, UUIDField, BooleanField)
from motorengine.fields.json_field import JsonField
from inmanta.resources import Id
from tornado import gen
from motorengine.fields.list_field import ListField
from motorengine.fields.embedded_document_field import EmbeddedDocumentField
from motor import motor_tornado
import datetime


LOGGER = logging.getLogger(__name__)

DBLIMIT = 100000


class Field(object):
    def __init__(self, field_type, required=False, default=None):
        self._field_type = field_type
        self._required = required
        self._default = default

    def get_field_type(self):
        return self._field_type

    field_type = property(get_field_type)

    def get_required(self):
        return self._required

    required = property(get_required)

    def get_default(self):
        return self._default

    default = property(get_default)


class BaseDocument(object):
    """
        A base document in the mongodb. Subclasses of this document determine collections names. This type is mainly used to
        bundle query methods and generate validate and query methods for optimized DB access. This is not a full ODM.
    """
    id = Field(field_type=uuid.UUID, required=True)

    @classmethod
    def collection(cls):
        """
            Return the name of the collection
        """
        return cls.__name__

    @classmethod
    def set_connection(cls, motor):
        cls._coll = motor[cls.collection()]

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
                raise AttributeError("%s field is not defined for this document %s" % (name, self.__class__.collection()))

            if not isinstance(value, fields[name].field_type):
                raise TypeError("Field %s should have the correct type" % name)

            del fields[name]
            setattr(self, name, value)

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
            if not isinstance(value, field.field_type):
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

            if not isinstance(value, typing.field_type):
                raise TypeError("Value of field %s does not have the correct type" % name)

            if mongo_pk and name == "id":
                result["_id"] = value
            else:
                result[name] = value

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

    @classmethod
    @gen.coroutine
    def get_by_id(cls, doc_id):
        """
            Get a specific document based on its ID

            :return An instance of this class with its fields filled from the database.
        """
        result = yield cls._coll.find_one({"_id": doc_id})
        return cls(from_mongo=True, **result)

    @classmethod
    @gen.coroutine
    def get_list(cls, limit=10000, **query):
        """
            Get a cu of documents matching the filter args
        """
        result = []
        cursor = cls._coll.find(query)

        while (yield cursor.fetch_next):
            obj = cls(from_mongo=True, **cursor.next_object())
            result.append(obj)

        return result


class IdDocument(Document):
    """
        A document that has a uuid as id that is required and unique
    """
    uuid = UUIDField(required=True, unique=True)

    @classmethod
    @gen.coroutine
    def get_uuid(cls, uuid):
        objects = yield cls.objects.filter(uuid=uuid).find_all()
        if len(objects) == 0:
            return None
        elif len(objects) > 1:
            raise Exception("Multiple objects with the same unique id found!")
        else:
            return objects[0]


class Project(IdDocument):
    """
        An inmanta configuration project

        :param name The name of the configuration project.
    """
    name = StringField(required=True, unique=True)

    def to_dict(self):
        return {"name": self.name,
                "id": self.uuid
                }

    @gen.coroutine
    def delete_cascade(self):
        envs = yield Environment.objects.filter(project_id=self.uuid).find_all()
        for env in envs:
            yield env.delete_cascade()

        yield self.delete()


class Environment(IdDocument):
    """
        A deployment environment of a project

        :param id A unique, machine generated id
        :param name The name of the deployment environment.
        :param project The project this environment belongs to.
        :param repo_url The repository url that contains the configuration model code for this environment
        :param repo_url The repository branch that contains the configuration model code for this environment
    """
    name = StringField(required=True)
    project_id = UUIDField(required=True)
    repo_url = StringField()
    repo_branch = StringField()

    def to_dict(self):
        return {"id": self.uuid,
                "name": self.name,
                "project": self.project_id,
                "repo_url": self.repo_url,
                "repo_branch": self.repo_branch
                }

    @gen.coroutine
    def delete_cascade(self):
        models = yield ConfigurationModel.objects.filter(environment=self).find_all()
        for model in models:
            yield model.delete_cascade()

        yield self.delete()


SOURCE = ("fact", "plugin", "user", "form", "report")


class Parameter(Document):
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
    name = StringField(required=True)
    value = StringField(default="", required=True)
    environment = ReferenceField(reference_document_type=Environment, required=True, sparse=True)
    source = StringField(required=True)
    resource_id = StringField(default="")
    updated = DateTimeField()
    metadata = JsonField(sparse=True)

    def to_dict(self):
        return {"name": self.name,
                "value": self.value,
                "source": self.source,
                "resource_id": self.resource_id,
                "updated": self.updated,
                "metadata": self.metadata,
                }


class UnknownParameter(Document):
    """
        A parameter that the compiler indicated that was unknown. This parameter causes the configuration model to be
        incomplete for a specific environment.

        :param name
        :param resource_id
        :param source
        :param environment
        :param version The version id of the configuration model on which this parameter was reported
    """
    name = StringField(required=True)
    environment = ReferenceField(reference_document_type=Environment, required=True, sparse=True)
    source = StringField(required=True)
    resource_id = StringField(default="")
    version = IntField(required=True)
    metadata = JsonField(sparse=True)
    resolved = BooleanField(default=False)

    def to_dict(self):
        return {"name": self.name,
                "source": self.source,
                "resource_id": self.resource_id,
                "version": self.version,
                "resolved": self.resolved,
                "metadata": self.metadata,
                }


class AgentProcess(IdDocument):
    """
        A process in the infrastructure that has (had) a session as an agent.

        :param hostname The hostname of the device.
        :prama environment To what environment is this process bound
        :param last_seen When did the server receive data from the node for the last time.
    """
    hostname = StringField(required=True, sparse=True)
    # environment = ReferenceField(reference_document_type=Environment, required=False, sparse=True)
    # for unknown environments
    environment_id = UUIDField(required=True, sparse=True)
    first_seen = DateTimeField(required=True)
    last_seen = DateTimeField()
    expired = DateTimeField()
    sid = UUIDField(required=True, sparse=True)

    @gen.coroutine
    def to_dict(self):
        yield self.load_references()
        out = {"id": self.uuid,
               "hostname": self.hostname,
               "environment": str(self.environment_id),
               "first_seen": self.first_seen.isoformat(),
               "last_seen": self.last_seen.isoformat()}
        if self.expired is not None:
            out["expired"] = self.expired.isoformat()
        else:
            out["expired"] = None

        return out

    @classmethod
    @gen.coroutine
    def get_live(cls):
        nodes = yield cls.objects.filter(expired__is_null=True).find_all()
        return nodes

    @classmethod
    @gen.coroutine
    def get_live_by_env(cls, env):
        nodes = yield cls.objects.filter(expired__is_null=True, environment_id=env.uuid).find_all()
        return nodes

    @classmethod
    @gen.coroutine
    def get(cls):
        nodes = yield cls.objects.find_all()
        return nodes

    @classmethod
    @gen.coroutine
    def get_by_env(cls, env):
        nodes = yield cls.objects.filter(environment_id=env.uuid).find_all()
        return nodes

    @classmethod
    @gen.coroutine
    def get_by_sid(cls, sid):
        objects = yield cls.objects.filter(expired__is_null=True, sid=sid).find_all()
        if len(objects) == 0:
            return None
        elif len(objects) > 1:
            LOGGER.exception("Multiple objects with the same unique id found!")
            return objects[0]
        else:
            return objects[0]


class AgentInstance(IdDocument):
    """
        A physical server/node in the infrastructure that reports to the management server.

        :param hostname The hostname of the device.
        :param last_seen When did the server receive data from the node for the last time.
    """
    process = ReferenceField(reference_document_type=AgentProcess, required=True)
    name = StringField(required=True)
    expired = DateTimeField()
    tid = UUIDField(required=True)

    @gen.coroutine
    def to_dict(self):
        yield self.load_references()
        return {"process": str(self.process.uuid),
                "name": self.name,
                "id": self.uuid}

    @classmethod
    @gen.coroutine
    def activeFor(cls, tid, endpoint):
        objects = yield cls.objects.filter(tid=tid, name=endpoint, expired__is_null=True).find_all()
        return objects

    @classmethod
    @gen.coroutine
    def active(cls):
        objects = yield cls.objects.filter(expired__is_null=True).find_all()
        return objects


class Agent(Document):
    """
        An inmanta agent

        :param environment The environment this resource is defined in
        :param name The name of this agent
        :param last_failover Moment at which the primary was last changed
        :param paused is this agent paused (if so, skip it)
        :param primary what is the current active instance (if none, state is down)
    """
    environment = ReferenceField(reference_document_type=Environment, required=True, sparse=True)
    name = StringField(required=True)
    last_failover = DateTimeField()
    paused = BooleanField(required=True)
    primary = ReferenceField(reference_document_type=AgentInstance)

    def get_status(self):
        if self.paused:
            return "paused"
        if self.primary is not None:
            return "up"
        return "down"

    @gen.coroutine
    def to_dict(self):
        yield self.load_references()
        if self.last_failover is None:
            fo = ""
        else:
            fo = self.last_failover.isoformat()

        if self.primary is None:
            prim = ""
        else:
            prim = str(self.primary.uuid)

        return {"environment": str(self.environment.uuid),
                "name": self.name,
                "last_failover": fo,
                "paused": self.paused,
                "primary": prim,
                "state": self.get_status()
                }

    @classmethod
    @gen.coroutine
    def get(cls, env, endpoint):
        objects = yield cls.objects.filter(environment=env, name=endpoint).find_all()
        if len(objects) == 0:
            return None
        elif len(objects) > 1:
            raise Exception("Multiple objects with the same unique id found!")
        else:
            return objects[0]

    @classmethod
    @gen.coroutine
    def by_env(cls, env):
        nodes = yield cls.objects.filter(environment=env).find_all()
        return nodes


class Report(Document):
    """
        A report of a substep of compilation

        :param started when the substep started
        :param completed when it ended
        :param command the command that was executed
        :param name The name of this step
        :param errstream what was reported on system err
        :param outstream what was reported on system out
    """
    started = DateTimeField(required=True)
    completed = DateTimeField(required=True)
    command = StringField(required=True)
    name = StringField(required=True)
    errstream = StringField(default="")
    outstream = StringField(default="")
    returncode = IntField()
    # compile = ReferenceField(reference_document_type="inmanta.data.Compile")

    def to_dict(self):
        return {"started": self.started.isoformat(),
                "completed": self.completed.isoformat(),
                "command": self.command,
                "name": self.name,
                "errstream": self.errstream,
                "outstream": self.outstream,
                "returncode": self.returncode
                }


class Compile(Document):
    """
        A run of the compiler

        :param environment The environment this resource is defined in
        :param started Time the compile started
        :param completed Time to compile was completed
        :param reports Per stage reports
    """
    environment = ReferenceField(reference_document_type=Environment)
    started = DateTimeField()
    completed = DateTimeField()
    reports = ListField(EmbeddedDocumentField(embedded_document_type=Report))

    @gen.coroutine
    def to_dict(self):
        yield self.load_references()
        return {"environment": str(self.environment.uuid),
                "started": self.started.isoformat(),
                "completed": self.completed.isoformat(),
                "reports": [v.to_dict() for v in self.reports],
                }


class Form(IdDocument):
    """
        A form in the dashboard defined by the configuration model
    """
    environment = ReferenceField(reference_document_type=Environment, required=True, sparse=True)
    form_type = StringField(required=True, sparse=True)
    options = JsonField()
    fields = JsonField()
    defaults = JsonField()
    field_options = JsonField()

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


class FormRecord(IdDocument):
    """
        A form record
    """
    form = ReferenceField(reference_document_type=Form, required=True)
    environment = ReferenceField(reference_document_type=Environment, required=True)
    fields = JsonField()
    changed = DateTimeField()

    @gen.coroutine
    def to_dict(self):
        yield self.load_references()
        return {"record_id": self.uuid,
                "form_id": self.form.uuid,
                "form_type": self.form.form_type,
                "changed": self.changed,
                "fields": self.fields
                }


class Resource(Document):
    """
        A resource that can be managed by an agent.

        :param environment The environment this resource is defined in
        :param resource_id The resource id of this resource

        The following parameters are derived directly from the resource_id:
        :param resource_type The type of the resource
        :param agent The agent that manages this resource (not a reference but can be used to query for agents)
        :param attribute_name The name of the identifying attribute
        :param attribute_value The value of the identifying attribute
        :param last_deploy When was the last deploy this resource
    """
    environment = ReferenceField(reference_document_type=Environment, sparse=True)
    resource_id = StringField(required=True, sparse=True)

    resource_type = StringField(required=True)
    agent = StringField(required=True)
    attribute_name = StringField(required=True)
    attribute_value = StringField(required=True)

    holds_state = BooleanField(default=False)

    version_latest = IntField(default=0)
    version_deployed = IntField(default=0)
    last_deploy = DateTimeField()

    def to_dict(self):
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


ACTIONS = ("store", "push", "pull", "deploy", "dryrun", "other")
LOGLEVEL = ("INFO", "ERROR", "WARNING", "DEBUG", "TRACE")


class ResourceAction(Document):
    """
        Log related to actions performed on a specific resource version by Inmanta.

        :param resource_version The resource on which the actions are performed
        :param action The action performed on the resource
        :param timestamp When did the action occur
        :param message The log message associated with this action
        :param level The "urgency" of this action
        :param data A python dictionary that can be serialized to json with additional data
    """
    resource_version = ReferenceField(reference_document_type="inmanta.data.ResourceVersion", sparse=True)
    action = StringField(required=True, sparse=True)
    timestamp = DateTimeField(required=True)
    message = StringField()
    level = StringField(default="INFO")
    data = StringField()
    status = StringField()

    def to_dict(self):
        return {"action": self.action,
                "timestamp": self.timestamp.isoformat(),
                "message": self.message,
                "level": self.level,
                "status": self.status,
                "data": json.loads(self.data) if self.data is not None else None,
                }


class ResourceVersion(Document):
    """
        A specific version of a resource. This entity contains the desired state of a resource.

        :param environment The environment this resource version is defined in
        :param rid The id of the resource and its version
        :param resource The resource for which this defines the state
        :param model The configuration model (versioned) this resource state is associated with
        :param attributes The state of this version of the resource
    """
    environment = ReferenceField(reference_document_type=Environment, required=True, sparse=True)
    rid = StringField(required=True, sparse=True)
    resource = ReferenceField(reference_document_type=Resource, required=True, sparse=True)
    model = ReferenceField(reference_document_type="inmanta.data.ConfigurationModel", required=True)
    attributes = JsonField()
    status = StringField(default="")

    # internal field to handle cross agent dependencies
    # if this resource is updated, it must notify all RV's in this list
    # the list contains full rv id's
    provides = ListField(StringField(), default=[])

    def to_dict(self):
        data = {}
        data["fields"] = self.attributes
        data["id"] = self.rid
        data["id_fields"] = Id.parse_id(self.rid).to_dict()
        data["status"] = self.status

        return data

    @gen.coroutine
    def delete_cascade(self):
        resource_actions = yield ResourceAction.objects.filter(resource_version=self).find_all()
        for r in resource_actions:
            yield r.delete()
        yield self.delete()

    @classmethod
    @gen.coroutine
    def get_resources_for_version(cls, environment, version):
        env = yield Environment.get_uuid(environment)
        if env is None:
            return Exception("The given environment id does not exist!")

        cm = yield ConfigurationModel.get_version(environment, version)
        if cm is None:
            return None

        resources = yield ResourceVersion.objects.filter(environment=env, model=cm).limit(DBLIMIT).find_all()
        return resources

    @classmethod
    @gen.coroutine
    def get_latest_version(cls, environment, resource_id):
        env = yield Environment.get_uuid(environment)
        if env is None:
            return Exception("The given environment id does not exist!")

        resources = yield Resource.objects.filter(environment=env, resource_id=resource_id).find_all()
        if len(resources) == 0:
            return None

        rv = yield ResourceVersion.objects.filter(environment=env,
                                                  resource=resources[0]).order_by("rid",
                                                                                  direction=DESCENDING).limit(1).find_all()

        if len(rv) == 0:
            return None

        return rv[0]

    @classmethod
    @gen.coroutine
    def get(cls, environment_id, resource_version_id):
        """
            Get a resource with the given resource version id
        """
        env = yield Environment.get_uuid(environment_id)
        if env is None:
            return Exception("The given environment id does not exist!")

        results = yield ResourceVersion.objects.filter(environment=env, rid=resource_version_id).find_all()

        if len(results) == 0:
            return None

        if len(results) > 0:
            raise Exception("Invalid database state, multiple resources with same id (%s) found in environment %s" %
                            (resource_version_id, environment_id))

        return results[0]


class ConfigurationModel(Document):
    """
        A specific version of the configuration model.

        :param version The version of the configuration model, represented by a unix timestamp.
        :param environment The environment this configuration model is defined in
        :param date The date this configuration model was created
        :param released Is this model released and available for deployment?
        :param deployed Is this model deployed?
        :param result The result of the deployment. Success or error.
    """
    version = IntField(required=True)
    environment = ReferenceField(reference_document_type=Environment, required=True)
    date = DateTimeField()

    released = BooleanField(default=False)
    deployed = BooleanField(default=False)
    result = StringField(default="pending")
    status = JsonField(default={})
    version_info = JsonField()

    resources_total = IntField(default=0)
    resources_done = IntField(default=0)

    @classmethod
    @gen.coroutine
    def get_version(cls, environment, version):
        env = yield Environment.get_uuid(environment)
        if env is None:
            return Exception("The given environment id does not exist!")

        versions = yield cls.objects.filter(environment=env, version=version).find_all()
        if len(versions) == 0:
            return None

        return versions[0]

    @classmethod
    @gen.coroutine
    def get_latest_version(cls, environment):
        env = yield Environment.get_uuid(environment)
        if env is None:
            return Exception("The given environment id does not exist!")

        versions = yield ConfigurationModel.objects.filter(environment=env,
                                                           released=True).order_by("version",
                                                                                   direction=DESCENDING).limit(1).find_all()

        if len(versions) == 0:
            return None

        return versions[0]

    @classmethod
    @gen.coroutine
    def get_agents(cls, environment, version):
        """
            Returns a list of all agents that have resources defined in this configuration model
        """
        env = yield Environment.get_uuid(environment)
        if env is None:
            return Exception("The given environment id does not exist!")

        model = yield ConfigurationModel.get_version(environment=environment, version=version)
        if model is None:
            return []

        rvs = yield ResourceVersion.objects.filter(model=model, environment=env).limit(DBLIMIT).find_all()  # @UndefinedVariable

        agents = set()
        for rv in rvs:
            rv_dict = rv.to_dict()
            agents.add(rv_dict["id_fields"]["agent_name"])

        return list(agents)

    @gen.coroutine
    def to_dict(self):
        yield self.load_references()
        return {"version": self.version,
                "environment": str(self.environment.uuid),
                "date": self.date,
                "released": self.released,
                "deployed": self.deployed,
                "result": self.result,
                "status": self.status,
                "total": self.resources_total,
                "done": self.resources_done,
                "version_info": self.version_info,
                }

    @gen.coroutine
    def delete_cascade(self):
        yield self.load_references()
        res_versions = yield ResourceVersion.objects.filter(model=self).find_all()
        for resv in res_versions:
            yield resv.delete_cascade()

        snapshots = yield Snapshot.objects.filter(model=self).find_all()
        for snapshot in snapshots:
            yield snapshot.delete_cascade()

        unknowns = yield UnknownParameter.objects.filter(environment=self.environment, version=self.version).find_all()
        for u in unknowns:
            yield u.delete()

        code = yield Code.objects.filter(environment=self.environment, version=self.version).find_all()
        for c in code:
            yield c.delete()

        drs = yield DryRun.objects.filter(model=self).find_all()
        for d in drs:
            yield d.delete()

        yield self.delete()


class Code(Document):
    """
        A code deployment

        :param environment The environment this code belongs to
        :param version The version of configuration model it belongs to
        :param sources The source code of plugins
        :param requires Python requires for the source code above
    """
    environment = ReferenceField(reference_document_type=Environment, sparse=True, required=True)
    resource = StringField(sparse=True, required=True)
    version = IntField(sparse=True, required=True)
    sources = JsonField()

    @classmethod
    @gen.coroutine
    def get_version(cls, environment, version, resource):
        codes = yield cls.objects.filter(environment=environment, version=version, resource=resource).find_all()
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


class ResourceSnapshot(Document):
    """
        Snapshot of a resource

        :param error Indicates if an error made the snapshot fail
    """
    environment = ReferenceField(reference_document_type=Environment)
    snapshot = ReferenceField(reference_document_type="inmanta.data.Snapshot")
    resource_id = StringField()
    state_id = StringField()
    started = DateTimeField()
    finished = DateTimeField()
    content_hash = StringField()
    success = BooleanField()
    error = BooleanField()
    msg = StringField()
    size = IntField()

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


class ResourceRestore(Document):
    """
        A restore of a resource from a snapshot
    """
    environment = ReferenceField(reference_document_type=Environment)
    restore = ReferenceField(reference_document_type="inmanta.data.SnapshotRestore")
    state_id = StringField()
    resource_id = StringField()
    started = DateTimeField()
    finished = DateTimeField()
    success = BooleanField()
    error = BooleanField()
    msg = StringField()

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


class SnapshotRestore(IdDocument):
    """
        Information about a snapshot restore
    """
    environment = ReferenceField(reference_document_type=Environment)
    snapshot = ReferenceField(reference_document_type="inmanta.data.Snapshot")
    started = DateTimeField()
    finished = DateTimeField()
    resources_todo = IntField(default=0)

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


class Snapshot(IdDocument):
    """
        A snapshot of an environment

        :param id The id of the snapshot
        :param environment A reference to the environment
        :param started When was this snapshot started
        :param finished When was this snapshot finished
        :param total_size The total size of this snapshot
    """
    environment = ReferenceField(reference_document_type=Environment)
    model = ReferenceField(reference_document_type=ConfigurationModel)
    name = StringField()
    started = DateTimeField()
    finished = DateTimeField()
    total_size = IntField(default=0)
    resources_todo = IntField(default=0)

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


def connect(host, port, database, io_loop):
    client = motor_tornado.MotorClient(host, port, io_loop=io_loop)
    db = client[database]

    for cls in [DryRun]:
        cls.set_connection(db)
