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
import sys
import time
import uuid
from asyncio import queues, subprocess
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union, cast
from uuid import UUID

import asyncpg.connection

from inmanta import const, data, util
from inmanta.config import Config
from inmanta.const import AgentAction, AgentStatus
from inmanta.data import APILIMIT, InvalidSort, model
from inmanta.data.model import ResourceIdStr
from inmanta.protocol import encode_token, handle, methods, methods_v2
from inmanta.protocol.common import ReturnValue
from inmanta.protocol.exceptions import BadRequest, Forbidden, NotFound, ShutdownInProgress
from inmanta.resources import Id
from inmanta.server import (
    SLICE_AGENT_MANAGER,
    SLICE_AUTOSTARTED_AGENT_MANAGER,
    SLICE_DATABASE,
    SLICE_SERVER,
    SLICE_SESSION_MANAGER,
    SLICE_TRANSPORT,
)
from inmanta.server import config as opt
from inmanta.server import protocol
from inmanta.server.protocol import ReturnClient, ServerSlice, SessionListener, SessionManager
from inmanta.server.server import Server
from inmanta.types import Apireturn, ArgumentTypes

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


get_resources_for_agent

resource_action_update

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
        self, action_type: SessionActionType, session: protocol.Session, endpoint_names_snapshot: Set[str], timestamp: datetime
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
        super(AgentManager, self).__init__(SLICE_AGENT_MANAGER)

        if fact_back_off is None:
            fact_back_off = opt.server_fact_resource_block.get()

        # back-off timer for fact requests
        self._fact_resource_block: int = fact_back_off
        # per resource time of last fact request
        self._fact_resource_block_set: Dict[str, float] = {}

        # session lock
        self.session_lock = asyncio.Lock()
        # all sessions
        self.sessions: Dict[UUID, protocol.Session] = {}
        # live sessions: Sessions to agents which are primary and unpaused
        self.tid_endpoint_to_session: Dict[Tuple[UUID, str], protocol.Session] = {}
        # All endpoints associated with a sid
        self.endpoints_for_sid: Dict[uuid.UUID, Set[str]] = {}

        # This queue ensures that notifications from the SessionManager are processed in the same order
        # in which they arrive in the SessionManager, without blocking the SessionManager.
        self._session_listener_actions: queues.Queue[SessionAction] = queues.Queue()

        self.closesessionsonstart: bool = closesessionsonstart

    async def get_status(self) -> Dict[str, ArgumentTypes]:
        return {
            "resource_facts": len(self._fact_resource_block_set),
            "sessions": len(self.sessions),
        }

    def get_dependencies(self) -> List[str]:
        return [SLICE_DATABASE, SLICE_SESSION_MANAGER]

    def get_depended_by(self) -> List[str]:
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

    async def prestop(self) -> None:
        await super().prestop()

    async def stop(self) -> None:
        await super().stop()

    async def halt_agents(self, env: data.Environment, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        """
        Halts all agents for an environment. Persists prior paused state.
        """
        await data.Agent.persist_on_halt(env.id, connection=connection)
        await self._pause_agent(env, connection=connection)

    async def resume_agents(self, env: data.Environment, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        """
        Resumes after halting. Unpauses all agents that had been paused by halting.
        """
        to_unpause: List[str] = await data.Agent.persist_on_resume(env.id, connection=connection)
        await asyncio.gather(*[self._unpause_agent(env, agent, connection=connection) for agent in to_unpause])

    @handle(methods_v2.all_agents_action, env="tid")
    async def all_agents_action(self, env: data.Environment, action: AgentAction) -> None:
        if env.halted and action in {AgentAction.pause, AgentAction.unpause}:
            raise Forbidden("Can not pause or unpause agents when the environment has been halted.")
        if not env.halted and action in {AgentAction.keep_paused_on_resume, AgentAction.unpause_on_resume}:
            raise Forbidden("Cannot set on_resume state of agents when the environment is not halted.")
        if action is AgentAction.pause:
            await self._pause_agent(env)
        elif action is AgentAction.unpause:
            await self._unpause_agent(env)
        elif action is AgentAction.keep_paused_on_resume:
            await self._set_unpause_on_resume(env, should_be_unpaused_on_resume=False)
        elif action is AgentAction.unpause_on_resume:
            await self._set_unpause_on_resume(env, should_be_unpaused_on_resume=True)
        else:
            raise BadRequest(f"Unknown agent action: {action.name}")

    @handle(methods_v2.agent_action, env="tid")
    async def agent_action(self, env: data.Environment, name: str, action: AgentAction) -> None:
        if env.halted and action in {AgentAction.pause, AgentAction.unpause}:
            raise Forbidden("Can not pause or unpause agents when the environment has been halted.")
        if not env.halted and action in {AgentAction.keep_paused_on_resume, AgentAction.unpause_on_resume}:
            raise Forbidden("Cannot set on_resume state of agents when the environment is not halted.")
        if action is AgentAction.pause:
            await self._pause_agent(env, name)
        elif action is AgentAction.unpause:
            await self._unpause_agent(env, name)
        elif action is AgentAction.keep_paused_on_resume:
            await self._set_unpause_on_resume(env, should_be_unpaused_on_resume=False, endpoint=name)
        elif action is AgentAction.unpause_on_resume:
            await self._set_unpause_on_resume(env, should_be_unpaused_on_resume=True, endpoint=name)
        else:
            raise BadRequest(f"Unknown agent action: {action.name}")

    async def _pause_agent(
        self, env: data.Environment, endpoint: Optional[str] = None, connection: Optional[asyncpg.connection.Connection] = None
    ) -> None:
        """
        Pause a logical agent by pausing an active agent instance if it exists, and removing the logical agent's primary.
        """

        async with self.session_lock:
            agents = await data.Agent.pause(env=env.id, endpoint=endpoint, paused=True, connection=connection)
            endpoints_with_new_primary = []
            for agent_name in agents:
                key = (env.id, agent_name)
                live_session = self.tid_endpoint_to_session.get(key)
                if live_session:
                    # The agent has an active agent instance that has to be paused
                    del self.tid_endpoint_to_session[key]
                    await live_session.get_client().set_state(agent_name, enabled=False)
                    endpoints_with_new_primary.append((agent_name, None))
            await data.Agent.update_primary(
                env.id, endpoints_with_new_primary, now=datetime.now().astimezone(), connection=connection
            )

    async def _unpause_agent(
        self, env: data.Environment, endpoint: Optional[str] = None, connection: Optional[asyncpg.connection.Connection] = None
    ) -> None:
        async with self.session_lock:
            agents = await data.Agent.pause(env=env.id, endpoint=endpoint, paused=False, connection=connection)
            endpoints_with_new_primary = []
            for agent_name in agents:
                key = (env.id, agent_name)
                live_session = self.tid_endpoint_to_session.get(key)
                # If the agent has a live_session, the agent wasn't paused
                if not live_session:
                    session = self.get_session_for(tid=env.id, endpoint=agent_name)
                    if session:
                        self.tid_endpoint_to_session[key] = session
                        await session.get_client().set_state(agent_name, enabled=True)
                        endpoints_with_new_primary.append((agent_name, session.id))
            await data.Agent.update_primary(
                env.id, endpoints_with_new_primary, now=datetime.now().astimezone(), connection=connection
            )

    async def _set_unpause_on_resume(
        self,
        env: data.Environment,
        should_be_unpaused_on_resume: bool,
        endpoint: Optional[str] = None,
        connection: Optional[asyncpg.connection.Connection] = None,
    ):
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
    async def new_session(self, session: protocol.Session, endpoint_names_snapshot: Set[str]) -> None:
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
    async def expire(self, session: protocol.Session, endpoint_names_snapshot: Set[str]) -> None:
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
    async def seen(self, session: protocol.Session, endpoint_names_snapshot: Set[str]) -> None:
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
    async def _seen_session(self, session: protocol.Session, endpoint_names_snapshot: Set[str]) -> None:
        endpoints_with_new_primary: List[Tuple[str, Optional[uuid.UUID]]] = []
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
        endpoints_to_add: Set[str],
        endpoints_to_remove: Set[str],
        endpoints_with_new_primary: List[Tuple[str, Optional[uuid.UUID]]],
    ) -> None:
        """
        Note: This method call is allowed to fail when the database connection is lost.
        """
        now = datetime.now().astimezone()
        async with data.AgentProcess.get_connection() as connection:
            async with connection.transaction():
                await data.AgentInstance.log_instance_creation(session.tid, session.id, endpoints_to_add, connection)
                await data.AgentInstance.log_instance_expiry(session.id, endpoints_to_remove, now, connection)
                await data.Agent.update_primary(session.tid, endpoints_with_new_primary, now, connection)
                await data.AgentProcess.update_last_seen(session.id, now, connection)

    # Session registration
    async def _register_session(self, session: protocol.Session, endpoint_names_snapshot: Set[str], now: datetime) -> None:
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
        endpoint_names: Set[str],
        endpoints_with_new_primary: Sequence[Tuple[str, Optional[uuid.UUID]]],
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
    async def _expire_session(self, session: protocol.Session, endpoint_names_snapshot: Set[str], now: datetime) -> None:
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
        endpoints_with_new_primary: Sequence[Tuple[str, Optional[uuid.UUID]]],
        session: protocol.Session,
        now: datetime,
    ) -> None:
        """
        Note: This method call is allowed to fail when the database connection is lost.
        """
        async with data.AgentProcess.get_connection() as connection:
            async with connection.transaction():
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
        self, session: protocol.Session, endpoints: Set[str]
    ) -> Sequence[Tuple[str, uuid.UUID]]:
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
        self, session: protocol.Session, endpoints: Set[str]
    ) -> Sequence[Tuple[str, Optional[uuid.UUID]]]:
        """
        If the given session is the primary for a given endpoint, failover to a new session.

        :return: The endpoints that got a new primary.

        Note: Always call under session lock.
        """
        agent_statuses = await data.Agent.get_statuses(session.tid, endpoints)
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

    async def are_agents_active(self, tid: uuid.UUID, endpoints: List[str]) -> bool:
        """
        Return true iff all the given agents are in the up or the paused state.
        """
        return all(active for (_, active) in await self.get_agent_active_status(tid, endpoints))

    async def get_agent_active_status(self, tid: uuid.UUID, endpoints: List[str]) -> List[Tuple[str, bool]]:
        """
        Return a list of tuples where the first element of the tuple contains the name of an endpoint
        and the second a boolean indicating where there is an active (up or paused) agent for that endpoint.
        """
        all_sids_for_env = [sid for (sid, session) in self.sessions.items() if session.tid == tid]
        all_active_endpoints_for_env = set(ep for sid in all_sids_for_env for ep in self.endpoints_for_sid[sid])
        return [(ep, ep in all_active_endpoints_for_env) for ep in endpoints]

    async def expire_all_sessions_for_environment(self, env_id: uuid.UUID) -> None:
        async with self.session_lock:
            await asyncio.gather(*[s.expire_and_abort(timeout=0) for s in self.sessions.values() if s.tid == env_id])

    async def expire_all_sessions(self) -> None:
        async with self.session_lock:
            await asyncio.gather(*[s.expire_and_abort(timeout=0) for s in self.sessions.values()])

    # Agent Management
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
        If an active agent instance exists for the given agent, it is marked as a the
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

    @handle(methods.trigger_agent, agent_id="id", env="tid")
    async def trigger_agent(self, env: UUID, agent_id: str) -> Apireturn:
        raise NotImplementedError()

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
        query: Dict[str, Any] = {}
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
        env: Optional[data.Environment],
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
        query = {}
        if env is not None:
            query["environment"] = env.id

        if limit is None:
            limit = APILIMIT
        elif limit > APILIMIT:
            raise BadRequest(f"Limit parameter can not exceed {APILIMIT}, got {limit}.")

        ags = await data.Agent.get_list_paged(
            page_by_column="name",
            order_by_column="name",
            order="ASC NULLS LAST",
            limit=limit,
            start=start,
            end=end,
            no_obj=False,
            lock=None,
            connection=None,
            **query,
        )

        return 200, {"agents": [a.to_dict() for a in ags], "servertime": util.datetime_utc_isoformat(datetime.now())}

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

    async def get_agent_process_report(self, agent_sid: uuid.UUID) -> Apireturn:
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

            # get a resource version
            res = await data.Resource.get_latest_version(env_id, resource_id)

            if res is None:
                return 404, {"message": "The resource has no recent version."}

            rid: Id = Id.parse_id(res.resource_version_id)
            version: int = rid.version

            # only request facts of a resource every _fact_resource_block time
            now = time.time()
            if (
                resource_id not in self._fact_resource_block_set
                or (self._fact_resource_block_set[resource_id] + self._fact_resource_block) < now
            ):

                agents = await data.ConfigurationModel.get_agents(env.id, version)
                await self._autostarted_agent_manager._ensure_agents(env, agents)

                client = self.get_agent_client(env_id, res.agent)
                if client is not None:
                    self.add_background_task(client.get_parameter(str(env_id), res.agent, res.to_dict()))

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

    @protocol.handle(methods_v2.get_agents, env="tid")
    async def get_agents(
        self,
        env: data.Environment,
        limit: Optional[int] = None,
        start: Optional[Union[datetime, bool, str]] = None,
        end: Optional[Union[datetime, bool, str]] = None,
        first_id: Optional[str] = None,
        last_id: Optional[str] = None,
        filter: Optional[Dict[str, List[str]]] = None,
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

    @protocol.handle(methods_v2.get_agent_process_details, env="tid")
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


class AutostartedAgentManager(ServerSlice):
    """
    An instance of this class manages autostarted agent instance processes. It does not manage the logical agents as those
    are managed by `:py:class:AgentManager`.
    """

    def __init__(self) -> None:
        super(AutostartedAgentManager, self).__init__(SLICE_AUTOSTARTED_AGENT_MANAGER)
        self._agent_procs: Dict[UUID, subprocess.Process] = {}  # env uuid -> subprocess.Process
        self.agent_lock = asyncio.Lock()  # Prevent concurrent updates on _agent_procs

    async def get_status(self) -> Dict[str, ArgumentTypes]:
        return {"processes": len(self._agent_procs)}

    async def prestart(self, server: protocol.Server) -> None:
        await ServerSlice.prestart(self, server)
        preserver = server.get_slice(SLICE_SERVER)
        assert isinstance(preserver, Server)
        self._server: Server = preserver
        self._server_storage: Dict[str, str] = self._server._server_storage

        agent_manager = server.get_slice(SLICE_AGENT_MANAGER)
        assert isinstance(agent_manager, AgentManager)
        self._agent_manager = agent_manager

    async def start(self) -> None:
        await super().start()
        self.add_background_task(self._start_agents())

    async def prestop(self) -> None:
        await super().prestop()
        await self._terminate_agents()

    async def stop(self) -> None:
        await super().stop()

    def get_dependencies(self) -> List[str]:
        return [SLICE_SERVER, SLICE_DATABASE, SLICE_AGENT_MANAGER]

    def get_depended_by(self) -> List[str]:
        return [SLICE_TRANSPORT]

    async def _start_agents(self) -> None:
        """
        Ensure that autostarted agents of each environment are started when AUTOSTART_ON_START is true. This method
        is called on server start.
        """
        environments = await data.Environment.get_list()
        for env in environments:
            autostart = await env.get(data.AUTOSTART_ON_START)
            if autostart:
                agents = await data.Agent.get_list(environment=env.id)
                agent_list = [a.name for a in agents]
                await self._ensure_agents(env, agent_list)

    async def restart_agents(self, env: data.Environment) -> None:
        LOGGER.debug("Restarting agents in environment %s", env.id)
        agents = await data.Agent.get_list(environment=env.id)
        agent_list = [a.name for a in agents]
        await self._ensure_agents(env, agent_list, True)

    async def stop_agents(self, env: data.Environment) -> None:
        """
        Stop all agents for this environment and close sessions
        """
        async with self.agent_lock:
            LOGGER.debug("Stopping all autostarted agents for env %s", env.id)
            if env.id in self._agent_procs:
                subproc = self._agent_procs[env.id]
                self._stop_process(subproc)
                await self._wait_for_proc_bounded([subproc])
                del self._agent_procs[env.id]

            LOGGER.debug("Expiring all sessions for %s", env.id)
            await self._agent_manager.expire_all_sessions_for_environment(env.id)

    def _stop_process(self, process: subprocess.Process) -> None:
        try:
            process.terminate()
        except ProcessLookupError:
            # Process was already terminated
            pass

    async def _terminate_agents(self) -> None:
        async with self.agent_lock:
            LOGGER.debug("Stopping all autostarted agents")
            for proc in self._agent_procs.values():
                self._stop_process(proc)
            await self._wait_for_proc_bounded(self._agent_procs.values())
            LOGGER.debug("Expiring all sessions")
            await self._agent_manager.expire_all_sessions()

    # Start/stop agents
    async def _ensure_agents(
        self,
        env: data.Environment,
        agents: List[str],
        restart: bool = False,
        *,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> bool:
        """
        Ensure that all agents defined in the current environment (model) and that should be autostarted, are started.

        :param env: The environment to start the agents for
        :param agents: A list of agent names that possibly should be started in this environment.
        :param restart: Restart all agents even if the list of agents is up to date.
        """
        if self._stopping:
            raise ShutdownInProgress()

        agent_map: Dict[str, str]
        agent_map = cast(
            Dict[str, str], await env.get(data.AUTOSTART_AGENT_MAP, connection=connection)
        )  # we know the type of this map

        # The internal agent should always be present in the autostart_agent_map. If it's not, this autostart_agent_map was
        # set in a previous version of the orchestrator which didn't have this constraint. This code fixes the inconsistency.
        if "internal" not in agent_map:
            agent_map["internal"] = "local:"
            await env.set(data.AUTOSTART_AGENT_MAP, dict(agent_map), connection=connection)

        agents = [agent for agent in agents if agent in agent_map]
        needsstart = restart
        if len(agents) == 0:
            return False

        async def is_start_agent_required() -> bool:
            if needsstart:
                return True
            return not await self._agent_manager.are_agents_active(env.id, agents)

        async with self.agent_lock:
            # silently ignore requests if this environment is halted
            refreshed_env: Optional[data.Environment] = await data.Environment.get_by_id(env.id, connection=connection)
            if refreshed_env is None:
                raise Exception("Can't ensure agent: environment %s does not exist" % env.id)
            env = refreshed_env
            if env.halted:
                return False

            if await is_start_agent_required():
                LOGGER.info("%s matches agents managed by server, ensuring it is started.", agents)
                res = await self.__do_start_agent(agents, env, connection=connection)
                return res
        return False

    async def __do_start_agent(
        self, agents: List[str], env: data.Environment, *, connection: Optional[asyncpg.connection.Connection] = None
    ) -> bool:
        """
        Start an agent process for the given agents in the given environment

        Note: Always call under agent_lock
        """
        agent_map: Dict[str, str]
        agent_map = cast(Dict[str, str], await env.get(data.AUTOSTART_AGENT_MAP, connection=connection))
        config: str
        config = await self._make_agent_config(env, agents, agent_map, connection=connection)

        config_dir = os.path.join(self._server_storage["agents"], str(env.id))
        if not os.path.exists(config_dir):
            os.mkdir(config_dir)

        config_path = os.path.join(config_dir, "agent.cfg")
        with open(config_path, "w+", encoding="utf-8") as fd:
            fd.write(config)

        out: str = os.path.join(self._server_storage["logs"], "agent-%s.out" % env.id)
        err: str = os.path.join(self._server_storage["logs"], "agent-%s.err" % env.id)

        agent_log = os.path.join(self._server_storage["logs"], "agent-%s.log" % env.id)

        proc: Optional[subprocess.Process] = None
        try:
            proc = await self._fork_inmanta(
                [
                    "-vvvv",
                    "--timed-logs",
                    "--config",
                    config_path,
                    "--config-dir",
                    Config._config_dir if Config._config_dir is not None else "",
                    "--log-file",
                    agent_log,
                    "agent",
                ],
                out,
                err,
            )

            if env.id in self._agent_procs and self._agent_procs[env.id] is not None:
                # If the return code is not None the process is already terminated
                if self._agent_procs[env.id].returncode is None:
                    LOGGER.debug("Terminating old agent with PID %s", self._agent_procs[env.id].pid)
                    self._agent_procs[env.id].terminate()
                    await self._wait_for_proc_bounded([self._agent_procs[env.id]])
            self._agent_procs[env.id] = proc
        except Exception as e:
            # Prevent dangling processes
            if proc is not None and proc.returncode is None:
                proc.kill()
            raise e

        async def _wait_until_agent_instances_are_active() -> None:
            """
            Wait until all AgentInstances for the endpoints `agents` are active.
            A TimeoutError is raised when not all AgentInstances are active and no new AgentInstance
            became active in the last 5 seconds.
            """
            agent_statuses: Dict[str, Optional[AgentStatus]] = await data.Agent.get_statuses(env.id, set(agents))
            # Only wait for agents that are not paused
            expected_agents_in_up_state: Set[str] = {
                agent_name
                for agent_name, status in agent_statuses.items()
                if status is not None and status is not AgentStatus.paused
            }
            actual_agents_in_up_state: Set[str] = set()
            started = int(time.time())
            last_new_agent_seen = started
            last_log = started

            while len(expected_agents_in_up_state) != len(actual_agents_in_up_state):
                await asyncio.sleep(0.1)
                now = int(time.time())
                if now - last_new_agent_seen > AUTO_STARTED_AGENT_WAIT:
                    raise asyncio.TimeoutError()
                if now - last_log > AUTO_STARTED_AGENT_WAIT_LOG_INTERVAL:
                    last_log = now
                    LOGGER.debug(
                        "Waiting for agent with PID %s, waited %d seconds, %d/%d instances up",
                        proc.pid,
                        now - started,
                        len(actual_agents_in_up_state),
                        len(expected_agents_in_up_state),
                    )
                new_actual_agents_in_up_state = {
                    agent_name
                    for agent_name in expected_agents_in_up_state
                    if (env.id, agent_name) in self._agent_manager.tid_endpoint_to_session
                }
                if len(new_actual_agents_in_up_state) > len(actual_agents_in_up_state):
                    # Reset timeout timer because a new instance became active
                    last_new_agent_seen = now
                actual_agents_in_up_state = new_actual_agents_in_up_state

        LOGGER.debug("Started new agent with PID %s", proc.pid)
        # Wait for all agents to start
        try:
            await _wait_until_agent_instances_are_active()
            LOGGER.debug("Agent with PID %s is up", proc.pid)
        except asyncio.TimeoutError:
            LOGGER.warning("Timeout: agent with PID %s took too long to start", proc.pid)
        return True

    async def _make_agent_config(
        self,
        env: data.Environment,
        agent_names: List[str],
        agent_map: Dict[str, str],
        *,
        connection: Optional[asyncpg.connection.Connection],
    ) -> str:
        """
        Generate the config file for the process that hosts the autostarted agents

        :param env: The environment for which to autostart agents
        :param agent_names: The names of the agents
        :param agent_map: The agent mapping to use
        :return: A string that contains the config file content.
        """
        environment_id = str(env.id)
        port: int = opt.get_bind_port()

        privatestatedir: str = os.path.join(Config.get("config", "state-dir", "/var/lib/inmanta"), environment_id)

        agent_deploy_splay: int = cast(int, await env.get(data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME, connection=connection))
        agent_deploy_interval: int = cast(int, await env.get(data.AUTOSTART_AGENT_DEPLOY_INTERVAL, connection=connection))

        agent_repair_splay: int = cast(int, await env.get(data.AUTOSTART_AGENT_REPAIR_SPLAY_TIME, connection=connection))
        agent_repair_interval: int = cast(int, await env.get(data.AUTOSTART_AGENT_REPAIR_INTERVAL, connection=connection))

        # The internal agent always needs to have a session. Otherwise the agentmap update trigger doesn't work
        if "internal" not in agent_names:
            agent_names.append("internal")

        # generate config file
        config = """[config]
state-dir=%(statedir)s

use_autostart_agent_map=true
agent-names = %(agents)s
environment=%(env_id)s

agent-deploy-splay-time=%(agent_deploy_splay)d
agent-deploy-interval=%(agent_deploy_interval)d
agent-repair-splay-time=%(agent_repair_splay)d
agent-repair-interval=%(agent_repair_interval)d

[agent_rest_transport]
port=%(port)s
host=%(serveradress)s
""" % {
            "agents": ",".join(agent_names),
            "env_id": environment_id,
            "port": port,
            "statedir": privatestatedir,
            "agent_deploy_splay": agent_deploy_splay,
            "agent_deploy_interval": agent_deploy_interval,
            "agent_repair_splay": agent_repair_splay,
            "agent_repair_interval": agent_repair_interval,
            "serveradress": server_config.server_address.get(),
        }

        if server_config.server_enable_auth.get():
            token = encode_token(["agent"], environment_id)
            config += """
token=%s
    """ % (
                token
            )

        ssl_cert: Optional[str] = server_config.server_ssl_key.get()
        ssl_ca: Optional[str] = server_config.server_ssl_ca_cert.get()

        if ssl_ca is not None and ssl_cert is not None:
            # override CA
            config += """
ssl=True
ssl_ca_cert_file=%s
    """ % (
                ssl_ca
            )
        elif ssl_cert is not None:
            # system CA
            config += """
ssl=True
    """

        return config

    async def _fork_inmanta(
        self, args: List[str], outfile: Optional[str], errfile: Optional[str], cwd: Optional[str] = None
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

            return await asyncio.create_subprocess_exec(
                sys.executable, *full_args, cwd=cwd, env=os.environ.copy(), stdout=outhandle, stderr=errhandle
            )
        finally:
            if outhandle is not None:
                outhandle.close()
            if errhandle is not None:
                errhandle.close()

    async def notify_agent_about_agent_map_update(self, env: data.Environment) -> None:
        agent_client = self._agent_manager.get_agent_client(tid=env.id, endpoint="internal", live_agent_only=False)
        if agent_client:
            new_agent_map = await env.get(data.AUTOSTART_AGENT_MAP)
            self.add_background_task(agent_client.update_agent_map(new_agent_map))
        else:
            LOGGER.warning("Could not send update_agent_map() trigger for environment %s. Internal agent is down.", env.id)

    async def _wait_for_proc_bounded(
        self, procs: Iterable[subprocess.Process], timeout: float = const.SHUTDOWN_GRACE_HARD
    ) -> None:
        try:
            unfinished_processes = [proc for proc in procs if proc.returncode is None]
            await asyncio.wait_for(asyncio.gather(*[asyncio.shield(proc.wait()) for proc in unfinished_processes]), timeout)
        except asyncio.TimeoutError:
            LOGGER.warning("Agent processes did not close in time (%s)", procs)
