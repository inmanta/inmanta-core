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
import logging
import os
import shutil
import sys
import time
import uuid
from asyncio import queues, subprocess
from collections.abc import Iterable, Iterator, Mapping, Sequence, Set
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from functools import reduce
from typing import Any, Optional, Union, assert_never, cast
from uuid import UUID

import asyncpg.connection

import inmanta.config
import inmanta.exceptions
import inmanta.server.services.environmentlistener
from inmanta import config as global_config
from inmanta import const, data
from inmanta import logging as inmanta_logging
from inmanta import tracing
from inmanta.agent import config as agent_cfg
from inmanta.config import Config, config_map_to_str, scheduler_log_config
from inmanta.const import AGENT_SCHEDULER_ID, AgentAction, AgentStatus, AllAgentAction
from inmanta.data import APILIMIT, Environment, InvalidSort, model
from inmanta.data.model import DataBaseReport
from inmanta.protocol import encode_token, handle, methods, methods_v2
from inmanta.protocol.common import ReturnValue
from inmanta.protocol.exceptions import BadRequest, Conflict, Forbidden, NotFound, ShutdownInProgress
from inmanta.server import (
    SLICE_AGENT_MANAGER,
    SLICE_AUTOSTARTED_AGENT_MANAGER,
    SLICE_DATABASE,
    SLICE_ENVIRONMENT,
    SLICE_SERVER,
    SLICE_SESSION_MANAGER,
    SLICE_TRANSPORT,
)
from inmanta.server import config as opt
from inmanta.server import protocol
from inmanta.server.protocol import ReturnClient, ServerSlice, SessionListener, SessionManager
from inmanta.server.server import Server
from inmanta.server.services import environmentservice
from inmanta.types import Apireturn, ArgumentTypes, ResourceIdStr, ReturnTupple

from ..data.dataview import AgentView
from . import config as server_config
from .validate_filter import InvalidFilter

LOGGER = logging.getLogger(__name__)


"""
Model in server         On Agent

+---------------+        +----------+
|               |        |          |
|  ENVIRONMENT  |   +---->  PROC    |
|               |   |    |          |
+------+--------+   |    +----+-----+
       |            |         |
       |            |         |
+------v--------+   |    +----v-------------+
|               |   |    |                  |
|  AGENT        |   |    |   AGENT INSTANCE |
|               |   |    |                  |
+------+--------+   |    +------------------+
       |            |
       |            |
+------v--------+   |
|               |   |
|  SESSION      +---+
|               |
+---------------+


dryrun_update

set_parameters
"""


class SessionActionType(str, Enum):
    REGISTER_SESSION = "register_session"
    EXPIRE_SESSION = "expire_session"
    SEEN_SESSION = "seen_session"


class SessionAction:
    """
    A session update to be executed by the AgentManager.
    """

    def __init__(
        self, action_type: SessionActionType, session: protocol.Session, endpoint_names_snapshot: set[str], timestamp: datetime
    ):
        self.action_type = action_type
        self.session = session
        self.endpoint_names_snapshot = endpoint_names_snapshot
        self.timestamp = timestamp


# Internal tuning constants

AUTO_STARTED_AGENT_WAIT = 5
# How long (in seconds) do we wait for autostarted agents. The wait time is reset any time a new instance comes online
AUTO_STARTED_AGENT_WAIT_LOG_INTERVAL = 1
# When waiting for an autostarted agent, how long (in seconds) do we wait before we log the wait status


