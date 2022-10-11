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
import argparse
import logging
import os
import socket
import subprocess
import sys
import time
from typing import Dict, List, Optional, Set, Tuple

from inmanta import config, const, module, postgresproc, protocol
from inmanta.config import Config
from inmanta.types import JsonType
from inmanta.util import get_free_tcp_port

LOGGER = logging.getLogger(__name__)
MAX_TRIES = 25


cfg_prj = config.Option("deploy", "project", "deploy", "The project name to use in the deploy", config.is_str_opt)
cfg_env = config.Option("deploy", "environment", "deploy", "The environment name to use in the deploy", config.is_str_opt)


class FinishedException(Exception):
    """
    This exception is raised when the deploy is ready
    """


class Deploy(object):
    _data_path: str
    _project_path: str
    _server_proc: subprocess.Popen
    _postgresproc: postgresproc.PostgresProc
    _client: protocol.SyncClient
    _environment_id: str

    def __init__(self, options: argparse.Namespace, postgresport: int = 0) -> None:
        self._postgresport = postgresport
        self._server_port = 0
        self._options = options

        loud_logger = logging.getLogger("inmanta.protocol")
        loud_logger.propagate = False

        loud_logger = logging.getLogger("tornado")
        loud_logger.propagate = False

    def _check_result(self, result: protocol.Result, fatal: bool = True) -> protocol.Result:
        """Check the result of a call protocol call. If the result is not 200, issue an error"""
        if result.code != 200:
            msg = f"Server request failed with code {result.code} and result {result.result}"
            LOGGER.error(msg)

            if fatal:
                raise Exception(msg)

        return result

    def _ensure_dir(self, path: str) -> None:
        if not os.path.exists(path):
            LOGGER.debug("Creating directory %s", path)
            os.mkdir(path)

    def setup_server(self) -> bool:
        state_dir = os.path.join(self._data_path, "state")
        self._ensure_dir(state_dir)

        log_dir = os.path.join(self._data_path, "logs")
        self._ensure_dir(log_dir)

        self._server_port = int(get_free_tcp_port())
        assert self._server_port != self._postgresport

        config.Config.set("client_rest_transport", "port", str(self._server_port))

        vars_in_configfile = {
            "state_dir": state_dir,
            "log_dir": log_dir,
            "server_port": self._server_port,
            "postgres_port": self._postgresport,
        }
        config_file = (
            """
[database]
name=postgres
port=%(postgres_port)s
host=localhost
username=postgres

[config]
state-dir=%(state_dir)s
log-dir=%(log_dir)s

[server]
bind-port=%(server_port)s
bind-address=127.0.0.1

[agent_rest_transport]
port=%(server_port)s
host=localhost

[compiler_rest_transport]
port=%(server_port)s
host=localhost

[client_rest_transport]
port=%(server_port)s
host=localhost

[cmdline_rest_transport]
port=%(server_port)s
host=localhost
"""
            % vars_in_configfile
        )

        server_config = os.path.join(self._data_path, "server.cfg")
        with open(server_config, "w+", encoding="utf-8") as fd:
            fd.write(config_file)

        log_file = os.path.join(log_dir, "inmanta.log")
        args = [
            sys.executable,
            "-m",
            "inmanta.app",
            "-vvv",
            "-c",
            server_config,
            "--config-dir",
            Config._config_dir if Config._config_dir is not None else "",
            "--log-file",
            log_file,
            "server",
        ]

        self._server_proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        LOGGER.debug("Started server on port %d", self._server_port)

        while self._server_proc.poll() is None:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                try:
                    s.connect(("localhost", int(self._server_port)))
                    return True
                except (IOError, socket.error):
                    time.sleep(0.25)
            finally:
                s.close()

        return False

    def setup_postgresql(self) -> bool:
        # start a local postgresql server on a random port
        if self._postgresport == 0:
            self._postgresport = int(get_free_tcp_port())
            postgres_dir = os.path.join(self._data_path, "postgres")
            self._postgresproc = postgresproc.PostgresProc(port=self._postgresport, db_path=postgres_dir)
            LOGGER.debug("Starting postgresql on port %d", self._postgresport)
            if not self._postgresproc.start():
                LOGGER.error(
                    "Unable to start postgresql instance on port %d and data directory %s", self._postgresport, postgres_dir
                )
                return False

        return True

    def _create_project(self, project_name: str) -> Optional[str]:
        LOGGER.debug("Creating project %s", project_name)
        result = self._client.create_project(project_name)
        if result.code != 200:
            LOGGER.error("Unable to create project %s", project_name)
            return None

        return result.result["project"]["id"]

    def _create_environment(self, project_id: str, environment_name: str) -> Optional[str]:
        LOGGER.debug("Creating environment %s in project %s", environment_name, project_id)
        result = self._client.create_environment(project_id=project_id, name=environment_name)
        if result.code != 200:
            LOGGER.error("Unable to create environment %s", environment_name)
            return None

        env_id: str = result.result["environment"]["id"]

        self._check_result(self._client.set_setting(env_id, "autostart_agent_deploy_splay_time", 0))
        self._check_result(self._client.set_setting(env_id, "autostart_agent_deploy_interval", 0))
        self._check_result(self._client.set_setting(env_id, "autostart_agent_repair_splay_time", 0))
        self._check_result(self._client.set_setting(env_id, "autostart_agent_repair_interval", 600))

        return env_id

    def _latest_version(self, environment_id: str) -> Optional[int]:
        result = self._client.list_versions(tid=environment_id)
        if result.code != 200:
            LOGGER.error("Unable to get all version of environment %s", environment_id)
            return None

        if "versions" in result.result and len(result.result["versions"]) > 0:
            versions: List[int] = [x["version"] for x in result.result["versions"]]
            sorted(versions)
            return versions[0]

        return None

    def setup_project(self) -> bool:
        """
        Set up the configured project and environment on the embedded server
        """
        self._client = protocol.SyncClient("client")

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
                self._client.list_projects()
                break
            except Exception:
                tries += 1

        # get project id
        projects = self._client.list_projects()
        if projects.code != 200:
            LOGGER.error("Unable to retrieve project listing from the server")
            return False

        project_id = None
        for project in projects.result["projects"]:
            if project_name == project["name"]:
                project_id = project["id"]
                break

        if project_id is None:
            project_id = self._create_project(project_name)
            if not project_id:
                return False

        # get or create the environment
        environments = self._client.list_environments()
        if environments.code != 200:
            LOGGER.error("Unable to retrieve environments from server")
            return False

        env_id = None
        for env in environments.result["environments"]:
            if project_id == env["project"] and environment_name == env["name"]:
                env_id = env["id"]
                break

        if env_id is None:
            env_id = self._create_environment(project_id, environment_name)
            if not env_id:
                return False

        self._environment_id = env_id

        # link the project into the server environment
        server_env = os.path.join(self._data_path, "state", "server", "environments", self._environment_id)
        full_path = os.path.abspath(self._project_path)
        if not os.path.islink(server_env) or os.readlink(server_env) != full_path:
            if os.path.exists(server_env):
                os.unlink(server_env)
            os.symlink(full_path, server_env)

        return True

    def setup(self) -> bool:
        """
        Run inmanta locally
        """
        # create local storage
        project = module.Project.get()
        self._project_path = project.project_path
        self._data_path = os.path.join(project.project_path, "data", "deploy")
        LOGGER.debug("Storing state data in %s", self._data_path)
        self._ensure_dir(os.path.join(project.project_path, "data"))
        self._ensure_dir(self._data_path)

        if not self.setup_postgresql():
            return False

        if not self.setup_server():
            return False

        if not self.setup_project():
            LOGGER.error("Failed to setup project")
            return False

        return True

    def export(self) -> bool:
        """
        Export a version to the embedded server
        """
        inmanta_path = [sys.executable, "-m", "inmanta.app"]

        cmd = inmanta_path + [
            "--config-dir",
            Config._config_dir if Config._config_dir is not None else "",
            "-vvv",
            "export",
            "-e",
            str(self._environment_id),
            "--server_address",
            "localhost",
            "--server_port",
            str(self._server_port),
        ]

        sub_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        log_out, log_err = sub_process.communicate()

        if sub_process.returncode > 0:
            print("An error occurred while compiling the model:")
            if len(log_out) > 0:
                print(log_out.decode())
            if len(log_err) > 0:
                print(log_err.decode())

            return False

        LOGGER.info("Export of model complete")
        return True

    def deploy(self, dry_run: bool, report: bool = True) -> None:
        version = self._latest_version(self._environment_id)
        LOGGER.info("Latest version for created environment is %s", version)
        if version is None:
            return

        # release the version!
        if not dry_run:
            self._check_result(
                self._client.release_version(
                    tid=self._environment_id,
                    id=version,
                    push=True,
                    agent_trigger_method=const.AgentTriggerMethod.push_full_deploy,
                )
            )
            if report:
                self.progress_deploy_report(version)

        else:
            result = self._check_result(self._client.dryrun_request(tid=self._environment_id, id=version))
            dryrun_id = result.result["dryrun"]["id"]
            if report:
                self.progress_dryrun_report(dryrun_id)

    def _get_deploy_stats(self, version: int) -> Tuple[int, int, Dict[str, str]]:
        version_result = self._client.get_version(tid=self._environment_id, id=version)
        if version_result.code != 200:
            LOGGER.error("Unable to get version %d of environment %s", version, self._environment_id)
            return (0, 0, {})

        total = 0
        deployed = 0
        ready = {}

        for res in version_result.result["resources"]:
            total += 1
            if res["status"] not in [x.name for x in const.TRANSIENT_STATES]:
                deployed += 1
                ready[res["id"]] = res["status"]

        return total, deployed, ready

    def progress_deploy_report(self, version: int) -> None:
        print("Starting deploy")
        current_ready: Set[str] = set()
        total = 0
        deployed = -1
        while total > deployed:
            total, deployed, ready = self._get_deploy_stats(version)

            ready_keys = set(ready.keys())
            new = ready_keys - current_ready
            current_ready = ready_keys

            # if we already printed progress, move cursor one line up
            if deployed >= 0:
                sys.stdout.write("\033[1A")
                sys.stdout.flush()

            for res in new:
                print("%s - %s" % (res, ready[res]))

            print("[%d / %d]" % (deployed, total))
            time.sleep(1)

        print("Deploy ready")

    def _get_dryrun_status(self, dryrun_id: str) -> Tuple[int, int, JsonType]:
        result = self._client.dryrun_report(self._environment_id, dryrun_id)

        if result.code != 200:
            raise Exception("Unable to get dryrun report")

        data = result.result["dryrun"]
        return data["total"], data["todo"], data["resources"]

    def progress_dryrun_report(self, dryrun_id: str) -> None:
        print("Starting dryrun")

        current_ready: Set[str] = set()
        todo = 1
        while todo > 0:
            # if we already printed progress, move cursor one line up
            if len(current_ready) > 0:
                sys.stdout.write("\033[1A")
                sys.stdout.flush()

            total, todo, ready = self._get_dryrun_status(dryrun_id)

            ready_keys: Set[str] = set(ready.keys())
            new = ready_keys - current_ready
            current_ready = ready_keys

            for res in new:
                changes: Dict[str, Tuple[str, str]] = ready[res]["changes"]
                if len(changes) == 0:
                    print("%s - no changes" % res)
                else:
                    print("%s:" % res)
                    for field, values in changes.items():
                        if field == "hash":
                            diff_result = self._client.diff(a=values[0], b=values[1])
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
            time.sleep(1)

        raise FinishedException()

    def run(self) -> None:
        self.export()
        self.deploy(dry_run=self._options.dryrun)

    def stop(self) -> None:
        loud_logger = logging.getLogger("inmanta.protocol")
        loud_logger.propagate = True

        loud_logger = logging.getLogger("tornado")
        loud_logger.propagate = True

        if hasattr(self, "_server_proc"):
            self._server_proc.terminate()

        if hasattr(self, "_postgresproc"):
            self._postgresproc.stop()
