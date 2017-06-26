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
import os
import logging
import random
import sys
import re

from mongobox import mongobox
from tornado import gen, process
from inmanta import module, config, server, agent, protocol, const, data


LOGGER = logging.getLogger(__name__)
PORT_START = 40000
MAX_TRIES = 25


cfg_prj = config.Option("deploy", "project", "deploy", "The project name to use in the deploy", config.is_str_opt)
cfg_env = config.Option("deploy", "environment", "deploy", "The environment name to use in the deploy", config.is_str_opt)


class FinishedException(Exception):
    """
        This exception is raised when the deploy is ready
    """


class Deploy(object):

    def __init__(self, io_loop, mongoport=0):
        self._mongobox = None
        self._mongoport = mongoport
        self._server_port = 0
        self._data_path = None
        self._server = None
        self._agent = None
        self._client = None

        self._environment_id = None

        self._io_loop = io_loop

        self._agent_ready = False

        loud_logger = logging.getLogger("inmanta.protocol")
        loud_logger.propagate = False

        loud_logger = logging.getLogger("tornado")
        loud_logger.propagate = False

    def _ensure_dir(self, path):
        if not os.path.exists(path):
            LOGGER.debug("Creating directory %s", path)
            os.mkdir(path)

    def _setup_server(self, no_agent_log):
        # set the custom config before starting the server
        config.Config.get("database", "name", "inmanta")

        state_dir = os.path.join(self._data_path, "state")
        self._ensure_dir(state_dir)
        config.Config.set("config", "state-dir", state_dir)

        log_dir = os.path.join(self._data_path, "logs")
        self._ensure_dir(log_dir)
        config.Config.set("config", "log-dir", log_dir)

        self._server_port = PORT_START + random.randint(0, 2000)
        assert self._server_port != self._mongoport

        config.Config.set("server_rest_transport", "port", str(self._server_port))
        config.Config.set("agent_rest_transport", "port", str(self._server_port))
        config.Config.set("compiler_rest_transport", "port", str(self._server_port))
        config.Config.set("client_rest_transport", "port", str(self._server_port))
        config.Config.set("cmdline_rest_transport", "port", str(self._server_port))

        # start the server
        self._server = server.Server(database_host="localhost", database_port=self._mongoport, io_loop=self._io_loop,
                                     agent_no_log=no_agent_log)
        self._server.start()
        LOGGER.debug("Started server on port %d", self._server_port)

        return True

    def _setup_mongodb(self):
        # start a local mongodb on a random port
        if self._mongoport == 0:
            self._mongoport = PORT_START + random.randint(0, 2000)
            mongo_dir = os.path.join(self._data_path, "mongo")
            self._mongobox = mongobox.MongoBox(db_path=mongo_dir, port=self._mongoport)
            LOGGER.debug("Starting mongodb on port %d", self._mongoport)
            if not self._mongobox.start():
                LOGGER.error("Unable to start mongodb instance on port %d and data directory %s", self._mongoport, mongo_dir)
                return False

        return True

    @gen.coroutine
    def _create_project(self, project_name):
        LOGGER.debug("Creating project %s", project_name)
        result = yield self._client.create_project(project_name)
        if result.code != 200:
            LOGGER.error("Unable to create project %s", project_name)
            return False

        return result.result["project"]["id"]

    @gen.coroutine
    def _create_environment(self, project_id, environment_name):
        LOGGER.debug("Creating environment %s in project %s", environment_name, project_id)
        result = yield self._client.create_environment(project_id=project_id, name=environment_name)
        if result.code != 200:
            LOGGER.error("Unable to create environment %s", environment_name)
            return False

        return result.result["environment"]["id"]

    @gen.coroutine
    def _latest_version(self, environment_id):
        result = yield self._client.list_versions(tid=environment_id)
        if result.code != 200:
            LOGGER.error("Unable to get all version of environment %s", environment_id)
            return None

        if "versions" in result.result and len(result.result["versions"]) > 0:
            versions = [x["version"] for x in result.result["versions"]]
            sorted(versions)
            return versions[0]

        return None

    @gen.coroutine
    def setup_project(self):
        """
            Set up the configured project and environment on the embedded server
        """
        self._client = protocol.Client("client")

        # get config
        project_name = cfg_prj.get()
        if project_name is None:
            LOGGER.error("The name of the project should be configured for an all-in-one deploy")
            return False

        environment_name = cfg_env.get()
        if environment_name is None:
            LOGGER.error("The name of the environment in the project should be configured for an all-in-one deploy")
            return False

        # wait and check to see if the server is up
        tries = 0
        while tries < MAX_TRIES:
            try:
                yield self._client.list_projects()
                break
            except Exception:
                tries += 1

        # get project id
        projects = yield self._client.list_projects()
        if projects.code != 200:
            LOGGER.error("Unable to retrieve project listing from the server")
            return False

        project_id = None
        for project in projects.result["projects"]:
            if project_name == project["name"]:
                project_id = project["id"]
                break

        if project_id is None:
            project_id = yield self._create_project(project_name)
            if not project_id:
                return False

        # get or create the environment
        environments = yield self._client.list_environments()
        if environments.code != 200:
            LOGGER.error("Unable to retrieve environments from server")
            return False

        for env in environments.result["environments"]:
            if project_id == env["project"] and environment_name == env["name"]:
                self._environment_id = env["id"]
                break

        if self._environment_id is None:
            self._environment_id = yield self._create_environment(project_id, environment_name)
            if not self._environment_id:
                return False

        return True

    @gen.coroutine
    def _wait(self, condition, name=""):
        tries = 0
        while tries < MAX_TRIES and not condition():
            tries += 1
            yield gen.sleep(0.5)

        if not condition():
            raise Exception("Timeout while waiting for %s" % name)

    @gen.coroutine
    def setup_agent(self):
        yield self._wait(lambda: self._environment_id is not None, "environment setup")

        # start the agent
        self._agent = agent.Agent(self._io_loop, env_id=self._environment_id, code_loader=True, poolsize=5)
        self._agent.start()

        self._agent_ready = True
        return True

    def setup_server(self, no_agent_log):
        """
            Run inmanta locally
        """
        # create local storage
        project = module.Project.get()
        self._data_path = os.path.join(project.project_path, "data", "deploy")
        LOGGER.debug("Storing state data in %s", self._data_path)
        self._ensure_dir(os.path.join(project.project_path, "data"))
        self._ensure_dir(self._data_path)

        if not self._setup_mongodb():
            return False

        if not self._setup_server(no_agent_log):
            return False

        return True

    @gen.coroutine
    def export(self, dry_run, agent_map):
        """
            Export a version to the embedded server
        """
        inmanta_path = [sys.executable, "-m", "inmanta.app"]

        cmd = inmanta_path + ["-vvv", "export", "-e", str(self._environment_id), "--server_address", "localhost",
                              "--server_port", str(self._server_port)]

        sub_process = process.Subprocess(cmd, stdout=process.Subprocess.STREAM, stderr=process.Subprocess.STREAM)

        log_out, log_err, returncode = yield [sub_process.stdout.read_until_close(),
                                              sub_process.stderr.read_until_close(),
                                              sub_process.wait_for_exit(raise_error=False)]

        sub_process.uninitialize()
        if returncode > 0:
            print("An error occurred while compiling the model:")
            if len(log_out) > 0:
                print(log_out.decode())
            if len(log_err) > 0:
                print(log_err.decode())

            return False

        LOGGER.info("Export of model complete")
        yield self.deploy(dry_run, agent_map)
        return True

    @gen.coroutine
    def get_agents_of_for_model(self, version):
        version_result = yield self._client.get_version(tid=self._environment_id, id=version)
        if version_result.code != 200:
            LOGGER.error("Unable to get version %d of environment %s", version, self._environment_id)
            return []

        return [x["agent"] for x in version_result.result["resources"]]

    @gen.coroutine
    def deploy(self, dry_run, agent_map):
        version = yield self._latest_version(self._environment_id)
        LOGGER.info("Latest version for created environment is %s", version)
        if version is None:
            return

        # Update the agentmap to autostart all agents
        agents = yield self.get_agents_of_for_model(version)
        LOGGER.debug("Agent(s) %s defined, adding them to autostart agent map", ", ".join(agents))
        result = yield self._client.get_setting(tid=self._environment_id, id=data.AUTOSTART_AGENT_MAP)

        if result.code == 200:
            current_map = result.result["value"]
        else:
            current_map = {}

        parts = agent_map.split(",")
        for part in parts:
            split = re.split("=", part.strip(), 1)
            if len(split) == 2:
                current_map[split[0].strip()] = split[1].strip()

        for agent_name in agents:
            if agent_name not in agent_map:
                current_map[agent_name] = "local:"

        yield self._client.set_setting(tid=self._environment_id, id=data.AUTOSTART_AGENT_MAP, value=current_map)

        # release the version!
        if not dry_run:
            yield self._client.release_version(tid=self._environment_id, id=version, push=True)
            yield self.progress_deploy_report(version)

        else:
            result = yield self._client.dryrun_request(tid=self._environment_id, id=version)
            dryrun_id = result.result["dryrun"]["id"]
            yield self.progress_dryrun_report(dryrun_id)

    @gen.coroutine
    def _get_deploy_stats(self, version):
        version_result = yield self._client.get_version(tid=self._environment_id, id=version)
        if version_result.code != 200:
            LOGGER.error("Unable to get version %d of environment %s", version, self._environment_id)
            return []

        total = 0
        deployed = 0
        ready = {}

        for res in version_result.result["resources"]:
            total += 1
            if res["status"] != const.ResourceState.available.name:
                deployed += 1
                ready[res["id"]] = res["status"]

        return total, deployed, ready

    @gen.coroutine
    def progress_deploy_report(self, version):
        print("Starting deploy")
        current_ready = set()
        total = 0
        deployed = -1
        while total > deployed:
            total, deployed, ready = yield self._get_deploy_stats(version)

            new = ready.keys() - current_ready
            current_ready = ready

            # if we already printed progress, move cursor one line up
            if deployed >= 0:
                sys.stdout.write('\033[1A')
                sys.stdout.flush()

            for res in new:
                print("%s - %s" % (res, ready[res]))

            print("[%d / %d]" % (deployed, total))
            yield gen.sleep(1)

        print("Deploy ready")
        raise FinishedException()

    @gen.coroutine
    def _get_dryrun_status(self, dryrun_id):
        result = yield self._client.dryrun_report(self._environment_id, dryrun_id)

        if result.code != 200:
            raise Exception("Unable to get dryrun report")

        data = result.result["dryrun"]
        return data["total"], data["todo"], data["resources"]

    @gen.coroutine
    def progress_dryrun_report(self, dryrun_id):
        print("Starting dryrun")

        current_ready = set()
        total = 0
        todo = 1
        while todo > 0:
            # if we already printed progress, move cursor one line up
            if len(current_ready) > 0:
                sys.stdout.write('\033[1A')
                sys.stdout.flush()

            total, todo, ready = yield self._get_dryrun_status(dryrun_id)

            new = ready.keys() - current_ready
            current_ready = ready

            for res in new:
                changes = ready[res]["changes"]
                if len(changes) == 0:
                    print("%s - no changes" % res)
                else:
                    print("%s:" % res)
                    for field, values in changes.items():
                        if field == "hash":
                            diff_result = yield self._client.diff(a=values[0], b=values[1])
                            if diff_result.code == 200:
                                print("  - content:")
                                diff_value = diff_result.result
                                print("    " + "    ".join(diff_value["diff"]))
                        else:
                            print("  - %s:" % field)
                            print("    from: %s" % values[0])
                            print("    to:   %s" % values[1])

                        print("")

            print("[%d / %d]" % (total - todo, total))
            yield gen.sleep(1)

        raise FinishedException()

    @gen.coroutine
    def do_deploy(self, dry_run, agent_map):
        yield self.setup_project()
        yield self.export(dry_run=dry_run, agent_map=agent_map)

    def run(self, options, only_setup=False):
        if options.agent is not None:
            config.Config.set("config", "agent", options.agent)
        self.setup_server(options.no_agent_log)

        if only_setup:
            return

        def handle_result(x):
            if x.exception() is not None or not x.result():
                self._io_loop.stop()
                self.stop()
                sys.exit(1)

        self._io_loop.add_future(self.do_deploy(dry_run=options.dryrun, agent_map=options.map), handle_result)

    def stop(self):
        if self._agent is not None:
            self._agent.stop()

        if self._server is not None:
            self._server.stop()

        if self._mongobox is not None:
            self._mongobox.stop()
