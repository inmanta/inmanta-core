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


from tornado import gen, ioloop
from inmanta.config import Config
import glob
import os
import select
from tornado import locks
import logging
from inmanta.agent.io.remote import RemoteIO
from inmanta.resources import Id, HostNotFoundException
import threading
from inmanta import data
from _collections import defaultdict
import datetime
import time


LOGGER = logging.getLogger(__name__)
LOCK = locks.Lock()


class AgentManager(object):
    '''
    This class contains all server functionality related to the management of agents
    '''

    def __init__(self, server):
        self._server = server

        self._requires_agents = {}
        if Config.getboolean("server", "autostart-on-start", True):
            server.add_future(self.start_agents())

        self.tid_endpoint_to_session = defaultdict(list)

    def new_session(self, session, tid, endpoint_names, nodename):
        if not isinstance(tid, str):
            tid = str(tid)

        # make index
        for endpoint in endpoint_names:
            self.tid_endpoint_to_session[(tid, endpoint)].append(session)

    def expire(self, session):
        tid = session.tid
        for endpoint in session.endpoint_names:
            self.tid_endpoint_to_session[(tid, endpoint)].remove(session)

    def get_agent_client(self, tid, endpoint):
        if not isinstance(tid, str):
            tid = str(tid)
        sessions = self.tid_endpoint_to_session[(tid, endpoint)]
        if not sessions:
            return None
        return sessions[0].get_client()

    def seen(self, session):
        # start async, let it run free
        self.flush_agent_presence(session.tid, session.endpoint_names, session.nodename)

    @gen.coroutine
    def flush_agent_presence(self, tid, endpoint_names, nodename):
        env = yield data.Environment.get_uuid(tid)
        if env is None:
            LOGGER.warning("The given environment id %s does not exist!", tid)
            return

        now = datetime.datetime.now()

        node = yield data.Node.get_by_hostname(nodename)
        if node is not None:
            node.last_seen = now
            node.save()

        else:
            node = data.Node(hostname=nodename, last_seen=now)
            yield node.save()

        for nh in endpoint_names:
            LOGGER.debug("Seen agent %s on %s", nh, nodename)
            agents = yield data.Agent.objects.filter(name=nh, node=node, environment=env).find_all()  # @UndefinedVariable
            if len(agents) == 0:
                agent = data.Agent(name=nh, node=node, environment=env)

            else:
                agent = agents[0]

            agent.last_seen = now
            yield agent.save()

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

    def _agent_matches(self, agent_name):
        agent_globs = [x.strip() for x in Config.get("server", "agent_autostart", "iaas_*").split(",")]

        for agent_glob in agent_globs:
            if glob.fnmatch.fnmatchcase(agent_name, agent_glob):
                return True

        return False

    def _log_agent_output(self, environment_id, proc):
        fds = {proc.stdout: open(os.path.join(self._server_storage["logs"], "agent-%s.log" % environment_id), "wb+"),
               proc.stderr: open(os.path.join(self._server_storage["logs"], "agent-%s.err" % environment_id), "wb+")}

        def check_io():
            ready_to_read = select.select([proc.stdout, proc.stderr], [], [], 1000)[0]
            for io in ready_to_read:
                line = io.readline()
                fds[io].write(line)

        # keep checking stdout/stderr until the child exits
        while proc.poll() is None:
            check_io()

        check_io()  # check again to catch anything after the process exits

        for fd in fds.values():
            fd.close()

        return proc.wait()

    @gen.coroutine
    def _ensure_agent(self, environment_id: str, agent_name):
        """
            Ensure that the agent is running if required
        """
        if self._agent_matches(agent_name):
            with (yield LOCK.acquire()):
                LOGGER.info("%s matches agents managed by server, ensuring it is started.", agent_name)
                agent_data = None
                if environment_id in self._requires_agents:
                    agent_data = self._requires_agents[environment_id]

                    if agent_name in agent_data["agents"]:
                        return

                if agent_data is None:
                    agent_data = {"agents": set(), "process": None}
                    self._requires_agents[environment_id] = agent_data

                agent_data["agents"].add(agent_name)

                agent_names = ",".join(agent_data["agents"])

                agent_map = {}
                for agent in agent_data["agents"]:
                    try:
                        gw = RemoteIO(agent)
                        gw.close()
                    except HostNotFoundException:
                        agent_map[agent] = "localhost"

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
                    "agent_map": ",".join(["%s=%s" % (k, v) for k, v in agent_map.items()]),
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

                config_dir = os.path.join(self._server_storage["agents"], str(environment_id))
                if not os.path.exists(config_dir):
                    os.mkdir(config_dir)

                config_path = os.path.join(config_dir, "agent.cfg")
                with open(config_path, "w+") as fd:
                    fd.write(config)

                proc = self._fork_inmanta(["-vvv", "--config", config_path, "agent"])

                if agent_data["process"] is not None:
                    LOGGER.debug("Terminating old agent with PID %s", agent_data["process"].pid)
                    agent_data["process"].terminate()

                # FIXME: include agent
                threading.Thread(target=self._log_agent_output, args=(environment_id, proc)).start()
                agent_data["process"] = proc
                self._requires_agents[environment_id] = agent_data
                # wait a bit here to make sure the agents registers with the server
                # TODO: queue calls in agent work queue even if agent is not available
                yield gen.sleep(2)

                LOGGER.debug("Started new agent with PID %s", proc.pid)

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

        return 404, {"message": "The parameter does not exist."}

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
