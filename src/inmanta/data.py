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

from motorengine import Document
from motorengine.fields import (StringField, ReferenceField, DateTimeField, IntField, UUIDField, BooleanField)
from motorengine.fields.json_field import JsonField
from inmanta.resources import Id
from tornado import gen
from motorengine.fields.list_field import ListField
from motorengine.fields.embedded_document_field import EmbeddedDocumentField


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
        futures = [env.delete_cascade() for env in envs]
        futures.append(self.delete())
        yield futures


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
        futures = [model.delete_cascade() for model in models]
        futures.append(self.delete())
        yield futures


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


class Node(Document):
    """
        A physical server/node in the infrastructure that reports to the management server.

        :param hostname The hostname of the device.
        :param last_seen When did the server receive data from the node for the last time.
    """
    hostname = StringField(required=True, unique=True)
    last_seen = DateTimeField()

    def to_dict(self):
        return {"hostname": self.hostname, "last_seen": self.last_seen.isoformat()}

    @classmethod
    @gen.coroutine
    def get_by_hostname(cls, hostname):
        nodes = yield cls.objects.filter(hostname=hostname).find_all()
        if len(nodes) == 0:
            return None

        return nodes[0]


class Agent(Document):
    """
        An inmanta agent that runs on a device.

        :param environment The environment this resource is defined in
        :param node The node on which this agent is deployed
        :param resources A list of resources that this agent handles
        :param name The name of this agent
        :param role The role of this agent
        :param last_seen When did the server receive data from the node for the last time.
        :param interval The reporting interval of this agent
    """
    environment = ReferenceField(reference_document_type=Environment)
    node = ReferenceField(reference_document_type=Node, required=True)
    name = StringField(required=True)
    last_seen = DateTimeField()
    interval = IntField()

    @gen.coroutine
    def to_dict(self):
        yield self.load_references()
        return {"name": self.name,
                "last_seen": self.last_seen.isoformat(),
                "interval": self.interval,
                "node": self.node.hostname,
                "environment": str(self.environment.uuid),
                }


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
        yield [r.delete() for r in resource_actions]
        yield self.delete(self)


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
        versions = yield cls.objects.filter(environment=environment, version=version).find_all()
        if len(versions) == 0:
            return None

        return versions[0]

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

        yield self.delete(self)


class Code(Document):
    """
        A code deployment

        :param environment The environment this code belongs to
        :param version The version of configuration model it belongs to
        :param sources The source code of plugins
        :param requires Python requires for the source code above
    """
    environment = ReferenceField(reference_document_type=Environment)
    version = IntField()
    sources = JsonField()
    requires = JsonField()

    @classmethod
    @gen.coroutine
    def get_version(cls, environment, version):
        codes = yield cls.objects.filter(environment=environment, version=version).find_all()
        if len(codes) == 0:
            return None

        return codes[0]


class DryRun(IdDocument):
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
    environment = ReferenceField(reference_document_type=Environment)
    model = ReferenceField(reference_document_type=ConfigurationModel)
    date = DateTimeField()
    resource_total = IntField()
    resource_todo = IntField()
    resources = JsonField()

    @gen.coroutine
    def to_dict(self):
        yield self.load_references()
        return {"id": self.uuid,
                "environment": str(self.environment.uuid),
                "model": str(self.model.version),
                "date": self.date.isoformat(),
                "total": self.resource_total,
                "todo": self.resource_todo,
                "resources": self.resources,
                }


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

        yield self.delete(self)
