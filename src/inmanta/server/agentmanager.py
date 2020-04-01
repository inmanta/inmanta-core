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
from asyncio import subprocess
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple
from uuid import UUID

from inmanta import const, data
from inmanta.config import Config
from inmanta.protocol import encode_token, methods, methods_v2
from inmanta.protocol.exceptions import NotFound, ShutdownInProgress
from inmanta.resources import Id
from inmanta.server import SLICE_AGENT_MANAGER, SLICE_DATABASE, SLICE_SERVER, SLICE_SESSION_MANAGER, SLICE_TRANSPORT
from inmanta.server import config as opt
from inmanta.server import protocol
from inmanta.server.protocol import ReturnClient, ServerSlice, SessionListener, SessionManager
from inmanta.server.server import Server
from inmanta.types import Apireturn, ArgumentTypes
from inmanta.util import retry_limited

from . import config as server_config

LOGGER = logging.getLogger(__name__)


agent_lock = asyncio.Lock()


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


async def wait_for_proc_bounded(procs: Iterable[subprocess.Process], timeout: float = const.SHUTDOWN_GRACE_HARD) -> None:
    try:
        unfinished_processes = [proc for proc in procs if proc.returncode is None]
        await asyncio.wait_for(asyncio.gather(*[asyncio.shield(proc.wait()) for proc in unfinished_processes]), timeout)
    except asyncio.TimeoutError:
        LOGGER.warning("Agent processes did not close in time (%s)", procs)


