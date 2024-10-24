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
from inmanta.const import STATE_UPDATE, TERMINAL_STATES, TRANSIENT_STATES, VALID_STATES_ON_STATE_UPDATE, Change
from inmanta.data.model import ResourceIdStr, ResourceVersionIdStr
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
        send_events: bool,
        keep_increment_cache: bool = False,
        is_increment_notification: bool = False,
        only_update_from_states: Optional[set[const.ResourceState]] = None,
        *,
        connection: ConnectionMaybeInTransaction = ConnectionNotInTransaction(),
    ) -> Apireturn:
        pass

    @abc.abstractmethod
    async def dryrun_update(self, environment, dryrun_id, resource, changes) -> None:
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

    async def dryrun_update(self, environment, dryrun_id, resource, changes) -> None:
        await self.client.dryrun_update(
            tid=environment,
            id=dryrun_id,
            resource=resource,
            changes=changes,
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
        send_events: bool,
        keep_increment_cache: bool = False,
        is_increment_notification: bool = False,
        only_update_from_states: Optional[set[const.ResourceState]] = None,
        *,
        connection: ConnectionMaybeInTransaction = ConnectionNotInTransaction(),
    ) -> Apireturn:
        await self.client.resource_action_update(
            tid=env,
            resource_ids=resource_ids,
            action_id=action_id,
            action=action,
            started=started,
            finished=finished,
            messages=messages,
            status=status,
        )


class ToDbUpdateManager(StateUpdateManager, TaskHandler[None]):

    def __init__(self, environment: UUID) -> None:
        super().__init__()
        self.environment = environment
        # FIXME: We may want to move the writing of the log to the scheduler side as well,
        #  when all uses of this logger are moved
        self._resource_action_logger = logging.getLogger(const.NAME_RESOURCE_ACTION_LOGGER)
        self._increment_cache: dict[
            UUID,
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
        # all sessions
        self.sessions: dict[UUID, Session] = {}
        # live sessions: Sessions to agents which are primary and unpaused
        self.tid_endpoint_to_session: dict[tuple[UUID, str], Session] = {}

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

    def error_and_log(self, message: str, **context: Any) -> None:
        """
        :param message: message to return both to logger and to remote caller
        :param context: additional context to attach to log
        """
        ctx = ",".join([f"{k}: {v}" for k, v in context.items()])
        LOGGER.error("%s %s", message, ctx)
        raise BadRequest(message)

    def log_resource_action(
        self, env: UUID, resource_ids: Sequence[str], log_level: int, ts: datetime.datetime, message: str
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

    def get_resource_action_logger(self, environment: UUID) -> logging.Logger:
        """Get the resource action logger for the given environment.
        :param environment: The environment to get a logger for
        :return: The logger for the given environment.
        """
        return self._resource_action_logger.getChild(str(environment))

    def clear_env_cache(self, env: UUID) -> None:
        LOGGER.log(const.LOG_LEVEL_TRACE, "Clearing cache for %s", env)
        self._increment_cache[env] = None

    async def dryrun_update(self, environment, dryrun_id, resource, changes):
        # async with self.dryrun_lock: Should this class have this lock or one of the child classes?
        payload = {"changes": changes, "id_fields": Id.parse_id(resource).to_dict(), "id": resource}
        await data.DryRun.update_resource(dryrun_id, resource, payload)

    def get_session_for(self, tid: UUID, endpoint: str) -> Optional[Session]:
        """
        Return a session that matches the given environment and endpoint.
        This method also returns session to paused or non-live agents.
        """
        key = (tid, endpoint)
        session = self.tid_endpoint_to_session.get(key)
        if session:
            # Agent has live session
            return session
        else:
            # Maybe session exists for a paused agent
            for session in self.sessions.values():
                if endpoint in session.endpoint_names and session.tid == tid:
                    return session
            # Agent is down
            return None

    def get_agent_client(self, tid: UUID, endpoint: str, live_agent_only: bool = True) -> Optional[ReturnClient]:
        if isinstance(tid, str):
            tid = UUID(tid)
        key = (tid, endpoint)
        session = self.tid_endpoint_to_session.get(key)
        if session:
            return session.get_client()
        elif not live_agent_only:
            session = self.get_session_for(tid, endpoint)
            if session:
                return session.get_client()
            else:
                return None
        else:
            return None

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
        send_events: bool,
        keep_increment_cache: bool = False,
        is_increment_notification: bool = False,
        only_update_from_states: Optional[set[const.ResourceState]] = None,
        *,
        connection: ConnectionMaybeInTransaction = ConnectionNotInTransaction(),
    ) -> Apireturn:
        """
        :param is_increment_notification: is this the increment calucation setting the deployed status,
            instead of an actual deploy? Used to keep track of the last_success field on the resources,
            which should not be updated for increments.
        """

        def convert_legacy_state(
            status: Optional[Union[const.ResourceState, const.DeprecatedResourceState]]
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
                self.error_and_log(
                    "Cannot perform state update without a status.",
                    resource_ids=resource_ids,
                    action=action,
                    action_id=action_id,
                )
            # and needs to be valid
            if status not in VALID_STATES_ON_STATE_UPDATE:
                self.error_and_log(
                    f"Status {status} is not valid on action {action}",
                    resource_ids=resource_ids,
                    action=action,
                    action_id=action_id,
                )
            if status in TRANSIENT_STATES:
                if not is_resource_action_finished:
                    pass
                else:
                    self.error_and_log(
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
                    self.error_and_log(
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

                # get instance
                resource_action = await data.ResourceAction.get(action_id=action_id, connection=inner_connection)
                if resource_action is None:
                    # new
                    if started is None:
                        raise ServerError(message="A resource action can only be created with a start datetime.")

                    version = Id.parse_id(resource_ids[0]).version
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
                            self.clear_env_cache(env.id)
                        return 200

                    else:
                        # final resource update
                        if not keep_increment_cache:
                            self.clear_env_cache(env.id)

                        model_version = None
                        for res in resources:
                            await res.update_fields(
                                status=status,
                                connection=inner_connection,
                            )
                            # Not very typeable
                            extra_fields: dict[str, Any] = {}

                            if change is not None and change != Change.nochange:
                                extra_fields["last_produced_events"] = finished

                            if not is_increment_notification:
                                if status == const.ResourceState.deployed:
                                    extra_fields["last_success"] = resource_action.started
                                if status not in {
                                    const.ResourceState.deploying,
                                    const.ResourceState.undefined,
                                    const.ResourceState.skipped_for_undefined,
                                }:
                                    extra_fields["last_non_deploying_status"] = const.NonDeployingResourceState(status)

                            await res.update_persistent_state(
                                **extra_fields,
                                last_deploy=finished,
                                last_deployed_attribute_hash=res.attribute_hash,
                                connection=inner_connection,
                            )

                            model_version = res.model

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
                assert model_version is not None  # mypy can't figure this out
                # Make sure tasks are scheduled AFTER the tx is done.
                # This method is only called if the transaction commits successfully.
                self.add_background_task(data.ConfigurationModel.mark_done_if_done(env.id, model_version))

                waiting_agents = {
                    (Id.parse_id(prov).get_agent_name(), res.resource_version_id) for res in resources for prov in res.provides
                }

                for agent, resource_id in waiting_agents:
                    aclient = self.get_agent_client(env.id, agent)
                    if aclient is not None:
                        if change is None:
                            my_change = const.Change.nochange
                        else:
                            my_change = change

                        self.add_background_task(
                            aclient.resource_event(env.id, agent, resource_id, send_events, status, my_change, changes)
                        )

            connection.call_after_tx(post_deploy_update)
