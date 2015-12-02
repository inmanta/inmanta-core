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
from threading import RLock
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

from mongoengine import connect, errors
from impera import methods
from impera import protocol
from impera import env
from impera import data
from impera.config import Config
from impera.loader import CodeLoader
from impera.resources import Id, HostNotFoundException
import dateutil
from impera.agent.io.remote import RemoteIO


LOGGER = logging.getLogger(__name__)


class Server(protocol.ServerEndpoint):
    """
        The central Impera server that communicates with clients and agents and persists configuration
        information

        :param code_loader Load code deployed from configuration modules
        :param usedb Use a database to store data. If not, only facts are persisted in a yaml file.
    """
    def __init__(self, code_loader=True, usedb=True):
        super().__init__("server", role="server")
        LOGGER.info("Starting server endpoint")
        self._server_storage = self.check_storage()
        self.check_keys()

        self._db = None
        if usedb:
            self._db = connect(Config.get("database", "name", "impera"), host=Config.get("database", "host", "localhost"))
            LOGGER.info("Connected to mongodb database %s on %s", Config.get("database", "name", "impera"),
                        Config.get("database", "host", "localhost"))

        if code_loader:
            self._env = env.VirtualEnv(self._server_storage["env"])
            self._env.use_virtual_env()
            self._loader = CodeLoader(self._server_storage["code"])
        else:
            self._loader = None

        self._fact_expire = int(Config.get("server", "fact-expire", 3600))
        self._fact_renew = int(Config.get("server", "fact-renew", self._fact_expire / 3))

        self.add_end_point_name(self.node_name)

        self._db_lock = RLock()

        self.schedule(self.renew_expired_facts, self._fact_renew)
        self.schedule(self._purge_versions, int(Config.get("server", "purge-versions-interval", 3600)))
        self._purge_versions()

        self._requests = defaultdict(dict)
        self._recompiles = defaultdict(lambda: None)

        self._requires_agents = {}

        if Config.getboolean("server", "autostart-on-start", True):
            agents = data.Agent.objects()  # @UndefinedVariable

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

    def check_keys(self):
        """
            Check if the ssh key(s) credentials of this server are configured properly
        """
        # TODO

    def _purge_versions(self):
        """
            Purge versions from the database
        """
        envs = data.Environment.objects()  # @UndefinedVariable
        for env_item in envs:
            # get available versions
            n_versions = int(Config.get("server", "available-versions-to-keep", 2))
            versions = data.ConfigurationModel.objects(released=False, environment=env_item)  # @UndefinedVariable
            if len(versions) > n_versions:
                LOGGER.info("Removing %s available versions from environment %s", len(versions) - n_versions, env_item.id)
                versions = versions.order_by("-date")[n_versions:]
                for v in versions:
                    v.delete()

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

        code_dir = os.path.join(server_state_dir, "code")
        dir_map["code"] = code_dir
        if not os.path.exists(code_dir):
            os.mkdir(code_dir)

        env_dir = os.path.join(server_state_dir, "env")
        dir_map["env"] = env_dir
        if not os.path.exists(env_dir):
            os.mkdir(env_dir)

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

    def _request_parameter(self, param):
        """
            Request the value of a parameter from an agent
        """
        resource_id = param.resource_id
        tid = str(param.environment.id)
        env = param.environment

        if resource_id is not None and resource_id != "":
            # get the latest version
            versions = (data.ConfigurationModel.
                        objects(environment=env, released=True).order_by("-version").limit(1))  # @UndefinedVariable

            if len(versions) == 0:
                return 404, {"message": "The environment associated with this parameter does not have any releases."}

            version = versions[0]

            # get the associated resource
            resources = data.Resource.objects(environment=env, resource_id=resource_id)  # @UndefinedVariable

            if len(resources) == 0:
                return 404, {"message": "The parameter does not exist."}

            resource = resources[0]

            # get a resource version
            rvs = data.ResourceVersion.objects(environment=env, model=version, resource=resource)  # @UndefinedVariable

            if len(rvs) == 0:
                return 404, {"message": "The parameter does not exist."}

            self.queue_request(tid, resource.agent, {"method": "fact", "resource_id": resource_id, "environment": tid,
                                                     "name": param.name, "resource": rvs[0].to_dict()})

            return 503, {"message": "Agents queried for resource parameter."}

        return 404, {"message": "The parameter does not exist."}

    def renew_expired_facts(self):
        """
            Send out requests to renew expired facts
        """
        LOGGER.info("Renewing expired parameters")

        updated_before = datetime.datetime.now() - datetime.timedelta(0, (self._fact_expire - self._fact_renew))
        expired_params = data.Parameter.objects(updated__lt=updated_before)  # @UndefinedVariable

        for param in expired_params:
            LOGGER.debug("Requesting new parameter value for %s of resource %s in env %s", param.name, param.resource_id,
                         param.environment.id)
            self._request_parameter(param)

        unknown_parameters = data.UnknownParameter.objects()  # @UndefinedVariable
        for u in unknown_parameters:
            LOGGER.debug("Requesting value for unknown parameter %s of resource %s in env %s", u.name, u.resource_id,
                         u.environment.id)
            self._request_parameter(u)

    @protocol.handle(methods.ParameterMethod.get_param)
    def get_param(self, tid, id, resource_id=None):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        params = data.Parameter.objects(environment=env, name=id, resource_id=resource_id)  # @UndefinedVariable

        if len(params) == 0:
            if resource_id is not None and resource_id != "":
                # get the latest version
                versions = (data.ConfigurationModel.
                            objects(environment=env, released=True).order_by("-version").limit(1))  # @UndefinedVariable

                if len(versions) == 0:
                    return 404, {"message": "The parameter does not exist."}

                version = versions[0]

                # get the associated resource
                resources = data.Resource.objects(environment=env, resource_id=resource_id)  # @UndefinedVariable

                if len(resources) == 0:
                    return 404, {"message": "The parameter does not exist."}

                resource = resources[0]

                # get a resource version
                rvs = data.ResourceVersion.objects(environment=env, model=version, resource=resource)  # @UndefinedVariable

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
    def set_param(self, tid, id, source, value, resource_id, metadata):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        if resource_id is None:
            resource_id = ""
        params = data.Parameter.objects(environment=env, name=id, resource_id=resource_id)  # @UndefinedVariable

        if len(params) == 0:
            param = data.Parameter(environment=env, name=id, resource_id=resource_id, value=value, source=source,
                                   updated=datetime.datetime.now(), metadata=metadata)
            param.save()

        else:
            param = params[0]
            param.source = source
            param.value = value
            param.updated = datetime.datetime.now()
            param.metadate = metadata
            param.save()

        # check if the parameter is an unknown
        params = data.UnknownParameter.objects(environment=env, name=id, resource_id=resource_id,  # @UndefinedVariable
                                               resolved=False)
        if len(params) > 0:
            LOGGER.info("Received values for unknown parameters %s, triggering a recompile",
                        ", ".join([x.name for x in params]))
            for p in params:
                p.resolved = True
                p.save()

            self._async_recompile(tid, False, int(Config.get("server", "wait-after-param", 5)))

        return 200, {"parameter": param.to_dict()}

    @protocol.handle(methods.ParameterMethod.list_params)
    def list_param(self, tid, query):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        m_query = {"environment": env}
        for k, v in query.items():
            m_query["metadata__" + k] = v

        params = data.Parameter.objects(**m_query)  # @UndefinedVariable

        return_value = []
        for p in params:
            d = p.to_dict()
            return_value.append(d)

        return 200, {"parameters": return_value, "expire": self._fact_expire, "now": datetime.datetime.now().isoformat()}

    @protocol.handle(methods.FormMethod.put_form)
    def put_form(self, tid: uuid.UUID, id: str, form: dict):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        forms = data.Form.objects(environment=env, form_type=id)  # @UndefinedVariable

        fields = {k: v["type"] for k, v in form["attributes"].items()}
        defaults = {k: v["default"] for k, v in form["attributes"].items() if "default" in v}
        field_options = {k: v["options"] for k, v in form["attributes"].items() if "options" in v}

        if len(forms) == 0:
            f = data.Form(form_id=uuid.uuid4(), environment=env, form_type=id, fields=fields, defaults=defaults,
                          options=form["options"], field_options=field_options)
            f.save()

        else:
            f = forms[0]
            # update the definition
            f.fields = fields
            f.defaults = defaults
            f.options = form["options"]
            f.field_options = field_options

            f.save()

        return 200, {"form": {"id": f.form_id}}

    @protocol.handle(methods.FormMethod.get_form)
    def get_form(self, tid, id):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        forms = data.Form.objects(environment=env, form_type=id)  # @UndefinedVariable

        if len(forms) == 0:
            return 404

        return 200, {"form": forms[0].to_dict()}

    @protocol.handle(methods.FormMethod.list_forms)
    def list_forms(self, tid):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        forms = data.Form.objects(environment=env)  # @UndefinedVariable

        return 200, {"forms": [{"form_id": x.form_id, "form_type": x.form_type} for x in forms]}

    @protocol.handle(methods.FormRecords.list_records)
    def list_records(self, tid, form_type):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        try:
            form_type = data.Form.objects().get(environment=env, form_type=form_type)  # @UndefinedVariable
            records = data.FormRecord.objects(form=form_type)  # @UndefinedVariable

            return 200, {"records": [{"record_id": r.record_id, "changed": r.changed} for r in records]}

        except errors.DoesNotExist:
            return 404, {"message": "No form is defined with id %s" % form_type}

    @protocol.handle(methods.FormRecords.get_record)
    def get_record(self, tid, id):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        try:
            record = data.FormRecord.objects().get(record_id=id)  # @UndefinedVariable
            return 200, {"record": record.to_dict()}
        except errors.DoesNotExist:
            return 404, {"message": "The record with id %s does not exist" % id}

    @protocol.handle(methods.FormRecords.update_record)
    def update_record(self, tid, id, form):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        record = data.FormRecord.objects().get(record_id=id)  # @UndefinedVariable
        record.changed = datetime.datetime.now()

        form_fields = record.form.fields
        for k, _v in form_fields.items():
            if k in form:
                record.fields[k] = form[k]

        record.save()

        return 200, {"record": record.to_dict()}

    @protocol.handle(methods.FormRecords.create_record)
    def create_record(self, tid, form_type, form):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        form_obj = data.Form.objects().get(environment=env, form_type=form_type)  # @UndefinedVariable
        record_id = uuid.uuid4()
        record = data.FormRecord(record_id=record_id, environment=env, form=form_obj)
        record.changed = datetime.datetime.now()

        form_fields = record.form.fields
        for k, _v in form_fields.items():
            if k in form:
                record.fields[k] = form[k]

        record.save()

        return 200, {"record": record.to_dict()}

    @protocol.handle(methods.FormRecords.delete_record)
    def delete_record(self, tid, id):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        record = data.FormRecord.objects().get(record_id=id, environment=env)  # @UndefinedVariable
        record.delete()

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
    def heartbeat(self, endpoint_names, nodename, role, interval, environment):
        try:
            env = data.Environment.objects().get(id=environment)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        now = datetime.datetime.now()
        LOGGER.debug("Seen node %s" % nodename)
        try:
            node = data.Node.objects().get(hostname=nodename)  # @UndefinedVariable
            node.last_seen = now
            node.save()
        except errors.DoesNotExist:
            node = data.Node(hostname=nodename, last_seen=now)
            node.save()

        response = []
        for nh in endpoint_names:
            LOGGER.debug("Seen agent %s on %s", nh, nodename)
            agent = data.Agent.objects(name=nh, node=node, environment=env)  # @UndefinedVariable
            if len(agent) == 0:
                agent = data.Agent(name=nh, node=node, role=role, environment=env)

            else:
                agent = agent[0]

            agent.interval = interval
            agent.last_seen = now
            agent.save()

            # check if there is something we need to push to the client
            environment = str(environment)
            if environment in self._requests and nh in self._requests[environment]:
                response.append({"items": self._requests[environment][nh], "agent": nh})
                del self._requests[environment][nh]

        return 200, {"requests": response, "environment": environment}

    @protocol.handle(methods.NodeMethod.get_agent)
    def get_agent(self, id):
        try:
            node = data.Node.objects().get(hostname=id)  # @UndefinedVariable
            return 200, {"node": node.to_dict(),
                         "agents": [a.to_dict() for a in node.agents]
                         }
        except errors.DoesNotExist:
            return 404

    @protocol.handle(methods.NodeMethod.trigger_agent)
    def trigger_agent(self, tid, id):
        try:
            data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        self.queue_request(tid, id, {"method": "version", "version": -1, "environment": tid})

        return 200

    @protocol.handle(methods.NodeMethod.list_agents)
    def list_agent(self, environment):
        response = []
        for node in data.Node.objects():  # @UndefinedVariable
            agents = data.Agent.objects(node=node)  # @UndefinedVariable
            node_dict = node.to_dict()
            node_dict["agents"] = [a.to_dict() for a in agents
                                   if environment is None or str(a.environment.id) == environment]

            if len(node_dict["agents"]) > 0:
                response.append(node_dict)

        return 200, {"nodes": response, "servertime": datetime.datetime.now().isoformat()}

    @protocol.handle(methods.ResourceMethod.get_resource)
    def get_resource_state(self, tid, id, logs):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        resv = data.ResourceVersion.objects(environment=env, rid=id)  # @UndefinedVariable
        if len(resv) == 0:
            return 404, {"message": "The resource with the given id does not exist in the given environment"}

        ra = data.ResourceAction(resource_version=resv[0], action="pull", level="INFO", timestamp=datetime.datetime.now(),
                                 message="Individual resource version pulled by client")
        ra.save()

        action_list = []
        if bool(logs):
            actions = data.ResourceAction.objects(resource_version=resv[0])  # @UndefinedVariable
            for action in actions:
                action_list.append(action.to_dict())

        return 200, {"resource": resv[0].to_dict(), "logs": action_list}

    @protocol.handle(methods.ResourceMethod.get_resources_for_agent)
    def get_resources_for_agent(self, tid, agent, version):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        if version is None:
            versions = (data.ConfigurationModel.
                        objects(environment=env, released=True).order_by("-version").limit(1))  # @UndefinedVariable

            if len(versions) == 0:
                return 404

            cm = versions[0]

        else:
            try:
                cm = (data.ConfigurationModel.objects().get(environment=env, version=version))  # @UndefinedVariable
            except errors.DoesNotExist:
                return 404, {"message": "The given version does not exist"}

        deploy_model = []
        resources = data.ResourceVersion.objects(environment=env, model=cm)  # @UndefinedVariable
        for rv in resources:
            if rv.resource.agent == agent:
                deploy_model.append(rv.to_dict())
                ra = data.ResourceAction(resource_version=rv, action="pull", level="INFO", timestamp=datetime.datetime.now(),
                                         message="Resource version pulled by client for agent %s state" % agent)
                ra.save()

        return 200, {"environment": tid, "agent": agent, "version": cm.version, "resources": deploy_model}

    @protocol.handle(methods.CMVersionMethod.list_versions)
    def list_version(self, tid, start=None, limit=None):
        if (start is None and limit is not None) or (limit is None and start is not None):
            return 500, {"message": "Start and limit should always be set together."}

        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        models = data.ConfigurationModel.objects(environment=env).order_by("-version")  # @UndefinedVariable
        count = len(models)

        if start is not None:
            models = models[int(start):int(limit) + int(start)]

        d = {"versions": [m.to_dict() for m in models]}

        if start is not None:
            d["start"] = start
            d["limit"] = limit

        d["count"] = count

        return 200, d

    @protocol.handle(methods.CMVersionMethod.get_version)
    def get_version(self, tid, id, include_logs=None, log_filter=None, limit=None):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        try:
            version = data.ConfigurationModel.objects().get(version=id)  # @UndefinedVariable
            resources = data.ResourceVersion.objects(model=version)  # @UndefinedVariable

            d = {"model": version.to_dict()}

            d["resources"] = []
            for res in resources:
                res_dict = res.to_dict()

                if bool(include_logs):
                    if log_filter is not None:
                        actions = data.ResourceAction.objects(resource_version=res, action=log_filter)  # @UndefinedVariable
                    else:
                        actions = data.ResourceAction.objects(resource_version=res)  # @UndefinedVariable

                    actions = actions.order_by("-timestamp")

                    if limit is not None:
                        actions = actions[0:int(limit)]

                    res_dict["actions"] = [x.to_dict() for x in actions]

                d["resources"].append(res_dict)

            unp = data.UnknownParameter.objects(environment=env, version=version.version)  # @UndefinedVariable
            d["unknowns"] = [x.to_dict() for x in unp]

            return 200, d
        except errors.DoesNotExist:
            return 404, {"message": "The given configuration model does not exist yet."}

    @protocol.handle(methods.CMVersionMethod.delete_version)
    def delete_version(self, tid, id):
        try:
            data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        try:
            version = data.ConfigurationModel.objects().get(version=id)  # @UndefinedVariable
            version.delete()

            return 200
        except errors.DoesNotExist:
            return 404, {"message": "The given configuration model does not exist yet."}

    @protocol.handle(methods.CMVersionMethod.put_version)
    def put_version(self, tid, version, resources, unknowns, version_info):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        try:
            data.ConfigurationModel.objects().get(version=version)  # @UndefinedVariable
            return 500, {"message": "The given version is already defined. Versions should be unique."}
        except errors.DoesNotExist:
            pass

        cm = data.ConfigurationModel(environment=env, version=version, date=datetime.datetime.now(),
                                     resources_total=len(resources), version_info=version_info)
        cm.save()

        for res_dict in resources:
            resource_obj = Id.parse_id(res_dict['id'])
            resource_id = resource_obj.resource_str()

            resource = data.Resource.objects(environment=env, resource_id=resource_id)  # @UndefinedVariable
            if len(resource) > 0:
                if len(resource) == 1:
                    resource = resource[0]
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

            resource.save()

            rv = data.ResourceVersion(environment=env, rid=res_dict['id'], resource=resource, model=cm, attributes=attributes)
            rv.save()

            ra = data.ResourceAction(resource_version=rv, action="store", level="INFO", timestamp=datetime.datetime.now())
            ra.save()

        # search for deleted resources
        env_resources = data.Resource.objects(environment=tid)  # @UndefinedVariable
        for res in env_resources:
            if res.version_latest < version:
                rv = data.ResourceVersion.objects(environment=env, resource=res).order_by("-rid").limit(1)  # @UndefinedVariable
                if len(rv) > 0:
                    rv = rv[0]
                    if "purge_on_delete" in rv.attributes and rv.attributes["purge_on_delete"]:
                        LOGGER.warning("Purging %s, purged resource based on %s" % (res.resource_id, rv.rid))

                        res.version_latest = version
                        res.save()

                        attributes = rv.attributes.copy()
                        attributes["purged"] = "true"
                        rv = data.ResourceVersion(environment=env, rid="%s,v=%s" % (res.resource_id, version),
                                                  resource=res, model=cm, attributes=attributes)
                        rv.save()

                        ra = data.ResourceAction(resource_version=rv, action="store", level="INFO",
                                                 timestamp=datetime.datetime.now())
                        ra.save()

                        cm.resources_total += 1
                        cm.save()

        for uk in unknowns:
            if "resource" not in uk:
                uk["resource"] = ""

            if "metadata" not in uk:
                uk["metadata"] = {}

            up = data.UnknownParameter(resource_id=uk["resource"], name=uk["parameter"], source=uk["source"], environment=env,
                                       version=version, metadata=uk["metadata"])
            up.save()

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
    def release_version(self, tid, id, push):
        tid = str(tid)
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        models = data.ConfigurationModel.objects(environment=env, version=id)  # @UndefinedVariable
        if len(models) == 0:
            return 404, {"message": "The request version does not exist."}

        model = models[0]  # there can only be one per id/tid
        model.released = True
        model.result = "deploying"
        model.save()

        if push:
            # fetch all resource in this cm and create a list of distinct agents
            rvs = data.ResourceVersion.objects(model=model, environment=env)  # @UndefinedVariable
            agents = set()
            for rv in rvs:
                agents.add(rv.resource.agent)

            for agent in agents:
                self._ensure_agent(tid, agent)
                self.queue_request(tid, agent, {"method": "version", "version": id, "environment": tid})

        return 200, {"model": model.to_dict()}

    @protocol.handle(methods.DryRunMethod.dryrun_request)
    def dryrun_request(self, tid, id):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        models = data.ConfigurationModel.objects(environment=env, version=id)  # @UndefinedVariable
        if len(models) == 0:
            return 404, {"message": "The request version does not exist."}

        model = models[0]  # there can only be one per id/tid

        # Create a dryrun document
        dryrun_id = str(uuid.uuid4())
        dryrun = data.DryRun(id=dryrun_id, environment=env, model=model, date=datetime.datetime.now())

        # fetch all resource in this cm and create a list of distinct agents
        rvs = data.ResourceVersion.objects(model=model, environment=env)  # @UndefinedVariable
        dryrun.resource_total = len(rvs)
        dryrun.resource_todo = dryrun.resource_total

        agents = set()
        for rv in rvs:
            agents.add(rv.resource.agent)

        tid = str(tid)
        for agent in agents:
            self._ensure_agent(tid, agent)
            self.queue_request(tid, agent, {"method": "dryrun", "version": id, "environment": tid, "dryrun": dryrun_id})

        dryrun.save()

        return 200, {"dryrun": dryrun.to_dict()}

    @protocol.handle(methods.DryRunMethod.dryrun_list)
    def dryrun_list(self, tid, version=None):
        query_args = {}
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
            query_args["environment"] = env
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        if version is not None:
            models = data.ConfigurationModel.objects(environment=env, version=version)  # @UndefinedVariable
            if len(models) == 0:
                return 404, {"message": "The request version does not exist."}

            model = models[0]  # there can only be one per id/tid
            query_args["model"] = model

        dryruns = data.DryRun.objects(**query_args)  # @UndefinedVariable

        return 200, {"dryruns": [{"id": x.id, "version": x.model.version,
                                  "date": x.date.isoformat(), "total": x.resource_total,
                                  "todo": x.resource_todo
                                  } for x in dryruns]}

    @protocol.handle(methods.DryRunMethod.dryrun_report)
    def dryrun_report(self, tid, id):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        try:
            dryrun = data.DryRun.objects().get(id=id)  # @UndefinedVariable
            return 200, {"dryrun": dryrun.to_dict()}
        except errors.DoesNotExist:
            return 404, {"message": "The given dryrun does not exist!"}

    @protocol.handle(methods.DryRunMethod.dryrun_update)
    def dryrun_update(self, tid, id, resource, changes, log_msg=None):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        try:
            dryrun = data.DryRun.objects().get(id=id)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given dryrun does not exist!"}

        if resource in dryrun.resources:
            return 500, {"message": "A dryrun was already stored for this resource."}

        payload = {"changes": changes,
                   "log": log_msg,
                   "id_fields": Id.parse_id(resource).to_dict()
                   }

        dryrun.resources[resource.replace(".", "\uff0e").replace("$", "\uff04")] = json.dumps(payload)
        dryrun.resource_todo -= 1

        dryrun.save()

        return 200

    @protocol.handle(methods.CodeMethod.upload_code)
    def upload_code(self, tid, id, sources, requires):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The provided environment id does not match an existing environment."}

        code = data.Code.objects(environment=env, version=id)  # @UndefinedVariable
        if len(code) > 0:
            return 500, {"message": "Code for this version has already been uploaded."}

        code = data.Code(environment=env, version=id, sources=sources, requires=requires)
        code.save()

        return 200

    @protocol.handle(methods.CodeMethod.get_code)
    def get_code(self, tid, id):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The provided environment id does not match an existing environment."}

        code = data.Code.objects(environment=env, version=id)  # @UndefinedVariable
        if len(code) == 0:
            return 404, {"message": "The version of the code does not exist."}

        return 200, {"version": id, "environment": tid, "sources": code[0].sources, "requires": code[0].requires}

    @protocol.handle(methods.ResourceMethod.resource_updated)
    def resource_updated(self, tid, id, level, action, message, status, extra_data):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        resv = data.ResourceVersion.objects(environment=env, rid=id)  # @UndefinedVariable
        if len(resv) == 0:
            return 404, {"message": "The resource with the given id does not exist in the given environment"}

        resv = resv[0]
        resv.status = status
        resv.save()

        extra_data = json.dumps(extra_data)

        now = datetime.datetime.now()
        ra = data.ResourceAction(resource_version=resv, action=action, message=message, data=extra_data, level=level,
                                 timestamp=now, status=status)
        ra.save()

        model = resv.model
        rid = resv.rid.replace(".", "\uff0e").replace("$", "\uff04")
        if rid not in model.status:
            model.resources_done += 1

        model.status[rid] = status
        model.save()

        resv.resource.version_deployed = model.version
        resv.resource.last_deploy = now
        resv.resource.status = status
        resv.resource.save()

        if model.resources_done == model.resources_total:
            model.result = "success"
            for status in model.status:
                if status != "deployed":
                    model.result = "failed"

            model.deployed = True
            model.save()

        return 200

    # Project handlers
    @protocol.handle(methods.Project.create_project)
    def create_project(self, name):
        try:
            project = data.Project(name=name, id=uuid.uuid4())
            project.save()
        except errors.NotUniqueError:
            return 500, {"message": "A project with name %s already exists." % name}

        return 200, {"project": project.to_dict()}

    @protocol.handle(methods.Project.delete_project)
    def delete_project(self, id):
        try:
            # delete all environments first
            envs = data.Environment.objects(project=id)  # @UndefinedVariable
            for env_item in envs:
                self.delete_environment(env_item)

            # now delete the project itself
            project = data.Project.objects().get(id=id)  # @UndefinedVariable
            project.delete()
        except errors.DoesNotExist:
            return 404, {"message": "The project with given id does not exist."}

        return 200, {}

    @protocol.handle(methods.Project.modify_project)
    def modify_project(self, id, name):
        try:
            project = data.Project.objects().get(id=id)  # @UndefinedVariable
            project.name = name
            project.save()

            return 200, {"project": project.to_dict()}
        except errors.DoesNotExist:
            return 404, {"message": "The project with given id does not exist."}

        except errors.NotUniqueError:
            return 500, {"message": "A project with name %s already exists." % name}

    @protocol.handle(methods.Project.list_projects)
    def list_projects(self):
        return 200, {"projects": [x.to_dict() for x in data.Project.objects()]}  # @UndefinedVariable

    @protocol.handle(methods.Project.get_project)
    def get_project(self, id):
        try:
            project = data.Project.objects().get(id=id)  # @UndefinedVariable
            environments = data.Environment.objects(project=project.id)  # @UndefinedVariable

            project_dict = project.to_dict()
            project_dict["environments"] = [e.id for e in environments]

            return 200, {"project": project_dict}
        except (errors.DoesNotExist, ValueError):
            return 404, {"message": "The project with given id does not exist."}

        return 500

    # Environment handlers
    @protocol.handle(methods.Environment.create_environment)
    def create_environment(self, project_id, name, repository, branch):
        if (repository is None and branch is not None) or (repository is not None and branch is None):
            return 500, {"message": "Repository and branch should be set together."}

        # fetch the project first
        try:
            project = data.Project.objects().get(id=project_id)  # @UndefinedVariable
            env = data.Environment(id=uuid.uuid4(), name=name, project=project)
            env.repo_url = repository
            env.repo_branch = branch
            env.save()

            return 200, {"environment": env.to_dict()}
        except errors.DoesNotExist:
            return 500, {"message": "The project id for the environment does not exist."}

        except errors.NotUniqueError:
            return 500, {"message": "Project %s (id=%s) already has an environment with name %s" %
                         (project.name, project.id, name)}

    @protocol.handle(methods.Environment.modify_environment)
    def modify_environment(self, id, name, repository, branch):
        try:
            env = data.Environment.objects().get(id=id)  # @UndefinedVariable
            env.name = name
            if repository is not None:
                env.repo_url = repository

            if branch is not None:
                env.repo_branch = branch

            env.save()

            return 200, {"environment": env.to_dict()}

        except errors.DoesNotExist:
            return 404, {"message": "The environment id does not exist."}

    @protocol.handle(methods.Environment.get_environment)
    def get_environment(self, id, versions=None, resources=None):
        versions = 0 if versions is None else int(versions)
        resources = 0 if resources is None else int(resources)

        try:
            env = data.Environment.objects().get(id=id)  # @UndefinedVariable
            env_dict = env.to_dict()

            if versions > 0:
                v = data.ConfigurationModel.objects(environment=env).order_by("-date").limit(versions)  # @UndefinedVariable
                env_dict["versions"] = [x.to_dict() for x in v]

            if resources > 0:
                r = data.Resource.objects(environment=env)  # @UndefinedVariable
                env_dict["resources"] = [x.to_dict() for x in r]

            return 200, {"environment": env_dict}

        except errors.DoesNotExist:
            return 404, {"message": "The environment id does not exist."}

    @protocol.handle(methods.Environment.list_environments)
    def list_environments(self):
        return 200, {"environments": [x.to_dict() for x in data.Environment.objects()]}  # @UndefinedVariable

    @protocol.handle(methods.Environment.delete_environment)
    def delete_environment(self, id):
        try:
            # delete everything with a reference to this environment
            # delete the environment
            env = data.Environment.objects().get(id=id)  # @UndefinedVariable
            env.delete()
        except errors.DoesNotExist:
            return 404, {"message": "The environment with given id does not exist."}

        return 200

    @protocol.handle(methods.NotifyMethod.is_compiling)
    def is_compiling(self, id):
        if self._recompiles[id] is self:
            return 200

        return 204

    @protocol.handle(methods.NotifyMethod.notify_change)
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

            try:
                env = data.Environment.objects().get(id=environment_id)  # @UndefinedVariable
            except errors.DoesNotExist:
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
            stages.append(self._run_compile_stage("Recompiling configuration model",
                                                  impera_path + ["-vvv", "export", "-e", str(environment_id),
                                                                 "--server_address", "localhost", "--server_port",
                                                                 Config.get("server_rest_transport", "port", "8888")],
                                                  project_dir, env=os.environ.copy()))
        finally:
            end = datetime.datetime.now()
            self._recompiles[environment_id] = end
            data.Compile(environment=env, started=requested, completed=end, reports=stages).save()

    @protocol.handle(methods.CompileReport.get_reports)
    def get_reports(self, environment=None, start=None, end=None, limit=None):
        argscount = len([x for x in [start, end, limit] if x is not None])
        if argscount == 3:
            return 500, {"message": "Limit, start and end can not be set togheter"}

        queryparts = {}

        if environment is not None:
            try:
                env = data.Environment.objects().get(id=environment)  # @UndefinedVariable
                queryparts["environment"] = env
            except errors.DoesNotExist:
                return 404, {"message": "The given environment id does not exist!"}

        if start is not None:
            queryparts["started__gt"] = dateutil.parser.parse(start)

        if end is not None:
            queryparts["started__lt"] = dateutil.parser.parse(end)

        if limit is not None and end is not None:
            # no negative indices supprted
            models = data.Compile.objects(**queryparts).order_by("started")  # @UndefinedVariable
            models = list(models[:int(limit)])
            models.reverse()
        else:
            models = data.Compile.objects(**queryparts).order_by("-started")  # @UndefinedVariable
            if limit is not None:
                models = models[:int(limit)]

        d = {"reports": [m.to_dict() for m in models]}

        return 200, d

    @protocol.handle(methods.Snapshot.list_snapshots)
    def list_snapshots(self, tid):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        snapshots = data.Snapshot.objects(environment=env)  # @UndefinedVariable

        return 200, {"snapshots": [s.to_dict() for s in snapshots]}

    @protocol.handle(methods.Snapshot.get_snapshot)
    def get_snapshot(self, tid, id):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        try:
            snapshot = data.Snapshot.objects().get(environment=env, id=id)  # @UndefinedVariable
            snap_dict = snapshot.to_dict()

            resources = data.ResourceSnapshot.objects(snapshot=snapshot)  # @UndefinedVariable
            snap_dict["resources"] = [x.to_dict() for x in resources]

            return 200, {"snapshot": snap_dict}
        except errors.DoesNotExist:
            return 404, {"message": "The given snapshot id does not exist!"}

    @protocol.handle(methods.Snapshot.create_snapshot)
    def create_snapshot(self, tid, name):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        # get the latest deployed configuration model
        versions = (data.ConfigurationModel
                    .objects(environment=env, deployed=True).order_by("-version").limit(1))  # @UndefinedVariable

        if len(versions) == 0:
            return 500, {"message": "There is no deployed configuration model to create a snapshot."}

        version = versions[0]

        LOGGER.info("Creating a snapshot from version %s in environment %s", version.version, tid)

        # create the snapshot
        snapshot_id = uuid.uuid4()
        snapshot = data.Snapshot(id=snapshot_id, environment=env, model=version, started=datetime.datetime.now(), name=name)
        snapshot.save()

        # find resources with state
        resources_to_snapshot = defaultdict(list)
        resource_list = []
        resource_states = data.ResourceVersion.objects(environment=env, model=version)  # @UndefinedVariable
        for rs in resource_states:
            if rs.resource.holds_state and "state_id" in rs.attributes:
                agent = rs.resource.agent
                resources_to_snapshot[agent].append(rs.to_dict())
                resource_list.append(rs.resource.resource_id)
                r = data.ResourceSnapshot(environment=env, snapshot=snapshot, resource_id=rs.resource.resource_id,
                                          state_id=rs.attributes["state_id"])
                r.save()

        if len(resource_list) == 0:
            snapshot.finished = datetime.datetime.now()
            snapshot.total_size = 0
        else:
            snapshot.resources_todo = len(resource_list)

        snapshot.save()

        for agent, resources in resources_to_snapshot.items():
            self.queue_request(tid, agent, {"method": "snapshot", "environment": tid, "snapshot_id": snapshot_id,
                               "resources": resources})

        value = snapshot.to_dict()
        value["resources"] = resource_list
        return 200, {"snapshot": value}

    @protocol.handle(methods.Snapshot.update_snapshot)
    def update_snapshot(self, tid, id, resource_id, snapshot_data, start, stop, size, success, error, msg):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        try:
            snapshot = data.Snapshot.objects().get(id=id)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "Snapshot with id %s does not exist!" % id}

        res = data.ResourceSnapshot.objects().get(environment=env,  # @UndefinedVariable
                                                  snapshot=snapshot, resource_id=resource_id)

        res.content_hash = snapshot_data
        res.started = start
        res.finished = stop
        res.size = size
        res.success = success
        res.error = error
        res.msg = msg

        res.save()

        snapshot.resources_todo -= 1
        snapshot.total_size += size

        if snapshot.resources_todo == 0:
            snapshot.finished = datetime.datetime.now()

        snapshot.save()

        return 200

    @protocol.handle(methods.Snapshot.delete_snapshot)
    def delete_snapshot(self, tid, id):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        try:
            snapshot = data.Snapshot.objects().get(id=id)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "Snapshot with id %s does not exist!" % id}

        snapshot.delete()

        return 200

    @protocol.handle(methods.RestoreSnapshot.restore_snapshot)
    def restore_snapshot(self, tid, snapshot):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        try:
            snapshot = data.Snapshot.objects().get(id=snapshot)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "Snapshot with id %s does not exist!" % snapshot}

        # get all resources in the snapshot
        snap_resources = data.ResourceSnapshot.objects(snapshot=snapshot)  # @UndefinedVariable

        # get all resource that support state in the current environment
        env_versions = (data.ConfigurationModel
                        .objects(environment=env, deployed=True).order_by("-version").limit(1))  # @UndefinedVariable

        if len(env_versions) == 0:
            return 500, {"message": "There is no deployed configuration model in this environment."}
        else:
            env_version = env_versions[0]

        env_resources = data.ResourceVersion.objects(model=env_version)  # @UndefinedVariable
        env_states = {}
        for r in env_resources:
            if "state_id" in r.attributes:
                env_states[r.attributes["state_id"]] = r

        # create a restore object
        restore_id = uuid.uuid4()
        restore = data.SnapshotRestore(id=restore_id, snapshot=snapshot, environment=env, started=datetime.datetime.now())
        restore.save()

        # find matching resources
        restore_list = defaultdict(list)
        for r in snap_resources:
            if r.state_id in env_states:
                env_res = env_states[r.state_id]
                LOGGER.debug("Matching state_id %s to %s, scheduling restore" % (r.state_id, env_res.id))
                restore_list[env_res.resource.agent].append((r.to_dict(), env_res.to_dict()))

                rr = data.ResourceRestore(environment=env, restore=restore, state_id=r.state_id, resource_id=env_res.rid,
                                          started=datetime.datetime.now(), )
                rr.save()
                restore.resources_todo += 1

        restore.save()

        for agent, resources in restore_list.items():
            self.queue_request(tid, agent, {"method": "restore", "environment": tid, "restore_id": restore_id,
                                            "snapshot_id": snapshot.id, "resources": resources})

        return 200, restore.to_dict()

    @protocol.handle(methods.RestoreSnapshot.list_restores)
    def list_restores(self, tid):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        restores = data.SnapshotRestore.objects(environment=env)  # @UndefinedVariable
        return 200, [x.to_dict() for x in restores]

    @protocol.handle(methods.RestoreSnapshot.get_restore_status)
    def get_restore_status(self, tid, id):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        try:
            restore = data.SnapshotRestore.objects().get(id=id)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given restore id does not exist!"}

        restore_dict = restore.to_dict()
        resources = data.ResourceRestore.objects(restore=restore)  # @UndefinedVariable
        restore_dict["resources"] = [x.to_dict() for x in resources]
        return 200, {"restore": restore_dict}

    @protocol.handle(methods.RestoreSnapshot.update_restore)
    def update_restore(self, tid, id, resource_id, success, error, msg, start, stop):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        try:
            rr = data.ResourceRestore.objects().get(environment=env, restore=id, resource_id=resource_id)  # @UndefinedVariable
            rr.error = error
            rr.success = success
            rr.started = start
            rr.finished = stop
            rr.save()

            rr.restore.resource_todo -= 1
            if rr.restore.resource_todo == 0:
                rr.restore.finished = datetime.datetime.now()
                rr.restore.save()

        except errors.DoesNotExist:
            return 404, {"message": "Resource restore not found."}

        return 200

    @protocol.handle(methods.RestoreSnapshot.delete_restore)
    def delete_restore(self, tid, id):
        try:
            env = data.Environment.objects().get(id=tid)  # @UndefinedVariable
        except errors.DoesNotExist:
            return 404, {"message": "The given environment id does not exist!"}

        try:
            restore = data.SnapshotRestore.objects().get(environment=env, id=id)  # @UndefinedVariable
            restore.delete()
            
            return 200
        except errors.DoesNotExist:
            return 404, {"message": "The given restore id does not exist!"}