class AgentManager(ServerSlice, SessionListener):
    """ This class contains all server functionality related to the management of agents
    """

    def __init__(self, closesessionsonstart: bool = True, fact_back_off: int = None) -> None:
        super(AgentManager, self).__init__(SLICE_AGENT_MANAGER)

        if fact_back_off is None:
            fact_back_off = opt.server_fact_resource_block.get()

        self._agent_procs: Dict[UUID, subprocess.Process] = {}  # env uuid -> subprocess.Process

        # back-off timer for fact requests
        self._fact_resource_block: int = fact_back_off
        # per resource time of last fact request
        self._fact_resource_block_set: Dict[str, float] = {}

        # session lock
        self.session_lock = asyncio.Lock()
        # all sessions
        self.sessions: Dict[UUID, protocol.Session] = {}
        # live sessions
        self.tid_endpoint_to_session: Dict[Tuple[UUID, str], protocol.Session] = {}

        self.closesessionsonstart: bool = closesessionsonstart

    async def get_status(self) -> Dict[str, ArgumentTypes]:
        return {
            "sessions": len(self.sessions),
            "processes": len(self._agent_procs),
            "resource_facts": len(self._fact_resource_block_set),
        }

    def get_dependencies(self) -> List[str]:
        return [SLICE_SERVER, SLICE_DATABASE, SLICE_SESSION_MANAGER]

    def get_depended_by(self) -> List[str]:
        return [SLICE_TRANSPORT]

    async def prestart(self, server: protocol.Server) -> None:
        await ServerSlice.prestart(self, server)

        preserver = server.get_slice(SLICE_SERVER)
        assert isinstance(preserver, Server)
        self._server: Server = preserver
        self._server_storage: Dict[str, str] = self._server._server_storage

        presession = server.get_slice(SLICE_SESSION_MANAGER)
        assert isinstance(presession, SessionManager)
        presession.add_listener(self)

    async def new_session(self, session: protocol.Session) -> None:
        await self._register_session(session, datetime.now())

    def expire(self, session: protocol.Session, timeout: float) -> None:
        self.add_background_task(self._expire_session(session, datetime.now()))

    def seen(self, session: protocol.Session, endpoint_names: List[str]) -> None:
        if set(session.endpoint_names) != set(endpoint_names):
            LOGGER.warning(
                "Agent endpoint set changed, this should not occur, update ignored (was %s is %s)"
                % (set(session.endpoint_names), set(endpoint_names))
            )
        # start async, let it run free
        self.add_background_task(self._flush_agent_presence(session, datetime.now()))

    # From server
    def get_agent_client(self, tid: uuid.UUID, endpoint: str) -> Optional[ReturnClient]:
        if isinstance(tid, str):
            tid = uuid.UUID(tid)
        key = (tid, endpoint)
        session = self.tid_endpoint_to_session.get(key, None)
        if session is not None:
            return session.get_client()
        return None

    async def start(self) -> None:
        await super().start()
        if self.closesessionsonstart:
            await self._expire_all_sessions_in_db()
        self.add_background_task(self._start_agents())

    async def prestop(self) -> None:
        await super().prestop()
        await self._terminate_agents()

    async def stop(self) -> None:
        await super().stop()

    @protocol.handle(methods_v2.pause_agent, env="tid")
    async def pause_agent(self, env: data.Environment, name: str, paused: bool) -> None:
        if paused:
            await self._pause_agent(env, name)
        else:
            await self._unpause_agent(env, name)

    async def _pause_agent(self, env: data.Environment, endpoint: str) -> None:
        key = (env.id, endpoint)
        async with self.session_lock:
            await data.Agent.pause(env=env.id, endpoint=endpoint, paused=True)
            live_session = self.tid_endpoint_to_session.get(key)
            if live_session is not None:
                del self.tid_endpoint_to_session[key]
                await live_session.get_client().set_state(endpoint, False)

    async def _unpause_agent(self, env: data.Environment, endpoint: str) -> None:
        key = (env.id, endpoint)
        async with self.session_lock:
            await data.Agent.pause(env=env.id, endpoint=endpoint, paused=False)
            live_session = self.tid_endpoint_to_session.get(key)
            if live_session:
                await live_session.get_client().set_state(endpoint, True)
            else:
                # TODO: Replace with find session for
                # TODO: Replace with more efficient datastructure
                for session in self.sessions.values():
                    if session.tid == env.id and endpoint in session.endpoint_names:
                        self.tid_endpoint_to_session[key] = session
                        await session.get_client().set_state(endpoint, True)

    # Agent Management
    async def ensure_agent_registered(self, env: data.Environment, nodename: str) -> data.Agent:
        """
            Make sure that an agent has been created in the database
        """
        async with self.session_lock:
            agent = await data.Agent.get(env.id, nodename)
            if agent is not None:
                return agent
            else:
                return await self._create_default_agent(env, nodename)

    async def _create_default_agent(self, env: data.Environment, nodename: str) -> data.Agent:
        """
            This method creates a new agent (agent in the model) in the database.
            If an active agent instance exists for the given agent, it is marked as a the
            primary instance for that agent in the database.

            Note: This method must be called under session lock
        """
        saved = data.Agent(environment=env.id, name=nodename, paused=False)
        await saved.insert()

        key = (env.id, nodename)
        session = self.tid_endpoint_to_session.get(key, None)
        if session is not None:
            await self._log_primary_to_db(env, [(nodename, session)], datetime.now())

        return saved

    async def _register_session(self, session: protocol.Session, now: datetime) -> None:
        """
            This method registers a new session in memory and asynchronously updates the agent
            session log in the database. When the database connection is lost, the get_statuses()
            call fails and the new session will be refused.
        """
        async with self.session_lock:
            tid = session.tid
            sid = session.get_id()

            agent_statuses = await data.Agent.get_statuses(tid, session.endpoint_names)

            self.sessions[sid] = session

            endpoints_with_new_primary: List[Tuple[str, Optional[protocol.Session]]] = []
            for endpoint in session.endpoint_names:
                if (tid, endpoint) not in self.tid_endpoint_to_session and agent_statuses[endpoint] != "paused":
                    LOGGER.debug("set session %s as primary for agent %s in env %s", sid, endpoint, tid)
                    self.tid_endpoint_to_session[(tid, endpoint)] = session
                    self.add_background_task(session.get_client().set_state(endpoint, True))
                    endpoints_with_new_primary.append((endpoint, session))

        self.add_background_task(self._log_session_creation_to_db(tid, endpoints_with_new_primary, session, now))

    async def _log_session_creation_to_db(
        self,
        tid: uuid.UUID,
        endpoints_with_new_primary: List[Tuple[str, Optional[protocol.Session]]],
        session: protocol.Session,
        now: datetime,
    ) -> None:
        """
            Note: This method call is allowed to fail when the database connection is lost.
        """
        sid = session.get_id()
        nodename = session.nodename

        env = await data.Environment.get_by_id(tid)
        if env is None:
            LOGGER.warning("The environment id %s, for agent %s does not exist!", tid, sid)

        proc = await data.AgentProcess.get_one(sid=sid)

        if proc is None:
            proc = data.AgentProcess(hostname=nodename, environment=tid, first_seen=now, last_seen=now, sid=sid)
            await proc.insert()
        else:
            await proc.update_fields(last_seen=now, expired=None)

        # Fix database corruption when database was down
        await data.AgentInstance.expire_all_for_process(tid, proc.sid, now)
        for nh in session.endpoint_names:
            LOGGER.debug("New session for agent %s on %s", nh, nodename)
            await data.AgentInstance(tid=tid, process=proc.sid, name=nh).insert()

        if env is not None:
            await self._log_primary_to_db(env, endpoints_with_new_primary, now)

    def _get_session_for(self, tid: uuid.UUID, endpoint: str) -> Optional[protocol.Session]:
        """
            Return a session that matches the given environment and endpoint.
        """
        for current_session in self.sessions.values():
            if current_session.tid == tid and endpoint in current_session.endpoint_names:
                return current_session
        return None

    async def _expire_session(self, session: protocol.Session, now: datetime) -> None:
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

            LOGGER.debug("expiring session %s", sid)
            del self.sessions[sid]

            endpoints_with_new_primary: List[Tuple[str, Optional[protocol.Session]]] = []
            for endpoint in session.endpoint_names:
                key = (tid, endpoint)
                current_active_session = self.tid_endpoint_to_session.get(key, None)
                if current_active_session is not None and current_active_session == session:

                    new_active_session = self._get_session_for(tid, endpoint)
                    if new_active_session is not None:
                        self.tid_endpoint_to_session[key] = new_active_session
                        self.add_background_task(new_active_session.get_client().set_state(endpoint, True))
                        endpoints_with_new_primary.append((endpoint, new_active_session))
                    else:
                        del self.tid_endpoint_to_session[key]
                        endpoints_with_new_primary.append((endpoint, None))

        self.add_background_task(self._log_session_expiry_to_db(tid, endpoints_with_new_primary, session, now))

    async def _log_session_expiry_to_db(
        self,
        tid: uuid.UUID,
        endpoints_with_new_primary: List[Tuple[str, Optional[protocol.Session]]],
        session: protocol.Session,
        now: datetime,
    ) -> None:
        """
            Note: This method call is allowed to fail when the database connection is lost.
        """
        sid = session.get_id()
        env = await data.Environment.get_by_id(tid)
        if env is None:
            LOGGER.warning("The environment id %s, for agent %s does not exist!", tid, sid)

        aps = await data.AgentProcess.get_by_sid(sid=sid)
        if aps is None:
            LOGGER.info("expiring session on none existant process sid:%s", sid)
        else:
            await aps.update_fields(expired=now)

            instances = await data.AgentInstance.get_list(process=aps.sid)
            for ai in instances:
                await ai.update_fields(expired=now)

        if env is not None:
            await self._log_primary_to_db(env, endpoints_with_new_primary, now)

    async def _get_environment_sessions(self, env_id: uuid.UUID) -> List[protocol.Session]:
        """
            Get a list of all sessions for the given environment id
        """
        sessions = await data.AgentProcess.get_live_by_env(env_id)

        result = []
        for session in sessions:
            live_session = self.sessions.get(session.sid, None)
            if live_session is not None:
                result.append(live_session)
        return result

    async def _flush_agent_presence(self, session: protocol.Session, now: datetime) -> None:
        tid = session.tid
        sid = session.get_id()

        env = await data.Environment.get_by_id(tid)
        if env is None:
            LOGGER.warning("The environment id %s, for agent %s does not exist!", tid, sid)
            return

        aps = await data.AgentProcess.get_by_sid(sid=sid)
        if aps is None:
            LOGGER.warning("No process registered for SID %s", sid)
            return

        await aps.update_fields(last_seen=now)

    async def _log_primary_to_db(
        self, env: data.Environment, endpoints_with_new_primary: List[Tuple[str, Optional[protocol.Session]]], now: datetime
    ) -> None:
        """
            Update the primary agent instance for agents present in the database.

            Note: This method call is allowed to fail when the database connection is lost.

            :param env: The environment of the agent
            :param endpoints_with_new_primary: Contains a tuple (agent-name, session) for each agent that has got a new
                                               primary agent instance. The session in the tuple is the session of the new
                                               primary.
            :param now: Timestamp of this failover
        """
        for (endpoint, session) in endpoints_with_new_primary:
            agent = await data.Agent.get(env.id, endpoint)
            if agent is None:
                continue

            if session is None:
                await agent.update_fields(last_failover=now, primary=None)
            else:
                instances = await data.AgentInstance.active_for(tid=env.id, endpoint=agent.name, process=session.get_id())
                if instances:
                    await agent.update_fields(last_failover=now, primary=instances[0].id)
                else:
                    await agent.update_fields(last_failover=now, primary=None)

    def is_primary(self, env: data.Environment, sid: uuid.UUID, agent: str) -> bool:
        prim = self.tid_endpoint_to_session.get((env.id, agent), None)
        if prim is None:
            return False
        return prim.get_id() == sid

    async def _expire_all_sessions_in_db(self) -> None:
        async with self.session_lock:
            LOGGER.debug("Cleaning server session DB")

            # TODO: do as one query
            procs = await data.AgentProcess.get_live()
            for proc in procs:
                await proc.update_fields(expired=datetime.now())

            ais = await data.AgentInstance.active()
            for ai in ais:
                await ai.update_fields(expired=datetime.now())

            agents = await data.Agent.get_list()
            for agent in agents:
                await agent.update_fields(primary=None)

    # utils
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

            # TODO: perhaps show in dashboard?
            return await asyncio.create_subprocess_exec(
                sys.executable, *full_args, cwd=cwd, env=os.environ.copy(), stdout=outhandle, stderr=errhandle
            )
        finally:
            if outhandle is not None:
                outhandle.close()
            if errhandle is not None:
                errhandle.close()

    # External APIS
    @protocol.handle(methods.get_agent_process, agent_sid="id")
    async def get_agent_process(self, agent_sid: uuid.UUID) -> Apireturn:
        return await self.get_agent_process_report(agent_sid)

    @protocol.handle(methods.trigger_agent, agent_id="id", env="tid")
    async def trigger_agent(self, env: UUID, agent_id: str) -> Apireturn:
        raise NotImplementedError()

    @protocol.handle(methods.list_agent_processes)
    async def list_agent_processes(self, environment: Optional[UUID], expired: bool) -> Apireturn:
        if environment is not None:
            env = await data.Environment.get_by_id(environment)
            if env is None:
                return 404, {"message": "The given environment id does not exist!"}

        tid = environment
        if tid is not None:
            if expired:
                aps = await data.AgentProcess.get_by_env(tid)
            else:
                aps = await data.AgentProcess.get_live_by_env(tid)
        else:
            if expired:
                aps = await data.AgentProcess.get_list()
            else:
                aps = await data.AgentProcess.get_live()

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

    @protocol.handle(methods.list_agents, env="tid")
    async def list_agents(self, env: Optional[data.Environment]) -> Apireturn:
        if env is not None:
            tid = env.id
            ags = await data.Agent.get_list(environment=tid)
        else:
            ags = await data.Agent.get_list()

        return 200, {"agents": [a.to_dict() for a in ags], "servertime": datetime.now().isoformat(timespec="microseconds")}

    @protocol.handle(methods.get_state, env="tid")
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

    # Start/stop agents
    async def _ensure_agents(self, env: data.Environment, agents: List[str], restart: bool = False) -> bool:
        """
            Ensure that all agents defined in the current environment (model) and that should be autostarted, are started.

            :param env: The environment to start the agents for
            :param agents: A list of agent names that possibly should be started in this environment.
            :param restart: Restart all agents even if the list of agents is up to date.
        """
        if self._stopping:
            raise ShutdownInProgress()

        agent_map: Dict[str, str]
        agent_map = await env.get(data.AUTOSTART_AGENT_MAP)
        agents = [agent for agent in agents if agent in agent_map]
        needsstart = restart
        if len(agents) == 0:
            return False

        async with agent_lock:
            LOGGER.info("%s matches agents managed by server, ensuring it is started.", agents)
            for agent in agents:
                async with self.session_lock:
                    myagent = self.get_agent_client(env.id, agent)
                    if myagent is None:
                        needsstart = True

            if needsstart:
                res = await self.__do_start_agent(agents, env)
                return res
        return False

    async def __do_start_agent(self, agents: List[str], env: data.Environment) -> bool:
        """
            Start an agent process for the given agents in the given environment
        """
        agent_map: Dict[str, str]
        agent_map = await env.get(data.AUTOSTART_AGENT_MAP)
        config: str
        config = await self._make_agent_config(env, agents, agent_map)

        config_dir = os.path.join(self._server_storage["agents"], str(env.id))
        if not os.path.exists(config_dir):
            os.mkdir(config_dir)

        config_path = os.path.join(config_dir, "agent.cfg")
        with open(config_path, "w+", encoding="utf-8") as fd:
            fd.write(config)

        out: str = os.path.join(self._server_storage["logs"], "agent-%s.out" % env.id)
        err: str = os.path.join(self._server_storage["logs"], "agent-%s.err" % env.id)

        agent_log = os.path.join(self._server_storage["logs"], "agent-%s.log" % env.id)
        proc = await self._fork_inmanta(
            ["-vvvv", "--timed-logs", "--config", config_path, "--log-file", agent_log, "agent"], out, err
        )

        if env.id in self._agent_procs and self._agent_procs[env.id] is not None:
            # If the return code is not None the process is already terminated
            if self._agent_procs[env.id].returncode is None:
                LOGGER.debug("Terminating old agent with PID %s", self._agent_procs[env.id].pid)
                self._agent_procs[env.id].terminate()
                await wait_for_proc_bounded([self._agent_procs[env.id]])

        self._agent_procs[env.id] = proc

        # Wait for an agent to start
        await retry_limited(lambda: self.get_agent_client(env.id, agents[0]) is not None, 5)
        # await sleep(2)

        LOGGER.debug("Started new agent with PID %s", proc.pid)
        return True

    async def _make_agent_config(self, env: data.Environment, agent_names: List[str], agent_map: Dict[str, str]) -> str:
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

        agent_deploy_splay: int = await env.get(data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME)
        agent_deploy_interval: int = await env.get(data.AUTOSTART_AGENT_DEPLOY_INTERVAL)

        agent_repair_splay: int = await env.get(data.AUTOSTART_AGENT_REPAIR_SPLAY_TIME)
        agent_repair_interval: int = await env.get(data.AUTOSTART_AGENT_REPAIR_INTERVAL)

        # generate config file
        config = """[config]
state-dir=%(statedir)s

agent-names = %(agents)s
environment=%(env_id)s
agent-map=%(agent_map)s

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
            "agent_map": ",".join(["%s=%s" % (k, v) for (k, v) in agent_map.items()]),
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

    # Parameters

    async def request_parameter(self, env_id: uuid.UUID, resource_id: str) -> Apireturn:
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
                await self._ensure_agents(env, agents)

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

    async def _start_agents(self) -> None:
        """
            Ensure that autostarted agents of each environment are started when AUTOSTART_ON_START is true. This method
            is called on server start.
        """
        environments = await data.Environment.get_list()
        for env in environments:
            agents = await data.Agent.get_list(environment=env.id)
            autostart = await env.get(data.AUTOSTART_ON_START)
            if autostart:
                agent_list = [a.name for a in agents]
                await self._ensure_agents(env, agent_list)

    async def restart_agents(self, env: data.Environment) -> None:
        agents = await data.Agent.get_list(environment=env.id)
        autostart = await env.get(data.AUTOSTART_ON_START)
        if autostart:
            agent_list = [a.name for a in agents]
            await self._ensure_agents(env, agent_list, True)

    async def stop_agents(self, env: data.Environment) -> None:
        """
            Stop all agents for this environment and close sessions
        """
        LOGGER.debug("Stopping all autostarted agents for env %s", env.id)
        if env.id in self._agent_procs:
            subproc = self._agent_procs[env.id]
            subproc.terminate()
            await wait_for_proc_bounded([subproc])
            del self._agent_procs[env.id]

        LOGGER.debug("Expiring all sessions for %s", env.id)
        sessions: List[protocol.Session]
        sessions = await self._get_environment_sessions(env.id)
        for session in sessions:
            session.expire(0)
            session.abort()

    async def _terminate_agents(self) -> None:
        LOGGER.debug("Stopping all autostarted agents")
        for proc in self._agent_procs.values():
            proc.terminate()
        await wait_for_proc_bounded(self._agent_procs.values())

        LOGGER.debug("Expiring all sessions")
        for session in self.sessions.values():
            session.expire(0)
            session.abort()
