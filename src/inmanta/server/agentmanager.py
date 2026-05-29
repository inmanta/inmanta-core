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
import configparser
import logging
import os
import shutil
import sys
import time
import uuid
from asyncio import subprocess
from collections.abc import Iterable, Mapping, Sequence, Set
from dataclasses import dataclass
from datetime import datetime
from functools import reduce
from typing import Any, Optional, Union, assert_never, cast

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
from inmanta.const import AgentAction, AgentStatus, AllAgentAction
from inmanta.data import APILIMIT, Environment, InvalidSort, model
from inmanta.data.model import DataBaseReport
from inmanta.protocol import common, encode_token, endpoints, handle, methods, methods_v2, websocket
from inmanta.protocol.exceptions import BadRequest, Conflict, Forbidden, NotFound, ShutdownInProgress
from inmanta.server import (
    SLICE_AGENT_MANAGER,
    SLICE_AUTOSTARTED_AGENT_MANAGER,
    SLICE_DATABASE,
    SLICE_ENVIRONMENT,
    SLICE_SERVER,
    SLICE_TRANSPORT,
)
from inmanta.server import config as opt
from inmanta.server import protocol
from inmanta.server.protocol import ServerSlice
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
|  ENVIRONMENT  |   +---->  AGENT   |
|               |   |    |  PROCESS |
+------+--------+   |    +----------+
       |            |
       |            |
+------v--------+   |
|               |   |
|  AGENT        |   |
|               |   |
+------+--------+   |
       |            |
       |            |
+------v--------+   |
|               |   |
|  SESSION      +---+
|  (WebSocket)  |
+---------------+

