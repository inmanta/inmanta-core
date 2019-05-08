"""
    Copyright 2018 Inmanta

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
import os
import re
import logging
import sys
import tempfile
import time
from uuid import UUID
import uuid
import shutil
import json

import dateutil.parser
import asyncpg
from tornado import gen, locks, process, ioloop
from typing import Dict, Any, Generator

from inmanta import const
from inmanta import data, config
from inmanta.protocol.common import attach_warnings
from inmanta.protocol.exceptions import BadRequest
from inmanta.reporter import InfluxReporter
from inmanta.server import protocol, SLICE_SERVER
from inmanta.ast import type
from inmanta.resources import Id
from inmanta.server import config as opt
from inmanta.types import JsonType, Apireturn
from inmanta.util import hash_file
from inmanta.const import STATE_UPDATE, VALID_STATES_ON_STATE_UPDATE, TERMINAL_STATES, TRANSIENT_STATES
from inmanta.protocol import encode_token, methods

from typing import List, TYPE_CHECKING

LOGGER = logging.getLogger(__name__)
agent_lock = locks.Lock()

if TYPE_CHECKING:
    from inmanta.server.agentmanager import AgentManager

DBLIMIT = 100000


def error_and_log(message: str, **context) -> None:
    """
    :param message: message to return both to logger and to remote caller
    :param context: additional context to attach to log
    """
    ctx = ",".join([f"{k}: {v}" for k, v in context.items()])
    LOGGER.error("%s %s", message, ctx)
    raise BadRequest(message)


class ResourceActionLogLine(logging.LogRecord):
    """ A special log record that is used to report log lines that come from the agent
    """

    def __init__(self, logger_name: str, level: str, msg: str, created: datetime.datetime) -> None:
        super().__init__(
            name=logger_name,
            level=level,
            pathname="(unknown file)",
            lineno=0,
            msg=msg,
            args=[],
            exc_info=None,
            func=None,
            sinfo=None
        )

        self.created = created.timestamp()
        self.created = self.created
        self.msecs = (self.created - int(self.created)) * 1000
        self.relativeCreated = (self.created - logging._startTime) * 1000


class Server(protocol.ServerSlice):
    """
        The central Inmanta server that communicates with clients and agents and persists configuration
        information
    """

    def __init__(self, database_host=None, database_port=None, agent_no_log=False):
        super().__init__(name=SLICE_SERVER)
        LOGGER.info("Starting server endpoint")

        self._server_storage: Dict[str, str] = self.check_storage()
        self._agent_no_log: bool = agent_no_log

        self._recompiles = defaultdict(lambda: None)

        self.setup_dashboard()
        self.dryrun_lock = locks.Lock()
        self._fact_expire = opt.server_fact_expire.get()
        self._fact_renew = opt.server_fact_renew.get()
        self._database_host = database_host
        self._database_port = database_port

        self._resource_action_loggers: Dict[uuid.UUID, logging.Logger] = {}
        self._resource_action_handlers: Dict[uuid.UUID, logging.Handler] = {}

        self._increment_cache = {}
        # lock to ensure only one inflight request
        self._increment_cache_locks = defaultdict(lambda: locks.Lock())
        self._influx_db_reporter = None

    @gen.coroutine
    def prestart(self, server):
        self.agentmanager: "AgentManager" = server.get_slice("agentmanager")

    @gen.coroutine
    def start(self):
        if self._database_host is None:
            self._database_host = opt.db_host.get()

        if self._database_port is None:
            self._database_port = opt.db_port.get()

        database_username = opt.db_username.get()
        database_password = opt.db_password.get()
        yield data.connect(self._database_host, self._database_port, opt.db_name.get(), database_username, database_password)
        LOGGER.info("Connected to PostgreSQL database %s on %s:%d", opt.db_name.get(), self._database_host, self._database_port)

        self.schedule(self.renew_expired_facts, self._fact_renew)
        self.schedule(self._purge_versions, opt.server_purge_version_interval.get())
        self.schedule(data.ResourceAction.purge_logs, opt.server_purge_resource_action_logs_interval.get())

        ioloop.IOLoop.current().add_callback(self._purge_versions)

        self.start_metric_reporters()

        yield super().start()

    @gen.coroutine
    def stop(self):
        yield super().stop()
        self._close_resource_action_loggers()
        yield data.disconnect()
        self.stop_metric_reporters()

    def stop_metric_reporters(self) -> None:
        if self._influx_db_reporter:
            self._influx_db_reporter.stop()
            self._influx_db_reporter = None

    def start_metric_reporters(self) -> None:
        if opt.influxdb_host.get():
            self._influx_db_reporter = InfluxReporter(server=opt.influxdb_host.get(),
                                                      port=opt.influxdb_port.get(),
                                                      database=opt.influxdb_name.get(),
                                                      username=opt.influxdb_username.get(),
                                                      password=opt.influxdb_password,
                                                      reporting_interval=opt.influxdb_interval.get(),
                                                      autocreate_database=True,
                                                      tags=opt.influxdb_tags.get()
                                                      )
            self._influx_db_reporter.start()

    @staticmethod
    def get_resource_action_log_file(environment: uuid.UUID) -> str:
        """Get the correct filename for the given environment
        :param environment: The environment id to get the file for
        :return: The path to the logfile
        """
        return os.path.join(
            opt.log_dir.get(),
            opt.server_resource_action_log_prefix.get() + str(environment) + ".log"
        )

    def get_resource_action_logger(self, environment: uuid.UUID) -> logging.Logger:
        """Get the resource action logger for the given environment. If the logger was not created, create it.
        :param environment: The environment to get a logger for
        :return: The logger for the given environment.
        """
        if environment in self._resource_action_loggers:
            return self._resource_action_loggers[environment]

        resource_action_log = self.get_resource_action_log_file(environment)

        file_handler = logging.handlers.WatchedFileHandler(filename=resource_action_log, mode='a+')
        # Most logs will come from agents. We need to use their level and timestamp and their formatted message
        file_handler.setFormatter(logging.Formatter(fmt="%(message)s"))
        file_handler.setLevel(logging.DEBUG)

        resource_action_logger = logging.getLogger(const.NAME_RESOURCE_ACTION_LOGGER).getChild(str(environment))
        resource_action_logger.setLevel(logging.DEBUG)
        resource_action_logger.addHandler(file_handler)

        self._resource_action_loggers[environment] = resource_action_logger
        self._resource_action_handlers[environment] = file_handler

        return resource_action_logger

    def _close_resource_action_loggers(self) -> None:
        """Close all resource action loggers and their associated handlers"""
        try:
            while True:
                env, logger = self._resource_action_loggers.popitem()
                self._close_resource_action_logger(env, logger)
        except KeyError:
            pass

    def _close_resource_action_logger(self, env: uuid.UUID, logger: logging.Logger = None) -> None:
        """Close the given logger for the given env.
        :param env: The environment to close the logger for
        :param logger: The logger to close, if the logger is none it is retrieved
        """
        if logger is None:
            if env in self._resource_action_loggers:
                logger = self._resource_action_loggers.pop(env)
            else:
                return

        handler = self._resource_action_handlers.pop(env)
        logger.removeHandler(handler)
        handler.flush()
        handler.close()

    def log_resource_action(
        self, env: uuid.UUID, resource_ids: List[str], log_level: int, ts: datetime.datetime, message: str
    ) -> None:
        """Write the given log to the correct resource action logger"""
        logger = self.get_resource_action_logger(env)
        if len(resource_ids) == 0:
            message = "no resources: " + message
        elif len(resource_ids) > 1:
            message = "multiple resources: " + message
        else:
            message = resource_ids[0] + ": " + message
        log_record = ResourceActionLogLine(logger.name, log_level, message, ts)
        logger.handle(log_record)

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

        # LCM support should move to a server extension
        lcm = ""
        if opt.dash_lcm_enable.get():
            lcm = """,
    'lcm': '%s://' + window.location.hostname + ':8889/'
