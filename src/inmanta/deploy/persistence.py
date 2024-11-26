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
from inmanta.agent.executor import DeployResult, DryrunResult, FactResult
from inmanta.const import TERMINAL_STATES, TRANSIENT_STATES, VALID_STATES_ON_STATE_UPDATE, Change, ResourceState
from inmanta.data.model import AttributeStateChange, ResourceVersionIdStr
from inmanta.deploy import state
from inmanta.protocol import Client
from inmanta.resources import Id
from inmanta.server.services import resourceservice

LOGGER = logging.getLogger(__name__)


class StateUpdateManager(abc.ABC):
    """
    Interface used by tasks to flush away their state updates, none of these method must do anything for the scheduler to work

    This interface is split off from the taskmanager, to make mocking it easier
    """

    @abc.abstractmethod
    async def send_in_progress(self, action_id: UUID, resource_id: ResourceVersionIdStr) -> None:
        # FIXME: get rid of version in the id
        pass

    @abc.abstractmethod
    async def send_deploy_done(self, result: DeployResult) -> None:
        pass

    @abc.abstractmethod
    async def dryrun_update(self, env: UUID, dryrun_result: DryrunResult) -> None:
        pass

    @abc.abstractmethod
    async def set_parameters(self, fact_result: FactResult) -> None:
        pass


class ToDbUpdateManager(StateUpdateManager):

    def __init__(self, client: Client, environment: UUID) -> None:
        self.environment = environment
        # TODO: The client is only here temporarily while we fix the dryrun_update
        self.client = client
        # FIXME: We may want to move the writing of the log to the scheduler side as well,
        #  when all uses of this logger are moved
        self._resource_action_logger = logging.getLogger(const.NAME_RESOURCE_ACTION_LOGGER)

    def get_resource_action_logger(self, environment: UUID) -> logging.Logger:
        """Get the resource action logger for the given environment.
        :param environment: The environment to get a logger for
        :return: The logger for the given environment.
        """
        return self._resource_action_logger.getChild(str(environment))

    def log_resource_action(self, env: UUID, resource_id: str, log_level: int, ts: datetime.datetime, message: str) -> None:
        """Write the given log to the correct resource action logger"""
        logger = self.get_resource_action_logger(env)
        message = resource_id + ": " + message
        log_record = resourceservice.ResourceActionLogLine(logger.name, log_level, message, ts)
        logger.handle(log_record)

    async def send_in_progress(self, action_id: UUID, resource_id: ResourceVersionIdStr) -> None:
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
                    raise ValueError(f"A resource action with id {action_id} already exists.")

                # FIXME: we may want to have this in the RPS table instead of Resource table, at some point
                await resource.update_fields(connection=connection, status=const.ResourceState.deploying)

    async def send_deploy_done(self, result: DeployResult) -> None:
        def error_and_log(message: str, **context: Any) -> None:
            """
            :param message: message to return both to logger and to remote caller
            :param context: additional context to attach to log
            """
            ctx = ",".join([f"{k}: {v}" for k, v in context.items()])
            LOGGER.error("%s %s", message, ctx)
            raise ValueError(message)

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
                    raise ValueError("The resource with the given id does not exist in the given environment.")

                # no escape from terminal
                if resource.status != status and resource.status in TERMINAL_STATES:
                    LOGGER.error("Attempting to set undeployable resource to deployable state")
                    raise AssertionError("Attempting to set undeployable resource to deployable state")

                resource_action = await data.ResourceAction.get(action_id=action_id, connection=connection)
                if resource_action is None:
                    raise ValueError(
                        f"No resource action exists for action_id {action_id}. Ensure send_in_progress is called first."
                    )
                if resource_action.finished is not None:
                    raise ValueError(
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

                extra_datetime_fields: dict[str, datetime.datetime] = {}
                if status == ResourceState.deployed:
                    extra_datetime_fields["last_success"] = resource_action.started

                # keep track IF we need to propagate if we are stale
                # but only do it at the end of the transaction
                if change != Change.nochange:
                    # We are producing an event
                    extra_datetime_fields["last_produced_events"] = finished

                await resource.update_fields(
                    status=status,
                    connection=connection,
                )
                await resource.update_persistent_state(
                    last_deploy=finished,
                    last_deployed_version=resource_id_parsed.version,
                    last_deployed_attribute_hash=resource.attribute_hash,
                    last_non_deploying_status=const.NonDeployingResourceState(status),
                    resource_status=state.ResourceStatus.UP_TO_DATE if status is const.ResourceState.deployed else None,
                    **extra_datetime_fields,
                    connection=connection,
                )

                if "purged" in resource.attributes and resource.attributes["purged"] and status == const.ResourceState.deployed:
                    await data.Parameter.delete_all(
                        environment=self.environment, resource_id=resource.resource_id, connection=connection
                    )

    async def dryrun_update(self, env: UUID, dryrun_result: DryrunResult) -> None:
        # TODO: Inline these methods so that we don't call the server
        # To be done after we update the dryrun database table
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

    async def set_parameters(self, fact_result: FactResult) -> None:
        await self.client.set_parameters(tid=self.environment, parameters=fact_result.parameters)
        await self.client.resource_action_update(
            tid=self.environment,
            resource_ids=[fact_result.resource_id],
            action_id=fact_result.action_id,
            action=const.ResourceAction.getfact,
            started=fact_result.started,
            finished=fact_result.finished,
            messages=fact_result.messages,
        )
