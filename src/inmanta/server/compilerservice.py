"""
    Copyright 2019 Inmanta

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
import datetime
import json
import logging
import os
import subprocess
import tempfile
import uuid
from typing import List, Dict, Union, Any, Optional
import re
from collections import defaultdict
from asyncio import CancelledError


import sys

import dateutil

from inmanta import protocol, data, config, server
from inmanta.protocol import methods, encode_token
from inmanta.server import SLICE_DATABASE, SLICE_COMPILER, SLICE_TRANSPORT, SLICE_SERVER
from inmanta.server.protocol import ServerSlice
from inmanta.server.server import Server
from inmanta.types import Apireturn, JsonType

from inmanta.server import config as opt


LOGGER = logging.getLogger(__name__)


class CompilerSerice(ServerSlice):
    def __init__(self) -> None:
        super(CompilerSerice, self).__init__(SLICE_COMPILER)
        self._recompiles: Dict[uuid.UUID, Union[None, CompilerSerice, datetime.datetime]] = defaultdict(lambda: None)

    def get_dependencies(self) -> List[str]:
        return [SLICE_DATABASE]

    def get_dependened_by(self) -> List[str]:
        return [SLICE_TRANSPORT]

    async def prestart(self, server: server.protocol.Server) -> None:
        await super(CompilerSerice, self).prestart(server)
        preserver = server.get_slice(SLICE_SERVER)
        assert isinstance(preserver, Server)
        self._server: Server = preserver
        self._server_storage: Dict[str, str] = self._server._server_storage

    @protocol.handle(methods.is_compiling, environment_id="id")
    async def is_compiling(self, environment_id: uuid.UUID) -> Apireturn:
        if self._recompiles[environment_id] is self:
            return 200

        return 204

    async def _async_recompile(self, env: data.Environment, update_repo: bool, metadata: JsonType = {}) -> None:
        """
            Recompile an environment in a different thread and taking wait time into account.
        """
        server_compile: bool = await env.get(data.SERVER_COMPILE)
        if not server_compile:
            LOGGER.info("Skipping compile because server compile not enabled for this environment.")
            return

        last_recompile = self._recompiles[env.id]
        wait_time = opt.server_autrecompile_wait.get()
        if last_recompile is self:
            LOGGER.info("Already recompiling")
            return

        if last_recompile is None:
            wait: float = 0
            LOGGER.info("First recompile")
        else:
            assert isinstance(last_recompile, datetime.datetime)
            wait = max(0, wait_time - (datetime.datetime.now() - last_recompile).total_seconds())
            LOGGER.info("Last recompile longer than %s ago (last was at %s)", wait_time, last_recompile)

        self._recompiles[env.id] = self
        self.add_background_task(self._recompile_environment(env.id, update_repo, wait, metadata))

    async def _run_compile_stage(self, name: str, cmd: List[str], cwd: str, **kwargs: Any) -> data.Report:
        start = datetime.datetime.now()

        try:
            out = tempfile.NamedTemporaryFile()
            err = tempfile.NamedTemporaryFile()
            sub_process = await asyncio.create_subprocess_exec(cmd[0], *cmd[1:], stdout=out, stderr=err, cwd=cwd, **kwargs)

            returncode = await sub_process.wait()

            out.seek(0)
            err.seek(0)

            stop = datetime.datetime.now()
            return data.Report(
                started=start,
                completed=stop,
                name=name,
                command=" ".join(cmd),
                errstream=err.read().decode(),
                outstream=out.read().decode(),
                returncode=returncode,
            )

        finally:
            out.close()
            err.close()

    async def _recompile_environment(
        self, environment_id: uuid.UUID, update_repo: bool = False, wait=0, metadata: JsonType = {}
    ) -> None:
        """
            Recompile an environment
        """
        if wait > 0:
            await asyncio.sleep(wait)

        env = await data.Environment.get_by_id(environment_id)
        if env is None:
            LOGGER.error("Environment %s does not exist.", environment_id)
            return

        requested = datetime.datetime.now()
        stages = []

        try:
            inmanta_path = [sys.executable, "-m", "inmanta.app"]
            project_dir = os.path.join(self._server_storage["environments"], str(environment_id))

            if not os.path.exists(project_dir):
                LOGGER.info("Creating project directory for environment %s at %s", environment_id, project_dir)
                os.mkdir(project_dir)

            if not env.repo_url:
                if not os.path.exists(os.path.join(project_dir, ".git")):
                    LOGGER.warning("Project not found and repository not set %s", project_dir)
            else:
                # checkout repo
                if not os.path.exists(os.path.join(project_dir, ".git")):
                    LOGGER.info("Cloning repository into environment directory %s", project_dir)
                    result = await self._run_compile_stage(
                        "Cloning repository", ["git", "clone", env.repo_url, "."], project_dir
                    )
                    stages.append(result)
                    if result.returncode > 0:
                        return

                elif update_repo:
                    LOGGER.info("Fetching changes from repo %s", env.repo_url)
                    result = await self._run_compile_stage("Fetching changes", ["git", "fetch", env.repo_url], project_dir)
                    stages.append(result)
                if env.repo_branch:
                    # verify if branch is correct
                    LOGGER.debug("Verifying correct branch")

                    sub_process = await asyncio.create_subprocess_exec(
                        "git", "branch", stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=project_dir
                    )

                    out, _, _ = await asyncio.gather(
                        sub_process.stdout.read_until_close(),
                        sub_process.stderr.read_until_close(),
                        sub_process.wait_for_exit(raise_error=False),
                    )

                    o = re.search(r"\* ([^\s]+)$", out.decode(), re.MULTILINE)
                    if o is not None and env.repo_branch != o.group(1):
                        LOGGER.info("Repository is at %s branch, switching to %s", o.group(1), env.repo_branch)
                        result = await self._run_compile_stage(
                            "switching branch", ["git", "checkout", env.repo_branch], project_dir
                        )
                        stages.append(result)

                if update_repo:
                    result = await self._run_compile_stage("Pulling updates", ["git", "pull"], project_dir)
                    stages.append(result)
                    LOGGER.info("Installing and updating modules")
                    result = await self._run_compile_stage(
                        "Installing modules", inmanta_path + ["modules", "install"], project_dir, env=os.environ.copy()
                    )
                    stages.append(result)
                    result = await self._run_compile_stage(
                        "Updating modules", inmanta_path + ["modules", "update"], project_dir, env=os.environ.copy()
                    )
                    stages.append(result)

            LOGGER.info("Recompiling configuration model")
            server_address = opt.server_address.get()
            server_port = opt.transport_port.get()
            cmd = inmanta_path + [
                "-vvv",
                "export",
                "-e",
                str(environment_id),
                "--server_address",
                server_address,
                "--server_port",
                str(server_port),
                "--metadata",
                json.dumps(metadata),
            ]
            if config.Config.get("server", "auth", False):
                token = encode_token(["compiler", "api"], str(environment_id))
                cmd.append("--token")
                cmd.append(token)

            if opt.server_ssl_cert.get() is not None:
                cmd.append("--ssl")

            if opt.server_ssl_ca_cert.get() is not None:
                cmd.append("--ssl-ca-cert")
                cmd.append(opt.server_ssl_ca_cert.get())

            result = await self._run_compile_stage("Recompiling configuration model", cmd, project_dir, env=os.environ.copy())

            stages.append(result)
        except CancelledError:
            # This compile was cancelled. Catch it here otherwise a warning will be printed in the logs because of an
            # unhandled exception in a backgrounded coroutine.
            pass

        except Exception:
            LOGGER.exception("An error occured while recompiling")

        finally:
            try:
                end = datetime.datetime.now()
                self._recompiles[environment_id] = end

                comp = data.Compile(environment=environment_id, started=requested, completed=end)

                for stage in stages:
                    stage.compile = comp.id

                await comp.insert()
                await data.Report.insert_many(stages)
            except Exception as exc:
                LOGGER.warning("An exception occurred that should not happen.", exc_info=exc)

    @protocol.handle(methods.get_reports, env="tid")
    async def get_reports(
        self, env: data.Environment, start: Optional[str] = None, end: Optional[str] = None, limit: Optional[int] = None
    ) -> Apireturn:
        argscount = len([x for x in [start, end, limit] if x is not None])
        if argscount == 3:
            return 500, {"message": "Limit, start and end can not be set together"}
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        start_time = None
        end_time = None
        if start is not None:
            start_time = dateutil.parser.parse(start)
        if end is not None:
            end_time = dateutil.parser.parse(end)
        models = await data.Compile.get_reports(env.id, limit, start_time, end_time)

        return 200, {"reports": models}

    @protocol.handle(methods.get_report, compile_id="id")
    async def get_report(self, compile_id: uuid.UUID) -> Apireturn:
        report = await data.Compile.get_report(compile_id)

        if report is None:
            return 404

        return 200, {"report": report}
