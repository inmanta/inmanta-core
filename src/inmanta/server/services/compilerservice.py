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
from itertools import chain
from logging import Logger
from tempfile import NamedTemporaryFile
from typing import Dict, Hashable, List, Optional, Tuple, cast

import dateutil
import dateutil.parser
import pydantic

import inmanta.data.model as model
from inmanta import config, const, data, protocol, server
from inmanta.data import APILIMIT, InvalidSort, QueryType
from inmanta.data.paging import CompileReportPagingCountsProvider, CompileReportPagingHandler, QueryIdentifier
from inmanta.protocol import encode_token, methods, methods_v2
from inmanta.protocol.common import ReturnValue
from inmanta.protocol.exceptions import BadRequest, NotFound
from inmanta.protocol.return_value_meta import ReturnValueWithMeta
from inmanta.server import SLICE_COMPILER, SLICE_DATABASE, SLICE_TRANSPORT
from inmanta.server import config as opt
from inmanta.server.protocol import ServerSlice
from inmanta.server.validate_filter import CompileReportFilterValidator, InvalidFilter
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

    async def _run_compile_stage(self, name: str, cmd: List[str], cwd: str, env: Dict[str, str] = {}) -> data.Report:
        await self._start_stage(name, " ".join(cmd))

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
            """ Propagate Cancel """
            raise
        except Exception as e:
            await self._error("".join(traceback.format_exception(type(e), e, e.__traceback__)))
            return await self._end_stage(RETURNCODE_INTERNAL_ERROR)
        finally:
            if sub_process.returncode is None:
                # The process is still running, kill it
                sub_process.kill()

    async def run(self, force_update: Optional[bool] = False) -> Tuple[bool, Optional[model.CompileData]]:
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
                        return False, None

                elif force_update or self.request.force_update:
                    result = await self._run_compile_stage("Fetching changes", ["git", "fetch", repo_url], project_dir)
                if repo_branch:
                    branch = await self.get_branch()
                    if branch is not None and repo_branch != branch:
                        result = await self._run_compile_stage(
                            f"switching branch from {branch} to {repo_branch}", ["git", "checkout", repo_branch], project_dir
                        )

                if force_update or self.request.force_update:
                    await self._run_compile_stage("Pulling updates", ["git", "pull"], project_dir)
                    LOGGER.info("Installing and updating modules")
                    await self._run_compile_stage(
                        "Updating modules", inmanta_path + ["-vvv", "-X", "modules", "update"], project_dir
                    )

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
                "--export-compile-data",
                "--export-compile-data-file",
                compile_data_json_file.name,
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
            LOGGER.exception("An error occured while recompiling")

        finally:
            with compile_data_json_file as file:
                compile_data_json: str = file.read().decode()
                if compile_data_json:
                    try:
                        return success, model.CompileData.parse_raw(compile_data_json)
                    except json.JSONDecodeError:
                        LOGGER.warning(
                            "Failed to load compile data json for compile %s. Invalid json: '%s'",
                            (self.request.id, compile_data_json),
                        )
                    except pydantic.ValidationError:
                        LOGGER.warning(
                            "Failed to parse compile data for compile %s. Json does not match CompileData model: '%s'",
                            (self.request.id, compile_data_json),
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
        oldest_retained_date = datetime.datetime.now().astimezone() - datetime.timedelta(
            seconds=opt.server_compiler_report_retention.get()
        )
        LOGGER.info("Cleaning up compile reports that are older than %s", oldest_retained_date)
        try:
            await data.Compile.delete_older_than(oldest_retained_date)
        except CancelledError:
            """ Propagate Cancel """
            raise
        except Exception:
            LOGGER.error("The following exception occurred while cleaning up old compiler reports", exc_info=True)

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

        requested = datetime.datetime.now().astimezone()

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

    @staticmethod
    def _compile_merge_key(c: data.Compile) -> Hashable:
        """
        Returns a key used to determine whether two compiles c1 and c2 are eligible for merging. They are iff
        _compile_merge_key(c1) == _compile_merge_key(c2).
        """
        return c.to_dto().json(include={"environment", "started", "do_export", "environment_variables"})

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

            if compile.environment not in self._recompiles or self._recompiles[compile.environment].done():
                task = self.add_background_task(self._run(compile))
                self._recompiles[compile.environment] = task

    async def _dequeue(self, environment: uuid.UUID) -> None:
        async with self._global_lock:
            if self.is_stopping():
                return
            env: Optional[data.Environment] = await data.Environment.get_by_id(environment)
            if env is None:
                raise Exception("Can't queue compile: environment %s does not exist" % environment)
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
        wait_time = opt.server_autrecompile_wait.get()
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
                "server-auto-recompile-wait is enabled and set to %s seconds, "
                "waiting for %.2f seconds before running a new compile",
                wait_time,
                wait,
            )
        else:
            LOGGER.debug("Running recompile without waiting: requested at %s", compile.requested)
        await asyncio.sleep(wait)

    async def _run(self, compile: data.Compile) -> None:
        """
        Runs a compile request. At completion, looks for similar compile requests based on _compile_merge_key and marks
        those as completed as well.
        """
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
    ) -> ReturnValue[List[model.CompileReport]]:

        if limit is None:
            limit = APILIMIT
        elif limit > APILIMIT:
            raise BadRequest(f"limit parameter can not exceed {APILIMIT}, got {limit}.")
        query: Dict[str, Tuple[QueryType, object]] = {}
        if filter:
            try:
                query.update(CompileReportFilterValidator().process_filters(filter))
            except InvalidFilter as e:
                raise BadRequest(e.message) from e
        try:
            compile_report_order = data.CompileReportOrder.parse_from_string(sort)
        except InvalidSort as e:
            raise BadRequest(e.message) from e

        try:
            dtos = await data.Compile.get_compile_reports(
                environment=env.id,
                database_order=compile_report_order,
                first_id=first_id,
                last_id=last_id,
                start=start,
                end=end,
                limit=limit,
                **query,
            )
        except (data.InvalidQueryParameter, data.InvalidFieldNameException) as e:
            raise BadRequest(e.message)

        paging_handler = CompileReportPagingHandler(CompileReportPagingCountsProvider())
        metadata = await paging_handler.prepare_paging_metadata(
            QueryIdentifier(environment=env.id), dtos, limit=limit, database_order=compile_report_order, db_query=query
        )
        links = await paging_handler.prepare_paging_links(
            dtos,
            database_order=compile_report_order,
            limit=limit,
            filter=filter,
            first_id=first_id,
            last_id=last_id,
            start=start,
            end=end,
            has_next=metadata.after > 0,
            has_prev=metadata.before > 0,
        )
        return ReturnValueWithMeta(response=dtos, links=links if links else {}, metadata=vars(metadata))

    @protocol.handle(methods_v2.compile_details, env="tid")
    async def compile_details(self, env: data.Environment, id: uuid.UUID) -> model.CompileDetails:
        details = await data.Compile.get_compile_details(env.id, id)
        if not details:
            raise NotFound("The compile with the given id does not exist.")
        return details
