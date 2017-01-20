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
import logging
import os
import re
import subprocess
import sys
import time
import uuid
from uuid import UUID


import dateutil
from tornado import gen
from tornado import locks
from tornado import process
from inmanta import data
from inmanta import methods
from inmanta import protocol
from inmanta.ast import type
from inmanta.resources import Id
from inmanta.server.agentmanager import AgentManager
from inmanta.server import config as opt
import pymongo


LOGGER = logging.getLogger(__name__)
agent_lock = locks.Lock()

DBLIMIT = 100000


class Server(protocol.ServerEndpoint):
    """
        The central Inmanta server that communicates with clients and agents and persists configuration
        information
    """

    def __init__(self, io_loop, database_host=None, database_port=None, agent_no_log=False):
        super().__init__("server", io_loop=io_loop, interval=opt.agent_timeout.get(), hangtime=opt.agent_hangtime.get())
        LOGGER.info("Starting server endpoint")
        self._server_storage = self.check_storage()
        self._agent_no_log = agent_no_log

        self._db = None
        if database_host is None:
            database_host = opt.db_host.get()

        if database_port is None:
            database_port = opt.db_port.get()

        data.connect(database_host, database_port, opt.db_name.get(), self._io_loop)
        LOGGER.info("Connected to mongodb database %s on %s:%d", opt.db_name.get(), database_host, database_port)

        self._io_loop.add_callback(data.create_indexes)

        self._fact_expire = opt.server_fact_expire.get()
        self._fact_renew = opt.server_fact_renew.get()

        self.add_end_point_name(self.node_name)

        self.schedule(self.renew_expired_facts, self._fact_renew)
        self.schedule(self._purge_versions, opt.server_purge_version_interval.get())

        self._io_loop.add_callback(self._purge_versions)

        self._recompiles = defaultdict(lambda: None)

        self.agentmanager = AgentManager(self,
                                         autostart=opt.server_autostart_on_start.get(),
                                         fact_back_off=opt.server_fact_resource_block.get())

        self.setup_dashboard()

        self.dryrun_lock = locks.Lock()

    def new_session(self, sid, tid, endpoint_names, nodename):
        session = protocol.ServerEndpoint.new_session(self, sid, tid, endpoint_names, nodename)
        self.agentmanager.new_session(session)
        return session

    def expire(self, session, timeout):
        self.agentmanager.expire(session)
        protocol.ServerEndpoint.expire(self, session, timeout)

    def seen(self, session, endpoint_names):
        self.agentmanager.seen(session, endpoint_names)
        protocol.ServerEndpoint.seen(self, session, endpoint_names)

    def start(self):
        super().start()
        self.agentmanager.start()

    def stop(self):
        super().stop()
        self.agentmanager.stop()

    def get_agent_client(self, tid: UUID, endpoint):
        return self.agentmanager.get_agent_client(tid, endpoint)

    def setup_dashboard(self):
        """
            If configured, set up tornado to serve the dashboard
        """
        if not opt.dash_enable.get():
            return

        dashboard_path = opt.dash_path.get()
        if dashboard_path is None:
            LOGGER.warning("The dashboard is enabled in the configuration but its path is not configured.")
            return

        self._transport_instance.add_static_handler("dashboard", dashboard_path, start=True)

    @gen.coroutine
    def _purge_versions(self):
        """
            Purge versions from the database
        """
        # TODO: move to data and use queries for delete
        envs = yield data.Environment.get_list()
        for env_item in envs:
            # get available versions
            n_versions = opt.server_version_to_keep.get()
            versions = yield data.ConfigurationModel.get_list(released=False, environment=env_item.id)
            if len(versions) > n_versions:
                LOGGER.info("Removing %s available versions from environment %s", len(versions) - n_versions, env_item.id)
                version_dict = {x.version: x for x in versions}
                delete_list = sorted(version_dict.keys())
                delete_list = delete_list[:-n_versions]

                for v in delete_list:
                    yield version_dict[v].delete_cascade()

    def check_storage(self):
        """
            Check if the server storage is configured and ready to use.
        """
        state_dir = opt.state_dir.get()

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

        log_dir = opt.log_dir.get()
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
        expired_params = yield data.Parameter.get_updated_before(updated_before)

        LOGGER.debug("Renewing %d expired parameters" % len(expired_params))

        for param in expired_params:
            if param.environment is None:
                LOGGER.warning("Found parameter without environment (%s for resource %s). Deleting it.",
                               param.name, param.resource_id)
                yield param.delete()
            else:
                LOGGER.debug("Requesting new parameter value for %s of resource %s in env %s", param.name, param.resource_id,
                             param.environment.id)
                yield self.agentmanager._request_parameter(param.environment, param.resource_id)

        unknown_parameters = yield data.UnknownParameter.get_list(resolved=False)
        for u in unknown_parameters:
            if u.environment is None:
                LOGGER.warning("Found unknown parameter without environment (%s for resource %s). Deleting it.",
                               u.name, u.resource_id)
                yield u.delete()
            else:
                LOGGER.debug("Requesting value for unknown parameter %s of resource %s in env %s", u.name, u.resource_id, u.id)
                yield self.agentmanager._request_parameter(u.environment, u.resource_id)

        LOGGER.info("Done renewing expired parameters")

    @protocol.handle(methods.ParameterMethod.get_param, param_id="id")
    @gen.coroutine
    def get_param(self, tid, param_id, resource_id=None):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        params = yield data.Parameter.get_list(environment=tid, name=param_id, resource_id=resource_id)

        if len(params) == 0:
            out = yield self.agentmanager._request_parameter(tid, resource_id)
            return out

        param = params[0]
        # check if it was expired
        now = datetime.datetime.now()
        if (param.updated + datetime.timedelta(0, self._fact_expire)) > now:
            return 200, {"parameter": params[0].to_dict()}

        LOGGER.info("Parameter %s of resource %s expired.", param_id, resource_id)
        out = yield self.agentmanager._request_parameter(tid, resource_id)
        return out

    @gen.coroutine
    def _update_param(self, env, name, value, source, resource_id, metadata):
        """
            Update or set a parameter. This method returns true if this update resolves an unknown
        """
        LOGGER.debug("Updating/setting parameter %s in env %s (for resource %s)", name, env.id, resource_id)
        if not isinstance(value, str):
            value = str(value)

        if value is None or value == "":
            value = " "

        if resource_id is None:
            resource_id = ""

        params = yield data.Parameter.get_list(environment=env.id, name=name, resource_id=resource_id)

        if len(params) == 0:
            param = data.Parameter(environment=env.id, name=name, resource_id=resource_id, value=value, source=source,
                                   updated=datetime.datetime.now(), metadata=metadata)
            yield param.insert()
        else:
            param = params[0]
            yield param.update(source=source, value=value, updated=datetime.datetime.now(), metadata=metadata)

        # check if the parameter is an unknown
        params = yield data.UnknownParameter.get_list(environment=env.id, name=name, resource_id=resource_id, resolved=False)
        if len(params) > 0:
            LOGGER.info("Received values for unknown parameters %s, triggering a recompile",
                        ", ".join([x.name for x in params]))
            for p in params:
                yield p.update_fields(resolved=True)

            return True

        return False

    @protocol.handle(methods.ParameterMethod.set_param, param_id="id")
    @gen.coroutine
    def set_param(self, tid, param_id, source, value, resource_id, metadata):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        result = yield self._update_param(env, param_id, value, source, resource_id, metadata)
        if result:
            self._async_recompile(tid, False, opt.server_wait_after_param.get())

        if resource_id is None:
            resource_id = ""

        params = yield data.Parameter.get_list(environment=env.id, name=param_id, resource_id=resource_id)

        return 200, {"parameter": params[0].to_dict()}

    @protocol.handle(methods.ParametersMethod.set_parameters)
    @gen.coroutine
    def set_parameters(self, tid, parameters):
        env = yield data.Environment.get_by_id(tid)
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
            self._async_recompile(tid, False, opt.server_wait_after_param.get())

        return 200

    @protocol.handle(methods.ParameterMethod.list_params)
    @gen.coroutine
    def list_param(self, tid, query):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        m_query = {"environment": env}
        for k, v in query.items():
            m_query["metadata." + k] = v

        params = yield data.Parameter.get_list(**m_query)
        return 200, {"parameters": params, "expire": self._fact_expire, "now": datetime.datetime.now().isoformat()}

    @protocol.handle(methods.FormMethod.put_form, form_id="id")
    @gen.coroutine
    def put_form(self, tid: uuid.UUID, form_id: str, form: dict):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        form_doc = yield data.Form.get_form(environment=tid, form_type=form_id)
        fields = {k: v["type"] for k, v in form["attributes"].items()}
        defaults = {k: v["default"] for k, v in form["attributes"].items() if "default" in v}
        field_options = {k: v["options"] for k, v in form["attributes"].items() if "options" in v}

        if form_doc is None:
            form_doc = data.Form(environment=tid, form_type=form_id, fields=fields, defaults=defaults,
                                 options=form["options"], field_options=field_options)
            yield form_doc.insert()

        else:
            # update the definition
            form_doc.fields = fields
            form_doc.defaults = defaults
            form_doc.options = form["options"]
            form_doc.field_options = field_options

            yield form_doc.update()

        return 200, {"form": {"id": form_doc.id}}

    @protocol.handle(methods.FormMethod.get_form, form_id="id")
    @gen.coroutine
    def get_form(self, tid, form_id):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        form = yield data.Form.get_form(environment=env.id, form_type=form_id)

        if form is None:
            return 404

        return 200, {"form": form}

    @protocol.handle(methods.FormMethod.list_forms)
    @gen.coroutine
    def list_forms(self, tid):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        forms = yield data.Form.get_list(environment=tid)

        return 200, {"forms": [{"form_id": x.id, "form_type": x.form_type} for x in forms]}

    @protocol.handle(methods.FormRecords.list_records)
    @gen.coroutine
    def list_records(self, tid, form_type, include_record):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        form_type = yield data.Form.get_form(environment=tid, form_type=form_type)
        if form_type is None:
            return 404, {"message": "No form is defined with id %s" % form_type}

        records = yield data.FormRecord.get_list(form=form_type.id)

        if not include_record:
            return 200, {"records": [{"record_id": r.id, "changed": r.changed} for r in records]}

        else:
            return 200, {"records": records}

    @protocol.handle(methods.FormRecords.get_record, record_id="id")
    @gen.coroutine
    def get_record(self, tid, record_id):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        record = yield data.FormRecord.get_by_id(record_id)
        if record is None:
            return 404, {"message": "The record with id %s does not exist" % record_id}

        return 200, {"record": record}

    @protocol.handle(methods.FormRecords.update_record, record_id="id")
    @gen.coroutine
    def update_record(self, tid, record_id, form):
        env = yield data.Environment.get_by_id(tid)
        record = yield data.FormRecord.get_by_id(record_id)
        form_def = yield data.Form.get_by_id(record.form)

        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        record.changed = datetime.datetime.now()

        for k, _v in form_def.fields.items():
            if k in form_def.fields:
                value = form[k]
                field_type = form_def.fields[k]
                if field_type in type.TYPES:
                    type_obj = type.TYPES[field_type]
                    record.fields[k] = type_obj.cast(value)
                else:
                    LOGGER.warning("Field %s in form %s has an invalid type." % (k, id))

        yield record.update()

        self._async_recompile(tid, False, opt.server_wait_after_param.get())
        return 200, {"record": record}

    @protocol.handle(methods.FormRecords.create_record)
    @gen.coroutine
    def create_record(self, tid, form_type, form):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        form_obj = yield data.Form.get_form(environment=tid, form_type=form_type)

        if form_obj is None:
            return 404, {"message": "The form %s does not exist in env %s" % (tid, form_type)}

        record = data.FormRecord(environment=tid, form=form_obj.id, fields={})
        record.changed = datetime.datetime.now()

        for k, _v in form_obj.fields.items():
            if k in form:
                value = form[k]
                field_type = form_obj.fields[k]
                if field_type in type.TYPES:
                    type_obj = type.TYPES[field_type]
                    record.fields[k] = type_obj.cast(value)
                else:
                    LOGGER.warning("Field %s in form %s has an invalid type." % (k, form_type))

        yield record.insert()
        self._async_recompile(tid, False, opt.server_wait_after_param.get())

        return 200, {"record": record}

    @protocol.handle(methods.FormRecords.delete_record, record_id="id")
    @gen.coroutine
    def delete_record(self, tid, record_id):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        record = yield data.FormRecord.get_by_id(record_id)
        yield record.delete()

        return 200

    @protocol.handle(methods.FileMethod.upload_file, file_hash="id")
    @gen.coroutine
    def upload_file(self, file_hash, content):
        file_name = os.path.join(self._server_storage["files"], file_hash)

        if os.path.exists(file_name):
            return 500, {"message": "A file with this id already exists."}

        with open(file_name, "wb+") as fd:
            fd.write(base64.b64decode(content))

        return 200

    @protocol.handle(methods.FileMethod.stat_file, file_hash="id")
    @gen.coroutine
    def stat_file(self, file_hash):
        file_name = os.path.join(self._server_storage["files"], file_hash)

        if os.path.exists(file_name):
            return 200
        else:
            return 404

    @protocol.handle(methods.FileMethod.get_file, file_hash="id")
    @gen.coroutine
    def get_file(self, file_hash):
        file_name = os.path.join(self._server_storage["files"], file_hash)

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

    @protocol.handle(methods.NodeMethod.get_agent_process, agent_id="id")
    @gen.coroutine
    def get_agent_process(self, agent_id):
        return (yield self.agentmanager.get_agent_process_report(agent_id))

    @protocol.handle(methods.ServerAgentApiMethod.trigger_agent, agent_id="id")
    @gen.coroutine
    def trigger_agent(self, tid, agent_id):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        yield self.agentmanager.trigger_agent(tid, agent_id)

    @protocol.handle(methods.NodeMethod.list_agent_processes)
    @gen.coroutine
    def list_agent_processes(self, environment, expired):
        env = yield data.Environment.get_by_id(environment)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        return (yield self.agentmanager.list_agent_processes(environment, expired))

    @protocol.handle(methods.ServerAgentApiMethod.list_agents)
    @gen.coroutine
    def list_agents(self, tid: UUID=None):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        return (yield self.agentmanager.list_agents(tid))

    @protocol.handle(methods.AgentRecovery.get_state)
    @gen.coroutine
    def get_state(self, tid: uuid.UUID, sid: uuid.UUID, agent: str):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        return (yield self.agentmanager.get_state(tid, sid, agent))

    @protocol.handle(methods.ResourceMethod.get_resource, resource_id="id")
    @gen.coroutine
    def get_resource(self, tid, resource_id, logs, status):
        resv = yield data.Resource.get(tid, resource_id)
        if resv is None:
            return 404, {"message": "The resource with the given id does not exist in the given environment"}

        if status is not None and status:
            return 200, {"status": resv.status}

        action_list = []
        if bool(logs):
            actions = yield data.ResourceAction.get_list(resource_version_id=resource_id)
            for action in actions:
                action_list.append(action.to_dict())

        return 200, {"resource": resv.to_dict(), "logs": action_list}

    @protocol.handle(methods.ResourceMethod.get_resources_for_agent)
    @gen.coroutine
    def get_resources_for_agent(self, tid, agent, version):
        if version is None:
            cm = yield data.ConfigurationModel.get_latest_version(tid)
            if cm is None:
                return 404, {"message": "No version available"}

            version = cm.version

        else:
            cm = yield data.ConfigurationModel.get_version(environment=tid, version=version)
            if cm is None:
                return 404, {"message": "The given version does not exist"}

        deploy_model = []

        resources = yield data.Resource.get_resources_for_version(tid, version, agent)

        for rv in resources:
            deploy_model.append(rv.to_dict())
            ra = data.ResourceAction(resource_version_id=rv.resource_version_id, action="pull", level="INFO",
                                     timestamp=datetime.datetime.now(),
                                     message="Resource version pulled by client for agent %s state" % agent)
            yield ra.insert()

        return 200, {"environment": tid, "agent": agent, "version": version, "resources": deploy_model}

    @protocol.handle(methods.CMVersionMethod.list_versions)
    @gen.coroutine
    def list_version(self, tid, start=None, limit=None):
        if (start is None and limit is not None) or (limit is None and start is not None):
            return 500, {"message": "Start and limit should always be set together."}

        if start is None:
            start = 0
            limit = data.DBLIMIT

        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        models = yield data.ConfigurationModel.get_versions(tid, start, limit)
        count = len(models)

        d = {"versions": []}
        for m in models:
            model_dict = m.to_dict()
            d["versions"].append(model_dict)

        if start is not None:
            d["start"] = start
            d["limit"] = limit

        d["count"] = count

        return 200, d

    @protocol.handle(methods.CMVersionMethod.get_version, version_id="id")
    @gen.coroutine
    def get_version(self, tid, version_id, include_logs=None, log_filter=None, limit=None):
        version = yield data.ConfigurationModel.get_version(tid, version_id)
        if version is None:
            return 404, {"message": "The given configuration model does not exist yet."}

        resources = yield data.Resource.get_resources_for_version(tid, version_id)
        if resources is None:
            return 404, {"message": "The given configuration model does not exist yet."}

        d = {"model": version.to_dict()}

        d["resources"] = []
        for res in resources:
            res_dict = res.to_dict()

            if bool(include_logs):
                actions = yield data.ResourceAction.get_log(res.resource_version_id, log_filter, limit)

                res_dict["actions"] = [x.to_dict() for x in actions]

            d["resources"].append(res_dict)

        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        unp = yield data.UnknownParameter.get_list(environment=tid, version=version_id)
        d["unknowns"] = [x.to_dict() for x in unp]

        return 200, d

    @protocol.handle(methods.CMVersionMethod.delete_version, version_id="id")
    @gen.coroutine
    def delete_version(self, tid, version_id):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        version = yield data.ConfigurationModel.get_version(tid, version_id)
        if version is None:
            return 404, {"message": "The given configuration model does not exist yet."}

        yield version.delete()
        return 200

    @protocol.handle(methods.CMVersionMethod.put_version)
    @gen.coroutine
    def put_version(self, tid, version, resources, unknowns, version_info):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        try:
            cm = data.ConfigurationModel(environment=tid, version=version, date=datetime.datetime.now(),
                                         total=len(resources), version_info=version_info)
            yield cm.insert()
        except pymongo.errors.DuplicateKeyError:
            return 500, {"message": "The given version is already defined. Versions should be unique."}

        agents = set()
        # lookup for all RV's, lookup by resource id
        rv_dict = {}
        # list of all resources which have a cross agent dependency, as a tuple, (dependant,requires)
        cross_agent_dep = []

        resource_objects = []
        resource_action_objects = []
        for res_dict in resources:
            res_obj = data.Resource.new(tid, res_dict["id"])

            # collect all agents
            agents.add(res_obj.agent)

            # for state handling
            if "state_id" in res_dict:
                if res_dict["state_id"] == "":
                    res_dict["state_id"] = res_obj.resource_id

            attributes = {}
            for field, value in res_dict.items():
                if field != "id":
                    attributes[field] = value

            res_obj.attributes = attributes
            resource_objects.append(res_obj)

            rv_dict[res_obj.resource_id] = res_obj

            ra = data.ResourceAction(resource_version_id=res_obj.resource_version_id, action="store", level="INFO",
                                     timestamp=datetime.datetime.now())
            resource_action_objects.append(ra)

            # find cross agent dependencies
            agent = res_obj.agent
            if "requires" not in attributes:
                LOGGER.warning("Received resource without requires attribute (%s)" % res_obj.resource_id)
            else:
                for req in attributes["requires"]:
                    rid = Id.parse_id(req)
                    if rid.get_agent_name() != agent:
                        # it is a CAD
                        cross_agent_dep.append((res_obj, rid))

        # hook up all CADs
        for f, t in cross_agent_dep:
            rv_dict[t.resource_str()].provides.append(f.resource_version_id)

        yield data.Resource.insert_many(resource_objects)
        yield data.ResourceAction.insert_many(resource_action_objects)

        # search for deleted resources
        resources_to_purge = yield data.Resource.get_deleted_resources(tid, version)
        for res in resources_to_purge:
            LOGGER.warning("Purging %s, purged resource based on %s" % (res.resource_id, res.resource_version_id))

            attributes = res.attributes.copy()
            attributes["purged"] = "true"

            # TODO: handle delete relations
            attributes["requires"] = []

            res_obj = data.Resource.new(tid, rid="%s,v=%s" % (res.resource_id, version), attributes=attributes)
            yield res_obj.insert()

            ra = data.ResourceAction(resource_version_id=res_obj.resource_version_id, action="store", level="INFO",
                                     timestamp=datetime.datetime.now())
            yield ra.insert()

            agents.add(res_obj.agent)

        yield cm.update_fields(total=cm.total + len(resources_to_purge))

        for uk in unknowns:
            if "resource" not in uk:
                uk["resource"] = ""

            if "metadata" not in uk:
                uk["metadata"] = {}

            up = data.UnknownParameter(resource_id=uk["resource"], name=uk["parameter"], source=uk["source"], environment=tid,
                                       version=version, metadata=uk["metadata"])
            yield up.insert()

        for agent in agents:
            yield self.agentmanager.ensure_agent_registered(env, agent)

        LOGGER.debug("Successfully stored version %d" % version)

        return 200

    @protocol.handle(methods.CMVersionMethod.release_version, version_id="id")
    @gen.coroutine
    def release_version(self, tid, version_id, push):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        model = yield data.ConfigurationModel.get_version(tid, version_id)
        if model is None:
            return 404, {"message": "The request version does not exist."}

        yield model.update_fields(released=True, result="deploying")

        if push:
            # fetch all resource in this cm and create a list of distinct agents
            agents = yield data.ConfigurationModel.get_agents(tid, version_id)
            yield self.agentmanager._ensure_agents(str(tid), agents)

            for agent in agents:
                client = self.get_agent_client(tid, agent)
                if client is not None:
                    future = client.trigger(tid, agent)
                    self.add_future(future)
                else:
                    LOGGER.warning("Agent %s from model %s in env %s is not available for a deploy", agent, version_id, tid)

        return 200, {"model": model}

    @protocol.handle(methods.DryRunMethod.dryrun_request, version_id="id")
    @gen.coroutine
    def dryrun_request(self, tid, version_id):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        model = yield data.ConfigurationModel.get_version(environment=tid, version=version_id)
        if model is None:
            return 404, {"message": "The request version does not exist."}

        # fetch all resource in this cm and create a list of distinct agents
        rvs = yield data.Resource.get_list(model=version_id, environment=tid)

        # Create a dryrun document
        dryrun = yield data.DryRun.create(environment=tid, model=version_id, todo=len(rvs), total=len(rvs))

        agents = yield data.ConfigurationModel.get_agents(tid, version_id)
        yield self.agentmanager._ensure_agents(str(tid), agents)

        for agent in agents:
            client = self.get_agent_client(tid, agent)
            if client is not None:
                future = client.do_dryrun(tid, dryrun.id, agent, version_id)
                self.add_future(future)
            else:
                LOGGER.warning("Agent %s from model %s in env %s is not available for a dryrun", agent, version_id, tid)

        return 200, {"dryrun": dryrun}

    @protocol.handle(methods.DryRunMethod.dryrun_list)
    @gen.coroutine
    def dryrun_list(self, tid, version=None):
        query_args = {}
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        query_args["environment"] = tid
        if version is not None:
            model = yield data.ConfigurationModel.get_version(environment=tid, version=version)
            if model is None:
                return 404, {"message": "The request version does not exist."}

            query_args["model"] = version

        dryruns = yield data.DryRun.get_list(**query_args)

        return 200, {"dryruns": [{"id": x.id, "version": x.model, "date": x.date, "total": x.total, "todo": x.todo}
                                 for x in dryruns]}

    @protocol.handle(methods.DryRunMethod.dryrun_report, dryrun_id="id")
    @gen.coroutine
    def dryrun_report(self, tid, dryrun_id):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        dryrun = yield data.DryRun.get_by_id(dryrun_id)
        if dryrun is None:
            return 404, {"message": "The given dryrun does not exist!"}

        return 200, {"dryrun": dryrun}

    @protocol.handle(methods.DryRunMethod.dryrun_update, dryrun_id="id")
    @gen.coroutine
    def dryrun_update(self, tid, dryrun_id, resource, changes, log_msg=None):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        with (yield self.dryrun_lock.acquire()):
            payload = {"changes": changes, "log": log_msg, "id_fields": Id.parse_id(resource).to_dict(), "id": resource}
            yield data.DryRun.update_resource(dryrun_id, resource, payload)

        return 200

    @protocol.handle(methods.CodeMethod.upload_code, code_id="id")
    @gen.coroutine
    def upload_code(self, tid, code_id, resource, sources):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        code = yield data.Code.get_version(environment=tid, version=code_id, resource=resource)
        if code is not None:
            return 500, {"message": "Code for this version has already been uploaded."}

        code = data.Code(environment=tid, version=code_id, resource=resource, sources=sources)
        yield code.insert()

        return 200

    @protocol.handle(methods.CodeMethod.get_code, code_id="id")
    @gen.coroutine
    def get_code(self, tid, code_id, resource):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        code = yield data.Code.get_version(environment=tid, version=code_id, resource=resource)
        if code is None:
            return 404, {"message": "The version of the code does not exist."}

        return 200, {"version": code_id, "environment": tid, "resource": resource, "sources": code.sources}

    @protocol.handle(methods.ResourceMethod.resource_updated, resource_id="id")
    @gen.coroutine
    def resource_updated(self, tid, resource_id, level, action, message, status, extra_data):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        resv = yield data.Resource.get(environment=tid, resource_version_id=resource_id)
        if resv is None:
            return 404, {"message": "The resource with the given id does not exist in the given environment"}

        now = datetime.datetime.now()
        yield resv.update_fields(last_deploy=now, status=status)

        ra = data.ResourceAction(resource_version_id=resource_id, action=action, message=message,
                                 data=extra_data, level=level, timestamp=now, status=status)
        yield ra.insert()

        # TODO: hairy stuff
        yield data.ConfigurationModel.set_ready(tid, resv.model, resv.id, resv.resource_id, status)
        model = yield data.ConfigurationModel.get_version(tid, resv.model)

        if model.done == model.total:
            result = "success"
            for status in model.status.values():
                if status != "deployed":
                    model.result = "failed"

            yield model.update_fields(deployed=True, result=result)

        waitingagents = set([Id.parse_id(prov).get_agent_name() for prov in resv.provides])

        for agent in waitingagents:
            yield self.get_agent_client(tid, agent).resource_event(tid, agent, resource_id, status)

        return 200

    # Project handlers
    @protocol.handle(methods.Project.create_project)
    @gen.coroutine
    def create_project(self, name):
        try:
            project = data.Project(name=name)
            yield project.insert()
        except pymongo.errors.DuplicateKeyError:
            return 500, {"message": "A project with name %s already exists." % name}

        return 200, {"project": project}

    @protocol.handle(methods.Project.delete_project, project_id="id")
    @gen.coroutine
    def delete_project(self, project_id):
        project = yield data.Project.get_by_id(project_id)
        if project is None:
            return 404, {"message": "The project with given id does not exist."}

        yield project.delete_cascade()
        return 200, {}

    @protocol.handle(methods.Project.modify_project, project_id="id")
    @gen.coroutine
    def modify_project(self, project_id, name):
        try:
            project = yield data.Project.get_by_id(project_id)
            if project is None:
                return 404, {"message": "The project with given id does not exist."}

            yield project.update_fields(name=name)

            return 200, {"project": project}

        except pymongo.errors.DuplicateKeyError:
            return 500, {"message": "A project with name %s already exists." % name}

    @protocol.handle(methods.Project.list_projects)
    @gen.coroutine
    def list_projects(self):
        projects = yield data.Project.get_list()
        return 200, {"projects": projects}

    @protocol.handle(methods.Project.get_project, project_id="id")
    @gen.coroutine
    def get_project(self, project_id):
        try:
            project = yield data.Project.get_by_id(project_id)
            environments = yield data.Environment.get_list(project=project_id)

            if project is None:
                return 404, {"message": "The project with given id does not exist."}

            project_dict = project.to_dict()
            project_dict["environments"] = [e.id for e in environments]

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
        project = yield data.Project.get_by_id(project_id)
        if project is None:
            return 500, {"message": "The project id for the environment does not exist."}

        # check if an environment with this name is already defined in this project
        envs = yield data.Environment.get_list(project=project_id, name=name)
        if len(envs) > 0:
            return 500, {"message": "Project %s (id=%s) already has an environment with name %s" %
                         (project.name, project.id, name)}

        env = data.Environment(name=name, project=project_id, repo_url=repository, repo_branch=branch)
        yield env.insert()
        return 200, {"environment": env}

    @protocol.handle(methods.Environment.modify_environment, environment_id="id")
    @gen.coroutine
    def modify_environment(self, environment_id, name, repository, branch):
        env = yield data.Environment.get_by_id(environment_id)
        if env is None:
            return 404, {"message": "The environment id does not exist."}

        # check if an environment with this name is already defined in this project
        envs = yield data.Environment.get_list(project=env.project, name=name)
        if len(envs) > 0:
            return 500, {"message": "Project with id=%s already has an environment with name %s" % (env.project_id, name)}

        fields = {"name": name}
        if repository is not None:
            fields["repo_url"] = repository

        if branch is not None:
            fields["repo_branch"] = branch

        yield env.update_fields(**fields)
        return 200, {"environment": env}

    @protocol.handle(methods.Environment.get_environment, environment_id="id")
    @gen.coroutine
    def get_environment(self, environment_id, versions=None, resources=None):
        versions = 0 if versions is None else int(versions)
        resources = 0 if resources is None else int(resources)

        env = yield data.Environment.get_by_id(environment_id)

        if env is None:
            return 404, {"message": "The environment id does not exist."}

        env_dict = env.to_dict()

        if versions > 0:
            v = yield data.ConfigurationModel.get_versions(environment_id, limit=versions)
            env_dict["versions"] = []
            for model in v:
                env_dict["versions"].append(model.to_dict())

        if resources > 0:
            env_dict["resources"] = yield data.Resource.get_resources_report(environment=environment_id)

        return 200, {"environment": env_dict}

    @protocol.handle(methods.Environment.list_environments)
    @gen.coroutine
    def list_environments(self):
        environments = yield data.Environment.get_list()
        dicts = []
        for env in environments:
            env_dict = env.to_dict()
            dicts.append(env_dict)

        return 200, {"environments": dicts}  # @UndefinedVariable

    @protocol.handle(methods.Environment.delete_environment, environment_id="id")
    @gen.coroutine
    def delete_environment(self, environment_id):
        env = yield data.Environment.get_by_id(environment_id)
        if env is None:
            return 404, {"message": "The environment with given id does not exist."}

        yield env.delete_cascade()

        return 200

    @protocol.handle(methods.NotifyMethod.is_compiling, environment_id="id")
    @gen.coroutine
    def is_compiling(self, environment_id):
        if self._recompiles[environment_id] is self:
            return 200

        return 204

    @protocol.handle(methods.NotifyMethod.notify_change, environment_id="id")
    @gen.coroutine
    def notify_change(self, environment_id, update):
        LOGGER.info("Received change notification for environment %s", environment_id)
        self._async_recompile(environment_id, update > 0)

        return 200

    def _async_recompile(self, environment_id, update_repo, wait=0):
        """
            Recompile an environment in a different thread and taking wait time into account.
        """
        if opt.server_no_recompile.get():
            LOGGER.info("Skipping compile due to no-recompile=True")
            return
        last_recompile = self._recompiles[environment_id]
        wait_time = opt.server_autrecompile_wait.get()
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

    @gen.coroutine
    def _run_compile_stage(self, name, cmd, cwd, **kwargs):
        start = datetime.datetime.now()

        sub_process = process.Subprocess(cmd, stdout=process.Subprocess.STREAM, stderr=process.Subprocess.STREAM,
                                         cwd=cwd, **kwargs)

        log_out, log_err, returncode = yield [gen.Task(sub_process.stdout.read_until_close),
                                              gen.Task(sub_process.stderr.read_until_close),
                                              sub_process.wait_for_exit(raise_error=False)]
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

        env = yield data.Environment.get_by_id(environment_id)
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
            server_address = opt.server_address.get()
            result = yield self._run_compile_stage("Recompiling configuration model",
                                                   inmanta_path + ["-vvv", "export", "-e", str(environment_id),
                                                                   "--server_address", server_address, "--server_port",
                                                                   opt.transport_port.get()],
                                                   project_dir, env=os.environ.copy())
            stages.append(result)
        finally:
            end = datetime.datetime.now()
            self._recompiles[environment_id] = end
            stage_ids = []
            for stage in stages:
                yield stage.insert()
                stage_ids.append(stage.id)

            comp = data.Compile(environment=environment_id, started=requested, completed=end,
                                reports=stage_ids)
            yield comp.insert()

    @protocol.handle(methods.CompileReport.get_reports)
    @gen.coroutine
    def get_reports(self, environment=None, start=None, end=None, limit=None):
        argscount = len([x for x in [start, end, limit] if x is not None])
        if argscount == 3:
            return 500, {"message": "Limit, start and end can not be set together"}

        queryparts = {}

        if environment is not None:
            env = yield data.Environment.get_by_id(environment)
            if env is None:
                return 404, {"message": "The given environment id does not exist!"}

            queryparts["environment"] = env

        if start is not None:
            queryparts["started"] = {"$gt": dateutil.parser.parse(start)}

        if end is not None:
            queryparts["started"] = {"$lt": dateutil.parser.parse(end)}

        if limit is not None and end is not None:
            cursor = data.Compile._coll.find(**queryparts).sort("started").limit(int(limit))
            models = []
            while (yield cursor.fetch_next):
                models.append(data.Compile(from_mongo=True, **cursor.next_object()))

            models.reverse()
        else:
            cursor = data.Compile._coll.find(**queryparts).sort("started", pymongo.DESCENDING).limit(int(limit))
            models = []
            while (yield cursor.fetch_next):
                models.append(data.Compile(from_mongo=True, **cursor.next_object()))

        reports = []
        for m in models:
            report_dict = yield m.to_dict()
            reports.append(report_dict)

        return 200, {"reports": reports}

    @protocol.handle(methods.Snapshot.list_snapshots)
    @gen.coroutine
    def list_snapshots(self, tid):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        snapshots = yield data.Snapshot.get_list(environment=tid)
        return 200, {"snapshots": snapshots}

    @protocol.handle(methods.Snapshot.get_snapshot, snapshot_id="id")
    @gen.coroutine
    def get_snapshot(self, tid, snapshot_id):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        snapshot = yield data.Snapshot.get_by_id(snapshot_id)
        if snapshot is None:
            return 404, {"message": "The given snapshot id does not exist!"}
        snap_dict = snapshot.to_dict()

        resources = yield data.ResourceSnapshot.get_list(snapshot=snapshot.id)
        snap_dict["resources"] = [r.to_dict() for r in resources]
        return 200, {"snapshot": snap_dict}

    @protocol.handle(methods.Snapshot.create_snapshot)
    @gen.coroutine
    def create_snapshot(self, tid, name):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        # get the latest deployed configuration model
        version = yield data.ConfigurationModel.get_latest_version(tid)
        if version is None:
            return 500, {"message": "There is no deployed configuration model to create a snapshot."}

        LOGGER.info("Creating a snapshot from version %s in environment %s", version.version, tid)

        # create the snapshot
        snapshot = data.Snapshot(environment=env.id, model=version.version, started=datetime.datetime.now(), name=name)
        yield snapshot.insert()

        # find resources with state
        resources_to_snapshot = defaultdict(list)
        resource_list = []
        resource_states = yield data.Resource.get_with_state(environment=tid, version=version.version)

        for rs in resource_states:
            agent = rs.agent
            resources_to_snapshot[agent].append(rs.to_dict())
            resource_list.append(rs.resource_id)
            r = data.ResourceSnapshot(environment=tid, snapshot=snapshot.id, resource_id=rs.resource_id,
                                      state_id=rs.attributes["state_id"])
            yield r.insert()

        if len(resource_list) == 0:
            yield snapshot.update_fields(finished=datetime.datetime.now(), total_size=0)
        else:
            yield snapshot.update_fields(resources_todo=len(resource_list))

        for agent, resources in resources_to_snapshot.items():
            client = self.get_agent_client(tid, agent)
            if client is not None:
                future = client.do_snapshot(tid, agent, snapshot.id, resources)
                self.add_future(future)

        value = snapshot.to_dict()
        value["resources"] = resource_list
        return 200, {"snapshot": value}

    @protocol.handle(methods.Snapshot.update_snapshot, snapshot_id="id")
    @gen.coroutine
    def update_snapshot(self, tid, snapshot_id, resource_id, snapshot_data, start, stop, size, success, error, msg):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        with (yield agent_lock.acquire()):
            snapshot = yield data.Snapshot.get_by_id(snapshot_id)
            if snapshot is None:
                return 404, {"message": "Snapshot with id %s does not exist!" % snapshot_id}

            res = yield data.ResourceSnapshot.get_list(environment=env.id, snapshot=snapshot.id, resource_id=resource_id)

            if len(res) == 0:
                return 404, {"message": "Resource not found"}
            res = res[0]

            yield res.update_fields(content_hash=snapshot_data, started=start, finished=stop, size=size, success=success,
                                    error=error, msg=msg)

            yield snapshot.resource_updated(size)

        return 200

    @protocol.handle(methods.Snapshot.delete_snapshot, snapshot_id="id")
    @gen.coroutine
    def delete_snapshot(self, tid, snapshot_id):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        snapshot = yield data.Snapshot.get_by_id(snapshot_id)
        if snapshot is None:
            return 404, {"message": "Snapshot with id %s does not exist!" % snapshot_id}

        yield snapshot.delete_cascade()

        return 200

    @protocol.handle(methods.RestoreSnapshot.restore_snapshot)
    @gen.coroutine
    def restore_snapshot(self, tid, snapshot):
        env = yield data.Environment.get_by_id(tid)
        snapshot = yield data.Snapshot.get_by_id(snapshot)

        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        if snapshot is None:
            return 404, {"message": "Snapshot with id %s does not exist!" % snapshot}

        # get all resources in the snapshot
        snap_resources = yield data.ResourceSnapshot.get_list(snapshot=snapshot.id)

        # get all resource that support state in the current environment
        env_version = yield data.ConfigurationModel.get_latest_version(tid)
        if env_version is None:
            return 500, {"message": "There is no deployed configuration model in this environment."}

        env_resources = yield data.Resource.get_with_state(environment=tid, version=env_version.version)
        env_states = {r.attributes["state_id"]: r for r in env_resources}

        # create a restore object
        restore = data.SnapshotRestore(snapshot=snapshot.id, environment=tid, started=datetime.datetime.now())

        # find matching resources
        restore_list = defaultdict(list)
        todo = 0
        for r in snap_resources:
            if r.state_id in env_states:
                env_res = env_states[r.state_id]
                LOGGER.debug("Matching state_id %s to %s, scheduling restore" % (r.state_id, env_res.resource_id))
                restore_list[env_res.agent].append((r.to_dict(), env_res.to_dict()))

                rr = data.ResourceRestore(environment=tid, restore=restore.id, state_id=r.state_id,
                                          resource_id=env_res.resource_version_id, started=datetime.datetime.now(),)
                yield rr.insert()
                todo += 1

        restore.resources_todo = todo
        yield restore.insert()

        for agent, resources in restore_list.items():
            client = self.get_agent_client(tid, agent)
            if client is not None:
                future = client.do_restore(tid, agent, restore.id, snapshot.id, resources)
                self.add_future(future)

        return 200, {"restore": restore}

    @protocol.handle(methods.RestoreSnapshot.list_restores)
    @gen.coroutine
    def list_restores(self, tid):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        restores = yield data.SnapshotRestore.get_list(environment=tid)
        return 200, {"restores": restores}

    @protocol.handle(methods.RestoreSnapshot.get_restore_status, restore_id="id")
    @gen.coroutine
    def get_restore_status(self, tid, restore_id):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        restore = yield data.SnapshotRestore.get_by_id(restore_id)
        if restore is None:
            return 404, {"message": "The given restore id does not exist!"}

        restore_dict = restore.to_dict()
        resources = yield data.ResourceRestore.get_list(restore=restore_id)
        restore_dict["resources"] = [x.to_dict() for x in resources]
        return 200, {"restore": restore_dict}

    @protocol.handle(methods.RestoreSnapshot.update_restore, restore_id="id")
    @gen.coroutine
    def update_restore(self, tid, restore_id, resource_id, success, error, msg, start, stop):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        restore = yield data.SnapshotRestore.get_by_id(restore_id)
        rr = yield data.ResourceRestore.get_list(environment=tid, restore=restore.id, resource_id=resource_id)
        if len(rr) == 0:
            return 404, {"message": "Resource restore not found."}
        rr = rr[0]

        yield rr.update_fields(error=error, success=success, started=start, finished=stop, msg=msg)
        yield restore.resource_updated()

        return 200

    @protocol.handle(methods.RestoreSnapshot.delete_restore, resource_id="id")
    @gen.coroutine
    def delete_restore(self, tid, restore_id):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        restore = yield data.SnapshotRestore.get_by_id(restore_id)
        if restore is None:
            return 404, {"message": "The given restore id does not exist!"}

        yield restore.delete()
        return 200

    @protocol.handle(methods.Decommision.decomission_environment, restore_id="id")
    @gen.coroutine
    def decomission_environment(self, restore_id):
        env = yield data.Environment.get_by_id(id)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        version = int(time.time())
        result = yield self.put_version(restore_id, version, [], [], {})
        return result, {"version": version}

    @protocol.handle(methods.Decommision.clear_environment, env_id="id")
    @gen.coroutine
    def clear_environment(self, env_id):
        """
            Clear the environment
        """
        env = yield data.Environment.get_by_id(env_id)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        yield data.Agent.delete_all(environment=env_id)
        models = yield data.ConfigurationModel.get_list()
        for model in models:
            yield model.delete_cascade()

        yield data.Parameter.delete_all(environment=env_id)
        yield data.Form.delete_all(environment=env_id)
        yield data.FormRecord.delete_all(environment=env_id)
        yield data.Compile.delete_all(environment=env_id)
        return 200
