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
import abc
import asyncio
import datetime
import json
import logging
import os
import re
import subprocess
import sys
import traceback
import uuid
from asyncio import CancelledError, Task
from logging import Logger
from tempfile import NamedTemporaryFile
from typing import Dict, List, Optional, Tuple, cast

import dateutil
import dateutil.parser

from inmanta import config, const, data, protocol, server
from inmanta.protocol import encode_token, methods
from inmanta.server import SLICE_COMPILER, SLICE_DATABASE, SLICE_TRANSPORT
from inmanta.server import config as opt
from inmanta.server.protocol import ServerSlice
from inmanta.types import Apireturn, ArgumentTypes, JsonType, Warnings
from inmanta.util import ensure_directory_exist

RETURNCODE_INTERNAL_ERROR = -1

LOGGER: Logger = logging.getLogger(__name__)
COMPILER_LOGGER: Logger = LOGGER.getChild("report")


class CompileStateListener(object):
    @abc.abstractmethod
    async def compile_done(self, compile: data.Compile) -> None:
        """Receive notification of all completed compiles

        1- Notifications are delivered at least once (retry until all listeners have returned or raise an exception other
        than CancelledError)
        2- Notification are delivered out-of-band (i.e. the next compile can already start, multiple notifications can be in
        flight at any given time, out-of-order delivery is possible but highly unlikely)
        3- Notification are cancelled upon shutdown
        """
        pass


