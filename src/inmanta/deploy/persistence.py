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
import uuid
from collections.abc import Set
from contextlib import AbstractAsyncContextManager
from typing import Any, Optional
from uuid import UUID

from asyncpg import Connection, UniqueViolationError

from inmanta import const, data
from inmanta.agent import executor
from inmanta.const import TERMINAL_STATES, TRANSIENT_STATES, VALID_STATES_ON_STATE_UPDATE, ResourceState
from inmanta.data import LogLine
from inmanta.deploy import state
from inmanta.protocol import Client
from inmanta.resources import Id
from inmanta.types import ResourceIdStr, ResourceVersionIdStr

LOGGER = logging.getLogger(__name__)


class StateUpdateManager(abc.ABC):
    """
    Interface used by tasks to flush away their state updates, none of these method must do anything for the scheduler to work

    This interface is split off from the taskmanager, to make mocking it easier
    """

    @abc.abstractmethod
    def get_connection(self, connection: Optional[Connection] = None) -> AbstractAsyncContextManager[Connection]:
        pass

    @abc.abstractmethod
    async def send_in_progress(self, action_id: UUID, resource_id: Id) -> None:
        """
        This method sets the state to in_progress.

        It is important that this method is atomic: if it fails, we assume the state to be not set and will not re-set it

        """
        # FIXME: get rid of version in the id
        pass

    @abc.abstractmethod
    async def send_deploy_done(
        self,
        attribute_hash: str,
        result: executor.DeployReport,
        state: Optional[state.ResourceState],
        *,
        started: datetime.datetime,
        finished: datetime.datetime,
    ) -> None:
        """
        Update the db to reflect the result of a deploy for a given resource.

        :param attribute_hash: The attribute hash of the intent that just finished deploying
        :param result: The deploy result of the finished deploy. Includes version information.
        :param state: The current state of this resource. None for stale deploys.
        """

    @abc.abstractmethod
    async def dryrun_update(self, env: UUID, dryrun_result: executor.DryrunReport) -> None:
        pass

    @abc.abstractmethod
    async def set_parameters(self, fact_result: executor.GetFactReport) -> None:
        pass

    @abc.abstractmethod
    async def update_resource_intent(
        self,
        environment: UUID,
        intent: dict[ResourceIdStr, tuple[state.ResourceState, state.ResourceIntent]],
        update_blocked_state: bool,
        connection: Optional[Connection] = None,
    ) -> None:
        pass

    @abc.abstractmethod
    async def mark_all_orphans(
        self, environment: UUID, *, current_version: int, connection: Optional[Connection] = None
    ) -> None:
        """
        Mark all resources that do not appear in the current version or a later one as orphans.

        More expensive than mark_as_orphan. Should only be used when it is not clear which resources should be orphaned.
        """
        pass

    @abc.abstractmethod
    async def mark_as_orphan(
        self, environment: UUID, resource_ids: Set[ResourceIdStr], connection: Optional[Connection] = None
    ) -> None:
        pass

    @abc.abstractmethod
    async def set_last_processed_model_version(
        self, environment: uuid.UUID, version: int, connection: Optional[Connection] = None
    ) -> None:
        """
        Set the last model version that was processed by the scheduler.
        """
        pass


