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
import typing
import uuid
from collections import abc, defaultdict
from collections.abc import Sequence
from typing import Any, Callable, Optional, Union, cast

from asyncpg.connection import Connection
from pydantic import ValidationError
from tornado.httputil import url_concat

from inmanta import const, data, util
from inmanta.const import STATE_UPDATE, TERMINAL_STATES, TRANSIENT_STATES, VALID_STATES_ON_STATE_UPDATE, Change, ResourceState
from inmanta.data import APILIMIT, InvalidSort, model
from inmanta.data.dataview import (
    DiscoveredResourceView,
    ResourceHistoryView,
    ResourceLogsView,
    ResourcesInVersionView,
    ResourceView,
)
from inmanta.data.model import (
    DiscoveredResourceABC,
    LatestReleasedResource,
    LinkedDiscoveredResource,
    ReleasedResourceDetails,
    Resource,
    ResourceAction,
    ResourceHistory,
    ResourceLog,
    VersionedResource,
    VersionedResourceDetails,
)
from inmanta.db.util import ConnectionMaybeInTransaction, ConnectionNotInTransaction
from inmanta.protocol import handle, methods, methods_v2
from inmanta.protocol.common import ReturnValue
from inmanta.protocol.exceptions import BadRequest, Forbidden, NotFound, ServerError
from inmanta.protocol.return_value_meta import ReturnValueWithMeta
from inmanta.resources import Id
from inmanta.server import SLICE_AGENT_MANAGER, SLICE_DATABASE, SLICE_ENVIRONMENT, SLICE_RESOURCE, SLICE_TRANSPORT, agentmanager
from inmanta.server import config as opt
from inmanta.server import extensions, protocol
from inmanta.server.services.environmentlistener import EnvironmentAction, EnvironmentListener
from inmanta.server.validate_filter import InvalidFilter
from inmanta.types import Apireturn, JsonType, PrimitiveTypes, ResourceIdStr, ResourceType, ResourceVersionIdStr
from inmanta.util import parse_timestamp

resource_discovery = extensions.BoolFeature(
    slice=SLICE_RESOURCE,
    name="resource_discovery",
    description="Enable resource discovery. This feature controls the APIs it does not affect the use of discovery resources.",
)


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


