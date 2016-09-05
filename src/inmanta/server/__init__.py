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

import base64
from collections import defaultdict
import datetime
import difflib
import glob
import json
import logging
import os
import re
import subprocess
import sys
import threading
import time
import uuid

import dateutil
from motorengine import connect, errors, DESCENDING
from motorengine.connection import disconnect
from tornado import gen
from tornado import locks
from tornado import process
from inmanta import data
from inmanta import methods
from inmanta import protocol
from inmanta.ast import type
from inmanta.config import Config
from inmanta.resources import Id, HostNotFoundException
from inmanta.server.agentmanager import AgentManager

LOGGER = logging.getLogger(__name__)
LOCK = locks.Lock()


class Server(protocol.ServerEndpoint):
    """
        The central Inmanta server that communicates with clients and agents and persists configuration
        information

        :param usedb Use a database to store data. If not, only facts are persisted in a yaml file.
    """

    def __init__(self, io_loop, database_host=None, database_port=None):
        super().__init__("server", io_loop=io_loop)
        LOGGER.info("Starting server endpoint")
        self._server_storage = self.check_storage()

        self._db = None
        if database_host is None:
            database_host = Config.get("database", "host", "localhost")

        if database_port is None:
            database_port = Config.get("database", "port", 27017)

        self._db = connect(Config.get("database", "name", "inmanta"), host=database_host, port=database_port)
        LOGGER.info("Connected to mongodb database %s on %s:%d", Config.get("database", "name", "inmanta"),
                    database_host, database_port)

        self._fact_expire = int(Config.get("server", "fact-expire", 3600))
        self._fact_renew = int(Config.get("server", "fact-renew", self._fact_expire / 3))
        self._fact_resource_block = int(Config.get("server", "fact-resource_block", 60))
        self._fact_resource_block_set = {}

        self.add_end_point_name(self.node_name)

        self.schedule(self.renew_expired_facts, self._fact_renew)
        self.schedule(self._purge_versions, int(Config.get("server", "purge-versions-interval", 3600)))

        self._io_loop.add_callback(self._purge_versions)

        self._recompiles = defaultdict(lambda: None)

        self.agentmanager = AgentManager(self)

        self.setup_dashboard()

    def new_session(self, sid, tid, endpoint_names, nodename):
        session = protocol.ServerEndpoint.new_session(self, sid, tid, endpoint_names, nodename)
        self.agentmanager.new_session(session,  tid, endpoint_names, nodename)
        return session

    def expire(self, session):
        self.agentmanager.expire(session)
        protocol.ServerEndpoint.expire(self, session)

    def seen(self, session):
        self.agentmanager.seen(session)
        protocol.ServerEndpoint.seen(self, session)

    def get_agent_client(self, tid, endpoint):
        return self.agentmanager.get_agent_client(tid, endpoint)

    def setup_dashboard(self):
        """
            If configured, set up tornado to serve the dashboard
        """
        if not Config.getboolean("dashboard", "enabled", False):
            return

        dashboard_path = Config.get("dashboard", "path")
        if dashboard_path is None:
            LOGGER.warning("The dashboard is enabled in the configuration but its path is not configured.")
            return

        self._transport_instance.add_static_handler("dashboard", dashboard_path, start=True)

    def stop(self):
        disconnect()
        super().stop()

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
                LOGGER.info("Removing %s available versions from environment %s", len(versions) - n_versions, env_item.uuid)
                version_dict = {x.version: x for x in versions}
                delete_list = sorted(version_dict.keys())
                delete_list = delete_list[:-n_versions]

                for v in delete_list:
                    yield version_dict[v].delete_cascade()

    def check_storage(self):
        """
            Check if the server storage is configured and ready to use.
        """
        if "config" not in Config.get() or "state-dir" not in Config.get()["config"]:
            raise Exception("The Inmanta server requires a state directory to be configured")

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

        environments_dir = os.path.join(server_state_dir, "environments")
        dir_map["environments"] = environments_dir
        if not os.path.exists(environments_dir):
            os.mkdir(environments_dir)

        env_agent_dir = os.path.join(server_state_dir, "agents")
        dir_map["agents"] = env_agent_dir
        if not os.path.exists(env_agent_dir):
            os.mkdir(env_agent_dir)

        log_dir = Config.get("config", "log-dir", "/var/log/inmanta")
        if not os.path.isdir(log_dir):
            os.mkdir(log_dir)
        dir_map["logs"] = log_dir

        return dir_map

    @gen.coroutine
    def renew_expired_facts(self):
        """
            Send out requests to renew expired facts
        """
        LOGGER.info("Renewing expired parameters")

        updated_before = datetime.datetime.now() - datetime.timedelta(0, (self._fact_expire - self._fact_renew))
        expired_params = yield data.Parameter.objects.filter(updated__lt=updated_before).find_all()  # @UndefinedVariable

        LOGGER.debug("Renewing %d expired parameters" % len(expired_params))

        for param in expired_params:
            yield param.load_references()
            if param.environment is None:
                LOGGER.warning("Found parameter without environment (%s for resource %s). Deleting it.",
                               param.name, param.resource_id)
                yield param.delete()
            else:
                LOGGER.debug("Requesting new parameter value for %s of resource %s in env %s", param.name, param.resource_id,
                             param.environment.uuid)
                yield self.agentmanager._request_parameter(param.environment, param.resource_id)

        unknown_parameters = yield data.UnknownParameter.objects.filter(resolved=False).find_all()  # @UndefinedVariable
        for u in unknown_parameters:
            yield u.load_references()
            if u.environment is None:
                LOGGER.warning("Found unknown parameter without environment (%s for resource %s). Deleting it.",
                               u.name, u.resource_id)
                yield u.delete()
            else:
                LOGGER.debug("Requesting value for unknown parameter %s of resource %s in env %s", u.name, u.resource_id,
                             u.environment.uuid)
                self.agentmanager._request_parameter(u.environment, u.resource_id)

        LOGGER.info("Done renewing expired parameters")

    @protocol.handle(methods.ParameterMethod.get_param)
    @gen.coroutine
    def get_param(self, tid, id, resource_id=None):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        params = yield data.Parameter.objects.filter(environment=env,  # @UndefinedVariable
                                                     name=id, resource_id=resource_id).find_all()  # @UndefinedVariable

        if len(params) == 0:
            out = yield self.agentmanager._request_parameter(env, resource_id)
            return out

        param = params[0]
        # check if it was expired
        now = datetime.datetime.now()
        if (param.updated + datetime.timedelta(0, self._fact_expire)) > now:
            return 200, {"parameter": params[0].to_dict()}

        LOGGER.info("Parameter %s of resource %s expired.", id, resource_id)
        out = yield self.agentmanager._request_parameter(env, resource_id)
        return out

    @gen.coroutine
    def _update_param(self, env, name, value, source, resource_id, metadata):
        """
            Update or set a parameter. This method returns true if this update resolves an unknown
        """
        LOGGER.debug("Updating/setting parameter %s in env %s (for resource %s)", name, env.uuid, resource_id)
        if not isinstance(value, str):
            value = str(value)

        if value is None or value == "":
            value = " "

        if resource_id is None:
            resource_id = ""

        params = yield data.Parameter.objects.filter(environment=env,  # @UndefinedVariable
                                                     name=name, resource_id=resource_id).find_all()  # @UndefinedVariable

        if len(params) == 0:
            param = data.Parameter(environment=env, name=name, resource_id=resource_id, value=value, source=source,
                                   updated=datetime.datetime.now(), metadata=metadata)

        else:
            param = params[0]
            param.source = source
            param.value = value
            param.updated = datetime.datetime.now()
            param.metadata = metadata

        yield param.save()

        # check if the parameter is an unknown
        params = yield data.UnknownParameter.objects.filter(environment=env, name=name,  # @UndefinedVariable
                                                            resource_id=resource_id,
                                                            resolved=False).find_all()  # @UndefinedVariable
        if len(params) > 0:
            LOGGER.info("Received values for unknown parameters %s, triggering a recompile",
                        ", ".join([x.name for x in params]))
            for p in params:
                p.resolved = True
                yield p.save()

            return True

        return False

    @protocol.handle(methods.ParameterMethod.set_param)
    @gen.coroutine
    def set_param(self, tid, id, source, value, resource_id, metadata):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        result = yield self._update_param(env, id, value, source, resource_id, metadata)
        if result:
            self._async_recompile(tid, False, int(Config.get("server", "wait-after-param", 5)))

        if resource_id is None:
            resource_id = ""

        params = yield data.Parameter.objects.filter(environment=env,  # @UndefinedVariable
                                                     name=id, resource_id=resource_id).find_all()  # @UndefinedVariable

        return 200, {"parameter": params[0].to_dict()}

    @protocol.handle(methods.ParametersMethod.set_parameters)
    @gen.coroutine
    def set_parameters(self, tid, parameters):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        recompile = False
        for param in parameters:
            name = param["id"]
            source = param["source"]
            value = param["value"] if "value" in param else None
            resource_id = param["resource_id"] if "resource_id" in param else None
            metadata = param["metadata"] if "metadata" in param else None

            result = yield self._update_param(env, name, value, source, resource_id, metadata)
            if result:
                recompile = True

        if recompile:
            self._async_recompile(tid, False, int(Config.get("server", "wait-after-param", 5)))

        return 200

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

        form_doc = yield data.Form.get_form(environment=env, form_type=id)
        fields = {k: v["type"] for k, v in form["attributes"].items()}
        defaults = {k: v["default"] for k, v in form["attributes"].items() if "default" in v}
        field_options = {k: v["options"] for k, v in form["attributes"].items() if "options" in v}

        if form_doc is None:
            form_doc = data.Form(uuid=uuid.uuid4(), environment=env, form_type=id, fields=fields, defaults=defaults,
                                 options=form["options"], field_options=field_options)

        else:
            # update the definition
            form_doc.fields = fields
            form_doc.defaults = defaults
            form_doc.options = form["options"]
            form_doc.field_options = field_options

        yield form_doc.save()

        return 200, {"form": {"id": form_doc.uuid}}

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

        return 200, {"forms": [{"form_id": x.uuid, "form_type": x.form_type} for x in forms]}

    @protocol.handle(methods.FormRecords.list_records)
    @gen.coroutine
    def list_records(self, tid, form_type, include_record):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        form_type = yield data.Form.get_form(environment=env, form_type=form_type)
        if form_type is None:
            return 404, {"message": "No form is defined with id %s" % form_type}

        records = yield data.FormRecord.objects.filter(form=form_type).find_all()  # @UndefinedVariable

        if not include_record:
            return 200, {"records": [{"record_id": r.uuid, "changed": r.changed} for r in records]}

        else:
            record_dict = []
            for record in records:
                data_dict = yield record.to_dict()
                record_dict.append(data_dict)

            return 200, {"records": record_dict}

    @protocol.handle(methods.FormRecords.get_record)
    @gen.coroutine
    def get_record(self, tid, id):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        record = yield data.FormRecord.get_uuid(id)
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
                value = form[k]
                field_type = form_fields[k]
                if field_type in type.TYPES:
                    type_obj = type.TYPES[field_type]
                    record.fields[k] = type_obj.cast(value)
                else:
                    LOGGER.warning("Field %s in form %s has an invalid type." % (k, id))

        yield record.save()

        new_record = yield data.FormRecord.get_uuid(id)
        record_dict = yield new_record.to_dict()

        self._async_recompile(tid, False, int(Config.get("server", "wait-after-param", 5)))
        return 200, {"record": record_dict}

    @protocol.handle(methods.FormRecords.create_record)
    @gen.coroutine
    def create_record(self, tid, form_type, form):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        form_obj = yield data.Form.get_form(environment=env, form_type=form_type)

        if form_obj is None:
            return 404, {"message": "The form %s does not exist in env %" % (tid, form_type)}

        record_id = uuid.uuid4()
        record = data.FormRecord(uuid=record_id, environment=env, form=form_obj, fields={})
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

        # need to query this again, to_dict with load_references only works on retrieved document and not on newly created
        record = yield data.FormRecord.get_uuid(record_id)
        record_dict = yield record.to_dict()

        return 200, {"record": record_dict}

    @protocol.handle(methods.FormRecords.delete_record)
    @gen.coroutine
    def delete_record(self, tid, id):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        record = yield data.FormRecord.get_uuid(id)
        yield record.delete()

        return 200

    @protocol.handle(methods.FileMethod.upload_file)
    @gen.coroutine
    def upload_file(self, id, content):
        file_name = os.path.join(self._server_storage["files"], id)

        if os.path.exists(file_name):
            return 500, {"message": "A file with this id already exists."}

        with open(file_name, "wb+") as fd:
            fd.write(base64.b64decode(content))

        return 200

    @protocol.handle(methods.FileMethod.stat_file)
    @gen.coroutine
    def stat_file(self, id):
        file_name = os.path.join(self._server_storage["files"], id)

        if os.path.exists(file_name):
            return 200
        else:
            return 404

    @protocol.handle(methods.FileMethod.get_file)
    @gen.coroutine
    def get_file(self, id):
        file_name = os.path.join(self._server_storage["files"], id)

        if not os.path.exists(file_name):
            return 404

        else:
            with open(file_name, "rb") as fd:
                return 200, {"content": base64.b64encode(fd.read()).decode("ascii")}

    @protocol.handle(methods.FileMethod.stat_files)
    @gen.coroutine
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
    @gen.coroutine
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

    @protocol.handle(methods.NodeMethod.get_agent)
    @gen.coroutine
    def get_agent(self, id):
        yield self.agentmanager.get_agent_info(id)

    @protocol.handle(methods.NodeMethod.trigger_agent)
    @gen.coroutine
    def trigger_agent(self, tid, id):
        yield self.agentmanager.trigger_agent(tid, id)

    @protocol.handle(methods.NodeMethod.list_agents)
    @gen.coroutine
    def list_agent(self, environment):
        yield self.agentmanager.list_agent(environment)

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
    @gen.coroutine
    def get_resources_for_agent(self, tid, agent, version):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        if version is None:
            versions = yield (data.ConfigurationModel.objects.filter(environment=env, released=True).  # @UndefinedVariable
                              order_by("version", direction=DESCENDING).limit(1).find_all())  # @UndefinedVariable

            if len(versions) == 0:
                return 404

            cm = versions[0]

        else:
            versions = yield (data.ConfigurationModel.objects.filter(environment=env, version=version).  # @UndefinedVariable
                              find_all())  # @UndefinedVariable
            if len(versions) == 0:
                return 404, {"message": "The given version does not exist"}

            cm = versions[0]

        deploy_model = []
        resources = yield data.ResourceVersion.objects.filter(environment=env, model=cm).find_all()  # @UndefinedVariable

        for rv in resources:
            yield rv.load_references()
            if rv.resource.agent == agent:
                deploy_model.append(rv.to_dict())
                ra = data.ResourceAction(resource_version=rv, action="pull", level="INFO", timestamp=datetime.datetime.now(),
                                         message="Resource version pulled by client for agent %s state" % agent)
                yield ra.save()

        return 200, {"environment": tid, "agent": agent, "version": cm.version, "resources": deploy_model}

    @protocol.handle(methods.CMVersionMethod.list_versions)
    @gen.coroutine
    def list_version(self, tid, start=None, limit=None):
        if (start is None and limit is not None) or (limit is None and start is not None):
            return 500, {"message": "Start and limit should always be set together."}

        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        models = yield (data.ConfigurationModel.objects.filter(environment=env).  # @UndefinedVariable
                        order_by("version", direction=DESCENDING).find_all())  # @UndefinedVariable
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

        resources = yield data.ResourceVersion.objects.filter(model=version).find_all()  # @UndefinedVariable

        version_dict = yield version.to_dict()
        d = {"model": version_dict}

        d["resources"] = []
        for res in resources:
            res_dict = res.to_dict()

            if bool(include_logs):
                if log_filter is not None:
                    actions = yield (data.ResourceAction.objects.filter(resource_version=res,  # @UndefinedVariable
                                                                        action=log_filter)
                                     .order_by("timestamp", direction=DESCENDING).find_all())  # @UndefinedVariable
                else:
                    actions = yield (data.ResourceAction.objects.filter(resource_version=res)  # @UndefinedVariable
                                     .order_by("timestamp", direction=DESCENDING).find_all())  # @UndefinedVariable

                if limit is not None:
                    actions = actions[0:int(limit)]

                res_dict["actions"] = [x.to_dict() for x in actions]

            d["resources"].append(res_dict)

        unp = yield (data.UnknownParameter.objects.  # @UndefinedVariable
                     filter(environment=env, version=version.version).find_all())  # @UndefinedVariable
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

        cm = yield data.ConfigurationModel.get_version(env, version)
        if cm is not None:
            return 500, {"message": "The given version is already defined. Versions should be unique."}

        cm = data.ConfigurationModel(environment=env, version=version, date=datetime.datetime.now(),
                                     resources_total=len(resources), version_info=version_info)
        yield cm.save()

        # Force motorengine to create the indexes required to speed up this operation
        yield data.ResourceVersion.objects.ensure_index()  # @UndefinedVariable
        yield data.Resource.objects.ensure_index()  # @UndefinedVariable
        yield data.ResourceAction.objects.ensure_index()  # @UndefinedVariable
        yield data.UnknownParameter.objects.ensure_index()  # @UndefinedVariable

        all_resources = yield data.Resource.objects.filter(environment=env).find_all()  # @UndefinedVariable
        resources_dict = {x.resource_id: x for x in all_resources}

        rv_list = []
        ra_list = []
        for res_dict in resources:
            resource_obj = Id.parse_id(res_dict['id'])
            resource_id = resource_obj.resource_str()

            if resource_id in resources_dict:
                res_obj = resources_dict[resource_id]
                res_obj.version_latest = version

            else:
                res_obj = data.Resource(environment=env, resource_id=resource_id,
                                        resource_type=resource_obj.get_entity_type(),
                                        agent=resource_obj.get_agent_name(),
                                        attribute_name=resource_obj.get_attribute(),
                                        attribute_value=resource_obj.get_attribute_value(), version_latest=version)

            if "state_id" in res_dict:
                if res_dict["state_id"] == "":
                    res_dict["state_id"] = resource_id
                if not res_obj.holds_state:
                    res_obj.holds_state = True

            yield res_obj.save()

            attributes = {}
            for field, value in res_dict.items():
                if field != "id":
                    attributes[field] = value

            rv = data.ResourceVersion(environment=env, rid=res_dict['id'], resource=res_obj, model=cm, attributes=attributes)
            rv_list.append(rv)

            ra = data.ResourceAction(resource_version=rv, action="store", level="INFO", timestamp=datetime.datetime.now())
            ra_list.append(ra)

        if len(rv_list) > 0:
            yield data.ResourceVersion.objects.bulk_insert(rv_list)  # @UndefinedVariable

        if len(ra_list) > 0:
            yield data.ResourceAction.objects.bulk_insert(ra_list)  # @UndefinedVariable

        # search for deleted resources
        for res in all_resources:
            if res.version_latest < version:
                rv = yield (data.ResourceVersion.objects.filter(environment=env, resource=res).  # @UndefinedVariable
                            order_by("rid", direction=DESCENDING).limit(1).find_all())  # @UndefinedVariable
                if len(rv) > 0:
                    rv = rv[0]
                    if "purge_on_delete" in rv.attributes and rv.attributes["purge_on_delete"]:
                        LOGGER.warning("Purging %s, purged resource based on %s" % (res.resource_id, rv.rid))

                        res.version_latest = version
                        yield res.save()

                        attributes = rv.attributes.copy()
                        attributes["purged"] = "true"
                        # TODO: handle delete relations
                        attributes["requires"] = []
                        rv = data.ResourceVersion(environment=env, rid="%s,v=%s" % (res.resource_id, version),
                                                  resource=res, model=cm, attributes=attributes)
                        yield rv.save()

                        ra = data.ResourceAction(resource_version=rv, action="store", level="INFO",
                                                 timestamp=datetime.datetime.now())
                        yield ra.save()

                        cm.resources_total += 1
                        yield cm.save()

        for uk in unknowns:
            if "resource" not in uk:
                uk["resource"] = ""

            if "metadata" not in uk:
                uk["metadata"] = {}

            up = data.UnknownParameter(resource_id=uk["resource"], name=uk["parameter"], source=uk["source"], environment=env,
                                       version=version, metadata=uk["metadata"])
            yield up.save()

        LOGGER.debug("Successfully stored version %d" % version)

        return 200

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
                yield rv.load_references()
                yield rv.resource.load_references()
                agents.add(rv.resource.agent)

            for agent in agents:
                yield self.agentmanager._ensure_agent(str(tid), agent)
                client = self.get_agent_client(tid, agent)
                if client is not None:
                    future = client.trigger_agent(tid, agent)
                    self.add_future(future)
                else:
                    LOGGER.warning("Agent %s from model %s in env %s is not available for a deploy", agent, id, tid)

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
        dryrun = data.DryRun(uuid=dryrun_id, environment=env, model=model, date=datetime.datetime.now(), resources={})

        # fetch all resource in this cm and create a list of distinct agents
        rvs = yield data.ResourceVersion.objects.filter(model=model, environment=env).find_all()  # @UndefinedVariable
        dryrun.resource_total = len(rvs)
        dryrun.resource_todo = dryrun.resource_total

        agents = set()
        for rv in rvs:
            yield rv.load_references()
            yield rv.resource.load_references()
            agents.add(rv.resource.agent)

        tid = str(tid)
        for agent in agents:
            yield self.agentmanager._ensure_agent(str(tid), agent)
            client = self.get_agent_client(tid, agent)
            if client is not None:
                future = client.do_dryrun(tid, dryrun_id, agent, id)
                self.add_future(future)
            else:
                LOGGER.warning("Agent %s from model %s in env %s is not available for a dryrun", agent, id, tid)

        yield dryrun.save()

        dryrun = yield data.DryRun.get_uuid(dryrun_id)
        dryrun_dict = yield dryrun.to_dict()
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

        for x in dryruns:
            yield x.load_references()

        return 200, {"dryruns": [{"id": x.uuid, "version": x.model.version,
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

        dryrun.resources[resource] = payload
        dryrun.resource_todo -= 1
        yield dryrun.save()

        return 200

    @protocol.handle(methods.CodeMethod.upload_code)
    @gen.coroutine
    def upload_code(self, tid, id, resource, sources):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        code = yield data.Code.get_version(environment=env, version=id, resource=resource)  # @UndefinedVariable
        if code is not None:
            return 500, {"message": "Code for this version has already been uploaded."}

        code = data.Code(environment=env, version=id, resource=resource, sources=sources)
        yield code.save()

        return 200

    @protocol.handle(methods.CodeMethod.get_code)
    @gen.coroutine
    def get_code(self, tid, id, resource):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        code = yield data.Code.get_version(environment=env, version=id, resource=resource)  # @UndefinedVariable
        if code is None:
            return 404, {"message": "The version of the code does not exist."}

        return 200, {"version": id, "environment": tid, "resource": resource, "sources": code.sources}

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
        yield ra.save()

        with (yield LOCK.acquire()):
            yield resv.load_references()
            model = resv.model
            rid = resv.rid
            if rid not in model.status:
                model.resources_done += 1

            model.status[rid] = status
            yield model.save()

        resv.resource.version_deployed = model.version
        resv.resource.last_deploy = now
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
            future_2 = data.Environment.objects.filter(project_id=id).find_all()  # @UndefinedVariable

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

        # check if an environment with this name is already defined in this project
        envs = yield data.Environment.objects.filter(project_id=project_id, name=name).find_all()  # @UndefinedVariable
        if len(envs) > 0:
            return 500, {"message": "Project %s (id=%s) already has an environment with name %s" %
                         (project.name, project.uuid, name)}

        env = data.Environment(uuid=uuid.uuid4(), name=name, project_id=project_id)
        env.repo_url = repository
        env.repo_branch = branch
        yield env.save()

        env_dict = env.to_dict()
        return 200, {"environment": env_dict}

    @protocol.handle(methods.Environment.modify_environment)
    @gen.coroutine
    def modify_environment(self, id, name, repository, branch):
        env = yield data.Environment.get_uuid(id)
        if env is None:
            return 404, {"message": "The environment id does not exist."}

        yield env.load_references()

        # check if an environment with this name is already defined in this project
        envs = yield data.Environment.objects.filter(project_id=env.project_id, name=name).find_all()  # @UndefinedVariable
        if len(envs) > 0:
            return 500, {"message": "Project with id=%s already has an environment with name %s" % (env.project_id, name)}

        env.name = name
        if repository is not None:
            env.repo_url = repository

        if branch is not None:
            env.repo_branch = branch

        yield env.save()
        return 200, {"environment": env.to_dict()}

    @protocol.handle(methods.Environment.get_environment)
    @gen.coroutine
    def get_environment(self, id, versions=None, resources=None):
        versions = 0 if versions is None else int(versions)
        resources = 0 if resources is None else int(resources)

        env = yield data.Environment.get_uuid(id)

        if env is None:
            return 404, {"message": "The environment id does not exist."}

        env_dict = env.to_dict()

        if versions > 0:
            v = yield (data.ConfigurationModel.objects.filter(environment=env).  # @UndefinedVariable
                       order_by("date", direction=DESCENDING).limit(versions).find_all())  # @UndefinedVariable
            env_dict["versions"] = []
            for model in v:
                model_dict = yield model.to_dict()
                env_dict["versions"].append(model_dict)

        if resources > 0:
            resource_list = yield data.Resource.objects.filter(environment=env).find_all()  # @UndefinedVariable
            env_dict["resources"] = [x.to_dict() for x in resource_list]

        return 200, {"environment": env_dict}

    @protocol.handle(methods.Environment.list_environments)
    @gen.coroutine
    def list_environments(self):
        environments = yield data.Environment.objects.find_all()  # @UndefinedVariable
        dicts = []
        for env in environments:
            env_dict = env.to_dict()
            dicts.append(env_dict)

        return 200, {"environments": dicts}  # @UndefinedVariable

    @protocol.handle(methods.Environment.delete_environment)
    @gen.coroutine
    def delete_environment(self, id):
        env = yield data.Environment.get_uuid(id)
        if env is None:
            return 404, {"message": "The environment with given id does not exist."}

        agents = yield data.Agent.objects.filter(environment=env).find_all()  # @UndefinedVariable
        for agent in agents:
            yield agent.delete()

        compiles = yield data.Compile.objects.filter(environment=env).find_all()  # @UndefinedVariable
        for compile in compiles:
            yield compile.delete()

        yield env.delete_cascade()

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
            self._io_loop.add_callback(self._recompile_environment, environment_id, update_repo, wait)
        else:
            LOGGER.info("Not recompiling, last recompile less than %s ago (last was at %s)", wait_time, last_recompile)

    def _fork_inmanta(self, args, cwd=None):
        """
            For an inmanta process from the same code base as the current code
        """
        inmanta_path = [sys.executable, os.path.abspath(sys.argv[0])]
        proc = subprocess.Popen(inmanta_path + args, cwd=cwd, env=os.environ.copy(),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return proc

    @gen.coroutine
    def _run_compile_stage(self, name, cmd, cwd, **kwargs):
        start = datetime.datetime.now()

        sub_process = process.Subprocess(cmd, stdout=process.Subprocess.STREAM, stderr=process.Subprocess.STREAM,
                                         cwd=cwd, **kwargs)

        log_out, log_err, returncode = yield [gen.Task(sub_process.stdout.read_until_close),
                                              gen.Task(sub_process.stderr.read_until_close),
                                              sub_process.wait_for_exit(raise_error=False)]
        returncode

        stop = datetime.datetime.now()
        return data.Report(started=start, completed=stop, name=name, command=" ".join(cmd),
                           errstream=log_err.decode(), outstream=log_out.decode(), returncode=returncode)

    @gen.coroutine
    def _recompile_environment(self, environment_id, update_repo=False, wait=0):
        """
            Recompile an environment
        """
        if wait > 0:
            yield gen.sleep(wait)

        env = yield data.Environment.get_uuid(environment_id)
        if env is None:
            LOGGER.error("Environment %s does not exist.", environment_id)
            return

        requested = datetime.datetime.now()
        stages = []

        try:
            inmanta_path = [sys.executable, os.path.abspath(sys.argv[0])]
            project_dir = os.path.join(self._server_storage["environments"], str(environment_id))

            if not os.path.exists(project_dir):
                LOGGER.info("Creating project directory for environment %s at %s", environment_id, project_dir)
                os.mkdir(project_dir)

            # checkout repo
            if not os.path.exists(os.path.join(project_dir, ".git")):
                LOGGER.info("Cloning repository into environment directory %s", project_dir)
                result = yield self._run_compile_stage("Cloning repository", ["git", "clone", env.repo_url, "."], project_dir)
                stages.append(result)
                if result.returncode > 0:
                    return

            elif update_repo:
                LOGGER.info("Fetching changes from repo %s", env.repo_url)
                result = yield self._run_compile_stage("Fetching changes", ["git", "fetch", env.repo_url], project_dir)
                stages.append(result)

            # verify if branch is correct
            proc = subprocess.Popen(["git", "branch"], cwd=project_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, _ = proc.communicate()

            o = re.search("\* ([^\s]+)$", out.decode(), re.MULTILINE)
            if o is not None and env.repo_branch != o.group(1):
                LOGGER.info("Repository is at %s branch, switching to %s", o.group(1), env.repo_branch)
                result = yield self._run_compile_stage("switching branch", ["git", "checkout", env.repo_branch], project_dir)
                stages.append(result)

            if update_repo:
                result = yield self._run_compile_stage("Pulling updates", ["git", "pull"], project_dir)
                stages.append(result)
                LOGGER.info("Installing and updating modules")
                result = yield self._run_compile_stage("Installing modules", inmanta_path + ["modules", "install"], project_dir,
                                                       env=os.environ.copy())
                stages.append(result)
                result = yield self._run_compile_stage("Updating modules", inmanta_path + ["modules", "update"], project_dir,
                                                       env=os.environ.copy())
                stages.append(result)

            LOGGER.info("Recompiling configuration model")
            server_address = Config.get("server", "server_address", "localhost")
            result = yield self._run_compile_stage("Recompiling configuration model",
                                                   inmanta_path + ["-vvv", "export", "-e", str(environment_id),
                                                                   "--server_address", server_address, "--server_port",
                                                                   Config.get("server_rest_transport", "port", "8888")],
                                                   project_dir, env=os.environ.copy())
            stages.append(result)
        finally:
            end = datetime.datetime.now()
            self._recompiles[environment_id] = end
            for stage in stages:
                yield stage.save()

            yield data.Compile(environment=env, started=requested, completed=end, reports=stages).save()

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
                            order_by("started", direction=DESCENDING).find_all())  # @UndefinedVariable
            if limit is not None:
                models = models[:int(limit)]

        reports = []
        for m in models:
            report_dict = yield m.to_dict()
            reports.append(report_dict)

        return 200, {"reports": reports}

    @protocol.handle(methods.Snapshot.list_snapshots)
    @gen.coroutine
    def list_snapshots(self, tid):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        snapshots = yield data.Snapshot.objects.filter(environment=env).find_all()  # @UndefinedVariable
        snap_list = []
        for s in snapshots:
            result_dict = yield s.to_dict()
            snap_list.append(result_dict)

        return 200, {"snapshots": snap_list}

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
        snap_dict["resources"] = []
        for x in resources:
            res_dict = yield x.to_dict()
            snap_dict["resources"].append(res_dict)

        return 200, {"snapshot": snap_dict}

    @protocol.handle(methods.Snapshot.create_snapshot)
    @gen.coroutine
    def create_snapshot(self, tid, name):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        # get the latest deployed configuration model
        versions = yield (data.ConfigurationModel.objects.filter(environment=env, deployed=True).  # @UndefinedVariable
                          order_by("version", direction=DESCENDING).limit(1).find_all())  # @UndefinedVariable

        if len(versions) == 0:
            return 500, {"message": "There is no deployed configuration model to create a snapshot."}

        version = versions[0]

        LOGGER.info("Creating a snapshot from version %s in environment %s", version.version, tid)

        # create the snapshot
        snapshot_id = uuid.uuid4()
        snapshot = data.Snapshot(uuid=snapshot_id, environment=env, model=version, started=datetime.datetime.now(), name=name)
        yield snapshot.save()

        # find resources with state
        resources_to_snapshot = defaultdict(list)
        resource_list = []
        resource_states = yield (data.ResourceVersion.objects.filter(environment=env, model=version).  # @UndefinedVariable
                                 find_all())  # @UndefinedVariable
        for rs in resource_states:
            yield rs.load_references()
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
            client = self.get_agent_client(tid, agent)
            if client is not None:
                future = client.do_snapshot(tid, agent, snapshot_id, resources)
                self.add_future(future)

        snapshot = yield data.Snapshot.get_uuid(snapshot_id)
        value = yield snapshot.to_dict()
        value["resources"] = resource_list
        return 200, {"snapshot": value}

    @protocol.handle(methods.Snapshot.update_snapshot)
    @gen.coroutine
    def update_snapshot(self, tid, id, resource_id, snapshot_data, start, stop, size, success, error, msg):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        with (yield LOCK.acquire()):
            snapshot = yield data.Snapshot.get_uuid(id)
            if snapshot is None:
                return 404, {"message": "Snapshot with id %s does not exist!" % id}

            res = yield (data.ResourceSnapshot.objects.  # @UndefinedVariable
                         filter(environment=env, snapshot=snapshot, resource_id=resource_id).find_all())  # @UndefinedVariable

            if len(res) == 0:
                return 404, {"message": "Resource not found"}
            res = res[0]

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
        f2 = data.Snapshot.get_uuid(snapshot)
        env, snapshot = yield [f1, f2]

        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        if snapshot is None:
            return 404, {"message": "Snapshot with id %s does not exist!" % snapshot}

        # get all resources in the snapshot
        snap_resources = yield data.ResourceSnapshot.objects.filter(snapshot=snapshot).find_all()  # @UndefinedVariable

        # get all resource that support state in the current environment
        env_versions = yield (data.ConfigurationModel.objects.filter(environment=env, deployed=True).  # @UndefinedVariable
                              order_by("version", direction=DESCENDING).limit(1).find_all())  # @UndefinedVariable

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
                LOGGER.debug("Matching state_id %s to %s, scheduling restore" % (r.state_id, env_res.rid))
                yield env_res.load_references()
                r_dict = yield r.to_dict()
                restore_list[env_res.resource.agent].append((r_dict, env_res.to_dict()))

                rr = data.ResourceRestore(environment=env, restore=restore, state_id=r.state_id, resource_id=env_res.rid,
                                          started=datetime.datetime.now(),)
                yield rr.save()
                restore.resources_todo += 1

        yield restore.save()

        for agent, resources in restore_list.items():
            client = self.get_agent_client(tid, agent)
            if client is not None:
                future = client.do_restore(tid, agent, restore_id, snapshot.uuid, resources)
                self.add_future(future)

        restore = yield data.SnapshotRestore.get_uuid(restore_id)
        restore_dict = yield restore.to_dict()
        return 200, {"restore": restore_dict}

    @protocol.handle(methods.RestoreSnapshot.list_restores)
    @gen.coroutine
    def list_restores(self, tid):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        restores = yield data.SnapshotRestore.objects.filter(environment=env).find_all()  # @UndefinedVariable
        restore_list = yield [x.to_dict() for x in restores]
        return 200, {"restores": restore_list}

    @protocol.handle(methods.RestoreSnapshot.get_restore_status)
    @gen.coroutine
    def get_restore_status(self, tid, id):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        restore = yield data.SnapshotRestore.get_uuid(id)
        if restore is None:
            return 404, {"message": "The given restore id does not exist!"}

        restore_dict = yield restore.to_dict()
        resources = yield data.ResourceRestore.objects.filter(restore=restore).find_all()  # @UndefinedVariable
        restore_dict["resources"] = []
        for x in resources:
            result = yield x.to_dict()
            restore_dict["resources"].append(result)

        return 200, {"restore": restore_dict}

    @protocol.handle(methods.RestoreSnapshot.update_restore)
    @gen.coroutine
    def update_restore(self, tid, id, resource_id, success, error, msg, start, stop):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        with (yield LOCK.acquire()):
            restore = yield data.SnapshotRestore.get_uuid(id)
            rr = yield (data.ResourceRestore.objects.  # @UndefinedVariable
                        filter(environment=env, restore=restore, resource_id=resource_id).find_all())  # @UndefinedVariable
            if len(rr) == 0:
                return 404, {"message": "Resource restore not found."}
            rr = rr[0]

            rr.error = error
            rr.success = success
            rr.started = start
            rr.finished = stop
            rr.msg = msg
            yield [rr.save(), rr.load_references()]

            restore.resources_todo -= 1
            if restore.resources_todo == 0:
                restore.finished = datetime.datetime.now()
            yield restore.save()

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
        return result, {"version": version}

    @protocol.handle(methods.Decommision.clear_environment)
    @gen.coroutine
    def clear_environment(self, id):
        """
            Clear the environment
        """
        env = yield data.Environment.get_uuid(id)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        agents = yield data.Agent.objects.filter(environment=env).find_all()  # @UndefinedVariable
        for agent in agents:
            yield agent.delete()

        models = yield data.ConfigurationModel.objects.filter(environment=env).find_all()  # @UndefinedVariable
        for model in models:
            yield model.delete_cascade()

        resources = yield data.Resource.objects.filter(environment=env).find_all()  # @UndefinedVariable
        for resource in resources:
            yield resource.delete()

        parameters = yield data.Parameter.objects.filter(environment=env).find_all()  # @UndefinedVariable
        for parameter in parameters:
            yield parameter.delete()

        forms = yield data.Form.objects.filter(environment=env).find_all()  # @UndefinedVariable
        for form in forms:
            yield form.delete()

        records = yield data.FormRecord.objects.filter(environment=env).find_all()  # @UndefinedVariable
        for record in records:
            yield record.delete()

        compiles = yield data.Compile.objects.filter(environment=env).find_all()  # @UndefinedVariable
        for compile in compiles:
            yield compile.delete()

        return 200
