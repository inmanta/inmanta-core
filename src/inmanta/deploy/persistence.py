"""
    Copyright 2024 Inmanta

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

import abc
import asyncio
import datetime
import logging
from typing import Any, Optional, Sequence, Union
from uuid import UUID

from inmanta import const, data
from inmanta.agent.executor import DryrunResult
from inmanta.const import STATE_UPDATE, TERMINAL_STATES, TRANSIENT_STATES, VALID_STATES_ON_STATE_UPDATE, Change
from inmanta.data.model import AttributeStateChange, ResourceIdStr, ResourceVersionIdStr
from inmanta.db.util import ConnectionMaybeInTransaction, ConnectionNotInTransaction
from inmanta.protocol import Client
from inmanta.protocol.exceptions import BadRequest, NotFound, ServerError
from inmanta.resources import Id
from inmanta.server.protocol import ReturnClient, Session
from inmanta.server.services.resourceservice import ResourceActionLogLine
from inmanta.types import Apireturn
from inmanta.util import TaskHandler, parse_timestamp

LOGGER = logging.getLogger(__name__)


class StateUpdateManager(abc.ABC):
    """
    Interface used by tasks to flush away their state updates, none of these method must do anything for the scheduler to work

    This interface is split off from the taskmanager, to make mocking it easier
    """

    @abc.abstractmethod
    async def send_in_progress(
        self, action_id: UUID, resource_id: ResourceVersionIdStr
    ) -> dict[ResourceIdStr, const.ResourceState]:
        # FIXME: get rid of version in the id
        pass

    @abc.abstractmethod
    async def dryrun_update(self, env: UUID, dryrun_result: DryrunResult) -> None:
        pass


class ToServerUpdateManager(StateUpdateManager):
    """
    This is a temporary structure to help refactoring
    """

    def __init__(self, client: Client, environment: UUID) -> None:
        self.client = client
        self.environment = environment

    async def send_in_progress(
        self, action_id: UUID, resource_id: ResourceVersionIdStr
    ) -> dict[ResourceIdStr, const.ResourceState]:
        result = await self.client.resource_deploy_start(
            tid=self.environment,
            rvid=resource_id,
            action_id=action_id,
        )
        if result.code != 200 or result.result is None:
            raise Exception("Failed to report the start of the deployment to the server")
        return {Id.parse_id(key).resource_str(): const.ResourceState[value] for key, value in result.result["data"].items()}

    async def dryrun_update(self, env: UUID, dryrun_result: DryrunResult) -> None:
        await self.client.dryrun_update(
            tid=env,
            id=dryrun_result.dryrun_id,
            resource=dryrun_result.rvid,
            changes=dryrun_result.changes,
        )
        await self.client.resource_action_update(
            tid=env,
            resource_ids=[dryrun_result.rvid],
            action_id=dryrun_result.dryrun_id,
            action=const.ResourceAction.dryrun,
            started=dryrun_result.started,
            finished=dryrun_result.finished,
            messages=dryrun_result.messages,
            status=const.ResourceState.dry,
        )

    async def resource_action_update(
        self,
        env: data.Environment,
        resource_ids: list[ResourceVersionIdStr],
        action_id: UUID,
        action: const.ResourceAction,
        started: datetime.datetime,
        finished: datetime.datetime,
        status: Optional[Union[const.ResourceState, const.DeprecatedResourceState]],
        messages: list[dict[str, Any]],
        changes: dict[str, Any],
        change: const.Change,
        *,
        connection: ConnectionMaybeInTransaction = ConnectionNotInTransaction(),
    ) -> Apireturn:
        return await self.client.resource_action_update(
            tid=env,
            resource_ids=resource_ids,
            action_id=action_id,
            action=action,
            started=started,
            finished=finished,
            messages=messages,
            status=status,
            changes=changes,
            change=change,
            connection=connection,
        )


class ToDbUpdateManager(StateUpdateManager, TaskHandler[None]):

    def __init__(self, environment: UUID) -> None:
        super().__init__()
        self.environment = environment
        # FIXME: We may want to move the writing of the log to the scheduler side as well,
        #  when all uses of this logger are moved
        self._resource_action_logger = logging.getLogger(const.NAME_RESOURCE_ACTION_LOGGER)

    def error_and_log(self, message: str, **context: Any) -> None:
        """
        :param message: message to return both to logger and to remote caller
        :param context: additional context to attach to log
        """
        ctx = ",".join([f"{k}: {v}" for k, v in context.items()])
        LOGGER.error("%s %s", message, ctx)
        raise BadRequest(message)

    def log_resource_action(self, env: UUID, resource_id: str, log_level: int, ts: datetime.datetime, message: str) -> None:
        """Write the given log to the correct resource action logger"""
        logger = self.get_resource_action_logger(env)
        message = resource_id + ": " + message
        log_record = ResourceActionLogLine(logger.name, log_level, message, ts)
        logger.handle(log_record)

    def get_resource_action_logger(self, environment: UUID) -> logging.Logger:
        """Get the resource action logger for the given environment.
        :param environment: The environment to get a logger for
        :return: The logger for the given environment.
        """
        return self._resource_action_logger.getChild(str(environment))

    async def dryrun_update(self, env: UUID, dryrun_result: DryrunResult) -> None:
        # async with self.dryrun_lock: Should this class have this lock or one of the child classes?
        payload = {
            "changes": dryrun_result.changes,
            "id_fields": Id.parse_id(dryrun_result.rvid).to_dict(),
            "id": dryrun_result.rvid,
        }
        await data.DryRun.update_resource(dryrun_result.dryrun_id, dryrun_result.rvid, payload)

        async with data.Resource.get_connection() as inner_connection:
            async with inner_connection.transaction():
                # validate resources
                resource_id_parsed = Id.parse_id(dryrun_result.rvid)
                version = resource_id_parsed.version
                resource = await data.Resource.get_one(
                    environment=env,
                    resource_id=resource_id_parsed.resource_str(),
                    model=version,
                    # acquire lock on Resource before read and before lock on ResourceAction to prevent conflicts with
                    # cascading deletes
                    lock=data.RowLockMode.FOR_NO_KEY_UPDATE,
                    connection=inner_connection,
                )
                assert (
                    resource is not None
                ), f"Resource {resource_id_parsed} does not exists in the database, this should not happen"

                # get instance
                resource_action = await data.ResourceAction.get(action_id=dryrun_result.dryrun_id, connection=inner_connection)
                if resource_action is None:
                    resource_action = data.ResourceAction(
                        environment=env,
                        version=version,
                        resource_version_ids=dryrun_result.rvid,
                        action_id=dryrun_result.dryrun_id,
                        action=const.ResourceAction.dryrun,
                        started=dryrun_result.started,
                        changes=dryrun_result.changes,
                        status=const.ResourceState.dry,
                        finished=dryrun_result.finished,
                        connection=inner_connection,
                        messages=[
                            {
                                **msg,
                                "timestamp": parse_timestamp(str(msg._data.get("timestamp"))).isoformat(
                                    timespec="microseconds"
                                ),
                            }
                            for msg in dryrun_result.messages
                        ],
                    )
                    await resource_action.insert(connection=inner_connection)
                for msg in dryrun_result.messages:
                    # All other data is stored in the database. The msg was already formatted at the client side.
                    self.log_resource_action(
                        env,
                        dryrun_result.rvid,
                        const.LogLevel(msg.log_level).to_int,
                        parse_timestamp(str(msg._data.get("timestamp"))),
                        msg.msg,
                    )
