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


from tornado import gen
from tornado import locks
from tornado import process


from inmanta.config import Config
from inmanta import data
from inmanta.server import protocol, SLICE_AGENT_MANAGER, SLICE_SESSION_MANAGER, SLICE_SERVER
from inmanta.asyncutil import retry_limited
from . import config as server_config
from inmanta.types import NoneGen, Apireturn

import logging
import os
from datetime import datetime
import time
import sys
import uuid
from inmanta.server.protocol import ServerSlice, SessionListener, SessionManager, ReturnClient
from inmanta.server import config as opt
from inmanta.protocol import encode_token, methods
from inmanta.resources import Id
import asyncio

from typing import Optional, Dict, Any, List, Generator, Tuple
from uuid import UUID
from inmanta.server.server import Server


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


@gen.coroutine
def wait_for_proc_bounded(procs: List[process.Subprocess], timeout: float=1.0) -> NoneGen:
    try:
        yield asyncio.wait_for(
            asyncio.gather(
                *[asyncio.shield(proc.wait_for_exit(raise_error=False)) for proc in procs]
            ),
            timeout)
    except asyncio.TimeoutError:
        LOGGER.warning("Agent processes did not close in time (%s)", procs)


class AgentManager(ServerSlice, SessionListener):
    '''
    This class contains all server functionality related to the management of agents
    '''

    def __init__(self, restserver: protocol.Server, closesessionsonstart: bool=True, fact_back_off: int=None) -> None:
        super(AgentManager, self).__init__(SLICE_AGENT_MANAGER)
        self.restserver = restserver

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

    @gen.coroutine
    def prestart(self, server: protocol.Server) -> NoneGen:
        yield ServerSlice.prestart(self, server)

        preserver = server.get_slice(SLICE_SERVER)
        assert isinstance(preserver, Server)
        self._server: Server = preserver
        self._server_storage: Dict[str, str] = self._server._server_storage

        presession = server.get_slice(SLICE_SESSION_MANAGER)
        assert isinstance(presession, SessionManager)
        presession.add_listener(self)

    def new_session(self, session: protocol.Session) -> None:
        self.add_future(self.register_session(session, datetime.now()))

    def expire(self, session: protocol.Session, timeout: float) -> None:
        self.add_future(self.expire_session(session, datetime.now()))

    def seen(self, session: protocol.Session, endpoint_names: List[str]) -> None:
        if set(session.endpoint_names) != set(endpoint_names):
            LOGGER.warning("Agent endpoint set changed, this should not occur, update ignored (was %s is %s)" %
                           (set(session.endpoint_names), set(endpoint_names)))
        # start async, let it run free
        self.add_future(self.flush_agent_presence(session, datetime.now()))

    # From server
    def get_agent_client(self, tid: uuid.UUID, endpoint: str) -> Optional[ReturnClient]:
        if isinstance(tid, str):
            tid = uuid.UUID(tid)
        key = (tid, endpoint)
        if key in self.tid_endpoint_to_session:
            return self.tid_endpoint_to_session[(tid, endpoint)].get_client()
        return None

    @gen.coroutine
    def start(self) -> NoneGen:
        yield super().start()
        self.add_future(self.start_agents())
        if self.closesessionsonstart:
            self.add_future(self.clean_db())

    @gen.coroutine
    def stop(self) -> NoneGen:
        yield super().stop()
        yield self.terminate_agents()

    # Agent Management
    @gen.coroutine
    def ensure_agent_registered(self, env: data.Environment, nodename: str) -> Generator[Any, Any, data.Agent]:
        """
            Make sure that an agent has been created in the database
        """
        with (yield self.session_lock.acquire()):
            agent = yield data.Agent.get(env.id, nodename)
            if agent is not None:
                return agent
            else:
                agent = yield self.create_default_agent(env, nodename)
                return agent

    @gen.coroutine
    def create_default_agent(self, env: data.Environment, nodename: str) -> Generator[Any, Any, data.Agent]:
        saved = data.Agent(environment=env.id, name=nodename, paused=False)
        yield saved.insert()
        yield self.verify_reschedule(env, [nodename])
        return saved

    @gen.coroutine
    def register_session(self, session: protocol.Session, now: float) -> Generator[Any, Any, data.Agent]:
        with (yield self.session_lock.acquire()):
            tid = session.tid
            sid = session.get_id()
            nodename = session.nodename

            self.sessions[sid] = session

            env = yield data.Environment.get_by_id(tid)
            if env is None:
                LOGGER.warning("The environment id %s, for agent %s does not exist!", tid, sid)

            proc = yield data.AgentProcess.get_one(sid=sid)

            if proc is None:
                proc = data.AgentProcess(hostname=nodename, environment=tid, first_seen=now, last_seen=now, sid=sid)
                yield proc.insert()
            else:
                yield proc.update_fields(last_seen=now)

            for nh in session.endpoint_names:
                LOGGER.debug("New session for agent %s on %s", nh, nodename)
                yield data.AgentInstance(tid=tid, process=proc.sid, name=nh).insert()
                # yield session.get_client().set_state(agent=nodename, enabled=False)

            if env is not None:
                yield self.verify_reschedule(env, session.endpoint_names)

    @gen.coroutine
    def expire_session(self, session: protocol.Session, now: float) -> NoneGen:
        if not self.running:
            return
        with (yield self.session_lock.acquire()):
            tid = session.tid
            sid = session.get_id()

            LOGGER.debug("expiring session %s", sid)

            del self.sessions[sid]

            env = yield data.Environment.get_by_id(tid)
            if env is None:
                LOGGER.warning("The environment id %s, for agent %s does not exist!", tid, sid)

            aps = yield data.AgentProcess.get_by_sid(sid=sid)
            if aps is None:
                LOGGER.info("expiring session on none existant process sid:%s", sid)
            else:
                yield aps.update_fields(expired=now)

                instances = yield data.AgentInstance.get_list(process=aps.sid)
                for ai in instances:
                    yield ai.update_fields(expired=now)

            if env is not None:
                for endpoint in session.endpoint_names:
                    if ((tid, endpoint) in self.tid_endpoint_to_session
                            and self.tid_endpoint_to_session[(tid, endpoint)] == session):
                        del self.tid_endpoint_to_session[(tid, endpoint)]

                yield self.verify_reschedule(env, session.endpoint_names)

    @gen.coroutine
    def get_environment_sessions(self, env_id: uuid.UUID) -> Generator[Any, Any, List[protocol.Session]]:
        """
            Get a list of all sessions for the given environment id
        """
        sessions = yield data.AgentProcess.get_live_by_env(env_id)

        session_list = []
        for session in sessions:
            if session.sid in self.sessions:
                session_list.append(self.sessions[session.sid])

        return session_list

    @gen.coroutine
    def flush_agent_presence(self, session: protocol.Session, now: float) -> NoneGen:
        tid = session.tid
        sid = session.get_id()

        env = yield data.Environment.get_by_id(tid)
        if env is None:
            LOGGER.warning("The environment id %s, for agent %s does not exist!", tid, sid)
            return

        aps = yield data.AgentProcess.get_by_sid(sid=sid)
        if aps is None:
            LOGGER.warning("No process registered for SID %s", sid)
            return

        yield aps.update_fields(last_seen=now)

    @gen.coroutine
    def verify_reschedule(self, env: data.Environment, enpoints: str) -> NoneGen:
        """
             only call under session lock
        """
        if not self.running:
            return
        tid = env.id
        no_primary = [endpoint for endpoint in enpoints if (tid, endpoint) not in self.tid_endpoint_to_session]
        agents = yield [data.Agent.get(env.id, endpoint) for endpoint in no_primary]
        needswork = [agent for agent in agents if agent is not None and not agent.paused]
        for agent in needswork:
            yield self.reschedule(env, agent)

    @gen.coroutine
    def reschedule(self, env: data.Environment, agent: data.Agent) -> NoneGen:
        """
             only call under session lock
        """
        tid = env.id
        instances = yield data.AgentInstance.active_for(tid, agent.name)

        for instance in instances:
            agent_proc = yield data.AgentProcess.get_one(sid=instance.process)
            sid = agent_proc.sid

            if sid not in self.sessions:
                LOGGER.warn("session marked as live in DB, but not found. sid: %s" % sid)
            else:
                yield self._set_primary(env, agent, instance, self.sessions[sid])
                return

        yield agent.update_fields(primary=None, last_failover=datetime.now())

    @gen.coroutine
    def _set_primary(self,
                     env: data.Environment,
                     agent: data.Agent,
                     instance: data.AgentInstance,
                     session: protocol.Session) -> NoneGen:
        LOGGER.debug("set session %s as primary for agent %s in env %s" % (session.get_id(), agent.name, env.id))
        self.tid_endpoint_to_session[(env.id, agent.name)] = session
        yield agent.update_fields(last_failover=datetime.now(), primary=instance.id)
        self.add_future(session.get_client().set_state(agent.name, True))

    def is_primary(self,
                   env: data.Environment,
                   sid: uuid.UUID,
                   agent: str):
        prim = self.tid_endpoint_to_session.get((env.id, agent), None)
        if prim is None:
            return False
        return prim.get_id() == sid

    @gen.coroutine
    def clean_db(self) -> NoneGen:
        with (yield self.session_lock.acquire()):
            LOGGER.debug("Cleaning server session DB")

            # TODO: do as one query
            procs = yield data.AgentProcess.get_live()
            for proc in procs:
                yield proc.update_fields(expired=datetime.now())

            ais = yield data.AgentInstance.active()
            for ai in ais:
                yield ai.update_fields(expired=datetime.now())

            agents = yield data.Agent.get_list()
            for agent in agents:
                yield agent.update_fields(primary=None)

    # utils
    def _fork_inmanta(self,
                      args: List[str],
                      outfile: Optional[str],
                      errfile: Optional[str],
                      cwd: Optional[str]=None) -> process.Subprocess:
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
    @gen.coroutine
    def get_agent_process(self, agent_sid: str) -> Apireturn:
        return (yield self.get_agent_process_report(agent_sid))

    @protocol.handle(methods.trigger_agent, agent_id="id", env="tid")
    @gen.coroutine
    def trigger_agent(self, env: UUID, agent_id: str) -> Apireturn:
        raise NotImplementedError()

    @protocol.handle(methods.list_agent_processes)
    @gen.coroutine
    def list_agent_processes(self, environment: Optional[UUID], expired: bool) -> Apireturn:
        if environment is not None:
            env = yield data.Environment.get_by_id(environment)
            if env is None:
                return 404, {"message": "The given environment id does not exist!"}

        tid = environment
        if tid is not None:
            if expired:
                aps = yield data.AgentProcess.get_by_env(tid)
            else:
                aps = yield data.AgentProcess.get_live_by_env(tid)
        else:
            if expired:
                aps = yield data.AgentProcess.get_list()
            else:
                aps = yield data.AgentProcess.get_live()

        processes = []
        for p in aps:
            agent_dict = p.to_dict()
            ais = yield data.AgentInstance.get_list(process=p.sid)
            oais = []
            for ai in ais:
                a = ai.to_dict()
                oais.append(a)
            agent_dict["endpoints"] = oais
            processes.append(agent_dict)

        return 200, {"processes": processes}

    @protocol.handle(methods.list_agents, env="tid")
    @gen.coroutine
    def list_agents(self, env: Optional[data.Environment]) -> Apireturn:
        if env is not None:
            tid = env.id
            ags = yield data.Agent.get_list(environment=tid)
        else:
            ags = yield data.Agent.get_list()

        return 200, {"agents": [a.to_dict() for a in ags], "servertime": datetime.now().isoformat(timespec='microseconds')}

    @protocol.handle(methods.get_state, env="tid")
    @gen.coroutine
    def get_state(self, env: data.Environment, sid: uuid.UUID, agent: str) -> Apireturn:
        tid: UUID = env.id
        if isinstance(tid, str):
            tid = uuid.UUID(tid)
        key = (tid, agent)
        if key in self.tid_endpoint_to_session:
            session = self.tid_endpoint_to_session[key]
            if session.id == sid:
                return 200, {"enabled": True}
        return 200, {"enabled": False}

    @gen.coroutine
    def get_agent_process_report(self, agent_sid: uuid.UUID) -> Apireturn:
        ap = yield data.AgentProcess.get_one(sid=agent_sid)
        if ap is None:
            return 404, {"message": "The given AgentProcess id does not exist!"}
        sid = ap.sid
        if sid not in self.sessions:
            return 404, {"message": "The given AgentProcess is not live!"}
        client = self.sessions[sid].get_client()
        result = yield client.get_status()
        return result.code, result.get_result()

    # Start/stop agents
    @gen.coroutine
    def _ensure_agents(self,
                       env: data.Environment,
                       agents: List[str],
                       restart: bool=False) -> Generator[Any, Any, bool]:
        """
            Ensure that all agents defined in the current environment (model) and that should be autostarted, are started.

            :param env: The environment to start the agents for
            :param agents: A list of agent names that possibly should be started in this environment.
            :param restart: Restart all agents even if the list of agents is up to date.
        """
        agent_map: Dict[str, str]
        agent_map = yield env.get(data.AUTOSTART_AGENT_MAP)
        agents = [agent for agent in agents if agent in agent_map]
        needsstart = restart
        if len(agents) == 0:
            return False

        with (yield agent_lock.acquire()):
            LOGGER.info("%s matches agents managed by server, ensuring it is started.", agents)
            for agent in agents:
                with (yield self.session_lock.acquire()):
                    myagent = self.get_agent_client(env.id, agent)
                    if myagent is None:
                        needsstart = True

            if needsstart:
                res = yield self.__do_start_agent(agents, env)
                return res
        return False

    @gen.coroutine
    def __do_start_agent(self, agents: List[str], env: data.Environment) -> Generator[Any, Any, bool]:
        """
            Start an agent process for the given agents in the given environment
        """
        agent_map: Dict[str, str]
        agent_map = yield env.get(data.AUTOSTART_AGENT_MAP)
        config: str
        config = yield self._make_agent_config(env, agents, agent_map)

        config_dir = os.path.join(self._server_storage["agents"], str(env.id))
        if not os.path.exists(config_dir):
            os.mkdir(config_dir)

        config_path = os.path.join(config_dir, "agent.cfg")
        with open(config_path, "w+") as fd:
            fd.write(config)

        if not self._server._agent_no_log:
            out: Optional[str] = os.path.join(self._server_storage["logs"], "agent-%s.out" % env.id)
            err: Optional[str] = os.path.join(self._server_storage["logs"], "agent-%s.err" % env.id)
        else:
            out = None
            err = None

        agent_log = os.path.join(self._server_storage["logs"], "agent-%s.log" % env.id)
        proc = self._fork_inmanta(["-vvvv", "--timed-logs", "--config", config_path, "--log-file", agent_log, "agent"],
                                  out, err)

        if env.id in self._agent_procs and self._agent_procs[env.id] is not None:
            LOGGER.debug("Terminating old agent with PID %s", self._agent_procs[env.id].proc.pid)
            self._agent_procs[env.id].proc.terminate()
            yield wait_for_proc_bounded([self._agent_procs[env.id]])

        self._agent_procs[env.id] = proc

        # Wait for an agent to start
        yield retry_limited(lambda: self.get_agent_client(env.id, agents[0]) is not None, 5)
        # yield sleep(2)

        LOGGER.debug("Started new agent with PID %s", proc.proc.pid)
        return True

    @gen.coroutine
    def terminate_agents(self) -> NoneGen:
        for proc in self._agent_procs.values():
            proc.proc.terminate()
        yield wait_for_proc_bounded(self._agent_procs.values())

    @gen.coroutine
    def _make_agent_config(self,
                           env: data.Environment,
                           agent_names: List[str],
                           agent_map: Dict[str, str]) -> Generator[Any, Any, str]:
        """
            Generate the config file for the process that hosts the autostarted agents

            :param env: The environment for which to autostart agents
            :param agent_names: The names of the agents
            :param agent_map: The agent mapping to use
            :return: A string that contains the config file content.
        """
        environment_id = str(env.id)
        port: int = Config.get("server_rest_transport", "port", "8888")

        privatestatedir: str = os.path.join(Config.get("config", "state-dir", "/var/lib/inmanta"), environment_id)

        agent_deploy_splay: int
        agent_deploy_splay = yield env.get(data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME)
        agent_deploy_interval: int
        agent_deploy_interval = yield env.get(data.AUTOSTART_AGENT_DEPLOY_INTERVAL)

        agent_repair_splay: int
        agent_repair_splay = yield env.get(data.AUTOSTART_AGENT_REPAIR_SPLAY_TIME)
        agent_repair_interval: int
        agent_repair_interval = yield env.get(data.AUTOSTART_AGENT_REPAIR_INTERVAL)

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
""" % {"agents": ",".join(agent_names), "env_id": environment_id, "port": port,
            "agent_map": ",".join(["%s=%s" % (k, v) for (k, v) in agent_map.items()]),
            "statedir": privatestatedir, "agent_deploy_splay": agent_deploy_splay,
            "agent_deploy_interval": agent_deploy_interval, "agent_repair_splay": agent_repair_splay,
            "agent_repair_interval": agent_repair_interval, "serveradress": server_config.server_address.get()}

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

        return config

    # Parameters

    @gen.coroutine
    def _request_parameter(self, env_id: uuid.UUID, resource_id: str) -> Apireturn:
        """
            Request the value of a parameter from an agent
        """
        if resource_id is not None and resource_id != "":
            env = yield data.Environment.get_by_id(env_id)

            # get a resource version
            res = yield data.Resource.get_latest_version(env_id, resource_id)

            if res is None:
                return 404, {"message": "The resource has no recent version."}

            rid: Id = Id.parse_id(res.resource_version_id)
            version: int = rid.version

            # only request facts of a resource every _fact_resource_block time
            now = time.time()
            if (resource_id not in self._fact_resource_block_set
                    or (self._fact_resource_block_set[resource_id] + self._fact_resource_block) < now):

                agents = yield data.ConfigurationModel.get_agents(env.id, version)
                yield self._ensure_agents(env, agents)

                client = self.get_agent_client(env_id, res.agent)
                if client is not None:
                    future = client.get_parameter(str(env_id), res.agent, res.to_dict())
                    self.add_future(future)

                self._fact_resource_block_set[resource_id] = now

            else:
                LOGGER.debug("Ignore fact request for %s, last request was sent %d seconds ago.",
                             resource_id, now - self._fact_resource_block_set[resource_id])

            return 503, {"message": "Agents queried for resource parameter."}
        else:
            return 404, {"message": "resource_id parameter is required."}

    @gen.coroutine
    def start_agents(self) -> NoneGen:
        """
            Ensure that autostarted agents of each environment are started when AUTOSTART_ON_START is true. This method
            is called on server start.
        """
        environments = yield data.Environment.get_list()
        for env in environments:
            agents = yield data.Agent.get_list(environment=env.id)
            autostart = yield env.get(data.AUTOSTART_ON_START)
            if autostart:
                agent_list = [a.name for a in agents]
                yield self._ensure_agents(env, agent_list)

    @gen.coroutine
    def restart_agents(self, env: data.Environment) -> NoneGen:
        agents = yield data.Agent.get_list(environment=env.id)
        autostart = yield env.get(data.AUTOSTART_ON_START)
        if autostart:
            agent_list = [a.name for a in agents]
            yield self._ensure_agents(env, agent_list, True)

    @gen.coroutine
    def stop_agents(self, env: data.Environment) -> NoneGen:
        """
            Stop all agents for this environment and close sessions
        """
        LOGGER.debug("Stopping all autostarted agents for env %s", env.id)
        if env.id in self._agent_procs:
            subproc = self._agent_procs[env.id]
            subproc.proc.terminate()
            yield wait_for_proc_bounded([subproc])
            del self._agent_procs[env.id]

        LOGGER.debug("Expiring all sessions for %s", env.id)
        sessions: List[protocol.Session]
        sessions = yield self.get_environment_sessions(env.id)
        for session in sessions:
            session.expire(0)