class CompileRun(object):
    """Class encapsulating running the compiler."""

    def __init__(self, request: data.Compile, project_dir: str) -> None:
        self.request = request
        self.stage: Optional[data.Report] = None
        self._project_dir = project_dir
        # When set, used to collect tail of std out
        self.tail_stdout: Optional[str] = None
        self.version: Optional[int] = None

    async def _error(self, message: str) -> None:
        assert self.stage is not None
        LOGGER.error(message)
        await self.stage.update_streams(err=message + "\n")

    async def _info(self, message: str) -> None:
        assert self.stage is not None
        LOGGER.info(message)
        await self.stage.update_streams(out=message + "\n")

    async def _warning(self, message: str) -> None:
        assert self.stage is not None
        LOGGER.warning(message)
        await self.stage.update_streams(out=message + "\n")

    async def _start_stage(self, name: str, command: str) -> None:
        LOGGER.log(const.LOG_LEVEL_TRACE, "starting stage %s for %s in %s", name, self.request.id, self.request.environment)
        start = datetime.datetime.now()
        stage = data.Report(compile=self.request.id, started=start, name=name, command=command)
        await stage.insert()
        self.stage = stage

    async def _end_stage(self, returncode: int) -> data.Report:
        assert self.stage is not None
        LOGGER.log(
            const.LOG_LEVEL_TRACE, "ending stage %s for %s in %s", self.stage.name, self.request.id, self.request.environment
        )
        stage = self.stage
        end = datetime.datetime.now()
        await stage.update_fields(completed=end, returncode=returncode)
        self.stage = None
        return stage

    def _add_to_tail(self, part: str) -> None:
        if self.tail_stdout is not None:
            self.tail_stdout += part
            self.tail_stdout = self.tail_stdout[-1024:]

    async def drain_out(self, stream: asyncio.StreamReader) -> None:
        assert self.stage is not None
        while not stream.at_eof():
            part = (await stream.read(8192)).decode()
            self._add_to_tail(part)
            COMPILER_LOGGER.log(const.LOG_LEVEL_TRACE, "%s %s Out:", self.request.id, part)
            await self.stage.update_streams(out=part)

    async def drain_err(self, stream: asyncio.StreamReader) -> None:
        assert self.stage is not None
        while not stream.at_eof():
            part = (await stream.read(8192)).decode()
            COMPILER_LOGGER.log(const.LOG_LEVEL_TRACE, "%s %s Err:", self.request.id, part)
            await self.stage.update_streams(err=part)

    async def drain(self, sub_process: asyncio.subprocess.Process) -> int:
        # pipe, so stream is actual, not optional
        out = cast(asyncio.StreamReader, sub_process.stdout)
        err = cast(asyncio.StreamReader, sub_process.stderr)
        ret, _, _ = await asyncio.gather(sub_process.wait(), self.drain_out(out), self.drain_err(err))
        return ret

    async def get_branch(self) -> Optional[str]:
        sub_process = await asyncio.create_subprocess_exec(
            "git", "branch", stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=self._project_dir
        )

        out, err = await sub_process.communicate()

        if sub_process.returncode != 0:
            return None

        o = re.search(r"\* ([^\s]+)$", out.decode(), re.MULTILINE)
        if o is not None:
            return o.group(1)
        else:
            return None

    async def _run_compile_stage(self, name: str, cmd: List[str], cwd: str, env: Dict[str, str] = {}) -> data.Report:
        await self._start_stage(name, " ".join(cmd))

        try:
            env_all = os.environ.copy()
            if env is not None:
                env_all.update(env)

            sub_process = await asyncio.create_subprocess_exec(
                cmd[0], *cmd[1:], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd, env=env
            )

            returncode = await self.drain(sub_process)

            return await self._end_stage(returncode)
        except Exception as e:
            await self._error("".join(traceback.format_exception(type(e), e, e.__traceback__)))
            return await self._end_stage(RETURNCODE_INTERNAL_ERROR)

    async def run(self) -> bool:
        success = False
        now = datetime.datetime.now()
        await self.request.update_fields(started=now)

        try:
            await self._start_stage("Init", "")

            environment_id = self.request.environment
            project_dir = self._project_dir

            env = await data.Environment.get_by_id(environment_id)

            env_string = ", ".join([f"{k}='{v}'" for k, v in self.request.environment_variables.items()])
            await self.stage.update_streams(out=f"Using extra environment variables during compile {env_string}\n")

            if env is None:
                await self._error("Environment %s does not exist." % environment_id)
                await self._end_stage(-1)
                return False

            inmanta_path = [sys.executable, "-m", "inmanta.app"]

            if not os.path.exists(project_dir):
                await self._info("Creating project directory for environment %s at %s" % (environment_id, project_dir))
                os.mkdir(project_dir)

            repo_url: str = env.repo_url
            repo_branch: str = env.repo_branch
            if not repo_url:
                if not os.path.exists(os.path.join(project_dir, "project.yml")):
                    await self._warning(f"Failed to compile: no project found in {project_dir} and no repository set")
                await self._end_stage(0)
            else:
                await self._end_stage(0)
                # checkout repo

                if not os.path.exists(os.path.join(project_dir, ".git")):
                    cmd = ["git", "clone", repo_url, "."]
                    if repo_branch:
                        cmd.extend(["-b", repo_branch])
                    result = await self._run_compile_stage("Cloning repository", cmd, project_dir)
                    if result.returncode is None or result.returncode > 0:
                        return False

                elif self.request.force_update:
                    result = await self._run_compile_stage("Fetching changes", ["git", "fetch", repo_url], project_dir)
                if repo_branch:
                    branch = await self.get_branch()
                    if branch is not None and repo_branch != branch:
                        result = await self._run_compile_stage(
                            f"switching branch from {branch} to {repo_branch}", ["git", "checkout", repo_branch], project_dir
                        )

                if self.request.force_update:
                    await self._run_compile_stage("Pulling updates", ["git", "pull"], project_dir)
                    LOGGER.info("Installing and updating modules")
                    await self._run_compile_stage("Updating modules", inmanta_path + ["modules", "update"], project_dir)

            server_address = opt.server_address.get()
            server_port = opt.get_bind_port()
            cmd = inmanta_path + [
                "-vvv",
                "export",
                "-X",
                "-e",
                str(environment_id),
                "--server_address",
                server_address,
                "--server_port",
                str(server_port),
                "--metadata",
                json.dumps(self.request.metadata),
            ]

            if not self.request.do_export:
                f = NamedTemporaryFile()
                cmd.append("-j")
                cmd.append(f.name)

            if config.Config.get("server", "auth", False):
                token = encode_token(["compiler", "api"], str(environment_id))
                cmd.append("--token")
                cmd.append(token)

            if opt.server_ssl_cert.get() is not None:
                cmd.append("--ssl")

            if opt.server_ssl_ca_cert.get() is not None:
                cmd.append("--ssl-ca-cert")
                cmd.append(opt.server_ssl_ca_cert.get())

            self.tail_stdout = ""

            env_vars_compile: Dict[str, str] = os.environ.copy()
            env_vars_compile.update(self.request.environment_variables)

            result = await self._run_compile_stage("Recompiling configuration model", cmd, project_dir, env=env_vars_compile)
            success = result.returncode == 0
            if not success:
                LOGGER.debug("Compile %s failed", self.request.id)

            print("---", self.tail_stdout, result.errstream)
            match = re.search(r"Committed resources with version (\d+)", self.tail_stdout)
            if match:
                self.version = int(match.group(1))
        except CancelledError:
            # This compile was cancelled. Catch it here otherwise a warning will be printed in the logs because of an
            # unhandled exception in a backgrounded coroutine.
            pass

        except Exception:
            LOGGER.exception("An error occured while recompiling")

        finally:
            return success