class ResourceService(protocol.ServerSlice, EnvironmentListener):
    """Resource Manager service"""

    agentmanager_service: "agentmanager.AgentManager"

    def __init__(self) -> None:
        super().__init__(SLICE_RESOURCE)

        # Dict: environment_id: (model_version, increment, negative_increment, negative_increment_per_agent, run_ahead_lock)
        self._increment_cache: dict[
            uuid.UUID,
            Optional[
                tuple[
                    int,
                    abc.Set[ResourceIdStr],
                    abc.Set[ResourceIdStr],
                    abc.Mapping[str, abc.Set[ResourceIdStr]],
                    Optional[asyncio.Event],
                ]
            ],
        ] = {}
        # lock to ensure only one inflight request
        self._increment_cache_locks: dict[uuid.UUID, asyncio.Lock] = defaultdict(lambda: asyncio.Lock())
        self._resource_action_logger = logging.getLogger(const.NAME_RESOURCE_ACTION_LOGGER)

    def get_dependencies(self) -> list[str]:
        return [SLICE_DATABASE, SLICE_AGENT_MANAGER]

    def get_depended_by(self) -> list[str]:
        return [SLICE_TRANSPORT]

    def define_features(self) -> list[extensions.Feature]:
        return [resource_discovery]

    async def prestart(self, server: protocol.Server) -> None:
        await super().prestart(server)
        self.agentmanager_service = cast("agentmanager.AgentManager", server.get_slice(SLICE_AGENT_MANAGER))
        # This is difficult to type without import loop
        # The type is EnvironmentService
        server.get_slice(SLICE_ENVIRONMENT).register_listener_for_multiple_actions(
            self, [EnvironmentAction.deleted, EnvironmentAction.cleared]
        )

    async def start(self) -> None:
        self.schedule(
            data.ResourceAction.purge_logs, opt.server_purge_resource_action_logs_interval.get(), cancel_on_stop=False
        )
        await super().start()

    async def stop(self) -> None:
        await super().stop()

    def clear_env_cache(self, env: data.Environment | model.Environment) -> None:
        LOGGER.log(const.LOG_LEVEL_TRACE, "Clearing cache for %s", env.id)
        self._increment_cache[env.id] = None

    async def environment_action_cleared(self, env: model.Environment) -> None:
        """
        Will be called when the environment is cleared
        :param env: The environment that is cleared
        """
        self.clear_env_cache(env)

    async def environment_action_deleted(self, env: model.Environment) -> None:
        """
        Will be called when the environment is deleted
        :param env: The environment that is deleted
        """
        self.clear_env_cache(env)

    def get_resource_action_logger(self, environment: uuid.UUID) -> logging.Logger:
        """Get the resource action logger for the given environment.
        :param environment: The environment to get a logger for
        :return: The logger for the given environment.
        """
        return self._resource_action_logger.getChild(str(environment))

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
        log_action: const.ResourceAction,
        log_limit: int,
        connection: Optional[Connection] = None,
    ) -> Apireturn:
        # Validate resource version id
        try:
            Id.parse_resource_version_id(resource_id)
        except ValueError:
            return 400, {"message": f"{resource_id} is not a valid resource version id"}

        async with data.ResourceAction.get_connection(connection) as con:
            resv = await data.Resource.get(env.id, resource_id, con)
            if resv is None:
                return 404, {"message": "The resource with the given id does not exist in the given environment"}

            actions: list[data.ResourceAction] = []
            if bool(logs):
                action_name = None
                if log_action is not None:
                    action_name = log_action.name

                actions = await data.ResourceAction.get_log(
                    environment=env.id, resource_version_id=resource_id, action=action_name, limit=log_limit, connection=con
                )

            return 200, {"resource": resv, "logs": actions}

    # This endpoint doesn't have a method associated yet.
    # Intended for use by other slices
    async def get_resources_in_latest_version(
        self,
        environment: data.Environment,
        resource_type: Optional[ResourceType] = None,
        attributes: dict[PrimitiveTypes, PrimitiveTypes] = {},
        connection: Optional[Connection] = None,
    ) -> list[Resource]:
        result = await data.Resource.get_resources_in_latest_version(
            environment.id, resource_type, attributes, connection=connection
        )
        return [r.to_dto() for r in result]

    async def mark_deployed(
        self,
        env: data.Environment,
        resources_id: abc.Set[ResourceIdStr],
        timestamp: datetime.datetime,
        version: int,
        filter: Callable[[ResourceIdStr], bool] = lambda x: True,
        connection: ConnectionMaybeInTransaction = ConnectionNotInTransaction(),
        only_update_from_states: Optional[Sequence[const.ResourceState]] = None,
    ) -> None:
        """
        Set the status of the provided resources as deployed
        :param env: Environment to consider.
        :param resources_id: Set of resources to mark as deployed.
        :param timestamp: Timestamp for the log message and the resource action entry.
        :param version: Version of the resources to consider.
        :param filter: Filter function that takes a resource id as an argument and returns True if it should be kept.
        """
        if not resources_id:
            return

        # performance-critical path: avoid parsing cost if we can
        resources_id_filtered = [res_id for res_id in resources_id if filter(res_id)]
        if not resources_id_filtered:
            return

        action_id = uuid.uuid4()

        async with data.Resource.get_connection(connection.connection) as inner_connection:
            async with inner_connection.transaction():
                # validate resources
                if only_update_from_states is not None:
                    resources = await data.Resource.get_resource_ids_with_status(
                        env.id,
                        resources_id_filtered,
                        version,
                        only_update_from_states,
                        # acquire lock on Resource before read and before lock on ResourceAction to prevent conflicts with
                        # cascading deletes
                        lock=data.RowLockMode.FOR_NO_KEY_UPDATE,
                        connection=inner_connection,
                    )
                    if not resources:
                        return None

                resources_version_ids: list[ResourceVersionIdStr] = [
                    ResourceVersionIdStr(f"{res_id},v={version}") for res_id in resources_id_filtered
                ]

                resource_action = data.ResourceAction(
                    environment=env.id,
                    version=version,
                    resource_version_ids=resources_version_ids,
                    action_id=action_id,
                    action=const.ResourceAction.deploy,
                    started=timestamp,
                    messages=[
                        {
                            "level": "INFO",
                            "msg": "Setting deployed due to known good status",
                            "args": [],
                            "timestamp": timestamp.isoformat(timespec="microseconds"),
                        }
                    ],
                    changes={},
                    status=const.ResourceState.deployed,
                    change=const.Change.nochange,
                    finished=timestamp,
                )
                await resource_action.insert(connection=inner_connection)
                self.log_resource_action(
                    env.id,
                    resources_version_ids,
                    const.LogLevel.INFO.to_int,
                    timestamp,
                    "Setting deployed due to known good status",
                )

                await data.Resource.set_deployed_multi(env.id, resources_id_filtered, version, connection=inner_connection)
                # Resource persistent state should not be affected

    async def get_increment(
        self,
        env: data.Environment,
        version: int,
        connection: Optional[Connection] = None,
        run_ahead_lock: Optional[asyncio.Event] = None,
    ) -> tuple[int, abc.Set[ResourceIdStr], abc.Set[ResourceIdStr], abc.Mapping[str, abc.Set[ResourceIdStr]]]:
        """
        Get the increment for a given environment and a given version of the model from the _increment_cache if possible.
        In case of cache miss, the increment calculation is performed behind a lock to make sure it is only done once per
        version, per environment.

        :param env: The environment to consider.
        :param version: The version of the model to consider.
        :param connection: connection to use towards the DB.
            When the connection is in a transaction, we will always invalidate the cache
        :param run_ahead_lock: lock used to keep agents hanging while building up the latest version
        """

        async def _get_cache_entry() -> (
            Optional[tuple[int, abc.Set[ResourceIdStr], abc.Set[ResourceIdStr], abc.Mapping[str, abc.Set[ResourceIdStr]]]]
        ):
            """
            Returns a tuple (increment, negative_increment, negative_increment_per_agent)
            if a cache entry exists for the given environment and version
            or None if no such cache entry exists.
            """
            cache_entry = self._increment_cache.get(env.id, None)
            if cache_entry is None:
                # No cache entry found
                return None
            version_cache_entry, incr, neg_incr, neg_incr_per_agent, cached_run_ahead_lock = cache_entry
            if version_cache_entry >= version:
                assert not run_ahead_lock  # We only expect a lock if WE are ahead
                # Cache is ahead or equal
                if cached_run_ahead_lock is not None:
                    await cached_run_ahead_lock.wait()
            elif version_cache_entry != version:
                # Cache entry exists for another version
                # Expire
                return None
            return version_cache_entry, incr, neg_incr, neg_incr_per_agent

        increment: Optional[
            tuple[int, abc.Set[ResourceIdStr], abc.Set[ResourceIdStr], abc.Mapping[str, abc.Set[ResourceIdStr]]]
        ] = await _get_cache_entry()
        if increment is None or (connection is not None and connection.is_in_transaction()):
            lock = self._increment_cache_locks[env.id]
            async with lock:
                increment = await _get_cache_entry()
                if increment is None:
                    positive, negative = await data.ConfigurationModel.get_increment(env.id, version, connection=connection)
                    negative_per_agent: dict[str, set[ResourceIdStr]] = defaultdict(set)
                    for rid in negative:
                        negative_per_agent[Id.parse_id(rid).agent_name].add(rid)
                    increment = (version, positive, negative, negative_per_agent)
                    self._increment_cache[env.id] = (version, positive, negative, negative_per_agent, run_ahead_lock)
        return increment

    @handle(methods.resource_action_update, env="tid")
    async def resource_action_update(
        self,
        env: data.Environment,
        resource_ids: list[ResourceVersionIdStr],
        action_id: uuid.UUID,
        action: const.ResourceAction,
        started: datetime.datetime,
        finished: datetime.datetime,
        status: Optional[Union[const.ResourceState, const.DeprecatedResourceState]],
        messages: list[dict[str, Any]],
        changes: dict[ResourceVersionIdStr, dict[str, object]],
        change: const.Change,
        send_events: bool,
        keep_increment_cache: bool = False,
        only_update_from_states: Optional[set[const.ResourceState]] = None,
        *,
        connection: ConnectionMaybeInTransaction = ConnectionNotInTransaction(),
    ) -> Apireturn:
        def convert_legacy_state(
            status: Optional[Union[const.ResourceState, const.DeprecatedResourceState]],
        ) -> Optional[const.ResourceState]:
            if status is None or isinstance(status, const.ResourceState):
                return status
            if status == const.DeprecatedResourceState.processing_events:
                return const.ResourceState.deploying
            else:
                raise BadRequest(f"Unsupported deprecated resources state {status.value}")

        # TODO: get rid of this?
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
                    f"Status {status} is not valid on action {action}",
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

        resources: list[data.Resource]
        async with data.Resource.get_connection(connection.connection) as inner_connection:
            async with inner_connection.transaction():
                # validate resources
                resources = await data.Resource.get_resources(
                    env.id,
                    resource_ids,
                    # acquire lock on Resource before read and before lock on ResourceAction to prevent conflicts with
                    # cascading deletes
                    lock=data.RowLockMode.FOR_NO_KEY_UPDATE,
                    connection=inner_connection,
                )
                if len(resources) == 0 or (len(resources) != len(resource_ids)):
                    raise NotFound(
                        message="The resources with the given ids do not exist in the given environment. "
                        f"Only {len(resources)} of {len(resource_ids)} resources found."
                    )

                if only_update_from_states is not None:
                    resources = [resource for resource in resources if resource.status in only_update_from_states]
                    if not resources:
                        return 200, {"message": "no resources with the given state found"}
                    resource_ids = [resource.resource_version_id for resource in resources]

                # validate transitions
                if is_resource_state_update:
                    # no escape from terminal
                    if any(resource.status != status and resource.status in TERMINAL_STATES for resource in resources):
                        LOGGER.error("Attempting to set undeployable resource to deployable state")
                        raise AssertionError("Attempting to set undeployable resource to deployable state")

                version = Id.parse_id(resource_ids[0]).version

                # get instance
                resource_action = await data.ResourceAction.get(action_id=action_id, connection=inner_connection)
                if resource_action is None:
                    # new
                    if started is None:
                        raise ServerError(message="A resource action can only be created with a start datetime.")

                    resource_action = data.ResourceAction(
                        environment=env.id,
                        version=version,
                        resource_version_ids=resource_ids,
                        action_id=action_id,
                        action=action,
                        started=started,
                    )
                    await resource_action.insert(connection=inner_connection)
                else:
                    # existing
                    if resource_action.finished is not None:
                        raise ServerError(
                            message="An resource action can only be updated when it has not been finished yet. This action "
                            f"finished at {resource_action.finished}"
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
                    connection=inner_connection,
                )

                if is_resource_state_update:
                    # transient resource update
                    if not is_resource_action_finished:
                        for res in resources:
                            await res.update_fields(status=status, connection=inner_connection)
                        if not keep_increment_cache:
                            self.clear_env_cache(env)
                        return 200

                    else:
                        # final resource update
                        if not keep_increment_cache:
                            self.clear_env_cache(env)

                        for res in resources:
                            await res.update_fields(
                                status=status,
                                connection=inner_connection,
                            )
                            # Not very typeable
                            extra_fields: dict[str, Any] = {}

                            if change is not None and change != Change.nochange:
                                extra_fields["last_produced_events"] = finished

                            if status == ResourceState.deployed:
                                extra_fields["last_success"] = resource_action.started
                            if status not in {
                                ResourceState.deploying,
                                ResourceState.undefined,
                                ResourceState.skipped_for_undefined,
                            }:
                                extra_fields["last_non_deploying_status"] = const.NonDeployingResourceState(status)
                                extra_fields["last_deployed_attribute_hash"] = res.attribute_hash
                                extra_fields["last_deploy"] = finished
                                extra_fields["last_deployed_version"] = version

                            await res.update_persistent_state(
                                **extra_fields,
                                connection=inner_connection,
                            )

                            if (
                                "purged" in res.attributes
                                and res.attributes["purged"]
                                and status == const.ResourceState.deployed
                            ):
                                await data.Parameter.delete_all(
                                    environment=env.id, resource_id=res.resource_id, connection=inner_connection
                                )

        if is_resource_state_update and is_resource_action_finished:

            def post_deploy_update() -> None:
                waiting_agents = {
                    (Id.parse_id(prov).get_agent_name(), res.resource_version_id) for res in resources for prov in res.provides
                }

                for agent, resource_id in waiting_agents:
                    aclient = self.agentmanager_service.get_agent_client(env.id, agent)
                    if aclient is not None:
                        if change is None:
                            my_change = const.Change.nochange
                        else:
                            my_change = change

                        self.add_background_task(
                            aclient.resource_event(env.id, agent, resource_id, send_events, status, my_change, changes)
                        )

            connection.call_after_tx(post_deploy_update)

        return 200

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
        exclude_changes: Optional[list[Change]] = None,
    ) -> ReturnValue[list[ResourceAction]]:
        if exclude_changes is None:
            exclude_changes = []

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
            exclude_changes=exclude_changes,
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
        ) -> dict[str, str]:
            query_params = {
                "resource_type": resource_type,
                "agent": agent,
                "attribute": attribute,
                "attribute_value": attribute_value,
                "log_severity": log_severity,
                "limit": str(limit) if limit else None,
            }
            return {param_key: param_value for param_key, param_value in query_params.items() if param_value is not None}

        if limit and resource_action_dtos:
            base_url = "/api/v2/resource_actions"
            common_query_params = _get_query_params(resource_type, agent, attribute, attribute_value, log_severity, limit)
            # Next is always earlier with regards to 'started' time
            next_params = common_query_params.copy()
            next_params["last_timestamp"] = util.datetime_iso_format(resource_action_dtos[-1].started)
            next_params["action_id"] = str(resource_action_dtos[-1].action_id)
            links["next"] = url_concat(base_url, next_params)
            previous_params = common_query_params.copy()
            previous_params["first_timestamp"] = util.datetime_iso_format(resource_action_dtos[0].started)
            previous_params["action_id"] = str(resource_action_dtos[0].action_id)
            links["prev"] = url_concat(base_url, previous_params)
        return_value = ReturnValue(response=resource_action_dtos, links=links if links else None)
        return return_value

    @handle(methods_v2.get_resource_events, env="tid", resource_id="rvid")
    async def get_resource_events(
        self, env: data.Environment, resource_id: Id, exclude_change: Optional[const.Change] = None
    ) -> dict[ResourceIdStr, list[ResourceAction]]:
        return {
            k: [ra.to_dto() for ra in v]
            for k, v in (await data.ResourceAction.get_resource_events(env, resource_id, exclude_change)).items()
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
        filter: Optional[dict[str, list[str]]] = None,
        sort: str = "resource_type.desc",
        deploy_summary: bool = False,
    ) -> ReturnValueWithMeta[Sequence[LatestReleasedResource]]:
        try:
            handler = ResourceView(env, limit, first_id, last_id, start, end, filter, sort, deploy_summary)

            out: ReturnValueWithMeta[Sequence[LatestReleasedResource]] = await handler.execute()
            if deploy_summary:
                out.metadata["deploy_summary"] = await data.Resource.get_resource_deploy_summary(env.id)
            return out

        except (InvalidFilter, InvalidSort, data.InvalidQueryParameter, data.InvalidFieldNameException) as e:
            raise BadRequest(e.message) from e

        # TODO: optimize for no orphans

    @handle(methods_v2.resource_details, env="tid")
    async def resource_details(self, env: data.Environment, rid: ResourceIdStr) -> ReleasedResourceDetails:
        details = await data.Resource.get_released_resource_details(env.id, rid)
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
        filter: Optional[dict[str, list[str]]] = None,
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
        filter: Optional[dict[str, list[str]]] = None,
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

    @handle(methods_v2.discovered_resource_create, env="tid")
    async def discovered_resource_create(
        self,
        env: data.Environment,
        discovered_resource_id: ResourceIdStr,
        values: JsonType,
        discovery_resource_id: ResourceIdStr,
    ) -> None:
        try:
            discovered_resource = LinkedDiscoveredResource(
                discovered_resource_id=discovered_resource_id, values=values, discovery_resource_id=discovery_resource_id
            )
        except ValidationError as e:
            # this part was copy/pasted from protocol.common.MethodProperties.validate_arguments.
            error_msg = f"Failed to validate argument\n{str(e)}"
            LOGGER.exception(error_msg)
            raise BadRequest(error_msg, {"validation_errors": e.errors()})

        dao = discovered_resource.to_dao(env.id)
        await dao.insert_with_overwrite()

    @handle(methods_v2.discovered_resource_create_batch, env="tid")
    async def discovered_resources_create_batch(
        self, env: data.Environment, discovered_resources: list[LinkedDiscoveredResource]
    ) -> None:
        dao_list = [res.to_dao(env.id) for res in discovered_resources]
        await data.DiscoveredResource.insert_many_with_overwrite(dao_list)

    @handle(methods_v2.discovered_resources_get, env="tid")
    async def discovered_resources_get(
        self, env: data.Environment, discovered_resource_id: ResourceIdStr
    ) -> DiscoveredResourceABC:
        if not self.feature_manager.enabled(resource_discovery):
            raise Forbidden(message="The resource discovery feature is not enabled.")

        result = await data.DiscoveredResource.get_one(environment=env.id, discovered_resource_id=discovered_resource_id)
        if not result:
            raise NotFound(f"discovered_resource with name {discovered_resource_id} not found in env {env.id}")
        dto = result.to_dto()
        return dto

    @protocol.handle(methods_v2.discovered_resources_get_batch, env="tid")
    async def discovered_resources_get_batch(
        self,
        env: data.Environment,
        limit: Optional[int] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        sort: str = "discovered_resource_id.asc",
        filter: Optional[dict[str, list[str]]] = None,
    ) -> ReturnValue[Sequence[DiscoveredResourceABC]]:
        if not self.feature_manager.enabled(resource_discovery):
            raise Forbidden(message="The resource discovery feature is not enabled.")

        try:
            handler = DiscoveredResourceView(environment=env, limit=limit, sort=sort, start=start, end=end, filter=filter)
            out = await handler.execute()

            return out
        except (InvalidFilter, InvalidSort, data.InvalidQueryParameter, data.InvalidFieldNameException) as e:
            raise BadRequest(e.message) from e

    @handle(methods_v2.discovered_resource_delete, env="tid")
    async def discovered_resource_delete(self, env: data.Environment, discovered_resource_id: ResourceIdStr) -> None:
        """
        Deletes a discovered resource based on id.

        :raise NotFound: This exception is raised if the discovered resource is not found in the provided environment
        """
        async with data.Resource.get_connection() as connection:
            result = await data.DiscoveredResource.get_one(
                environment=env.id, discovered_resource_id=discovered_resource_id, connection=connection
            )
            if not result:
                raise NotFound(f"Discovered Resource with id {discovered_resource_id} not found in env {env.id}")
            await result.delete(connection=connection)

    @handle(methods_v2.discovered_resource_delete_batch, env="tid")
    async def discovered_resource_delete_batch(
        self, env: data.Environment, discovered_resource_ids: typing.Sequence[str]
    ) -> None:
        """
        Deletes one or more discovered resources based on id.
        Does not raise an Exception if one or more of the discovered resources are not found.
        """
        async with data.Resource.get_connection() as connection:
            query = f"""
            DELETE FROM {data.DiscoveredResource.table_name()} as dr
            WHERE dr.environment=$1
                AND dr.discovered_resource_id=ANY($2)
            """
            await connection.execute(query, env.id, discovered_resource_ids)