class ToDbUpdateManager(StateUpdateManager):

    def __init__(self, client: Client, environment: UUID) -> None:
        self.environment = environment
        # TODO: The client is only here temporarily while we fix the dryrun_update
        self.client = client

    def get_connection(self, connection: Optional[Connection] = None) -> AbstractAsyncContextManager[Connection]:
        return data.Scheduler.get_connection()

    async def send_in_progress(self, action_id: UUID, resource_id: Id) -> None:
        """
        Update the db to reflect that deployment has started for a given resource.
        """

        async with data.Resource.get_connection() as connection:
            async with connection.transaction():
                # This check is made in an overabundance of caution and can probably be dropped
                resource = await data.Resource.get_one(
                    connection=connection,
                    environment=self.environment,
                    resource_id=resource_id.resource_str(),
                    model=resource_id.version,
                    lock=data.RowLockMode.FOR_UPDATE,
                )
                assert resource is not None, f"Resource {resource_id} does not exists in the database, this should not happen"

                log_line = data.LogLine.log(
                    logging.INFO,
                    "Resource deploy started on agent %(agent)s, setting status to deploying",
                    agent=resource_id.agent_name,
                )
                # Not in Handler context, need to flush explicitly
                log_line.write_to_logger_for_resource(resource_id.agent_name, resource_id.resource_version_str(), False)

                resource_action = data.ResourceAction(
                    environment=self.environment,
                    version=resource_id.version,
                    resource_version_ids=[resource_id.resource_version_str()],
                    action_id=action_id,
                    action=const.ResourceAction.deploy,
                    started=datetime.datetime.now().astimezone(),
                    messages=[log_line],
                    status=const.ResourceState.deploying,
                )
                try:
                    await resource_action.insert(connection=connection)
                except UniqueViolationError:
                    raise ValueError(f"A resource action with id {action_id} already exists.")

                # FIXME: we may want to have this in the RPS table instead of Resource table, at some point
                await resource.update_fields(connection=connection, status=const.ResourceState.deploying)

    async def send_deploy_done(
        self,
        attribute_hash: str,
        result: executor.DeployReport,
        state: Optional[state.ResourceState],
        *,
        started: datetime.datetime,
        finished: datetime.datetime,
    ) -> None:
        stale_deploy: bool = state is None

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

        # TODO: clean up this particular dict
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
                # TODO: do we need the resource at all?
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
                    # use start time for last_success because it is used for comparison with dependencies' last_produced_events
                    extra_datetime_fields["last_success"] = started

                # We are producing an event
                # use finished time for last_produced_events because it is used for comparison with dependencies' start
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
                    last_deploy_result=state.last_deploy_result if state is not None else None,
                    **extra_datetime_fields,
                    connection=connection,
                )

                if (
                    not stale_deploy
                    and "purged" in resource.attributes
                    and resource.attributes["purged"]
                    and status == const.ResourceState.deployed
                ):
                    await data.Parameter.delete_all(
                        environment=self.environment, resource_id=resource.resource_id, connection=connection
                    )

    async def dryrun_update(self, env: UUID, dryrun_result: executor.DryrunReport) -> None:
        await self.client.dryrun_update(
            tid=env,
            id=dryrun_result.dryrun_id,
            resource=dryrun_result.rvid,
            changes=dryrun_result.changes,
        )

        await self._write_resource_action(
            env,
            dryrun_result.rvid,
            const.ResourceAction.dryrun,
            uuid.uuid4(),
            dryrun_result.resource_state or const.ResourceState.dry,
            dryrun_result.started,
            dryrun_result.finished,
            dryrun_result.messages,
        )

    async def _write_resource_action(
        self,
        env: UUID,
        resource: ResourceVersionIdStr,
        action: const.ResourceAction,
        action_id: UUID,
        status: const.ResourceState | None,
        started: datetime.datetime,
        finished: datetime.datetime,
        messages: list[LogLine],
    ) -> None:
        id = Id.parse_id(resource)

        resource_action = data.ResourceAction(
            environment=env,
            version=id.version,
            resource_version_ids=[resource],
            action_id=action_id,
            action=action,
            started=started,
            finished=finished,
            status=status,
            messages=[msg.to_dict() for msg in messages],
        )
        await resource_action.insert()

    async def set_parameters(self, fact_result: executor.GetFactReport) -> None:
        # TODO: fact_result -> fact_report
        if fact_result.success:
            await self.client.set_parameters(tid=self.environment, parameters=fact_result.parameters)
        await self._write_resource_action(
            env=self.environment,
            resource=fact_result.resource_id,
            action=const.ResourceAction.getfact,
            action_id=fact_result.action_id or uuid.uuid4(),
            started=fact_result.started,
            finished=fact_result.finished,
            messages=fact_result.messages,
            status=fact_result.resource_state,
        )

    async def update_resource_intent(
        self,
        environment: UUID,
        intent: dict[ResourceIdStr, tuple[state.ResourceState, state.ResourceIntent]],
        update_blocked_state: bool,
        connection: Optional[Connection] = None,
    ) -> None:
        await data.ResourcePersistentState.update_resource_intent(
            environment, intent, update_blocked_state, connection=connection
        )

    async def mark_all_orphans(
        self, environment: UUID, *, current_version: int, connection: Optional[Connection] = None
    ) -> None:
        await data.Scheduler._execute_query(
            f"""
            UPDATE {data.ResourcePersistentState.table_name()} AS rps
            SET is_orphan=true
            WHERE
                rps.environment=$1
                AND NOT rps.is_orphan
                AND NOT EXISTS(
                    SELECT 1
                    FROM {data.Resource.table_name()} AS r
                    INNER JOIN {data.ConfigurationModel.table_name()} AS cm
                        ON cm.environment = r.environment
                        AND cm.version = r.model
                    WHERE
                        r.environment=rps.environment
                        AND r.resource_id=rps.resource_id
                        AND cm.version >= $2
                        AND cm.released
                )
            """,
            environment,
            current_version,
            connection=connection,
        )

    async def mark_as_orphan(
        self,
        environment: UUID,
        resource_ids: Set[ResourceIdStr],
        connection: Optional[Connection] = None,
    ) -> None:
        await data.ResourcePersistentState.mark_as_orphan(environment, resource_ids, connection=connection)

    async def set_last_processed_model_version(
        self, environment: uuid.UUID, version: int, connection: Optional[Connection] = None
    ) -> None:
        await data.Scheduler.set_last_processed_model_version(environment, version, connection=connection)
