"""
    Copyright 2019 Inmanta

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
import datetime
import logging
import os
import uuid
from collections import abc, defaultdict
from typing import Any, Dict, List, Optional, Sequence, Union, cast

from asyncpg.connection import Connection
from asyncpg.exceptions import UniqueViolationError
from tornado.httputil import url_concat

from inmanta import const, data, util
from inmanta.const import STATE_UPDATE, TERMINAL_STATES, TRANSIENT_STATES, VALID_STATES_ON_STATE_UPDATE, Change, ResourceState
from inmanta.data import APILIMIT, InvalidSort
from inmanta.data.dataview import ResourceHistoryView, ResourceLogsView, ResourcesInVersionView, ResourceView
from inmanta.data.model import (
    AttributeStateChange,
    LatestReleasedResource,
    LogLine,
    ReleasedResourceDetails,
    Resource,
    ResourceAction,
    ResourceHistory,
    ResourceIdStr,
    ResourceLog,
    ResourceType,
    ResourceVersionIdStr,
    VersionedResource,
    VersionedResourceDetails,
)
from inmanta.protocol import handle, methods, methods_v2
from inmanta.protocol.common import ReturnValue
from inmanta.protocol.exceptions import BadRequest, Conflict, NotFound
from inmanta.protocol.return_value_meta import ReturnValueWithMeta
from inmanta.resources import Id
from inmanta.server import SLICE_AGENT_MANAGER, SLICE_DATABASE, SLICE_RESOURCE, SLICE_TRANSPORT
from inmanta.server import config as opt
from inmanta.server import protocol
from inmanta.server.agentmanager import AgentManager
from inmanta.server.validate_filter import InvalidFilter
from inmanta.types import Apireturn, PrimitiveTypes

LOGGER = logging.getLogger(__name__)


def error_and_log(message: str, **context: Any) -> None:
    """
    :param message: message to return both to logger and to remote caller
    :param context: additional context to attach to log
    """
    ctx = ",".join([f"{k}: {v}" for k, v in context.items()])
    LOGGER.error("%s %s", message, ctx)
    raise BadRequest(message)


class ResourceActionLogLine(logging.LogRecord):
    """A special log record that is used to report log lines that come from the agent"""

    def __init__(self, logger_name: str, level: int, msg: str, created: datetime.datetime) -> None:
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


class ResourceService(protocol.ServerSlice):
    """Resource Manager service"""

    agentmanager_service: "AgentManager"

    def __init__(self) -> None:
        super(ResourceService, self).__init__(SLICE_RESOURCE)

        self._resource_action_loggers: Dict[uuid.UUID, logging.Logger] = {}
        self._resource_action_handlers: Dict[uuid.UUID, logging.Handler] = {}

        self._increment_cache: Dict[uuid.UUID, Optional[tuple[abc.Set[ResourceIdStr], abc.Set[ResourceIdStr]]]] = {}
        # lock to ensure only one inflight request
        self._increment_cache_locks: Dict[uuid.UUID, asyncio.Lock] = defaultdict(lambda: asyncio.Lock())

    def get_dependencies(self) -> List[str]:
        return [SLICE_DATABASE, SLICE_AGENT_MANAGER]

    def get_depended_by(self) -> List[str]:
        return [SLICE_TRANSPORT]

    async def prestart(self, server: protocol.Server) -> None:
        await super().prestart(server)
        self.agentmanager_service = cast("AgentManager", server.get_slice(SLICE_AGENT_MANAGER))

    async def start(self) -> None:
        self.schedule(
            data.ResourceAction.purge_logs, opt.server_purge_resource_action_logs_interval.get(), cancel_on_stop=False
        )
        await super().start()

    async def stop(self) -> None:
        await super().stop()
        self._close_resource_action_loggers()

    def clear_env_cache(self, env: data.Environment) -> None:
        LOGGER.log(const.LOG_LEVEL_TRACE, "Clearing cache for %s", env.id)
        self._increment_cache[env.id] = None
        # ??? del self._increment_cache[env.id]

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
        file_handler.setFormatter(logging.Formatter(fmt="%(asctime)s %(levelname)-8s %(name)-10s %(message)s"))
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
                self.close_resource_action_logger(env, logger)
        except KeyError:
            pass

    def close_resource_action_logger(self, env: uuid.UUID, logger: Optional[logging.Logger] = None) -> None:
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
        self, env: uuid.UUID, resource_ids: Sequence[str], log_level: int, ts: datetime.datetime, message: str
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

    @handle(methods.get_resource, resource_id="id", env="tid")
    async def get_resource(
        self,
        env: data.Environment,
        resource_id: ResourceVersionIdStr,
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

    # This endpoint does't have a method associated yet.
    # Intended for use by other slices
    async def get_resources_in_latest_version(
        self,
        environment: data.Environment,
        resource_type: Optional[ResourceType] = None,
        attributes: Dict[PrimitiveTypes, PrimitiveTypes] = {},
    ) -> List[Resource]:
        result = await data.Resource.get_resources_in_latest_version(environment.id, resource_type, attributes)
        return [r.to_dto() for r in result]

    @handle(methods.get_resources_for_agent, env="tid")
    async def get_resources_for_agent(
        self, env: data.Environment, agent: str, version: int, sid: uuid.UUID, incremental_deploy: bool
    ) -> Apireturn:
        if not self.agentmanager_service.is_primary(env, sid, agent):
            return 409, {"message": "This agent is not currently the primary for the endpoint %s (sid: %s)" % (agent, sid)}
        if incremental_deploy:
            if version is not None:
                return 500, {"message": "Cannot request increment for a specific version"}
            result = await self.get_resource_increment_for_agent(env, agent)
        else:
            result = await self.get_all_resources_for_agent(env, agent, version)
        return result

    async def get_all_resources_for_agent(self, env: data.Environment, agent: str, version: int) -> Apireturn:
        started = datetime.datetime.now().astimezone()
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

        # Don't log ResourceActions without resource_version_ids, because
        # no API call exists to retrieve them.
        if resource_ids:
            now = datetime.datetime.now().astimezone()
            log_line = data.LogLine.log(
                logging.INFO, "Resource version pulled by client for agent %(agent)s state", agent=agent
            )
            self.log_resource_action(env.id, resource_ids, logging.INFO, now, log_line.msg)
            ra = data.ResourceAction(
                environment=env.id,
                version=version,
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
        started = datetime.datetime.now().astimezone()

        version = await data.ConfigurationModel.get_version_nr_latest_version(env.id)
        if version is None:
            return 404, {"message": "No version available"}

        increment: Optional[tuple[abc.Set[ResourceIdStr], abc.Set[ResourceIdStr]]] = self._increment_cache.get(env.id, None)
        if increment is None:
            lock = self._increment_cache_locks[env.id]
            async with lock:
                increment = self._increment_cache.get(env.id, None)
                if increment is None:
                    increment = await data.ConfigurationModel.get_increment(env.id, version)
                    self._increment_cache[env.id] = increment

        increment_ids, neg_increment = increment

        # set already done to deployed
        now = datetime.datetime.now().astimezone()

        def on_agent(res: ResourceIdStr) -> bool:
            idr = Id.parse_id(res)
            return idr.get_agent_name() == agent

        neg_increment_version_ids: list[ResourceVersionIdStr] = [
            ResourceVersionIdStr(f"{res_id},v={version}") for res_id in neg_increment if on_agent(res_id)
        ]

        logline = {
            "level": "INFO",
            "msg": "Setting deployed due to known good status",
            "timestamp": util.datetime_utc_isoformat(now),
            "args": [],
        }
        await self.resource_action_update(
            env,
            neg_increment_version_ids,
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

        resources = await data.Resource.get_resources_for_version(env.id, version, agent)

        deploy_model: List[Dict[str, Any]] = []
        resource_ids: List[str] = []

        for rv in resources:
            if rv.resource_id not in increment_ids:
                continue

            # TODO double parsing of ID
            def in_requires(req: ResourceIdStr) -> bool:
                if req in increment_ids:
                    return True
                idr = Id.parse_id(req)
                return idr.get_agent_name() != agent

            rv.attributes["requires"] = [r for r in rv.attributes["requires"] if in_requires(r)]
            deploy_model.append(rv.to_dict())
            resource_ids.append(rv.resource_version_id)

        # Don't log ResourceActions without resource_version_ids, because
        # no API call exists to retrieve them.
        if resource_ids:
            ra = data.ResourceAction(
                environment=env.id,
                version=version,
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

    @handle(methods_v2.resource_deploy_done, env="tid", resource_id="rvid")
    async def resource_deploy_done(
        self,
        env: data.Environment,
        resource_id: Id,
        action_id: uuid.UUID,
        status: ResourceState,
        messages: List[LogLine] = [],
        changes: Dict[str, AttributeStateChange] = {},
        change: Optional[Change] = None,
        keep_increment_cache: bool = False,
    ) -> None:
        resource_id_str = resource_id.resource_version_str()
        finished = datetime.datetime.now().astimezone()
        changes_with_rvid = {resource_id_str: {attr_name: attr_change.dict()} for attr_name, attr_change in changes.items()}

        if status not in VALID_STATES_ON_STATE_UPDATE:
            error_and_log(
                f"Status {status} is not a valid status at the end of a deployment.",
                resource_ids=[resource_id_str],
                action=const.ResourceAction.deploy,
                action_id=action_id,
            )
        if status in TRANSIENT_STATES:
            error_and_log(
                "No transient state can be used to mark a deployment as done.",
                status=status,
                resource_ids=[resource_id_str],
                action=const.ResourceAction.deploy,
                action_id=action_id,
            )

        async with data.Resource.get_connection() as connection:
            async with connection.transaction():
                resource = await data.Resource.get_one(
                    connection=connection,
                    environment=env.id,
                    resource_id=resource_id.resource_str(),
                    model=resource_id.version,
                    # acquire lock on Resource before read and before lock on ResourceAction to prevent conflicts with
                    # cascading deletes
                    lock=data.RowLockMode.FOR_UPDATE,
                )
                if resource is None:
                    raise NotFound("The resource with the given id does not exist in the given environment.")

                # no escape from terminal
                if resource.status != status and resource.status in TERMINAL_STATES:
                    LOGGER.error("Attempting to set undeployable resource to deployable state")
                    raise AssertionError("Attempting to set undeployable resource to deployable state")

                resource_action = await data.ResourceAction.get(action_id=action_id, connection=connection)
                if resource_action is None:
                    raise NotFound(
                        f"No resource action exists for action_id {action_id}. Ensure "
                        f"`/resource/<resource_id>/deploy/start` is called first. "
                    )
                if resource_action.finished is not None:
                    raise Conflict(
                        f"Resource action with id {resource_id_str} was already marked as done at {resource_action.finished}."
                    )

                for log in messages:
                    # All other data is stored in the database. The msg was already formatted at the client side.
                    self.log_resource_action(
                        env.id,
                        [resource_id_str],
                        log.level.to_int,
                        log.timestamp,
                        log.msg,
                    )

                await resource_action.set_and_save(
                    messages=[
                        {
                            **log.dict(),
                            "timestamp": log.timestamp.astimezone().isoformat(timespec="microseconds"),
                        }
                        for log in messages
                    ],
                    changes=changes_with_rvid,
                    status=status,
                    change=change,
                    finished=finished,
                    connection=connection,
                )

                # final resource update
                if not keep_increment_cache:
                    self.clear_env_cache(env)

                await resource.update_fields(
                    last_deploy=finished,
                    status=status,
                    last_non_deploying_status=const.NonDeployingResourceState(status),
                    connection=connection,
                )

                if "purged" in resource.attributes and resource.attributes["purged"] and status == const.ResourceState.deployed:
                    await data.Parameter.delete_all(environment=env.id, resource_id=resource.resource_id, connection=connection)

        self.add_background_task(data.ConfigurationModel.mark_done_if_done(env.id, resource.model))

        waiting_agents = set([(Id.parse_id(prov).get_agent_name(), resource.resource_version_id) for prov in resource.provides])
        for agent, resource_id in waiting_agents:
            aclient = self.agentmanager_service.get_agent_client(env.id, agent)
            if aclient is not None:
                if change is None:
                    change = const.Change.nochange
                await aclient.resource_event(
                    tid=env.id,
                    id=agent,
                    resource=resource_id,
                    send_events=False,
                    state=status,
                    change=change,
                    changes=changes_with_rvid,
                )

    @handle(methods.resource_action_update, env="tid")
    async def resource_action_update(
        self,
        env: data.Environment,
        resource_ids: List[ResourceVersionIdStr],
        action_id: uuid.UUID,
        action: const.ResourceAction,
        started: datetime.datetime,
        finished: datetime.datetime,
        status: Optional[Union[const.ResourceState, const.DeprecatedResourceState]],
        messages: List[Dict[str, Any]],
        changes: Dict[str, Any],
        change: const.Change,
        send_events: bool,
        keep_increment_cache: bool = False,
        *,
        connection: Optional[Connection] = None,
    ) -> Apireturn:
        def convert_legacy_state(
            status: Optional[Union[const.ResourceState, const.DeprecatedResourceState]]
        ) -> Optional[const.ResourceState]:
            if status is None or isinstance(status, const.ResourceState):
                return status
            if status == const.DeprecatedResourceState.processing_events:
                return const.ResourceState.deploying
            else:
                raise BadRequest(f"Unsupported deprecated resources state {status.value}")

        status = convert_legacy_state(status)

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

        assert all(Id.is_resource_version_id(rvid) for rvid in resource_ids)

        resources: List[data.Resource]
        async with data.Resource.get_connection(connection) as connection:
            async with connection.transaction():
                # validate resources
                resources = await data.Resource.get_resources(
                    env.id,
                    resource_ids,
                    # acquire lock on Resource before read and before lock on ResourceAction to prevent conflicts with
                    # cascading deletes
                    lock=data.RowLockMode.FOR_UPDATE,
                    connection=connection,
                )
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
                resource_action = await data.ResourceAction.get(action_id=action_id, connection=connection)
                if resource_action is None:
                    # new
                    if started is None:
                        return 500, {"message": "A resource action can only be created with a start datetime."}

                    version = Id.parse_id(resource_ids[0]).version
                    resource_action = data.ResourceAction(
                        environment=env.id,
                        version=version,
                        resource_version_ids=resource_ids,
                        action_id=action_id,
                        action=action,
                        started=started,
                    )
                    await resource_action.insert(connection=connection)
                else:
                    # existing
                    if resource_action.finished is not None:
                        return (
                            500,
                            {
                                "message": (
                                    "An resource action can only be updated when it has not been finished yet. This action "
                                    "finished at %s" % resource_action.finished
                                )
                            },
                        )

                def parse_timestamp(timestamp: str) -> datetime.datetime:
                    try:
                        return datetime.datetime.strptime(timestamp, const.TIME_ISOFMT + "%z")
                    except ValueError:
                        # interpret naive datetimes as UTC
                        return datetime.datetime.strptime(timestamp, const.TIME_ISOFMT).replace(tzinfo=datetime.timezone.utc)

                for msg in messages:
                    # All other data is stored in the database. The msg was already formatted at the client side.
                    self.log_resource_action(
                        env.id,
                        resource_ids,
                        const.LogLevel(msg["level"]).to_int,
                        parse_timestamp(msg["timestamp"]),
                        msg["msg"],
                    )
                await resource_action.set_and_save(
                    messages=[
                        {
                            **msg,
                            "timestamp": parse_timestamp(msg["timestamp"]).isoformat(timespec="microseconds"),
                        }
                        for msg in messages
                    ],
                    changes=changes,
                    status=status,
                    change=change,
                    finished=finished,
                    connection=connection,
                )

                async def update_fields_resource(
                    resource: data.Resource, connection: Optional[Connection] = None, **kwargs: object
                ) -> None:
                    """
                    This method ensures that the `last_non_deploying_status` field in the database
                    is updated correctly when the `status` field of a resource is updated.
                    """
                    if "status" in kwargs and kwargs["status"] is not ResourceState.deploying:
                        kwargs["last_non_deploying_status"] = const.NonDeployingResourceState(kwargs["status"])
                    await resource.update_fields(**kwargs, connection=connection)

                if is_resource_state_update:
                    # transient resource update
                    if not is_resource_action_finished:
                        for res in resources:
                            await update_fields_resource(res, status=status, connection=connection)
                        if not keep_increment_cache:
                            self.clear_env_cache(env)
                        return 200

                    else:
                        # final resource update
                        if not keep_increment_cache:
                            self.clear_env_cache(env)

                        model_version = None
                        for res in resources:
                            await update_fields_resource(res, last_deploy=finished, status=status, connection=connection)
                            model_version = res.model

                            if (
                                "purged" in res.attributes
                                and res.attributes["purged"]
                                and status == const.ResourceState.deployed
                            ):
                                await data.Parameter.delete_all(
                                    environment=env.id, resource_id=res.resource_id, connection=connection
                                )

        if is_resource_state_update and is_resource_action_finished:
            self.add_background_task(data.ConfigurationModel.mark_done_if_done(env.id, model_version))
            waiting_agents = set(
                [(Id.parse_id(prov).get_agent_name(), res.resource_version_id) for res in resources for prov in res.provides]
            )

            for agent, resource_id in waiting_agents:
                aclient = self.agentmanager_service.get_agent_client(env.id, agent)
                if aclient is not None:
                    if change is None:
                        change = const.Change.nochange
                    self.add_background_task(
                        aclient.resource_event(env.id, agent, resource_id, send_events, status, change, changes)
                    )

        return 200

    @handle(methods_v2.resource_deploy_start, env="tid", resource_id="rvid")
    async def resource_deploy_start(
        self,
        env: data.Environment,
        resource_id: Id,
        action_id: uuid.UUID,
    ) -> Dict[ResourceVersionIdStr, const.ResourceState]:
        resource_id_str = resource_id.resource_version_str()
        async with data.Resource.get_connection() as connection:
            async with connection.transaction():
                resource = await data.Resource.get_one(
                    connection=connection,
                    environment=env.id,
                    resource_id=resource_id.resource_str(),
                    model=resource_id.version,
                )
                if resource is None:
                    raise NotFound(message=f"Environment {env.id} doesn't contain a resource with id {resource_id_str}")

                resource_action = data.ResourceAction(
                    environment=env.id,
                    version=resource_id.version,
                    resource_version_ids=[resource_id_str],
                    action_id=action_id,
                    action=const.ResourceAction.deploy,
                    started=datetime.datetime.now().astimezone(),
                    messages=[
                        data.LogLine.log(
                            logging.INFO,
                            "Resource deploy started on agent %(agent)s, setting status to deploying",
                            agent=resource_id.agent_name,
                        )
                    ],
                    status=const.ResourceState.deploying,
                )
                try:
                    await resource_action.insert(connection=connection)
                except UniqueViolationError:
                    raise Conflict(message=f"A resource action with id {action_id} already exists.")

                await resource.update_fields(connection=connection, status=const.ResourceState.deploying)

            self.clear_env_cache(env)

            return await data.Resource.get_last_non_deploying_state_for_dependencies(
                environment=env.id, resource_version_id=resource_id, connection=connection
            )

    @handle(methods_v2.get_resource_actions, env="tid")
    async def get_resource_actions(
        self,
        env: data.Environment,
        resource_type: Optional[str] = None,
        agent: Optional[str] = None,
        attribute: Optional[str] = None,
        attribute_value: Optional[str] = None,
        log_severity: Optional[str] = None,
        limit: Optional[int] = 0,
        action_id: Optional[uuid.UUID] = None,
        first_timestamp: Optional[datetime.datetime] = None,
        last_timestamp: Optional[datetime.datetime] = None,
    ) -> ReturnValue[List[ResourceAction]]:
        if (attribute and not attribute_value) or (not attribute and attribute_value):
            raise BadRequest(
                f"Attribute and attribute_value should both be supplied to use them filtering. "
                f"Received attribute: {attribute}, attribute_value: {attribute_value}"
            )
        if first_timestamp and last_timestamp:
            raise BadRequest(
                f"Only one of the parameters first_timestamp and last_timestamp should be used "
                f"Received first_timestamp: {first_timestamp}, last_timestamp: {last_timestamp}"
            )
        if action_id and not (first_timestamp or last_timestamp):
            raise BadRequest(
                f"The action_id parameter should be used in combination with either the first_timestamp or the last_timestamp "
                f"Received action_id: {action_id}, first_timestamp: {first_timestamp}, last_timestamp: {last_timestamp}"
            )

        if limit is None:
            limit = APILIMIT
        elif limit > APILIMIT:
            raise BadRequest(f"limit parameter can not exceed {APILIMIT}, got {limit}.")

        resource_actions = await data.ResourceAction.query_resource_actions(
            env.id,
            resource_type,
            agent,
            attribute=attribute,
            attribute_value=attribute_value,
            log_severity=log_severity,
            limit=limit,
            action_id=action_id,
            first_timestamp=first_timestamp,
            last_timestamp=last_timestamp,
        )
        resource_action_dtos = [resource_action.to_dto() for resource_action in resource_actions]
        links = {}

        def _get_query_params(
            resource_type: Optional[str] = None,
            agent: Optional[str] = None,
            attribute: Optional[str] = None,
            attribute_value: Optional[str] = None,
            log_severity: Optional[str] = None,
            limit: Optional[int] = 0,
        ) -> dict:
            query_params = {
                "resource_type": resource_type,
                "agent": agent,
                "attribute": attribute,
                "attribute_value": attribute_value,
                "log_severity": log_severity,
                "limit": limit,
            }
            query_params = {param_key: param_value for param_key, param_value in query_params.items() if param_value}
            return query_params

        if limit and resource_action_dtos:
            base_url = "/api/v2/resource_actions"
            common_query_params = _get_query_params(resource_type, agent, attribute, attribute_value, log_severity, limit)
            # Next is always earlier with regards to 'started' time
            next_params = common_query_params.copy()
            next_params["last_timestamp"] = resource_action_dtos[-1].started
            next_params["action_id"] = resource_action_dtos[-1].action_id
            links["next"] = url_concat(base_url, next_params)
            previous_params = common_query_params.copy()
            previous_params["first_timestamp"] = resource_action_dtos[0].started
            previous_params["action_id"] = resource_action_dtos[0].action_id
            links["prev"] = url_concat(base_url, previous_params)
        return_value = ReturnValue(response=resource_action_dtos, links=links if links else None)
        return return_value

    @handle(methods_v2.get_resource_events, env="tid", resource_id="rvid")
    async def get_resource_events(
        self,
        env: data.Environment,
        resource_id: Id,
    ) -> Dict[ResourceIdStr, List[ResourceAction]]:
        return {
            k: [ra.to_dto() for ra in v] for k, v in (await data.ResourceAction.get_resource_events(env, resource_id)).items()
        }

    @handle(methods_v2.resource_did_dependency_change, env="tid", resource_id="rvid")
    async def resource_did_dependency_change(
        self,
        env: data.Environment,
        resource_id: Id,
    ) -> bool:
        # This resource has been deployed before => determine whether it should be redeployed based on events
        return any(
            True
            for dependency, actions in (
                await data.ResourceAction.get_resource_events(env, resource_id, const.Change.nochange)
            ).items()
            for action in actions
        )

    @handle(methods_v2.resource_list, env="tid")
    async def resource_list(
        self,
        env: data.Environment,
        limit: Optional[int] = None,
        first_id: Optional[ResourceVersionIdStr] = None,
        last_id: Optional[ResourceVersionIdStr] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        filter: Optional[Dict[str, List[str]]] = None,
        sort: str = "resource_type.desc",
        deploy_summary: bool = False,
    ) -> ReturnValueWithMeta[Sequence[LatestReleasedResource]]:

        try:
            handler = ResourceView(env, limit, first_id, last_id, start, end, filter, sort, deploy_summary)

            out = await handler.execute()
            if deploy_summary:
                out.metadata["deploy_summary"] = await data.Resource.get_resource_deploy_summary(env.id)
            return out

        except (InvalidFilter, InvalidSort, data.InvalidQueryParameter, data.InvalidFieldNameException) as e:
            raise BadRequest(e.message) from e

        # TODO: optimize for no orphans

    @handle(methods_v2.resource_details, env="tid")
    async def resource_details(self, env: data.Environment, rid: ResourceIdStr) -> ReleasedResourceDetails:

        details = await data.Resource.get_resource_details(env.id, rid)
        if not details:
            raise NotFound("The resource with the given id does not exist, or was not released yet in the given environment.")
        return details

    @handle(methods_v2.resource_history, env="tid")
    async def resource_history(
        self,
        env: data.Environment,
        rid: ResourceIdStr,
        limit: Optional[int] = None,
        first_id: Optional[str] = None,
        last_id: Optional[str] = None,
        start: Optional[datetime.datetime] = None,
        end: Optional[datetime.datetime] = None,
        sort: str = "date.desc",
    ) -> ReturnValue[Sequence[ResourceHistory]]:
        try:
            handler = ResourceHistoryView(
                environment=env,
                rid=rid,
                limit=limit,
                sort=sort,
                first_id=first_id,
                last_id=last_id,
                start=start,
                end=end,
            )
            out = await handler.execute()
            return out
        except (InvalidFilter, InvalidSort, data.InvalidQueryParameter, data.InvalidFieldNameException) as e:
            raise BadRequest(e.message) from e

    @handle(methods_v2.resource_logs, env="tid")
    async def resource_logs(
        self,
        env: data.Environment,
        rid: ResourceIdStr,
        limit: Optional[int] = None,
        start: Optional[datetime.datetime] = None,
        end: Optional[datetime.datetime] = None,
        filter: Optional[Dict[str, List[str]]] = None,
        sort: str = "timestamp.desc",
    ) -> ReturnValue[Sequence[ResourceLog]]:
        try:
            handler = ResourceLogsView(environment=env, rid=rid, limit=limit, sort=sort, start=start, end=end, filter=filter)
            out = await handler.execute()
            return out
        except (InvalidFilter, InvalidSort, data.InvalidQueryParameter, data.InvalidFieldNameException) as e:
            raise BadRequest(e.message) from e

    @handle(methods_v2.get_resources_in_version, env="tid")
    async def get_resources_in_version(
        self,
        env: data.Environment,
        version: int,
        limit: Optional[int] = None,
        first_id: Optional[ResourceVersionIdStr] = None,
        last_id: Optional[ResourceVersionIdStr] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        filter: Optional[Dict[str, List[str]]] = None,
        sort: str = "resource_type.desc",
    ) -> ReturnValueWithMeta[Sequence[VersionedResource]]:

        try:
            handler = ResourcesInVersionView(env, version, limit, filter, sort, first_id, last_id, start, end)
            return await handler.execute()
        except (InvalidFilter, InvalidSort, data.InvalidQueryParameter, data.InvalidFieldNameException) as e:
            raise BadRequest(e.message) from e

    @handle(methods_v2.versioned_resource_details, env="tid")
    async def versioned_resource_details(
        self, env: data.Environment, version: int, rid: ResourceIdStr
    ) -> VersionedResourceDetails:
        resource = await data.Resource.get_versioned_resource_details(environment=env.id, version=version, resource_id=rid)
        if not resource:
            raise NotFound("The resource with the given id does not exist")
        return resource
