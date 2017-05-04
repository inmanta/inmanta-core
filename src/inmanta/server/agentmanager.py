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
from inmanta.agent.io.remote import RemoteIO
from inmanta.resources import HostNotFoundException
from inmanta import data
from inmanta.agent import config as agent_config
from inmanta.server.config import server_agent_autostart
from inmanta.protocol import Session
from inmanta.asyncutil import retry_limited

import logging
import glob
import os
from datetime import datetime
import time
import sys
import subprocess
import uuid
from uuid import UUID


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

    def __init__(self, server, autostart=True, closesessionsonstart=True, fact_back_off=60):
        self._server = server

        self._requires_agents = {}
        if autostart:
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
    def new_session(self, session: Session):
        self.add_future(self.register_session(session, datetime.now()))

    def expire(self, session: Session):
        self.add_future(self.expire_session(session, datetime.now()))

    def get_agent_client(self, tid: UUID, endpoint):
        if isinstance(tid, str):
            tid = UUID(tid)
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
    def register_session(self, session: Session, now):
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
    def expire_session(self, session: Session, now):
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
    def flush_agent_presence(self, session: Session, now):
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
    def _set_primary(self, env: data.Environment, agent: data.Agent, instance: data.AgentInstance, session: Session):
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
            For an inmanta process from the same code base as the current code
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
    def get_agent_process_report(self, apid: UUID):
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
    def _ensure_agents(self, environment_id: str, agents):
        agents = [agent for agent in agents if self._agent_matches(agent)]
        started = False
        needsstart = False
        if len(agents) > 0:
            with (yield agent_lock.acquire()):
                LOGGER.info("%s matches agents managed by server, ensuring it is started.", agents)
                agent_data = None
                if environment_id in self._requires_agents:
                    agent_data = self._requires_agents[environment_id]

                if agent_data is None:
                    agent_data = {"agents": set(), "process": None}
                    self._requires_agents[environment_id] = agent_data

                for agent in agents:
                    agent_data["agents"].add(agent)
                    with (yield self.session_lock.acquire()):
                        agent = self.get_agent_client(environment_id, agent)
                        if agent is None:
                            needsstart = True

                if needsstart:
                    res = yield self.__do_start_agent(agent_data, environment_id)
                    started |= res
            return started
        else:
            return False

    @gen.coroutine
    def _ensure_agent(self, environment_id: str, agent_name):
        """
            Ensure that the agent is running if required

            make sure that ensure_agent_registered has been called for this agent
        """
        if self._agent_matches(agent_name):
            with (yield agent_lock.acquire()):
                LOGGER.info("%s matches agents managed by server, ensuring it is started.", agent_name)
                agent_data = None
                if environment_id in self._requires_agents:
                    agent_data = self._requires_agents[environment_id]

                    if agent_name in agent_data["agents"]:
                        # agent existed
                        with (yield self.session_lock.acquire()):
                            agent = self.get_agent_client(environment_id, agent_name)
                            if agent is not None:
                                # and is live
                                # TODO: is this the behaviour we want,
                                # do we want to start the agent locally, if it is already running remotely?
                                # and do we want this check to be enforced everywhere?
                                return False

                if agent_data is None:
                    agent_data = {"agents": set(), "process": None}
                    self._requires_agents[environment_id] = agent_data

                agent_data["agents"].add(agent_name)

                return (yield self.__do_start_agent(agent_data, environment_id))
        else:
            return False

    @gen.coroutine
    def __do_start_agent(self, agent_data, environment_id):
        agent_names = ",".join(agent_data["agents"])

        # todo: cache what is what
        agent_map = {}
        config_map = agent_config.agent_map.get()
        for agent in agent_data["agents"]:
            if agent in config_map:
                agent_map[agent] = config_map[agent]
            else:
                try:
                    gw = RemoteIO(agent)
                    gw.close()
                except HostNotFoundException:
                    agent_map[agent] = "localhost"

        config = self._make_agent_config(environment_id, agent_names, agent_map)

        config_dir = os.path.join(self._server_storage["agents"], str(environment_id))
        if not os.path.exists(config_dir):
            os.mkdir(config_dir)

        config_path = os.path.join(config_dir, "agent.cfg")
        with open(config_path, "w+") as fd:
            fd.write(config)

        if not self._server._agent_no_log:
            out = os.path.join(self._server_storage["logs"], "agent-%s.log" % environment_id)
            err = os.path.join(self._server_storage["logs"], "agent-%s.err" % environment_id)
        else:
            out = None
            err = None

        proc = self._fork_inmanta(["-vvvv", "--timed-logs", "--config", config_path, "agent"], out, err)

        if agent_data["process"] is not None:
            LOGGER.debug("Terminating old agent with PID %s", agent_data["process"].pid)
            agent_data["process"].terminate()

        # FIXME: include agent
        agent_data["process"] = proc
        self._requires_agents[environment_id] = agent_data

        yield retry_limited(lambda: self.get_agent_client(environment_id, agent) is not None, 5)
        # yield sleep(2)

        LOGGER.debug("Started new agent with PID %s", proc.pid)
        return True

    def terminate_agents(self):
        for agent in self._requires_agents.values():
            if agent["process"] is not None:
                agent["process"].terminate()

    def _agent_matches(self, agent_name):
        agent_globs = server_agent_autostart.get()

        for agent_glob in agent_globs:
            if glob.fnmatch.fnmatchcase(agent_name, agent_glob):
                return True

        return False

    def _make_agent_config(self, environment_id, agent_names, agent_map):
        port = Config.get("server_rest_transport", "port", "8888")

        privatestatedir = os.path.join(Config.get("config", "state-dir", "/var/lib/inmanta"), environment_id)
    # generate config file
        config = """[config]
heartbeat-interval = 60
state-dir=%(statedir)s

agent-names = %(agents)s
environment=%(env_id)s
agent-map=%(agent_map)s
python_binary=%(python_binary)s

[agent_rest_transport]
port=%(port)s
host=localhost
""" % {"agents": agent_names, "env_id": environment_id, "port": port,
            "python_binary": Config.get("config", "python_binary", "python"),
            "agent_map": ",".join(["%s=%s" % (k, v) for (k, v) in agent_map.items()]),
            "statedir": privatestatedir}

        user = Config.get("server", "username", None)
        passwd = Config.get("server", "password", None)
        if user is not None and passwd is not None:
            config += """
username=%s
password=%s
    """ % (user, passwd)

        ssl_cert = Config.get("server", "ssl_key_file", None)
        ssl_ca = Config.get("server", "ssl_cert_file", None)
        if ssl_ca is not None and ssl_cert is not None:
            config += """
ssl=True
ssl_ca_cert_file=%s
    """ % (ssl_ca)

        return config

    # Parameters

    @gen.coroutine
    def _request_parameter(self, env, resource_id):
        """
            Request the value of a parameter from an agent
        """
        tid = str(env)

        if resource_id is not None and resource_id != "":
            # get the latest version
            version = yield data.ConfigurationModel.get_latest_version(env)

            if version is None:
                return 404, {"message": "The environment associated with this parameter does not have any releases."}

            # get a resource version
            res = yield data.Resource.get_latest_version(env, resource_id)

            if res is None:
                return 404, {"message": "The resource has no recent version."}

            # only request facts of a resource every _fact_resource_block time
            now = time.time()
            if (resource_id not in self._fact_resource_block_set or
                    (self._fact_resource_block_set[resource_id] + self._fact_resource_block) < now):
                yield self._ensure_agent(str(tid), res.agent)
                client = self.get_agent_client(env, res.agent)
                if client is not None:
                    future = client.get_parameter(tid, res.agent, res.to_dict())
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
            tid = UUID(tid)
        key = (tid, agent)
        if key in self.tid_endpoint_to_session:
            session = self.tid_endpoint_to_session[(tid, agent)]
            if session.id == sid:
                return 200, {"enabled": True}
        return 200, {"enabled": False}

    @gen.coroutine
    def trigger_agent(self, tid, id):
        env = yield data.Environment.get_by_id(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        agent_env = self.get_env(tid)
        for agent in agent_env.agents:
            client = self.get_agent_client(tid, agent)
            if client is not None:
                future = client.trigger(tid, agent)
                self.add_future(future)

        return 200

    @gen.coroutine
    def start_agents(self):
        agents = yield data.Agent.get_list()
        for agent in agents:
            if self._agent_matches(agent.name):
                env_id = str(agent.environment)
                if env_id not in self._requires_agents:
                    agent_data = {"agents": set(), "process": None}
                    self._requires_agents[env_id] = agent_data

                self._requires_agents[env_id]["agents"].add(agent.name)

        for env_id in self._requires_agents.keys():
            agent = list(self._requires_agents[env_id]["agents"])[0]
            self._requires_agents[env_id]["agents"].remove(agent)
            yield self._ensure_agent(str(env_id), agent)
