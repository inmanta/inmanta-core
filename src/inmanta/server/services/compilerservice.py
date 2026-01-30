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
import contextlib
import datetime
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import traceback
import uuid
from asyncio import CancelledError
from asyncio.subprocess import Process
from collections.abc import AsyncIterator, Awaitable, Hashable, Mapping, Sequence
from itertools import chain
from logging import Logger
from tempfile import NamedTemporaryFile
from typing import Optional, cast

import dateutil
import dateutil.parser
import pydantic
from asyncpg import Connection

import inmanta.data.model as model
import inmanta.server.services.environmentlistener
from inmanta import config, const, data, protocol, server, tracing
from inmanta.config import Config
from inmanta.data import APILIMIT, InvalidSort
from inmanta.data.dataview import CompileReportView
from inmanta.env import PipCommandBuilder, PythonEnvironment, VenvActivationFailedError, VirtualEnv
from inmanta.protocol import encode_token, methods, methods_v2
from inmanta.protocol.common import ReturnValue
from inmanta.protocol.exceptions import BadRequest, NotFound
from inmanta.server import SLICE_COMPILER, SLICE_DATABASE, SLICE_ENVIRONMENT, SLICE_SERVER, SLICE_TRANSPORT
from inmanta.server import config as opt
from inmanta.server.protocol import ServerSlice
from inmanta.server.services import environmentservice
from inmanta.server.validate_filter import InvalidFilter
from inmanta.types import Apireturn, ArgumentTypes, JsonType, Warnings
from inmanta.util import TaskMethod, ensure_directory_exist

RETURNCODE_INTERNAL_ERROR = -1

LOGGER: Logger = logging.getLogger(__name__)
COMPILER_LOGGER: Logger = LOGGER.getChild("report")


class CompileStateListener:
    @abc.abstractmethod
    async def compile_done(self, compile: data.Compile) -> None:
        """
        Coroutine to execute when this listener is notified of a completed compile

        1- Notifications are delivered at least once (retry until all listeners have returned or raise an exception other
        than CancelledError)
        2- If this listener is blocking, the next compile can only start after this coroutine is done
        3- Multiple notifications can be in flight at any given time, out-of-order delivery is possible but highly unlikely.
        4- This coroutine is cancelled upon shutdown
        """

    def is_blocking(self) -> bool:
        """
        Should this handler be run before the next compile can start?
        """
        return False