class CompilerService(ServerSlice):
    """
    Compiler services offers:

    1. service slice API for lifecyclemanagement
    2. internal api for requesting compiles: :meth:`~CompilerService.request_recompile`
    3. internal api for watching complete compiles: :meth:`~CompilerService.add_listener`
    4. api endpoints: is_compiling, get_report, get_reports
    """

    """
    General design of compile scheduling:

    1. all compile request are stored in the database.
    2. when a task starts, _queue is called, if no job is executing for that environment, it is started
    3. when a task ends, it is marked as completed in the database and _dequeue is called and _notify_listeners is scheduled
    as a background task
    4. _dequeue checks the database for a runnable job and starts it (if present)
    5. _notify_listeners runs all listeners in parallel, afterwards the task is marked as handled

    Upon restart
    1. find a runnable(incomplete) job for every environment (if any) and call _queue on it
    2. find all unhandled but complete jobs and run _notify_listeners on them
    """

    _env_folder: str

    def __init__(self) -> None:
        super(CompilerService, self).__init__(SLICE_COMPILER)
        self._recompiles: Dict[uuid.UUID, Task] = {}
        self._global_lock = asyncio.locks.Lock()
        self.listeners: List[CompileStateListener] = []

    async def get_status(self) -> Dict[str, ArgumentTypes]:
        return {"task_queue": await data.Compile.get_next_compiles_count(), "listeners": len(self.listeners)}

    def add_listener(self, listener: CompileStateListener) -> None:
        self.listeners.append(listener)

    def get_dependencies(self) -> List[str]:
        return [SLICE_DATABASE]

    def get_depended_by(self) -> List[str]:
        return [SLICE_TRANSPORT]

    async def prestart(self, server: server.protocol.Server) -> None:
        await super(CompilerService, self).prestart(server)
        state_dir: str = opt.state_dir.get()
        server_state_dir = ensure_directory_exist(state_dir, "server")
        self._env_folder = ensure_directory_exist(server_state_dir, "environments")

    async def start(self) -> None:
        await super(CompilerService, self).start()
        await self._recover()
        self.schedule(self._cleanup, opt.server_cleanup_compiler_reports_interval.get(), initial_delay=0)

    async def _cleanup(self) -> None:
        oldest_retained_date = datetime.datetime.now() - datetime.timedelta(seconds=opt.server_compiler_report_retention.get())
        LOGGER.info("Cleaning up compile reports that are older than %s", oldest_retained_date)
        try:
            await data.Compile.delete_older_than(oldest_retained_date)
        except Exception:
            LOGGER.error("The following exception occured while cleaning up old compiler reports", exc_info=True)

    async def request_recompile(
        self,
        env: data.Environment,
        force_update: bool,
        do_export: bool,
        remote_id: uuid.UUID,
        metadata: JsonType = {},
        env_vars: Dict[str, str] = {},
    ) -> Tuple[Optional[uuid.UUID], Warnings]:
        """
            Recompile an environment in a different thread and taking wait time into account.

            :return: the compile id of the requested compile and any warnings produced during the request
        """
        server_compile: bool = await env.get(data.SERVER_COMPILE)
        if not server_compile:
            LOGGER.info("Skipping compile because server compile not enabled for this environment.")
            return None, ["Skipping compile because server compile not enabled for this environment."]

        requested = datetime.datetime.now()
        compile = data.Compile(
            environment=env.id,
            requested=requested,
            remote_id=remote_id,
            do_export=do_export,
            force_update=force_update,
            metadata=metadata,
            environment_variables=env_vars,
        )
        await compile.insert()
        await self._queue(compile)
        return compile.id, None

    async def _queue(self, compile: data.Compile) -> None:
        async with self._global_lock:
            if compile.environment not in self._recompiles or self._recompiles[compile.environment].done():
                task = self.add_background_task(self._run(compile))
                self._recompiles[compile.environment] = task

    async def _dequeue(self, environment: uuid.UUID) -> None:
        async with self._global_lock:
            nextrun = await data.Compile.get_next_run(environment)
            if nextrun:
                task = self.add_background_task(self._run(nextrun))
                self._recompiles[environment] = task
            else:
                del self._recompiles[environment]

    async def _notify_listeners(self, compile: data.Compile) -> None:
        async def notify(listener: CompileStateListener) -> None:
            try:
                await listener.compile_done(compile)
            except CancelledError:
                """ Propagate Cancel """
                raise
            except Exception:
                logging.exception("CompileStateListener failed")

        await asyncio.gather(*[notify(listener) for listener in self.listeners])
        await compile.update_fields(handled=True)
        LOGGER.log(const.LOG_LEVEL_TRACE, "listeners notified for %s", compile.id)

    async def _recover(self) -> None:
        """Restart runs after server restart"""
        runs = await data.Compile.get_next_run_all()
        for run in runs:
            await self._queue(run)
        unhandled = await data.Compile.get_unhandled_compiles()
        for u in unhandled:
            self.add_background_task(self._notify_listeners(u))

    @protocol.handle(methods.is_compiling, environment_id="id")
    async def is_compiling(self, environment_id: uuid.UUID) -> Apireturn:
        if environment_id in self._recompiles and not self._recompiles[environment_id].done():
            return 200
        return 204

    async def _run(self, compile: data.Compile) -> None:
        now = datetime.datetime.now()

        wait_time = opt.server_autrecompile_wait.get()

        lastrun = await data.Compile.get_last_run(compile.environment)
        if not lastrun:
            wait: float = 0
        else:
            assert lastrun.completed is not None
            wait = max(0, wait_time - (now - lastrun.completed).total_seconds())
        if wait > 0:
            LOGGER.info(
                "Last recompile longer than %s ago (last was at %s), waiting for %d", wait_time, lastrun.completed, wait
            )
        await asyncio.sleep(wait)

        runner = self._get_compile_runner(compile, project_dir=os.path.join(self._env_folder, str(compile.environment)))
        success = await runner.run()

        version = runner.version

        end = datetime.datetime.now()
        await compile.update_fields(completed=end, success=success, version=version)
        if self.is_stopping():
            return
        self.add_background_task(self._notify_listeners(compile))
        await self._dequeue(compile.environment)

    def _get_compile_runner(self, compile: data.Compile, project_dir: str) -> CompileRun:
        return CompileRun(compile, project_dir)

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

    @protocol.handle(methods.get_compile_queue, env="tid")
    async def get_compile_queue(self, env: data.Environment) -> List[CompileRun]:
        """
            Get the current compiler queue on the server
        """
        compiles = await data.Compile.get_next_compiles_for_environment(env.id)
        return [x.to_dto() for x in compiles]
