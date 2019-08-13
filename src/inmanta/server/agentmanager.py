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
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from tornado import locks, process

from inmanta import data
from inmanta.config import Config
from inmanta.protocol import encode_token, methods
from inmanta.protocol.exceptions import ShutdownInProgress
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


agent_lock = locks.Lock()


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


async def wait_for_proc_bounded(procs: List[process.Subprocess], timeout: float = 1.0) -> None:
    try:
        await asyncio.wait_for(
            asyncio.gather(*[asyncio.shield(proc.wait_for_exit(raise_error=False)) for proc in procs]), timeout
        )
    except asyncio.TimeoutError:
        LOGGER.warning("Agent processes did not close in time (%s)", procs)


class AgentManager(ServerSlice, SessionListener):
    """ This class contains all server functionality related to the management of agents
    """

    def __init__(self, closesessionsonstart: bool = True, fact_back_off: int = None) -> None:
        super(AgentManager, self).__init__(SLICE_AGENT_MANAGER)

        if fact_back_off is None:
            fact_back_off = opt.server_fact_resource_block.get()

        self._agent_procs: Dict[UUID, process.Subprocess] = {}  # env uuid -> process.SubProcess

        # back-off timer for fact requests
        self._fact_resource_block: int = fact_back_off
        # per resource time of last fact request
        self._fact_resource_block_set: Dict[str, float] = {}

        # session lock
        self.session_lock = locks.Lock()
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
        return [SLICE_SERVER, SLICE_DATABASE]

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

    def new_session(self, session: protocol.Session) -> None:
        self.add_background_task(self._register_session(session, datetime.now()))

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
        if key in self.tid_endpoint_to_session:
            return self.tid_endpoint_to_session[(tid, endpoint)].get_client()
        return None

    async def start(self) -> None:
        await super().start()
        self.add_background_task(self._start_agents())
        if self.closesessionsonstart:
            self.add_background_task(self._clean_db())

    async def prestop(self) -> None:
        await super().prestop()
        await self._terminate_agents()

    async def stop(self) -> None:
        await super().stop()

    # Agent Management
    async def ensure_agent_registered(self, env: data.Environment, nodename: str) -> data.Agent:
        """
            Make sure that an agent has been created in the database
        """
        with (await self.session_lock.acquire()):
            agent = await data.Agent.get(env.id, nodename)
            if agent is not None:
                return agent
            else:
                agent = await self._create_default_agent(env, nodename)
                return agent

    async def _create_default_agent(self, env: data.Environment, nodename: str) -> data.Agent:
        saved = data.Agent(environment=env.id, name=nodename, paused=False)
        await saved.insert()
        await self._verify_reschedule(env, [nodename])
        return saved

    async def _register_session(self, session: protocol.Session, now: float) -> data.Agent:
        with (await self.session_lock.acquire()):
            tid = session.tid
            sid = session.get_id()
            nodename = session.nodename

            self.sessions[sid] = session

            env = await data.Environment.get_by_id(tid)
            if env is None:
                LOGGER.warning("The environment id %s, for agent %s does not exist!", tid, sid)

            proc = await data.AgentProcess.get_one(sid=sid)

            if proc is None:
                proc = data.AgentProcess(hostname=nodename, environment=tid, first_seen=now, last_seen=now, sid=sid)
                await proc.insert()
            else:
                await proc.update_fields(last_seen=now)

            for nh in session.endpoint_names:
                LOGGER.debug("New session for agent %s on %s", nh, nodename)
                await data.AgentInstance(tid=tid, process=proc.sid, name=nh).insert()
                # await session.get_client().set_state(agent=nodename, enabled=False)

            if env is not None:
                await self._verify_reschedule(env, session.endpoint_names)

    async def _expire_session(self, session: protocol.Session, now: float) -> None:
        if not self.is_running() or self.is_stopping():
            return
        with (await self.session_lock.acquire()):
            tid = session.tid
            sid = session.get_id()

            LOGGER.debug("expiring session %s", sid)

            del self.sessions[sid]

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
                for endpoint in session.endpoint_names:
                    if (tid, endpoint) in self.tid_endpoint_to_session and self.tid_endpoint_to_session[
                        (tid, endpoint)
                    ] == session:
                        del self.tid_endpoint_to_session[(tid, endpoint)]

                await self._verify_reschedule(env, session.endpoint_names)

    async def _get_environment_sessions(self, env_id: uuid.UUID) -> List[protocol.Session]:
        """
            Get a list of all sessions for the given environment id
        """
        sessions = await data.AgentProcess.get_live_by_env(env_id)

        session_list = []
        for session in sessions:
            if session.sid in self.sessions:
                session_list.append(self.sessions[session.sid])

        return session_list

    async def _flush_agent_presence(self, session: protocol.Session, now: float) -> None:
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

    async def _verify_reschedule(self, env: data.Environment, enpoints: str) -> None:
        """
             only call under session lock
        """
        if not self.is_running() or self.is_stopping():
            return
        tid = env.id
        no_primary = [endpoint for endpoint in enpoints if (tid, endpoint) not in self.tid_endpoint_to_session]
        agents = await asyncio.gather(*[data.Agent.get(env.id, endpoint) for endpoint in no_primary])
        needswork = [agent for agent in agents if agent is not None and not agent.paused]
        for agent in needswork:
            await self._reschedule(env, agent)

    async def _reschedule(self, env: data.Environment, agent: data.Agent) -> None:
        """
             only call under session lock
        """
        tid = env.id
        instances = await data.AgentInstance.active_for(tid, agent.name)

        for instance in instances:
            agent_proc = await data.AgentProcess.get_one(sid=instance.process)
            sid = agent_proc.sid

            if sid not in self.sessions:
                LOGGER.warn("session marked as live in DB, but not found. sid: %s" % sid)
            else:
                await self._set_primary(env, agent, instance, self.sessions[sid])
                return

        await agent.update_fields(primary=None, last_failover=datetime.now())

    async def _set_primary(
        self, env: data.Environment, agent: data.Agent, instance: data.AgentInstance, session: protocol.Session
    ) -> None:
        LOGGER.debug("set session %s as primary for agent %s in env %s" % (session.get_id(), agent.name, env.id))
        self.tid_endpoint_to_session[(env.id, agent.name)] = session
        await agent.update_fields(last_failover=datetime.now(), primary=instance.id)
        self.add_background_task(session.get_client().set_state(agent.name, True))

    def is_primary(self, env: data.Environment, sid: uuid.UUID, agent: str) -> bool:
        prim = self.tid_endpoint_to_session.get((env.id, agent), None)
        if prim is None:
            return False
        return prim.get_id() == sid

    async def _clean_db(self) -> None:
        with (await self.session_lock.acquire()):
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
    def _fork_inmanta(
        self, args: List[str], outfile: Optional[str], errfile: Optional[str], cwd: Optional[str] = None
    ) -> process.Subprocess:
        """
            Fork an inmanta process from the same code base as the current code
        """
        inmanta_path = [sys.executable, "-m", "inmanta.app"]
        # handles can be closed, owned by child process,...
        try:
            outhandle = None
            errhandle = None
            if outfile is not None:
                outhandle = open(outfile, "wb+")
            if errfile is not None:
                errhandle = open(errfile, "wb+")

            # TODO: perhaps show in dashboard?
            return process.Subprocess(inmanta_path + args, cwd=cwd, env=os.environ.copy(), stdout=outhandle, stderr=errhandle)
        finally:
            if outhandle is not None:
                outhandle.close()
            if errhandle is not None:
                errhandle.close()

    # External APIS
    @protocol.handle(methods.get_agent_process, agent_sid="id")
    async def get_agent_process(self, agent_sid: str) -> Apireturn:
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
        if key in self.tid_endpoint_to_session:
            session = self.tid_endpoint_to_session[key]
            if session.id == sid:
                return 200, {"enabled": True}
        return 200, {"enabled": False}

    async def get_agent_process_report(self, agent_sid: uuid.UUID) -> Apireturn:
        ap = await data.AgentProcess.get_one(sid=agent_sid)
        if ap is None:
            return 404, {"message": "The given AgentProcess id does not exist!"}
        sid = ap.sid
        if sid not in self.sessions:
            return 404, {"message": "The given AgentProcess is not live!"}
        client = self.sessions[sid].get_client()
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

        with (await agent_lock.acquire()):
            LOGGER.info("%s matches agents managed by server, ensuring it is started.", agents)
            for agent in agents:
                with (await self.session_lock.acquire()):
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
        with open(config_path, "w+") as fd:
            fd.write(config)

        out: str = os.path.join(self._server_storage["logs"], "agent-%s.out" % env.id)
        err: str = os.path.join(self._server_storage["logs"], "agent-%s.err" % env.id)

        agent_log = os.path.join(self._server_storage["logs"], "agent-%s.log" % env.id)
        proc = self._fork_inmanta(
            ["-vvvv", "--timed-logs", "--config", config_path, "--log-file", agent_log, "agent"], out, err
        )

        if env.id in self._agent_procs and self._agent_procs[env.id] is not None:
            LOGGER.debug("Terminating old agent with PID %s", self._agent_procs[env.id].proc.pid)
            self._agent_procs[env.id].proc.terminate()
            await wait_for_proc_bounded([self._agent_procs[env.id]])

        self._agent_procs[env.id] = proc

        # Wait for an agent to start
        await retry_limited(lambda: self.get_agent_client(env.id, agents[0]) is not None, 5)
        # await sleep(2)

        LOGGER.debug("Started new agent with PID %s", proc.proc.pid)
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
        port: int = Config.get("server_rest_transport", "port", 8888)

        privatestatedir: str = os.path.join(Config.get("config", "state-dir", "/var/lib/inmanta"), environment_id)

        agent_deploy_splay: int
        agent_deploy_splay = await env.get(data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME)
        agent_deploy_interval: int
        agent_deploy_interval = await env.get(data.AUTOSTART_AGENT_DEPLOY_INTERVAL)

        agent_repair_splay: int
        agent_repair_splay = await env.get(data.AUTOSTART_AGENT_REPAIR_SPLAY_TIME)
        agent_repair_interval: int
        agent_repair_interval = await env.get(data.AUTOSTART_AGENT_REPAIR_INTERVAL)

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
            subproc.proc.terminate()
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
            proc.proc.terminate()
        await wait_for_proc_bounded(self._agent_procs.values())

        LOGGER.debug("Expiring all sessions")
        for session in self.sessions.values():
            session.expire(0)
            session.abort()