""" % ("https" if opt.server_ssl_key.get() else "http")

        content = """
angular.module('inmantaApi.config', []).constant('inmantaConfig', {
    'backend': window.location.origin+'/'%s
});
        """ % (lcm + auth)
        self.add_static_content("/dashboard/config.js", content=content)
        self.add_static_handler("/dashboard", dashboard_path, start=True)

    def clear_env_cache(self, env):
        LOGGER.log(const.LOG_LEVEL_TRACE, "Clearing cache for %s", env.id)
        self._increment_cache[env.id] = None

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
        def _ensure_directory_exist(directory, *subdirs):
            directory = os.path.join(directory, *subdirs)
            if not os.path.exists(directory):
                os.mkdir(directory)
            return directory

        state_dir = opt.state_dir.get()
        server_state_dir = os.path.join(state_dir, "server")
        dir_map = {"server": _ensure_directory_exist(state_dir, "server")}
        dir_map["files"] = _ensure_directory_exist(server_state_dir, "files")
        dir_map["environments"] = _ensure_directory_exist(server_state_dir, "environments")
        dir_map["agents"] = _ensure_directory_exist(server_state_dir, "agents")
        dir_map["logs"] = _ensure_directory_exist(opt.log_dir.get())
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

    @protocol.handle(methods.get_param, param_id="id", env="tid")
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

    @protocol.handle(methods.set_param, param_id="id", env="tid")
    @gen.coroutine
    def set_param(self, env, param_id, source, value, resource_id, metadata, recompile):
        result = yield self._update_param(env, param_id, value, source, resource_id, metadata, recompile)
        if result:
            compile_metadata = {
                "message": "Recompile model because one or more parameters were updated",
                "type": "param",
                "params": [(param_id, resource_id)],
            }
            yield self._async_recompile(env, False, metadata=compile_metadata)

        if resource_id is None:
            resource_id = ""

        params = yield data.Parameter.get_list(environment=env.id, name=param_id, resource_id=resource_id)

        return 200, {"parameter": params[0]}

    @protocol.handle(methods.set_parameters, env="tid")
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
            yield self._async_recompile(env, False, metadata=compile_metadata)

        return 200

    @protocol.handle(methods.delete_param, env="tid", parameter_name="id")
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
        yield self._async_recompile(env, False, metadata=metadata)

        return 200

    @protocol.handle(methods.list_params, env="tid")
    @gen.coroutine
    def list_param(self, env, query):
        params = yield data.Parameter.list_parameters(env.id, **query)
        return 200, {"parameters": params,
                     "expire": self._fact_expire,
                     "now": datetime.datetime.now().isoformat(timespec='microseconds')
                     }

    @protocol.handle(methods.put_form, form_id="id", env="tid")
    @gen.coroutine
    def put_form(self, env: data.Environment, form_id: str, form: dict):
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

        return 200, {"form": {"id": form_doc.form_type}}

    @protocol.handle(methods.get_form, form_id="id", env="tid")
    @gen.coroutine
    def get_form(self, env, form_id):
        form = yield data.Form.get_form(environment=env.id, form_type=form_id)

        if form is None:
            return 404

        return 200, {"form": form}

    @protocol.handle(methods.list_forms, env="tid")
    @gen.coroutine
    def list_forms(self, env):
        forms = yield data.Form.get_list(environment=env.id)
        return 200, {"forms": [{"form_id": x.form_type, "form_type": x.form_type} for x in forms]}

    @protocol.handle(methods.list_records, env="tid")
    @gen.coroutine
    def list_records(self, env, form_type, include_record):
        form_type = yield data.Form.get_form(environment=env.id, form_type=form_type)
        if form_type is None:
            return 404, {"message": "No form is defined with id %s" % form_type}

        records = yield data.FormRecord.get_list(form=form_type.form_type)

        if not include_record:
            return 200, {"records": [{"id": r.id, "changed": r.changed} for r in records]}

        else:
            return 200, {"records": records}

    @protocol.handle(methods.get_record, record_id="id", env="tid")
    @gen.coroutine
    def get_record(self, env, record_id):
        record = yield data.FormRecord.get_by_id(record_id)
        if record is None:
            return 404, {"message": "The record with id %s does not exist" % record_id}

        return 200, {"record": record}

    @protocol.handle(methods.update_record, record_id="id", env="tid")
    @gen.coroutine
    def update_record(self, env, record_id, form):
        record = yield data.FormRecord.get_by_id(record_id)
        if record is None:
            return 404, {"message": "The record with id %s does not exist" % record_id}
        if record.environment != env.id:
            return 404, {"message": "The record with id %s does not exist" % record_id}

        form_def = yield data.Form.get_one(environment=env.id, form_type=record.form)

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

        yield self._async_recompile(env, False, metadata=metadata)
        return 200, {"record": record}

    @protocol.handle(methods.create_record, env="tid")
    @gen.coroutine
    def create_record(self, env, form_type, form):
        form_obj = yield data.Form.get_form(environment=env.id, form_type=form_type)

        if form_obj is None:
            return 404, {"message": "The form %s does not exist in env %s" % (env.id, form_type)}

        record = data.FormRecord(environment=env.id, form=form_obj.form_type, fields={})
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
        yield self._async_recompile(env, False, metadata=metadata)

        return 200, {"record": record}

    @protocol.handle(methods.delete_record, record_id="id", env="tid")
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
        yield self._async_recompile(env, False, metadata=metadata)

        return 200

    @protocol.handle(methods.upload_file, file_hash="id")
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

    @protocol.handle(methods.stat_file, file_hash="id")
    @gen.coroutine
    def stat_file(self, file_hash):
        file_name = os.path.join(self._server_storage["files"], file_hash)

        if os.path.exists(file_name):
            return 200
        else:
            return 404

    @protocol.handle(methods.get_file, file_hash="id")
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
            return 404, None

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

    @protocol.handle(methods.stat_files)
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

    @protocol.handle(methods.diff)
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

    @protocol.handle(methods.get_resource, resource_id="id", env="tid")
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

            actions = yield data.ResourceAction.get_log(
                environment=env.id,
                resource_version_id=resource_id,
                action=action_name,
                limit=log_limit)

        return 200, {"resource": resv, "logs": actions}

    @protocol.handle(methods.get_resources_for_agent, env="tid")
    @gen.coroutine
    def get_resources_for_agent(self,
                                env: data.Environment,
                                agent: str,
                                version: str,
                                sid: uuid.UUID,
                                incremental_deploy: bool) -> Generator[Any, Any, JsonType]:

        if not self.agentmanager.is_primary(env, sid, agent):
            return 409, {"message": "This agent is not currently the primary for the endpoint %s (sid: %s)" % (agent, sid)}
        if incremental_deploy:
            if version is not None:
                return 500, {"message": "Cannot request increment for a specific version"}
            result = yield self.get_resource_increment_for_agent(env, agent)
        else:
            result = yield self.get_all_resources_for_agent(env, agent, version)
        return result

    @gen.coroutine
    def get_all_resources_for_agent(self, env: data.Environment, agent: str, version: str) -> Generator[Any, Any, JsonType]:
        started = datetime.datetime.now()
        if version is None:
            version = yield data.ConfigurationModel.get_version_nr_latest_version(env.id)
            if version is None:
                return 404, {"message": "No version available"}

        else:
            exists = yield data.ConfigurationModel.version_exists(environment=env.id, version=version)
            if not exists:
                return 404, {"message": "The given version does not exist"}

        deploy_model = []

        resources = yield data.Resource.get_resources_for_version(env.id, version, agent)

        resource_ids = []
        for rv in resources:
            deploy_model.append(rv.to_dict())
            resource_ids.append(rv.resource_version_id)

        now = datetime.datetime.now()

        log_line = data.LogLine.log(logging.INFO, "Resource version pulled by client for agent %(agent)s state", agent=agent)
        self.log_resource_action(env.id, resource_ids, logging.INFO, now, log_line.msg)
        ra = data.ResourceAction(environment=env.id, resource_version_ids=resource_ids, action=const.ResourceAction.pull,
                                 action_id=uuid.uuid4(), started=started, finished=now, messages=[log_line])
        yield ra.insert()

        return 200, {"environment": env.id, "agent": agent, "version": version, "resources": deploy_model}

    @gen.coroutine
    def get_resource_increment_for_agent(self, env: data.Environment, agent: str) -> Generator[Any, Any, JsonType]:
        started = datetime.datetime.now()

        version = yield data.ConfigurationModel.get_version_nr_latest_version(env.id)
        if version is None:
            return 404, {"message": "No version available"}

        increment = self._increment_cache.get(env.id, None)
        if increment is None:
            with (yield self._increment_cache_locks[env.id].acquire()):
                increment = self._increment_cache.get(env.id, None)
                if increment is None:
                    increment = yield data.ConfigurationModel.get_increment(env.id, version)
                    self._increment_cache[env.id] = increment

        increment_ids, neg_increment = increment

        # set already done to deployed
        now = datetime.datetime.now()

        def on_agent(res):
            idr = Id.parse_id(res)
            return idr.get_agent_name() == agent

        neg_increment = [res_id for res_id in neg_increment if on_agent(res_id)]

        logline = {
            "level": "INFO",
            "msg": "Setting deployed due to known good status",
            "timestamp": now.isoformat(timespec='microseconds'),
            "args": []
        }
        self.add_future(self.resource_action_update(env, neg_increment, action_id=uuid.uuid4(),
                                                    started=now, finished=now, status=const.ResourceState.deployed,
                                                    # does this require a different ResourceAction?
                                                    action=const.ResourceAction.deploy, changes={}, messages=[logline],
                                                    change=const.Change.nochange, send_events=False, keep_increment_cache=True))

        resources = yield data.Resource.get_resources_for_version(env.id, version, agent)

        deploy_model = []
        resource_ids = []
        for rv in resources:
            if rv.resource_version_id not in increment_ids:
                continue

            def in_requires(req):
                if req in increment_ids:
                    return True
                idr = Id.parse_id(req)
                return idr.get_agent_name() != agent

            rv.attributes["requires"] = [r for r in rv.attributes["requires"] if in_requires(r)]

            deploy_model.append(rv.to_dict())
            resource_ids.append(rv.resource_version_id)

        ra = data.ResourceAction(environment=env.id, resource_version_ids=resource_ids, action=const.ResourceAction.pull,
                                 action_id=uuid.uuid4(), started=started, finished=now,
                                 messages=[data.LogLine.log(logging.INFO,
                                                            "Resource version pulled by client for agent %(agent)s state",
                                                            agent=agent)])
        yield ra.insert()

        return 200, {"environment": env.id, "agent": agent, "version": version, "resources": deploy_model}

    @protocol.handle(methods.list_versions, env="tid")
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

    @protocol.handle(methods.get_version, version_id="id", env="tid")
    @gen.coroutine
    def get_version(self, env, version_id, include_logs=None, log_filter=None, limit=0):
        version = yield data.ConfigurationModel.get_version(env.id, version_id)
        if version is None:
            return 404, {"message": "The given configuration model does not exist yet."}

        resources = yield data.Resource.get_resources_for_version(env.id, version_id, no_obj=True)
        if resources is None:
            return 404, {"message": "The given configuration model does not exist yet."}

        d = {"model": version}

        # todo: batch get_log into single query?
        d["resources"] = []
        for res_dict in resources:
            if bool(include_logs):
                res_dict["actions"] = yield data.ResourceAction.get_log(
                    env.id,
                    res_dict["resource_version_id"],
                    log_filter,
                    limit)

            d["resources"].append(res_dict)

        d["unknowns"] = yield data.UnknownParameter.get_list(environment=env.id, version=version_id)

        return 200, d

    @protocol.handle(methods.delete_version, version_id="id", env="tid")
    @gen.coroutine
    def delete_version(self, env, version_id):
        version = yield data.ConfigurationModel.get_version(env.id, version_id)
        if version is None:
            return 404, {"message": "The given configuration model does not exist yet."}

        yield version.delete_cascade()
        return 200

    @protocol.handle(methods.put_version, env="tid")
    @gen.coroutine
    def put_version(self, env, version, resources, resource_state, unknowns, version_info):
        started = datetime.datetime.now()

        agents = set()
        # lookup for all RV's, lookup by resource id
        rv_dict = {}
        # reverse dependency tree, Resource.provides [:] -- Resource.requires as resource_id
        provides_tree = defaultdict(lambda: [])
        # list of all resources which have a cross agent dependency, as a tuple, (dependant,requires)
        cross_agent_dep = []
        # list of all resources which are undeployable
        undeployable = []

        resource_objects = []
        resource_version_ids = []
        for res_dict in resources:
            res_obj = data.Resource.new(env.id, res_dict["id"])
            if res_obj.resource_id in resource_state:
                res_obj.status = const.ResourceState[resource_state[res_obj.resource_id]]
                if res_obj.status in const.UNDEPLOYABLE_STATES:
                    undeployable.append(res_obj)

            # collect all agents
            agents.add(res_obj.agent)

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
            resc_id = res_obj.resource_id
            if "requires" not in attributes:
                LOGGER.warning("Received resource without requires attribute (%s)" % res_obj.resource_id)
            else:
                for req in attributes["requires"]:
                    rid = Id.parse_id(req)
                    provides_tree[rid.resource_str()].append(resc_id)
                    if rid.get_agent_name() != agent:
                        # it is a CAD
                        cross_agent_dep.append((res_obj, rid))

        # hook up all CADs
        for f, t in cross_agent_dep:
            res_obj = rv_dict[t.resource_str()]
            res_obj.provides.append(f.resource_version_id)

        # detect failed compiles
        def safe_get(input, key, default):
            if not isinstance(input, dict):
                return default
            if key not in input:
                return default
            return input[key]
        metadata = safe_get(version_info, const.EXPORT_META_DATA, {})
        compile_state = safe_get(metadata, const.META_DATA_COMPILE_STATE, "")
        failed = compile_state == const.Compilestate.failed.name

        resources_to_purge = []
        if not failed:
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

        undeployable = [res.resource_id for res in undeployable]
        # get skipped for undeployable
        work = list(undeployable)
        skippeable = set()
        while len(work) > 0:
            current = work.pop()
            if current in skippeable:
                continue
            skippeable.add(current)
            work.extend(provides_tree[current])

        skippeable = sorted(list(skippeable - set(undeployable)))

        try:
            cm = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(),
                                         total=len(resources), version_info=version_info, undeployable=undeployable,
                                         skipped_for_undeployable=skippeable)
            yield cm.insert()
        except asyncpg.exceptions.UniqueViolationError:
            return 500, {"message": "The given version is already defined. Versions should be unique."}

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

        now = datetime.datetime.now()
        log_line = data.LogLine.log(logging.INFO, "Successfully stored version %(version)d", version=version)
        self.log_resource_action(env.id, resource_version_ids, logging.INFO, now, log_line.msg)
        ra = data.ResourceAction(
            environment=env.id,
            resource_version_ids=resource_version_ids,
            action_id=uuid.uuid4(),
            action=const.ResourceAction.store,
            started=started,
            finished=now,
            messages=[log_line]
        )
        yield ra.insert()
        LOGGER.debug("Successfully stored version %d", version)

        self.clear_env_cache(env)

        auto_deploy = yield env.get(data.AUTO_DEPLOY)
        if auto_deploy:
            LOGGER.debug("Auto deploying version %d", version)
            push_on_auto_deploy = yield env.get(data.PUSH_ON_AUTO_DEPLOY)
            agent_trigger_method_on_autodeploy = yield env.get(data.AGENT_TRIGGER_METHOD_ON_AUTO_DEPLOY)
            agent_trigger_method_on_autodeploy = const.AgentTriggerMethod[agent_trigger_method_on_autodeploy]
            yield self.release_version(env, version, push_on_auto_deploy, agent_trigger_method_on_autodeploy)

        return 200

    @protocol.handle(methods.release_version, version_id="id", env="tid")
    @gen.coroutine
    def release_version(self, env, version_id, push, agent_trigger_method=None):
        model = yield data.ConfigurationModel.get_version(env.id, version_id)
        if model is None:
            return 404, {"message": "The request version does not exist."}

        yield model.update_fields(released=True, result=const.VersionState.deploying)

        if model.total == 0:
            yield model.mark_done()
            return 200, {"model": model}

        # Already mark undeployable resources as deployed to create a better UX (change the version counters)
        undep = yield model.get_undeployable()
        undep = [rid + ",v=%s" % version_id for rid in undep]

        now = datetime.datetime.now()

        # not checking error conditions
        yield self.resource_action_update(env, undep, action_id=uuid.uuid4(), started=now,
                                          finished=now, status=const.ResourceState.undefined,
                                          action=const.ResourceAction.deploy, changes={}, messages=[],
                                          change=const.Change.nochange, send_events=False)

        skippable = yield model.get_skipped_for_undeployable()
        skippable = [rid + ",v=%s" % version_id for rid in skippable]
        # not checking error conditions
        yield self.resource_action_update(env, skippable, action_id=uuid.uuid4(),
                                          started=now, finished=now, status=const.ResourceState.skipped_for_undefined,
                                          action=const.ResourceAction.deploy, changes={}, messages=[],
                                          change=const.Change.nochange, send_events=False)

        if push:
            # fetch all resource in this cm and create a list of distinct agents
            agents = yield data.ConfigurationModel.get_agents(env.id, version_id)
            yield self.agentmanager._ensure_agents(env, agents)

            for agent in agents:
                client = self.get_agent_client(env.id, agent)
                if client is not None:
                    if not agent_trigger_method:
                        # Ensure backward compatibility
                        incremental_deploy = False
                    else:
                        incremental_deploy = agent_trigger_method is const.AgentTriggerMethod.push_incremental_deploy
                    future = client.trigger(env.id, agent, incremental_deploy)
                    self.add_future(future)
                else:
                    LOGGER.warning("Agent %s from model %s in env %s is not available for a deploy", agent, version_id, env.id)

        return 200, {"model": model}

    @protocol.handle(methods.deploy, env="tid")
    @gen.coroutine
    def deploy(self,
               env: data.Environment,
               agent_trigger_method: const.AgentTriggerMethod = const.AgentTriggerMethod.push_full_deploy,
               agents: List[str] = None) -> Apireturn:
        warnings = []

        # get latest version
        version_id = yield data.ConfigurationModel.get_version_nr_latest_version(env.id)
        if version_id is None:
            return 404, {"message": "No version available"}

        # filter agents
        allagents = yield data.ConfigurationModel.get_agents(env.id, version_id)
        if agents is not None:
            required = set(agents)
            present = set(allagents)
            allagents = list(required.intersection(present))
            notfound = required - present
            if notfound:
                warnings.append(
                    "Model version %d does not contain agents named [%s]" % (
                        version_id,
                        ",".join(sorted(list(notfound)))
                    )
                )

        if not allagents:
            return attach_warnings(404, {"message": "No agent could be reached"}, warnings)

        present = set()
        absent = set()

        yield self.agentmanager._ensure_agents(env, allagents)

        for agent in allagents:
            client = self.get_agent_client(env.id, agent)
            if client is not None:
                incremental_deploy = agent_trigger_method is const.AgentTriggerMethod.push_incremental_deploy
                future = client.trigger(env.id, agent, incremental_deploy)
                self.add_future(future)
                present.add(agent)
            else:
                absent.add(agent)

        if absent:
            warnings.append("Could not reach agents named [%s]" % ",".join(sorted(list(absent))))

        if not present:
            return attach_warnings(404, {"message": "No agent could be reached"}, warnings)

        return attach_warnings(200, {"agents": sorted(list(present))}, warnings)

    @protocol.handle(methods.dryrun_request, version_id="id", env="tid")
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
        with (yield self.dryrun_lock.acquire()):
            undeployableids = yield model.get_undeployable()
            undeployableids = [rid + ",v=%s" % version_id for rid in undeployableids]
            undeployable = yield data.Resource.get_resources(environment=env.id,
                                                             resource_version_ids=undeployableids)
            for res in undeployable:
                parsed_id = Id.parse_id(res.resource_version_id)
                payload = {"changes": {}, "id_fields": {"entity_type": res.resource_type, "agent_name": res.agent,
                                                        "attribute": parsed_id.attribute,
                                                        "attribute_value": parsed_id.attribute_value,
                                                        "version": res.model}, "id": res.resource_version_id}
                yield data.DryRun.update_resource(dryrun.id, res.resource_version_id, payload)

            skipundeployableids = yield model.get_skipped_for_undeployable()
            skipundeployableids = [rid + ",v=%s" % version_id for rid in skipundeployableids]
            skipundeployable = yield data.Resource.get_resources(environment=env.id, resource_version_ids=skipundeployableids)
            for res in skipundeployable:
                parsed_id = Id.parse_id(res.resource_version_id)
                payload = {"changes": {}, "id_fields": {"entity_type": res.resource_type, "agent_name": res.agent,
                                                        "attribute": parsed_id.attribute,
                                                        "attribute_value": parsed_id.attribute_value,
                                                        "version": res.model}, "id": res.resource_version_id}
                yield data.DryRun.update_resource(dryrun.id, res.resource_version_id, payload)

        return 200, {"dryrun": dryrun}

    @protocol.handle(methods.dryrun_list, env="tid")
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

    @protocol.handle(methods.dryrun_report, dryrun_id="id", env="tid")
    @gen.coroutine
    def dryrun_report(self, env, dryrun_id):
        dryrun = yield data.DryRun.get_by_id(dryrun_id)
        if dryrun is None:
            return 404, {"message": "The given dryrun does not exist!"}

        return 200, {"dryrun": dryrun}

    @protocol.handle(methods.dryrun_update, dryrun_id="id", env="tid")
    @gen.coroutine
    def dryrun_update(self, env, dryrun_id, resource, changes):
        with (yield self.dryrun_lock.acquire()):
            payload = {"changes": changes, "id_fields": Id.parse_id(resource).to_dict(), "id": resource}
            yield data.DryRun.update_resource(dryrun_id, resource, payload)

        return 200

    @protocol.handle(methods.upload_code, code_id="id", env="tid")
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

        code = data.Code(environment=env.id, version=code_id, resource=resource, source_refs=compact)
        yield code.insert()

        return 200

    @protocol.handle(methods.upload_code_batched, code_id="id", env="tid")
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

    @protocol.handle(methods.get_code, code_id="id", env="tid")
    @gen.coroutine
    def get_code(self, env, code_id, resource):
        code = yield data.Code.get_version(environment=env.id, version=code_id, resource=resource)
        if code is None:
            return 404, {"message": "The version of the code does not exist."}

        sources = {}
        if code.source_refs is not None:
            for code_hash, (file_name, module, req) in code.source_refs.items():
                ret, c = self.get_file_internal(code_hash)
                if ret != 200:
                    return ret, c
                sources[code_hash] = (file_name, module, c.decode(), req)

        return 200, {"version": code_id, "environment": env.id, "resource": resource, "sources": sources}

    @protocol.handle(methods.resource_action_update, env="tid")
    @gen.coroutine
    def resource_action_update(self, env, resource_ids, action_id, action, started, finished, status, messages, changes,
                               change, send_events, keep_increment_cache=False):
        # can update resource state
        is_resource_state_update = action in STATE_UPDATE
        # this ra is finishing
        is_resource_action_finished = finished is not None

        if is_resource_state_update:
            # if status update, status is required
            if status is None:
                error_and_log("Cannot perform state update without a status.",
                              resource_ids=resource_ids,
                              action=action,
                              action_id=action_id)
            # and needs to be valid
            if status not in VALID_STATES_ON_STATE_UPDATE:
                error_and_log("Status %s is not valid on action %s" % (status, action),
                              resource_ids=resource_ids,
                              action=action,
                              action_id=action_id
                              )
            if status in TRANSIENT_STATES:
                if not is_resource_action_finished:
                    pass
                else:
                    error_and_log("The finished field must not be set for transient states",
                                  status=status,
                                  resource_ids=resource_ids,
                                  action=action,
                                  action_id=action_id)
            else:
                if is_resource_action_finished:
                    pass
                else:
                    error_and_log("The finished field must be set for none transient states",
                                  status=status,
                                  resource_ids=resource_ids,
                                  action=action,
                                  action_id=action_id)

        # validate resources
        resources = yield data.Resource.get_resources(env.id, resource_ids)
        if len(resources) == 0 or (len(resources) != len(resource_ids)):
            return 404, {"message": "The resources with the given ids do not exist in the given environment. "
                         "Only %s of %s resources found." % (len(resources), len(resource_ids))}

        # validate transitions
        if is_resource_state_update:
            # no escape from terminal
            if any(resource.status != status and resource.status in TERMINAL_STATES for resource in resources):
                LOGGER.error("Attempting to set undeployable resource to deployable state")
                raise AssertionError("Attempting to set undeployable resource to deployable state")

        # get instance
        resource_action = yield data.ResourceAction.get(action_id=action_id)
        if resource_action is None:
            # new
            if started is None:
                return 500, {"message": "A resource action can only be created with a start datetime."}

            resource_action = data.ResourceAction(environment=env.id, resource_version_ids=resource_ids,
                                                  action_id=action_id, action=action, started=started)
            yield resource_action.insert()
        else:
            # existing
            if resource_action.finished is not None:
                return 500, {"message": "An resource action can only be updated when it has not been finished yet. This action "
                                        "finished at %s" % resource_action.finished}

        if len(messages) > 0:
            resource_action.add_logs(messages)
            for msg in messages:
                # All other data is stored in the database. The msg was already formatted at the client side.
                self.log_resource_action(
                    env.id,
                    resource_ids,
                    const.LogLevel[msg["level"]].value,
                    datetime.datetime.strptime(msg["timestamp"], const.TIME_ISOFMT),
                    msg["msg"]
                )

        if len(changes) > 0:
            resource_action.add_changes(changes)

        if status is not None:
            resource_action.set_field("status", status)

        if change is not None:
            resource_action.set_field("change", change)

        resource_action.set_field("send_event", send_events)

        if finished is not None:
            resource_action.set_field("finished", finished)

        yield resource_action.save()

        if is_resource_state_update:
            # transient resource update
            if not is_resource_action_finished:
                for res in resources:
                    yield res.update_fields(status=status)
                if not keep_increment_cache:
                    self.clear_env_cache(env)
                return 200

            else:
                # final resource update
                if not keep_increment_cache:
                    self.clear_env_cache(env)

                model_version = None
                for res in resources:
                    yield res.update_fields(last_deploy=finished, status=status)
                    model_version = res.model

                    if "purged" in res.attributes and res.attributes["purged"] and status == const.ResourceState.deployed:
                        yield data.Parameter.delete_all(environment=env.id, resource_id=res.resource_id)

                yield data.ConfigurationModel.mark_done_if_done(env.id, model_version)

                waiting_agents = set([(Id.parse_id(prov).get_agent_name(), res.resource_version_id)
                                      for res in resources for prov in res.provides])

                for agent, resource_id in waiting_agents:
                    aclient = self.get_agent_client(env.id, agent)
                    if aclient is not None:
                        yield aclient.resource_event(env.id, agent, resource_id, send_events, status, change, changes)

        return 200

    # Project handlers
    @protocol.handle(methods.create_project)
    @gen.coroutine
    def create_project(self, name, project_id):
        if project_id is None:
            project_id = uuid.uuid4()
        try:
            project = data.Project(id=project_id, name=name)
            yield project.insert()
        except asyncpg.exceptions.UniqueViolationError:
            return 500, {"message": "A project with name %s already exists." % name}

        return 200, {"project": project}

    @protocol.handle(methods.delete_project, project_id="id")
    @gen.coroutine
    def delete_project(self, project_id):
        project = yield data.Project.get_by_id(project_id)
        if project is None:
            return 404, {"message": "The project with given id does not exist."}

        environments = yield data.Environment.get_list(project=project.id)
        for env in environments:
            yield [self.agentmanager.stop_agents(env), env.delete_cascade()]
            self._close_resource_action_logger(env)

        yield project.delete()

        return 200, {}

    @protocol.handle(methods.modify_project, project_id="id")
    @gen.coroutine
    def modify_project(self, project_id, name):
        try:
            project = yield data.Project.get_by_id(project_id)
            if project is None:
                return 404, {"message": "The project with given id does not exist."}

            yield project.update_fields(name=name)

            return 200, {"project": project}

        except asyncpg.exceptions.UniqueViolationError:
            return 500, {"message": "A project with name %s already exists." % name}

    @protocol.handle(methods.list_projects)
    @gen.coroutine
    def list_projects(self):
        projects = yield data.Project.get_list()
        return 200, {"projects": projects}

    @protocol.handle(methods.get_project, project_id="id")
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
    @protocol.handle(methods.create_environment)
    @gen.coroutine
    def create_environment(self, project_id, name, repository, branch, environment_id):
        if environment_id is None:
            environment_id = uuid.uuid4()

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

        env = data.Environment(
            id=environment_id, name=name, project=project_id, repo_url=repository, repo_branch=branch
        )
        yield env.insert()
        return 200, {"environment": env}

    @protocol.handle(methods.modify_environment, environment_id="id")
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

    @protocol.handle(methods.get_environment, environment_id="id")
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

    @protocol.handle(methods.list_environments)
    @gen.coroutine
    def list_environments(self):
        environments = yield data.Environment.get_list()
        dicts = []
        for env in environments:
            env_dict = env.to_dict()
            dicts.append(env_dict)

        return 200, {"environments": dicts}  # @UndefinedVariable

    @protocol.handle(methods.delete_environment, environment_id="id")
    @gen.coroutine
    def delete_environment(self, environment_id):
        env = yield data.Environment.get_by_id(environment_id)
        if env is None:
            return 404, {"message": "The environment with given id does not exist."}

        yield [self.agentmanager.stop_agents(env), env.delete_cascade()]

        self._close_resource_action_logger(environment_id)

        return 200

    @protocol.handle(methods.list_settings, env="tid")
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

    @protocol.handle(methods.set_setting, env="tid", key="id")
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

    @protocol.handle(methods.get_setting, env="tid", key="id")
    @gen.coroutine
    def get_setting(self, env: data.Environment, key: str):
        try:
            value = yield env.get(key)
            return 200, {"value": value, "metadata": data.Environment._settings}
        except KeyError:
            return 404

    @protocol.handle(methods.delete_setting, env="tid", key="id")
    @gen.coroutine
    def delete_setting(self, env: data.Environment, key: str):
        try:
            yield env.unset(key)
            yield self._setting_change(env, key)
            return 200
        except KeyError:
            return 404

    @protocol.handle(methods.is_compiling, environment_id="id")
    @gen.coroutine
    def is_compiling(self, environment_id):
        if self._recompiles[environment_id] is self:
            return 200

        return 204

    @protocol.handle(methods.notify_change_get, env="id")
    @gen.coroutine
    def notify_change_get(self, env, update):
        result = yield self.notify_change(env, update, {})
        return result

    @protocol.handle(methods.notify_change, env="id")
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
    def _async_recompile(self, env, update_repo, metadata={}):
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

        if last_recompile is None:
            wait = 0
            LOGGER.info("First recompile")
        else:
            wait = max(0, wait_time - (datetime.datetime.now() - last_recompile).total_seconds())
            LOGGER.info("Last recompile longer than %s ago (last was at %s)", wait_time, last_recompile)

        self._recompiles[env.id] = self
        ioloop.IOLoop.current().add_callback(self._recompile_environment, env.id, update_repo, wait, metadata)

    @gen.coroutine
    def _run_compile_stage(self, name, cmd, cwd, **kwargs):
        start = datetime.datetime.now()

        try:
            out = tempfile.NamedTemporaryFile()
            err = tempfile.NamedTemporaryFile()
            sub_process = process.Subprocess(cmd, stdout=out, stderr=err, cwd=cwd, **kwargs)

            returncode = yield sub_process.wait_for_exit(raise_error=False)

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

            if not env.repo_url:
                if not os.path.exists(os.path.join(project_dir, ".git")):
                    LOGGER.warning("Project not found and repository not set %s", project_dir)
            else:
                # checkout repo
                if not os.path.exists(os.path.join(project_dir, ".git")):
                    LOGGER.info("Cloning repository into environment directory %s", project_dir)
                    result = yield self._run_compile_stage("Cloning repository", ["git", "clone", env.repo_url, "."],
                                                           project_dir)
                    stages.append(result)
                    if result.returncode > 0:
                        return

                elif update_repo:
                    LOGGER.info("Fetching changes from repo %s", env.repo_url)
                    result = yield self._run_compile_stage("Fetching changes", ["git", "fetch", env.repo_url],
                                                           project_dir)
                    stages.append(result)
                if env.repo_branch:
                    # verify if branch is correct
                    LOGGER.debug("Verifying correct branch")
                    sub_process = process.Subprocess(["git", "branch"],
                                                     stdout=process.Subprocess.STREAM,
                                                     stderr=process.Subprocess.STREAM,
                                                     cwd=project_dir)

                    out, _, _ = yield [sub_process.stdout.read_until_close(),
                                       sub_process.stderr.read_until_close(),
                                       sub_process.wait_for_exit(raise_error=False)]

                    o = re.search(r"\* ([^\s]+)$", out.decode(), re.MULTILINE)
                    if o is not None and env.repo_branch != o.group(1):
                        LOGGER.info("Repository is at %s branch, switching to %s", o.group(1), env.repo_branch)
                        result = yield self._run_compile_stage("switching branch", ["git", "checkout", env.repo_branch],
                                                               project_dir)
                        stages.append(result)

                if update_repo:
                    result = yield self._run_compile_stage("Pulling updates", ["git", "pull"], project_dir)
                    stages.append(result)
                    LOGGER.info("Installing and updating modules")
                    result = yield self._run_compile_stage("Installing modules", inmanta_path + ["modules", "install"],
                                                           project_dir,
                                                           env=os.environ.copy())
                    stages.append(result)
                    result = yield self._run_compile_stage("Updating modules", inmanta_path + ["modules", "update"],
                                                           project_dir,
                                                           env=os.environ.copy())
                    stages.append(result)

            LOGGER.info("Recompiling configuration model")
            server_address = opt.server_address.get()
            cmd = inmanta_path + ["-vvv", "export", "-e", str(environment_id), "--server_address", server_address,
                                  "--server_port", opt.transport_port.get(), "--metadata", json.dumps(metadata)]
            if config.Config.get("server", "auth", False):
                token = encode_token(["compiler", "api"], str(environment_id))
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

            yield comp.insert()
            yield data.Report.insert_many(stages)

    @protocol.handle(methods.get_reports, env="tid")
    @gen.coroutine
    def get_reports(self, env, start=None, end=None, limit=None):
        argscount = len([x for x in [start, end, limit] if x is not None])
        if argscount == 3:
            return 500, {"message": "Limit, start and end can not be set together"}
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        if start is not None:
            start = dateutil.parser.parse(start)
        if end is not None:
            end = dateutil.parser.parse(end)
        models = yield data.Compile.get_reports(env.id, limit, start, end)

        return 200, {"reports": models}

    @protocol.handle(methods.get_report, compile_id="id")
    @gen.coroutine
    def get_report(self, compile_id):
        report = yield data.Compile.get_report(compile_id)

        if report is None:
            return 404

        return 200, {"report": report}

    @protocol.handle(methods.decomission_environment, env="id")
    @gen.coroutine
    def decomission_environment(self, env, metadata):
        version = int(time.time())
        if metadata is None:
            metadata = {
                "message": "Decommission of environment",
                "type": "api"
            }
        result = yield self.put_version(env, version, [], {}, [], {const.EXPORT_META_DATA: metadata})
        return result, {"version": version}

    @protocol.handle(methods.clear_environment, env="id")
    @gen.coroutine
    def clear_environment(self, env: data.Environment):
        """
            Clear the environment
        """
        yield self.agentmanager.stop_agents(env)
        yield env.delete_cascade(only_content=True)

        project_dir = os.path.join(self._server_storage["environments"], str(env.id))
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir)

        return 200

    @protocol.handle(methods.create_token, env="tid")
    @gen.coroutine
    def create_token(self, env, client_types, idempotent):
        """
            Create a new auth token for this environment
        """
        return 200, {"token": encode_token(client_types, str(env.id), idempotent)}