class CompileRun:
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
        with tracing.span("drain"):
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

    async def _run_compile_stage(self, name: str, cmd: list[str], cwd: str, env: dict[str, str] = {}) -> data.Report:
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

    async def ensure_compiler_venv(self) -> None:
        """ "
        Ensure we have a compiler venv in the project

        Expected to be in a running stage

        It is built as
        1. a `.env` symlink to
        2. a `.env-py3.12` versioned directory
        """
        assert os.path.exists(self._project_dir)
        project_dir = self._project_dir

        # Eventual venv dir
        venv_dir = os.path.join(project_dir, ".env")

        # Versioned python dir
        python_version = ".".join(platform.python_version_tuple()[0:2])
        versioned_venv_dir = ".env-py" + python_version
        versioned_venv_dir_full = os.path.join(project_dir, versioned_venv_dir)

        async def ensure_venv() -> None:
            """
            Ensures that a compatible venv exists at .venv-py<version>
            """
            if os.path.exists(versioned_venv_dir_full):
                return
            # migration from old .env
            if os.path.exists(venv_dir) and not os.path.islink(venv_dir):
                virtual_env = VirtualEnv(venv_dir)
                if virtual_env.exists():
                    with contextlib.suppress(VenvActivationFailedError):
                        virtual_env.can_activate()  # raises exception
                        # version matches, move it to the correct folder
                        os.rename(venv_dir, versioned_venv_dir_full)
                        await self._info(f"Moving existing venv from {venv_dir} to {versioned_venv_dir_full}")
                        # All done
                        return
                # version doesn't match
                os.rename(venv_dir, venv_dir + "_old")
                await self._info(f"Discarding existing venv from {venv_dir} to {venv_dir}_old, Creating new")

            # No there yet
            await self._info(f"Creating new venv at {versioned_venv_dir_full}")
            virtual_env = VirtualEnv(versioned_venv_dir_full)
            virtual_env.init_env()

        async def link() -> None:
            """
            Ensures that a link from .venv to .venv-py<version> exists
            """
            is_link: bool = os.path.islink(venv_dir)
            with contextlib.suppress(FileNotFoundError):
                if is_link and os.path.samefile(venv_dir, versioned_venv_dir_full):
                    await self._info("Found existing venv")
                    return
            if os.path.exists(venv_dir):
                if is_link:
                    os.unlink(venv_dir)
                else:
                    os.rename(venv_dir, f"{venv_dir}_old")

            os.symlink(versioned_venv_dir, venv_dir)

        await ensure_venv()
        await link()

    async def run(self, force_update: Optional[bool] = False) -> tuple[bool, Optional[model.CompileData]]:
        """
        Runs this compile run.

        :return: Tuple of a boolean representing success and the compile data, if any.
        """
        success = False

        compile_data_json_file = NamedTemporaryFile()
        try:
            await self._start_stage("Init", "")

            environment_id = self.request.environment
            project_dir = self._project_dir

            env = await data.Environment.get_by_id(environment_id)

            env_string = (
                ", ".join([f"{k}='{v}'" for k, v in self.request.used_environment_variables.items()])
                if self.request.used_environment_variables
                else ""
            )
            assert self.stage
            await self.stage.update_streams(out=f"Using extra environment variables during compile {env_string}\n")

            if env is None:
                await self._error("Environment %s does not exist." % environment_id)
                await self._end_stage(-1)
                return False, None

            if self.request.reinstall_project_and_venv and os.path.exists(project_dir):
                await self._info(f"Removing project and venv directory for environment {environment_id} at {project_dir}")
                shutil.rmtree(project_dir)

            if not os.path.exists(project_dir):
                await self._info(f"Creating project directory for environment {environment_id} at {project_dir}")
                os.makedirs(project_dir)

            # Use a separate venv to compile the project to prevent that packages are installed in the
            # venv of the Inmanta server.
            venv_dir = os.path.join(project_dir, ".env")

            # Load configuration
            server_address = opt.internal_server_address.get()
            server_port = opt.server_bind_port.get()

            app_cli_args = ["-vvv"]

            if Config._min_c_config_file is not None:
                app_cli_args.append("-c")
                app_cli_args.append(Config._min_c_config_file)

            if Config._config_dir is not None:
                app_cli_args.append("--config-dir")
                app_cli_args.append(Config._config_dir)

            export_command = [
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
                export_command.append("--export-plugin")
                export_command.append(self.request.exporter_plugin)

            if self.request.partial:
                export_command.append("--partial")

            if self.request.removed_resource_sets is not None:
                for resource_set in self.request.removed_resource_sets:
                    export_command.append("--delete-resource-set")
                    export_command.append(resource_set)

            if self.request.soft_delete:
                export_command.append("--soft-delete")

            if not self.request.do_export:
                f = NamedTemporaryFile()
                export_command.append("-j")
                export_command.append(f.name)

            if config.Config.get("server", "auth", False):
                token = encode_token(["compiler", "api"], str(environment_id))
                export_command.append("--token")
                export_command.append(token)

            if opt.server_ssl_cert.get() is not None:
                export_command.append("--ssl")
            else:
                export_command.append("--no-ssl")

            ssl_ca_cert = opt.server_ssl_ca_cert.get()
            if ssl_ca_cert is not None:
                export_command.append("--ssl-ca-cert")
                export_command.append(ssl_ca_cert)

            # Make mypy happy
            assert self.request.used_environment_variables is not None
            env_vars_compile: dict[str, str] = os.environ.copy()
            env_vars_compile.update(self.request.used_environment_variables)

            cmd = app_cli_args + export_command

            async def ensure_venv() -> Optional[data.Report]:
                """
                Ensure a venv is present at `venv_dir`.
                """
                await self._start_stage("Venv check", command="")
                try:
                    await self.ensure_compiler_venv()
                except Exception as e:
                    await self._error(message=str(e))
                    return await self._end_stage(returncode=1)
                else:
                    return await self._end_stage(returncode=0)

            async def uninstall_protected_inmanta_packages() -> data.Report:
                """
                Ensure that no protected Inmanta packages are installed in the compiler venv.
                """
                cmd: list[str] = PipCommandBuilder.compose_uninstall_command(
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
                stage_name: str, inmanta_args: list[str], cwd: str, env: dict[str, str] = {}
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
                env.update(tracing.get_context())
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

            self.tail_stdout = ""
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

        except Exception as e:
            if self.stage is not None:
                await self._error(message=str(e))
                await self._end_stage(1)
            else:
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
                        return success, model.CompileData.model_validate_json(compile_data_json)
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


class CompilerService(ServerSlice, inmanta.server.services.environmentlistener.EnvironmentListener):
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
    2. when compile is queued, _process_next_compile_in_queue is called: if no job is executing for that environment, it is
        started
    3. when a compile run ends:
        a. it is marked as completed in the database
        b. _notify_listeners notifies blocking listeners and schedules notification of async listeners as a background task.
            When the background task finishes, the compile is marked as handled
        c. _process_next_compile_in_queue is called again to start the next queued compile, if any

    Upon restart
    1. call _process_next_compile_in_queue in all-environments mode to find a runnable (incomplete) request for every
        environment and start it.
    2. find all unhandled but complete jobs and run _notify_listeners on them
    """

    _server_state_dir: str
    environment_service: "environmentservice.EnvironmentService"

    def __init__(self) -> None:
        super().__init__(SLICE_COMPILER)

        self._env_to_compile_task: dict[uuid.UUID, asyncio.Task[None | protocol.Result]] = {}
        # write lock only, writers take care to uphold consistency so that readers don't need the lock
        self._write_lock_env_to_compile_task = asyncio.locks.Lock()

        # boolean indicating when everything is up and compile execution can start
        self.fully_ready = False

        self.blocking_listeners: list[CompileStateListener] = []
        self.async_listeners: list[CompileStateListener] = []

        self._scheduled_full_compiles: dict[uuid.UUID, tuple[TaskMethod, str]] = {}
        # In-memory cache to keep track of the total length of all the compile queues on this Inmanta server.
        # This cache is used by the /serverstatus endpoint.
        self._queue_count_cache: int = 0
        self._queue_count_cache_lock = asyncio.locks.Lock()

    async def get_status(self) -> Mapping[str, ArgumentTypes]:
        return {"task_queue": self._queue_count_cache, "listeners": len(self.async_listeners) + len(self.blocking_listeners)}

    def add_listener(self, listener: CompileStateListener) -> None:
        if listener.is_blocking():
            self.blocking_listeners.append(listener)
        else:
            self.async_listeners.append(listener)

    def get_dependencies(self) -> list[str]:
        return [SLICE_DATABASE]

    def get_depended_by(self) -> list[str]:
        return [SLICE_ENVIRONMENT, SLICE_SERVER, SLICE_TRANSPORT]

    async def prestart(self, server: server.protocol.Server) -> None:
        await super().prestart(server)
        state_dir: str = config.state_dir.get()
        self._server_state_dir = ensure_directory_exist(state_dir, "server")

    async def start(self) -> None:
        await super().start()
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
            metadata: dict[str, str] = {
                "type": "schedule",
                "message": "Full recompile triggered by AUTO_FULL_COMPILE cron schedule",
            }

            async def _request_recompile_task() -> tuple[Optional[uuid.UUID], Warnings]:
                """
                Creates a new task for the full compile schedule.
                If the environment is halted, the task does nothing.
                Otherwise, it requests a recompile.
                """
                latest_env = await data.Environment.get_by_id(env.id)
                if not latest_env or latest_env.halted:
                    return None, []

                return await self.request_recompile(
                    env,
                    force_update=False,
                    do_export=True,
                    remote_id=uuid.uuid4(),
                    metadata=metadata,
                )

            self.schedule_cron(_request_recompile_task, schedule_cron, cancel_on_stop=False)
            self._scheduled_full_compiles[env.id] = (_request_recompile_task, schedule_cron)

    async def request_recompile(
        self,
        env: data.Environment,
        force_update: bool,
        do_export: bool,
        remote_id: uuid.UUID,
        metadata: Optional[JsonType] = None,
        env_vars: Optional[Mapping[str, str]] = None,
        partial: bool = False,
        exporter_plugin: Optional[str] = None,
        notify_failed_compile: Optional[bool] = None,
        failed_compile_message: Optional[str] = None,
        in_db_transaction: bool = False,
        connection: Optional[Connection] = None,
        soft_delete: bool = False,
        mergeable_env_vars: Optional[Mapping[str, str]] = None,
        links: Optional[dict[str, list[str]]] = None,
        reinstall_project_and_venv: bool = False,
    ) -> tuple[Optional[uuid.UUID], Warnings]:
        """
        Recompile an environment in a different thread and taking wait time into account.

        :param notify_failed_compile: if set to True, errors during compilation will be notified using the
                                      "failed_compile_message".
                                      if set to false, nothing will be notified. If not set then the default notifications are
                                      sent (failed pull stage and errors during the do_export)
        :param failed_compile_message: the message used in notifications if notify_failed_compile is set to True.
        :param connection: Perform the database changes using this database connection. If this connection is in a transaction
                           context, in_db_transaction must be set to True.
        :param in_db_transaction: If set to True, the connection must be provided and the connection must be part of an ongoing
                                  database transaction. If this parameter is set to True, is required to call
                                  `CompileService.notify_compile_request_committed()` right after the transaction commits.
        :param soft_delete: Silently ignore deletion of resource sets passed in the env_vars or mergeable_env_vars if
            they contain resources that are being exported.
        :param mergeable_env_vars: a set of env vars that can be compacted over multiple compiles.
            If multiple values are compacted, they will be joined using spaces.
        :param links: An object that contains relevant links to this compile.
            It is a dictionary where the key is something that identifies one or more links
            and the value is a list of urls. i.e. {"instances": ["link-1',"link-2"], "compiles": ["link-3"]}
        :param reinstall_project_and_venv: True iff perform a clean checkout of the project and re-create the compiler venv.
        :return: the compile id of the requested compile and any warnings produced during the request
        """
        if in_db_transaction and not connection:
            raise Exception("A connection should be provided when in_db_transaction is True.")
        if in_db_transaction != (connection is not None and connection.is_in_transaction()):
            raise Exception(
                f"in_db_transaction is {in_db_transaction},"
                f" but the given connection is{' not' if in_db_transaction else ''} executing in a transaction."
            )

        if metadata is None:
            metadata = {}
        if env_vars is None:
            env_vars = {}
        if mergeable_env_vars is None:
            mergeable_env_vars = {}
        if links is None:
            links = {}

        server_compile: bool = bool(await env.get(data.SERVER_COMPILE))
        if not server_compile:
            LOGGER.info("Skipping compile because server compile not enabled for this environment.")
            return None, ["Skipping compile because server compile not enabled for this environment."]

        requested = datetime.datetime.now().astimezone()

        shared_keys = mergeable_env_vars.keys() & env_vars.keys()
        if shared_keys:
            raise ValueError(
                "Invalid compile request: The same environment variable cannot be present in the "
                f"env_vars and mergeable_env_vars dictionary simultaneously: {shared_keys}."
            )

        compile = data.Compile(
            environment=env.id,
            requested=requested,
            remote_id=remote_id,
            do_export=do_export,
            force_update=force_update,
            metadata=metadata,
            requested_environment_variables=env_vars,
            used_environment_variables=None,
            mergeable_environment_variables=mergeable_env_vars,
            partial=partial,
            exporter_plugin=exporter_plugin,
            notify_failed_compile=notify_failed_compile,
            failed_compile_message=failed_compile_message,
            soft_delete=soft_delete,
            links=links,
            reinstall_project_and_venv=reinstall_project_and_venv,
        )
        if not in_db_transaction:
            async with self._queue_count_cache_lock:
                await compile.insert(connection)
                self._queue_count_cache += 1
            await self._process_next_compile_in_queue(environment=compile.environment, connection=connection)
        else:
            # We are running inside a transaction. The changes will only be applied after the transaction commits.
            # We cannot increment the queue count yet or schedule the requested compile for execution. This will be
            # done when the notify_compile_request_committed() method is invoked.
            await compile.insert(connection)

        return compile.id, None

    async def notify_compile_request_committed(self, compile_id: uuid.UUID) -> None:
        """
        This method must be called when the `request_recompile()` method was called with in_db_transaction=True. It must be
        called right after the transaction committed. If the transaction was aborted, this method most not be called.

        This method is safe with respect to server restarts. If the server restarts after the transaction was committed,
        but before this method was invoked, the server will automatically recover from this and run the requested compile
        without any need to call this method.
        """
        compile_obj: Optional[data.Compile] = await data.Compile.get_by_id(compile_id)
        if not compile_obj:
            raise Exception(f"Compile with id {compile_id} not found.")
        async with self._queue_count_cache_lock:
            self._queue_count_cache += 1
        await self._process_next_compile_in_queue(environment=compile_obj.environment)

    @staticmethod
    def _compile_merge_key(c: data.Compile) -> Hashable:
        """
        Returns a key used to determine whether two compiles c1 and c2 are eligible for merging. They are iff
        _compile_merge_key(c1) == _compile_merge_key(c2).
        """
        return c.to_dto().model_dump_json(
            include={
                "environment",
                "started",
                "do_export",
                "requested_environment_variables",
                "partial",
            },
        )

    async def _process_next_compile_in_queue(
        self,
        *,
        environment: Optional[uuid.UUID] = None,
        finish_current_compile: bool = False,
        connection: Optional[Connection] = None,
    ) -> None:
        """
        Process the next compile in the queue, for a single environment or for all of them. Does not start any compiles
        if the service is still coming up or if it is shutting down.

        Acquires the compiler service's write lock for the compiling environments and ensures consistency of that set.
        i.e. no transient state will exist between the end of one compile and the start of the next one, if one is queued.
        This way pure readers of the compiling envs do not need to acquire the lock to read consistent data.

        :param environment: If set, only process this environment. Otherwise process all environments.
        :param finish_current_compile: Signal completion of the currently running compile for this environment. If True,
            the environment will be considered free to start a new compile run, and if no new run is started, it removed from
            the compiling environments set. Requires environment to be set.
        :param connection: The database connection to execute queries in, if any. Must not be in a transaction context.
            Its main purpose is to be able to share the connection resource for contention reasons.
        """
        if finish_current_compile and environment is None:
            raise ValueError("The finish_current_compile argument is only supported in single environment mode")
        if connection is not None and connection.is_in_transaction():
            raise ValueError("The _process_next_compile_in_queue method should not be called in a transaction context")

        async def process_compile(compile: data.Compile, *, replace_active: bool = False) -> None:
            """
            Process a single compile: start it if no compile is currently active for its environment, unless the environment is
            halted. If replace_active is set, a new compile is started even if one is already active.

            Writes to self._env_to_compile_task => must be called under the lock.

            :param replace_active: Replace the active compile if there is any. Should only be passed if the active run is
                being wrapped up.
            """
            env: Optional[data.Environment] = await data.Environment.get_by_id(compile.environment, connection=con)
            if env is None:
                raise Exception("Can't queue compile: environment %s does not exist" % compile.environment)

            # don't execute any compiles in a halted environment
            if env.halted:
                return

            # start a new compile run iff there is no compile active or if it should be replaced
            if replace_active or compile.environment not in self._env_to_compile_task:
                # Run the compile. self._run will call back into this method when done
                self._env_to_compile_task[compile.environment] = self.add_background_task(self._run(compile))

        # acquire connection before lock to ensure lock contention remains short lived
        async with data.Environment.get_connection(connection) as con:
            async with self._write_lock_env_to_compile_task:
                # only inspect state and fetch compile details under the global lock to protect against race conditions
                if not self.fully_ready or self.is_stopping():
                    # do still mark compiles as done for accurate compile queue reporting
                    if finish_current_compile and environment is not None:
                        self._env_to_compile_task.pop(environment, None)
                    return

                c: Optional[data.Compile]
                if environment is None:
                    compiles: Sequence[data.Compile] = await data.Compile.get_next_run_all(connection=con)
                    for c in compiles:
                        await process_compile(c)
                else:
                    finishing_compile_task: Optional[asyncio.Task[object]] = (
                        self._env_to_compile_task.get(environment, None) if finish_current_compile else None
                    )
                    try:
                        c = await data.Compile.get_next_run(environment, connection=con)
                        if c is None:
                            return
                        assert c.environment == environment
                        await process_compile(c, replace_active=finish_current_compile)
                    finally:
                        # drop the current compile run if finish_current_compile=True and we didn't start a new one
                        if (
                            finishing_compile_task is not None
                            and self._env_to_compile_task.get(environment, None) is finishing_compile_task
                        ):
                            del self._env_to_compile_task[environment]

    async def _notify_listeners(self, compile: data.Compile) -> None:
        async def notify(listener: CompileStateListener) -> None:
            try:
                await listener.compile_done(compile)
            except CancelledError:
                """Propagate Cancel"""
                raise
            except Exception:
                logging.exception("CompileStateListener failed")

        blockers = asyncio.gather(*[notify(listener) for listener in self.blocking_listeners])

        async def _sub_notify() -> None:
            await asyncio.gather(*[notify(listener) for listener in self.async_listeners])
            await blockers
            await compile.update_fields(handled=True)
            LOGGER.log(const.LOG_LEVEL_TRACE, "listeners notified for %s", compile.id)

        self.add_background_task(_sub_notify())
        await blockers

    async def _recover(self) -> None:
        """Restart runs after server restart"""
        # patch up in-memory state
        async with self._queue_count_cache_lock:
            self._queue_count_cache = await data.Compile.get_total_length_of_all_compile_queues(exclude_started_compiles=False)

        # we run the recovery and start in the background to prevent deadlocks with sync handlers
        async def sub_recovery() -> None:
            unhandled = await data.Compile.get_unhandled_compiles()
            for u in unhandled:
                await self._notify_listeners(u)

            # We are ready to start!
            self.fully_ready = True
            # start a waiting compile in each environment
            await self._process_next_compile_in_queue()

        self.add_background_task(sub_recovery())

    async def resume_environment(self, environment: uuid.UUID) -> None:
        """
        Resume compiler service after halt.
        """
        await self._process_next_compile_in_queue(environment=environment)

    @protocol.handle(methods.is_compiling, environment_id="id")
    async def is_compiling(self, environment_id: uuid.UUID) -> Apireturn:
        if environment_id in self._env_to_compile_task:
            return 200
        return 204

    def _calculate_recompile_backoff_time(
        self,
        wait_time: float,
        compile_requested: datetime.datetime,
        last_compile_completed: datetime.datetime,
        now: datetime.datetime,
    ) -> float:
        if wait_time == 0:
            wait: float = 0
        else:
            if last_compile_completed >= compile_requested:
                wait = max(0, wait_time - (now - compile_requested).total_seconds())
            else:
                wait = max(0, wait_time - (now - last_compile_completed).total_seconds())
        return wait

    async def _recompile_backoff(self, compile: data.Compile) -> None:
        """
        If a recompile_backoff is set for the environment, this method waits until the backoff time has finished.
        """
        env = await data.Environment.get_by_id(compile.environment)
        if env is None:
            LOGGER.error("Unable to find environment %s in the database.", compile.environment)
            return
        wait_time: float = cast(float, await env.get(data.RECOMPILE_BACKOFF))
        if wait_time:
            LOGGER.info("The recompile_backoff environment setting is enabled and set to %s seconds.", wait_time)
        else:
            LOGGER.info("The recompile_backoff environment setting is disabled")
        last_run = await data.Compile.get_last_run(compile.environment)
        if not last_run:
            wait: float = 0
        else:
            assert last_run.completed is not None
            assert compile.requested is not None
            wait = self._calculate_recompile_backoff_time(
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
        await self._recompile_backoff(compile)

        compile_merge_key: Hashable = CompilerService._compile_merge_key(compile)
        merge_candidates: list[data.Compile] = [
            c
            for c in await data.Compile.get_next_compiles_for_environment(compile.environment)
            if not c.id == compile.id and CompilerService._compile_merge_key(c) == compile_merge_key
        ]

        runner = self._get_compile_runner(
            compile, project_dir=os.path.join(self._server_state_dir, str(compile.environment), "compiler")
        )

        merged_env_vars = dict(compile.mergeable_environment_variables)
        for merge_candidate in merge_candidates:
            for key, to_add in merge_candidate.mergeable_environment_variables.items():
                existing = merged_env_vars.get(key, None)
                if existing:
                    merged_env_vars[key] = existing + " " + to_add
                else:
                    merged_env_vars[key] = to_add

        merged_env_vars.update(compile.requested_environment_variables)

        started = datetime.datetime.now().astimezone()
        async with self._queue_count_cache_lock:
            await compile.update_fields(started=started, used_environment_variables=merged_env_vars)
            self._queue_count_cache -= 1

        # set force_update == True iff any compile request has force_update == True
        compile_data: Optional[model.CompileData]
        success, compile_data = await runner.run(force_update=any(c.force_update for c in chain([compile], merge_candidates)))

        version = runner.version

        end = datetime.datetime.now().astimezone()
        compile_data_json: Optional[dict[str, object]] = None if compile_data is None else compile_data.model_dump()
        await compile.update_fields(completed=end, success=success, version=version, compile_data=compile_data_json)
        awaitables = [
            merge_candidate.update_fields(
                started=compile.started,
                completed=end,
                success=success,
                used_environment_variables=merged_env_vars,
                version=version,
                substitute_compile_id=compile.id,
                compile_data=compile_data_json,
            )
            for merge_candidate in merge_candidates
        ]

        async with self._queue_count_cache_lock:
            await asyncio.gather(*awaitables)
            self._queue_count_cache -= len(merge_candidates)
        if self.is_stopping():
            return
        await asyncio.gather(
            self._notify_listeners(compile), *(self._notify_listeners(merge_candidate) for merge_candidate in merge_candidates)
        )
        await self._process_next_compile_in_queue(environment=compile.environment, finish_current_compile=True)

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
    async def get_compile_queue(self, env: data.Environment) -> list[model.CompileRun]:
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
        filter: Optional[dict[str, list[str]]] = None,
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

    async def environment_action_cleared(self, env: model.Environment) -> None:
        """
        Will be called when the environment is cleared

        :param env: The environment that is cleared
        """
        await self.recalculate_queue_count_cache()

    async def environment_action_deleted(self, env: model.Environment) -> None:
        """
        Will be called when the environment is deleted

        :param env: The environment that is deleted
        """
        await self.recalculate_queue_count_cache()

    async def recalculate_queue_count_cache(self) -> None:
        async with self._queue_count_cache_lock:
            self._queue_count_cache = await data.Compile.get_total_length_of_all_compile_queues()

    async def cancel_compile(self, env_id: uuid.UUID) -> None:
        """
        Cancel the ongoing compile for the given environment (if any). After the cancellation, this method
        will not start the execution of a new compile, if a compile request would be present in the compile
        queue for the given environment.

        pre-condition: The given environment is halted.

        :param env_id: The id of the environment for which the compile should be cancelled.
        """
        async with self._write_lock_env_to_compile_task:
            compile_task: Optional[asyncio.Task[None | protocol.Result]] = self._env_to_compile_task.pop(env_id, None)
        if compile_task:
            # We cancel the compile_task outside of the self._write_lock_env_to_compile_task lock to prevent lock contention.
            # This is only safe if no new compiles can be scheduled on the given environment, otherwise there is the
            # possibility that multiple compiles run concurrently on the same environment. Hence the pre-condition that
            # this method can only be called on halted environments.
            compile_task.cancel()
            try:
                # Wait until cancellation has finished
                await compile_task
            except asyncio.CancelledError:
                # Don't propagate CancelledError raised by invoking compile_task.cancel()
                pass
