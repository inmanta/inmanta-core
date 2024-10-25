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
import datetime
import logging
from typing import Any
from uuid import UUID

from asyncpg import UniqueViolationError

from inmanta import const, data
from inmanta.agent.executor import DeployResult, DryrunResult
from inmanta.const import TERMINAL_STATES, TRANSIENT_STATES, VALID_STATES_ON_STATE_UPDATE, Change, ResourceState
from inmanta.data.model import AttributeStateChange, ResourceIdStr, ResourceVersionIdStr
from inmanta.protocol import Client
from inmanta.protocol.exceptions import BadRequest, Conflict, NotFound
from inmanta.resources import Id
from inmanta.server.services import resourceservice
from inmanta.util import parse_timestamp

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
    async def send_deploy_done(self, result: DeployResult) -> None:
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

    async def send_deploy_done(self, result: DeployResult) -> None:
        changes: dict[ResourceVersionIdStr, dict[str, AttributeStateChange]] = {result.rvid: result.changes}
        response = await self.client.resource_deploy_done(
            tid=self.environment,
            rvid=result.rvid,
            action_id=result.action_id,
            status=result.status,
            messages=result.messages,
            changes=changes,
            change=result.change,
        )
        if response.code != 200:
            LOGGER.error("Resource status update failed %s for %s ", response.result, result.rvid)

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


class ToDbUpdateManager(StateUpdateManager):

    def __init__(self, environment: UUID) -> None:
        self.environment = environment
        # FIXME: We may want to move the writing of the log to the scheduler side as well,
        #  when all uses of this logger are moved
        self._resource_action_logger = logging.getLogger(const.NAME_RESOURCE_ACTION_LOGGER)

    async def send_in_progress(
        self, action_id: UUID, resource_id: ResourceVersionIdStr
    ) -> dict[ResourceIdStr, const.ResourceState]:
        resource_id_str = resource_id
        resource_id_parsed = Id.parse_id(resource_id_str)

        async with data.Resource.get_connection() as connection:
            async with connection.transaction():
                # This check is made in an overabundance of caution and can probably be dropped
                resource = await data.Resource.get_one(
                    connection=connection,
                    environment=self.environment,
                    resource_id=resource_id_parsed.resource_str(),
                    model=resource_id_parsed.version,
                    lock=data.RowLockMode.FOR_UPDATE,
                )
                assert (
                    resource is not None
                ), f"Resource {resource_id_parsed} does not exists in the database, this should not happen"

                resource_action = data.ResourceAction(
                    environment=self.environment,
                    version=resource_id_parsed.version,
                    resource_version_ids=[resource_id_str],
                    action_id=action_id,
                    action=const.ResourceAction.deploy,
                    started=datetime.datetime.now().astimezone(),
                    messages=[
                        data.LogLine.log(
                            logging.INFO,
                            "Resource deploy started on agent %(agent)s, setting status to deploying",
                            agent=resource_id_parsed.agent_name,
                        )
                    ],
                    status=const.ResourceState.deploying,
                )
                try:
                    await resource_action.insert(connection=connection)
                except UniqueViolationError:
                    raise Conflict(message=f"A resource action with id {action_id} already exists.")

                # FIXME: we may want to have this in the RPS table instead of Resource table, at some point
                await resource.update_fields(connection=connection, status=const.ResourceState.deploying)

            # FIXME: shortcut to use scheduler state
            result = await data.Resource.get_last_non_deploying_state_for_dependencies(
                environment=self.environment, resource_version_id=resource_id_parsed, connection=connection
            )

            return {Id.parse_id(key).resource_str(): const.ResourceState[value] for key, value in result.items()}

    async def send_deploy_done(self, result: DeployResult) -> None:
        def error_and_log(message: str, **context: Any) -> None:
            """
            :param message: message to return both to logger and to remote caller
            :param context: additional context to attach to log
            """
            ctx = ",".join([f"{k}: {v}" for k, v in context.items()])
            LOGGER.error("%s %s", message, ctx)
            raise BadRequest(message)

        resource_id_str = result.rvid
        resource_id_parsed = Id.parse_id(resource_id_str)

        action_id = result.action_id

        status = result.status
        messages = result.messages
        change = result.change

        finished = datetime.datetime.now().astimezone()

        changes_with_rvid: dict[ResourceVersionIdStr, dict[str, object]] = {
            resource_id_str: {attr_name: attr_change.model_dump()} for attr_name, attr_change in result.changes.items()
        }

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
                    environment=self.environment,
                    resource_id=resource_id_parsed.resource_str(),
                    model=resource_id_parsed.version,
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
                        self.environment,
                        resource_id_str,
                        log.log_level.to_int,
                        log.timestamp,
                        log.msg,
                    )

                await resource_action.set_and_save(
                    messages=[
                        {
                            **log.to_dict(),
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

                extra_fields = {}
                if status == ResourceState.deployed:
                    extra_fields["last_success"] = resource_action.started

                # keep track IF we need to propagate if we are stale
                # but only do it at the end of the transaction
                if change != Change.nochange:
                    # We are producing an event
                    extra_fields["last_produced_events"] = finished

                await resource.update_fields(
                    status=status,
                    connection=connection,
                )
                await resource.update_persistent_state(
                    last_deploy=finished,
                    last_deployed_version=resource_id_parsed.version,
                    last_deployed_attribute_hash=resource.attribute_hash,
                    last_non_deploying_status=const.NonDeployingResourceState(status),
                    **extra_fields,
                    connection=connection,
                )

                if "purged" in resource.attributes and resource.attributes["purged"] and status == const.ResourceState.deployed:
                    await data.Parameter.delete_all(
                        environment=self.environment, resource_id=resource.resource_id, connection=connection
                    )

    def log_resource_action(self, env: UUID, resource_id: str, log_level: int, ts: datetime.datetime, message: str) -> None:
        """Write the given log to the correct resource action logger"""
        logger = self.get_resource_action_logger(env)
        message = resource_id + ": " + message
        log_record = resourceservice.ResourceActionLogLine(logger.name, log_level, message, ts)
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
