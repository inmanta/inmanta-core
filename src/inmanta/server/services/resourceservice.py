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
from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, cast

from tornado.httputil import url_concat

from inmanta import const, data, util
from inmanta.const import STATE_UPDATE, TERMINAL_STATES, TRANSIENT_STATES, VALID_STATES_ON_STATE_UPDATE
from inmanta.data import APILIMIT, InvalidSort, QueryType, ResourceOrder, VersionedResourceOrder
from inmanta.data.model import (
    LatestReleasedResource,
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
from inmanta.data.paging import (
    QueryIdentifier,
    ResourceHistoryPagingCountsProvider,
    ResourceHistoryPagingHandler,
    ResourceLogPagingCountsProvider,
    ResourceLogPagingHandler,
    ResourcePagingCountsProvider,
    ResourcePagingHandler,
    ResourceQueryIdentifier,
    VersionedQueryIdentifier,
    VersionedResourcePagingCountsProvider,
    VersionedResourcePagingHandler,
)
from inmanta.protocol import handle, methods, methods_v2
from inmanta.protocol.common import ReturnValue
from inmanta.protocol.exceptions import BadRequest, NotFound
from inmanta.protocol.return_value_meta import ReturnValueWithMeta
from inmanta.resources import Id
from inmanta.server import SLICE_AGENT_MANAGER, SLICE_DATABASE, SLICE_RESOURCE, SLICE_TRANSPORT
from inmanta.server import config as opt
from inmanta.server import protocol
from inmanta.server.agentmanager import AgentManager
from inmanta.server.validate_filter import (
    InvalidFilter,
    ResourceFilterValidator,
    ResourceLogFilterValidator,
    VersionedResourceFilterValidator,
)
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

        self._increment_cache: Dict[uuid.UUID, Optional[Tuple[Set[ResourceVersionIdStr], List[ResourceVersionIdStr]]]] = {}
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
        self.schedule(data.ResourceAction.purge_logs, opt.server_purge_resource_action_logs_interval.get())
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

        increment = self._increment_cache.get(env.id, None)
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

        def on_agent(res: ResourceVersionIdStr) -> bool:
            idr = Id.parse_id(res)
            return idr.get_agent_name() == agent

        neg_increment = [res_id for res_id in neg_increment if on_agent(res_id)]

        logline = {
            "level": "INFO",
            "msg": "Setting deployed due to known good status",
            "timestamp": util.datetime_utc_isoformat(now),
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

            def in_requires(req: ResourceVersionIdStr) -> bool:
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

    @protocol.handle(methods.resource_action_update, env="tid")
    async def resource_action_update(
        self,
        env: data.Environment,
        resource_ids: List[ResourceVersionIdStr],
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

        resources: List[data.Resource]
        async with data.Resource.get_connection() as connection:
            async with connection.transaction():
                # validate resources
                resources = await data.Resource.get_resources(env.id, resource_ids, connection=connection)
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

                if len(messages) > 0:

                    def parse_timestamp(timestamp: str) -> datetime.datetime:
                        try:
                            return datetime.datetime.strptime(timestamp, const.TIME_ISOFMT + "%z")
                        except ValueError:
                            # interpret naive datetimes as UTC
                            return datetime.datetime.strptime(timestamp, const.TIME_ISOFMT).replace(
                                tzinfo=datetime.timezone.utc
                            )

                    resource_action.add_logs(
                        [
                            {**msg, "timestamp": parse_timestamp(msg["timestamp"]).isoformat(timespec="microseconds")}
                            for msg in messages
                        ]
                    )
                    for msg in messages:
                        # All other data is stored in the database. The msg was already formatted at the client side.
                        self.log_resource_action(
                            env.id,
                            resource_ids,
                            const.LogLevel(msg["level"]).to_int,
                            parse_timestamp(msg["timestamp"]),
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

                await resource_action.save(connection=connection)

                if is_resource_state_update:
                    # transient resource update
                    if not is_resource_action_finished:
                        for res in resources:
                            await res.update_fields(status=status, connection=connection)
                        if not keep_increment_cache:
                            self.clear_env_cache(env)
                        return 200

                    else:
                        # final resource update
                        if not keep_increment_cache:
                            self.clear_env_cache(env)

                        model_version = None
                        for res in resources:
                            await res.update_fields(last_deploy=finished, status=status, connection=connection)
                            model_version = res.model

                            if (
                                "purged" in res.attributes
                                and res.attributes["purged"]
                                and status == const.ResourceState.deployed
                            ):
                                await data.Parameter.delete_all(
                                    environment=env.id, resource_id=res.resource_id, connection=connection
                                )

                        await data.ConfigurationModel.mark_done_if_done(env.id, model_version, connection=connection)

        if is_resource_state_update and is_resource_action_finished:
            waiting_agents = set(
                [(Id.parse_id(prov).get_agent_name(), res.resource_version_id) for res in resources for prov in res.provides]
            )

            for agent, resource_id in waiting_agents:
                aclient = self.agentmanager_service.get_agent_client(env.id, agent)
                if aclient is not None:
                    if change is None:
                        change = const.Change.nochange
                    await aclient.resource_event(env.id, agent, resource_id, send_events, status, change, changes)

        return 200

    @protocol.handle(methods_v2.get_resource_actions, env="tid")
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

    @protocol.handle(methods_v2.resource_list, env="tid")
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
    ) -> ReturnValue[List[LatestReleasedResource]]:
        if limit is None:
            limit = APILIMIT
        elif limit > APILIMIT:
            raise BadRequest(f"limit parameter can not exceed {APILIMIT}, got {limit}.")

        query: Dict[str, Tuple[QueryType, object]] = {}
        if filter:
            try:
                query.update(ResourceFilterValidator().process_filters(filter))
            except InvalidFilter as e:
                raise BadRequest(e.message) from e
        try:
            resource_order = ResourceOrder.parse_from_string(sort)
        except InvalidSort as e:
            raise BadRequest(e.message) from e
        try:
            dtos = await data.Resource.get_released_resources(
                database_order=resource_order,
                limit=limit,
                environment=env.id,
                first_id=first_id,
                last_id=last_id,
                start=start,
                end=end,
                connection=None,
                **query,
            )
        except (data.InvalidQueryParameter, data.InvalidFieldNameException) as e:
            raise BadRequest(e.message)

        paging_handler = ResourcePagingHandler(ResourcePagingCountsProvider(data.Resource))
        paging_metadata = await paging_handler.prepare_paging_metadata(
            QueryIdentifier(environment=env.id), dtos, query, limit, resource_order
        )
        links = await paging_handler.prepare_paging_links(
            dtos,
            filter,
            resource_order,
            limit,
            first_id=first_id,
            last_id=last_id,
            start=start,
            end=end,
            has_next=paging_metadata.after > 0,
            has_prev=paging_metadata.before > 0,
            deploy_summary=deploy_summary,
        )
        metadata = vars(paging_metadata)
        if deploy_summary:
            metadata["deploy_summary"] = await data.Resource.get_resource_deploy_summary(env.id)

        return ReturnValueWithMeta(response=dtos, links=links if links else {}, metadata=metadata)

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
    ) -> ReturnValue[List[ResourceHistory]]:
        if limit is None:
            limit = APILIMIT
        elif limit > APILIMIT:
            raise BadRequest(f"limit parameter can not exceed {APILIMIT}, got {limit}.")

        try:
            resource_order = data.ResourceHistoryOrder.parse_from_string(sort)
        except InvalidSort as e:
            raise BadRequest(e.message) from e
        try:
            history = await data.Resource.get_resource_history(
                env.id,
                rid,
                database_order=resource_order,
                first_id=first_id,
                last_id=last_id,
                start=start,
                end=end,
                limit=limit,
            )
        except (data.InvalidQueryParameter, data.InvalidFieldNameException) as e:
            raise BadRequest(e.message)

        paging_handler = ResourceHistoryPagingHandler(ResourceHistoryPagingCountsProvider(data.Resource), rid)
        metadata = await paging_handler.prepare_paging_metadata(
            ResourceQueryIdentifier(environment=env.id, resource_id=rid),
            history,
            limit=limit,
            database_order=resource_order,
            db_query={},
        )
        links = await paging_handler.prepare_paging_links(
            history,
            database_order=resource_order,
            limit=limit,
            filter=None,
            first_id=first_id,
            last_id=last_id,
            start=start,
            end=end,
            has_next=metadata.after > 0,
            has_prev=metadata.before > 0,
        )
        return ReturnValueWithMeta(response=history, links=links if links else {}, metadata=vars(metadata))

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
    ) -> ReturnValue[List[ResourceLog]]:
        if limit is None:
            limit = APILIMIT
        elif limit > APILIMIT:
            raise BadRequest(f"limit parameter can not exceed {APILIMIT}, got {limit}.")
        try:
            resource_order = data.ResourceLogOrder.parse_from_string(sort)
        except InvalidSort as e:
            raise BadRequest(e.message) from e
        query: Dict[str, Tuple[QueryType, object]] = {}
        if filter:
            try:
                query.update(ResourceLogFilterValidator().process_filters(filter))
            except InvalidFilter as e:
                raise BadRequest(e.message) from e
        try:
            dtos = await data.ResourceAction.get_logs_paged(
                resource_order, limit, env.id, rid, start=start, end=end, connection=None, **query
            )
        except (data.InvalidQueryParameter, data.InvalidFieldNameException) as e:
            raise BadRequest(e.message)
        paging_handler = ResourceLogPagingHandler(ResourceLogPagingCountsProvider(data.ResourceAction), rid)
        metadata = await paging_handler.prepare_paging_metadata(
            ResourceQueryIdentifier(environment=env.id, resource_id=rid), dtos, query, limit, resource_order
        )
        links = await paging_handler.prepare_paging_links(
            dtos,
            filter,
            resource_order,
            limit,
            first_id=None,
            last_id=None,
            start=start,
            end=end,
            has_next=metadata.after > 0,
            has_prev=metadata.before > 0,
        )

        return ReturnValueWithMeta(response=dtos, links=links if links else {}, metadata=vars(metadata))

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
    ) -> ReturnValue[List[VersionedResource]]:
        if limit is None:
            limit = APILIMIT
        elif limit > APILIMIT:
            raise BadRequest(f"limit parameter can not exceed {APILIMIT}, got {limit}.")

        query: Dict[str, Tuple[QueryType, object]] = {}
        if filter:
            try:
                query.update(VersionedResourceFilterValidator().process_filters(filter))
            except InvalidFilter as e:
                raise BadRequest(e.message) from e
        try:
            resource_order = VersionedResourceOrder.parse_from_string(sort)
        except InvalidSort as e:
            raise BadRequest(e.message) from e
        try:
            dtos = await data.Resource.get_versioned_resources(
                version=version,
                database_order=resource_order,
                limit=limit,
                environment=env.id,
                first_id=first_id,
                last_id=last_id,
                start=start,
                end=end,
                connection=None,
                **query,
            )
        except (data.InvalidQueryParameter, data.InvalidFieldNameException) as e:
            raise BadRequest(e.message)

        paging_handler = VersionedResourcePagingHandler(VersionedResourcePagingCountsProvider(), version)
        metadata = await paging_handler.prepare_paging_metadata(
            VersionedQueryIdentifier(environment=env.id, version=version), dtos, query, limit, resource_order
        )
        links = await paging_handler.prepare_paging_links(
            dtos,
            filter,
            resource_order,
            limit,
            first_id=first_id,
            last_id=last_id,
            start=start,
            end=end,
            has_next=metadata.after > 0,
            has_prev=metadata.before > 0,
        )

        return ReturnValueWithMeta(response=dtos, links=links if links else {}, metadata=vars(metadata))

    @handle(methods_v2.versioned_resource_details, env="tid")
    async def versioned_resource_details(
        self, env: data.Environment, version: int, rid: ResourceIdStr
    ) -> VersionedResourceDetails:
        resource = await data.Resource.get_versioned_resource_details(environment=env.id, version=version, resource_id=rid)
        if not resource:
            raise NotFound("The resource with the given id does not exist")
        return resource
