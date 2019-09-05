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
import asyncio
import base64
import datetime
import difflib
import logging
import os
import shutil
import time
import uuid
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Union
from uuid import UUID

import asyncpg
import importlib_metadata
from tornado import locks

from inmanta import const, data
from inmanta.ast import type
from inmanta.const import STATE_UPDATE, TERMINAL_STATES, TRANSIENT_STATES, VALID_STATES_ON_STATE_UPDATE
from inmanta.data.model import ExtensionStatus, SliceStatus, StatusResponse
from inmanta.protocol import encode_token, exceptions, methods
from inmanta.protocol.common import attach_warnings
from inmanta.protocol.exceptions import BadRequest, NotFound
from inmanta.reporter import InfluxReporter
from inmanta.resources import Id
from inmanta.server import (
    SLICE_AGENT_MANAGER,
    SLICE_COMPILER,
    SLICE_DATABASE,
    SLICE_SERVER,
    SLICE_SESSION_MANAGER,
    SLICE_TRANSPORT,
)
from inmanta.server import config as opt
from inmanta.server import protocol
from inmanta.types import Apireturn, ArgumentTypes, JsonType, PrimitiveTypes, ReturnTupple, Warnings
from inmanta.util import hash_file

LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from inmanta.server.agentmanager import AgentManager
    from inmanta.server.compilerservice import CompilerService

DBLIMIT = 100000


def error_and_log(message: str, **context: Any) -> None:
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
            sinfo=None,
        )

        self.created = created.timestamp()
        self.msecs = (self.created - int(self.created)) * 1000
        self.relativeCreated = (self.created - logging._startTime) * 1000


class DatabaseSlice(protocol.ServerSlice):
    """Slice to initialize the database"""

    def __init__(self) -> None:
        super(DatabaseSlice, self).__init__(SLICE_DATABASE)
        self._pool: Optional[asyncpg.pool.Pool] = None

    async def start(self) -> None:
        await self.connect_database()

    async def stop(self) -> None:
        await self.disconnect_database()
        self._pool = None

    def get_dependencies(self) -> List[str]:
        return []

    async def connect_database(self) -> None:
        """ Connect to the database
        """
        database_host = opt.db_host.get()
        database_port = opt.db_port.get()

        database_username = opt.db_username.get()
        database_password = opt.db_password.get()
        self._pool = await data.connect(database_host, database_port, opt.db_name.get(), database_username, database_password)
        LOGGER.info("Connected to PostgreSQL database %s on %s:%d", opt.db_name.get(), database_host, database_port)

    async def disconnect_database(self) -> None:
        """ Disconnect the database
        """
        await data.disconnect()

    async def get_status(self) -> Dict[str, ArgumentTypes]:
        """ Get the status of the database connection
        """
        return {
            "connected": self._pool is not None,
            "max_pool": self._pool._maxsize,
            "open_connections": len([x for x in self._pool._holders if x._con is not None and not x._con.is_closed()]),
            "database": opt.db_name.get(),
            "host": opt.db_host.get(),
        }


class Server(protocol.ServerSlice):
    """
        The central Inmanta server that communicates with clients and agents and persists configuration
        information
    """

    _server_storage: Dict[str, str]
    compiler: "CompilerService"
    _server: protocol.Server

    def __init__(self) -> None:
        super().__init__(name=SLICE_SERVER)
        LOGGER.info("Starting server endpoint")

        self.setup_dashboard()
        self.dryrun_lock = locks.Lock()
        self._fact_expire = opt.server_fact_expire.get()
        self._fact_renew = opt.server_fact_renew.get()

        self._resource_action_loggers: Dict[uuid.UUID, logging.Logger] = {}
        self._resource_action_handlers: Dict[uuid.UUID, logging.Handler] = {}

        self._increment_cache = {}
        # lock to ensure only one inflight request
        self._increment_cache_locks: Dict[uuid.UUID, locks.Lock] = defaultdict(lambda: locks.Lock())
        self._influx_db_reporter: Optional[InfluxReporter] = None

    def get_dependencies(self) -> List[str]:
        return [SLICE_SESSION_MANAGER, SLICE_DATABASE]

    def get_depended_by(self) -> List[str]:
        return [SLICE_TRANSPORT]

    async def prestart(self, server: protocol.Server) -> None:
        self._server = server
        self._server_storage: Dict[str, str] = self.check_storage()
        self.agentmanager: "AgentManager" = server.get_slice(SLICE_AGENT_MANAGER)
        self.compiler: "CompilerService" = server.get_slice(SLICE_COMPILER)

    async def start(self) -> None:
        self.schedule(self.renew_expired_facts, self._fact_renew)
        self.schedule(self._purge_versions, opt.server_purge_version_interval.get())
        self.schedule(data.ResourceAction.purge_logs, opt.server_purge_resource_action_logs_interval.get())

        self.add_background_task(self._purge_versions())
        self.start_metric_reporters()

        await super().start()

    async def stop(self) -> None:
        await super().stop()
        self._close_resource_action_loggers()
        self.stop_metric_reporters()

    def stop_metric_reporters(self) -> None:
        if self._influx_db_reporter:
            self._influx_db_reporter.stop()
            self._influx_db_reporter = None

    def start_metric_reporters(self) -> None:
        if opt.influxdb_host.get():
            self._influx_db_reporter = InfluxReporter(
                server=opt.influxdb_host.get(),
                port=opt.influxdb_port.get(),
                database=opt.influxdb_name.get(),
                username=opt.influxdb_username.get(),
                password=opt.influxdb_password,
                reporting_interval=opt.influxdb_interval.get(),
                autocreate_database=True,
                tags=opt.influxdb_tags.get(),
            )
            self._influx_db_reporter.start()

    @staticmethod
    def get_resource_action_log_file(environment: uuid.UUID) -> str:
        """Get the correct filename for the given environment
        :param environment: The environment id to get the file for
        :return: The path to the logfile
        """
        return os.path.join(opt.log_dir.get(), opt.server_resource_action_log_prefix.get() + str(environment) + ".log")

    def get_resource_action_logger(self, environment: uuid.UUID) -> logging.Logger:
        """Get the resource action logger for the given environment. If the logger was not created, create it.
        :param environment: The environment to get a logger for
        :return: The logger for the given environment.
        """
        if environment in self._resource_action_loggers:
            return self._resource_action_loggers[environment]

        resource_action_log = self.get_resource_action_log_file(environment)

        file_handler = logging.handlers.WatchedFileHandler(filename=resource_action_log, mode="a+")
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

    def get_agent_client(self, tid: UUID, endpoint: str) -> Optional[protocol.ReturnClient]:
        return self.agentmanager.get_agent_client(tid, endpoint)

    def setup_dashboard(self) -> None:
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
    }""" % (
                opt.dash_realm.get(),
                opt.dash_auth_url.get(),
                opt.dash_client_id.get(),
            )

        content = """
