"""
    Copyright 2015 Impera

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Contact: bart@impera.io
"""

import datetime
import logging
import os
import difflib
import subprocess
import re
import threading
import sys
from collections import defaultdict
import uuid
import json
import glob
import time
import base64

from motorengine import connect, errors, ASCENDING
from motorengine.connection import disconnect
from impera import methods
from impera import protocol
from impera import data
from impera.config import Config
from impera.resources import Id, HostNotFoundException
import dateutil
from impera.agent.io.remote import RemoteIO
from impera.ast import type
from tornado import gen
from tornado.ioloop import IOLoop


LOGGER = logging.getLogger(__name__)


class Server(protocol.ServerEndpoint):
    """
        The central Impera server that communicates with clients and agents and persists configuration
        information

        :param usedb Use a database to store data. If not, only facts are persisted in a yaml file.
    """
    def __init__(self, database_host=None, database_port=None):
        super().__init__("server", role="server")
        LOGGER.info("Starting server endpoint")
        self._server_storage = self.check_storage()
        self.check_keys()

        self._db = None
        if database_host is None:
            database_host = Config.get("database", "host", "localhost")

        if database_port is None:
            database_port = Config.get("database", "port", 27017)

        self._db = connect(Config.get("database", "name", "impera"), host=database_host, port=database_port)
        LOGGER.info("Connected to mongodb database %s on %s:%d", Config.get("database", "name", "impera"),
                    database_host, database_port)

        self._fact_expire = int(Config.get("server", "fact-expire", 3600))
        self._fact_renew = int(Config.get("server", "fact-renew", self._fact_expire / 3))

        self.add_end_point_name(self.node_name)

        self.schedule(self.renew_expired_facts, self._fact_renew)
        self.schedule(self._purge_versions, int(Config.get("server", "purge-versions-interval", 3600)))

        IOLoop.current().add_callback(self._purge_versions)

        self._requests = defaultdict(dict)
        self._recompiles = defaultdict(lambda: None)

        self._requires_agents = {}

        if Config.getboolean("server", "autostart-on-start", True):
            def start_agents(agents):
                for agent in agents:
                    if self._agent_matches(agent.name):
                        env_id = str(agent.environment.id)
                        if env_id not in self._requires_agents:
                            agent_data = {"agents": set(), "process": None}
                            self._requires_agents[env_id] = agent_data

                        self._requires_agents[env_id]["agents"].add(agent.name)

                for env_id in self._requires_agents.keys():
                    agent = list(self._requires_agents[env_id]["agents"])[0]
                    self._requires_agents[env_id]["agents"].remove(agent)
                    self._ensure_agent(env_id, agent)

            data.Agent.objects.find_all(callback=start_agents)  # @UndefinedVariable

    def stop(self):
        disconnect()
        super().stop()

    def check_keys(self):
        """
            Check if the ssh key(s) credentials of this server are configured properly
        """
        # TODO

    @gen.coroutine
    def _purge_versions(self):
        """
            Purge versions from the database
        """
        envs = yield data.Environment.objects.find_all()  # @UndefinedVariable
        for env_item in envs:
            # get available versions
            n_versions = int(Config.get("server", "available-versions-to-keep", 2))
            versions = yield data.ConfigurationModel.objects.filter(released=False,  # @UndefinedVariable
                                                                    environment=env_item).find_all()  # @UndefinedVariable
            if len(versions) > n_versions:
                LOGGER.info("Removing %s available versions from environment %s", len(versions) - n_versions, env_item.id)
                versions = versions.order_by("-date")[n_versions:]
                futures = [v.delete() for v in versions]
                yield futures

    def check_storage(self):
        """
            Check if the server storage is configured and ready to use.
        """
        if "config" not in Config.get() or "state-dir" not in Config.get()["config"]:
            raise Exception("The Impera server requires a state directory to be configured")

        state_dir = Config.get()["config"]["state-dir"]

        if not os.path.exists(state_dir):
            os.mkdir(state_dir)

        server_state_dir = os.path.join(state_dir, "server")

        if not os.path.exists(server_state_dir):
            os.mkdir(server_state_dir)

        dir_map = {"server": server_state_dir}

        file_dir = os.path.join(server_state_dir, "files")
        dir_map["files"] = file_dir
        if not os.path.exists(file_dir):
            os.mkdir(file_dir)

        db_dir = os.path.join(server_state_dir, "database")
        dir_map["db"] = db_dir
        if not os.path.exists(db_dir):
            os.mkdir(db_dir)

        environments_dir = os.path.join(server_state_dir, "environments")
        dir_map["environments"] = environments_dir
        if not os.path.exists(environments_dir):
            os.mkdir(environments_dir)

        env_agent_dir = os.path.join(server_state_dir, "agents")
        dir_map["agents"] = env_agent_dir
        if not os.path.exists(env_agent_dir):
            os.mkdir(env_agent_dir)

        return dir_map

    def queue_request(self, environment, agent, request):
        """
            Queue a request for the agent in the given environment
        """
        environment = str(environment)
        LOGGER.debug("Queueing request for agent %s in environment %s", agent, environment)
        if agent not in self._requests[environment]:
            self._requests[environment][agent] = []

        self._requests[environment][agent].append(request)

    @gen.coroutine
    def _request_parameter(self, param):
        """
            Request the value of a parameter from an agent
        """
        resource_id = param.resource_id
        tid = str(param.environment.id)
        env = param.environment

        if resource_id is not None and resource_id != "":
            # get the latest version
            versions = yield (data.ConfigurationModel.objects.filter(environment=env, released=True).  # @UndefinedVariable
                              order_by("-version").limit(1).find_all())  # @UndefinedVariable

            if len(versions) == 0:
                return 404, {"message": "The environment associated with this parameter does not have any releases."}

            version = versions[0]

            # get the associated resource
            resources = yield data.Resource.objects.filter(environment=env,  # @UndefinedVariable
                                                           resource_id=resource_id).find_all()  # @UndefinedVariable

            if len(resources) == 0:
                return 404, {"message": "The parameter does not exist."}

            resource = resources[0]

            # get a resource version
            rvs = yield data.ResourceVersion.objects.filter(environment=env,  # @UndefinedVariable
                                                            model=version, resource=resource).find_all()  # @UndefinedVariable

            if len(rvs) == 0:
                return 404, {"message": "The parameter does not exist."}

            self.queue_request(tid, resource.agent, {"method": "fact", "resource_id": resource_id, "environment": tid,
                                                     "name": param.name, "resource": rvs[0].to_dict()})

            return 503, {"message": "Agents queried for resource parameter."}

        return 404, {"message": "The parameter does not exist."}

    @gen.coroutine
    def renew_expired_facts(self):
        """
            Send out requests to renew expired facts
        """
        LOGGER.info("Renewing expired parameters")

        updated_before = datetime.datetime.now() - datetime.timedelta(0, (self._fact_expire - self._fact_renew))
        expired_params = yield data.Parameter.objects.filter(updated__lt=updated_before).find_all()  # @UndefinedVariable

        for param in expired_params:
            LOGGER.debug("Requesting new parameter value for %s of resource %s in env %s", param.name, param.resource_id,
                         param.environment.id)
            self._request_parameter(param)

        unknown_parameters = yield data.UnknownParameter.objects.find_all()  # @UndefinedVariable
        for u in unknown_parameters:
            LOGGER.debug("Requesting value for unknown parameter %s of resource %s in env %s", u.name, u.resource_id,
                         u.environment.id)
            self._request_parameter(u)

    @protocol.handle(methods.ParameterMethod.get_param)
    @gen.coroutine
    def get_param(self, tid, id, resource_id=None):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        params = yield data.Parameter.objects.filter(environment=env,  # @UndefinedVariable
                                                     name=id, resource_id=resource_id).find_all()  # @UndefinedVariable

        if len(params) == 0:
            if resource_id is not None and resource_id != "":
                # get the latest version
                versions = yield (data.ConfigurationModel.objects.filter(environment=env, released=True).  # @UndefinedVariable
                                  order_by("-version").limit(1).find_all())  # @UndefinedVariable

                if len(versions) == 0:
                    return 404, {"message": "The parameter does not exist."}

                version = versions[0]

                # get the associated resource
                resources = yield data.Resource.objects.filter(environment=env,  # @UndefinedVariable
                                                               resource_id=resource_id).find_all()  # @UndefinedVariable

                if len(resources) == 0:
                    return 404, {"message": "The parameter does not exist."}

                resource = resources[0]

                # get a resource version
                rvs = yield (data.ResourceVersion.objects.  # @UndefinedVariable
                             filter(environment=env, model=version, resource=resource).find_all())  # @UndefinedVariable

                if len(rvs) == 0:
                    return 404, {"message": "The parameter does not exist."}

                self._ensure_agent(tid, resource.agent)
                self.queue_request(tid, resource.agent, {"method": "fact", "resource_id": resource_id, "environment": tid,
                                                         "name": id, "resource": rvs[0].to_dict()})

                return 503, {"message": "Agents queried for resource parameter."}

            return 404, {"message": "The parameter does not exist."}

        param = params[0]
        # check if it was expired
        now = datetime.datetime.now()
        if (param.updated + datetime.timedelta(0, self._fact_expire)) > now:
            return 200, {"parameter": params[0].to_dict()}

        return self._request_parameter(param)

    @protocol.handle(methods.ParameterMethod.set_param)
    @gen.coroutine
    def set_param(self, tid, id, source, value, resource_id, metadata):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        if resource_id is None:
            resource_id = ""

        params = yield data.Parameter.objects.filter(environment=env,  # @UndefinedVariable
                                                     name=id, resource_id=resource_id).find_all()  # @UndefinedVariable

        if len(params) == 0:
            param = data.Parameter(environment=env, name=id, resource_id=resource_id, value=value, source=source,
                                   updated=datetime.datetime.now(), metadata=metadata)

        else:
            param = params[0]
            param.source = source
            param.value = value
            param.updated = datetime.datetime.now()
            param.metadate = metadata

        futures = [param.save()]

        # check if the parameter is an unknown
        params = data.UnknownParameter.objects(environment=env, name=id, resource_id=resource_id,  # @UndefinedVariable
                                               resolved=False)
        if len(params) > 0:
            LOGGER.info("Received values for unknown parameters %s, triggering a recompile",
                        ", ".join([x.name for x in params]))
            for p in params:
                p.resolved = True
                futures.append(p.save())

            self._async_recompile(tid, False, int(Config.get("server", "wait-after-param", 5)))

        yield futures
        return 200, {"parameter": param.to_dict()}

    @protocol.handle(methods.ParameterMethod.list_params)
    @gen.coroutine
    def list_param(self, tid, query):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        m_query = {"environment": env}
        for k, v in query.items():
            m_query["metadata__" + k] = v

        params = yield data.Parameter.objects.filter(**m_query).find_all()  # @UndefinedVariable

        return_value = []
        for p in params:
            d = p.to_dict()
            return_value.append(d)

        return 200, {"parameters": return_value, "expire": self._fact_expire, "now": datetime.datetime.now().isoformat()}

    @protocol.handle(methods.FormMethod.put_form)
    @gen.coroutine
    def put_form(self, tid: uuid.UUID, id: str, form: dict):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        form = yield data.Form.get_form(environment=env, form_type=id)

        fields = {k: v["type"] for k, v in form["attributes"].items()}
        defaults = {k: v["default"] for k, v in form["attributes"].items() if "default" in v}
        field_options = {k: v["options"] for k, v in form["attributes"].items() if "options" in v}

        if form is None:
            form = data.Form(form_id=uuid.uuid4(), environment=env, form_type=id, fields=fields, defaults=defaults,
                             options=form["options"], field_options=field_options)

        else:
            # update the definition
            form.fields = fields
            form.defaults = defaults
            form.options = form["options"]
            form.field_options = field_options

        yield form.save()

        return 200, {"form": {"id": form.uuid}}

    @protocol.handle(methods.FormMethod.get_form)
    @gen.coroutine
    def get_form(self, tid, id):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        form = yield data.Form.get_form(environment=env, form_type=id)

        if form is None:
            return 404

        return 200, {"form": form.to_dict()}

    @protocol.handle(methods.FormMethod.list_forms)
    @gen.coroutine
    def list_forms(self, tid):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        forms = yield data.Form.objects.filter(environment=env).find_all()  # @UndefinedVariable

        return 200, {"forms": [{"form_id": x.form_id, "form_type": x.form_type} for x in forms]}

    @protocol.handle(methods.FormRecords.list_records)
    @gen.coroutine
    def list_records(self, tid, form_type):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        form_type = yield data.Form.get_form(environment=env, form_type=id)
        if form_type is None:
            return 404, {"message": "No form is defined with id %s" % form_type}

        records = yield data.FormRecord.objects.filter(form=form_type).find_all()  # @UndefinedVariable

        return 200, {"records": [{"record_id": r.uuid, "changed": r.changed} for r in records]}

    @protocol.handle(methods.FormRecords.get_record)
    @gen.coroutine
    def get_record(self, tid, id):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        record = data.FormRecord.get_uuid(id)
        if record is None:
            return 404, {"message": "The record with id %s does not exist" % id}

        record_dict = yield record.to_dict()
        return 200, {"record": record_dict}

    @protocol.handle(methods.FormRecords.update_record)
    @gen.coroutine
    def update_record(self, tid, id, form):
        f1 = data.Environment.get_uuid(tid)
        f2 = data.FormRecord.get_uuid(id)
        env, record = yield [f1, f2]

        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        record.changed = datetime.datetime.now()

        yield record.load_references()

        form_fields = record.form.fields
        for k, _v in form_fields.items():
            if k in form:
                record.fields[k] = form[k]

        _, record_dict = yield [record.save(), record.to_dict()]

        self._async_recompile(tid, False, int(Config.get("server", "wait-after-param", 5)))
        return 200, {"record": record_dict}

    @protocol.handle(methods.FormRecords.create_record)
    @gen.coroutine
    def create_record(self, tid, form_type, form):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        form_obj = yield data.Form.get_form(environment=env, form_type=id)

        record_id = uuid.uuid4()
        record = data.FormRecord(uuid=record_id, environment=env, form=form_obj)
        record.changed = datetime.datetime.now()

        form_fields = record.form.fields
        for k, _v in form_fields.items():
            if k in form:
                value = form[k]
                field_type = form_obj.fields[k]
                if field_type in type.TYPES:
                    type_obj = type.TYPES[field_type]
                    record.fields[k] = type_obj.cast(value)
                else:
                    LOGGER.warning("Field %s in form %s has an invalid type." % (k, form_type))

        yield record.save()
        self._async_recompile(tid, False, int(Config.get("server", "wait-after-param", 5)))
        record_dict = yield record.to_dict()
        return 200, {"record": record_dict}

    @protocol.handle(methods.FormRecords.delete_record)
    def delete_record(self, tid, id):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        record = yield data.FormRecord.get_uuid(id)
        yield record.delete()

        return 200

    @protocol.handle(methods.FileMethod.upload_file)
    def upload_file(self, id, content):
        file_name = os.path.join(self._server_storage["files"], id)

        if os.path.exists(file_name):
            return 500, {"message": "A file with this id already exists."}

        with open(file_name, "wb+") as fd:
            fd.write(base64.b64decode(content))

        return 200

    @protocol.handle(methods.FileMethod.stat_file)
    def stat_file(self, id):
        file_name = os.path.join(self._server_storage["files"], id)

        if os.path.exists(file_name):
            return 200
        else:
            return 404

    @protocol.handle(methods.FileMethod.get_file)
    def get_file(self, id):
        file_name = os.path.join(self._server_storage["files"], id)

        if not os.path.exists(file_name):
            return 404

        else:
            with open(file_name, "rb") as fd:
                return 200, {"content": base64.b64encode(fd.read()).decode("ascii")}

    @protocol.handle(methods.FileMethod.stat_files)
    def stat_files(self, files):
        """
            Return which files in the list exist on the server
        """
        response = []
        for f in files:
            f_path = os.path.join(self._server_storage["files"], f)
            if not os.path.exists(f_path):
                response.append(f)

        return 200, {"files": response}

    @protocol.handle(methods.FileDiff.diff)
    def file_diff(self, a, b):
        """
            Diff the two files identified with the two hashes
        """
        if a == "" or a == "0":
            a_lines = []
        else:
            a_path = os.path.join(self._server_storage["files"], a)
            if not os.path.exists(a_path):
                return 404

            with open(a_path, "r") as fd:
                a_lines = fd.readlines()

        if b == "" or b == "0":
            b_lines = []
        else:
            b_path = os.path.join(self._server_storage["files"], b)
            if not os.path.exists(b_path):
                return 404

            with open(b_path, "r") as fd:
                b_lines = fd.readlines()

        try:
            diff = difflib.unified_diff(a_lines, b_lines, fromfile=a, tofile=b)
        except FileNotFoundError:
            return 404

        return 200, {"diff": list(diff)}

    @protocol.handle(methods.HeartBeatMethod.heartbeat)
    @gen.coroutine
    def heartbeat(self, endpoint_names, nodename, role, interval, environment):
        env = yield data.Environment.get_uuid(environment)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        now = datetime.datetime.now()
        LOGGER.debug("Seen node %s" % nodename)
        node = yield data.Node.get_by_hostname(nodename)
        if node is not None:
            node.last_seen = now
            node.save()

        else:
            node = data.Node(hostname=nodename, last_seen=now)
            yield node.save()

        response = []
        for nh in endpoint_names:
            LOGGER.debug("Seen agent %s on %s", nh, nodename)
            agents = yield data.Agent.objects.filter(name=nh, node=node, environment=env).find_all()  # @UndefinedVariable
            if len(agents) == 0:
                agent = data.Agent(name=nh, node=node, role=role, environment=env)

            else:
                agent = agents[0]

            agent.interval = interval
            agent.last_seen = now
            yield agent.save()

            # check if there is something we need to push to the client
            environment = str(environment)
            if environment in self._requests and nh in self._requests[environment]:
                response.append({"items": self._requests[environment][nh], "agent": nh})
                del self._requests[environment][nh]

        return 200, {"requests": response, "environment": environment}

    @protocol.handle(methods.NodeMethod.get_agent)
    @gen.coroutine
    def get_agent(self, id):
        node = yield data.Node.get_by_hostname(id)
        if node is None:
            return 404

        agents = yield data.Agent.objects.filter(node=node).find_all()  # @UndefinedVariable
        agent_list = []
        for agent in agents:
            agent_dict = yield agent.to_dict()
            agent_list.append(agent_dict)

        return 200, {"node": node.to_dict(), "agents": agent_list}

    @protocol.handle(methods.NodeMethod.trigger_agent)
    @gen.coroutine
    def trigger_agent(self, tid, id):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        self.queue_request(tid, id, {"method": "version", "version": -1, "environment": tid})
        return 200

    @protocol.handle(methods.NodeMethod.list_agents)
    @gen.coroutine
    def list_agent(self, environment):
        response = []
        nodes = yield data.Node.objects.find_all()  # @UndefinedVariable
        for node in nodes:  # @UndefinedVariable
            agents = yield data.Agent.objects.filter(node=node).find_all()  # @UndefinedVariable
            node_dict = node.to_dict()
            node_dict["agents"] = []
            for agent in agents:
                agent_dict = yield agent.to_dict()  # do this first, because it also loads all lazy references
                if environment is None or str(agent.environment.id) == environment:
                    node_dict["agents"].append(agent_dict)

            if len(node_dict["agents"]) > 0:
                response.append(node_dict)

        return 200, {"nodes": response, "servertime": datetime.datetime.now().isoformat()}

    @protocol.handle(methods.ResourceMethod.get_resource)
    @gen.coroutine
    def get_resource_state(self, tid, id, logs):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        resv = yield data.ResourceVersion.objects.filter(environment=env, rid=id).find_all()  # @UndefinedVariable
        if len(resv) == 0:
            return 404, {"message": "The resource with the given id does not exist in the given environment"}

        ra = data.ResourceAction(resource_version=resv[0], action="pull", level="INFO", timestamp=datetime.datetime.now(),
                                 message="Individual resource version pulled by client")
        yield ra.save()

        action_list = []
        if bool(logs):
            actions = yield data.ResourceAction.objects.filter(resource_version=resv[0]).find_all()  # @UndefinedVariable
            for action in actions:
                action_list.append(action.to_dict())

        return 200, {"resource": resv[0].to_dict(), "logs": action_list}

    @protocol.handle(methods.ResourceMethod.get_resources_for_agent)
    def get_resources_for_agent(self, tid, agent, version):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        if version is None:
            versions = yield (data.ConfigurationModel.objects.filter(environment=env, released=True).  # @UndefinedVariable
                              order_by("-version").limit(1).find_all())  # @UndefinedVariable

            if len(versions) == 0:
                return 404

            cm = versions[0]

        else:
            versions = yield data.ConfigurationModel.objects.filter(environment=env, version=version).find_all()  # @UndefinedVariable
            if len(versions) == 0:
                return 404, {"message": "The given version does not exist"}

            cm = versions[0]

        deploy_model = []
        resources = yield data.ResourceVersion.objects.filter(environment=env, model=cm).find_all()  # @UndefinedVariable

        futures = [rv.load_references() for rv in resources]
        yield futures

        futures = [rv.agent.load_references() for rv in resources]
        yield futures

        futures = []
        for rv in resources:
            if rv.resource.agent == agent:
                deploy_model.append(rv.to_dict())
                ra = data.ResourceAction(resource_version=rv, action="pull", level="INFO", timestamp=datetime.datetime.now(),
                                         message="Resource version pulled by client for agent %s state" % agent)
                futures.append(ra.save())

        yield futures

        return 200, {"environment": tid, "agent": agent, "version": cm.version, "resources": deploy_model}

    @protocol.handle(methods.CMVersionMethod.list_versions)
    @gen.coroutine
    def list_version(self, tid, start=None, limit=None):
        if (start is None and limit is not None) or (limit is None and start is not None):
            return 500, {"message": "Start and limit should always be set together."}

        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        models = yield data.ConfigurationModel.objects.filter(environment=env).order_by("version", direction=ASCENDING).find_all()  # @UndefinedVariable
        count = len(models)

        if start is not None:
            models = models[int(start):int(limit) + int(start)]

        d = {"versions": []}
        for m in models:
            model_dict = yield m.to_dict()
            d["versions"].append(model_dict)

        if start is not None:
            d["start"] = start
            d["limit"] = limit

        d["count"] = count

        return 200, d

    @protocol.handle(methods.CMVersionMethod.get_version)
    @gen.coroutine
    def get_version(self, tid, id, include_logs=None, log_filter=None, limit=None):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        version = yield data.ConfigurationModel.get_version(env, id)
        if version is None:
            return 404, {"message": "The given configuration model does not exist yet."}

        resources = yield data.ResourceVersion.objects(model=version)  # @UndefinedVariable

        version_dict = yield version.to_dict()
        d = {"model": version_dict}

        d["resources"] = []
        for res in resources:
            res_dict = res.to_dict()

            if bool(include_logs):
                if log_filter is not None:
                    actions = data.ResourceAction.objects(resource_version=res, action=log_filter)  # @UndefinedVariable
                else:
                    actions = data.ResourceAction.objects(resource_version=res)  # @UndefinedVariable

                actions = yield actions.order_by("timestamp", direction=ASCENDING).find_all()

                if limit is not None:
                    actions = actions[0:int(limit)]

                res_dict["actions"] = [x.to_dict() for x in actions]

            d["resources"].append(res_dict)

        unp = yield data.UnknownParameter.objects.filter(environment=env, version=version.version).find_all()  # @UndefinedVariable
        d["unknowns"] = [x.to_dict() for x in unp]

        return 200, d

    @protocol.handle(methods.CMVersionMethod.delete_version)
    @gen.coroutine
    def delete_version(self, tid, id):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        version = yield data.ConfigurationModel.get_version(env, id)
        if version is None:
            return 404, {"message": "The given configuration model does not exist yet."}

        yield version.delete()
        return 200

    @protocol.handle(methods.CMVersionMethod.put_version)
    @gen.coroutine
    def put_version(self, tid, version, resources, unknowns, version_info):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        version = yield data.ConfigurationModel.get_version(env, id)
        if version is not None:
            return 500, {"message": "The given version is already defined. Versions should be unique."}

        cm = data.ConfigurationModel(environment=env, version=version, date=datetime.datetime.now(),
                                     resources_total=len(resources), version_info=version_info)
        yield cm.save()

        for res_dict in resources:
            resource_obj = Id.parse_id(res_dict['id'])
            resource_id = resource_obj.resource_str()

            resources = yield data.Resource.objects.filter(environment=env, resource_id=resource_id).find_all()  # @UndefinedVariable
            if len(resources) > 0:
                if len(resources) == 1:
                    resource = resources[0]
                    resource.version_latest = version

                else:
                    raise Exception("A resource id should be unique in an environment! (env=%s, resource=%s)" %
                                    (tid, resource_id))

            else:
                resource = data.Resource(environment=env, resource_id=resource_id,
                                         resource_type=resource_obj.get_entity_type(),
                                         agent=resource_obj.get_agent_name(),
                                         attribute_name=resource_obj.get_attribute(),
                                         attribute_value=resource_obj.get_attribute_value(), version_latest=version)

            if "state_id" in res_dict:
                resource.holds_state = True
                if res_dict["state_id"] == "":
                    res_dict["state_id"] = resource_id

            attributes = {}
            for field, value in res_dict.items():
                if field != "id":
                    attributes[field.replace(".", "\uff0e").replace("$", "\uff04")] = json.dumps(value)

            yield resource.save()

            rv = data.ResourceVersion(environment=env, rid=res_dict['id'], resource=resource, model=cm, attributes=attributes)
            yield rv.save()

            ra = data.ResourceAction(resource_version=rv, action="store", level="INFO", timestamp=datetime.datetime.now())
            yield ra.save()

        # search for deleted resources
        env_resources = yield data.Resource.objects.filter(environment=tid).find_all()  # @UndefinedVariable
        for res in env_resources:
            if res.version_latest < version:
                rv = yield data.ResourceVersion.objects.filter(environment=env, resource=res).order_by("rid", direction=ASCENDING).limit(1).find_all()  # @UndefinedVariable
                if len(rv) > 0:
                    rv = rv[0]
                    if "purge_on_delete" in rv.attributes and rv.attributes["purge_on_delete"]:
                        LOGGER.warning("Purging %s, purged resource based on %s" % (res.resource_id, rv.rid))

                        res.version_latest = version
                        yield res.save()

                        attributes = rv.attributes.copy()
                        attributes["purged"] = "true"
                        rv = data.ResourceVersion(environment=env, rid="%s,v=%s" % (res.resource_id, version),
                                                  resource=res, model=cm, attributes=attributes)
                        yield rv.save()

                        ra = data.ResourceAction(resource_version=rv, action="store", level="INFO",
                                                 timestamp=datetime.datetime.now())
                        yield ra.save()

                        cm.resources_total += 1
                        yield cm.save()

        futures = []
        for uk in unknowns:
            if "resource" not in uk:
                uk["resource"] = ""

            if "metadata" not in uk:
                uk["metadata"] = {}

            up = data.UnknownParameter(resource_id=uk["resource"], name=uk["parameter"], source=uk["source"], environment=env,
                                       version=version, metadata=uk["metadata"])
            futures.append(up.save())

        yield futures

        LOGGER.debug("Successfully stored version %d" % version)

        return 200

    def _agent_matches(self, agent_name):
        agent_globs = [x.strip() for x in Config.get("server", "agent_autostart", "iaas_*").split(",")]

        for agent_glob in agent_globs:
            if glob.fnmatch.fnmatchcase(agent_name, agent_glob):
                return True

        return False

    def _ensure_agent(self, environment_id, agent_name):
        """
            Ensure that the agent is running if required
        """
        if self._agent_matches(agent_name):
            LOGGER.debug("%s matches agents managed by server, ensuring it is started.", agent_name)
            agent_data = None
            if environment_id in self._requires_agents:
                agent_data = self._requires_agents[environment_id]

                if agent_name in agent_data["agents"]:
                    return

            if agent_data is None:
                agent_data = {"agents": set(), "process": None}
                self._requires_agents[environment_id] = agent_data

            agent_data["agents"].add(agent_name)

            agent_names = ",".join(agent_data["agents"])

            agent_map = {}
            for agent in agent_data["agents"]:
                try:
                    gw = RemoteIO(agent)
                    gw.close()
                except HostNotFoundException:
                    agent_map[agent] = "localhost"

            port = Config.get("server_rest_transport", "port", "8888")

            # generate config file
            config = """[config]
heartbeat-interval = 60
state-dir=/var/lib/impera

agent-names = %(agents)s
environment=%(env_id)s
agent-map=%(agent_map)s

[agent_rest_transport]
port = %(port)s
host = localhost
""" % {"agents": agent_names, "env_id": environment_id, "port": port, "agent_map":
                ",".join(["%s=%s" % (k, v) for k, v in agent_map.items()])}

            config_dir = os.path.join(self._server_storage["agents"], str(environment_id))
            if not os.path.exists(config_dir):
                os.mkdir(config_dir)

            config_path = os.path.join(config_dir, "agent.cfg")
            with open(config_path, "w+") as fd:
                fd.write(config)

            proc = self._fork_impera(["-vvv", "-c", config_path, "agent"])

            if agent_data["process"] is not None:
                LOGGER.debug("Terminating old agent with PID %s", agent_data["process"].pid)
                agent_data["process"].terminate()

            threading.Thread(target=proc.communicate).start()
            agent_data["process"] = proc

            LOGGER.debug("Started new agent with PID %s", proc.pid)

    @protocol.handle(methods.CMVersionMethod.release_version)
    @gen.coroutine
    def release_version(self, tid, id, push):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        model = yield data.ConfigurationModel.get_version(env, id)
        if model is None:
            return 404, {"message": "The request version does not exist."}

        model.released = True
        model.result = "deploying"
        yield model.save()

        if push:
            # fetch all resource in this cm and create a list of distinct agents
            rvs = yield data.ResourceVersion.objects.filter(model=model, environment=env).find_all()  # @UndefinedVariable
            agents = set()
            for rv in rvs:
                agents.add(rv.resource.agent)

            for agent in agents:
                self._ensure_agent(tid, agent)
                self.queue_request(tid, agent, {"method": "version", "version": id, "environment": tid})

        model_dict = yield model.to_dict()
        return 200, {"model": model_dict}

    @protocol.handle(methods.DryRunMethod.dryrun_request)
    @gen.coroutine
    def dryrun_request(self, tid, id):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        model = yield data.ConfigurationModel.get_version(environment=env, version=id)
        if model is None:
            return 404, {"message": "The request version does not exist."}

        # Create a dryrun document
        dryrun_id = str(uuid.uuid4())
        dryrun = data.DryRun(uuid=dryrun_id, environment=env, model=model, date=datetime.datetime.now())

        # fetch all resource in this cm and create a list of distinct agents
        rvs = yield data.ResourceVersion.objects.filter(model=model, environment=env).find_all()  # @UndefinedVariable
        dryrun.resource_total = len(rvs)
        dryrun.resource_todo = dryrun.resource_total

        agents = set()
        for rv in rvs:
            agents.add(rv.resource.agent)

        tid = str(tid)
        for agent in agents:
            self._ensure_agent(tid, agent)
            self.queue_request(tid, agent, {"method": "dryrun", "version": id, "environment": tid, "dryrun": dryrun_id})

        _, dryrun_dict = yield dryrun.save(), dryrun.to_dict()
        return 200, {"dryrun": dryrun_dict}

    @protocol.handle(methods.DryRunMethod.dryrun_list)
    @gen.coroutine
    def dryrun_list(self, tid, version=None):
        query_args = {}
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        query_args["environment"] = env
        if version is not None:
            model = yield data.ConfigurationModel.get_version(environment=env, version=version)
            if model is None:
                return 404, {"message": "The request version does not exist."}

            query_args["model"] = model

        dryruns = yield data.DryRun.objects.filter(**query_args).find_all()  # @UndefinedVariable

        dryrun_futures = [x.load_references() for x in dryruns]
        yield dryrun_futures

        return 200, {"dryruns": [{"id": x.id, "version": x.model.version,
                                  "date": x.date.isoformat(), "total": x.resource_total,
                                  "todo": x.resource_todo
                                  } for x in dryruns]}

    @protocol.handle(methods.DryRunMethod.dryrun_report)
    @gen.coroutine
    def dryrun_report(self, tid, id):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        dryrun = yield data.DryRun.get_uuid(id)
        if dryrun is None:
            return 404, {"message": "The given dryrun does not exist!"}

        dryrun_dict = yield dryrun.to_dict()
        return 200, {"dryrun": dryrun_dict}

    @protocol.handle(methods.DryRunMethod.dryrun_update)
    @gen.coroutine
    def dryrun_update(self, tid, id, resource, changes, log_msg=None):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        dryrun = yield data.DryRun.get_uuid(id)
        if dryrun is None:
            return 404, {"message": "The given dryrun does not exist!"}

        if resource in dryrun.resources:
            return 500, {"message": "A dryrun was already stored for this resource."}

        payload = {"changes": changes,
                   "log": log_msg,
                   "id_fields": Id.parse_id(resource).to_dict()
                   }

        dryrun.resources[resource.replace(".", "\uff0e").replace("$", "\uff04")] = json.dumps(payload)
        dryrun.resource_todo -= 1
        yield dryrun.save()

        return 200

    @protocol.handle(methods.CodeMethod.upload_code)
    @gen.coroutine
    def upload_code(self, tid, id, sources, requires):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        code = data.Code.get_version(environment=env, version=id)  # @UndefinedVariable
        if code is not None:
            return 500, {"message": "Code for this version has already been uploaded."}

        code = data.Code(environment=env, version=id, sources=sources, requires=requires)
        yield code.save()

        return 200

    @protocol.handle(methods.CodeMethod.get_code)
    @gen.coroutine
    def get_code(self, tid, id):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        code = data.Code.get_version(environment=env, version=id)  # @UndefinedVariable
        if code is None:
            return 404, {"message": "The version of the code does not exist."}

        return 200, {"version": id, "environment": tid, "sources": code.sources, "requires": code.requires}

    @protocol.handle(methods.ResourceMethod.resource_updated)
    @gen.coroutine
    def resource_updated(self, tid, id, level, action, message, status, extra_data):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        resv = yield data.ResourceVersion.objects.filter(environment=env, rid=id).find_all()  # @UndefinedVariable
        if len(resv) == 0:
            return 404, {"message": "The resource with the given id does not exist in the given environment"}

        resv = resv[0]
        resv.status = status
        yield resv.save()

        extra_data = json.dumps(extra_data)

        now = datetime.datetime.now()
        ra = data.ResourceAction(resource_version=resv, action=action, message=message, data=extra_data, level=level,
                                 timestamp=now, status=status)
        yield ra.save(), resv.load_references()

        model = resv.model
        rid = resv.rid.replace(".", "\uff0e").replace("$", "\uff04")
        if rid not in model.status:
            model.resources_done += 1

        model.status[rid] = status
        yield model.save()

        resv.resource.version_deployed = model.version
        resv.resource.last_deploy = now
        resv.resource.status = status
        yield resv.resource.save()

        if model.resources_done == model.resources_total:
            model.result = "success"
            for status in model.status:
                if status != "deployed":
                    model.result = "failed"

            model.deployed = True
            yield model.save()

        return 200

    # Project handlers
    @protocol.handle(methods.Project.create_project)
    @gen.coroutine
    def create_project(self, name):
        try:
            project = data.Project(name=name, uuid=uuid.uuid4())
            project = yield project.save()
        except errors.UniqueKeyViolationError:
            return 500, {"message": "A project with name %s already exists." % name}

        return 200, {"project": project.to_dict()}

    @protocol.handle(methods.Project.delete_project)
    @gen.coroutine
    def delete_project(self, id):
        project = yield data.Project.get_uuid(id)
        if project is None:
            return 404, {"message": "The project with given id does not exist."}

        yield project.delete_cascade()
        return 200, {}

    @protocol.handle(methods.Project.modify_project)
    @gen.coroutine
    def modify_project(self, id, name):
        try:
            project = yield data.Project.get_uuid(id)
            if project is None:
                return 404, {"message": "The project with given id does not exist."}

            project.name = name
            yield project.save()

            return 200, {"project": project.to_dict()}

        except errors.UniqueKeyViolationError:
            return 500, {"message": "A project with name %s already exists." % name}

    @protocol.handle(methods.Project.list_projects)
    @gen.coroutine
    def list_projects(self):
        projects = yield data.Project.objects.find_all()  # @UndefinedVariable
        return 200, {"projects": [x.to_dict() for x in projects]}

    @protocol.handle(methods.Project.get_project)
    @gen.coroutine
    def get_project(self, id):
        try:
            future_1 = data.Project.get_uuid(id)
            future_2 = data.Environment.objects.find_all(project=id)  # @UndefinedVariable

            project, environments = yield [future_1, future_2]

            if project is None:
                return 404, {"message": "The project with given id does not exist."}

            project_dict = project.to_dict()
            project_dict["environments"] = [e.uuid for e in environments]

            return 200, {"project": project_dict}
        except ValueError:
            return 404, {"message": "The project with given id does not exist."}

        return 500

    # Environment handlers
    @protocol.handle(methods.Environment.create_environment)
    @gen.coroutine
    def create_environment(self, project_id, name, repository, branch):
        if (repository is None and branch is not None) or (repository is not None and branch is None):
            return 500, {"message": "Repository and branch should be set together."}

        # fetch the project first
        project = yield data.Project.get_uuid(project_id)
        if project is None:
            return 500, {"message": "The project id for the environment does not exist."}

        try:
            env = data.Environment(uuid=uuid.uuid4(), name=name, project=project)
            env.repo_url = repository
            env.repo_branch = branch
            yield env.save()

            env_dict = yield env.to_dict()
            return 200, {"environment": env_dict}
        except errors.UniqueKeyViolationError:
            return 500, {"message": "Project %s (id=%s) already has an environment with name %s" %
                         (project.name, project.id, name)}

    @protocol.handle(methods.Environment.modify_environment)
    @gen.coroutine
    def modify_environment(self, id, name, repository, branch):
        env = yield data.Environment.get_uuid(id)
        if env is None:
            return 404, {"message": "The environment id does not exist."}

        try:
            env.name = name
            if repository is not None:
                env.repo_url = repository

            if branch is not None:
                env.repo_branch = branch

            yield env.save()
        except errors.UniqueKeyViolationError:
            return 500, {"message": "Project %s (id=%s) already has an environment with name %s" %
                         (env.project.name, env.project.id, name)}

        env_dict = yield env.to_dict()
        return 200, {"environment": env_dict}

    @protocol.handle(methods.Environment.get_environment)
    @gen.coroutine
    def get_environment(self, id, versions=None, resources=None):
        versions = 0 if versions is None else int(versions)
        resources = 0 if resources is None else int(resources)

        env = yield data.Environment.get_uuid(id)

        if env is None:
            return 404, {"message": "The environment id does not exist."}

        env_dict = yield env.to_dict()

        if versions > 0:
            v = yield data.ConfigurationModel.objects.filter(environment=env).order_by("date", direction=ASCENDING).limit(versions).find_all()  # @UndefinedVariable
            env_dict["versions"] = []
            for model in v:
                model_dict = yield model.to_dict()
                env_dict["versions"].append(model_dict)

        if resources > 0:
            r = yield data.Resource.objects.filter(environment=env).find_all()  # @UndefinedVariable
            env_dict["resources"] = []
            for x in r:
                d = yield x.to_dict()
                env_dict["resources"].append(d)

        return 200, {"environment": env_dict}

    @protocol.handle(methods.Environment.list_environments)
    @gen.coroutine
    def list_environments(self):
        environments = yield data.Environment.objects.find_all()  # @UndefinedVariable
        dicts = []
        for env in environments:
            env_dict = yield env.to_dict()
            dicts.append(env_dict)

        return 200, {"environments": dicts}  # @UndefinedVariable

    @protocol.handle(methods.Environment.delete_environment)
    @gen.coroutine
    def delete_environment(self, id):
        env = yield data.Environment.get_uuid(id)
        if env is None:
            return 404, {"message": "The environment with given id does not exist."}

        compiles = yield data.Compile.objects.filter(environment=env).find_all()  # @UndefinedVariable
        futures = [compile.delete_cascade() for compile in compiles]
        futures.append(env.delete_cascade())
        yield futures

        return 200

    @protocol.handle(methods.NotifyMethod.is_compiling)
    @gen.coroutine
    def is_compiling(self, id):
        if self._recompiles[id] is self:
            return 200

        return 204

    @protocol.handle(methods.NotifyMethod.notify_change)
    @gen.coroutine
    def notify_change(self, id, update):
        LOGGER.info("Received change notification for environment %s", id)
        self._async_recompile(id, update > 0)

        return 200

    def _async_recompile(self, environment_id, update_repo, wait=0):
        """
            Recompile an environment in a different thread and taking wait time into account.
        """
        last_recompile = self._recompiles[environment_id]
        wait_time = int(Config.get("server", "auto-recompile-wait", 600))
        if last_recompile is self:
            LOGGER.info("Already recompiling")
            return

        if last_recompile is None or (datetime.datetime.now() - datetime.timedelta(0, wait_time)) > last_recompile:
            if last_recompile is None:
                LOGGER.info("First recompile")
            else:
                LOGGER.info("Last recompile longer than %s ago (last was at %s)", wait_time, last_recompile)

            self._recompiles[environment_id] = self
            threading.Thread(target=self._recompile_environment, args=(environment_id, update_repo, wait)).start()

        else:
            LOGGER.info("Not recompiling, last recompile less than %s ago (last was at %s)", wait_time, last_recompile)

    def _fork_impera(self, args, cwd=None):
        """
            For an impera process from the same code base as the current code
        """
        impera_path = [sys.executable, os.path.abspath(sys.argv[0])]
        proc = subprocess.Popen(impera_path + args, cwd=cwd, env=os.environ.copy(),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        return proc

    def _run_compile_stage(self, name, cmd, cwd, **kwargs):
        start = datetime.datetime.now()
        proc = subprocess.Popen(cmd, cwd=cwd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, **kwargs)
        log_out, log_err = proc.communicate()
        returncode = proc.returncode
        stop = datetime.datetime.now()
        return data.Report(started=start, completed=stop, name=name, command=" ".join(cmd),
                           errstream=log_err, outstream=log_out, returncode=returncode)

    @gen.coroutine
    def _recompile_environment(self, environment_id, update_repo=False, wait=0):
        """
            Recompile an environment
        """
        if wait > 0:
            time.sleep(wait)

        try:
            impera_path = [sys.executable, os.path.abspath(sys.argv[0])]
            project_dir = os.path.join(self._server_storage["environments"], str(environment_id))
            requested = datetime.datetime.now()
            stages = []

            env = yield data.Environment.get_uuid(environment_id)
            if env is None:
                LOGGER.error("Environment %s does not exist.", environment_id)
                return

            if not os.path.exists(project_dir):
                LOGGER.info("Creating project directory for environment %s at %s", environment_id, project_dir)
                os.mkdir(project_dir)

            # checkout repo
            if not os.path.exists(os.path.join(project_dir, ".git")):
                LOGGER.info("Cloning repository into environment directory %s", project_dir)
                result = self._run_compile_stage("Cloning repository", ["git", "clone", env.repo_url, "."], project_dir)
                stages.append(result)
                if result.returncode > 0:
                    return

            elif update_repo:
                LOGGER.info("Fetching changes from repo %s", env.repo_url)
                stages.append(self._run_compile_stage("Fetching changes", ["git", "fetch", env.repo_url], project_dir))

            # verify if branch is correct
            proc = subprocess.Popen(["git", "branch"], cwd=project_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, _ = proc.communicate()

            o = re.search("\* ([^\s]+)$", out.decode(), re.MULTILINE)
            if o is not None and env.repo_branch != o.group(1):
                LOGGER.info("Repository is at %s branch, switching to %s", o.group(1), env.repo_branch)
                stages.append(self._run_compile_stage("switching branch", ["git", "checkout", env.repo_branch], project_dir))

            if update_repo:
                stages.append(self._run_compile_stage("Pulling updates", ["git", "pull"], project_dir))
                LOGGER.info("Installing and updating modules")
                stages.append(self._run_compile_stage("Installing modules", impera_path + ["modules", "install"], project_dir))
                stages.append(self._run_compile_stage("Updating modules", impera_path + ["modules", "update"], project_dir,
                                                      env=os.environ.copy()))

            LOGGER.info("Recompiling configuration model")
            server_address = Config.get("server", "server_address", "localhost")
            stages.append(self._run_compile_stage("Recompiling configuration model",
                                                  impera_path + ["-vvv", "export", "-e", str(environment_id),
                                                                 "--server_address", server_address, "--server_port",
                                                                 Config.get("server_rest_transport", "port", "8888")],
                                                  project_dir, env=os.environ.copy()))
        finally:
            end = datetime.datetime.now()
            self._recompiles[environment_id] = end
            futures = [x.save() for x in stages]
            futures.append(data.Compile(environment=env, started=requested, completed=end, reports=stages).save())

            yield futures

    @protocol.handle(methods.CompileReport.get_reports)
    @gen.coroutine
    def get_reports(self, environment=None, start=None, end=None, limit=None):
        argscount = len([x for x in [start, end, limit] if x is not None])
        if argscount == 3:
            return 500, {"message": "Limit, start and end can not be set togheter"}

        queryparts = {}

        if environment is not None:
            env = yield data.Environment.get_uuid(environment)
            if env is None:
                return 404, {"message": "The given environment id does not exist!"}

            queryparts["environment"] = env

        if start is not None:
            queryparts["started__gt"] = dateutil.parser.parse(start)

        if end is not None:
            queryparts["started__lt"] = dateutil.parser.parse(end)

        if limit is not None and end is not None:
            # no negative indices supported
            models = yield data.Compile.objects.filter(**queryparts).order_by("started").find_all()  # @UndefinedVariable
            models = list(models[:int(limit)])
            models.reverse()
        else:
            models = yield (data.Compile.objects.filter(**queryparts).  # @UndefinedVariable
                            order_by("started", direction=ASCENDING).find_all())  # @UndefinedVariable
            if limit is not None:
                models = models[:int(limit)]

        futures = [m.to_dict() for m in models]
        reports = yield futures
        d = {"reports": reports}

        return 200, d

    @protocol.handle(methods.Snapshot.list_snapshots)
    @gen.coroutine
    def list_snapshots(self, tid):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        snapshots = yield data.Snapshot.objects.filter(environment=env).find_all()  # @UndefinedVariable
        return 200, {"snapshots": [s.to_dict() for s in snapshots]}

    @protocol.handle(methods.Snapshot.get_snapshot)
    @gen.coroutine
    def get_snapshot(self, tid, id):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        snapshot = yield data.Snapshot.get_uuid(id)
        if snapshot is None:
            return 404, {"message": "The given snapshot id does not exist!"}
        snap_dict = yield snapshot.to_dict()

        resources = yield data.ResourceSnapshot.objects.filter(snapshot=snapshot).find_all()  # @UndefinedVariable
        snap_dict["resources"] = [x.to_dict() for x in resources]

        return 200, {"snapshot": snap_dict}

    @protocol.handle(methods.Snapshot.create_snapshot)
    @gen.coroutine
    def create_snapshot(self, tid, name):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        # get the latest deployed configuration model
        versions = yield (data.ConfigurationModel.objects.filter(environment=env, deployed=True).  # @UndefinedVariable
                          order_by("version", direction=ASCENDING).limit(1).find_all())  # @UndefinedVariable

        if len(versions) == 0:
            return 500, {"message": "There is no deployed configuration model to create a snapshot."}

        version = versions[0]

        LOGGER.info("Creating a snapshot from version %s in environment %s", version.version, tid)

        # create the snapshot
        snapshot_id = uuid.uuid4()
        snapshot = data.Snapshot(id=snapshot_id, environment=env, model=version, started=datetime.datetime.now(), name=name)
        yield snapshot.save()

        # find resources with state
        resources_to_snapshot = defaultdict(list)
        resource_list = []
        resource_states = yield data.ResourceVersion.objects.filter(environment=env, model=version).find_all()  # @UndefinedVariable
        for rs in resource_states:
            if rs.resource.holds_state and "state_id" in rs.attributes:
                agent = rs.resource.agent
                resources_to_snapshot[agent].append(rs.to_dict())
                resource_list.append(rs.resource.resource_id)
                r = data.ResourceSnapshot(environment=env, snapshot=snapshot, resource_id=rs.resource.resource_id,
                                          state_id=rs.attributes["state_id"])
                yield r.save()

        if len(resource_list) == 0:
            snapshot.finished = datetime.datetime.now()
            snapshot.total_size = 0
        else:
            snapshot.resources_todo = len(resource_list)

        yield snapshot.save()

        for agent, resources in resources_to_snapshot.items():
            self.queue_request(tid, agent, {"method": "snapshot", "environment": tid, "snapshot_id": snapshot_id,
                               "resources": resources})

        value = yield snapshot.to_dict()
        value["resources"] = resource_list
        return 200, {"snapshot": value}

    @protocol.handle(methods.Snapshot.update_snapshot)
    @gen.coroutine
    def update_snapshot(self, tid, id, resource_id, snapshot_data, start, stop, size, success, error, msg):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        snapshot = data.Snapshot.get_uuid(tid)
        if snapshot is None:
            return 404, {"message": "Snapshot with id %s does not exist!" % id}

        res = yield data.ResourceSnapshot.objects.filter(environment=env,  # @UndefinedVariable
                                                         snapshot=snapshot, resource_id=resource_id).find_all()  # @UndefinedVariable

        res.content_hash = snapshot_data
        res.started = start
        res.finished = stop
        res.size = size
        res.success = success
        res.error = error
        res.msg = msg

        yield res.save()

        snapshot.resources_todo -= 1
        snapshot.total_size += size

        if snapshot.resources_todo == 0:
            snapshot.finished = datetime.datetime.now()

        yield snapshot.save()

        return 200

    @protocol.handle(methods.Snapshot.delete_snapshot)
    @gen.coroutine
    def delete_snapshot(self, tid, id):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        snapshot = yield data.Snapshot.get_uuid(id)
        if snapshot is None:
            return 404, {"message": "Snapshot with id %s does not exist!" % id}

        yield snapshot.delete_cascade()

        return 200

    @protocol.handle(methods.RestoreSnapshot.restore_snapshot)
    @gen.coroutine
    def restore_snapshot(self, tid, snapshot):
        f1 = data.Environment.get_uuid(tid)
        f2 = data.Snapshot.get_uuid(id)
        env, snapshot = yield f1, f2

        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        if snapshot is None:
            return 404, {"message": "Snapshot with id %s does not exist!" % snapshot}

        # get all resources in the snapshot
        snap_resources = yield data.ResourceSnapshot.objects.fitler(snapshot=snapshot).find_all()  # @UndefinedVariable

        # get all resource that support state in the current environment
        env_versions = yield (data.ConfigurationModel.objects(environment=env, deployed=True).  # @UndefinedVariable
                              order_by("version", direction=ASCENDING).limit(1).find_all())  # @UndefinedVariable

        if len(env_versions) == 0:
            return 500, {"message": "There is no deployed configuration model in this environment."}
        else:
            env_version = env_versions[0]

        env_resources = yield data.ResourceVersion.objects.filter(model=env_version).find_all()  # @UndefinedVariable
        env_states = {}
        for r in env_resources:
            if "state_id" in r.attributes:
                env_states[r.attributes["state_id"]] = r

        # create a restore object
        restore_id = uuid.uuid4()
        restore = data.SnapshotRestore(uuid=restore_id, snapshot=snapshot, environment=env, started=datetime.datetime.now())
        yield restore.save()

        # find matching resources
        restore_list = defaultdict(list)
        for r in snap_resources:
            if r.state_id in env_states:
                env_res = env_states[r.state_id]
                LOGGER.debug("Matching state_id %s to %s, scheduling restore" % (r.state_id, env_res.id))
                restore_list[env_res.resource.agent].append((r.to_dict(), env_res.to_dict()))

                rr = data.ResourceRestore(environment=env, restore=restore, state_id=r.state_id, resource_id=env_res.rid,
                                          started=datetime.datetime.now(), )
                yield rr.save()
                restore.resources_todo += 1

        yield restore.save()

        for agent, resources in restore_list.items():
            self.queue_request(tid, agent, {"method": "restore", "environment": tid, "restore_id": restore_id,
                                            "snapshot_id": snapshot.id, "resources": resources})
        restore_dict = yield restore.to_dict()
        return 200, restore_dict

    @protocol.handle(methods.RestoreSnapshot.list_restores)
    @gen.coroutine
    def list_restores(self, tid):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        restores = yield data.SnapshotRestore.objects.filter(environment=env).find_all()  # @UndefinedVariable
        restore_list = yield [x.to_dict() for x in restores]
        return 200, restore_list

    @protocol.handle(methods.RestoreSnapshot.get_restore_status)
    @gen.coroutine
    def get_restore_status(self, tid, id):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        restore = data.SnapshotRestore.get_uuid(id)
        if restore is None:
            return 404, {"message": "The given restore id does not exist!"}

        restore_dict = yield restore.to_dict()
        resources = yield data.ResourceRestore.objects.filter(restore=restore).find_all()  # @UndefinedVariable
        restore_dict["resources"] = [x.to_dict() for x in resources]
        return 200, {"restore": restore_dict}

    @protocol.handle(methods.RestoreSnapshot.update_restore)
    @gen.coroutine
    def update_restore(self, tid, id, resource_id, success, error, msg, start, stop):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        rr = yield data.ResourceRestore.objects.filter(environment=env, restore=id, resource_id=resource_id).find_all()  # @UndefinedVariable
        if rr is None:
            return 404, {"message": "Resource restore not found."}

        rr.error = error
        rr.success = success
        rr.started = start
        rr.finished = stop
        yield rr.save(), rr.load_references()

        rr.restore.resource_todo -= 1
        if rr.restore.resource_todo == 0:
            rr.restore.finished = datetime.datetime.now()
            yield rr.restore.save()

        return 200

    @protocol.handle(methods.RestoreSnapshot.delete_restore)
    @gen.coroutine
    def delete_restore(self, tid, id):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        restore = yield data.SnapshotRestore.get_uuid(id)
        if restore is None:
            return 404, {"message": "The given restore id does not exist!"}

        yield restore.delete()
        return 200

    @protocol.handle(methods.Decommision.decomission_environment)
    @gen.coroutine
    def decomission_environment(self, id):
        env = yield data.Environment.get_uuid(id)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        version = int(time.time())
        result = yield self.put_version(id, version, [], [], {})
        return result

    @protocol.handle(methods.Decommision.clear_environment)
    @gen.coroutine
    def clear_environment(self, id):
        """
            Clear the environment
        """
        env = yield data.Environment.get_uuid(id)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        models = data.ConfigurationModel.objects.filter(environment=env).find_all()  # @UndefinedVariable
        futures = [model.delete_cascade() for model in models]

        futures.append(data.Resource.objects.filter(environment=env).find_all().delete())  # @UndefinedVariable
        futures.append(data.Parameter.objects(environment=env).delete())  # @UndefinedVariable
        futures.append(data.Agent.objects(environment=env).delete())  # @UndefinedVariable
        futures.append(data.Form.objects(environment=env).delete())  # @UndefinedVariable
        futures.append(data.FormRecord.objects(environment=env).delete())  # @UndefinedVariable
        futures.append(data.Compile.objects(environment=env).delete())  # @UndefinedVariable

        yield futures
        return 200
