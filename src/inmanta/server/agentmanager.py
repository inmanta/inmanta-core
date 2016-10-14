"""
    Copyright 2016 Inmanta

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
from motorengine import DESCENDING

from inmanta.config import Config, executable
from inmanta.agent.io.remote import RemoteIO
from inmanta.resources import HostNotFoundException
from inmanta import data
from inmanta.server.config import server_agent_autostart

import logging
import glob
import os
from _collections import defaultdict
from datetime import datetime
import time
import sys
import subprocess
from inmanta.protocol import Session
from inmanta.data import AgentProcess, AgentInstance, Agent, Environment
import uuid


LOGGER = logging.getLogger(__name__)
LOCK = locks.Lock()


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


todo: 
 1-create data model in DB
 2-create API
 

exposed APIS

list agent-processes
list agent-process endpoints
get agent-process report

list agents (api)
pause agent (api)
get agent state (api)
 - paused / down / up

set primary agent (api)
 - endpoint

get agent state (internal)
 - enabled / disabled, current version
set agent state (on agent)
 - enabled / disabled, current version

procedures:
 select primary agent (on failover)
  - acquire lock
  - send disable to old primary
  - set state on new primary
  - release lock

TODO:
  agent failover modes (max 1, min 1, ....)



"""


class AgentManager(object):
    '''
    This class contains all server functionality related to the management of agents
    '''

    def __init__(self, server, autostart=True, fact_back_off=60):
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

    # From server
    def new_session(self, session: Session):
        self.add_future(self.register_session(session, datetime.now()))

    def expire(self, session: Session):
        self.add_future(self.expire_session(session, datetime.now()))

    def get_agent_client(self, tid, endpoint):
        if not isinstance(tid, str):
            tid = str(tid)
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

    def stop(self):
        self.terminate_agents()

    # To Server
    def add_future(self, future):
        self._server.add_future(future)

    # Agent Management

    @gen.coroutine
    def register_session(self, session: Session, now):
        with (yield self.session_lock.acquire()):
            tid = session.tid
            sid = session.id
            nodename = session.nodename

            self.sessions[sid] = session

            env = yield data.Environment.get_uuid(tid)
            if env is None:
                LOGGER.warning("The environment id %s, for agent %s does not exist!", tid, sid)
                return

            proc = yield AgentProcess(uuid=uuid.uuid4(),
                                      hostname=nodename,
                                      environment=env,
                                      first_seen=now,
                                      last_seen=now,
                                      sid=sid).save()

            for nh in session.endpoint_names:
                LOGGER.debug("Seen agent %s on %s", nh, nodename)
                yield data.AgentInstance(uuid=uuid.uuid4(),
                                         tid=tid,
                                         process=proc,
                                         name=nh).save()
            yield self.verify_reschedule(env, session.endpoint_names)

    @gen.coroutine
    def expire_session(self, session: Session, now):
        with (yield self.session_lock.aquire()):

            tid = session.tid
            sid = session.id

            env = yield data.Environment.get_uuid(tid)
            if env is None:
                LOGGER.warning("The environment id %s, for agent %s does not exist!", tid, sid)
                return

            aps = AgentProcess.get_by_sid(sid=sid).find_all()

            aps.expired = now
            aps.sid = None

            yield aps.save

            for ai in AgentInstance.objects.filter(process=aps):
                ai.expired = now
                yield ai.save()

            yield self.verify_reschedule(env, session.endpoint_names)

    @gen.coroutine
    def flush_agent_presence(self, session: Session, now):
        tid = session.tid
        sid = session.id

        env = yield data.Environment.get_uuid(tid)
        if env is None:
            LOGGER.warning("The environment id %s, for agent %s does not exist!", tid, sid)
            return

        aps = AgentProcess.get_by_sid(sid=sid).find_all()
        aps.last_seen = now
        aps.save()

    @gen.coroutine
    def verify_reschedule(self, env, enpoints):
        """
             only call under session lock
        """
        tid = env.uuid
        no_primary = [endpoint for endpoint in enpoints if (tid, endpoint) not in self.tid_endpoint_to_session]
        agents = yield [Agent.get(env, endpoint) for endpoint in no_primary]
        needswork = [agent for agent in agents if agent is not None and not agent.paused]
        for agent in needswork:
            yield self.reschedule(env, agent)

    @gen.coroutine
    def reschedule(self, env, agent):
        """
             only call under session lock
        """
        tid = env.uuid
        instances = yield AgentInstance.activeFor(tid, agent.name)
        for instance in instances:
            yield instance.load_references()
            sid = instance.process.sid
            if sid not in self.sessions:
                LOGGER.warn("session marked as live in DB, but not found. sid: %s" % sid)
            else:
                yield self._setPrimary(env, agent, instance, self.sessions[sid])
                # todo: mark as online
                return
        # todo: mark as offline

    @gen.coroutine
    def _setPrimary(self, env: Environment, agent: Agent, instance: AgentInstance, session: Session):
        self.tid_endpoint_to_session[(env.uuid, agent.name)] = session
        agent.primary = instance
        yield agent.save()
        self.add_future(session.get_client().set_state(agent.name, True, 0))

    @gen.coroutine
    def clean_db(self):
        """
             only call under session lock
        """
        procs = yield AgentProcess.get_live()

        for proc in procs:
            proc.expired = datetime.now()
            yield proc.save()

        ais = yield AgentInstance.active()
        for ai in ais:
            ai.expired = datetime.now()
            yield ai.save()

    # utils
    def _fork_inmanta(self, args, outfile, errfile, cwd=None):
        """
            For an inmanta process from the same code base as the current code
        """
        main = executable.get()
        inmanta_path = [sys.executable, main]
        # handles can be closed, owned by child process,...s
        with open(outfile, "wb+") as outhandle:
            with open(errfile, "wb+") as errhandle:
                # TODO: perhaps show in dashboard?
                return subprocess.Popen(inmanta_path + args, cwd=cwd, env=os.environ.copy(),
                                        stdout=outhandle, stderr=errhandle)

    # Start/stop agents
    @gen.coroutine
    def _ensure_agent(self, environment_id: str, agent_name):
        """
            Ensure that the agent is running if required
        """
        if self._agent_matches(agent_name):
            with (yield LOCK.aquire()):
                LOGGER.info("%s matches agents managed by server, ensuring it is started.", agent_name)
                agent_data = None
                if environment_id in self._requires_agents:
                    # already have a process for this env
                    agent_data = self._requires_agents[environment_id]

                    if agent_data["process"] is not None and agent_data["process"].poll() is not None:
                        # but it is dead
                        pass
                    elif agent_name in agent_data["agents"]:
                        # and it already has this agent
                        # todo: check if alive
                        return False

                if agent_data is None:
                    agent_data = {"agents": set(), "process": None}
                    self._requires_agents[environment_id] = agent_data

                agent_data["agents"].add(agent_name)

                agent_names = ",".join(agent_data["agents"])

                # todo: cache what is what
                agent_map = {}
                for agent in agent_data["agents"]:
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

                out = os.path.join(self._server_storage["logs"], "agent-%s.log" % environment_id)
                err = os.path.join(self._server_storage["logs"], "agent-%s.err" % environment_id)
                proc = self._fork_inmanta(["-vvv", "--config", config_path, "agent"], out, err)

                if agent_data["process"] is not None:
                    LOGGER.debug("Terminating old agent with PID %s", agent_data["process"].pid)
                    agent_data["process"].terminate()

                # FIXME: include agent
                agent_data["process"] = proc
                self._requires_agents[environment_id] = agent_data
                # wait a bit here to make sure the agents registers with the server
                # TODO: queue calls in agent work queue even if agent is not available
                # TODO: wait for connection, instead of sleeping
                yield gen.sleep(2)

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
            "statedir": Config.get("config", "state-dir", "/var/lib/inmanta")}

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
        tid = str(env.uuid)

        if resource_id is not None and resource_id != "":
            # get the latest version
            versions = yield (data.ConfigurationModel.objects.filter(environment=env, released=True).  # @UndefinedVariable
                              order_by("version", direction=DESCENDING).limit(1).find_all())  # @UndefinedVariable

            if len(versions) == 0:
                return 404, {"message": "The environment associated with this parameter does not have any releases."}

            version = versions[0]

            # get the associated resource
            resources = yield data.Resource.objects.filter(environment=env,  # @UndefinedVariable
                                                           resource_id=resource_id).find_all()  # @UndefinedVariable

            if len(resources) == 0:
                return 404, {"message": "The resource parameter does not exist."}

            resource = resources[0]

            # get a resource version
            rvs = yield data.ResourceVersion.objects.filter(environment=env,  # @UndefinedVariable
                                                            model=version, resource=resource).find_all()  # @UndefinedVariable

            if len(rvs) == 0:
                return 404, {"message": "The resource has no recent version."}

            # only request facts of a resource every _fact_resource_block time
            now = time.time()
            if (resource_id not in self._fact_resource_block_set or
                    (self._fact_resource_block_set[resource_id] + self._fact_resource_block) < now):
                yield self._ensure_agent(str(tid), resource.agent)
                client = self.get_agent_client(tid, resource.agent)
                if client is not None:
                    future = client.get_parameter(tid, resource.agent, rvs[0].to_dict())
                    self.add_future(future)

                self._fact_resource_block_set[resource_id] = now

            else:
                LOGGER.debug("Ignore fact request for %s, last request was sent %d seconds ago.",
                             resource_id, now - self._fact_resource_block_set[resource_id])

            return 503, {"message": "Agents queried for resource parameter."}
        else:
            return 404, {"message": "resource_id parameter is required."}

    @gen.coroutine
    def get_agent_info(self, id):
        node = yield data.Node.get_by_hostname(id)
        if node is None:
            return 404

        agents = yield data.Agent.objects.filter(node=node).find_all()  # @UndefinedVariable
        agent_list = []
        for agent in agents:
            agent_dict = yield agent.to_dict()
            agent_list.append(agent_dict)

        return 200, {"node": node.to_dict(), "agents": agent_list}

    @gen.coroutine
    def trigger_agent(self, tid, id):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        agent_env = self.get_env(tid)
        for agent in agent_env.agents:
            client = self.get_agent_client(tid, agent)
            if client is not None:
                future = client.trigger_agent(tid, agent)
                self.add_future(future)

        return 200

    @gen.coroutine
    def list_agent(self, environment):
        response = []
        nodes = yield data.Node.objects.find_all()  # @UndefinedVariable
        for node in nodes:  # @UndefinedVariable
            agents = yield data.Agent.objects.filter(node=node).find_all()  # @UndefinedVariable
            node_dict = node.to_dict()
            node_dict["agents"] = []
            for agent in agents:
                agent_dict = yield agent.to_dict()  # do this first, because it also loads all lazy references
                if environment is None or agent.environment.uuid == environment:
                    node_dict["agents"].append(agent_dict)

            if len(node_dict["agents"]) > 0:
                response.append(node_dict)

        return 200, {"nodes": response, "servertime": datetime.datetime.now().isoformat()}

    @gen.coroutine
    def start_agents(self):
        agents = yield data.Agent.objects.find_all()  # @UndefinedVariable
        for agent in agents:
            if self._agent_matches(agent.name):
                yield agent.load_references()
                env_id = str(agent.environment.uuid)
                if env_id not in self._requires_agents:
                    agent_data = {"agents": set(), "process": None}
                    self._requires_agents[env_id] = agent_data

                self._requires_agents[env_id]["agents"].add(agent.name)

        for env_id in self._requires_agents.keys():
            agent = list(self._requires_agents[env_id]["agents"])[0]
            self._requires_agents[env_id]["agents"].remove(agent)
            yield self._ensure_agent(str(env_id), agent)
