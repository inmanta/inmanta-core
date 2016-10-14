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
import os
import logging
import random

from mongobox import mongobox
from tornado import gen
from inmanta import module, config, server, agent, protocol


LOGGER = logging.getLogger(__name__)
PORT_START = 40000
MAX_TRIES = 25


class Deploy(object):
    def __init__(self, io_loop):
        self._mongobox = None
        self._mongoport = 0
        self._server_port = 0
        self._data_path = None
        self._server = None
        self._agent = None
        self._client = None

        self._environment_id = None

        self._io_loop = io_loop

    def _ensure_dir(self, path):
        if not os.path.exists(path):
            LOGGER.debug("Creating directory %s", path)
            os.mkdir(path)

    def _setup_server(self):
        # set the custom config before starting the server
        config.Config.load_config()

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
        self._server = server.Server(database_host="localhost", database_port=self._mongoport, io_loop=self._io_loop)
        self._server.start()
        LOGGER.debug("Started server on port %d", self._server_port)

        return True

    def _setup_mongodb(self):
        # start a local mongodb on a random port
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
    def setup_project(self):
        """
            Set up the configured project and environment on the embedded server
        """
        self._client = protocol.Client("client")

        # get config
        project_name = config.Config.get("deploy", "project", None)
        if project_name is None:
            LOGGER.error("The name of the project should be configured for an all-in-one deploy")
            return False

        environment_name = config.Config.get("deploy", "environment", None)
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
    def setup_agent(self):
        tries = 0
        while tries < MAX_TRIES and self._environment_id is None:
            tries += 1
            yield gen.sleep(0.5)

        # start the agent
        self._agent = agent.Agent(self._io_loop, env_id=self._environment_id, code_loader=False)
        self._agent.start()

        return True

    def setup_server(self):
        """
            Run inmanta locally
        """
        # create local storage
        project = module.Project.get()
        self._data_path = os.path.join(project.project_path, "data", "deploy")
        LOGGER.debug("Storing state data in %s", self._data_path)
        self._ensure_dir(self._data_path)

        if not self._setup_mongodb():
            return False

        if not self._setup_server():
            return False

        return True

    def stop(self):
        if self._agent is not None:
            self._agent.stop()

        if self._server is not None:
            self._server.stop()

        if self._mongobox is not None:
            self._mongobox.stop()
