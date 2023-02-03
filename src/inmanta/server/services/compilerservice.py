"""
    Copyright 2022 Inmanta

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
import traceback
import uuid
from asyncio import CancelledError, Task
from asyncio.subprocess import Process
from collections.abc import Mapping
from functools import partial
from itertools import chain
from logging import Logger
from tempfile import NamedTemporaryFile
from typing import AsyncIterator, Awaitable, Dict, Hashable, List, Optional, Sequence, Tuple, cast

import dateutil
import dateutil.parser
import pydantic

import inmanta.data.model as model
from inmanta import config, const, data, protocol, server
from inmanta.config import Config
from inmanta.data import APILIMIT, InvalidSort
from inmanta.data.dataview import CompileReportView
from inmanta.env import PipCommandBuilder, PythonEnvironment, VenvCreationFailedError, VirtualEnv
from inmanta.protocol import encode_token, methods, methods_v2
from inmanta.protocol.common import ReturnValue
from inmanta.protocol.exceptions import BadRequest, NotFound
from inmanta.server import SLICE_COMPILER, SLICE_DATABASE, SLICE_ENVIRONMENT, SLICE_SERVER, SLICE_TRANSPORT
from inmanta.server import config as opt
from inmanta.server.protocol import ServerSlice
from inmanta.server.validate_filter import InvalidFilter
from inmanta.types import Apireturn, ArgumentTypes, JsonType, Warnings
from inmanta.util import TaskMethod, ensure_directory_exist

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
        self._project_dir = os.path.abspath(project_dir)
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
        start = datetime.datetime.now().astimezone()
        stage = data.Report(compile=self.request.id, started=start, name=name, command=command)
        await stage.insert()
        self.stage = stage

    async def _end_stage(self, returncode: int) -> data.Report:
        assert self.stage is not None
        LOGGER.log(
            const.LOG_LEVEL_TRACE, "ending stage %s for %s in %s", self.stage.name, self.request.id, self.request.environment
        )
        stage = self.stage
        end = datetime.datetime.now().astimezone()
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
        try:
            sub_process = await asyncio.create_subprocess_exec(
                "git", "branch", stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=self._project_dir
            )

            out, err = await sub_process.communicate()
        finally:
            if sub_process.returncode is None:
                # The process is still running, kill it
                sub_process.kill()

        if sub_process.returncode != 0:
            return None

        o = re.search(r"\* ([^\s]+)$", out.decode(), re.MULTILINE)
        if o is not None:
            return o.group(1)
        else:
            return None

    async def get_upstream_branch(self) -> Optional[str]:
        """
        Returns the fully qualified branch name of the upstream branch associated with the currently checked out branch.
        """
        try:
            sub_process = await asyncio.create_subprocess_exec(
                "git",
                "rev-parse",
                "--symbolic-full-name",
                "@{upstream}",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self._project_dir,
            )
            out, err = await sub_process.communicate()
        finally:
            if sub_process.returncode is None:
                # The process is still running, kill it
                sub_process.kill()

        if sub_process.returncode != 0:
            return None

        return out.decode().strip()

    async def _run_compile_stage(self, name: str, cmd: List[str], cwd: str, env: Dict[str, str] = {}) -> data.Report:
        await self._start_stage(name, " ".join(cmd))

        sub_process: Optional[Process] = None
        try:
            env_all = os.environ.copy()
            if env is not None:
                env_all.update(env)

            sub_process = await asyncio.create_subprocess_exec(
                cmd[0], *cmd[1:], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd, env=env_all
            )

            returncode = await self.drain(sub_process)
            return await self._end_stage(returncode)
        except CancelledError:
            """Propagate Cancel"""
            raise
        except Exception as e:
            await self._error("".join(traceback.format_exception(type(e), e, e.__traceback__)))
            return await self._end_stage(RETURNCODE_INTERNAL_ERROR)
        finally:
            if sub_process and sub_process.returncode is None:
                # The process is still running, kill it
                sub_process.kill()

    async def run(self, force_update: Optional[bool] = False) -> Tuple[bool, Optional[model.CompileData]]:
        """
        Runs this compile run.

        :return: Tuple of a boolean representing success and the compile data, if any.
        """
        success = False
        now = datetime.datetime.now().astimezone()
        await self.request.update_fields(started=now)

        compile_data_json_file = NamedTemporaryFile()
        try:
            await self._start_stage("Init", "")

            environment_id = self.request.environment
            project_dir = self._project_dir

            env = await data.Environment.get_by_id(environment_id)

            env_string = ", ".join([f"{k}='{v}'" for k, v in self.request.environment_variables.items()])
            assert self.stage
            await self.stage.update_streams(out=f"Using extra environment variables during compile {env_string}\n")

            if env is None:
                await self._error("Environment %s does not exist." % environment_id)
                await self._end_stage(-1)
                return False, None

            if not os.path.exists(project_dir):
                await self._info("Creating project directory for environment %s at %s" % (environment_id, project_dir))
                os.mkdir(project_dir)

            # Use a separate venv to compile the project to prevent that packages are installed in the
            # venv of the Inmanta server.
            venv_dir = os.path.join(project_dir, ".env")

            async def ensure_venv() -> Optional[data.Report]:
                """
                Ensure a venv is present at `venv_dir`.
                """
                virtual_env = VirtualEnv(venv_dir)
                if virtual_env.exists():
                    return None

                await self._start_stage("Creating venv", command="")
                try:
                    virtual_env.init_env()
                except VenvCreationFailedError as e:
                    await self._error(message=e.msg)
                    return await self._end_stage(returncode=1)
                else:
                    return await self._end_stage(returncode=0)

            async def uninstall_protected_inmanta_packages() -> data.Report:
                """
                Ensure that no protected Inmanta packages are installed in the compiler venv.
                """
                cmd: List[str] = PipCommandBuilder.compose_uninstall_command(
                    python_path=PythonEnvironment.get_python_path_for_env_path(venv_dir),
                    pkg_names=PythonEnvironment.get_protected_inmanta_packages(),
                )
                return await self._run_compile_stage(
                    name="Uninstall inmanta packages from the compiler venv", cmd=cmd, cwd=project_dir
                )

            async def update_modules() -> data.Report:
                return await run_compile_stage_in_venv("Updating modules", ["-vvv", "-X", "project", "update"], cwd=project_dir)

            async def install_modules() -> data.Report:
                return await run_compile_stage_in_venv(
                    "Installing modules", ["-vvv", "-X", "project", "install"], cwd=project_dir
                )

            async def run_compile_stage_in_venv(
                stage_name: str, inmanta_args: List[str], cwd: str, env: Dict[str, str] = {}
            ) -> data.Report:
                """
                Run a compile stage by executing the given command in the venv `venv_dir`.

                :param stage_name: Name of the compile stage.
                :param inmanta_args: The command to be executed in the venv. This command should not include the part
                                      ["<python-interpreter>", "-m", "inmanta.app"]
                :param cwd: The current working directory to be used for the command invocation.
                :param env: Execute the command with these environment variables.
                """
                LOGGER.info(stage_name)
                python_path = PythonEnvironment.get_python_path_for_env_path(venv_dir)
                assert os.path.exists(python_path)
                full_cmd = [python_path, "-m", "inmanta.app"] + inmanta_args
                return await self._run_compile_stage(stage_name, full_cmd, cwd, env)

            async def setup() -> AsyncIterator[Awaitable[Optional[data.Report]]]:
                """
                Returns an iterator over all setup stages. Inspecting stage success state is the responsibility of the caller.
                """
                repo_url: str = env.repo_url
                repo_branch: str = env.repo_branch
                if os.path.exists(os.path.join(project_dir, "project.yml")):
                    yield self._end_stage(0)

                    yield ensure_venv()

                    should_update: bool = force_update or self.request.force_update

                    # switch branches
                    if repo_branch:
                        branch = await self.get_branch()
                        if branch is not None and repo_branch != branch:
                            if should_update:
                                yield self._run_compile_stage("Fetching new branch heads", ["git", "fetch"], project_dir)
                            yield self._run_compile_stage(
                                f"Switching branch from {branch} to {repo_branch}",
                                ["git", "checkout", repo_branch],
                                project_dir,
                            )
                            if not should_update:
                                # if we update, update procedure will install modules
                                yield install_modules()

                    # update project
                    if should_update:
                        # only pull changes if there is an upstream branch
                        if await self.get_upstream_branch():
                            yield self._run_compile_stage("Pulling updates", ["git", "pull"], project_dir)
                        yield uninstall_protected_inmanta_packages()
                        yield update_modules()
                else:
                    if not repo_url:
                        await self._warning(f"Failed to compile: no project found in {project_dir} and no repository set.")
                        yield self._end_stage(1)
                        return

                    if len(os.listdir(project_dir)) > 0:
                        await self._warning(f"Failed to compile: no project found in {project_dir} but directory is not empty.")
                        yield self._end_stage(1)
                        return

                    yield self._end_stage(0)

                    # clone repo and install project
                    cmd = ["git", "clone", repo_url, "."]
                    if repo_branch:
                        cmd.extend(["-b", repo_branch])
                    yield self._run_compile_stage("Cloning repository", cmd, project_dir)
                    yield ensure_venv()
                    yield install_modules()

            async for stage in setup():
                stage_result: Optional[data.Report] = await stage
                if stage_result and (stage_result.returncode is None or stage_result.returncode > 0):
                    return False, None

            server_address = opt.server_address.get()
            server_port = opt.get_bind_port()
            cmd = [
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
                "--export-compile-data",
                "--export-compile-data-file",
                compile_data_json_file.name,
            ]

            if self.request.exporter_plugin:
                cmd.append("--export-plugin")
                cmd.append(self.request.exporter_plugin)

            if self.request.partial:
                cmd.append("--partial")

            if self.request.removed_resource_sets is not None:
                for resource_set in self.request.removed_resource_sets:
                    cmd.append("--delete-resource-set")
                    cmd.append(resource_set)

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
            else:
                cmd.append("--no-ssl")

            if opt.server_ssl_ca_cert.get() is not None:
                cmd.append("--ssl-ca-cert")
                cmd.append(opt.server_ssl_ca_cert.get())

            self.tail_stdout = ""

            env_vars_compile: Dict[str, str] = os.environ.copy()
            env_vars_compile.update(self.request.environment_variables)

            result: data.Report = await run_compile_stage_in_venv(
                "Recompiling configuration model", cmd, cwd=project_dir, env=env_vars_compile
            )
            success = result.returncode == 0
            if not success:
                if self.request.do_export:
                    LOGGER.warning("Compile %s failed", self.request.id)
                else:
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
            LOGGER.exception("An error occurred while recompiling")

        finally:

            async def warn(message: str) -> None:
                if self.stage is not None:
                    await self._warning(message)
                else:
                    LOGGER.warning(message)

            with compile_data_json_file as file:
                compile_data_json: str = file.read().decode()
                if compile_data_json:
                    try:
                        return success, model.CompileData.parse_raw(compile_data_json)
                    except json.JSONDecodeError:
                        await warn(
                            "Failed to load compile data json for compile %s. Invalid json: '%s'"
                            % (self.request.id, compile_data_json)
                        )
                    except pydantic.ValidationError:
                        await warn(
                            "Failed to parse compile data for compile %s. Json does not match CompileData model: '%s'"
                            % (self.request.id, compile_data_json)
                        )
            return success, None


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
        self._scheduled_full_compiles: Dict[uuid.UUID, Tuple[TaskMethod, str]] = {}
        # cache the queue count for DB-less and lock-less access to number of tasks
        self._queue_count_cache: int = 0

    async def get_status(self) -> Dict[str, ArgumentTypes]:
        return {"task_queue": self._queue_count_cache, "listeners": len(self.listeners)}

    def add_listener(self, listener: CompileStateListener) -> None:
        self.listeners.append(listener)

    def get_dependencies(self) -> List[str]:
        return [SLICE_DATABASE]

    def get_depended_by(self) -> List[str]:
        return [SLICE_ENVIRONMENT, SLICE_SERVER, SLICE_TRANSPORT]

    async def prestart(self, server: server.protocol.Server) -> None:
        await super(CompilerService, self).prestart(server)
        state_dir: str = opt.state_dir.get()
        server_state_dir = ensure_directory_exist(state_dir, "server")
        self._env_folder = ensure_directory_exist(server_state_dir, "environments")

    async def start(self) -> None:
        await super(CompilerService, self).start()
        await self._recover()
        self.schedule(self._cleanup, opt.server_cleanup_compiler_reports_interval.get(), initial_delay=0, cancel_on_stop=False)

    async def _cleanup(self) -> None:
        oldest_retained_date = datetime.datetime.now().astimezone() - datetime.timedelta(
            seconds=opt.server_compiler_report_retention.get()
        )
        LOGGER.info("Cleaning up compile reports that are older than %s", oldest_retained_date)
        try:
            await data.Compile.delete_older_than(oldest_retained_date)
        except CancelledError:
            """Propagate Cancel"""
            raise
        except Exception:
            LOGGER.error("The following exception occurred while cleaning up old compiler reports", exc_info=True)

    def schedule_full_compile(self, env: data.Environment, schedule_cron: str) -> None:
        """
        Schedules full compiles for a single environment. Overrides any previously enabled schedule for this environment.

        :param env: The environment to schedule full compiles for
        :param schedule_cron: The cron expression for the schedule, may be an empty string to disable full compile scheduling.
        """
        # remove old schedule if it exists
        if env.id in self._scheduled_full_compiles:
            self.remove_cron(*self._scheduled_full_compiles[env.id])
            del self._scheduled_full_compiles[env.id]
        # set up new schedule
        if schedule_cron:
            metadata: Dict[str, str] = {
                "type": "schedule",
                "message": "Full recompile triggered by AUTO_FULL_COMPILE cron schedule",
            }
            recompile: TaskMethod = partial(
                self.request_recompile, env, force_update=False, do_export=True, remote_id=uuid.uuid4(), metadata=metadata
            )
            self.schedule_cron(recompile, schedule_cron, cancel_on_stop=False)
            self._scheduled_full_compiles[env.id] = (recompile, schedule_cron)

    async def request_recompile(
        self,
        env: data.Environment,
        force_update: bool,
        do_export: bool,
        remote_id: uuid.UUID,
        metadata: Optional[JsonType] = None,
        env_vars: Optional[Mapping[str, str]] = None,
        partial: bool = False,
        removed_resource_sets: Optional[List[str]] = None,
        exporter_plugin: Optional[str] = None,
        notify_failed_compile: Optional[bool] = None,
        failed_compile_message: Optional[str] = None,
    ) -> Tuple[Optional[uuid.UUID], Warnings]:
        """
        Recompile an environment in a different thread and taking wait time into account.

        :param notify_failed_compile: if set to True, errors during compilation will be notified using the
        "failed_compile_message".
        if set to false, nothing will be notified. If not set then the default notifications are
        sent (failed pull stage and errors during the do_export)
        :param failed_compile_message: the message used in notifications if notify_failed_compile is set to True.
        :return: the compile id of the requested compile and any warnings produced during the request

        """
        if removed_resource_sets is None:
            removed_resource_sets = []
        if metadata is None:
            metadata = {}
        if env_vars is None:
            env_vars = {}

        server_compile: bool = await env.get(data.SERVER_COMPILE)
        if not server_compile:
            LOGGER.info("Skipping compile because server compile not enabled for this environment.")
            return None, ["Skipping compile because server compile not enabled for this environment."]

        requested = datetime.datetime.now().astimezone()

        compile = data.Compile(
            environment=env.id,
            requested=requested,
            remote_id=remote_id,
            do_export=do_export,
            force_update=force_update,
            metadata=metadata,
            environment_variables=env_vars,
            partial=partial,
            removed_resource_sets=removed_resource_sets,
            exporter_plugin=exporter_plugin,
            notify_failed_compile=notify_failed_compile,
            failed_compile_message=failed_compile_message,
        )
        await compile.insert()
        await self._queue(compile)
        return compile.id, None

    @staticmethod
    def _compile_merge_key(c: data.Compile) -> Hashable:
        """
        Returns a key used to determine whether two compiles c1 and c2 are eligible for merging. They are iff
        _compile_merge_key(c1) == _compile_merge_key(c2).
        """
        return c.to_dto().json(
            include={"environment", "started", "do_export", "environment_variables", "partial", "removed_resource_sets"}
        )

    async def _queue(self, compile: data.Compile) -> None:
        async with self._global_lock:
            if self.is_stopping():
                return
            env: Optional[data.Environment] = await data.Environment.get_by_id(compile.environment)
            if env is None:
                raise Exception("Can't queue compile: environment %s does not exist" % compile.environment)
            assert env is not None
            # don't execute any compiles in a halted environment
            if env.halted:
                return
            self._queue_count_cache += 1
            if compile.environment not in self._recompiles or self._recompiles[compile.environment].done():
                task = self.add_background_task(self._run(compile))
                self._recompiles[compile.environment] = task

    async def _dequeue(self, environment: uuid.UUID) -> None:
        async with self._global_lock:
            if self.is_stopping():
                return
            env: Optional[data.Environment] = await data.Environment.get_by_id(environment)
            if env is None:
                raise Exception("Can't dequeue compile: environment %s does not exist" % environment)
            nextrun = await data.Compile.get_next_run(environment)
            if nextrun and not env.halted:
                task = self.add_background_task(self._run(nextrun))
                self._recompiles[environment] = task
            else:
                del self._recompiles[environment]

    async def _notify_listeners(self, compile: data.Compile) -> None:
        async def notify(listener: CompileStateListener) -> None:
            try:
                await listener.compile_done(compile)
            except CancelledError:
                """Propagate Cancel"""
                raise
            except Exception:
                logging.exception("CompileStateListener failed")

        await asyncio.gather(*[notify(listener) for listener in self.listeners])
        await compile.update_fields(handled=True)
        LOGGER.log(const.LOG_LEVEL_TRACE, "listeners notified for %s", compile.id)

    async def _recover(self) -> None:
        """Restart runs after server restart"""
        # one run per env max to get started
        runs = await data.Compile.get_next_run_all()
        self._queue_count_cache = await data.Compile.get_next_compiles_count() - len(runs)
        for run in runs:
            await self._queue(run)
        unhandled = await data.Compile.get_unhandled_compiles()
        for u in unhandled:
            self.add_background_task(self._notify_listeners(u))

    async def resume_environment(self, environment: uuid.UUID) -> None:
        """
        Resume compiler service after halt.
        """
        compile: Optional[data.Compile] = await data.Compile.get_next_run(environment)
        if compile is not None:
            await self._queue(compile)

    @protocol.handle(methods.is_compiling, environment_id="id")
    async def is_compiling(self, environment_id: uuid.UUID) -> Apireturn:
        if environment_id in self._recompiles and not self._recompiles[environment_id].done():
            return 200
        return 204

    def _calculate_recompile_wait(
        self,
        wait_time: int,
        compile_requested: datetime.datetime,
        last_compile_completed: datetime.datetime,
        now: datetime.datetime,
    ) -> int:
        if wait_time == 0:
            wait: float = 0
        else:
            if last_compile_completed >= compile_requested:
                wait = max(0, wait_time - (now - compile_requested).total_seconds())
            else:
                wait = max(0, wait_time - (now - last_compile_completed).total_seconds())
        return wait

    async def _auto_recompile_wait(self, compile: data.Compile) -> None:
        if Config.is_set("server", "auto-recompile-wait"):
            wait_time = opt.server_autrecompile_wait.get()
            LOGGER.warning(
                "The server-auto-recompile-wait is enabled and set to %s seconds. "
                "This option is deprecated in favor of the recompile_backoff environment setting.",
                wait_time,
            )
        else:
            env = await data.Environment.get_by_id(compile.environment)
            wait_time = await env.get(data.RECOMPILE_BACKOFF)
            if wait_time:
                LOGGER.info("The recompile_backoff environment setting is enabled and set to %s seconds.", wait_time)
            else:
                LOGGER.info("The recompile_backoff environment setting is disabled")
        last_run = await data.Compile.get_last_run(compile.environment)
        if not last_run:
            wait: float = 0
        else:
            assert last_run.completed is not None
            wait = self._calculate_recompile_wait(
                wait_time, compile.requested, last_run.completed, datetime.datetime.now().astimezone()
            )
        if wait > 0:
            LOGGER.info(
                "Waiting for %.2f seconds before running a new compile",
                wait,
            )
        else:
            assert compile.requested is not None  # Make mypy happy
            LOGGER.debug("Running recompile without waiting: requested at %s", compile.requested.astimezone())
        await asyncio.sleep(wait)

    async def _run(self, compile: data.Compile) -> None:
        """
        Runs a compile request. At completion, looks for similar compile requests based on _compile_merge_key and marks
        those as completed as well.
        """
        self._queue_count_cache -= 1
        await self._auto_recompile_wait(compile)

        compile_merge_key: Hashable = CompilerService._compile_merge_key(compile)
        merge_candidates: List[data.Compile] = [
            c
            for c in await data.Compile.get_next_compiles_for_environment(compile.environment)
            if not c.id == compile.id and CompilerService._compile_merge_key(c) == compile_merge_key
        ]

        runner = self._get_compile_runner(compile, project_dir=os.path.join(self._env_folder, str(compile.environment)))
        # set force_update == True iff any compile request has force_update == True
        compile_data: Optional[model.CompileData]
        success, compile_data = await runner.run(force_update=any(c.force_update for c in chain([compile], merge_candidates)))

        version = runner.version

        end = datetime.datetime.now().astimezone()
        compile_data_json: Optional[dict] = None if compile_data is None else compile_data.dict()
        await compile.update_fields(completed=end, success=success, version=version, compile_data=compile_data_json)
        awaitables = [
            merge_candidate.update_fields(
                started=compile.started,
                completed=end,
                success=success,
                version=version,
                substitute_compile_id=compile.id,
                compile_data=compile_data_json,
            )
            for merge_candidate in merge_candidates
        ]

        await asyncio.gather(*awaitables)
        if self.is_stopping():
            return
        self.add_background_task(self._notify_listeners(compile))
        self._queue_count_cache -= len(merge_candidates)
        for merge_candidate in merge_candidates:
            self.add_background_task(self._notify_listeners(merge_candidate))
        await self._dequeue(compile.environment)

    def _get_compile_runner(self, compile: data.Compile, project_dir: str) -> CompileRun:
        return CompileRun(compile, project_dir)

    @protocol.handle(methods.get_reports, env="tid")
    async def get_reports(
        self, env: data.Environment, start: Optional[str] = None, end: Optional[str] = None, limit: Optional[int] = None
    ) -> Apireturn:
        if env is None:
            return 404, {"message": "The given environment id does not exist!"}

        if limit is None:
            limit = APILIMIT
        elif limit > APILIMIT:
            raise BadRequest(f"limit parameter can not exceed {APILIMIT}, got {limit}.")

        start_time = None
        end_time = None
        if start is not None:
            start_time = dateutil.parser.parse(start)
        if end is not None:
            end_time = dateutil.parser.parse(end)

        models = await data.Compile.get_list_paged(
            page_by_column="started",
            order_by_column="started",
            order="DESC",
            limit=limit,
            start=start_time,
            end=end_time,
            no_obj=False,
            connection=None,
            environment=env.id,
        )

        return 200, {"reports": [m.to_dict() for m in models]}

    @protocol.handle(methods.get_report, compile_id="id")
    async def get_report(self, compile_id: uuid.UUID) -> Apireturn:
        report = await data.Compile.get_report(compile_id)

        if report is None:
            return 404

        return 200, {"report": report}

    @protocol.handle(methods_v2.get_compile_data, compile_id="id")
    async def get_compile_data(self, compile_id: uuid.UUID) -> Optional[model.CompileData]:
        compile: Optional[data.Compile] = await data.Compile.get_by_id(compile_id)
        if compile is None:
            raise NotFound("The given compile id does not exist")
        return compile.to_dto().compile_data

    @protocol.handle(methods.get_compile_queue, env="tid")
    async def get_compile_queue(self, env: data.Environment) -> List[model.CompileRun]:
        """
        Get the current compiler queue on the server
        """
        compiles = await data.Compile.get_next_compiles_for_environment(env.id)
        return [x.to_dto() for x in compiles]

    @protocol.handle(methods_v2.get_compile_reports, env="tid")
    async def get_compile_reports(
        self,
        env: data.Environment,
        limit: Optional[int] = None,
        first_id: Optional[uuid.UUID] = None,
        last_id: Optional[uuid.UUID] = None,
        start: Optional[datetime.datetime] = None,
        end: Optional[datetime.datetime] = None,
        filter: Optional[Dict[str, List[str]]] = None,
        sort: str = "requested.desc",
    ) -> ReturnValue[Sequence[model.CompileReport]]:

        try:
            handler = CompileReportView(env, limit, filter, sort, first_id, last_id, start, end)
            return await handler.execute()
        except (InvalidFilter, InvalidSort, data.InvalidQueryParameter, data.InvalidFieldNameException) as e:
            raise BadRequest(e.message) from e

    @protocol.handle(methods_v2.compile_details, env="tid")
    async def compile_details(self, env: data.Environment, id: uuid.UUID) -> model.CompileDetails:
        details = await data.Compile.get_compile_details(env.id, id)
        if not details:
            raise NotFound("The compile with the given id does not exist.")
        return details