angular.module('inmantaApi.config', []).constant('inmantaConfig', {
    'backend': window.location.origin+'/'%s
});
        """ % (
            auth
        )
        self.add_static_content("/dashboard/config.js", content=content)
        self.add_static_handler("/dashboard", dashboard_path, start=True)

    def clear_env_cache(self, env: data.Environment) -> None:
        LOGGER.log(const.LOG_LEVEL_TRACE, "Clearing cache for %s", env.id)
        self._increment_cache[env.id] = None

    async def _purge_versions(self) -> None:
        """
            Purge versions from the database
        """
        # TODO: move to data and use queries for delete
        envs = await data.Environment.get_list()
        for env_item in envs:
            # get available versions
            n_versions = opt.server_version_to_keep.get()
            versions = await data.ConfigurationModel.get_list(environment=env_item.id)
            if len(versions) > n_versions:
                LOGGER.info("Removing %s available versions from environment %s", len(versions) - n_versions, env_item.id)
                version_dict = {x.version: x for x in versions}
                delete_list = sorted(version_dict.keys())
                delete_list = delete_list[:-n_versions]

                for v in delete_list:
                    await version_dict[v].delete_cascade()

    def check_storage(self) -> Dict[str, str]:
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

    async def renew_expired_facts(self) -> None:
        """
            Send out requests to renew expired facts
        """
        LOGGER.info("Renewing expired parameters")

        updated_before = datetime.datetime.now() - datetime.timedelta(0, (self._fact_expire - self._fact_renew))
        expired_params = await data.Parameter.get_updated_before(updated_before)

        LOGGER.debug("Renewing %d expired parameters" % len(expired_params))

        for param in expired_params:
            if param.environment is None:
                LOGGER.warning(
                    "Found parameter without environment (%s for resource %s). Deleting it.", param.name, param.resource_id
                )
                await param.delete()
            else:
                LOGGER.debug(
                    "Requesting new parameter value for %s of resource %s in env %s",
                    param.name,
                    param.resource_id,
                    param.environment,
                )
                await self.agentmanager.request_parameter(param.environment, param.resource_id)

        unknown_parameters = await data.UnknownParameter.get_list(resolved=False)
        for u in unknown_parameters:
            if u.environment is None:
                LOGGER.warning(
                    "Found unknown parameter without environment (%s for resource %s). Deleting it.", u.name, u.resource_id
                )
                await u.delete()
            else:
                LOGGER.debug("Requesting value for unknown parameter %s of resource %s in env %s", u.name, u.resource_id, u.id)
                await self.agentmanager.request_parameter(u.environment, u.resource_id)

        LOGGER.info("Done renewing expired parameters")

    @protocol.handle(methods.get_param, param_id="id", env="tid")
    async def get_param(self, env: data.Environment, param_id: str, resource_id: Optional[str] = None) -> Apireturn:
        if resource_id is None:
            params = await data.Parameter.get_list(environment=env.id, name=param_id)
        else:
            params = await data.Parameter.get_list(environment=env.id, name=param_id, resource_id=resource_id)

        if len(params) == 0:
            if resource_id is not None:
                out = await self.agentmanager.request_parameter(env.id, resource_id)
                return out
            return 404

        param = params[0]

        # check if it was expired
        now = datetime.datetime.now()
        if resource_id is None or (param.updated + datetime.timedelta(0, self._fact_expire)) > now:
            return 200, {"parameter": params[0]}

        LOGGER.info("Parameter %s of resource %s expired.", param_id, resource_id)
        out = await self.agentmanager.request_parameter(env.id, resource_id)
        return out

    async def _update_param(
        self,
        env: data.Environment,
        name: str,
        value: str,
        source: str,
        resource_id: str,
        metadata: JsonType,
        recompile: bool = False,
    ) -> bool:
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

        params = await data.Parameter.get_list(environment=env.id, name=name, resource_id=resource_id)

        value_updated = True
        if len(params) == 0:
            param = data.Parameter(
                environment=env.id,
                name=name,
                resource_id=resource_id,
                value=value,
                source=source,
                updated=datetime.datetime.now(),
                metadata=metadata,
            )
            await param.insert()
        else:
            param = params[0]
            value_updated = param.value != value
            await param.update(source=source, value=value, updated=datetime.datetime.now(), metadata=metadata)

        # check if the parameter is an unknown
        params = await data.UnknownParameter.get_list(environment=env.id, name=name, resource_id=resource_id, resolved=False)
        if len(params) > 0:
            LOGGER.info(
                "Received values for unknown parameters %s, triggering a recompile", ", ".join([x.name for x in params])
            )
            for p in params:
                await p.update_fields(resolved=True)

            return True

        return recompile and value_updated

    @protocol.handle(methods.set_param, param_id="id", env="tid")
    async def set_param(
        self,
        env: data.Environment,
        param_id: str,
        source: str,
        value: str,
        resource_id: str,
        metadata: JsonType,
        recompile: bool,
    ) -> Apireturn:
        result = await self._update_param(env, param_id, value, source, resource_id, metadata, recompile)
        warnings = None
        if result:
            compile_metadata = {
                "message": "Recompile model because one or more parameters were updated",
                "type": "param",
                "params": [(param_id, resource_id)],
            }
            warnings = await self._async_recompile(env, False, metadata=compile_metadata)

        if resource_id is None:
            resource_id = ""

        params = await data.Parameter.get_list(environment=env.id, name=param_id, resource_id=resource_id)

        return attach_warnings(200, {"parameter": params[0]}, warnings)

    @protocol.handle(methods.set_parameters, env="tid")
    async def set_parameters(self, env: data.Environment, parameters: JsonType) -> Apireturn:
        recompile = False
        compile_metadata = {
            "message": "Recompile model because one or more parameters were updated",
            "type": "param",
            "params": [],
        }
        for param in parameters:
            name = param["id"]
            source = param["source"]
            value = param["value"] if "value" in param else None
            resource_id = param["resource_id"] if "resource_id" in param else None
            metadata = param["metadata"] if "metadata" in param else None

            result = await self._update_param(env, name, value, source, resource_id, metadata)
            if result:
                recompile = True
                compile_metadata["params"].append((name, resource_id))

        warnings = None
        if recompile:
            warnings = await self._async_recompile(env, False, metadata=compile_metadata)

        return attach_warnings(200, None, warnings)

    @protocol.handle(methods.delete_param, env="tid", parameter_name="id")
    async def delete_param(self, env: data.Environment, parameter_name: str, resource_id: str) -> Apireturn:
        if resource_id is None:
            params = await data.Parameter.get_list(environment=env.id, name=parameter_name)
        else:
            params = await data.Parameter.get_list(environment=env.id, name=parameter_name, resource_id=resource_id)

        if len(params) == 0:
            return 404

        param = params[0]
        await param.delete()
        metadata = {
            "message": "Recompile model because one or more parameters were deleted",
            "type": "param",
            "params": [(param.name, param.resource_id)],
        }
        warnings = await self._async_recompile(env, False, metadata=metadata)

        return attach_warnings(200, None, warnings)

    @protocol.handle(methods.list_params, env="tid")
    async def list_params(self, env: data.Environment, query: Dict[str, str]) -> Apireturn:
        params = await data.Parameter.list_parameters(env.id, **query)
        return (
            200,
            {
                "parameters": params,
                "expire": self._fact_expire,
                "now": datetime.datetime.now().isoformat(timespec="microseconds"),
            },
        )

    @protocol.handle(methods.put_form, form_id="id", env="tid")
    async def put_form(self, env: data.Environment, form_id: str, form: JsonType) -> Apireturn:
        form_doc = await data.Form.get_form(environment=env.id, form_type=form_id)
        fields = {k: v["type"] for k, v in form["attributes"].items()}
        defaults = {k: v["default"] for k, v in form["attributes"].items() if "default" in v}
        field_options = {k: v["options"] for k, v in form["attributes"].items() if "options" in v}

        if form_doc is None:
            form_doc = data.Form(
                environment=env.id,
                form_type=form_id,
                fields=fields,
                defaults=defaults,
                options=form["options"],
                field_options=field_options,
            )
            await form_doc.insert()

        else:
            # update the definition
            form_doc.fields = fields
            form_doc.defaults = defaults
            form_doc.options = form["options"]
            form_doc.field_options = field_options

            await form_doc.update()

        return 200, {"form": {"id": form_doc.form_type}}

    @protocol.handle(methods.get_form, form_id="id", env="tid")
    async def get_form(self, env: data.Environment, form_id: str) -> Apireturn:
        form = await data.Form.get_form(environment=env.id, form_type=form_id)

        if form is None:
            return 404

        return 200, {"form": form}

    @protocol.handle(methods.list_forms, env="tid")
    async def list_forms(self, env: data.Environment) -> Apireturn:
        forms = await data.Form.get_list(environment=env.id)
        return 200, {"forms": [{"form_id": x.form_type, "form_type": x.form_type} for x in forms]}

    @protocol.handle(methods.list_records, env="tid")
    async def list_records(self, env: data.Environment, form_type: str, include_record: bool) -> Apireturn:
        form_type = await data.Form.get_form(environment=env.id, form_type=form_type)
        if form_type is None:
            return 404, {"message": "No form is defined with id %s" % form_type}

        records = await data.FormRecord.get_list(form=form_type.form_type)

        if not include_record:
            return 200, {"records": [{"id": r.id, "changed": r.changed} for r in records]}

        else:
            return 200, {"records": records}

    @protocol.handle(methods.get_record, record_id="id", env="tid")
    async def get_record(self, env: data.Environment, record_id: uuid.UUID) -> Apireturn:
        record = await data.FormRecord.get_by_id(record_id)
        if record is None:
            return 404, {"message": "The record with id %s does not exist" % record_id}

        return 200, {"record": record}

    @protocol.handle(methods.update_record, record_id="id", env="tid")
    async def update_record(self, env: data.Environment, record_id: uuid.UUID, form: JsonType) -> Apireturn:
        record = await data.FormRecord.get_by_id(record_id)
        if record is None:
            return 404, {"message": "The record with id %s does not exist" % record_id}
        if record.environment != env.id:
            return 404, {"message": "The record with id %s does not exist" % record_id}

        form_def = await data.Form.get_one(environment=env.id, form_type=record.form)

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

        await record.update()

        metadata = {
            "message": "Recompile model because a form record was updated",
            "type": "form",
            "records": [str(record_id)],
            "form": form,
        }

        warnings = await self._async_recompile(env, False, metadata=metadata)
        return attach_warnings(200, {"record": record}, warnings)

    @protocol.handle(methods.create_record, env="tid")
    async def create_record(self, env: data.Environment, form_type: str, form: JsonType) -> Apireturn:
        form_obj = await data.Form.get_form(environment=env.id, form_type=form_type)

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

        await record.insert()
        metadata = {
            "message": "Recompile model because a form record was inserted",
            "type": "form",
            "records": [str(record.id)],
            "form": form,
        }
        warnings = await self._async_recompile(env, False, metadata=metadata)

        return attach_warnings(200, {"record": record}, warnings)

    @protocol.handle(methods.delete_record, record_id="id", env="tid")
    async def delete_record(self, env: data.Environment, record_id: uuid.UUID) -> Apireturn:
        record = await data.FormRecord.get_by_id(record_id)
        if record is None:
            raise NotFound()
        await record.delete()

        metadata = {
            "message": "Recompile model because a form record was removed",
            "type": "form",
            "records": [str(record.id)],
            "form": record.form,
        }

        warnings = await self._async_recompile(env, False, metadata=metadata)

        return attach_warnings(200, None, warnings)

    @protocol.handle(methods.upload_file, file_hash="id")
    async def upload_file(self, file_hash: str, content: str) -> Apireturn:
        content = base64.b64decode(content)
        return self.upload_file_internal(file_hash, content)

    def upload_file_internal(self, file_hash, content) -> Apireturn:
        file_name = os.path.join(self._server_storage["files"], file_hash)

        if os.path.exists(file_name):
            return 500, {"message": "A file with this id already exists."}

        if hash_file(content) != file_hash:
            return 400, {"message": "The hash does not match the content"}

        with open(file_name, "wb+") as fd:
            fd.write(content)

        return 200

    @protocol.handle(methods.stat_file, file_hash="id")
    async def stat_file(self, file_hash: str) -> Apireturn:
        file_name = os.path.join(self._server_storage["files"], file_hash)

        if os.path.exists(file_name):
            return 200
        else:
            return 404

    @protocol.handle(methods.get_file, file_hash="id")
    async def get_file(self, file_hash: str) -> ReturnTupple:
        ret, content = self.get_file_internal(file_hash)
        if ret == 200:
            return 200, {"content": base64.b64encode(content).decode("ascii")}
        else:
            return ret, content

    def get_file_internal(self, file_hash: str) -> ReturnTupple:
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
                        LOGGER.error(
                            "File corrupt, expected hash %s but found %s at %s, Deleting file"
                            % (file_hash, actualhash, file_name)
                        )
                        try:
                            os.remove(file_name)
                        except OSError:
                            LOGGER.exception("Failed to delete file %s" % (file_name))
                            return (
                                500,
                                {
                                    "message": (
                                        "File corrupt, expected hash %s but found %s,"
                                        " Failed to delete file, please contact the server administrator"
                                    )
                                    % (file_hash, actualhash)
                                },
                            )
                        return (
                            500,
                            {
                                "message": (
                                    "File corrupt, expected hash %s but found %s, "
                                    "Deleting file, please re-upload the corrupt file"
                                )
                                % (file_hash, actualhash)
                            },
                        )
                    else:
                        LOGGER.error("File corrupt, expected hash %s but found %s at %s" % (file_hash, actualhash, file_name))
                        return (
                            500,
                            {
                                "message": (
                                    "File corrupt, expected hash %s but found %s," " please contact the server administrator"
                                )
                                % (file_hash, actualhash)
                            },
                        )
                return 200, content

    @protocol.handle(methods.stat_files)
    async def stat_files(self, files: List[str]) -> ReturnTupple:
        """
            Return which files in the list exist on the server
        """
        response: List[str] = []
        for f in files:
            f_path = os.path.join(self._server_storage["files"], f)
            if not os.path.exists(f_path):
                response.append(f)

        return 200, {"files": response}

    @protocol.handle(methods.diff)
    async def file_diff(self, a: str, b: str) -> Apireturn:
        """
            Diff the two files identified with the two hashes
        """
        if a == "" or a == "0":
            a_lines: List[str] = []
        else:
            a_path = os.path.join(self._server_storage["files"], a)
            if not os.path.exists(a_path):
                return 404

            with open(a_path, "r") as fd:
                a_lines = fd.readlines()

        if b == "" or b == "0":
            b_lines: List[str] = []
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
    async def get_resource(
        self,
        env: data.Environment,
        resource_id: str,
        logs: bool,
        status: bool,
        log_action: const.ResourceAction,
        log_limit: int,
    ) -> Apireturn:
        resv = await data.Resource.get(env.id, resource_id)
        if resv is None:
            return 404, {"message": "The resource with the given id does not exist in the given environment"}

        if status is not None and status:
            return 200, {"status": resv.status}

        actions: List[data.ResourceAction] = []
        if bool(logs):
            action_name = None
            if log_action is not None:
                action_name = log_action.name

            actions = await data.ResourceAction.get_log(
                environment=env.id, resource_version_id=resource_id, action=action_name, limit=log_limit
            )

        return 200, {"resource": resv, "logs": actions}

    @protocol.handle(methods.get_resources_for_agent, env="tid")
    async def get_resources_for_agent(
        self, env: data.Environment, agent: str, version: str, sid: uuid.UUID, incremental_deploy: bool
    ) -> Apireturn:
        if not self.agentmanager.is_primary(env, sid, agent):
            return 409, {"message": "This agent is not currently the primary for the endpoint %s (sid: %s)" % (agent, sid)}
        if incremental_deploy:
            if version is not None:
                return 500, {"message": "Cannot request increment for a specific version"}
            result = await self.get_resource_increment_for_agent(env, agent)
        else:
            result = await self.get_all_resources_for_agent(env, agent, version)
        return result

    async def get_all_resources_for_agent(self, env: data.Environment, agent: str, version: str) -> Apireturn:
        started = datetime.datetime.now()
        if version is None:
            version = await data.ConfigurationModel.get_version_nr_latest_version(env.id)
            if version is None:
                return 404, {"message": "No version available"}

        else:
            exists = await data.ConfigurationModel.version_exists(environment=env.id, version=version)
            if not exists:
                return 404, {"message": "The given version does not exist"}

        deploy_model = []

        resources = await data.Resource.get_resources_for_version(env.id, version, agent)

        resource_ids = []
        for rv in resources:
            deploy_model.append(rv.to_dict())
            resource_ids.append(rv.resource_version_id)

        now = datetime.datetime.now()

        log_line = data.LogLine.log(logging.INFO, "Resource version pulled by client for agent %(agent)s state", agent=agent)
        self.log_resource_action(env.id, resource_ids, logging.INFO, now, log_line.msg)
        ra = data.ResourceAction(
            environment=env.id,
            resource_version_ids=resource_ids,
            action=const.ResourceAction.pull,
            action_id=uuid.uuid4(),
            started=started,
            finished=now,
            messages=[log_line],
        )
        await ra.insert()

        return 200, {"environment": env.id, "agent": agent, "version": version, "resources": deploy_model}

    async def get_resource_increment_for_agent(self, env: data.Environment, agent: str) -> Apireturn:
        started = datetime.datetime.now()

        version = await data.ConfigurationModel.get_version_nr_latest_version(env.id)
        if version is None:
            return 404, {"message": "No version available"}

        increment = self._increment_cache.get(env.id, None)
        if increment is None:
            with (await self._increment_cache_locks[env.id].acquire()):
                increment = self._increment_cache.get(env.id, None)
                if increment is None:
                    increment = await data.ConfigurationModel.get_increment(env.id, version)
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
            "timestamp": now.isoformat(timespec="microseconds"),
            "args": [],
        }
        self.add_background_task(
            self.resource_action_update(
                env,
                neg_increment,
                action_id=uuid.uuid4(),
                started=now,
                finished=now,
                status=const.ResourceState.deployed,
                # does this require a different ResourceAction?
                action=const.ResourceAction.deploy,
                changes={},
                messages=[logline],
                change=const.Change.nochange,
                send_events=False,
                keep_increment_cache=True,
            )
        )

        resources = await data.Resource.get_resources_for_version(env.id, version, agent)

        deploy_model: List[Dict[str, Any]] = []
        resource_ids: List[str] = []
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

        ra = data.ResourceAction(
            environment=env.id,
            resource_version_ids=resource_ids,
            action=const.ResourceAction.pull,
            action_id=uuid.uuid4(),
            started=started,
            finished=now,
            messages=[
                data.LogLine.log(logging.INFO, "Resource version pulled by client for agent %(agent)s state", agent=agent)
            ],
        )
        await ra.insert()

        return 200, {"environment": env.id, "agent": agent, "version": version, "resources": deploy_model}

    @protocol.handle(methods.list_versions, env="tid")
    async def list_version(self, env: data.Environment, start: Optional[int] = None, limit: Optional[int] = None) -> Apireturn:
        if (start is None and limit is not None) or (limit is None and start is not None):
            return 500, {"message": "Start and limit should always be set together."}

        if start is None:
            start = 0
            limit = data.DBLIMIT

        models = await data.ConfigurationModel.get_versions(env.id, start, limit)
        count = len(models)

        d = {"versions": models}

        if start is not None:
            d["start"] = start
            d["limit"] = limit

        d["count"] = count

        return 200, d

    @protocol.handle(methods.get_version, version_id="id", env="tid")
    async def get_version(
        self,
        env: data.Environment,
        version_id: int,
        include_logs: Optional[bool] = None,
        log_filter: Optional[str] = None,
        limit: Optional[int] = 0,
    ) -> Apireturn:
        version = await data.ConfigurationModel.get_version(env.id, version_id)
        if version is None:
            return 404, {"message": "The given configuration model does not exist yet."}

        resources = await data.Resource.get_resources_for_version(env.id, version_id, no_obj=True)
        if resources is None:
            return 404, {"message": "The given configuration model does not exist yet."}

        d = {"model": version}

        # todo: batch get_log into single query?
        d["resources"] = []
        for res_dict in resources:
            if bool(include_logs):
                res_dict["actions"] = await data.ResourceAction.get_log(
                    env.id, res_dict["resource_version_id"], log_filter, limit
                )

            d["resources"].append(res_dict)

        d["unknowns"] = await data.UnknownParameter.get_list(environment=env.id, version=version_id)

        return 200, d

    @protocol.handle(methods.delete_version, version_id="id", env="tid")
    async def delete_version(self, env, version_id):
        version = await data.ConfigurationModel.get_version(env.id, version_id)
        if version is None:
            return 404, {"message": "The given configuration model does not exist yet."}

        await version.delete_cascade()
        return 200

    @protocol.handle(methods.put_version, env="tid")
    async def put_version(
        self,
        env: data.Environment,
        version: int,
        resources: List[JsonType],
        resource_state: Dict[str, const.ResourceState],
        unknowns: List[Dict[str, PrimitiveTypes]],
        version_info: JsonType,
    ) -> Apireturn:
        started = datetime.datetime.now()

        agents = set()
        # lookup for all RV's, lookup by resource id
        rv_dict = {}
        # reverse dependency tree, Resource.provides [:] -- Resource.requires as resource_id
        provides_tree: Dict[str, List[str]] = defaultdict(lambda: [])
        # list of all resources which have a cross agent dependency, as a tuple, (dependant,requires)
        cross_agent_dep = []
        # list of all resources which are undeployable
        undeployable: List[data.Resource] = []

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

        resources_to_purge: List[data.Resource] = []
        if not failed:
            # search for deleted resources
            resources_to_purge = await data.Resource.get_deleted_resources(env.id, version, set(rv_dict.keys()))

            previous_requires = {}
            for res in resources_to_purge:
                LOGGER.warning("Purging %s, purged resource based on %s" % (res.resource_id, res.resource_version_id))

                attributes = res.attributes.copy()
                attributes["purged"] = True
                attributes["requires"] = []
                res_obj = data.Resource.new(
                    env.id, resource_version_id="%s,v=%s" % (res.resource_id, version), attributes=attributes
                )
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

        undeployable_ids: List[str] = [res.resource_id for res in undeployable]
        # get skipped for undeployable
        work = list(undeployable_ids)
        skippeable: Set[str] = set()
        while len(work) > 0:
            current = work.pop()
            if current in skippeable:
                continue
            skippeable.add(current)
            work.extend(provides_tree[current])

        skippeable = sorted(list(skippeable - set(undeployable_ids)))

        try:
            cm = data.ConfigurationModel(
                environment=env.id,
                version=version,
                date=datetime.datetime.now(),
                total=len(resources),
                version_info=version_info,
                undeployable=undeployable_ids,
                skipped_for_undeployable=skippeable,
            )
            await cm.insert()
        except asyncpg.exceptions.UniqueViolationError:
            return 500, {"message": "The given version is already defined. Versions should be unique."}

        await data.Resource.insert_many(resource_objects)
        await cm.update_fields(total=cm.total + len(resources_to_purge))

        for uk in unknowns:
            if "resource" not in uk:
                uk["resource"] = ""

            if "metadata" not in uk:
                uk["metadata"] = {}

            up = data.UnknownParameter(
                resource_id=uk["resource"],
                name=uk["parameter"],
                source=uk["source"],
                environment=env.id,
                version=version,
                metadata=uk["metadata"],
            )
            await up.insert()

        for agent in agents:
            await self.agentmanager.ensure_agent_registered(env, agent)

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
            messages=[log_line],
        )
        await ra.insert()
        LOGGER.debug("Successfully stored version %d", version)

        self.clear_env_cache(env)

        auto_deploy = await env.get(data.AUTO_DEPLOY)
        if auto_deploy:
            LOGGER.debug("Auto deploying version %d", version)
            push_on_auto_deploy = await env.get(data.PUSH_ON_AUTO_DEPLOY)
            agent_trigger_method_on_autodeploy = await env.get(data.AGENT_TRIGGER_METHOD_ON_AUTO_DEPLOY)
            agent_trigger_method_on_autodeploy = const.AgentTriggerMethod[agent_trigger_method_on_autodeploy]
            await self.release_version(env, version, push_on_auto_deploy, agent_trigger_method_on_autodeploy)

        return 200

    @protocol.handle(methods.release_version, version_id="id", env="tid")
    async def release_version(
        self,
        env: data.Environment,
        version_id: int,
        push: bool,
        agent_trigger_method: Optional[const.AgentTriggerMethod] = None,
    ) -> Apireturn:
        model = await data.ConfigurationModel.get_version(env.id, version_id)
        if model is None:
            return 404, {"message": "The request version does not exist."}

        await model.update_fields(released=True, result=const.VersionState.deploying)

        if model.total == 0:
            await model.mark_done()
            return 200, {"model": model}

        # Already mark undeployable resources as deployed to create a better UX (change the version counters)
        undep = await model.get_undeployable()
        undep = [rid + ",v=%s" % version_id for rid in undep]

        now = datetime.datetime.now()

        # not checking error conditions
        await self.resource_action_update(
            env,
            undep,
            action_id=uuid.uuid4(),
            started=now,
            finished=now,
            status=const.ResourceState.undefined,
            action=const.ResourceAction.deploy,
            changes={},
            messages=[],
            change=const.Change.nochange,
            send_events=False,
        )

        skippable = await model.get_skipped_for_undeployable()
        skippable = [rid + ",v=%s" % version_id for rid in skippable]
        # not checking error conditions
        await self.resource_action_update(
            env,
            skippable,
            action_id=uuid.uuid4(),
            started=now,
            finished=now,
            status=const.ResourceState.skipped_for_undefined,
            action=const.ResourceAction.deploy,
            changes={},
            messages=[],
            change=const.Change.nochange,
            send_events=False,
        )

        if push:
            # fetch all resource in this cm and create a list of distinct agents
            agents = await data.ConfigurationModel.get_agents(env.id, version_id)
            await self.agentmanager._ensure_agents(env, agents)

            for agent in agents:
                client = self.get_agent_client(env.id, agent)
                if client is not None:
                    if not agent_trigger_method:
                        # Ensure backward compatibility
                        incremental_deploy = False
                    else:
                        incremental_deploy = agent_trigger_method is const.AgentTriggerMethod.push_incremental_deploy
                    self.add_background_task(client.trigger(env.id, agent, incremental_deploy))
                else:
                    LOGGER.warning("Agent %s from model %s in env %s is not available for a deploy", agent, version_id, env.id)

        return 200, {"model": model}

    @protocol.handle(methods.deploy, env="tid")
    async def deploy(
        self,
        env: data.Environment,
        agent_trigger_method: const.AgentTriggerMethod = const.AgentTriggerMethod.push_full_deploy,
        agents: List[str] = None,
    ) -> Apireturn:
        warnings = []

        # get latest version
        version_id = await data.ConfigurationModel.get_version_nr_latest_version(env.id)
        if version_id is None:
            return 404, {"message": "No version available"}

        # filter agents
        allagents = await data.ConfigurationModel.get_agents(env.id, version_id)
        if agents is not None:
            required = set(agents)
            present = set(allagents)
            allagents = list(required.intersection(present))
            notfound = required - present
            if notfound:
                warnings.append(
                    "Model version %d does not contain agents named [%s]" % (version_id, ",".join(sorted(list(notfound))))
                )

        if not allagents:
            return attach_warnings(404, {"message": "No agent could be reached"}, warnings)

        present = set()
        absent = set()

        await self.agentmanager._ensure_agents(env, allagents)

        for agent in allagents:
            client = self.get_agent_client(env.id, agent)
            if client is not None:
                incremental_deploy = agent_trigger_method is const.AgentTriggerMethod.push_incremental_deploy
                self.add_background_task(client.trigger(env.id, agent, incremental_deploy))
                present.add(agent)
            else:
                absent.add(agent)

        if absent:
            warnings.append("Could not reach agents named [%s]" % ",".join(sorted(list(absent))))

        if not present:
            return attach_warnings(404, {"message": "No agent could be reached"}, warnings)

        return attach_warnings(200, {"agents": sorted(list(present))}, warnings)

    @protocol.handle(methods.dryrun_request, version_id="id", env="tid")
    async def dryrun_request(self, env: data.Environment, version_id: int) -> Apireturn:
        model = await data.ConfigurationModel.get_version(environment=env.id, version=version_id)
        if model is None:
            return 404, {"message": "The request version does not exist."}

        # fetch all resource in this cm and create a list of distinct agents
        rvs = await data.Resource.get_list(model=version_id, environment=env.id)

        # Create a dryrun document
        dryrun = await data.DryRun.create(environment=env.id, model=version_id, todo=len(rvs), total=len(rvs))

        agents = await data.ConfigurationModel.get_agents(env.id, version_id)
        await self.agentmanager._ensure_agents(env, agents)

        for agent in agents:
            client = self.get_agent_client(env.id, agent)
            if client is not None:
                self.add_background_task(client.do_dryrun(env.id, dryrun.id, agent, version_id))
            else:
                LOGGER.warning("Agent %s from model %s in env %s is not available for a dryrun", agent, version_id, env.id)

        # Mark the resources in an undeployable state as done
        with (await self.dryrun_lock.acquire()):
            undeployableids = await model.get_undeployable()
            undeployableids = [rid + ",v=%s" % version_id for rid in undeployableids]
            undeployable = await data.Resource.get_resources(environment=env.id, resource_version_ids=undeployableids)
            for res in undeployable:
                parsed_id = Id.parse_id(res.resource_version_id)
                payload = {
                    "changes": {},
                    "id_fields": {
                        "entity_type": res.resource_type,
                        "agent_name": res.agent,
                        "attribute": parsed_id.attribute,
                        "attribute_value": parsed_id.attribute_value,
                        "version": res.model,
                    },
                    "id": res.resource_version_id,
                }
                await data.DryRun.update_resource(dryrun.id, res.resource_version_id, payload)

            skipundeployableids = await model.get_skipped_for_undeployable()
            skipundeployableids = [rid + ",v=%s" % version_id for rid in skipundeployableids]
            skipundeployable = await data.Resource.get_resources(environment=env.id, resource_version_ids=skipundeployableids)
            for res in skipundeployable:
                parsed_id = Id.parse_id(res.resource_version_id)
                payload = {
                    "changes": {},
                    "id_fields": {
                        "entity_type": res.resource_type,
                        "agent_name": res.agent,
                        "attribute": parsed_id.attribute,
                        "attribute_value": parsed_id.attribute_value,
                        "version": res.model,
                    },
                    "id": res.resource_version_id,
                }
                await data.DryRun.update_resource(dryrun.id, res.resource_version_id, payload)

        return 200, {"dryrun": dryrun}

    @protocol.handle(methods.dryrun_list, env="tid")
    async def dryrun_list(self, env: data.Environment, version: Optional[int] = None) -> Apireturn:
        query_args = {}
        query_args["environment"] = env.id
        if version is not None:
            model = await data.ConfigurationModel.get_version(environment=env.id, version=version)
            if model is None:
                return 404, {"message": "The request version does not exist."}

            query_args["model"] = version

        dryruns = await data.DryRun.get_list(**query_args)

        return (
            200,
            {"dryruns": [{"id": x.id, "version": x.model, "date": x.date, "total": x.total, "todo": x.todo} for x in dryruns]},
        )

    @protocol.handle(methods.dryrun_report, dryrun_id="id", env="tid")
    async def dryrun_report(self, env: data.Environment, dryrun_id: uuid.UUID) -> Apireturn:
        dryrun = await data.DryRun.get_by_id(dryrun_id)
        if dryrun is None:
            return 404, {"message": "The given dryrun does not exist!"}

        return 200, {"dryrun": dryrun}

    @protocol.handle(methods.dryrun_update, dryrun_id="id", env="tid")
    async def dryrun_update(self, env: data.Environment, dryrun_id: uuid.UUID, resource: str, changes: JsonType) -> Apireturn:
        with (await self.dryrun_lock.acquire()):
            payload = {"changes": changes, "id_fields": Id.parse_id(resource).to_dict(), "id": resource}
            await data.DryRun.update_resource(dryrun_id, resource, payload)

        return 200

    @protocol.handle(methods.upload_code, code_id="id", env="tid")
    async def upload_code(self, env: data.Environment, code_id: int, resource: str, sources: JsonType) -> Apireturn:
        code = await data.Code.get_version(environment=env.id, version=code_id, resource=resource)
        if code is not None:
            return 500, {"message": "Code for this version has already been uploaded."}

        hasherrors = any((k != hash_file(content[2].encode()) for k, content in sources.items()))
        if hasherrors:
            return 400, {"message": "Hashes in source map do not match to source_code"}

        ret, to_upload = await self.stat_files(sources.keys())

        if ret != 200:
            return ret, to_upload

        for file_hash in to_upload["files"]:
            ret = self.upload_file_internal(file_hash, sources[file_hash][2].encode())
            if ret != 200:
                return ret

        compact = {code_hash: (file_name, module, req) for code_hash, (file_name, module, _, req) in sources.items()}

        code = data.Code(environment=env.id, version=code_id, resource=resource, source_refs=compact)
        await code.insert()

        return 200

    @protocol.handle(methods.upload_code_batched, code_id="id", env="tid")
    async def upload_code_batched(self, env: data.Environment, code_id: int, resources: JsonType) -> Apireturn:
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
                if (
                    len(refs) != 3
                    or not isinstance(refs[0], str)
                    or not isinstance(refs[1], str)
                    or not isinstance(refs[2], list)
                ):
                    return (
                        400,
                        {"message": "The values in the source map should be of the" " form (filename, module, [requirements])"},
                    )

        allrefs = [ref for sourcemap in resources.values() for ref in sourcemap.keys()]

        ret, val = await self.stat_files(allrefs)

        if ret != 200:
            return ret, val

        if len(val["files"]) != 0:
            return 400, {"message": "Not all file references provided are valid", "references": val["files"]}

        code = await data.Code.get_versions(environment=env.id, version=code_id)
        oldmap = {c.resource: c for c in code}

        new = {k: v for k, v in resources.items() if k not in oldmap}
        conflict = [k for k, v in resources.items() if k in oldmap and oldmap[k].source_refs != v]

        if len(conflict) > 0:
            return (
                500,
                {"message": "Some of these items already exists, but with different source files", "references": conflict},
            )

        newcodes = [
            data.Code(environment=env.id, version=code_id, resource=resource, source_refs=hashes)
            for resource, hashes in new.items()
        ]

        await data.Code.insert_many(newcodes)

        return 200

    @protocol.handle(methods.get_code, code_id="id", env="tid")
    async def get_code(self, env: data.Environment, code_id: int, resource: str) -> Apireturn:
        code = await data.Code.get_version(environment=env.id, version=code_id, resource=resource)
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
    async def resource_action_update(
        self,
        env: data.Environment,
        resource_ids: List[str],
        action_id: uuid.UUID,
        action: const.ResourceAction,
        started: datetime.datetime,
        finished: datetime.datetime,
        status: const.ResourceState,
        messages: List[Dict[str, Any]],
        changes: Dict[str, Any],
        change: const.Change,
        send_events: bool,
        keep_increment_cache: bool = False,
    ) -> Apireturn:
        # can update resource state
        is_resource_state_update = action in STATE_UPDATE
        # this ra is finishing
        is_resource_action_finished = finished is not None

        if is_resource_state_update:
            # if status update, status is required
            if status is None:
                error_and_log(
                    "Cannot perform state update without a status.",
                    resource_ids=resource_ids,
                    action=action,
                    action_id=action_id,
                )
            # and needs to be valid
            if status not in VALID_STATES_ON_STATE_UPDATE:
                error_and_log(
                    "Status %s is not valid on action %s" % (status, action),
                    resource_ids=resource_ids,
                    action=action,
                    action_id=action_id,
                )
            if status in TRANSIENT_STATES:
                if not is_resource_action_finished:
                    pass
                else:
                    error_and_log(
                        "The finished field must not be set for transient states",
                        status=status,
                        resource_ids=resource_ids,
                        action=action,
                        action_id=action_id,
                    )
            else:
                if is_resource_action_finished:
                    pass
                else:
                    error_and_log(
                        "The finished field must be set for none transient states",
                        status=status,
                        resource_ids=resource_ids,
                        action=action,
                        action_id=action_id,
                    )

        # validate resources
        resources = await data.Resource.get_resources(env.id, resource_ids)
        if len(resources) == 0 or (len(resources) != len(resource_ids)):
            return (
                404,
                {
                    "message": "The resources with the given ids do not exist in the given environment. "
                    "Only %s of %s resources found." % (len(resources), len(resource_ids))
                },
            )

        # validate transitions
        if is_resource_state_update:
            # no escape from terminal
            if any(resource.status != status and resource.status in TERMINAL_STATES for resource in resources):
                LOGGER.error("Attempting to set undeployable resource to deployable state")
                raise AssertionError("Attempting to set undeployable resource to deployable state")

        # get instance
        resource_action = await data.ResourceAction.get(action_id=action_id)
        if resource_action is None:
            # new
            if started is None:
                return 500, {"message": "A resource action can only be created with a start datetime."}

            resource_action = data.ResourceAction(
                environment=env.id, resource_version_ids=resource_ids, action_id=action_id, action=action, started=started
            )
            await resource_action.insert()
        else:
            # existing
            if resource_action.finished is not None:
                return (
                    500,
                    {
                        "message": "An resource action can only be updated when it has not been finished yet. This action "
                        "finished at %s" % resource_action.finished
                    },
                )

        if len(messages) > 0:
            resource_action.add_logs(messages)
            for msg in messages:
                # All other data is stored in the database. The msg was already formatted at the client side.
                self.log_resource_action(
                    env.id,
                    resource_ids,
                    const.LogLevel[msg["level"]].value,
                    datetime.datetime.strptime(msg["timestamp"], const.TIME_ISOFMT),
                    msg["msg"],
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

        await resource_action.save()

        if is_resource_state_update:
            # transient resource update
            if not is_resource_action_finished:
                for res in resources:
                    await res.update_fields(status=status)
                if not keep_increment_cache:
                    self.clear_env_cache(env)
                return 200

            else:
                # final resource update
                if not keep_increment_cache:
                    self.clear_env_cache(env)

                model_version = None
                for res in resources:
                    await res.update_fields(last_deploy=finished, status=status)
                    model_version = res.model

                    if "purged" in res.attributes and res.attributes["purged"] and status == const.ResourceState.deployed:
                        await data.Parameter.delete_all(environment=env.id, resource_id=res.resource_id)

                await data.ConfigurationModel.mark_done_if_done(env.id, model_version)

                waiting_agents = set(
                    [
                        (Id.parse_id(prov).get_agent_name(), res.resource_version_id)
                        for res in resources
                        for prov in res.provides
                    ]
                )

                for agent, resource_id in waiting_agents:
                    aclient = self.get_agent_client(env.id, agent)
                    if aclient is not None:
                        await aclient.resource_event(env.id, agent, resource_id, send_events, status, change, changes)

        return 200

    # Project handlers
    @protocol.handle(methods.create_project)
    async def create_project(self, name: str, project_id: uuid.UUID) -> Apireturn:
        if project_id is None:
            project_id = uuid.uuid4()
        try:
            project = data.Project(id=project_id, name=name)
            await project.insert()
        except asyncpg.exceptions.UniqueViolationError:
            return 500, {"message": "A project with name %s already exists." % name}

        return 200, {"project": project}

    @protocol.handle(methods.delete_project, project_id="id")
    async def delete_project(self, project_id: uuid.UUID) -> Apireturn:
        project = await data.Project.get_by_id(project_id)
        if project is None:
            return 404, {"message": "The project with given id does not exist."}

        environments = await data.Environment.get_list(project=project.id)
        for env in environments:
            await asyncio.gather(self.agentmanager.stop_agents(env), env.delete_cascade())
            self._close_resource_action_logger(env)

        await project.delete()

        return 200, {}

    @protocol.handle(methods.modify_project, project_id="id")
    async def modify_project(self, project_id: uuid.UUID, name: str) -> Apireturn:
        try:
            project = await data.Project.get_by_id(project_id)
            if project is None:
                return 404, {"message": "The project with given id does not exist."}

            await project.update_fields(name=name)

            return 200, {"project": project}

        except asyncpg.exceptions.UniqueViolationError:
            return 500, {"message": "A project with name %s already exists." % name}

    @protocol.handle(methods.list_projects)
    async def list_projects(self) -> Apireturn:
        projects = await data.Project.get_list()
        return 200, {"projects": projects}

    @protocol.handle(methods.get_project, project_id="id")
    async def get_project(self, project_id: uuid.UUID) -> Apireturn:
        try:
            project = await data.Project.get_by_id(project_id)
            environments = await data.Environment.get_list(project=project_id)

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
    async def create_environment(
        self, project_id: uuid.UUID, name: str, repository: str, branch: str, environment_id: uuid.UUID
    ) -> Apireturn:
        if environment_id is None:
            environment_id = uuid.uuid4()

        if (repository is None and branch is not None) or (repository is not None and branch is None):
            return 500, {"message": "Repository and branch should be set together."}

        # fetch the project first
        project = await data.Project.get_by_id(project_id)
        if project is None:
            return 500, {"message": "The project id for the environment does not exist."}

        # check if an environment with this name is already defined in this project
        envs = await data.Environment.get_list(project=project_id, name=name)
        if len(envs) > 0:
            return (
                500,
                {"message": "Project %s (id=%s) already has an environment with name %s" % (project.name, project.id, name)},
            )

        env = data.Environment(id=environment_id, name=name, project=project_id, repo_url=repository, repo_branch=branch)
        await env.insert()
        return 200, {"environment": env}

    @protocol.handle(methods.modify_environment, environment_id="id")
    async def modify_environment(self, environment_id: uuid.UUID, name: str, repository: str, branch: str) -> Apireturn:
        env = await data.Environment.get_by_id(environment_id)
        if env is None:
            return 404, {"message": "The environment id does not exist."}

        # check if an environment with this name is already defined in this project
        envs = await data.Environment.get_list(project=env.project, name=name)
        if len(envs) > 0 and envs[0].id != environment_id:
            return 500, {"message": "Project with id=%s already has an environment with name %s" % (env.project_id, name)}

        fields = {"name": name}
        if repository is not None:
            fields["repo_url"] = repository

        if branch is not None:
            fields["repo_branch"] = branch

        await env.update_fields(**fields)
        return 200, {"environment": env}

    @protocol.handle(methods.get_environment, environment_id="id")
    async def get_environment(
        self, environment_id: uuid.UUID, versions: Optional[int] = None, resources: Optional[int] = None
    ) -> Apireturn:
        versions = 0 if versions is None else int(versions)
        resources = 0 if resources is None else int(resources)

        env = await data.Environment.get_by_id(environment_id)

        if env is None:
            return 404, {"message": "The environment id does not exist."}

        env_dict = env.to_dict()

        if versions > 0:
            env_dict["versions"] = await data.ConfigurationModel.get_versions(environment_id, limit=versions)

        if resources > 0:
            env_dict["resources"] = await data.Resource.get_resources_report(environment=environment_id)

        return 200, {"environment": env_dict}

    @protocol.handle(methods.list_environments)
    async def list_environments(self) -> Apireturn:
        environments = await data.Environment.get_list()
        dicts = []
        for env in environments:
            env_dict = env.to_dict()
            dicts.append(env_dict)

        return 200, {"environments": dicts}  # @UndefinedVariable

    @protocol.handle(methods.delete_environment, environment_id="id")
    async def delete_environment(self, environment_id: uuid.UUID) -> Apireturn:
        env = await data.Environment.get_by_id(environment_id)
        if env is None:
            return 404, {"message": "The environment with given id does not exist."}

        await asyncio.gather(self.agentmanager.stop_agents(env), env.delete_cascade())

        self._close_resource_action_logger(environment_id)

        return 200

    @protocol.handle(methods.list_settings, env="tid")
    async def list_settings(self, env: data.Environment) -> Apireturn:
        return 200, {"settings": env.settings, "metadata": data.Environment._settings}

    async def _setting_change(self, env: data.Environment, key: str) -> Warning:
        setting = env._settings[key]

        warnings = None
        if setting.recompile:
            LOGGER.info("Environment setting %s changed. Recompiling with update = %s", key, setting.update)
            metadata = {"message": "Recompile for modified setting", "type": "setting", "setting": key}
            warnings = await self._async_recompile(env, setting.update, metadata=metadata)

        if setting.agent_restart:
            LOGGER.info("Environment setting %s changed. Restarting agents.", key)
            await self.agentmanager.restart_agents(env)

        return warnings

    @protocol.handle(methods.set_setting, env="tid", key="id")
    async def set_setting(self, env: data.Environment, key: str, value: Union[PrimitiveTypes, JsonType]) -> Apireturn:
        try:
            await env.set(key, value)
            warnings = await self._setting_change(env, key)
            return attach_warnings(200, None, warnings)
        except KeyError:
            return 404
        except ValueError:
            return 500, {"message": "Invalid value"}

    @protocol.handle(methods.get_setting, env="tid", key="id")
    async def get_setting(self, env: data.Environment, key: str) -> Apireturn:
        try:
            value = await env.get(key)
            return 200, {"value": value, "metadata": data.Environment._settings}
        except KeyError:
            return 404

    @protocol.handle(methods.delete_setting, env="tid", key="id")
    async def delete_setting(self, env: data.Environment, key: str) -> Apireturn:
        try:
            await env.unset(key)
            warnings = await self._setting_change(env, key)
            return attach_warnings(200, None, warnings)
        except KeyError:
            return 404

    @protocol.handle(methods.notify_change_get, env="id")
    async def notify_change_get(self, env: data.Environment, update: bool) -> Apireturn:
        result = await self.notify_change(env, update, {})
        return result

    @protocol.handle(methods.notify_change, env="id")
    async def notify_change(self, env: data.Environment, update: bool, metadata: JsonType) -> Apireturn:
        LOGGER.info("Received change notification for environment %s", env.id)
        if "type" not in metadata:
            metadata["type"] = "api"

        if "message" not in metadata:
            metadata["message"] = "Recompile trigger through API call"

        warnings = await self._async_recompile(env, update, metadata=metadata)

        return attach_warnings(200, None, warnings)

    async def _async_recompile(self, env: data.Environment, update_repo: bool, metadata: JsonType = {}) -> Warnings:
        """
            Recompile an environment in a different thread and taking wait time into account.
        """
        _, warnings = await self.compiler.request_recompile(
            env=env, force_update=update_repo, do_export=True, remote_id=uuid.uuid4(), metadata=metadata
        )
        return warnings

    @protocol.handle(methods.decomission_environment, env="id")
    async def decomission_environment(self, env: data.Environment, metadata: JsonType) -> Apireturn:
        version = int(time.time())
        if metadata is None:
            metadata = {"message": "Decommission of environment", "type": "api"}
        result = await self.put_version(env, version, [], {}, [], {const.EXPORT_META_DATA: metadata})
        return result, {"version": version}

    @protocol.handle(methods.clear_environment, env="id")
    async def clear_environment(self, env: data.Environment) -> Apireturn:
        """
            Clear the environment
        """
        await self.agentmanager.stop_agents(env)
        await env.delete_cascade(only_content=True)

        project_dir = os.path.join(self._server_storage["environments"], str(env.id))
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir)

        return 200

    @protocol.handle(methods.create_token, env="tid")
    async def create_token(self, env: data.Environment, client_types: List[str], idempotent: bool) -> Apireturn:
        """
            Create a new auth token for this environment
        """
        return 200, {"token": encode_token(client_types, str(env.id), idempotent)}

    @protocol.handle(methods.get_server_status)
    async def get_server_status(self) -> StatusResponse:
        try:
            distr = importlib_metadata.distribution("inmanta")
        except importlib_metadata.PackageNotFoundError:
            raise exceptions.ServerError(
                "Could not find version number for the inmanta compiler."
                "Is inmanta installed? Use stuptools install or setuptools dev to install."
            )
        slices = []
        extension_names = set()
        for slice_name, slice in self._server.get_slices().items():
            slices.append(SliceStatus(name=slice_name, status=await slice.get_status()))

            try:
                ext_name = slice_name.split(".")[0]
                package_name = slice.__class__.__module__.split(".")[0]
                distribution = importlib_metadata.distribution(package_name)

                extension_names.add((ext_name, package_name, distribution.version))
            except importlib_metadata.PackageNotFoundError:
                LOGGER.info(
                    "Package %s of slice %s is not packaged in a distribution. Unable to determine its extension.",
                    package_name,
                    slice_name,
                )

        response = StatusResponse(
            version=distr.version,
            license=distr.metadata["License"] if "License" in distr.metadata else "unknown",
            extensions=[
                ExtensionStatus(name=name, package=package, version=version) for name, package, version in extension_names
            ],
            slices=slices,
        )

        return response
