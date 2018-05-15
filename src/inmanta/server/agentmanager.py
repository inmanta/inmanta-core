"""
    Copyright 2017 Inmanta

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

from inmanta.config import Config
from inmanta import data
from inmanta import protocol
from inmanta.asyncutil import retry_limited
from . import config as server_config

import logging
import os
from datetime import datetime
import time
import sys
import subprocess
import uuid


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

"""


class AgentManager(object):
    '''
    This class contains all server functionality related to the management of agents
    '''

    def __init__(self, server, closesessionsonstart=True, fact_back_off=60):
        self._server = server

        self._agent_procs = {}  # env uuid -> subprocess.Popen
        server.add_future(self.start_agents())

        # back-off timer for fact requests
        self._fact_resource_block = fact_back_off
        # per resource time of last fact request
        self._fact_resource_block_set = {}

        self._server_storage = server._server_storage

        # session lock
        self.session_lock = locks.Lock()
        # all sessions
        self.sessions = {}
        # live sessions
        self.tid_endpoint_to_session = {}

        self.closesessionsonstart = closesessionsonstart

    # From server
    def new_session(self, session: protocol.Session):
        self.add_future(self.register_session(session, datetime.now()))

    def expire(self, session: protocol.Session):
        self.add_future(self.expire_session(session, datetime.now()))

    def get_agent_client(self, tid: uuid.UUID, endpoint):
        if isinstance(tid, str):
            tid = uuid.UUID(tid)
        key = (tid, endpoint)
        if key in self.tid_endpoint_to_session:
            return self.tid_endpoint_to_session[(tid, endpoint)].get_client()
        return None

    def seen(self, session, endpoint_names):
        if set(session.endpoint_names) != set(endpoint_names):
            LOGGER.warning("Agent endpoint set changed, this should not occur, update ignored (was %s is %s)" %
                           (set(session.endpoint_names), set(endpoint_names)))
        # start async, let it run free
        self.add_future(self.flush_agent_presence(session, datetime.now()))

    def start(self):
        if self.closesessionsonstart:
            self.add_future(self.clean_db())

    def stop(self):
        self.terminate_agents()

    # To Server
    def add_future(self, future):
        self._server.add_future(future)

    # Agent Management

    @gen.coroutine
    def ensure_agent_registered(self, env: data.Environment, nodename: str):
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
    def create_default_agent(self, env: data.Environment, nodename: str):
        saved = data.Agent(environment=env.id, name=nodename, paused=False)
        yield saved.insert()
        yield self.verify_reschedule(env, [nodename])
        return saved

    @gen.coroutine
    def register_session(self, session: protocol.Session, now):
        with (yield self.session_lock.acquire()):
            tid = session.tid
            sid = session.id
            nodename = session.nodename

            self.sessions[sid] = session

            env = yield data.Environment.get_by_id(tid)
            if env is None:
                LOGGER.warning("The environment id %s, for agent %s does not exist!", tid, sid)

            proc = yield data.AgentProcess.get_by_sid(sid)
            if proc is None:
                proc = data.AgentProcess(hostname=nodename, environment=tid, first_seen=now, last_seen=now, sid=sid)
                yield proc.insert()
            else:
                yield proc.update_fields(last_seen=now)

            for nh in session.endpoint_names:
                LOGGER.debug("New session for agent %s on %s", nh, nodename)
                yield data.AgentInstance(tid=tid, process=proc.id, name=nh).insert()
                # yield session.get_client().set_state(agent=nodename, enabled=False)

            if env is not None:
                yield self.verify_reschedule(env, session.endpoint_names)

    @gen.coroutine
    def expire_session(self, session: protocol.Session, now):
        with (yield self.session_lock.acquire()):
            tid = session.tid
            sid = session.id

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

                instances = yield data.AgentInstance.get_list(process=aps.id)
                for ai in instances:
                    yield ai.update_fields(expired=now)

            if env is not None:
                for endpoint in session.endpoint_names:
                    if ((tid, endpoint) in self.tid_endpoint_to_session and
                            self.tid_endpoint_to_session[(tid, endpoint)] == session):
                        del self.tid_endpoint_to_session[(tid, endpoint)]

                yield self.verify_reschedule(env, session.endpoint_names)

    @gen.coroutine
    def get_environment_sessions(self, env_id: uuid.UUID):
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
    def flush_agent_presence(self, session: protocol.Session, now):
        tid = session.tid
        sid = session.id

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
    def verify_reschedule(self, env, enpoints):
        """
             only call under session lock
        """
        tid = env.id
        no_primary = [endpoint for endpoint in enpoints if (tid, endpoint) not in self.tid_endpoint_to_session]
        agents = yield [data.Agent.get(env.id, endpoint) for endpoint in no_primary]
        needswork = [agent for agent in agents if agent is not None and not agent.paused]
        for agent in needswork:
            yield self.reschedule(env, agent)

    @gen.coroutine
    def reschedule(self, env, agent):
        """
             only call under session lock
        """
        tid = env.id
        instances = yield data.AgentInstance.active_for(tid, agent.name)

        for instance in instances:
            agent_proc = yield data.AgentProcess.get_by_id(instance.process)
            sid = agent_proc.sid

            if sid not in self.sessions:
                LOGGER.warn("session marked as live in DB, but not found. sid: %s" % sid)
            else:
                yield self._set_primary(env, agent, instance, self.sessions[sid])
                return

        yield agent.update_fields(primary=None, last_failover=datetime.now())

    @gen.coroutine
    def _set_primary(self, env: data.Environment, agent: data.Agent, instance: data.AgentInstance, session: protocol.Session):
        LOGGER.debug("set session %s as primary for agent %s in env %s" % (session.get_id(), agent.name, env.id))
        self.tid_endpoint_to_session[(env.id, agent.name)] = session
        yield agent.update_fields(last_failover=datetime.now(), primary=instance.id)
        self.add_future(session.get_client().set_state(agent.name, True))

    @gen.coroutine
    def clean_db(self):
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
    def _fork_inmanta(self, args, outfile, errfile, cwd=None):
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
            return subprocess.Popen(inmanta_path + args, cwd=cwd, env=os.environ.copy(),
                                    stdout=outhandle, stderr=errhandle)
        finally:
            if outhandle is not None:
                outhandle.close()
            if errhandle is not None:
                errhandle.close()

    # External APIS

    @gen.coroutine
    def list_agent_processes(self, tid, expired):
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
            ais = yield data.AgentInstance.get_list(process=p.id)
            oais = []
            for ai in ais:
                a = ai.to_dict()
                oais.append(a)
            agent_dict["endpoints"] = oais
            processes.append(agent_dict)

        return 200, {"processes": processes}

    @gen.coroutine
    def get_agent_process_report(self, apid: uuid.UUID):
        ap = yield data.AgentProcess.get_by_id(apid)
        if ap is None:
            return 404, {"message": "The given AgentProcess id does not exist!"}
        sid = ap.sid
        if sid not in self.sessions:
            return 404, {"message": "The given AgentProcess is not live!"}
        client = self.sessions[sid].get_client()
        result = yield client.get_status()
        return result.code, result.get_result()

    @gen.coroutine
    def list_agents(self, tid):
        if tid is not None:
            ags = yield data.Agent.get_list(environment=tid)
        else:
            ags = yield data.Agent.get_list()

        return 200, {"agents": [a.to_dict() for a in ags], "servertime": datetime.now().isoformat()}

    # Start/stop agents
    @gen.coroutine
    def _ensure_agents(self, env: data.Environment, agents: list, restart: bool=False):
        """
            Ensure that all agents defined in the current environment (model) and that should be autostarted, are started.

            :param env: The environment to start the agents for
            :param agents: A list of agent names that possibly should be started in this environment.
            :param restart: Restart all agents even if the list of agents is up to date.
        """
        agent_map = yield env.get(data.AUTOSTART_AGENT_MAP)
        agents = [agent for agent in agents if agent in agent_map]
        needsstart = restart
        if len(agents) == 0:
            return False

        with (yield agent_lock.acquire()):
            LOGGER.info("%s matches agents managed by server, ensuring it is started.", agents)
            for agent in agents:
                with (yield self.session_lock.acquire()):
                    agent = self.get_agent_client(env.id, agent)
                    if agent is None:
                        needsstart = True

            if needsstart:
                res = yield self.__do_start_agent(agents, env)
                return res
        return False

    @gen.coroutine
    def __do_start_agent(self, agents, env):
        """
            Start an agent process for the given agents in the given environment
        """
        agent_map = yield env.get(data.AUTOSTART_AGENT_MAP)
        config = yield self._make_agent_config(env, agents, agent_map)

        config_dir = os.path.join(self._server_storage["agents"], str(env.id))
        if not os.path.exists(config_dir):
            os.mkdir(config_dir)

        config_path = os.path.join(config_dir, "agent.cfg")
        with open(config_path, "w+") as fd:
            fd.write(config)

        if not self._server._agent_no_log:
            out = os.path.join(self._server_storage["logs"], "agent-%s.log" % env.id)
            err = os.path.join(self._server_storage["logs"], "agent-%s.err" % env.id)
        else:
            out = None
            err = None

        proc = self._fork_inmanta(["-vvvv", "--timed-logs", "--config", config_path, "agent"], out, err)

        if env.id in self._agent_procs and self._agent_procs[env.id] is not None:
            LOGGER.debug("Terminating old agent with PID %s", self._agent_procs[env.id].pid)
            self._agent_procs[env.id].terminate()

        self._agent_procs[env.id] = proc

        # Wait for an agent to start
        yield retry_limited(lambda: self.get_agent_client(env.id, agents[0]) is not None, 5)
        # yield sleep(2)

        LOGGER.debug("Started new agent with PID %s", proc.pid)
        return True

    def terminate_agents(self):
        for proc in self._agent_procs.values():
            proc.terminate()

    @gen.coroutine
    def _make_agent_config(self, env: data.Environment, agent_names: list, agent_map: dict) -> str:
        """
            Generate the config file for the process that hosts the autostarted agents

            :param env: The environment for which to autostart agents
            :param agent_names: The names of the agents
            :param agent_map: The agent mapping to use
            :return: A string that contains the config file content.
        """
        environment_id = str(env.id)
        port = Config.get("server_rest_transport", "port", "8888")

        privatestatedir = os.path.join(Config.get("config", "state-dir", "/var/lib/inmanta"), environment_id)
        agent_splay = yield env.get(data.AUTOSTART_SPLAY)
        agent_interval = yield env.get(data.AUTOSTART_AGENT_INTERVAL)
        # generate config file
        config = """[config]
heartbeat-interval = 60
state-dir=%(statedir)s

agent-names = %(agents)s
environment=%(env_id)s
agent-map=%(agent_map)s
agent_splay=%(agent_splay)d
agent_interval=%(agent_interval)d

[agent_rest_transport]
port=%(port)s
host=localhost
""" % {"agents": ",".join(agent_names), "env_id": environment_id, "port": port,
            "agent_map": ",".join(["%s=%s" % (k, v) for (k, v) in agent_map.items()]),
            "statedir": privatestatedir, "agent_splay": agent_splay, "agent_interval": agent_interval}

        if server_config.server_enable_auth.get():
            token = protocol.encode_token(["agent"], environment_id)
            config += """
token=%s
    """ % (token)

        ssl_cert = server_config.server_ssl_key.get()
        ssl_ca = server_config.server_ssl_ca_cert.get()

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
    def _request_parameter(self, env_id: uuid.UUID, resource_id):
        """
            Request the value of a parameter from an agent
        """
        if resource_id is not None and resource_id != "":
            env = yield data.Environment.get_by_id(env_id)

            # get the latest version
            version = yield data.ConfigurationModel.get_latest_version(env_id)

            if version is None:
                return 404, {"message": "The environment associated with this parameter does not have any releases."}

            # get a resource version
            res = yield data.Resource.get_latest_version(env_id, resource_id)

            if res is None:
                return 404, {"message": "The resource has no recent version."}

            # only request facts of a resource every _fact_resource_block time
            now = time.time()
            if (resource_id not in self._fact_resource_block_set or
                    (self._fact_resource_block_set[resource_id] + self._fact_resource_block) < now):

                agents = yield data.ConfigurationModel.get_agents(env.id, version.version)
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
    def get_state(self, tid: uuid.UUID, sid: uuid.UUID, agent: str):
        if isinstance(tid, str):
            tid = uuid.UUID(tid)
        key = (tid, agent)
        if key in self.tid_endpoint_to_session:
            session = self.tid_endpoint_to_session[(tid, agent)]
            if session.id == sid:
                return 200, {"enabled": True}
        return 200, {"enabled": False}

    @gen.coroutine
    def start_agents(self):
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
    def restart_agents(self, env):
        agents = yield data.Agent.get_list(environment=env.id)
        autostart = yield env.get(data.AUTOSTART_ON_START)
        if autostart:
            agent_list = [a.name for a in agents]
            yield self._ensure_agents(env, agent_list, True)

    @gen.coroutine
    def stop_agents(self, env):
        """
            Stop all agents for this environment and close sessions
        """
        LOGGER.debug("Stopping all autostarted agents for env %s", env.id)
        if env.id in self._agent_procs:
            self._agent_procs[env.id].terminate()
            del self._agent_procs[env.id]

        LOGGER.debug("Expiring all sessions for %s", env.id)
        sessions = yield self.get_environment_sessions(env.id)
        for session in sessions:
            session.expire(0)
