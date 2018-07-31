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

import base64
from collections import defaultdict
import datetime
import difflib
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
from uuid import UUID
import uuid

import dateutil
import pymongo
from tornado import gen
from tornado import locks
from tornado import process

from inmanta import const
from inmanta import data, config
from inmanta import methods
from inmanta import protocol
from inmanta.ast import type
from inmanta.resources import Id
from inmanta.server import config as opt
from inmanta.server.agentmanager import AgentManager
import json
from inmanta.util import hash_file

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

        self.agentmanager = AgentManager(self, fact_back_off=opt.server_fact_resource_block.get())

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

        if not opt.server_enable_auth.get():
            auth = ""
        else:
            auth = """,
    'auth': {
        'realm': '%s',
        'url': '%s',
        'clientId': '%s'
    }""" % (opt.dash_realm.get(), opt.dash_auth_url.get(), opt.dash_client_id.get())
        content = """
angular.module('inmantaApi.config', []).constant('inmantaConfig', {
    'backend': window.location.origin+'/'%s
});
        """ % auth
        self._transport_instance.add_static_content("/dashboard/config.js", content=content)
        self._transport_instance.add_static_handler("/dashboard", dashboard_path, start=True)

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
            versions = yield data.ConfigurationModel.get_list(environment=env_item.id)
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
                             param.environment)
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

    @protocol.handle(methods.ParameterMethod.get_param, param_id="id", env="tid")
    @gen.coroutine
    def get_param(self, env, param_id, resource_id=None):
        if resource_id is None:
            params = yield data.Parameter.get_list(environment=env.id, name=param_id)
        else:
            params = yield data.Parameter.get_list(environment=env.id, name=param_id, resource_id=resource_id)

        if len(params) == 0:
            if resource_id is not None:
                out = yield self.agentmanager._request_parameter(env.id, resource_id)
                return out
            return 404

        param = params[0]

        # check if it was expired
        now = datetime.datetime.now()
        if resource_id is None or (param.updated + datetime.timedelta(0, self._fact_expire)) > now:
            return 200, {"parameter": params[0]}

        LOGGER.info("Parameter %s of resource %s expired.", param_id, resource_id)
        out = yield self.agentmanager._request_parameter(env.id, resource_id)
        return out

    @gen.coroutine
    def _update_param(self, env, name, value, source, resource_id, metadata, recompile=False):
        """
            Update or set a parameter.

            This method returns true if:
            - this update resolves an unknown
            - recompile is true and the parameter updates an existing parameter to a new value
        """
        LOGGER.debug("Updating/setting parameter %s in env %s (for resource %s)", name, env.id, resource_id)
        if not isinstance(value, str):
            value = str(value)

        if value is None or value == "":
            value = " "

        if resource_id is None:
            resource_id = ""

        params = yield data.Parameter.get_list(environment=env.id, name=name, resource_id=resource_id)

        value_updated = True
        if len(params) == 0:
            param = data.Parameter(environment=env.id, name=name, resource_id=resource_id, value=value, source=source,
                                   updated=datetime.datetime.now(), metadata=metadata)
            yield param.insert()
        else:
            param = params[0]
            value_updated = param.value != value
            yield param.update(source=source, value=value, updated=datetime.datetime.now(), metadata=metadata)

        # check if the parameter is an unknown
        params = yield data.UnknownParameter.get_list(environment=env.id, name=name, resource_id=resource_id, resolved=False)
        if len(params) > 0:
            LOGGER.info("Received values for unknown parameters %s, triggering a recompile",
                        ", ".join([x.name for x in params]))
            for p in params:
                yield p.update_fields(resolved=True)

            return True

        return (recompile and value_updated)

    @protocol.handle(methods.ParameterMethod.set_param, param_id="id", env="tid")
    @gen.coroutine
    def set_param(self, env, param_id, source, value, resource_id, metadata, recompile):
        result = yield self._update_param(env, param_id, value, source, resource_id, metadata, recompile)
        if result:
            compile_metadata = {
                "message": "Recompile model because one or more parameters were updated",
                "type": "param",
                "params": [(param_id, resource_id)],
            }
            yield self._async_recompile(env, False, opt.server_wait_after_param.get(), metadata=compile_metadata)

        if resource_id is None:
            resource_id = ""

        params = yield data.Parameter.get_list(environment=env.id, name=param_id, resource_id=resource_id)

        return 200, {"parameter": params[0]}

    @protocol.handle(methods.ParametersMethod.set_parameters, env="tid")
    @gen.coroutine
    def set_parameters(self, env, parameters):
        recompile = False
        compile_metadata = {
            "message": "Recompile model because one or more parameters were updated",
            "type": "param",
            "params": []
        }
        for param in parameters:
            name = param["id"]
            source = param["source"]
            value = param["value"] if "value" in param else None
            resource_id = param["resource_id"] if "resource_id" in param else None
            metadata = param["metadata"] if "metadata" in param else None

            result = yield self._update_param(env, name, value, source, resource_id, metadata)
            if result:
                recompile = True
                compile_metadata["params"].append((name, resource_id))

        if recompile:
            yield self._async_recompile(env, False, opt.server_wait_after_param.get(), metadata=compile_metadata)

        return 200

    @protocol.handle(methods.ParameterMethod.delete_param, env="tid", parameter_name="id")
    @gen.coroutine
    def delete_param(self, env, parameter_name, resource_id):
        if resource_id is None:
            params = yield data.Parameter.get_list(environment=env.id, name=parameter_name)
        else:
            params = yield data.Parameter.get_list(environment=env.id, name=parameter_name, resource_id=resource_id)

        if len(params) == 0:
            return 404

        param = params[0]
        yield param.delete()
        metadata = {
            "message": "Recompile model because one or more parameters were deleted",
            "type": "param",
            "params": [(param.name, param.resource_id)]
        }
        yield self._async_recompile(env, False, opt.server_wait_after_param.get(), metadata=metadata)

        return 200

    @protocol.handle(methods.ParameterMethod.list_params, env="tid")
    @gen.coroutine
    def list_param(self, env, query):
        m_query = {"environment": env.id}
        for k, v in query.items():
            m_query["metadata." + k] = v

        params = yield data.Parameter.get_list(**m_query)
        return 200, {"parameters": params, "expire": self._fact_expire, "now": datetime.datetime.now().isoformat()}

    @protocol.handle(methods.FormMethod.put_form, form_id="id", env="tid")
    @gen.coroutine
    def put_form(self, env: uuid.UUID, form_id: str, form: dict):
        form_doc = yield data.Form.get_form(environment=env.id, form_type=form_id)
        fields = {k: v["type"] for k, v in form["attributes"].items()}
        defaults = {k: v["default"] for k, v in form["attributes"].items() if "default" in v}
        field_options = {k: v["options"] for k, v in form["attributes"].items() if "options" in v}

        if form_doc is None:
            form_doc = data.Form(environment=env.id, form_type=form_id, fields=fields,
                                 defaults=defaults, options=form["options"],
                                 field_options=field_options)
            yield form_doc.insert()

        else:
            # update the definition
            form_doc.fields = fields
            form_doc.defaults = defaults
            form_doc.options = form["options"]
            form_doc.field_options = field_options

            yield form_doc.update()

        return 200, {"form": {"id": form_doc.id}}

    @protocol.handle(methods.FormMethod.get_form, form_id="id", env="tid")
    @gen.coroutine
    def get_form(self, env, form_id):
        form = yield data.Form.get_form(environment=env.id, form_type=form_id)

        if form is None:
            return 404

        return 200, {"form": form}

    @protocol.handle(methods.FormMethod.list_forms, env="tid")
    @gen.coroutine
    def list_forms(self, env):
        forms = yield data.Form.get_list(environment=env.id)
        return 200, {"forms": [{"form_id": x.id, "form_type": x.form_type} for x in forms]}

    @protocol.handle(methods.FormRecords.list_records, env="tid")
    @gen.coroutine
    def list_records(self, env, form_type, include_record):
        form_type = yield data.Form.get_form(environment=env.id, form_type=form_type)
        if form_type is None:
            return 404, {"message": "No form is defined with id %s" % form_type}

        records = yield data.FormRecord.get_list(form=form_type.id)

        if not include_record:
            return 200, {"records": [{"id": r.id, "changed": r.changed} for r in records]}

        else:
            return 200, {"records": records}

    @protocol.handle(methods.FormRecords.get_record, record_id="id", env="tid")
    @gen.coroutine
    def get_record(self, env, record_id):
        record = yield data.FormRecord.get_by_id(record_id)
        if record is None:
            return 404, {"message": "The record with id %s does not exist" % record_id}

        return 200, {"record": record}

    @protocol.handle(methods.FormRecords.update_record, record_id="id", env="tid")
    @gen.coroutine
    def update_record(self, env, record_id, form):
        record = yield data.FormRecord.get_by_id(record_id)
        form_def = yield data.Form.get_by_id(record.form)
        record.changed = datetime.datetime.now()

        for k, _v in form_def.fields.items():
            if k in form_def.fields and k in form:
                value = form[k]
                field_type = form_def.fields[k]
                if field_type in type.TYPES:
                    type_obj = type.TYPES[field_type]
                    record.fields[k] = type_obj.cast(value)
                else:
                    LOGGER.warning("Field %s in record %s of form %s has an invalid type." % (k, record_id, form))

        yield record.update()

        metadata = {
            "message": "Recompile model because a form record was updated",
            "type": "form",
            "records": [str(record_id)],
            "form": form
        }

        yield self._async_recompile(env, False, opt.server_wait_after_param.get(), metadata=metadata)
        return 200, {"record": record}

    @protocol.handle(methods.FormRecords.create_record, env="tid")
    @gen.coroutine
    def create_record(self, env, form_type, form):
        form_obj = yield data.Form.get_form(environment=env.id, form_type=form_type)

        if form_obj is None:
            return 404, {"message": "The form %s does not exist in env %s" % (env.id, form_type)}

        record = data.FormRecord(environment=env.id, form=form_obj.id, fields={})
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
        metadata = {
            "message": "Recompile model because a form record was inserted",
            "type": "form",
            "records": [str(record.id)],
            "form": form
        }
        yield self._async_recompile(env, False, opt.server_wait_after_param.get(), metadata=metadata)

        return 200, {"record": record}

    @protocol.handle(methods.FormRecords.delete_record, record_id="id", env="tid")
    @gen.coroutine
    def delete_record(self, env, record_id):
        record = yield data.FormRecord.get_by_id(record_id)
        yield record.delete()

        metadata = {
            "message": "Recompile model because a form record was removed",
            "type": "form",
            "records": [str(record.id)],
            "form": record.form
        }
        yield self._async_recompile(env, False, opt.server_wait_after_param.get(), metadata=metadata)

        return 200

    @protocol.handle(methods.FileMethod.upload_file, file_hash="id")
    @gen.coroutine
    def upload_file(self, file_hash, content):
        content = base64.b64decode(content)
        return self.upload_file_internal(file_hash, content)

    def upload_file_internal(self, file_hash, content):
        file_name = os.path.join(self._server_storage["files"], file_hash)

        if os.path.exists(file_name):
            return 500, {"message": "A file with this id already exists."}

        if hash_file(content) != file_hash:
            return 400, {"message": "The hash does not match the content"}

        with open(file_name, "wb+") as fd:
            fd.write(content)

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
        ret, c = self.get_file_internal(file_hash)
        if ret == 200:
            return 200, {"content": base64.b64encode(c).decode("ascii")}
        else:
            return ret, c

    def get_file_internal(self, file_hash):
        """get_file, but on return code 200, content is not encoded """

        file_name = os.path.join(self._server_storage["files"], file_hash)

        if not os.path.exists(file_name):
            return 404

        else:
            with open(file_name, "rb") as fd:
                content = fd.read()
                actualhash = hash_file(content)
                if actualhash != file_hash:
                    if opt.server_delete_currupt_files.get():
                        LOGGER.error("File corrupt, expected hash %s but found %s at %s, Deleting file" %
                                     (file_hash, actualhash, file_name))
                        try:
                            os.remove(file_name)
                        except OSError:
                            LOGGER.exception("Failed to delete file %s" % (file_name))
                            return 500, {"message": ("File corrupt, expected hash %s but found %s,"
                                                     " Failed to delete file, please contact the server administrator"
                                                     ) % (file_hash, actualhash)}
                        return 500, {"message": ("File corrupt, expected hash %s but found %s, "
                                                 "Deleting file, please re-upload the corrupt file"
                                                 ) % (file_hash, actualhash)}
                    else:
                        LOGGER.error("File corrupt, expected hash %s but found %s at %s" % (file_hash, actualhash, file_name))
                        return 500, {"message": ("File corrupt, expected hash %s but found %s,"
                                                 " please contact the server administrator") % (file_hash, actualhash)}
                return 200, content

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

    @protocol.handle(methods.ServerAgentApiMethod.trigger_agent, agent_id="id", env="tid")
    @gen.coroutine
    def trigger_agent(self, env, agent_id):
        yield self.agentmanager.trigger_agent(env.id, agent_id)

    @protocol.handle(methods.NodeMethod.list_agent_processes)
    @gen.coroutine
    def list_agent_processes(self, environment, expired):
        if environment is not None:
            env = yield data.Environment.get_by_id(environment)
            if env is None:
                return 404, {"message": "The given environment id does not exist!"}

        return (yield self.agentmanager.list_agent_processes(environment, expired))

    @protocol.handle(methods.ServerAgentApiMethod.list_agents, env="tid")
    @gen.coroutine
    def list_agents(self, env):
        return (yield self.agentmanager.list_agents(env.id))

    @protocol.handle(methods.AgentRecovery.get_state, env="tid")
    @gen.coroutine
    def get_state(self, env: uuid.UUID, sid: uuid.UUID, agent: str):
        return (yield self.agentmanager.get_state(env.id, sid, agent))

    @protocol.handle(methods.ResourceMethod.get_resource, resource_id="id", env="tid")
    @gen.coroutine
    def get_resource(self, env, resource_id, logs, status, log_action, log_limit):
        resv = yield data.Resource.get(env.id, resource_id)
        if resv is None:
            return 404, {"message": "The resource with the given id does not exist in the given environment"}

        if status is not None and status:
            return 200, {"status": resv.status}

        actions = []
        if bool(logs):
            action_name = None
            if log_action is not None:
                action_name = log_action.name
            actions = yield data.ResourceAction.get_log(environment=env.id, resource_version_id=resource_id,
                                                        action=action_name, limit=log_limit)

        return 200, {"resource": resv, "logs": actions}

    @protocol.handle(methods.ResourceMethod.get_resources_for_agent, env="tid")
    @gen.coroutine
    def get_resources_for_agent(self, env, agent, version):
        started = datetime.datetime.now()
        if version is None:
            cm = yield data.ConfigurationModel.get_latest_version(env.id)
            if cm is None:
                return 404, {"message": "No version available"}

            version = cm.version

        else:
            cm = yield data.ConfigurationModel.get_version(environment=env.id, version=version)
            if cm is None:
                return 404, {"message": "The given version does not exist"}

        deploy_model = []

        resources = yield data.Resource.get_resources_for_version(env.id, version, agent)

        resource_ids = []
        for rv in resources:
            deploy_model.append(rv.to_dict())
            resource_ids.append(rv.resource_version_id)

        now = datetime.datetime.now()
        ra = data.ResourceAction(environment=env.id, resource_version_ids=resource_ids, action=const.ResourceAction.pull,
                                 action_id=uuid.uuid4(), started=started, finished=now,
                                 messages=[data.LogLine.log(logging.INFO,
                                                            "Resource version pulled by client for agent %(agent)s state",
                                                            agent=agent)])
        yield ra.insert()

        return 200, {"environment": env.id, "agent": agent, "version": version, "resources": deploy_model}

    @protocol.handle(methods.VersionMethod.list_versions, env="tid")
    @gen.coroutine
    def list_version(self, env, start=None, limit=None):
        if (start is None and limit is not None) or (limit is None and start is not None):
            return 500, {"message": "Start and limit should always be set together."}

        if start is None:
            start = 0
            limit = data.DBLIMIT

        models = yield data.ConfigurationModel.get_versions(env.id, start, limit)
        count = len(models)

        d = {"versions": models}

        if start is not None:
            d["start"] = start
            d["limit"] = limit

        d["count"] = count

        return 200, d

    @protocol.handle(methods.VersionMethod.get_version, version_id="id", env="tid")
    @gen.coroutine
    def get_version(self, env, version_id, include_logs=None, log_filter=None, limit=0):
        version = yield data.ConfigurationModel.get_version(env.id, version_id)
        if version is None:
            return 404, {"message": "The given configuration model does not exist yet."}

        resources = yield data.Resource.get_resources_for_version(env.id, version_id, include_attributes=True, no_obj=True)
        if resources is None:
            return 404, {"message": "The given configuration model does not exist yet."}

        d = {"model": version}

        d["resources"] = []
        for res_dict in resources:
            if bool(include_logs):
                res_dict["actions"] = yield data.ResourceAction.get_log(env.id, res_dict["resource_version_id"],
                                                                        log_filter, limit)

            d["resources"].append(res_dict)

        d["unknowns"] = yield data.UnknownParameter.get_list(environment=env.id, version=version_id)

        return 200, d

    @protocol.handle(methods.VersionMethod.delete_version, version_id="id", env="tid")
    @gen.coroutine
    def delete_version(self, env, version_id):
        version = yield data.ConfigurationModel.get_version(env.id, version_id)
        if version is None:
            return 404, {"message": "The given configuration model does not exist yet."}

        yield version.delete_cascade()
        return 200

    @protocol.handle(methods.VersionMethod.put_version, env="tid")
    @gen.coroutine
    def put_version(self, env, version, resources, resource_state, unknowns, version_info):
        started = datetime.datetime.now()
        try:
            cm = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(),
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
        resource_version_ids = []
        for res_dict in resources:
            res_obj = data.Resource.new(env.id, res_dict["id"])
            if res_obj.resource_id in resource_state:
                res_obj.status = const.ResourceState[resource_state[res_obj.resource_id]]

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
            resource_version_ids.append(res_obj.resource_version_id)

            rv_dict[res_obj.resource_id] = res_obj

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
            res_obj = rv_dict[t.resource_str()]
            res_obj.provides.append(f.resource_version_id)

        # search for deleted resources
        resources_to_purge = yield data.Resource.get_deleted_resources(env.id, version, set(rv_dict.keys()))
        previous_requires = {}
        for res in resources_to_purge:
            LOGGER.warning("Purging %s, purged resource based on %s" % (res.resource_id, res.resource_version_id))

            attributes = res.attributes.copy()
            attributes["purged"] = "true"
            attributes["requires"] = []

            res_obj = data.Resource.new(env.id, resource_version_id="%s,v=%s" % (res.resource_id, version),
                                        attributes=attributes)
            resource_objects.append(res_obj)

            previous_requires[res_obj.resource_id] = res.attributes["requires"]
            resource_version_ids.append(res_obj.resource_version_id)
            agents.add(res_obj.agent)
            rv_dict[res_obj.resource_id] = res_obj

        # invert dependencies on purges
        for res_id, requires in previous_requires.items():
            res_obj = rv_dict[res_id]
            for require in requires:
                req_id = Id.parse_id(require)

                if req_id.resource_str() in rv_dict:
                    req_res = rv_dict[req_id.resource_str()]

                    req_res.attributes["requires"].append(res_obj.resource_version_id)
                    res_obj.provides.append(req_res.resource_version_id)

        yield data.Resource.insert_many(resource_objects)
        yield cm.update_fields(total=cm.total + len(resources_to_purge))

        for uk in unknowns:
            if "resource" not in uk:
                uk["resource"] = ""

            if "metadata" not in uk:
                uk["metadata"] = {}

            up = data.UnknownParameter(resource_id=uk["resource"], name=uk["parameter"],
                                       source=uk["source"], environment=env.id,
                                       version=version, metadata=uk["metadata"])
            yield up.insert()

        for agent in agents:
            yield self.agentmanager.ensure_agent_registered(env, agent)

        ra = data.ResourceAction(environment=env.id, resource_version_ids=resource_version_ids, action_id=uuid.uuid4(),
                                 action=const.ResourceAction.store, started=started, finished=datetime.datetime.now(),
                                 messages=[data.LogLine.log(logging.INFO, "Successfully stored version %(version)d",
                                                            version=version)])
        yield ra.insert()
        LOGGER.debug("Successfully stored version %d", version)

        auto_deploy = yield env.get(data.AUTO_DEPLOY)
        if auto_deploy:
            LOGGER.debug("Auto deploying version %d", version)
            push = yield env.get(data.PUSH_ON_AUTO_DEPLOY)
            yield self.release_version(env, version, push)

        return 200

    @protocol.handle(methods.VersionMethod.release_version, version_id="id", env="tid")
    @gen.coroutine
    def release_version(self, env, version_id, push):
        model = yield data.ConfigurationModel.get_version(env.id, version_id)
        if model is None:
            return 404, {"message": "The request version does not exist."}

        yield model.update_fields(released=True, result=const.VersionState.deploying)

        # Already mark undeployable resources as deployed to create a better UX (change the version counters)
        resources = yield data.Resource.get_undeployable(env.id, version_id)

        now = datetime.datetime.now()
        for res in resources:
            yield self.resource_action_update(env, [res.resource_version_id], action_id=uuid.uuid4(), started=now,
                                              finished=now, status=res.status, action=const.ResourceAction.deploy,
                                              changes={}, messages=[], change=const.Change.nochange, send_events=False)

            # Skip all resources that depend on this undepoyable resource
            requires = yield data.Resource.get_requires(env.id, version_id, res.resource_version_id)
            yield self.resource_action_update(env, [r.resource_version_id for r in requires], action_id=uuid.uuid4(),
                                              started=now, finished=now, status=const.ResourceState.skipped,
                                              action=const.ResourceAction.deploy, changes={}, messages=[],
                                              change=const.Change.nochange, send_events=False)

        if push:
            # fetch all resource in this cm and create a list of distinct agents
            agents = yield data.ConfigurationModel.get_agents(env.id, version_id)
            yield self.agentmanager._ensure_agents(env, agents)

            for agent in agents:
                client = self.get_agent_client(env.id, agent)
                if client is not None:
                    future = client.trigger(env.id, agent)
                    self.add_future(future)
                else:
                    LOGGER.warning("Agent %s from model %s in env %s is not available for a deploy", agent, version_id, env.id)

        return 200, {"model": model}

    @protocol.handle(methods.DryRunMethod.dryrun_request, version_id="id", env="tid")
    @gen.coroutine
    def dryrun_request(self, env, version_id):
        model = yield data.ConfigurationModel.get_version(environment=env.id, version=version_id)
        if model is None:
            return 404, {"message": "The request version does not exist."}

        # fetch all resource in this cm and create a list of distinct agents
        rvs = yield data.Resource.get_list(model=version_id, environment=env.id)

        # Create a dryrun document
        dryrun = yield data.DryRun.create(environment=env.id, model=version_id, todo=len(rvs), total=len(rvs))

        agents = yield data.ConfigurationModel.get_agents(env.id, version_id)
        yield self.agentmanager._ensure_agents(env, agents)

        for agent in agents:
            client = self.get_agent_client(env.id, agent)
            if client is not None:
                future = client.do_dryrun(env.id, dryrun.id, agent, version_id)
                self.add_future(future)
            else:
                LOGGER.warning("Agent %s from model %s in env %s is not available for a dryrun", agent, version_id, env.id)

        # Mark the resources in an undeployable state as done
        resources = yield data.Resource.get_undeployable(env.id, version_id)
        with (yield self.dryrun_lock.acquire()):
            for res in resources:
                payload = {"changes": {}, "id_fields": {"entity_type": res.resource_type, "agent_name": res.agent,
                                                        "attribute": res.id_attribute_name,
                                                        "attribute_value": res.id_attribute_value,
                                                        "version": res.model}, "id": res.resource_version_id}
                yield data.DryRun.update_resource(dryrun.id, res.resource_version_id, payload)

                # Also skip all resources that depend on this undepoyable resource
                requires = yield data.Resource.get_requires(env.id, version_id, res.resource_version_id)
                for req in requires:
                    payload = {"changes": {}, "id_fields": {"entity_type": req.resource_type, "agent_name": req.agent,
                                                            "attribute": req.id_attribute_name,
                                                            "attribute_value": req.id_attribute_value,
                                                            "version": req.model}, "id": req.resource_version_id}
                    yield data.DryRun.update_resource(dryrun.id, req.resource_version_id, payload)

        return 200, {"dryrun": dryrun}

    @protocol.handle(methods.DryRunMethod.dryrun_list, env="tid")
    @gen.coroutine
    def dryrun_list(self, env, version=None):
        query_args = {}
        query_args["environment"] = env.id
        if version is not None:
            model = yield data.ConfigurationModel.get_version(environment=env.id, version=version)
            if model is None:
                return 404, {"message": "The request version does not exist."}

            query_args["model"] = version

        dryruns = yield data.DryRun.get_list(**query_args)

        return 200, {"dryruns": [{"id": x.id, "version": x.model, "date": x.date, "total": x.total, "todo": x.todo}
                                 for x in dryruns]}

    @protocol.handle(methods.DryRunMethod.dryrun_report, dryrun_id="id", env="tid")
    @gen.coroutine
    def dryrun_report(self, env, dryrun_id):
        dryrun = yield data.DryRun.get_by_id(dryrun_id)
        if dryrun is None:
            return 404, {"message": "The given dryrun does not exist!"}

        return 200, {"dryrun": dryrun}

    @protocol.handle(methods.DryRunMethod.dryrun_update, dryrun_id="id", env="tid")
    @gen.coroutine
    def dryrun_update(self, env, dryrun_id, resource, changes):
        with (yield self.dryrun_lock.acquire()):
            payload = {"changes": changes, "id_fields": Id.parse_id(resource).to_dict(), "id": resource}
            yield data.DryRun.update_resource(dryrun_id, resource, payload)

        return 200

    @protocol.handle(methods.CodeMethod.upload_code, code_id="id", env="tid")
    @gen.coroutine
    def upload_code(self, env, code_id, resource, sources):
        code = yield data.Code.get_version(environment=env.id, version=code_id, resource=resource)
        if code is not None:
            return 500, {"message": "Code for this version has already been uploaded."}

        hasherrors = any((k != hash_file(content[2].encode()) for k, content in sources.items()))
        if hasherrors:
            return 400, {"message": "Hashes in source map do not match to source_code"}

        ret, to_upload = yield self.stat_files(sources.keys())

        if ret != 200:
            return ret, to_upload

        for file_hash in to_upload["files"]:
            ret = self.upload_file_internal(file_hash, sources[file_hash][2].encode())
            if ret != 200:
                return ret

        compact = {code_hash: (file_name, module, req) for code_hash, (file_name, module, _, req) in sources.items()}

        code = data.Code(environment=env.id, version=code_id, resource=resource, source_refs=compact, sources={})
        yield code.insert()

        return 200

    @protocol.handle(methods.CodeBatchedMethod.upload_code_batched, code_id="id", env="tid")
    @gen.coroutine
    def upload_code_batched(self, env, code_id, resources):
        # validate
        for rtype, sources in resources.items():
            if not isinstance(rtype, str):
                return 400, {"message": "all keys in the resources map must be strings"}
            if not isinstance(sources, dict):
                return 400, {"message": "all values in the resources map must be dicts"}
            for name, refs in sources.items():
                if not isinstance(name, str):
                    return 400, {"message": "all keys in the sources map must be strings"}
                if not isinstance(refs, (list, tuple)):
                    return 400, {"message": "all values in the sources map must be lists or tuple"}
                if len(refs) != 3 or\
                        not isinstance(refs[0], str) or \
                        not isinstance(refs[1], str) or \
                        not isinstance(refs[2], list):
                    return 400, {"message": "The values in the source map should be of the"
                                 " form (filename, module, [requirements])"}

        allrefs = [ref for sourcemap in resources.values() for ref in sourcemap.keys()]

        ret, val = yield self.stat_files(allrefs)

        if ret != 200:
            return ret, val

        if len(val["files"]) != 0:
            return 400, {"message": "Not all file references provided are valid", "references": val["files"]}

        code = yield data.Code.get_versions(environment=env.id, version=code_id)
        oldmap = {c.resource: c for c in code}

        new = {k: v for k, v in resources.items() if k not in oldmap}
        conflict = [k for k, v in resources.items() if k in oldmap and oldmap[k].source_refs != v]

        if len(conflict) > 0:
            return 500, {"message": "Some of these items already exists, but with different source files",
                         "references": conflict}

        newcodes = [data.Code(environment=env.id, version=code_id, resource=resource, source_refs=hashes)
                    for resource, hashes in new.items()]

        yield data.Code.insert_many(newcodes)

        return 200

    @protocol.handle(methods.CodeMethod.get_code, code_id="id", env="tid")
    @gen.coroutine
    def get_code(self, env, code_id, resource):
        code = yield data.Code.get_version(environment=env.id, version=code_id, resource=resource)
        if code is None:
            return 404, {"message": "The version of the code does not exist."}

        if code.sources is not None:
            sources = dict(code.sources)
        else:
            sources = {}

        if code.source_refs is not None:
            for code_hash, (file_name, module, req) in code.source_refs.items():
                ret, c = self.get_file_internal(code_hash)
                if ret != 200:
                    return ret, c
                sources[code_hash] = (file_name, module, c.decode(), req)

        return 200, {"version": code_id, "environment": env.id, "resource": resource, "sources": sources}

    @protocol.handle(methods.ResourceMethod.resource_action_update, env="tid")
    @gen.coroutine
    def resource_action_update(self, env, resource_ids, action_id, action, started, finished, status, messages, changes,
                               change, send_events):
        resources = yield data.Resource.get_resources(env.id, resource_ids)
        if len(resources) == 0 or (len(resources) != len(resource_ids)):
            return 404, {"message": "The resources with the given ids do not exist in the given environment. "
                         "Only %s of %s resources found." % (len(resources), len(resource_ids))}

        resource_action = yield data.ResourceAction.get(environment=env.id, action_id=action_id)
        if resource_action is None:
            if started is None:
                return 500, {"message": "A resource action can only be created with a start datetime."}

            resource_action = data.ResourceAction(environment=env.id, resource_version_ids=resource_ids,
                                                  action_id=action_id, action=action, started=started)
            yield resource_action.insert()

        if resource_action.finished is not None:
            return 500, {"message": "An resource action can only be updated when it has not been finished yet. This action "
                                    "finished at %s" % resource_action.finished}

        if len(messages) > 0:
            resource_action.add_logs(messages)

        if len(changes) > 0:
            resource_action.add_changes(changes)

        if status is not None:
            resource_action.set_field("status", status)

        if change is not None:
            resource_action.set_field("change", change)

        resource_action.set_field("send_event", send_events)

        done = False
        if finished is not None:
            # this resource has finished
            if status is None:
                return 500, {"message": "Cannot finish an action without a status."}

            resource_action.set_field("finished", finished)
            done = True

        yield resource_action.save()

        if done and action in const.STATE_UPDATE:
            model_version = None
            for res in resources:
                yield res.update_fields(last_deploy=finished, status=status)
                yield data.ConfigurationModel.set_ready(env.id, res.model, res.id, res.resource_id, status)
                model_version = res.model

                if "purged" in res.attributes and res.attributes["purged"] and status == const.ResourceState.deployed:
                    yield data.Parameter.delete_all(environment=env.id, resource_id=res.resource_id)

            model = yield data.ConfigurationModel.get_version(env.id, model_version)

            if model.done == model.total:
                result = const.VersionState.success
                for state in model.status.values():
                    if state["status"] != "deployed":
                        result = const.VersionState.failed

                yield model.update_fields(deployed=True, result=result)

            waiting_agents = set([(Id.parse_id(prov).get_agent_name(), res.resource_version_id)
                                  for res in resources for prov in res.provides])

            for agent, resource_id in waiting_agents:
                aclient = self.get_agent_client(env.id, agent)
                if aclient is not None:
                    yield aclient.resource_event(env.id, agent, resource_id, send_events, status, change, changes)

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
        if len(envs) > 0 and envs[0].id != environment_id:
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
            env_dict["versions"] = yield data.ConfigurationModel.get_versions(environment_id, limit=versions)

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

    @protocol.handle(methods.EnvironmentSettings.list_settings, env="tid")
    @gen.coroutine
    def list_settings(self, env: data.Environment):
        return 200, {"settings": env.settings, "metadata": data.Environment._settings}

    @gen.coroutine
    def _setting_change(self, env, key):
        setting = env._settings[key]
        if setting.recompile:
            LOGGER.info("Environment setting %s changed. Recompiling with update = %s", key, setting.update)
            metadata = {
                "message": "Recompile for modified setting",
                "type": "setting",
                "setting": key
            }
            yield self._async_recompile(env, setting.update, metadata=metadata)

        if setting.agent_restart:
            LOGGER.info("Environment setting %s changed. Restarting agents.", key)
            yield self.agentmanager.restart_agents(env)

    @protocol.handle(methods.EnvironmentSettings.set_setting, env="tid", key="id")
    @gen.coroutine
    def set_setting(self, env: data.Environment, key: str, value: str):
        try:
            yield env.set(key, value)
            yield self._setting_change(env, key)
            return 200
        except KeyError:
            return 404
        except ValueError:
            return 500, {"message": "Invalid value"}

    @protocol.handle(methods.EnvironmentSettings.get_setting, env="tid", key="id")
    @gen.coroutine
    def get_setting(self, env: data.Environment, key: str):
        try:
            value = yield env.get(key)
            return 200, {"value": value, "metadata": data.Environment._settings}
        except KeyError:
            return 404

    @protocol.handle(methods.EnvironmentSettings.delete_setting, env="tid", key="id")
    @gen.coroutine
    def delete_setting(self, env: data.Environment, key: str):
        try:
            yield env.unset(key)
            yield self._setting_change(env, key)
            return 200
        except KeyError:
            return 404

    @protocol.handle(methods.NotifyMethod.is_compiling, environment_id="id")
    @gen.coroutine
    def is_compiling(self, environment_id):
        if self._recompiles[environment_id] is self:
            return 200

        return 204

    @protocol.handle(methods.NotifyMethod.notify_change_get, env="id")
    @gen.coroutine
    def notify_change_get(self, env, update):
        result = yield self.notify_change(env, update, {})
        return result

    @protocol.handle(methods.NotifyMethod.notify_change, env="id")
    @gen.coroutine
    def notify_change(self, env, update, metadata):
        LOGGER.info("Received change notification for environment %s", env.id)
        if "type" not in metadata:
            metadata["type"] = "api"

        if "message" not in metadata:
            metadata["message"] = "Recompile trigger through API call"

        yield self._async_recompile(env, update, metadata=metadata)

        return 200

    @gen.coroutine
    def _async_recompile(self, env, update_repo, wait=0, metadata={}):
        """
            Recompile an environment in a different thread and taking wait time into account.
        """
        server_compile = yield env.get(data.SERVER_COMPILE)
        if not server_compile:
            LOGGER.info("Skipping compile because server compile not enabled for this environment.")
            return

        last_recompile = self._recompiles[env.id]
        wait_time = opt.server_autrecompile_wait.get()
        if last_recompile is self:
            LOGGER.info("Already recompiling")
            return

        if last_recompile is None or (datetime.datetime.now() - datetime.timedelta(0, wait_time)) > last_recompile:
            if last_recompile is None:
                LOGGER.info("First recompile")
            else:
                LOGGER.info("Last recompile longer than %s ago (last was at %s)", wait_time, last_recompile)

            self._recompiles[env.id] = self
            self._io_loop.add_callback(self._recompile_environment, env.id, update_repo, wait, metadata)
        else:
            LOGGER.info("Not recompiling, last recompile less than %s ago (last was at %s)", wait_time, last_recompile)

    @gen.coroutine
    def _run_compile_stage(self, name, cmd, cwd, **kwargs):
        start = datetime.datetime.now()

        try:
            out = tempfile.NamedTemporaryFile()
            err = tempfile.NamedTemporaryFile()
            sub_process = process.Subprocess(cmd, stdout=out, stderr=err, cwd=cwd, **kwargs)

            returncode = yield sub_process.wait_for_exit(raise_error=False)
            sub_process.uninitialize()

            out.seek(0)
            err.seek(0)

            stop = datetime.datetime.now()
            return data.Report(started=start, completed=stop, name=name, command=" ".join(cmd),
                               errstream=err.read().decode(), outstream=out.read().decode(), returncode=returncode)

        finally:
            out.close()
            err.close()

    @gen.coroutine
    def _recompile_environment(self, environment_id, update_repo=False, wait=0, metadata={}):
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
            inmanta_path = [sys.executable, "-m", "inmanta.app"]
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
            LOGGER.debug("Verifying correct branch")
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
            cmd = inmanta_path + ["-vvv", "export", "-e", str(environment_id), "--server_address", server_address,
                                  "--server_port", opt.transport_port.get(), "--metadata", json.dumps(metadata)]
            if config.Config.get("server", "auth", False):
                token = protocol.encode_token(["compiler", "api"], str(environment_id))
                cmd.append("--token")
                cmd.append(token)

            if opt.server_ssl_cert.get() is not None:
                cmd.append("--ssl")

            if opt.server_ssl_ca_cert.get() is not None:
                cmd.append("--ssl-ca-cert")
                cmd.append(opt.server_ssl_ca_cert.get())

            result = yield self._run_compile_stage("Recompiling configuration model", cmd, project_dir, env=os.environ.copy())

            stages.append(result)
        except Exception:
            LOGGER.exception("An error occured while recompiling")
        finally:
            end = datetime.datetime.now()
            self._recompiles[environment_id] = end

            comp = data.Compile(environment=environment_id, started=requested, completed=end)

            for stage in stages:
                stage.compile = comp.id

            yield data.Report.insert_many(stages)
            yield comp.insert()

    @protocol.handle(methods.CompileReport.get_reports, env="tid")
    @gen.coroutine
    def get_reports(self, env, start=None, end=None, limit=None):
        argscount = len([x for x in [start, end, limit] if x is not None])
        if argscount == 3:
            return 500, {"message": "Limit, start and end can not be set together"}

        queryparts = {}

        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        queryparts["environment"] = env.id

        if start is not None:
            queryparts["started"] = {"$gt": dateutil.parser.parse(start)}

        if end is not None:
            queryparts["started"] = {"$lt": dateutil.parser.parse(end)}

        models = yield data.Compile.get_reports(queryparts, limit, start, end)

        return 200, {"reports": models}

    @protocol.handle(methods.CompileReport.get_report, compile_id="id")
    @gen.coroutine
    def get_report(self, compile_id):
        report = yield data.Compile.get_report(compile_id)

        if report is None:
            return 404

        return 200, {"report": report}

    @protocol.handle(methods.Snapshot.list_snapshots, env="tid")
    @gen.coroutine
    def list_snapshots(self, env):
        snapshots = yield data.Snapshot.get_list(environment=env.id)
        return 200, {"snapshots": snapshots}

    @protocol.handle(methods.Snapshot.get_snapshot, snapshot_id="id", env="tid")
    @gen.coroutine
    def get_snapshot(self, env, snapshot_id):
        snapshot = yield data.Snapshot.get_by_id(snapshot_id)
        if snapshot is None:
            return 404, {"message": "The given snapshot id does not exist!"}
        snap_dict = snapshot.to_dict()

        resources = yield data.ResourceSnapshot.get_list(snapshot=snapshot.id)
        snap_dict["resources"] = [r.to_dict() for r in resources]
        return 200, {"snapshot": snap_dict}

    @protocol.handle(methods.Snapshot.create_snapshot, env="tid")
    @gen.coroutine
    def create_snapshot(self, env, name):
        # get the latest deployed configuration model
        version = yield data.ConfigurationModel.get_latest_version(env.id)
        if version is None:
            return 500, {"message": "There is no deployed configuration model to create a snapshot."}

        LOGGER.info("Creating a snapshot from version %s in environment %s", version.version, env.id)

        # create the snapshot
        snapshot = data.Snapshot(environment=env.id, model=version.version, started=datetime.datetime.now(), name=name)
        yield snapshot.insert()

        # find resources with state
        resources_to_snapshot = defaultdict(list)
        resource_list = []
        resource_states = yield data.Resource.get_with_state(environment=env.id, version=version.version)

        for rs in resource_states:
            if rs.status not in const.UNDEPLOYABLE_STATES:
                agent = rs.agent
                resources_to_snapshot[agent].append(rs.to_dict())
                resource_list.append(rs.resource_id)
                r = data.ResourceSnapshot(environment=env.id, snapshot=snapshot.id, resource_id=rs.resource_id,
                                          state_id=rs.attributes["state_id"])
                yield r.insert()

        if len(resource_list) == 0:
            yield snapshot.update_fields(finished=datetime.datetime.now(), total_size=0)
        else:
            yield snapshot.update_fields(resources_todo=len(resource_list))

        for agent, resources in resources_to_snapshot.items():
            client = self.get_agent_client(env.id, agent)
            if client is not None:
                future = client.do_snapshot(env.id, agent, snapshot.id, resources)
                self.add_future(future)

        value = snapshot.to_dict()
        value["resources"] = resource_list
        return 200, {"snapshot": value}

    @protocol.handle(methods.Snapshot.update_snapshot, snapshot_id="id", env="tid")
    @gen.coroutine
    def update_snapshot(self, env, snapshot_id, resource_id, snapshot_data, start, stop, size, success, error, msg):
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

    @protocol.handle(methods.Snapshot.delete_snapshot, snapshot_id="id", env="tid")
    @gen.coroutine
    def delete_snapshot(self, env, snapshot_id):
        snapshot = yield data.Snapshot.get_by_id(snapshot_id)
        if snapshot is None:
            return 404, {"message": "Snapshot with id %s does not exist!" % snapshot_id}

        yield snapshot.delete_cascade()

        return 200

    @protocol.handle(methods.RestoreSnapshot.restore_snapshot, env="tid")
    @gen.coroutine
    def restore_snapshot(self, env, snapshot):
        snapshot = yield data.Snapshot.get_by_id(snapshot)

        if snapshot is None:
            return 404, {"message": "Snapshot with id %s does not exist!" % snapshot}

        # get all resources in the snapshot
        snap_resources = yield data.ResourceSnapshot.get_list(snapshot=snapshot.id)

        # get all resource that support state in the current environment
        env_version = yield data.ConfigurationModel.get_latest_version(env.id)
        if env_version is None:
            return 500, {"message": "There is no deployed configuration model in this environment."}

        env_resources = yield data.Resource.get_with_state(environment=env.id, version=env_version.version)
        env_states = {r.attributes["state_id"]: r for r in env_resources}

        # create a restore object
        restore = data.SnapshotRestore(snapshot=snapshot.id, environment=env.id, started=datetime.datetime.now())

        # find matching resources
        restore_list = defaultdict(list)
        todo = 0
        for r in snap_resources:
            if r.state_id in env_states:
                env_res = env_states[r.state_id]
                LOGGER.debug("Matching state_id %s to %s, scheduling restore" % (r.state_id, env_res.resource_id))
                restore_list[env_res.agent].append((r.to_dict(), env_res.to_dict()))

                rr = data.ResourceRestore(environment=env.id, restore=restore.id, state_id=r.state_id,
                                          resource_id=env_res.resource_version_id, started=datetime.datetime.now(),)
                yield rr.insert()
                todo += 1

        restore.resources_todo = todo
        yield restore.insert()

        for agent, resources in restore_list.items():
            client = self.get_agent_client(env.id, agent)
            if client is not None:
                future = client.do_restore(env.id, agent, restore.id, snapshot.id, resources)
                self.add_future(future)

        return 200, {"restore": restore}

    @protocol.handle(methods.RestoreSnapshot.list_restores, env="tid")
    @gen.coroutine
    def list_restores(self, env):
        restores = yield data.SnapshotRestore.get_list(environment=env.id)
        return 200, {"restores": restores}

    @protocol.handle(methods.RestoreSnapshot.get_restore_status, restore_id="id", env="tid")
    @gen.coroutine
    def get_restore_status(self, env, restore_id):
        restore = yield data.SnapshotRestore.get_by_id(restore_id)
        if restore is None:
            return 404, {"message": "The given restore id does not exist!"}

        restore_dict = restore.to_dict()
        resources = yield data.ResourceRestore.get_list(restore=restore_id)
        restore_dict["resources"] = [x.to_dict() for x in resources]
        return 200, {"restore": restore_dict}

    @protocol.handle(methods.RestoreSnapshot.update_restore, restore_id="id", env="tid")
    @gen.coroutine
    def update_restore(self, env, restore_id, resource_id, success, error, msg, start, stop):
        restore = yield data.SnapshotRestore.get_by_id(restore_id)
        rr = yield data.ResourceRestore.get_list(environment=env.id, restore=restore.id, resource_id=resource_id)
        if len(rr) == 0:
            return 404, {"message": "Resource restore not found."}
        rr = rr[0]

        yield rr.update_fields(error=error, success=success, started=start, finished=stop, msg=msg)
        yield restore.resource_updated()

        return 200

    @protocol.handle(methods.RestoreSnapshot.delete_restore, restore_id="id", env="tid")
    @gen.coroutine
    def delete_restore(self, env, restore_id):
        restore = yield data.SnapshotRestore.get_by_id(restore_id)
        if restore is None:
            return 404, {"message": "The given restore id does not exist!"}

        yield restore.delete()
        return 200

    @protocol.handle(methods.Decommision.decomission_environment, env="id")
    @gen.coroutine
    def decomission_environment(self, env, metadata):
        version = int(time.time())
        if metadata is None:
            metadata = {
                "message": "Decommission of environment",
                "type": "api"
            }
        result = yield self.put_version(env, version, [], {}, [], {"export_metadata": metadata})
        return result, {"version": version}

    @protocol.handle(methods.Decommision.clear_environment, env="id")
    @gen.coroutine
    def clear_environment(self, env):
        """
            Clear the environment
        """
        yield self.agentmanager.stop_agents(env)
        yield env.delete_cascade(only_content=True)
        return 200

    @protocol.handle(methods.EnvironmentAuth.create_token, env="tid")
    @gen.coroutine
    def create_token(self, env, client_types, idempotent):
        """
            Create a new auth token for this environment
        """
        return 200, {"token": protocol.encode_token(client_types, str(env.id), idempotent)}
