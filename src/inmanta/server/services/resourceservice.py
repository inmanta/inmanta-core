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
from typing import Any, Optional, cast

from asyncpg.connection import Connection
from pydantic import ValidationError
from tornado.httputil import url_concat

from inmanta import const, data, util
from inmanta.data import APILIMIT, InvalidSort, model
from inmanta.data.dataview import (
    DiscoveredResourceView,
    ResourceHistoryView,
    ResourceLogsView,
    ResourcesInVersionView,
    ResourceView,
)
from inmanta.data.model import (
    LatestReleasedResource,
    ReleasedResourceDetails,
    Resource,
    ResourceAction,
    ResourceComplianceDiff,
    ResourceHistory,
    ResourceLog,
    VersionedResource,
    VersionedResourceDetails,
)
from inmanta.protocol import handle, methods, methods_v2
from inmanta.protocol.common import ReturnValue
from inmanta.protocol.exceptions import BadRequest, Forbidden, NotFound
from inmanta.protocol.return_value_meta import ReturnValueWithMeta
from inmanta.resources import Id
from inmanta.server import SLICE_AGENT_MANAGER, SLICE_DATABASE, SLICE_ENVIRONMENT, SLICE_RESOURCE, SLICE_TRANSPORT, agentmanager
from inmanta.server import config as opt
from inmanta.server import extensions, protocol
from inmanta.server.services.environmentlistener import EnvironmentAction, EnvironmentListener
from inmanta.server.validate_filter import InvalidFilter
from inmanta.types import Apireturn, JsonType, PrimitiveTypes, ResourceIdStr, ResourceType, ResourceVersionIdStr

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
        self.schedule(
            data.ResourcePersistentState.purge_old_diffs,
            opt.server_purge_resource_action_logs_interval.get(),
            cancel_on_stop=False,
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
        result = await data.Resource.get_resources_in_latest_version_as_dto(
            environment.id, resource_type, attributes, connection=connection
        )
        return result

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
        exclude_changes: Optional[list[const.Change]] = None,
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
            discovered_resource = model.DiscoveredResourceInput(
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
        self, env: data.Environment, discovered_resources: list[model.DiscoveredResourceInput]
    ) -> None:
        dao_list = [res.to_dao(env.id) for res in discovered_resources]
        await data.DiscoveredResource.insert_many_with_overwrite(dao_list)

    @handle(methods_v2.discovered_resources_get, env="tid")
    async def discovered_resources_get(
        self, env: data.Environment, discovered_resource_id: ResourceIdStr
    ) -> model.DiscoveredResourceOutput:
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
    ) -> ReturnValue[Sequence[model.DiscoveredResourceOutput]]:
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

    @handle(methods_v2.get_compliance_report, env="tid")
    async def get_compliance_report(
        self, env: data.Environment, resource_ids: typing.Sequence[ResourceIdStr]
    ) -> dict[ResourceIdStr, ResourceComplianceDiff]:
        """
        Get the compliance status report for a list of resources.
        """
        return await data.ResourcePersistentState.get_compliance_report(env.id, resource_ids)