Each environment has one or more logical agents. Each agent has at most one
active session (WebSocket connection) to the agent process at any time.
"""


# Internal tuning constants

AUTO_STARTED_AGENT_WAIT = 5
# How long (in seconds) do we wait for autostarted agents. The wait time is reset any time a new instance comes online
AUTO_STARTED_AGENT_WAIT_LOG_INTERVAL = 1
# When waiting for an autostarted agent, how long (in seconds) do we wait before we log the wait status


class AgentManager(ServerSlice, websocket.SessionListener):
    """
    This class contains all server functionality related to the management of agents.

    Each logical agent is identified by a name within an environment. An agent connects to the server
    via a WebSocket session. At most one active session exists per agent at any time; when an agent
    reconnects, the old session is evicted and replaced.

    A subset of agents are autostarted by the server, managed by :py:class:`AutostartedAgentManager`.
    """

    def __init__(self, closesessionsonstart: bool = True, fact_back_off: Optional[int] = None) -> None:
        super().__init__(SLICE_AGENT_MANAGER)

        if fact_back_off is None:
            fact_back_off = opt.server_fact_resource_block.get()

        # back-off timer for fact requests
        self._fact_resource_block: int = fact_back_off
        # per resource time of last fact request
        self._fact_resource_block_set: dict[str, float] = {}

        # session per environment
        self.scheduler_for_env: dict[uuid.UUID, websocket.Session] = {}
        # all sessions per ID
        self.sessions: dict[uuid.UUID, websocket.Session] = {}

        # session lock
        self.session_lock = asyncio.Lock()

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

        async def get_report(env: uuid.UUID, session: websocket.Session) -> tuple[uuid.UUID, DataBaseReport]:
            result = await asyncio.wait_for(session.get_client().get_db_status(), deadline)
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
        return [SLICE_DATABASE]

    def get_depended_by(self) -> list[str]:
        return [SLICE_TRANSPORT]

    async def prestart(self, server: protocol.Server) -> None:
        await ServerSlice.prestart(self, server)
        autostarted_agent_manager = server.get_slice(SLICE_AUTOSTARTED_AGENT_MANAGER)
        assert isinstance(autostarted_agent_manager, AutostartedAgentManager)
        self._autostarted_agent_manager = autostarted_agent_manager
        server._transport.add_session_listener(self)

    async def start(self) -> None:
        await super().start()

        if self.closesessionsonstart:
            await self._expire_all_sessions_in_db()

        # Schedule cleanup of schedulersession table
        agent_process_purge_interval = opt.agent_process_purge_interval.get()
        if agent_process_purge_interval > 0:
            self.schedule(
                self._purge_agent_processes, interval=agent_process_purge_interval, initial_delay=0, cancel_on_stop=False
            )

    async def prestop(self) -> None:
        await super().prestop()

    async def stop(self) -> None:
        await super().stop()

    def get_all_schedulers(self) -> list[tuple[uuid.UUID, websocket.Session]]:
        # Linear scan, but every item should be a hit
        return list(self.scheduler_for_env.items())

    def is_scheduler_running_for(self, env: uuid.UUID) -> bool:
        return env in self.scheduler_for_env

    async def halt_agents(self, env: data.Environment, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        """
        Halts all agents for an environment. Persists prior paused state. Also halts the scheduler "agent".

        The DB operations are done using the provided connection (which may be in a transaction).
        The RPC notifications to the agent are done separately to avoid deadlocks: the agent's
        RPC handler may need to query the DB, which would deadlock if the caller's transaction
        holds locks on the same rows.
        """
        await data.Agent.persist_on_halt(env.id, connection=connection)
        # DB operations (safe inside a transaction)
        await self._update_paused_status_in_db(env, new_paused_status=True, connection=connection)
        await self._update_paused_status_in_db(
            env, new_paused_status=True, endpoint=const.AGENT_SCHEDULER_ID, connection=connection
        )

    async def halt_agents_notify(self, env: data.Environment) -> None:
        """
        Send RPC notifications to the agent after halt DB operations have been committed.
        Must be called outside any DB transaction.
        """
        await self._notify_agent_state_change(env, new_paused_status=True)
        await self._notify_agent_state_change(env, new_paused_status=True, endpoint=const.AGENT_SCHEDULER_ID)

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
        agent_client = self.get_agent_client(tid=env.id)
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
        await self._update_paused_status_in_db(env, new_paused_status, endpoint, connection=connection)
        await self._notify_agent_state_change(env, new_paused_status, endpoint)

    async def _update_paused_status_in_db(
        self,
        env: data.Environment,
        new_paused_status: bool,
        endpoint: Optional[str] = None,
        *,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> None:
        """
        Update the paused status of an agent in the database.
        """
        # We need this lock otherwise, we would have transaction conflict in DB
        async with self.session_lock:
            await data.Agent.pause(env=env.id, endpoint=endpoint, paused=new_paused_status, connection=connection)

    async def _notify_agent_state_change(
        self,
        env: data.Environment,
        new_paused_status: bool,
        endpoint: Optional[str] = None,
    ) -> None:
        """
        Notify the agent of a state change via RPC. Must be called outside any DB transaction to avoid deadlocks.
        """
        live_session = self.scheduler_for_env.get(env.id)
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

    # Notify from session listener
    async def session_opened(self, session: websocket.Session) -> None:
        """
        Register a new session synchronously so that ``scheduler_for_env`` is populated before
        the server completes its ``register_session`` call and replies ``SESSION_OPENED`` to
        the client. The agent's ``on_reconnect`` issues ``get_state`` immediately after that
        reply; if registration were deferred to a background queue, the ``get_state`` could
        race ahead and see ``enabled=False``, leaving the scheduler idle.
        """
        await self._register_session(session, datetime.now().astimezone())

    # Notify from session listener
    async def session_closed(self, session: websocket.Session) -> None:
        """Expire a session synchronously; see :meth:`session_opened` for the rationale."""
        await self._expire_session(session, datetime.now().astimezone())

    # Session registration
    async def _register_session(self, session: websocket.Session, now: datetime) -> None:
        """
        This method registers a new session in memory and asynchronously updates the agent
        session log in the database. When the database connection is lost, the get_statuses()
        call fails and the new session will be refused.
        """
        if not self.is_running() or self.is_stopping():
            return
        LOGGER.debug("New session %s for environment %s", session.name, session.environment)
        async with self.session_lock:
            if session.environment in self.scheduler_for_env or session.id in self.sessions:
                raise Exception(
                    f"Duplicate session registration: session {session.id} for environment {session.environment} "
                    f"(environment registered: {session.environment in self.scheduler_for_env}, "
                    f"session registered: {session.id in self.sessions})"
                )
            self.scheduler_for_env[session.environment] = session
            self.sessions[session.id] = session

        self.add_background_task(self._log_session_creation_to_db(session, now))

    async def _log_session_creation_to_db(
        self,
        session: websocket.Session,
        now: datetime,
    ) -> None:
        """
        Note: This method call is allowed to fail when the database connection is lost.
        """
        await data.SchedulerSession.register(session.environment, session.hostname, session.id, now)

    # Session expiry
    async def _expire_session(self, session: websocket.Session, now: datetime) -> None:
        """
        This method expires the given session and update the in-memory session state.
        The in-database session log is updated asynchronously. These database updates
        are allowed to fail when the database connection is lost.

        During shutdown, this method returns early — in-memory state is discarded and
        DB cleanup happens at next startup via _expire_all_sessions_in_db.
        """
        if not self.is_running() or self.is_stopping():
            return
        async with self.session_lock:
            self.scheduler_for_env.pop(session.environment, None)
            self.sessions.pop(session.id, None)

        self.add_background_task(self._log_session_expiry_to_db(session, now))

    async def _log_session_expiry_to_db(
        self,
        session: websocket.Session,
        now: datetime,
    ) -> None:
        """
        Note: This method call is allowed to fail when the database connection is lost.
        """
        async with data.SchedulerSession.get_connection() as connection:
            await data.SchedulerSession.expire_process(session.id, now, connection)

    async def _expire_all_sessions_in_db(self) -> None:
        async with self.session_lock:
            LOGGER.debug("Cleaning server session DB")
            async with data.SchedulerSession.get_connection() as connection:
                async with connection.transaction():
                    await data.SchedulerSession.expire_all(now=datetime.now().astimezone(), connection=connection)

    async def _purge_agent_processes(self) -> None:
        agent_processes_to_keep = opt.agent_processes_to_keep.get()
        await data.SchedulerSession.cleanup(nr_expired_records_to_keep=agent_processes_to_keep)

    def get_session_for(self, tid: uuid.UUID) -> Optional[websocket.Session]:
        """
        Return a session that matches the given environment and endpoint.
        This method also returns session to paused or non-live agents.
        """
        session = self.scheduler_for_env.get(tid)
        return session

    def get_agent_client(self, tid: uuid.UUID) -> Optional[endpoints.Client]:
        session = self.scheduler_for_env.get(tid)
        if session is None:
            return None
        return session.get_client()

    async def expire_sessions_for_environment(self, env_id: uuid.UUID) -> None:
        """
        Close the scheduler session for the given environment, if any.

        Important: the actual ``close_connection()`` call is performed *outside* the
        ``session_lock``. ``close_connection`` cascades through ``on_close_session`` ->
        ``notify_close_session`` -> ``session_closed`` -> ``_expire_session``, which itself
        acquires ``session_lock``; holding the lock across the call would deadlock.
        """
        async with self.session_lock:
            session_to_expire = self.scheduler_for_env.get(env_id)
        if session_to_expire is not None:
            await session_to_expire.close_connection()

    async def is_scheduler_active(self, tid: uuid.UUID) -> bool:
        """
        Return true iff all the given agents are in the up or the paused state.
        """
        return tid in self.scheduler_for_env

    async def expire_all_sessions(self) -> None:
        # See expire_sessions_for_environment for why close_connection runs outside the lock.
        async with self.session_lock:
            sessions_snapshot = list(self.sessions.values())
        await asyncio.gather(*[s.close_connection() for s in sessions_snapshot])

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

        Note: This method must be called under session lock
        """
        saved = data.Agent(environment=env.id, name=nodename, paused=False)
        await saved.insert(connection=connection)

        return saved

    # External APIS
    @handle(methods.get_agent_process, agent_sid="id")
    async def get_agent_process(self, agent_sid: uuid.UUID) -> Apireturn:
        return await self.get_agent_process_report(agent_sid)

    @handle(methods.list_agent_processes)
    async def list_agent_processes(
        self,
        environment: Optional[uuid.UUID],
        expired: bool,
        start: Optional[uuid.UUID] = None,
        end: Optional[uuid.UUID] = None,
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

        aps = await data.SchedulerSession.get_list_paged(
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
            agent_dict["endpoints"] = []  # backward compat
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
            native["state"] = agent.status
            return native

        return 200, {
            "agents": [mangle_format(a) for a in new_agent_endpoint._response],
            "servertime": datetime.now().astimezone(),
        }

    @handle(methods.get_state, env="tid")
    async def get_state(self, env: data.Environment, agent: str) -> dict[str, bool]:
        tid: uuid.UUID = env.id
        if isinstance(tid, str):
            tid = uuid.UUID(tid)
        session = self.scheduler_for_env.get(tid)
        if session is not None:
            return {"enabled": True}
        return {"enabled": False}

    async def get_agent_process_report(self, agent_sid: uuid.UUID) -> ReturnTupple:
        ap = await data.SchedulerSession.get_one(sid=agent_sid)
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
                client = self.get_agent_client(env_id)
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
    ) -> common.ReturnValue[Sequence[model.Agent]]:
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
        agent_process = await data.SchedulerSession.get_one(environment=env.id, sid=id)
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
        self._agent_procs: dict[uuid.UUID, ProcessDetails] = {}  # env uuid -> ProcessDetails
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

            LOGGER.debug("Expiring session for %s", env.id)
            await self._agent_manager.expire_sessions_for_environment(env.id)

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
        await self._agent_manager.expire_sessions_for_environment(env.id)

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

        async with data.Agent.get_connection(connection) as connection:
            async with self.agent_lock:
                # silently ignore requests if this environment is halted
                refreshed_env: Optional[data.Environment] = await data.Environment.get_by_id(env, connection=connection)
                if refreshed_env is None:
                    raise inmanta.exceptions.EnvironmentNotFound(f"Can't ensure scheduler: environment {env} does not exist")
                if refreshed_env.halted:
                    return False

                if await self._agent_manager.is_scheduler_active(env):
                    # do not start a new agent process if the scheduler is already active.
                    return False

                start_new_process: bool
                if env not in self._agent_procs or not self._agent_procs[env].is_running():
                    LOGGER.info("Ensuring scheduler is started for environment %s.", env)
                    start_new_process = True
                elif restart:
                    LOGGER.info(
                        "Forcing scheduler restart for environment %s: stopping process with PID %s.",
                        env,
                        self._agent_procs[env].process,
                    )
                    await self._stop_scheduler(refreshed_env)
                    start_new_process = True
                else:
                    start_new_process = False

                if start_new_process:
                    self._agent_procs[env] = await self.__do_start_agent(refreshed_env)

                # Wait for the scheduler to come up
                try:
                    await self._wait_for_agents(refreshed_env, {const.AGENT_SCHEDULER_ID}, connection=connection)
                except asyncio.TimeoutError:
                    LOGGER.warning("Scheduler did not become active before the timeout expired")
                return start_new_process

    async def __do_start_agent(self, env: data.Environment) -> ProcessDetails:
        """
        Start an autostarted agent process for the given environment. Should only be called if none is running yet.

        :return: A ProcessDetails object consisting of the agent process, the stdout log file and the stderr log file.
        """
        assert not assert_no_start_scheduler

        config_options: str = await self._make_agent_config(env)

        root_dir: str = self._server_storage["server"]
        config_dir = os.path.join(root_dir, str(env.id))

        os.makedirs(config_dir, exist_ok=True)

        # TODO: clean up, move to config module
        parser = global_config.LenientConfigParser(interpolation=configparser.Interpolation())
        section_dict: dict[str, dict[str, str]] = {}
        for option, value in config_options.items():
            if value is not None:
                section_dict.setdefault(option.section, {})[option.name] = str(value)
        parser.read_dict(section_dict)

        config_path = os.path.join(config_dir, "scheduler.cfg")
        with open(config_path, "w+", encoding="utf-8") as fd:
            parser.write(fd)

        out: str = os.path.join(self._server_storage["logs"], "agent-%s.out" % env.id)
        err: str = os.path.join(self._server_storage["logs"], "agent-%s.err" % env.id)

        env = os.environ.copy()
        # TODO: clean up
        for opt in config_options.keys():
            env.pop(opt.get_environment_variable(), None)
        # TODO: does this belong here or in fork_inmanta?
        env.update(tracing.get_context())

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
            env=env,
        )

        LOGGER.debug("Started new agent with PID %s", proc.pid)
        return ProcessDetails(process=proc, path_stdout=out, path_stderr=err)

    async def _make_agent_config(
        self,
        env: data.Environment,
    ) -> dict[inmanta.config.Option[object], object | None]:
        # TODO: return type. Also mention the None semantics
        """
        Generate the config file for the process that hosts the autostarted agents

        :param env: The environment for which to autostart agents
        :return: A string that contains the config file content.
        """
        environment_id: str = str(env.id)
        port: int = opt.server_bind_port.get()

        privatestatedir: str = self._get_state_dir_for_agent_in_env(env.id)

        agent_config_overrides: dict[inmanta.config.Option[object], object | None] = {
            # global config overrides
            global_config.state_dir: privatestatedir,
            # TODO: redundant?
            global_config.log_dir: global_config.log_dir.get(),

            # scheduler config
            agent_cfg.environment: environment_id,
            # TODO: 2 redundant?
            agent_cfg.agent_executor_cap: agent_cfg.agent_executor_cap.get(),
            agent_cfg.agent_executor_retention_time: agent_cfg.agent_executor_retention_time.get(),

            # agent transport
            agent_cfg.agent_transport.host: opt.internal_server_address.get(),
            agent_cfg.agent_transport.port: port,
            agent_cfg.agent_transport.ssl: server_config.server_ssl_key.get() is not None,
            agent_cfg.agent_transport.ssl_ca_cert_file: server_config.server_ssl_ca_cert.get(),
            agent_cfg.agent_transport.token: encode_token(["agent"], environment_id) if server_config.server_enable_auth.get() else None,
        }
        # TODO: add a comment: passthrough just in case until the follow-up ticket is fixed, though server config is read by agent anyway
        agent_config_passthrough: dict[inmanta.config.Option[object], object | None] = {
            option: option.get()
            for option in [
                opt.db_wait_time,
                opt.db_host,
                opt.db_port,
                opt.db_name,
                opt.db_username,
                opt.db_password,
                agent_cfg.scheduler_db_connection_pool_min_size,
                agent_cfg.scheduler_db_connection_pool_max_size,
                agent_cfg.scheduler_db_connection_timeout,
                opt.influxdb_host,
                opt.influxdb_port,
                opt.influxdb_name,
                opt.influxdb_username,
                opt.influxdb_password,
                opt.influxdb_interval,
                opt.influxdb_tags,
                scheduler_log_config,
            ]
        }

        return agent_config_overrides | agent_config_passthrough

    async def _fork_inmanta(
        self, args: list[str], outfile: Optional[str], errfile: Optional[str], cwd: Optional[str] = None, *, env: Mapping[str, object] | None = None
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
                    (session := self._agent_manager.scheduler_for_env.get(env.id)) is not None
                    # make sure to check for closure because sessions are unregistered from the agent manager asynchronously
                    and session.active
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
        agent_client = self._agent_manager.get_agent_client(tid=env.id)
        if agent_client:
            self.add_background_task(agent_client.notify_timer_update(env.id))


# For testing only
# Assert the scheduler will not be started (i.e. agent mock setup is correct)
assert_no_start_scheduler = False
# Ensure the scheduler is not started
no_start_scheduler = False