class AgentManager(ServerSlice, SessionListener):
    """
    This class contains all server functionality related to the management of agents.
    Each logical agent managed by an instance of this class has at most one primary agent instance process associated with
    it. A subset of these processes are autostarted, those are managed by :py:class:`AutostartedAgentManager`.
    The server ignores all requests from non-primary agent instances. Therefore an agent without a primary is effectively
    paused as far as the server is concerned, though any rogue agent instances could still perform actions agent-side.

    Throughout this class the terms "logical agent" or sometimes just "agent" refer to a logical agent managed by an
    instance of this class. The terms "agent instance", "agent process" or just "process" refer to a concrete process
    running an agent instance, which might be the primary for a logical agent.
    """

    def __init__(self, closesessionsonstart: bool = True, fact_back_off: Optional[int] = None) -> None:
        super().__init__(SLICE_AGENT_MANAGER)

        if fact_back_off is None:
            fact_back_off = opt.server_fact_resource_block.get()

        # back-off timer for fact requests
        self._fact_resource_block: int = fact_back_off
        # per resource time of last fact request
        self._fact_resource_block_set: dict[str, float] = {}

        # session lock
        self.session_lock = asyncio.Lock()
        # all sessions
        self.sessions: dict[UUID, protocol.Session] = {}
        # live sessions: Sessions to agents which are primary and unpaused
        self.tid_endpoint_to_session: dict[tuple[UUID, str], protocol.Session] = {}
        # All endpoints associated with a sid
        self.endpoints_for_sid: dict[uuid.UUID, set[str]] = {}

        # This queue ensures that notifications from the SessionManager are processed in the same order
        # in which they arrive in the SessionManager, without blocking the SessionManager.
        self._session_listener_actions: queues.Queue[SessionAction] = queues.Queue()

        self.closesessionsonstart: bool = closesessionsonstart

    async def get_status(self) -> Mapping[str, ArgumentTypes | Mapping[str, ArgumentTypes]]:
        # The basic report

        out: dict[str, ArgumentTypes | Mapping[str, ArgumentTypes]] = {
            "resource_facts": len(self._fact_resource_block_set),
            "sessions": len(self.sessions),
        }

        # Try to get more info from scheduler, but make sure not to timeout
        schedulers = self.get_all_schedulers()
        deadline = 0.9 * Server.GET_SLICE_STATUS_TIMEOUT

        async def get_report(env: uuid.UUID, session: protocol.Session) -> tuple[uuid.UUID, DataBaseReport]:
            result = await asyncio.wait_for(session.client.get_db_status(), deadline)
            assert result.code == 200
            # Mypy can't help here, ....
            return (env, DataBaseReport(**result.result["data"]))

        # Get env name mapping in parallel with next call
        env_mapping = asyncio.create_task(
            asyncio.wait_for(Environment.get_list(details=False, is_marked_for_deletion=False), deadline)
        )
        # Get the reports of all schedulers
        results = await asyncio.gather(*[get_report(env, scheduler) for env, scheduler in schedulers], return_exceptions=True)
        try:
            # This can timeout, but not likely
            env_mapping_result = await env_mapping
            uuid_to_name = {env.id: env.name for env in env_mapping_result}
        except TimeoutError:
            # default to uuid's
            uuid_to_name = {}

        # Filter out timeouts and other errors
        good_reports = [x[1] for x in results if not isinstance(x, BaseException)]

        def short_report(report: DataBaseReport) -> Mapping[str, ArgumentTypes]:
            return {
                "connected": report.connected,
                "max_pool": report.max_pool,
                "open_connections": report.open_connections,
                "free_connections": report.free_connections,
                "pool_exhaustion_time": report.pool_exhaustion_time,
            }

        if good_reports:
            total: DataBaseReport = reduce(lambda x, y: x + y, good_reports)
            out["database"] = total.database
            out["host"] = total.host
            out["total"] = short_report(total)

        for result in results:
            if isinstance(result, BaseException):
                logging.debug("Failed to collect database status for scheduler", exc_info=True)
            else:
                the_uuid = result[0]
                # Default name to uuid
                name = uuid_to_name.get(the_uuid, str(the_uuid))
                out[name] = short_report(result[1])

        return out

    def get_dependencies(self) -> list[str]:
        return [SLICE_DATABASE, SLICE_SESSION_MANAGER]

    def get_depended_by(self) -> list[str]:
        return [SLICE_TRANSPORT]

    async def prestart(self, server: protocol.Server) -> None:
        await ServerSlice.prestart(self, server)
        autostarted_agent_manager = server.get_slice(SLICE_AUTOSTARTED_AGENT_MANAGER)
        assert isinstance(autostarted_agent_manager, AutostartedAgentManager)
        self._autostarted_agent_manager = autostarted_agent_manager
        presession = server.get_slice(SLICE_SESSION_MANAGER)
        assert isinstance(presession, SessionManager)
        presession.add_listener(self)

    async def start(self) -> None:
        await super().start()

        if self.closesessionsonstart:
            await self._expire_all_sessions_in_db()

        self.add_background_task(self._process_session_listener_actions())
        # Schedule cleanup agentprocess and agentinstance tables
        agent_process_purge_interval = opt.agent_process_purge_interval.get()
        if agent_process_purge_interval > 0:
            self.schedule(
                self._purge_agent_processes, interval=agent_process_purge_interval, initial_delay=0, cancel_on_stop=False
            )

    async def prestop(self) -> None:
        await super().prestop()

    async def stop(self) -> None:
        await super().stop()

    def get_all_schedulers(self) -> list[tuple[uuid.UUID, protocol.Session]]:
        # Linear scan, but every item should be a hit
        return [
            (env_id, session)
            for (env_id, agent_id), session in self.tid_endpoint_to_session.items()
            if agent_id == AGENT_SCHEDULER_ID
        ]

    async def halt_agents(self, env: data.Environment, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        """
        Halts all agents for an environment. Persists prior paused state. Also halts the scheduler "agent"
        """
        await data.Agent.persist_on_halt(env.id, connection=connection)
        await self._pause_agent(env, connection=connection)  # excludes scheduler
        await self._pause_agent(env, endpoint=const.AGENT_SCHEDULER_ID, connection=connection)

    async def resume_agents(self, env: data.Environment, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        """
        Resumes after halting. Unpauses all agents that had been paused by halting, then restarts the scheduler.
        """
        to_unpause: list[str] = await data.Agent.persist_on_resume(env.id, connection=connection)
        await asyncio.gather(*[self._unpause_agent(env, agent, connection=connection) for agent in to_unpause])
        await self._unpause_agent(env, endpoint=const.AGENT_SCHEDULER_ID, connection=connection)

    @handle(methods_v2.all_agents_action, env="tid")
    async def all_agents_action(self, env: data.Environment, action: AllAgentAction) -> None:
        if env.halted and action in {AllAgentAction.pause, AllAgentAction.unpause}:
            raise Forbidden("Can not pause or unpause agents when the environment has been halted.")
        if not env.halted and action in {AllAgentAction.keep_paused_on_resume, AllAgentAction.unpause_on_resume}:
            raise Forbidden("Cannot set on_resume state of agents when the environment is not halted.")
        match action:
            case AllAgentAction.pause:
                await self._pause_agent(env=env)
            case AllAgentAction.unpause:
                await self._unpause_agent(env=env)
            case AllAgentAction.keep_paused_on_resume:
                await self._set_unpause_on_resume(env, should_be_unpaused_on_resume=False)
            case AllAgentAction.unpause_on_resume:
                await self._set_unpause_on_resume(env, should_be_unpaused_on_resume=True)
            case AllAgentAction.remove_all_agent_venvs:
                await self._remove_executor_venvs(env)
            case _ as _never:
                assert_never(_never)

    async def _remove_executor_venvs(self, env: data.Environment) -> None:
        """
        Remove the venvs of the executors used by the given environment.
        """
        agent_client = self.get_agent_client(tid=env.id, endpoint=AGENT_SCHEDULER_ID, live_agent_only=False)
        if agent_client:
            self.add_background_task(agent_client.remove_executor_venvs())
        else:
            raise Conflict(f"No scheduler process is running for environment {env.id}")

    @handle(methods_v2.agent_action, env="tid")
    async def agent_action(self, env: data.Environment, name: str, action: AgentAction) -> None:
        if name == const.AGENT_SCHEDULER_ID:
            raise BadRequest(f"Particular action cannot be directed towards the Scheduler agent: {action.name}")

        if env.halted and action in {AgentAction.pause, AgentAction.unpause}:
            raise Forbidden("Can not pause or unpause agents when the environment has been halted.")
        if not env.halted and action in {AgentAction.keep_paused_on_resume, AgentAction.unpause_on_resume}:
            raise Forbidden("Cannot set on_resume state of agents when the environment is not halted.")
        match action:
            case AgentAction.pause:
                await self._pause_agent(env, name)
            case AgentAction.unpause:
                await self._unpause_agent(env, name)
            case AgentAction.keep_paused_on_resume:
                await self._set_unpause_on_resume(env, should_be_unpaused_on_resume=False, endpoint=name)
            case AgentAction.unpause_on_resume:
                await self._set_unpause_on_resume(env, should_be_unpaused_on_resume=True, endpoint=name)
            case _ as _never:
                assert_never(_never)

    async def _update_paused_status_agent(
        self,
        env: data.Environment,
        new_paused_status: bool,
        endpoint: Optional[str] = None,
        *,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> None:
        """
        Helper method to pause / unpause a logical agent by pausing an active agent instance if it exists and notify the
        scheduler that something has changed.

        If no endpoint provided, pauses all logical agents. This does not include the scheduler itself.
        """
        # We need this lock otherwise, we would have transaction conflict in DB
        async with self.session_lock:
            await data.Agent.pause(env=env.id, endpoint=endpoint, paused=new_paused_status, connection=connection)
            key = (env.id, const.AGENT_SCHEDULER_ID)
            live_session = self.tid_endpoint_to_session.get(key)
            if live_session:
                await live_session.get_client().set_state(endpoint, enabled=not new_paused_status)

    async def _pause_agent(
        self, env: data.Environment, endpoint: Optional[str] = None, connection: Optional[asyncpg.connection.Connection] = None
    ) -> None:
        """
        Pause a logical agent by pausing an active agent instance if it exists.
        If no endpoint provided, pauses all logical agents. This does not include the scheduler itself.
        """
        await self._update_paused_status_agent(env=env, new_paused_status=True, endpoint=endpoint, connection=connection)

    async def _unpause_agent(
        self, env: data.Environment, endpoint: Optional[str] = None, connection: Optional[asyncpg.connection.Connection] = None
    ) -> None:
        """
        Unpause a logical agent by pausing an active agent instance if it exists.
        If no endpoint provided, pauses all logical agents. This does not include the scheduler itself.
        """
        await self._update_paused_status_agent(env=env, new_paused_status=False, endpoint=endpoint, connection=connection)

    async def _set_unpause_on_resume(
        self,
        env: data.Environment,
        should_be_unpaused_on_resume: bool,
        endpoint: Optional[str] = None,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> None:
        """
        Set the unpause_on_resume field of an agent (or all agents in an environment when the endpoint is set to None)
        so that the agent is paused or unpaused after the environment is resumed
        """
        await data.Agent.set_unpause_on_resume(
            env=env.id, endpoint=endpoint, should_be_unpaused_on_resume=should_be_unpaused_on_resume, connection=connection
        )

    async def _process_session_listener_actions(self) -> None:
        """
        This is the consumer of the _session_listener_actions queue.
        """
        while not self.is_stopping():
            try:
                session_action = await self._session_listener_actions.get()
                await self._process_action(session_action)
            except asyncio.CancelledError:
                return
            except Exception:
                LOGGER.exception(
                    "An exception occurred while handling session action %s on session id %s.",
                    session_action.action_type.name,
                    session_action.session.id,
                    exc_info=True,
                )
            finally:
                try:
                    self._session_listener_actions.task_done()
                except Exception:
                    # Should never occur
                    pass

    async def _process_action(self, action: SessionAction) -> None:
        """
        Process a specific SessionAction.
        """
        action_type = action.action_type
        if action_type == SessionActionType.REGISTER_SESSION:
            await self._register_session(action.session, action.endpoint_names_snapshot, action.timestamp)
        elif action_type == SessionActionType.SEEN_SESSION:
            await self._seen_session(action.session, action.endpoint_names_snapshot)
        elif action_type == SessionActionType.EXPIRE_SESSION:
            await self._expire_session(action.session, action.endpoint_names_snapshot, action.timestamp)
        else:
            LOGGER.warning("Unknown SessionAction %s", action_type.name)

    # Notify from session listener
    async def new_session(self, session: protocol.Session, endpoint_names_snapshot: set[str]) -> None:
        """
        The _session_listener_actions queue ensures that all SessionActions are executed in the order of arrival.
        """
        session_action = SessionAction(
            action_type=SessionActionType.REGISTER_SESSION,
            session=session,
            endpoint_names_snapshot=endpoint_names_snapshot,
            timestamp=datetime.now().astimezone(),
        )
        await self._session_listener_actions.put(session_action)

    # Notify from session listener
    async def expire(self, session: protocol.Session, endpoint_names_snapshot: set[str]) -> None:
        """
        The _session_listener_actions queue ensures that all SessionActions are executed in the order of arrival.
        """
        session_action = SessionAction(
            action_type=SessionActionType.EXPIRE_SESSION,
            session=session,
            endpoint_names_snapshot=endpoint_names_snapshot,
            timestamp=datetime.now().astimezone(),
        )
        await self._session_listener_actions.put(session_action)

    # Notify from session listener
    async def seen(self, session: protocol.Session, endpoint_names_snapshot: set[str]) -> None:
        """
        The _session_listener_actions queue ensures that all SessionActions are executed in the order of arrival.
        """
        session_action = SessionAction(
            action_type=SessionActionType.SEEN_SESSION,
            session=session,
            endpoint_names_snapshot=endpoint_names_snapshot,
            timestamp=datetime.now().astimezone(),
        )
        await self._session_listener_actions.put(session_action)

    # Seen
    @tracing.instrument("AgentManager.seen_session", extract_args=True)
    async def _seen_session(self, session: protocol.Session, endpoint_names_snapshot: set[str]) -> None:
        endpoints_with_new_primary: list[tuple[str, Optional[uuid.UUID]]] = []
        async with self.session_lock:
            endpoints_in_agent_manager = self.endpoints_for_sid[session.id]
            endpoints_in_session = endpoint_names_snapshot
            endpoints_to_add = endpoints_in_session - endpoints_in_agent_manager
            LOGGER.debug("Adding endpoints %s to session %s on %s", endpoints_to_add, session.id, session.nodename)
            endpoints_to_remove = endpoints_in_agent_manager - endpoints_in_session
            LOGGER.debug("Removing endpoints %s from session %s on %s", endpoints_to_remove, session.id, session.nodename)

            endpoints_with_new_primary += await self._failover_endpoints(session, endpoints_to_remove)
            endpoints_with_new_primary += await self._ensure_primary_if_not_exists(session, endpoints_to_add)
            self.endpoints_for_sid[session.id] = endpoints_in_session

        self.add_background_task(
            self._log_session_seen_to_db(session, endpoints_to_add, endpoints_to_remove, endpoints_with_new_primary)
        )

    async def _log_session_seen_to_db(
        self,
        session: protocol.Session,
        endpoints_to_add: set[str],
        endpoints_to_remove: set[str],
        endpoints_with_new_primary: list[tuple[str, Optional[uuid.UUID]]],
    ) -> None:
        """
        Note: This method call is allowed to fail when the database connection is lost.
        """
        now = datetime.now().astimezone()
        async with data.AgentProcess.get_connection() as connection:
            async with connection.transaction():
                await data.AgentProcess.update_last_seen(session.id, now, connection)
                await data.AgentInstance.log_instance_creation(session.tid, session.id, endpoints_to_add, connection)
                await data.AgentInstance.log_instance_expiry(session.id, endpoints_to_remove, now, connection)
                await data.Agent.update_primary(session.tid, endpoints_with_new_primary, now, connection)

    # Session registration
    async def _register_session(self, session: protocol.Session, endpoint_names_snapshot: set[str], now: datetime) -> None:
        """
        This method registers a new session in memory and asynchronously updates the agent
        session log in the database. When the database connection is lost, the get_statuses()
        call fails and the new session will be refused.
        """
        LOGGER.debug("New session %s for agents %s on %s", session.id, endpoint_names_snapshot, session.nodename)
        async with self.session_lock:
            tid = session.tid
            sid = session.get_id()
            self.sessions[sid] = session
            self.endpoints_for_sid[sid] = endpoint_names_snapshot
            try:
                endpoints_with_new_primary = await self._ensure_primary_if_not_exists(session, endpoint_names_snapshot)
            except Exception as e:
                # Database connection failed
                del self.sessions[sid]
                del self.endpoints_for_sid[sid]
                self.add_background_task(session.expire(timeout=0))
                raise e

        self.add_background_task(
            self._log_session_creation_to_db(tid, session, endpoint_names_snapshot, endpoints_with_new_primary, now)
        )

    async def _log_session_creation_to_db(
        self,
        tid: uuid.UUID,
        session: protocol.Session,
        endpoint_names: set[str],
        endpoints_with_new_primary: Sequence[tuple[str, Optional[uuid.UUID]]],
        now: datetime,
    ) -> None:
        """
        Note: This method call is allowed to fail when the database connection is lost.
        """
        async with data.AgentProcess.get_connection() as connection:
            async with connection.transaction():
                await data.AgentProcess.seen(tid, session.nodename, session.id, now, connection)
                await data.AgentInstance.log_instance_creation(tid, session.id, endpoint_names, connection)
                await data.Agent.update_primary(tid, endpoints_with_new_primary, now, connection)

    # Session expiry
    async def _expire_session(self, session: protocol.Session, endpoint_names_snapshot: set[str], now: datetime) -> None:
        """
        This method expires the given session and update the in-memory session state.
        The in-database session log is updated asynchronously. These database updates
        are allowed to fail when the database connection is lost.
        """
        if not self.is_running() or self.is_stopping():
            return
        async with self.session_lock:
            tid = session.tid
            sid = session.get_id()
            if sid not in self.sessions:
                # The session is already expired
                return
            LOGGER.debug("expiring session %s", sid)
            del self.sessions[sid]
            del self.endpoints_for_sid[sid]
            endpoints_with_new_primary = await self._failover_endpoints(session, endpoint_names_snapshot)

        self.add_background_task(self._log_session_expiry_to_db(tid, endpoints_with_new_primary, session, now))

    async def _log_session_expiry_to_db(
        self,
        tid: uuid.UUID,
        endpoints_with_new_primary: Sequence[tuple[str, Optional[uuid.UUID]]],
        session: protocol.Session,
        now: datetime,
    ) -> None:
        """
        Note: This method call is allowed to fail when the database connection is lost.
        """
        async with data.AgentProcess.get_connection() as connection:
            async with connection.transaction():
                # Make sure to access the database tables in the order defined in docs string of inmanta/data/__init__.py
                # to prevent deadlock issues.
                await data.AgentProcess.expire_process(session.id, now, connection)
                await data.AgentInstance.log_instance_expiry(session.id, session.endpoint_names, now, connection)
                await data.Agent.update_primary(tid, endpoints_with_new_primary, now, connection)

    async def _expire_all_sessions_in_db(self) -> None:
        async with self.session_lock:
            LOGGER.debug("Cleaning server session DB")
            async with data.AgentProcess.get_connection() as connection:
                async with connection.transaction():
                    await data.AgentProcess.expire_all(now=datetime.now().astimezone(), connection=connection)
                    await data.AgentInstance.expire_all(now=datetime.now().astimezone(), connection=connection)
                    await data.Agent.mark_all_as_non_primary(connection=connection)

    async def _purge_agent_processes(self) -> None:
        agent_processes_to_keep = opt.agent_processes_to_keep.get()
        await data.AgentProcess.cleanup(nr_expired_records_to_keep=agent_processes_to_keep)

    # Util
    async def _use_new_active_session_for_agent(self, tid: uuid.UUID, endpoint_name: str) -> Optional[protocol.Session]:
        """
        This method searches for a new active session for the given agent. If a new active session if found,
        the in-memory state of the agentmanager is updated to use that new session. No logging is done in the
        database.

        :return The new active session in use or None if no new active session was found

        Note: Always call under session lock.
        """
        key = (tid, endpoint_name)
        new_active_session = self._get_session_to_failover_agent(tid, endpoint_name)
        if new_active_session:
            self.tid_endpoint_to_session[key] = new_active_session
            set_state_call = new_active_session.get_client().set_state(endpoint_name, enabled=True)
            self.add_background_task(set_state_call)
        elif key in self.tid_endpoint_to_session:
            del self.tid_endpoint_to_session[key]
        return new_active_session

    async def _ensure_primary_if_not_exists(
        self, session: protocol.Session, endpoints: set[str]
    ) -> Sequence[tuple[str, uuid.UUID]]:
        """
        Make this session the primary session for the endpoints of this session if no primary exists and the agent is not
        paused.

        :return: The endpoints that got a new primary.

        Note: Always call under session lock.
        Note: This call will fail when the database connection is lost.
        """
        agent_statuses = await data.Agent.get_statuses(session.tid, endpoints)

        result = []
        for endpoint in endpoints:
            key = (session.tid, endpoint)
            if key not in self.tid_endpoint_to_session and agent_statuses[endpoint] != AgentStatus.paused:
                LOGGER.debug("set session %s as primary for agent %s in env %s", session.id, endpoint, session.tid)
                self.tid_endpoint_to_session[key] = session
                self.add_background_task(session.get_client().set_state(endpoint, enabled=True))
                result.append((endpoint, session.id))
        return result

    async def _failover_endpoints(
        self, session: protocol.Session, endpoints: set[str]
    ) -> Sequence[tuple[str, Optional[uuid.UUID]]]:
        """
        If the given session is the primary for a given endpoint, failover to a new session.

        :param endpoints: set of agent names to detach from this session

        :return: The endpoints that got a new primary.

        Note: Always call under session lock.
        """
        agent_statuses: dict[str, Optional[AgentStatus]] = await data.Agent.get_statuses(session.tid, endpoints)
        result = []
        for endpoint_name in endpoints:
            key = (session.tid, endpoint_name)
            if key in self.tid_endpoint_to_session and self.tid_endpoint_to_session[key].id == session.id:
                if agent_statuses[endpoint_name] != AgentStatus.paused:
                    new_active_session = await self._use_new_active_session_for_agent(session.tid, endpoint_name)
                    if new_active_session:
                        result.append((endpoint_name, new_active_session.id))
                    else:
                        result.append((endpoint_name, None))
                else:
                    # This should never occur. An agent cannot have an active session while its paused,
                    # given the fact that this method executes under session_lock
                    LOGGER.warning("Paused agent %s has an active session (sid=%s)", endpoint_name, session.id)
                    del self.tid_endpoint_to_session[key]
                    result.append((endpoint_name, None))
        return result

    def is_primary(self, env: data.Environment, sid: uuid.UUID, agent: str) -> bool:
        prim = self.tid_endpoint_to_session.get((env.id, agent), None)
        if not prim:
            return False
        return prim.get_id() == sid

    def get_session_for(self, tid: uuid.UUID, endpoint: str) -> Optional[protocol.Session]:
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

    def _get_session_to_failover_agent(self, tid: uuid.UUID, endpoint: str) -> Optional[protocol.Session]:
        current_active_session = self.tid_endpoint_to_session[(tid, endpoint)]
        for session in self.sessions.values():
            if endpoint in session.endpoint_names and session.tid == tid:
                if not current_active_session or session.id != current_active_session.id:
                    return session
        return None

    def get_agent_client(self, tid: uuid.UUID, endpoint: str, live_agent_only: bool = True) -> Optional[ReturnClient]:
        if isinstance(tid, str):
            tid = uuid.UUID(tid)
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

    async def expire_sessions_for_agents(self, env_id: uuid.UUID, endpoints: Set[str]) -> None:
        """
        Expire all sessions for any of the requested agent endpoints.
        """
        async with self.session_lock:
            sessions_to_expire: Iterator[protocol.Session] = (
                session for session in self.sessions.values() if endpoints & session.endpoint_names and session.tid == env_id
            )
            await asyncio.gather(*(s.expire_and_abort(timeout=0) for s in sessions_to_expire))

    async def are_agents_active(self, tid: uuid.UUID, endpoints: Iterable[str]) -> bool:
        """
        Return true iff all the given agents are in the up or the paused state.
        """
        return all(active for (_, active) in await self.get_agent_active_status(tid, endpoints))

    async def get_agent_active_status(self, tid: uuid.UUID, endpoints: Iterable[str]) -> list[tuple[str, bool]]:
        """
        Return a list of tuples where the first element of the tuple contains the name of an endpoint
        and the second a boolean indicating where there is an active (up or paused) agent for that endpoint.
        """
        all_sids_for_env = [sid for (sid, session) in self.sessions.items() if session.tid == tid]
        all_active_endpoints_for_env = {ep for sid in all_sids_for_env for ep in self.endpoints_for_sid[sid]}
        return [(ep, ep in all_active_endpoints_for_env) for ep in endpoints]

    async def expire_all_sessions_for_environment(self, env_id: uuid.UUID) -> None:
        async with self.session_lock:
            await asyncio.gather(*[s.expire_and_abort(timeout=0) for s in self.sessions.values() if s.tid == env_id])

    async def expire_all_sessions(self) -> None:
        async with self.session_lock:
            await asyncio.gather(*[s.expire_and_abort(timeout=0) for s in self.sessions.values()])

    # Agent Management
    @tracing.instrument("AgentManager.ensure_agent_registered")
    async def ensure_agent_registered(
        self, env: data.Environment, nodename: str, *, connection: Optional[asyncpg.connection.Connection] = None
    ) -> data.Agent:
        """
        Make sure that an agent has been created in the database
        """
        async with self.session_lock:
            agent = await data.Agent.get(env.id, nodename, connection=connection)
            if agent:
                return agent
            else:
                return await self._create_default_agent(env, nodename, connection=connection)

    async def _create_default_agent(
        self, env: data.Environment, nodename: str, *, connection: Optional[asyncpg.connection.Connection] = None
    ) -> data.Agent:
        """
        This method creates a new agent (agent in the model) in the database.
        If an active agent instance exists for the given agent, it is marked as the
        primary instance for that agent in the database.

        Note: This method must be called under session lock
        """
        saved = data.Agent(environment=env.id, name=nodename, paused=False)
        await saved.insert(connection=connection)

        key = (env.id, nodename)
        session = self.tid_endpoint_to_session.get(key)
        if session:
            await data.Agent.update_primary(
                env.id, [(nodename, session.id)], datetime.now().astimezone(), connection=connection
            )

        return saved

    # External APIS
    @handle(methods.get_agent_process, agent_sid="id")
    async def get_agent_process(self, agent_sid: uuid.UUID) -> Apireturn:
        return await self.get_agent_process_report(agent_sid)

    @handle(methods.list_agent_processes)
    async def list_agent_processes(
        self,
        environment: Optional[UUID],
        expired: bool,
        start: Optional[UUID] = None,
        end: Optional[UUID] = None,
        limit: Optional[int] = None,
    ) -> Apireturn:
        """List all agent processes whose sid is after start and before end

        :param environment: Optional, the environment the agent should come from.
        :param expired: If True, expired agents will also be shown, they are hidden otherwise.
        :param start: The sid all of the selected agent process should be greater than this, defaults to None
        :param end: The sid all of the selected agent process should be smaller than this, defaults to None
        :param limit: Whether to limit the number of returned entries, defaults to None
        :raises BadRequest: Limit, start and end can not be set together
        :raises NotFound: The given environment id does not exist!
        :raises BadRequest: Limit parameter can not exceed 1000
        """
        query: dict[str, Any] = {}
        if environment is not None:
            query["environment"] = environment
            env = await data.Environment.get_by_id(environment)
            if env is None:
                return 404, {"message": "The given environment id does not exist!"}
        if not expired:
            query["expired"] = None

        if limit is None:
            limit = APILIMIT
        elif limit > APILIMIT:
            raise BadRequest(f"Limit parameter can not exceed {APILIMIT}, got {limit}.")

        aps = await data.AgentProcess.get_list_paged(
            page_by_column="sid",
            limit=limit,
            start=start,
            end=end,
            no_obj=False,
            connection=None,
            **query,
        )

        processes = []
        for p in aps:
            agent_dict = p.to_dict()
            ais = await data.AgentInstance.get_list(process=p.sid)
            oais = []
            for ai in ais:
                a = ai.to_dict()
                oais.append(a)
            agent_dict["endpoints"] = oais
            processes.append(agent_dict)

        return 200, {"processes": processes}

    @handle(methods.list_agents, env="tid")
    async def list_agents(
        self,
        env: data.Environment,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Apireturn:
        """List all agents whose name is after start and before end

        :param env: The environment the agents should come from
        :param start: The name all of the selected agent should be greater than this, defaults to None
        :param end: The name all of the selected agent should be smaller than this, defaults to None
        :param limit: Whether to limit the number of returned entries, defaults to None
        :raises BadRequest: Limit, start and end can not be set together
        :raises BadRequest: Limit parameter can not exceed 1000
        """
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}
        new_agent_endpoint = await self.get_agents(env, limit, start, end, start, end)

        def mangle_format(agent: model.Agent) -> dict[str, object]:
            native = agent.model_dump()
            native["primary"] = ""
            native["state"] = agent.status
            if native["last_failover"] is None:
                native["last_failover"] = ""
            return native

        return 200, {
            "agents": [mangle_format(a) for a in new_agent_endpoint._response],
            "servertime": datetime.now().astimezone(),
        }

    @handle(methods.get_state, env="tid")
    async def get_state(self, env: data.Environment, sid: uuid.UUID, agent: str) -> Apireturn:
        tid: UUID = env.id
        if isinstance(tid, str):
            tid = uuid.UUID(tid)
        key = (tid, agent)
        session = self.tid_endpoint_to_session.get(key, None)
        if session is not None and session.id == sid:
            return 200, {"enabled": True}
        return 200, {"enabled": False}

    async def get_agent_process_report(self, agent_sid: uuid.UUID) -> ReturnTupple:
        ap = await data.AgentProcess.get_one(sid=agent_sid)
        if ap is None:
            return 404, {"message": "The given AgentProcess id does not exist!"}
        sid = ap.sid
        session_for_ap = self.sessions.get(sid, None)
        if session_for_ap is None:
            return 404, {"message": "The given AgentProcess is not live!"}
        client = session_for_ap.get_client()
        result = await client.get_status()
        return result.code, result.get_result()

    async def request_parameter(self, env_id: uuid.UUID, resource_id: ResourceIdStr) -> Apireturn:
        """
        Request the value of a parameter from an agent
        """
        if resource_id is not None and resource_id != "":
            env = await data.Environment.get_by_id(env_id)

            if env is None:
                raise NotFound(f"Environment with {env_id} does not exist.")

            # only request facts of a resource every _fact_resource_block time
            now = time.time()
            if (
                resource_id not in self._fact_resource_block_set
                or (self._fact_resource_block_set[resource_id] + self._fact_resource_block) < now
            ):
                await self._autostarted_agent_manager._ensure_scheduler(env_id)
                agent = const.AGENT_SCHEDULER_ID
                client = self.get_agent_client(env_id, agent)
                if client is not None:
                    await client.get_parameter(env_id, agent, resource_id)

                self._fact_resource_block_set[resource_id] = now

            else:
                LOGGER.debug(
                    "Ignore fact request for %s, last request was sent %d seconds ago.",
                    resource_id,
                    now - self._fact_resource_block_set[resource_id],
                )

            return 503, {"message": "Agents queried for resource parameter."}
        else:
            return 404, {"message": "resource_id parameter is required."}

    @handle(methods_v2.get_agents, env="tid")
    async def get_agents(
        self,
        env: data.Environment,
        limit: Optional[int] = None,
        start: Optional[Union[datetime, bool, str]] = None,
        end: Optional[Union[datetime, bool, str]] = None,
        first_id: Optional[str] = None,
        last_id: Optional[str] = None,
        filter: Optional[dict[str, list[str]]] = None,
        sort: str = "name.asc",
    ) -> ReturnValue[Sequence[model.Agent]]:
        try:
            handler = AgentView(
                environment=env,
                limit=limit,
                sort=sort,
                first_id=first_id,
                last_id=last_id,
                start=start,
                end=end,
                filter=filter,
            )
            out = await handler.execute()
            return out
        except (InvalidFilter, InvalidSort, data.InvalidQueryParameter, data.InvalidFieldNameException) as e:
            raise BadRequest(e.message) from e

    @handle(methods_v2.get_agent_process_details, env="tid")
    async def get_agent_process_details(self, env: data.Environment, id: uuid.UUID, report: bool = False) -> model.AgentProcess:
        agent_process = await data.AgentProcess.get_one(environment=env.id, sid=id)
        if not agent_process:
            raise NotFound(f"Agent process with id {id} not found")
        dto = agent_process.to_dto()
        if report:
            report_status, report_result = await self.get_agent_process_report(id)
            if report_status == 200:
                dto.state = report_result
        return dto


@dataclass
class ProcessDetails:
    """
    A dataclass that holds the details of a process.
    """

    process: subprocess.Process
    path_stdout: str
    path_stderr: str

    @property
    def pid(self) -> int:
        """
        Returns the process id of the process.
        """
        return self.process.pid

    def is_running(self) -> bool:
        """
        Return True iff the process is running.
        """
        return self.process.returncode is None


class AutostartedAgentManager(ServerSlice, inmanta.server.services.environmentlistener.EnvironmentListener):
    """
    An instance of this class manages scheduler processes.
    """

    environment_service: "environmentservice.EnvironmentService"

    def __init__(self) -> None:
        super().__init__(SLICE_AUTOSTARTED_AGENT_MANAGER)
        self._agent_procs: dict[UUID, ProcessDetails] = {}  # env uuid -> ProcessDetails
        self.agent_lock = asyncio.Lock()  # Prevent concurrent updates on _agent_procs

    async def get_status(self) -> Mapping[str, ArgumentTypes]:
        return {"processes": len(self._agent_procs)}

    async def prestart(self, server: protocol.Server) -> None:
        await ServerSlice.prestart(self, server)
        preserver = server.get_slice(SLICE_SERVER)
        assert isinstance(preserver, Server)
        self._server: Server = preserver
        self._server_storage: dict[str, str] = self._server._server_storage

        agent_manager = server.get_slice(SLICE_AGENT_MANAGER)
        assert isinstance(agent_manager, AgentManager)
        self._agent_manager = agent_manager

        self.environment_service = cast(environmentservice.EnvironmentService, server.get_slice(SLICE_ENVIRONMENT))
        self.environment_service.register_listener(self, inmanta.server.services.environmentlistener.EnvironmentAction.created)

    async def start(self) -> None:
        await super().start()
        self.add_background_task(self._start_agents())

    async def prestop(self) -> None:
        await super().prestop()
        await self._terminate_agents()

    async def stop(self) -> None:
        await super().stop()

    def get_dependencies(self) -> list[str]:
        return [SLICE_SERVER, SLICE_DATABASE, SLICE_AGENT_MANAGER]

    def get_depended_by(self) -> list[str]:
        return [SLICE_TRANSPORT]

    async def _start_agents(self) -> None:
        """
        Ensure that a scheduler is started for each environment having AUTOSTART_ON_START is true. This method
        is called on server start.
        """
        environments = await data.Environment.get_list()

        for env in environments:
            autostart = await env.get(data.AUTOSTART_ON_START)
            if not autostart:
                continue
            await self._ensure_scheduler(env.id)

    async def restart_agents(self, env: data.Environment) -> None:
        LOGGER.debug("Restarting Scheduler in environment %s", env.id)
        await self._ensure_scheduler(env.id)

    async def stop_agents(
        self,
        env: data.Environment,
        *,
        delete_venv: bool = False,
    ) -> None:
        """
        Stop all agents for this environment and close sessions
        """
        async with self.agent_lock:
            LOGGER.debug("Stopping scheduler for env %s", env.id)
            if env.id in self._agent_procs:
                proc_details = self._agent_procs[env.id]
                self._stop_process(proc_details)
                await self._wait_for_proc_bounded([proc_details])
                del self._agent_procs[env.id]
            if delete_venv:
                self._remove_venv_for_agent_in_env(env.id)

            LOGGER.debug("Expiring all sessions for %s", env.id)
            await self._agent_manager.expire_all_sessions_for_environment(env.id)

    async def _stop_scheduler(
        self,
        env: data.Environment,
    ) -> None:
        """
        Stop the scheduler for this environment and expire all its sessions.

        Must be called under the agent lock
        """
        LOGGER.debug("Stopping scheduler for environment %s", env.id)
        if env.id in self._agent_procs:
            proc_details = self._agent_procs[env.id]
            self._stop_process(proc_details)
            await self._wait_for_proc_bounded([proc_details])
            del self._agent_procs[env.id]

        LOGGER.debug("Expiring session for scheduler in environment %s", env.id)
        await self._agent_manager.expire_sessions_for_agents(env.id, endpoints={AGENT_SCHEDULER_ID})

    def _get_state_dir_for_agent_in_env(self, env_id: uuid.UUID) -> str:
        """
        Return the state dir to be used by the auto-started agent in the given environment.
        """
        state_dir: str = inmanta.config.state_dir.get()
        return os.path.join(state_dir, "server", str(env_id))

    def _remove_venv_for_agent_in_env(self, env_id: uuid.UUID) -> None:
        """
        Remove the venv for the auto-started agent in the given environment.
        """
        agent_state_dir: str = self._get_state_dir_for_agent_in_env(env_id)
        venv_dir: str = os.path.join(agent_state_dir, "agent", "env")
        try:
            shutil.rmtree(venv_dir)
        except FileNotFoundError:
            pass

    def _stop_process(self, process_details: ProcessDetails) -> None:
        try:
            process_details.process.terminate()
        except ProcessLookupError:
            # Process was already terminated
            pass

    async def _terminate_agents(self) -> None:
        async with self.agent_lock:
            LOGGER.debug("Stopping all schedulers")
            for proc_details in self._agent_procs.values():
                self._stop_process(proc_details)
            await self._wait_for_proc_bounded(self._agent_procs.values())
            LOGGER.debug("Expiring all sessions")
            await self._agent_manager.expire_all_sessions()

    # Start/Restart scheduler
    async def _ensure_scheduler(
        self,
        env: uuid.UUID,
        *,
        restart: bool = False,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> bool:
        """
        Ensure that the scheduler for the given environment, that should be autostarted, are started.

        :param env: The environment to start the scheduler for.
        :param restart: Restart the scheduler even if it's running.
        :param connection: The database connection to use. Must not be in a transaction context.

        :return: True iff a new scheduler process was started.
        """
        if no_start_scheduler:
            return False
        if self._stopping:
            raise ShutdownInProgress()

        if connection is not None and connection.is_in_transaction():
            # Should not be called in a transaction context because it has (immediate) side effects outside of the database
            # that are tied to the database state. Several inconsistency issues could occur if this runs in a transaction
            # context:
            #   - side effects based on oncommitted reads (may even need to be rolled back)
            #   - race condition with similar side effect flows due to stale reads (e.g. other flow pauses agent and kills
            #       process, this one brings it back because it reads the agent as unpaused)
            raise Exception("_ensure_scheduler should not be called in a transaction context")

        autostart_scheduler = {const.AGENT_SCHEDULER_ID}
        async with data.Agent.get_connection(connection) as connection:
            async with self.agent_lock:
                # silently ignore requests if this environment is halted
                refreshed_env: Optional[data.Environment] = await data.Environment.get_by_id(env, connection=connection)
                if refreshed_env is None:
                    raise inmanta.exceptions.EnvironmentNotFound(f"Can't ensure scheduler: environment {env} does not exist")
                if refreshed_env.halted:
                    return False

                are_active = await self._agent_manager.are_agents_active(env, autostart_scheduler)
                if not restart and are_active:
                    # do not start a new agent process if the agents are already active, regardless of whether their session
                    # is with an autostarted process or not.
                    return False

                start_new_process: bool
                if env not in self._agent_procs or not self._agent_procs[env].is_running():
                    # Start new process if none is currently running for this environment.
                    LOGGER.info("%s matches agents managed by server, ensuring they are started.", autostart_scheduler)
                    start_new_process = True
                elif restart:
                    LOGGER.info(
                        "%s matches agents managed by server, forcing restart: stopping process with PID %s.",
                        autostart_scheduler,
                        self._agent_procs[env].process,
                    )
                    await self._stop_scheduler(refreshed_env)
                    start_new_process = True
                else:
                    start_new_process = False

                if start_new_process:
                    self._agent_procs[env] = await self.__do_start_agent(refreshed_env, connection=connection)

                # Wait for all agents to start
                try:
                    await self._wait_for_agents(refreshed_env, autostart_scheduler, connection=connection)
                except asyncio.TimeoutError:
                    LOGGER.warning("Not all agent instances started successfully")
                return start_new_process

    async def __do_start_agent(
        self, env: data.Environment, *, connection: Optional[asyncpg.connection.Connection] = None
    ) -> ProcessDetails:
        """
        Start an autostarted agent process for the given environment. Should only be called if none is running yet.

        :return: A ProcessDetails object consisting of the agent process, the stdout log file and the stderr log file.
        """
        assert not assert_no_start_scheduler

        config: str = await self._make_agent_config(env, connection=connection)

        root_dir: str = self._server_storage["server"]
        config_dir = os.path.join(root_dir, str(env.id))

        if not os.path.exists(config_dir):
            os.mkdir(config_dir)

        config_path = os.path.join(config_dir, "scheduler.cfg")
        with open(config_path, "w+", encoding="utf-8") as fd:
            fd.write(config)

        out: str = os.path.join(self._server_storage["logs"], "agent-%s.out" % env.id)
        err: str = os.path.join(self._server_storage["logs"], "agent-%s.err" % env.id)

        proc: subprocess.Process = await self._fork_inmanta(
            [
                "--log-file-level",
                "DEBUG",
                "--config",
                config_path,
                *(["--config-dir", Config._config_dir] if Config._config_dir is not None else []),
                "scheduler",
            ],
            out,
            err,
        )

        LOGGER.debug("Started new agent with PID %s", proc.pid)
        return ProcessDetails(process=proc, path_stdout=out, path_stderr=err)

    async def _make_agent_config(
        self,
        env: data.Environment,
        *,
        connection: Optional[asyncpg.connection.Connection],
    ) -> str:
        """
        Generate the config file for the process that hosts the autostarted agents

        :param env: The environment for which to autostart agents
        :return: A string that contains the config file content.
        """
        environment_id = str(env.id)
        port: int = opt.server_bind_port.get()

        privatestatedir: str = self._get_state_dir_for_agent_in_env(env.id)

        # generate config file
        config = f"""[config]
state-dir=%(statedir)s
log-dir={global_config.log_dir.get()}

environment=%(env_id)s

[agent]
executor-cap={agent_cfg.agent_executor_cap.get()}
executor-retention-time={agent_cfg.agent_executor_retention_time.get()}

[agent_rest_transport]
port=%(port)s
host={opt.internal_server_address.get()}
""" % {
            "env_id": environment_id,
            "port": port,
            "statedir": privatestatedir,
        }

        if server_config.server_enable_auth.get():
            token = encode_token(["agent"], environment_id)
            config += """
token=%s
    """ % (token)

        ssl_cert: Optional[str] = server_config.server_ssl_key.get()
        ssl_ca: Optional[str] = server_config.server_ssl_ca_cert.get()

        if ssl_ca is not None and ssl_cert is not None:
            # override CA
            config += """
ssl=True
ssl_ca_cert_file=%s
    """ % (ssl_ca)
        elif ssl_cert is not None:
            # system CA
            config += """
ssl=True
    """
        config += f"""
[database]
wait_time={opt.db_wait_time.get()}
host={opt.db_host.get()}
port={opt.db_port.get()}
name={opt.db_name.get()}
username={opt.db_username.get()}
password={opt.db_password.get()}

[scheduler]
db-connection-pool-min-size={agent_cfg.scheduler_db_connection_pool_min_size.get()}
db-connection-pool-max-size={agent_cfg.scheduler_db_connection_pool_max_size.get()}
db-connection-timeout={agent_cfg.scheduler_db_connection_timeout.get()}

[influxdb]
host = {opt.influxdb_host.get()}
port = {opt.influxdb_port.get()}
name = {opt.influxdb_name.get()}
username = {opt.influxdb_username.get()}
password = {opt.influxdb_password.get()}
interval = {opt.influxdb_interval.get()}
tags = {config_map_to_str(opt.influxdb_tags.get())}
"""

        if scheduler_log_config.get():
            config += f"""

[logging]
scheduler = {os.path.abspath(scheduler_log_config.get())}
"""

        return config

    async def _fork_inmanta(
        self, args: list[str], outfile: Optional[str], errfile: Optional[str], cwd: Optional[str] = None
    ) -> subprocess.Process:
        """
        Fork an inmanta process from the same code base as the current code
        """
        full_args = ["-m", "inmanta.app", *args]
        # handles can be closed, owned by child process,...
        outhandle = None
        errhandle = None
        try:
            if outfile is not None:
                outhandle = open(outfile, "wb+")
            if errfile is not None:
                errhandle = open(errfile, "wb+")

            env = os.environ.copy()
            env.update(tracing.get_context())
            return await asyncio.create_subprocess_exec(
                sys.executable, *full_args, cwd=cwd, env=env, stdout=outhandle, stderr=errhandle
            )
        finally:
            if outhandle is not None:
                outhandle.close()
            if errhandle is not None:
                errhandle.close()

    async def _wait_for_agents(
        self,
        env: data.Environment,
        agents: Set[str],
        *,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> None:
        """
        Wait until all requested autostarted agent instances are active, e.g. after starting a new agent process.

        Must be called under the agent lock.

        :param env: The environment for which to wait for agents.
        :param agents: Autostarted agent endpoints to wait for.

        :raises TimeoutError: When not all agent instances are active and no new agent instance became active in the last
            5 seconds.
        """
        agent_statuses: dict[str, Optional[AgentStatus]] = await data.Agent.get_statuses(env.id, agents, connection=connection)
        # Only wait for agents that are not paused
        expected_agents_in_up_state: Set[str] = {
            agent_name
            for agent_name, status in agent_statuses.items()
            if status is not None and status is not AgentStatus.paused
        }

        assert env.id in self._agent_procs
        proc_details = self._agent_procs[env.id]

        actual_agents_in_up_state: set[str] = set()
        started = int(time.time())
        last_new_agent_seen = started
        last_log = started

        log_files = [
            inmanta_logging.LoggingConfigBuilder.get_log_file_for_scheduler(str(env.id), global_config.log_dir.get()),
            proc_details.path_stdout,
            proc_details.path_stderr,
        ]

        while len(expected_agents_in_up_state) != len(actual_agents_in_up_state):
            await asyncio.sleep(0.1)
            now = int(time.time())
            if now - last_new_agent_seen > AUTO_STARTED_AGENT_WAIT:
                LOGGER.warning(
                    "Timeout: agent with PID %s took too long to start: still waiting for agent instances %s."
                    " See log files %s for more information.",
                    proc_details.pid,
                    ",".join(sorted(expected_agents_in_up_state - actual_agents_in_up_state)),
                    ", ".join(log_files),
                )

                raise asyncio.TimeoutError()
            if now - last_log > AUTO_STARTED_AGENT_WAIT_LOG_INTERVAL:
                last_log = now
                LOGGER.debug(
                    "Waiting for agent with PID %s, waited %d seconds, %d/%d instances up",
                    proc_details.pid,
                    now - started,
                    len(actual_agents_in_up_state),
                    len(expected_agents_in_up_state),
                )
            new_actual_agents_in_up_state = {
                agent_name
                for agent_name in expected_agents_in_up_state
                if (
                    (session := self._agent_manager.tid_endpoint_to_session.get((env.id, agent_name), None)) is not None
                    # make sure to check for expiry because sessions are unregistered from the agent manager asynchronously
                    and not session.expired
                )
            }
            if len(new_actual_agents_in_up_state) > len(actual_agents_in_up_state):
                # Reset timeout timer because a new instance became active
                last_new_agent_seen = now
            actual_agents_in_up_state = new_actual_agents_in_up_state

        LOGGER.debug(
            "Agent process with PID %s is up for agent instances %s",
            proc_details.pid,
            ",".join(sorted(expected_agents_in_up_state)),
        )

    async def _wait_for_proc_bounded(
        self, proc_details: Iterable[ProcessDetails], timeout: float = const.SHUTDOWN_GRACE_HARD
    ) -> None:
        try:
            unfinished_processes = [p.process for p in proc_details if p.is_running()]
            await asyncio.wait_for(asyncio.gather(*[asyncio.shield(proc.wait()) for proc in unfinished_processes]), timeout)
        except asyncio.TimeoutError:
            LOGGER.warning("Agent processes did not close in time (%s)", [p.process for p in proc_details])

    async def environment_action_created(self, env: model.Environment) -> None:
        """
        Will be called when a new environment is created to create a scheduler agent

        :param env: The new environment
        """
        env_db = await data.Environment.get_by_id(env.id)
        assert env_db
        # We need to make sure that the AGENT_SCHEDULER is registered to be up and running
        await self._agent_manager.ensure_agent_registered(env_db, const.AGENT_SCHEDULER_ID)
        if not (assert_no_start_scheduler or no_start_scheduler):
            await self._ensure_scheduler(env.id)

    async def notify_agent_deploy_timer_update(self, env: data.Environment) -> None:
        agent_client = self._agent_manager.get_agent_client(tid=env.id, endpoint=AGENT_SCHEDULER_ID, live_agent_only=False)
        if agent_client:
            self.add_background_task(agent_client.notify_timer_update(env.id))


# For testing only
# Assert the scheduler will not be started (i.e. agent mock setup is correct)
assert_no_start_scheduler = False
# Ensure the scheduler is not started
no_start_scheduler = False
