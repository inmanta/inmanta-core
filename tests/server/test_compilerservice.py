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
import functools
import logging
import os
import platform
import queue
import re
import shutil
import subprocess
import uuid
from asyncio import Semaphore
from collections import abc
from typing import TYPE_CHECKING, Optional

import py.path
import pytest
from pytest import approx

import inmanta.ast.export as ast_export
import inmanta.data.model as model
import inmanta.util
import utils
from inmanta import config, data
from inmanta.const import INMANTA_REMOVED_SET_ID, ParameterSource
from inmanta.data import APILIMIT, Compile, Report
from inmanta.data.model import PipConfig
from inmanta.env import PythonEnvironment, VirtualEnv
from inmanta.export import cfg_env
from inmanta.protocol import Result
from inmanta.server import SLICE_COMPILER, SLICE_SERVER, protocol
from inmanta.server.bootloader import InmantaBootloader
from inmanta.server.protocol import Server
from inmanta.server.services.compilerservice import CompilerService, CompileRun, CompileStateListener
from inmanta.server.services.notificationservice import NotificationService
from inmanta.util import ensure_directory_exist
from server.conftest import EnvironmentFactory
from utils import LogSequence, log_contains, report_db_index_usage, retry_limited, wait_for_version

logger = logging.getLogger("inmanta.test.server.compilerservice")

if TYPE_CHECKING:
    from conftest import CompileRunnerMock


@pytest.fixture
async def compilerservice(server_config, init_dataclasses_and_load_schema):
    server = Server()
    cs = CompilerService()
    await cs.prestart(server)
    await cs.start()
    server.add_slice(cs)
    notification_service = NotificationService()
    await notification_service.prestart(server)
    await notification_service.start()
    yield cs
    await notification_service.prestop()
    await notification_service.stop()
    await cs.prestop()
    await cs.stop()


async def compile_and_assert(
    env,
    client,
    project_work_dir: str,
    export=True,
    meta={},
    env_vars={},
    update=False,
    exporter_plugin=None,
) -> tuple[CompileRun, abc.Mapping[str, object]]:
    """
    Create a compile data object and run it. Returns the compile run itself and the reports for each stage.
    """
    compile = data.Compile(
        remote_id=uuid.uuid4(),
        environment=env.id,
        do_export=export,
        metadata=meta,
        requested_environment_variables=env_vars,
        used_environment_variables=env_vars,
        force_update=update,
        exporter_plugin=exporter_plugin,
    )
    await compile.insert()

    # compile with export
    cr = CompileRun(compile, project_work_dir)
    await cr.run()

    # get and process reports
    result = await client.get_report(compile.id)
    assert result.code == 200
    stages = result.result["report"]["reports"]
    if export:
        assert cr.version > 0
        result = await client.get_version(env.id, cr.version)
        assert result.code == 200
        metadata = result.result["model"]["version_info"]["export_metadata"]
        for k, v in meta.items():
            assert k in metadata
            assert v == metadata[k]

    print(stages)

    stage_by_name = {stage["name"]: stage for stage in stages}

    return cr, stage_by_name


async def test_scheduler(server_config, init_dataclasses_and_load_schema, caplog):
    """Test the scheduler part in isolation, mock out compile runner and listen to state updates"""

    class Collector(CompileStateListener):
        """
        Collect all state updates, optionally hang the processing of listeners
        """

        def __init__(self) -> None:
            self.seen = []
            self.preseen = []
            self.lock = Semaphore(1)
            self.blocking = False

        def reset(self) -> None:
            self.seen = []
            self.preseen = []

        async def compile_done(self, compile: data.Compile) -> None:
            self.preseen.append(compile)
            print("Got compile done for ", compile.remote_id)
            logger.info("Got compile done for %s (blocking: %s)", compile.remote_id, self.blocking)
            async with self.lock:
                logger.info("INTO LOCK %s (blocking: %s)", compile.remote_id, self.blocking)
                self.seen.append(compile)

        async def hang(self) -> None:
            await self.lock.acquire()

        def release(self) -> None:
            self.lock.release()

        def verify(self, envs: uuid.UUID) -> None:
            assert sorted([x.remote_id for x in self.seen]) == sorted(envs)
            self.reset()

        def is_blocking(self) -> bool:
            return self.blocking

    class HangRunner:
        """
        compile runner mock, hang until released
        """

        def __init__(self, compile: data.Compile):
            self.lock = Semaphore(0)
            self.started = False
            self.done = False
            self.version = None
            self.request = compile

        async def run(self, force_update: Optional[bool] = False):
            print("Start Run: ", self.request.id, self.request.environment)

            self.started = True
            await self.lock.acquire()
            self.done = True
            print("END Run: ", self.request.id, self.request.environment)
            return True, None

        def release(self):
            self.lock.release()

    class HookedCompilerService(CompilerService):
        """
        hook in the hangrunner
        """

        def __init__(self) -> None:
            super().__init__()
            self.locks = {}

        def _get_compile_runner(self, compile: data.Compile, project_dir: str) -> HangRunner:
            runner = HangRunner(compile)
            self.locks[compile.remote_id] = runner
            return runner

        def get_runner(self, remote_id: uuid.UUID) -> HangRunner:
            return self.locks.get(remote_id)

    async def compiler_cache_consistent(expected: int) -> None:
        async def inner() -> bool:
            async with cs._queue_count_cache_lock:
                not_done = await data.Compile.get_total_length_of_all_compile_queues()
                print(expected, cs._queue_count_cache, not_done)
                return cs._queue_count_cache == not_done == expected

        # Use retry_limited here, because after the runner has finished executing, it might take
        # some time until the compiler service has registered the data in the database.
        await retry_limited(inner, 1)

    # manual setup of server
    server = Server()
    cs = HookedCompilerService()
    await cs.prestart(server)
    await cs.start()
    server.add_slice(cs)
    notification_service = NotificationService()
    await notification_service.prestart(server)
    await notification_service.start()
    collector = Collector()
    cs.add_listener(collector)

    hanging_collector = Collector()
    hanging_collector.blocking = True
    cs.add_listener(hanging_collector)

    async def request_compile(env: data.Environment) -> uuid.UUID:
        """Request compile for given env, return remote_id"""
        logger.info("Requesting compile for %s", env)
        u1 = uuid.uuid4()
        # add unique environment variables to prevent merging in request_recompile
        await cs.request_recompile(env, False, False, u1, env_vars={"uuid": str(u1)})
        results = await data.Compile.get_by_remote_id(env.id, u1)
        assert len(results) == 1
        assert results[0].remote_id == u1
        print("request: ", results[0].id, env.id)
        return u1

    async def get_compile(env: data.Environment, remote_id: uuid.UUID) -> data.Compile:
        results = await data.Compile.get_by_remote_id(env.id, remote_id)
        assert len(results) == 1
        assert results[0].remote_id == remote_id
        return results[0]

    async def is_handled(env: data.Environment, remote_id: uuid.UUID) -> bool:
        compile = await get_compile(env, remote_id)
        return compile.handled

    # setup projects in the database
    project = data.Project(name="test")
    await project.insert()
    env1 = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env1.insert()
    env2 = data.Environment(name="dev2", project=project.id, repo_url="", repo_branch="")
    await env2.insert()

    # setup series of compiles for two envs
    # e1 is for a plain run
    # e2 is for server restart
    e1 = [await request_compile(env1) for i in range(3)]
    e2 = [await request_compile(env2) for i in range(4)]
    print("env 1:", e1)

    async def check_compile_in_sequence(
        env: data.Environment, remote_ids: list[uuid.UUID], idx: int, can_handle: bool = True
    ) -> None:
        """
        Check integrity of a compile sequence and progress the hangrunner.
        """
        before = remote_ids[:idx]

        for rid in before:
            prevrunner = cs.get_runner(rid)
            assert prevrunner.done

        if idx < len(remote_ids):
            current = remote_ids[idx]
            after = remote_ids[idx + 1 :]

            assert await cs.is_compiling(env.id) == 200

            await retry_limited(lambda: cs.get_runner(current) is not None, 1)
            await retry_limited(lambda: cs.get_runner(current).started, 1)

            for rid in after:
                nextrunner = cs.get_runner(rid)
                assert nextrunner is None

            logger.info("Test in-line handlers by making it block for %s", current)
            await hanging_collector.hang()

            logger.info("Progress compile for %s", current)
            cs.get_runner(current).release()
            await asyncio.sleep(0)

            # Wait for done
            await retry_limited(lambda: cs.get_runner(current).done, 1)
            logger.info("Compile done for %s", current)

            # Ensure we are blocked on the handler
            compile = await get_compile(env, current)
            assert compile.handled is False

            # Proceed
            logger.info("Start handling for %s", current)
            hanging_collector.release()
            if can_handle:
                await retry_limited(functools.partial(is_handled, env, current), 1)
                logger.info("Handling done for %s", current)
        else:

            async def isdone():
                return await cs.is_compiling(env.id) == 204

            await retry_limited(isdone, 1)

    await compiler_cache_consistent(5)

    # run through env1, entire sequence
    for i in range(4):
        await check_compile_in_sequence(env1, e1, i)
        if i < 2:
            # First one is never queued, so not counted
            # Last iteration here doesn't de-queue an item, but allows it to complete
            # So don't handle last 2
            await compiler_cache_consistent(4 - i)

    await compiler_cache_consistent(3)

    collector.verify(e1)
    print("env1 done")

    print("env2 ", e2)
    # make event collector hang
    await collector.hang()
    # progress two steps into env2
    for i in range(2):
        await check_compile_in_sequence(env2, e2, i, can_handle=False)
        await compiler_cache_consistent(2 - i)

    assert not collector.seen
    print(collector.preseen)
    await retry_limited(lambda: len(collector.preseen) == 2, 1)

    # test server restart
    await notification_service.prestop()
    await notification_service.stop()
    await cs.prestop()
    await cs.stop()

    # in the log, find cancel of compile(hangs) and handler(hangs)
    LogSequence(caplog, allow_errors=False).contains("inmanta.util", logging.WARNING, "was cancelled").contains(
        "inmanta.util", logging.WARNING, "was cancelled"
    ).no_more_errors()

    print("restarting")

    # restart new server
    cs = HookedCompilerService()
    await cs.prestart(server)
    collector = Collector()
    cs.add_listener(collector)

    hanging_collector = Collector()
    hanging_collector.blocking = True
    await hanging_collector.hang()  # Can we boot when a handler hangs?
    cs.add_listener(hanging_collector)
    await cs.start()

    # Can we request compiles while recovery is ongoing?
    extra_compile = await request_compile(env2)
    e2.append(extra_compile)

    # We haven't started, because we hang on a handler,
    assert len(cs._env_to_compile_task) == 0

    # Continue
    hanging_collector.release()

    # two in cache, one running
    await compiler_cache_consistent(2)

    # complete the sequence, expect re-run of third compile
    for i in range(4):
        await check_compile_in_sequence(env2, e2[2:], i)
    await compiler_cache_consistent(0)

    # all are re-run, entire sequence present
    collector.verify(e2)

    await report_db_index_usage()


@pytest.mark.slowtest
@pytest.mark.parametrize("no_agent", [True])
async def test_compile_runner(environment_factory: EnvironmentFactory, server, client, tmpdir):
    testmarker_env = "TESTMARKER"
    no_marker = "__no__marker__"
    marker_print = "_INM_MM:"
    marker_print2 = "_INM_MM2:"
    marker_print3 = "_INM_MM3:"

    def make_main(marker_print):
        return f"""
    import std::testing
    marker = std::get_env("{testmarker_env}","{no_marker}")
    std::print("{marker_print} {{{{marker}}}}")

    std::testing::NullResource(name="test")
        """

    env = await environment_factory.create_environment(make_main(marker_print))
    env2 = await environment_factory.create_environment(make_main(marker_print2))

    project_work_dir = os.path.join(tmpdir, "work")
    ensure_directory_exist(project_work_dir)

    def _compile_and_assert(env, export=True, meta={}, env_vars={}, update=False, exporter_plugin=None):
        return compile_and_assert(
            env=env,
            client=client,
            project_work_dir=project_work_dir,
            export=export,
            meta=meta,
            env_vars=env_vars,
            update=update,
            exporter_plugin=exporter_plugin,
        )

    # with export
    compile, stages = await _compile_and_assert(env=env, export=True, meta={"type": "Test"})
    assert stages["Init"]["returncode"] == 0
    assert stages["Cloning repository"]["returncode"] == 0
    assert stages["Venv check"]["returncode"] == 0
    assert stages["Installing modules"]["returncode"] == 0
    assert stages["Recompiling configuration model"]["returncode"] == 0
    out = stages["Recompiling configuration model"]["outstream"]
    assert f"{marker_print} {no_marker}" in out
    assert len(stages) == 5
    assert compile.version is not None

    # no export
    compile, stages = await _compile_and_assert(env=env, export=False)
    assert stages["Init"]["returncode"] == 0
    assert stages["Venv check"]["returncode"] == 0
    assert stages["Recompiling configuration model"]["returncode"] == 0
    out = stages["Recompiling configuration model"]["outstream"]
    assert f"{marker_print} {no_marker}" in out
    assert len(stages) == 3
    assert compile.version is None

    # env vars
    marker = str(uuid.uuid4())
    compile, stages = await _compile_and_assert(env=env, export=False, env_vars={testmarker_env: marker})
    assert len(compile.request.requested_environment_variables) == 1
    assert stages["Init"]["returncode"] == 0
    assert f"Using extra environment variables during compile TESTMARKER='{marker}'" in stages["Init"]["outstream"]
    assert stages["Venv check"]["returncode"] == 0
    assert stages["Recompiling configuration model"]["returncode"] == 0
    out = stages["Recompiling configuration model"]["outstream"]
    assert f"{marker_print} {marker}" in out
    assert len(stages) == 3
    assert compile.version is None

    # switch branch
    compile, stages = await _compile_and_assert(env=env2, export=False)
    assert stages["Init"]["returncode"] == 0
    assert stages[f"Switching branch from {env.repo_branch} to {env2.repo_branch}"]["returncode"] == 0
    assert stages["Venv check"]["returncode"] == 0
    assert stages["Installing modules"]["returncode"] == 0
    assert stages["Recompiling configuration model"]["returncode"] == 0
    out = stages["Recompiling configuration model"]["outstream"]
    assert f"{marker_print2} {no_marker}" in out
    assert len(stages) == 5
    assert compile.version is None

    # update with no update
    compile, stages = await _compile_and_assert(env=env2, export=False, update=True)
    assert stages["Init"]["returncode"] == 0
    assert stages["Venv check"]["returncode"] == 0
    assert stages["Pulling updates"]["returncode"] == 0
    assert stages["Uninstall inmanta packages from the compiler venv"]["returncode"] == 0
    assert stages["Updating modules"]["returncode"] == 0
    assert stages["Recompiling configuration model"]["returncode"] == 0
    out = stages["Recompiling configuration model"]["outstream"]
    assert f"{marker_print2} {no_marker}" in out
    assert len(stages) == 6
    assert compile.version is None

    environment_factory.write_main(make_main(marker_print3))
    compile, stages = await _compile_and_assert(env=env2, export=False, update=True)
    assert stages["Init"]["returncode"] == 0
    assert stages["Venv check"]["returncode"] == 0
    assert stages["Pulling updates"]["returncode"] == 0
    assert stages["Uninstall inmanta packages from the compiler venv"]["returncode"] == 0
    assert stages["Updating modules"]["returncode"] == 0
    assert stages["Recompiling configuration model"]["returncode"] == 0
    out = stages["Recompiling configuration model"]["outstream"]
    assert f"{marker_print3} {no_marker}" in out
    assert len(stages) == 6
    assert compile.version is None

    # Ensure that the pip binary created in the venv of the compiler service works correctly
    pip_binary_path = os.path.join(project_work_dir, ".env", "bin", "pip")
    output = subprocess.check_output([pip_binary_path, "list", "--format", "json"], encoding="utf-8")
    assert "inmanta-core" in output


@pytest.mark.slowtest
async def test_server_side_compile_with_ssl_enabled(
    tmpdir, request, environment_factory: EnvironmentFactory, server_multi, client_multi, environment_multi
) -> None:
    """
    Ensure that server-side compiles work correctly when SSL is enabled on the server, but the
    .inmanta file present in the project disables SSL (issue: #4640).
    """
    if request.node.callspec.id != "SSL" and request.node.callspec.id != "Normal":
        # Only run this test case once for a server with SSL enabled and once for a server with SSL disabled.
        return

    ssl_enabled_on_server = "SSL" in request.node.callspec.id

    project_work_dir = os.path.join(tmpdir, "work")
    ensure_directory_exist(project_work_dir)

    main_cf = """
import std::testing
std::testing::NullResource(name="test")
    """.strip()

    # Add .inmanta file with inverse SSL config as the server itself.
    dot_inmanta = f"""
[compiler_rest_transport]
ssl={str(not ssl_enabled_on_server).lower()}
    """.strip()

    env = await environment_factory.create_environment(main=main_cf)
    environment_factory.write_file(path=".inmanta", content=dot_inmanta)

    compile, stages = await compile_and_assert(env=env, client=client_multi, project_work_dir=project_work_dir, export=True)
    assert all(stage["returncode"] == 0 for stage in stages.values())


@pytest.mark.slowtest
async def test_compilerservice_compile_data(environment_factory: EnvironmentFactory, client, server) -> None:
    async def get_compile_data(main: str) -> model.CompileData:
        env: data.Environment = await environment_factory.create_environment(main)
        result: Result = await client.notify_change(env.id)
        assert result.code == 200

        async def compile_done():
            return (await client.get_compile_queue(env.id)).result["queue"] == []

        await retry_limited(compile_done, 10)

        reports = await client.get_reports(env.id)
        assert reports.code == 200
        assert len(reports.result["reports"]) == 1
        compile_id: str = reports.result["reports"][0]["id"]
        compile_data_a = model.CompileData(**reports.result["reports"][0]["compile_data"])

        result = await client.get_compile_data(uuid.UUID(compile_id))
        assert result.code == 200
        assert "data" in result.result
        compile_data: model.CompileData = model.CompileData(**result.result["data"])
        assert compile_data_a == compile_data
        return compile_data

    errors0: list[ast_export.Error] = (await get_compile_data("x = 0")).errors
    assert len(errors0) == 0

    errors1: list[ast_export.Error] = (await get_compile_data("x = 0 x = 1")).errors
    assert len(errors1) == 1
    error: ast_export.Error = errors1[0]
    assert error.category == ast_export.ErrorCategory.runtime
    assert error.type == "inmanta.ast.DoubleSetException"
    assert error.message == "value set twice:\n\told value: 0\n\t\tset at ./main.cf:1\n\tnew value: 1\n\t\tset at ./main.cf:1\n"


@pytest.mark.parametrize("use_trx_based_api", [True, False])
async def test_e2e_recompile_failure(compilerservice: CompilerService, use_trx_based_api: bool):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    async def request_compile(remote_id: uuid.UUID, env_vars: dict[str, str]) -> None:
        if use_trx_based_api:
            async with data.Environment.get_connection() as connection:
                async with connection.transaction():
                    compile_id, warnings = await compilerservice.request_recompile(
                        env=env,
                        force_update=False,
                        do_export=False,
                        remote_id=remote_id,
                        env_vars=env_vars,
                        connection=connection,
                        in_db_transaction=True,
                    )
                assert compile_id is not None, warnings
            await compilerservice.notify_compile_request_committed(compile_id)
        else:
            await compilerservice.request_recompile(
                env=env, force_update=False, do_export=False, remote_id=remote_id, env_vars=env_vars
            )

    u1 = uuid.uuid4()
    await request_compile(remote_id=u1, env_vars={"my_unique_var": str(u1)})

    u2 = uuid.uuid4()
    await request_compile(remote_id=u2, env_vars={"my_unique_var": str(u2)})

    async def compile_done():
        res = await compilerservice.is_compiling(env.id)
        print(res)
        return res == 204 and compilerservice._queue_count_cache == 0

    await retry_limited(compile_done, 10)
    # All compiles are finished. The queue should be empty
    assert compilerservice._queue_count_cache == 0

    _, all_compiles = await compilerservice.get_reports(env)
    all_reports = {i["remote_id"]: await compilerservice.get_report(i["id"]) for i in all_compiles["reports"]}

    def assert_report(uid):
        code, report = all_reports[uid]
        report = report["report"]
        assert report["remote_id"] == uid
        assert not report["success"]
        reports = report["reports"]
        reports = {r["name"]: r for r in reports}

        # stages
        init = reports["Init"]
        assert not init["errstream"]
        assert "no project found in" in init["outstream"] and "and no repository set" in init["outstream"]

        # no compile report
        assert len(reports) == 1

        return report["requested"], report["started"], report["completed"]

    r1, s1, f1 = assert_report(u1)
    r2, s2, f2 = assert_report(u2)

    assert r2 > r1
    assert r1 < s1 < f1
    assert r2 < s2 < f2
    assert f1 < s2


@pytest.mark.slowtest
async def test_server_partial_compile(server, client, environment, monkeypatch):
    """
    Test a partial_compile on the server
    """
    project_dir = os.path.join(server.get_slice(SLICE_SERVER)._server_storage["server"], str(environment), "compiler")
    project_source = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "project")
    print("Project at: ", project_dir)

    shutil.copytree(project_source, project_dir)
    subprocess.check_output(["git", "init"], cwd=project_dir)
    subprocess.check_output(["git", "add", "*"], cwd=project_dir)
    subprocess.check_output(["git", "config", "user.name", "Unit"], cwd=project_dir)
    subprocess.check_output(["git", "config", "user.email", "unit@test.example"], cwd=project_dir)
    subprocess.check_output(["git", "commit", "-m", "unit test"], cwd=project_dir)

    # add main.cf
    with open(os.path.join(project_dir, "main.cf"), "w", encoding="utf-8") as fd:
        fd.write("")
    env = await data.Environment.get_by_id(environment)
    compilerslice: CompilerService = server.get_slice(SLICE_COMPILER)
    remote_id1 = uuid.uuid4()

    async def wait_for_report() -> bool:
        report = await client.get_report(compile_id)
        if report.code != 200:
            return False
        return report.result["report"]["completed"] is not None

    def verify_command_report(report: dict, expected: str) -> bool:
        """
        verify that the expected string is present in the command field of the 'Recompiling configuration model' report
        """
        reports = report.result["report"]["reports"]
        report = [x for x in reports if x["name"] == "Recompiling configuration model"][0]
        return expected in report["command"]

    def set_removal_was_requested(report: dict, removed_sets: Optional[set[str]] = None) -> bool:
        """
        Returns True if a resource set removal was requested for a given compile report.
        In addition, if the removed_sets param is set, the removal of these specific sets is checked.

        :param report: Compile report for which to check if a resource set removal was requested
        """
        if not removed_sets:
            return INMANTA_REMOVED_SET_ID in report["requested_environment_variables"]

        assert INMANTA_REMOVED_SET_ID in report["requested_environment_variables"]
        return set(report["requested_environment_variables"][INMANTA_REMOVED_SET_ID].split()) == removed_sets

    # Do a compile
    compile_id, _ = await compilerslice.request_recompile(env, force_update=False, do_export=False, remote_id=remote_id1)

    await retry_limited(wait_for_report, 10)
    report = await client.get_report(compile_id)
    assert not verify_command_report(report, "--partial")
    assert not set_removal_was_requested(report.result["report"])

    # Do a partial compile
    compile_id, _ = await compilerslice.request_recompile(
        env, force_update=False, do_export=False, remote_id=remote_id1, partial=True
    )

    await retry_limited(wait_for_report, 10)
    report = await client.get_report(compile_id)
    assert verify_command_report(report, "--partial")
    assert not set_removal_was_requested(report.result["report"])

    # Do a partial compile with removed resource_sets
    compile_id, _ = await compilerslice.request_recompile(
        env,
        force_update=False,
        do_export=False,
        remote_id=remote_id1,
        partial=True,
        env_vars={INMANTA_REMOVED_SET_ID: "a b c"},
    )

    await retry_limited(wait_for_report, 10)
    report = await client.get_report(compile_id)
    assert verify_command_report(report, "--partial")
    assert set_removal_was_requested(report.result["report"], {"a", "b", "c"})


@pytest.mark.slowtest
@pytest.mark.parametrize("no_agent", [True])
async def test_server_recompile(server, client, environment, monkeypatch):
    """
    Test a recompile on the server and verify recompile triggers
    """

    project_dir = os.path.join(server.get_slice(SLICE_SERVER)._server_storage["server"], str(environment), "compiler")
    project_source = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "project")
    print("Project at: ", project_dir)

    shutil.copytree(project_source, project_dir)
    subprocess.check_output(["git", "init"], cwd=project_dir)
    subprocess.check_output(["git", "add", "*"], cwd=project_dir)
    subprocess.check_output(["git", "config", "user.name", "Unit"], cwd=project_dir)
    subprocess.check_output(["git", "config", "user.email", "unit@test.example"], cwd=project_dir)
    subprocess.check_output(["git", "commit", "-m", "unit test"], cwd=project_dir)

    # Set environment variable to be passed to the compiler
    key_env_var = "TEST_MESSAGE"
    value_env_var = "a_message"
    monkeypatch.setenv(key_env_var, value_env_var)

    # add main.cf
    with open(os.path.join(project_dir, "main.cf"), "w", encoding="utf-8") as fd:
        fd.write(
            f"""
        import std::testing

        host = std::Host(name="test", os=std::linux)
        std::testing::NullResource(name=host.name)
        std::print(std::get_env("{key_env_var}"))
"""
        )

    logger.info("request a compile")
    result = await client.notify_change(environment)
    assert result.code == 200

    logger.info("wait for 1")
    versions = await wait_for_version(client, environment, 1, compile_timeout=40)
    assert versions["versions"][0]["total"] == 1
    assert versions["versions"][0]["version_info"]["export_metadata"]["type"] == "api"

    # get compile reports and make sure the environment variables are not logged
    reports = await client.get_reports(environment)
    assert reports.code == 200
    assert len(reports.result["reports"]) == 1
    env_vars_compile = reports.result["reports"][0]["environment_variables"]
    assert key_env_var not in env_vars_compile

    # get report
    compile_report = await client.get_report(reports.result["reports"][0]["id"])
    assert compile_report.code == 200
    report_map = {r["name"]: r for r in compile_report.result["report"]["reports"]}
    assert value_env_var in report_map["Recompiling configuration model"]["outstream"]

    # set a parameter without requesting a recompile
    result = await client.set_param(environment, id="param1", value="test", source=ParameterSource.plugin)
    assert result.code == 200
    versions = await wait_for_version(client, environment, 1)
    assert versions["count"] == 1

    logger.info("request second compile")
    # set a new parameter and request a recompile
    result = await client.set_param(environment, id="param2", value="test", source=ParameterSource.plugin, recompile=True)
    assert result.code == 200
    logger.info("wait for 2")
    versions = await wait_for_version(client, environment, 2)
    assert versions["versions"][0]["version_info"]["export_metadata"]["type"] == "param"
    assert versions["count"] == 2

    # update the parameter to the same value -> no compile
    result = await client.set_param(environment, id="param2", value="test", source=ParameterSource.plugin, recompile=True)
    assert result.code == 200
    versions = await wait_for_version(client, environment, 2)
    assert versions["count"] == 2

    # update the parameter to a new value
    result = await client.set_param(environment, id="param2", value="test2", source=ParameterSource.plugin, recompile=True)
    assert result.code == 200
    logger.info("wait for 3")
    versions = await wait_for_version(client, environment, 3)
    assert versions["count"] == 3

    # set a full compile schedule
    async def schedule_soon() -> None:
        soon: datetime.datetime = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=2)
        cron_soon: str = "%d %d %d * * * *" % (soon.second, soon.minute, soon.hour)
        result = await client.environment_settings_set(environment, id="auto_full_compile", value=cron_soon)
        assert result.code == 200

    async def is_compiling() -> None:
        return (await client.is_compiling(environment)).code == 200

    await schedule_soon()
    await retry_limited(is_compiling, 3)
    logger.info("wait for 4")
    versions = await wait_for_version(client, environment, 4)
    assert versions["count"] == 4

    # override existing schedule
    await schedule_soon()
    await retry_limited(is_compiling, 3)
    logger.info("wait for 5")
    versions = await wait_for_version(client, environment, 5)
    assert versions["count"] == 5

    # delete schedule, verify it is cancelled
    await schedule_soon()
    result = await client.environment_setting_delete(environment, id="auto_full_compile")
    assert result.code == 200
    with pytest.raises(AssertionError, match="Bounded wait failed"):
        await retry_limited(is_compiling, 4)
    result = await client.list_versions(environment)
    assert result.code == 200
    assert result.result["count"] == 5

    # override with schedule in far future (+- 24h), check that it doesn't trigger an immediate recompile
    recent: datetime.datetime = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=2)
    cron_recent: str = "%d %d %d * * * *" % (recent.second, recent.minute, recent.hour)
    result = await client.environment_settings_set(environment, id="auto_full_compile", value=cron_recent)
    assert result.code == 200
    with pytest.raises(AssertionError, match="Bounded wait failed"):
        await retry_limited(is_compiling, 4)
    result = await client.list_versions(environment)
    assert result.code == 200
    assert result.result["count"] == 5

    # clear the environment
    state_dir = config.state_dir.get()
    project_dir = os.path.join(state_dir, "server", environment)
    assert os.path.exists(project_dir)

    result = await client.clear_environment(environment)
    assert result.code == 200

    assert not os.path.exists(project_dir)


@pytest.mark.slowtest
async def test_server_recompile_param_fact_v2(server, client, environment):
    """
    Test recompile triggers when setting params and facts with the v2 endpoint
    """

    project_dir = os.path.join(server.get_slice(SLICE_SERVER)._server_storage["server"], str(environment), "compiler")
    project_source = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "project")

    shutil.copytree(project_source, project_dir)

    # add main.cf
    with open(os.path.join(project_dir, "main.cf"), "w", encoding="utf-8") as fd:
        fd.write(
            """
import std::testing
std::testing::NullResource(name='test')
"""
        )

    logger.info("request a compile")
    result = await client.notify_change(environment)
    assert result.code == 200

    versions = await wait_for_version(client, environment, cnt=1, compile_timeout=40)
    assert versions["versions"][0]["total"] == 1
    assert versions["versions"][0]["version_info"]["export_metadata"]["type"] == "api"

    # get an existing resource
    resources = await data.Resource.get_resources_for_version(environment, 1)
    resource_id = resources[0].resource_id

    # set a parameter without requesting a recompile
    result = await client.set_parameter(environment, name="param1", value="test", source=ParameterSource.plugin)
    assert result.code == 200
    versions = await wait_for_version(client, environment, cnt=1)
    assert versions["count"] == 1

    logger.info("request second compile")
    # set a new parameter and request a recompile
    result = await client.set_parameter(environment, name="param2", value="test", source=ParameterSource.plugin, recompile=True)
    assert result.code == 200
    logger.info("wait for 2")
    versions = await wait_for_version(client, environment, cnt=2)
    assert versions["versions"][0]["version_info"]["export_metadata"]["type"] == "param"
    assert versions["count"] == 2

    # update the parameter to the same value -> no compile
    result = await client.set_parameter(environment, name="param2", value="test", source=ParameterSource.plugin, recompile=True)
    assert result.code == 200
    versions = await wait_for_version(client, environment, cnt=2)
    assert versions["count"] == 2

    # update the parameter to a new value
    result = await client.set_parameter(
        environment, name="param2", value="test2", source=ParameterSource.plugin, recompile=True
    )
    assert result.code == 200
    logger.info("wait for 3")
    versions = await wait_for_version(client, environment, cnt=3)
    assert versions["count"] == 3

    # set a fact without requesting a recompile
    result = await client.set_fact(
        environment, name="fact1", value="test", source=ParameterSource.fact, resource_id=resource_id
    )
    assert result.code == 200
    versions = await wait_for_version(client, environment, cnt=3)
    assert versions["count"] == 3

    # set a new fact and request a recompile
    result = await client.set_fact(
        environment, name="fact2", value="test", source=ParameterSource.fact, resource_id=resource_id, recompile=True
    )
    assert result.code == 200
    logger.info("wait for 4")
    versions = await wait_for_version(client, environment, cnt=4)
    assert versions["versions"][0]["version_info"]["export_metadata"]["type"] == "fact"
    assert versions["count"] == 4

    # update the fact to the same value -> no compile
    result = await client.set_fact(
        environment, name="fact2", value="test", source=ParameterSource.fact, resource_id=resource_id, recompile=True
    )
    assert result.code == 200
    versions = await wait_for_version(client, environment, cnt=4)
    assert versions["count"] == 4

    # update the fact to a new value
    result = await client.set_fact(
        environment, name="fact2", value="test2", source=ParameterSource.fact, resource_id=resource_id, recompile=True
    )
    assert result.code == 200
    logger.info("wait for 5")
    versions = await wait_for_version(client, environment, cnt=5)
    assert versions["count"] == 5


async def run_compile_and_wait_until_compile_is_done(
    compiler_service: CompilerService,
    compiler_queue: queue.Queue["CompileRunnerMock"],
    env_id: uuid.UUID,
    fail: Optional[bool] = None,
    fail_on_pull=False,
) -> "CompileRunnerMock":
    """
    Unblock the first compile in the compiler queue and wait until the compile finishes.
    """
    # prevent race conditions where compile request is not yet in queue
    await retry_limited(lambda: not compiler_queue.empty(), timeout=10)
    run = compiler_queue.get(block=True)
    if fail is not None:
        run._make_compile_fail = fail
    run._make_pull_fail = fail_on_pull

    current_task = compiler_service._env_to_compile_task[env_id]
    run.block = False

    def _is_compile_finished() -> bool:
        if env_id not in compiler_service._env_to_compile_task:
            return True
        if current_task is not compiler_service._env_to_compile_task[env_id]:
            return True
        return False

    await retry_limited(_is_compile_finished, timeout=10)
    return run


async def test_compileservice_queue(mocked_compiler_service_block: queue.Queue, server, client, environment):
    """
    Test the inspection of the compile queue. The compile runner is mocked out so the "started" field does not have the
    correct value in this test.
    """
    env = await data.Environment.get_by_id(environment)
    compilerslice: CompilerService = server.get_slice(SLICE_COMPILER)

    # Queue = [
    #
    # ]
    result = await client.get_compile_queue(environment)
    assert len(result.result["queue"]) == 0
    assert result.code == 200

    # request a compile
    remote_id1 = uuid.uuid4()
    await compilerslice.request_recompile(
        env=env, force_update=False, do_export=False, remote_id=remote_id1, env_vars={"my_unique_var": "1"}
    )

    # api should return one
    # Queue = [
    #   remote_id1 (Running)
    # ]
    result = await client.get_compile_queue(environment)
    assert len(result.result["queue"]) == 1
    assert result.result["queue"][0]["remote_id"] == str(remote_id1)
    assert result.code == 200
    # None in the queue, all running
    await retry_limited(lambda: compilerslice._queue_count_cache == 0, 10)

    # request a compile
    remote_id2 = uuid.uuid4()
    compile_id2, _ = await compilerslice.request_recompile(env=env, force_update=False, do_export=False, remote_id=remote_id2)

    # api should return two
    # Queue = [
    #   remote_id1 (Running),
    #   remote_id2 (Waiting),
    # ]
    result = await client.get_compile_queue(environment)
    assert len(result.result["queue"]) == 2
    assert result.result["queue"][1]["remote_id"] == str(remote_id2)
    assert result.code == 200
    # 1 in the queue, 1 running
    await retry_limited(lambda: compilerslice._queue_count_cache == 1, 10)

    # request a compile with do_export=True
    remote_id3 = uuid.uuid4()
    compile_id3, _ = await compilerslice.request_recompile(env=env, force_update=False, do_export=True, remote_id=remote_id3)

    # Queue = [
    #   remote_id1 (Running),
    #   remote_id2 (Waiting),
    #   remote_id3 (Waiting),
    # ]
    result = await client.get_compile_queue(environment)
    assert len(result.result["queue"]) == 3
    assert result.result["queue"][2]["remote_id"] == str(remote_id3)
    assert result.code == 200
    # 2 in the queue, 1 running
    await retry_limited(lambda: compilerslice._queue_count_cache == 2, 10)

    # request a compile with do_export=False -> expect merge with compile2
    remote_id4 = uuid.uuid4()
    compile_id4, _ = await compilerslice.request_recompile(env=env, force_update=False, do_export=False, remote_id=remote_id4)

    # Queue = [
    #   remote_id1 (Running),
    #   remote_id2 (Waiting), <--+
    #   remote_id3 (Waiting),    |-- same _compile_merge_key
    #   remote_id4 (Waiting), <--+
    # ]
    result = await client.get_compile_queue(environment)
    assert len(result.result["queue"]) == 4
    assert result.result["queue"][3]["remote_id"] == str(remote_id4)
    assert result.code == 200
    # 3 in the queue, 1 running
    await retry_limited(lambda: compilerslice._queue_count_cache == 3, 10)

    # request a compile with do_export=True -> expect merge with compile3, expect force_update == True for the compile
    remote_id5 = uuid.uuid4()
    compile_id5, _ = await compilerslice.request_recompile(env=env, force_update=True, do_export=True, remote_id=remote_id5)
    remote_id6 = uuid.uuid4()
    compile_id6, _ = await compilerslice.request_recompile(env=env, force_update=False, do_export=True, remote_id=remote_id6)

    # Queue = [
    #   remote_id1 (Running),
    #   remote_id2 (Waiting), <----------+
    #   remote_id3 (Waiting), <----+     |-- same _compile_merge_key
    #   remote_id4 (Waiting), <--- | ----+
    #   remote_id5 (Waiting), <----+
    #   remote_id6 (Waiting), <----+-- same _compile_merge_key
    # ]

    # request with partial, will not be merged
    remote_id7 = uuid.uuid4()
    compile_id7, _ = await compilerslice.request_recompile(
        env=env, force_update=False, do_export=True, remote_id=remote_id7, partial=True
    )

    # Queue = [
    #   remote_id1 (Running),
    #   remote_id2 (Waiting), <----------+
    #   remote_id3 (Waiting), <----+     |-- same _compile_merge_key
    #   remote_id4 (Waiting), <--- | ----+
    #   remote_id5 (Waiting), <----+
    #   remote_id6 (Waiting), <----+-- same _compile_merge_key
    #   remote_id7 (Waiting),
    # ]

    result = await client.get_compile_queue(environment)
    assert len(result.result["queue"]) == 7
    assert result.result["queue"][4]["remote_id"] == str(remote_id5)
    assert result.result["queue"][5]["remote_id"] == str(remote_id6)
    assert result.result["queue"][6]["remote_id"] == str(remote_id7)
    assert result.code == 200
    # 6 in the queue, 1 running
    await retry_limited(lambda: compilerslice._queue_count_cache == 6, 10)

    async def has_matching_compile_report(first_compile_id: uuid.UUID, second_compile_id: uuid.UUID) -> bool:
        return await compilerslice.get_report(first_compile_id) == await compilerslice.get_report(second_compile_id)

    # finish a compile and wait for service to take on next
    await run_compile_and_wait_until_compile_is_done(compilerslice, mocked_compiler_service_block, env.id)

    # api should return 6 when ready
    # Queue = [
    #   remote_id2 (Running), <----------+
    #   remote_id3 (Waiting), <----+     |-- same _compile_merge_key
    #   remote_id4 (Waiting), <--- | ----+
    #   remote_id5 (Waiting), <----+
    #   remote_id6 (Waiting), <----+-- same _compile_merge_key
    #   remote_id7 (Waiting),
    # ]
    result = await client.get_compile_queue(environment)
    assert len(result.result["queue"]) == 6
    assert result.result["queue"][0]["remote_id"] == str(remote_id2)
    assert result.code == 200
    # 5 in the queue, 1 running
    await retry_limited(lambda: compilerslice._queue_count_cache == 5, 10)

    # finish second compile
    await run_compile_and_wait_until_compile_is_done(compilerslice, mocked_compiler_service_block, env.id)

    # Queue = [
    #   remote_id3 (Running), <----+
    #   remote_id5 (Waiting), <----+-- same _compile_merge_key
    #   remote_id6 (Waiting), <----+
    #   remote_id7 (Waiting),
    # ]

    # The "halted" field of a compile report is set asynchronously by a background task.
    # Use try_limited to prevent a race condition.
    await retry_limited(lambda: has_matching_compile_report(compile_id2, compile_id4), timeout=10)
    # 3 in the queue, 1 running
    await retry_limited(lambda: compilerslice._queue_count_cache == 3, 10)

    # finish third compile
    await run_compile_and_wait_until_compile_is_done(compilerslice, mocked_compiler_service_block, env.id)
    await retry_limited(lambda: has_matching_compile_report(compile_id3, compile_id5), timeout=10)
    await retry_limited(lambda: has_matching_compile_report(compile_id3, compile_id6), timeout=10)

    # One left
    # Queue = [
    #   remote_id7 (Running),
    # ]
    result = await client.get_compile_queue(environment)
    assert len(result.result["queue"]) == 1

    # finish 7th compile
    await run_compile_and_wait_until_compile_is_done(compilerslice, mocked_compiler_service_block, env.id)

    while env.id in compilerslice._env_to_compile_task:
        await asyncio.sleep(0.2)

    # 0 in the queue, 0 running
    await retry_limited(lambda: compilerslice._queue_count_cache == 0, 10)

    # api should return none
    result = await client.get_compile_queue(environment)
    assert len(result.result["queue"]) == 0
    assert result.code == 200


async def test_compileservice_queue_with_env_var_merging(
    mocked_compiler_service_block: queue.Queue, server, client, environment
):
    """
    Test the compile queue (as above), but with mergeable env vars
    """
    env = await data.Environment.get_by_id(environment)
    compilerslice: CompilerService = server.get_slice(SLICE_COMPILER)

    result = await client.get_compile_queue(environment)
    assert len(result.result["queue"]) == 0
    assert result.code == 200

    # request a compile, all by itself
    remote_id1 = uuid.uuid4()
    compile_id1, _ = await compilerslice.request_recompile(
        env=env, force_update=False, do_export=True, remote_id=remote_id1, env_vars={"my_var": "1"}, partial=False
    )

    # Then one to compact on top of
    remote_id2 = uuid.uuid4()
    compile_id2, _ = await compilerslice.request_recompile(
        env=env, force_update=False, do_export=True, remote_id=remote_id2, env_vars={"my_var": "1"}, partial=True
    )

    # Then add one
    remote_id3 = uuid.uuid4()
    compile_id3, _ = await compilerslice.request_recompile(
        env=env,
        force_update=False,
        do_export=True,
        remote_id=remote_id3,
        env_vars={"my_var": "1"},
        partial=True,
        mergeable_env_vars={"v1": "a", "v2": "b"},
    )

    # Then another one
    remote_id4 = uuid.uuid4()
    compile_id4, _ = await compilerslice.request_recompile(
        env=env,
        force_update=False,
        do_export=True,
        remote_id=remote_id4,
        env_vars={"my_var": "1"},
        partial=True,
        mergeable_env_vars={"v1": "C"},
    )

    # finish first compile
    t1 = await run_compile_and_wait_until_compile_is_done(compilerslice, mocked_compiler_service_block, env.id)
    # finish all other compiles at once
    t2 = await run_compile_and_wait_until_compile_is_done(compilerslice, mocked_compiler_service_block, env.id)

    # api should return none
    result = await client.get_compile_queue(environment)
    assert len(result.result["queue"]) == 0
    assert result.code == 200

    assert t1.request.used_environment_variables == {"my_var": "1"}
    assert t2.request.used_environment_variables == {"my_var": "1", "v1": "a C", "v2": "b"}


@pytest.mark.parametrize("no_agent", [True])
async def test_compilerservice_halt(
    mocked_compiler_service_block, server, client, environment: uuid.UUID, no_agent: bool
) -> None:
    compilerslice: CompilerService = server.get_slice(SLICE_COMPILER)

    result = await client.get_compile_queue(environment)
    assert result.code == 200
    assert len(result.result["queue"]) == 0
    assert compilerslice._queue_count_cache == 0

    await client.halt_environment(environment)

    env = await data.Environment.get_by_id(environment)
    assert env is not None
    await compilerslice.request_recompile(env=env, force_update=False, do_export=False, remote_id=uuid.uuid4())

    result = await client.get_compile_queue(environment)
    assert result.code == 200
    assert len(result.result["queue"]) == 1
    assert compilerslice._queue_count_cache == 1

    result = await client.is_compiling(environment)
    assert result.code == 204

    await client.resume_environment(environment)
    result = await client.is_compiling(environment)
    assert result.code == 200


async def test_compileservice_queue_count_on_trx_based_api(mocked_compiler_service_block, server, client, environment):
    """
    Verify that the `_queue_count_cache` is not incremented and that the compile is not scheduled until the
    `notify_compile_request_committed()` method is called.
    """
    env = await data.Environment.get_by_id(environment)
    compiler_service: CompilerService = server.get_slice(SLICE_COMPILER)

    async with data.Environment.get_connection() as connection:
        async with connection.transaction():
            remote_id1 = uuid.uuid4()
            compile_id, warnings = await compiler_service.request_recompile(
                env=env,
                force_update=False,
                do_export=False,
                remote_id=remote_id1,
                connection=connection,
                in_db_transaction=True,
            )
            assert compile_id is not None, warnings
            assert compiler_service._queue_count_cache == 0
            assert len(compiler_service._env_to_compile_task) == 0
    # Transaction committed
    await compiler_service.notify_compile_request_committed(compile_id)
    assert compiler_service._queue_count_cache == 1
    assert len(compiler_service._env_to_compile_task) == 1

    await run_compile_and_wait_until_compile_is_done(compiler_service, mocked_compiler_service_block, env.id)
    assert len(compiler_service._env_to_compile_task) == 0


@pytest.fixture(scope="function")
async def server_with_frequent_cleanups(server_pre_start, server_config, async_finalizer):
    config.Config.set("server", "compiler-report-retention", "60")
    config.Config.set("server", "cleanup-compiler-reports_interval", "1")
    ibl = InmantaBootloader(configure_logging=True)
    await ibl.start()
    yield ibl.restserver
    await ibl.stop(timeout=20)


@pytest.fixture(scope="function")
def client_for_cleanup(server_with_frequent_cleanups):
    client = protocol.Client("client")
    yield client


@pytest.fixture(scope="function")
async def environment_for_cleanup(client_for_cleanup, server_with_frequent_cleanups):
    """
    Create a project and environment. This fixture returns the uuid of the environment
    """
    result = await client_for_cleanup.create_project("env-test")
    assert result.code == 200
    project_id = result.result["project"]["id"]

    result = await client_for_cleanup.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    cfg_env.set(env_id)

    yield env_id


@pytest.fixture
async def old_and_new_compile_report(server_with_frequent_cleanups, environment_for_cleanup) -> tuple[uuid.UUID, uuid.UUID]:
    """
    This fixture creates two compile reports. One for a compile that started
    and finished 30 days ago and one that started and finished now.

    This fixture return a tuple containing the id of the old and the new compile report
    respectively.
    """
    now = datetime.datetime.now()
    time_of_old_compile = now - datetime.timedelta(days=30)
    compile_id_old = uuid.UUID("c00cc33f-f70f-4800-ad01-ff042f67118f")
    old_compile = {
        "id": compile_id_old,
        "remote_id": uuid.UUID("c9a10da1-9bf6-4152-8461-98adc02c4cee"),
        "environment": uuid.UUID(environment_for_cleanup),
        "requested": time_of_old_compile,
        "started": time_of_old_compile,
        "completed": time_of_old_compile,
        "do_export": True,
        "force_update": True,
        "metadata": {"type": "api", "message": "Recompile trigger through API call"},
        "requested_environment_variables": {},
        "success": True,
        "handled": True,
        "version": 1,
    }
    compile_id_new = uuid.uuid4()
    new_compile = {**old_compile, "id": compile_id_new, "requested": now, "started": now, "completed": now}

    report1 = {
        "id": uuid.UUID("2baa0175-9169-40c5-a546-64d646f62da6"),
        "started": time_of_old_compile,
        "completed": time_of_old_compile,
        "command": "",
        "name": "Init",
        "errstream": "",
        "outstream": "Using extra environment variables during compile \n",
        "returncode": 0,
        "compile": compile_id_old,
    }
    report2 = {
        **report1,
        "id": uuid.UUID("2a86d2a0-666f-4cca-b0a8-13e0379128d5"),
        "command": "python -m inmanta.app -vvv export -X",
        "name": "Recompiling configuration model",
        "compile": compile_id_new,
    }

    async with Compile.get_connection() as con:
        async with con.transaction():
            await Compile(**old_compile).insert(connection=con)
            await Compile(**new_compile).insert(connection=con)
            await Report(**report1).insert(connection=con)
            await Report(**report2).insert(connection=con)

    yield compile_id_old, compile_id_new


async def test_compileservice_cleanup(
    server_with_frequent_cleanups,
    client_for_cleanup,
    environment_for_cleanup,
    old_and_new_compile_report: tuple[uuid.UUID, uuid.UUID],
):
    """
    Ensure that the process to cleanup old compile reports works correctly.

    The `old_and_new_compile_report` fixture creates a compile report for a compile that is 30 days
    old and one for a compile that happened now. The `server_with_frequent_cleanups` fixture
    sets the `compiler-report-retention` config option to 60 seconds. This test case verifies
    that one old report is cleaned up and the new one is retained.
    """
    compile_id_old, compile_id_new = old_and_new_compile_report

    async def report_cleanup_finished_successfully() -> bool:
        result = await client_for_cleanup.get_reports(environment_for_cleanup)
        assert result.code == 200
        return len(result.result["reports"]) == 1

    # Cleanup happens every second. A timeout of four seconds should be sufficient
    await retry_limited(report_cleanup_finished_successfully, timeout=4)

    result = await client_for_cleanup.get_report(compile_id_old)
    assert result.code == 404
    result = await client_for_cleanup.get_report(compile_id_new)
    assert result.code == 200
    result = await client_for_cleanup.get_reports(environment_for_cleanup)
    assert result.code == 200
    assert len(result.result["reports"]) == 1


@pytest.mark.parametrize("halted", [True, False])
async def test_compileservice_cleanup_halted(server, client, environment, halted):
    """
    Test that the cleanup process of the CompileService works correctly when the environment is halted.

    This test creates two compiles and inserts them into the database.
    If the 'halted' parameter is true, it halts the environment and checks that both compiles remain after cleanup.
    Otherwise, it checks that only one compile remains after cleanup (the new latest one).
    """

    if halted:
        result = await client.halt_environment(environment)
        assert result.code == 200

    now = datetime.datetime.now()
    time_of_old_compile = now - datetime.timedelta(days=30)
    compile_id_old = uuid.UUID("c00cc33f-f70f-4800-ad01-ff042f67118f")
    old_compile = {
        "id": compile_id_old,
        "remote_id": uuid.UUID("c9a10da1-9bf6-4152-8461-98adc02c4cee"),
        "environment": uuid.UUID(environment),
        "requested": time_of_old_compile,
        "started": time_of_old_compile,
        "completed": time_of_old_compile,
        "do_export": True,
        "force_update": True,
        "metadata": {"type": "api", "message": "Recompile trigger through API call"},
        "requested_environment_variables": {},
        "used_environment_variables": {},
        "success": True,
        "handled": True,
        "version": 1,
    }
    compile_id_new = uuid.uuid4()
    new_compile = {**old_compile, "id": compile_id_new, "requested": now, "started": now, "completed": now}

    # insert compiles and reports into the database
    async with Compile.get_connection() as con:
        async with con.transaction():
            await Compile(**old_compile).insert(connection=con)
            await Compile(**new_compile).insert(connection=con)

    compiles = await data.Compile.get_list()
    assert len(compiles) == 2

    oldest_retained_date = datetime.datetime.now().astimezone() - datetime.timedelta(seconds=50)

    await data.Compile.delete_older_than(oldest_retained_date)

    compiles = await data.Compile.get_list()
    # if halted, nothing should be cleaned up, otherwise only the old compile should be cleaned up
    assert len(compiles) == (2 if halted else 1)


async def test_issue_2361(environment_factory: EnvironmentFactory, server, client, tmpdir):
    env = await environment_factory.create_environment(main="")

    # Change the branch of the environment to a non-existing branch as such that the run method
    # of the CompileRun returns after executing the clone stage.
    result = await client.environment_modify(id=env.id, name=env.id, branch="non-existing-branch")
    assert result.code == 200

    project_work_dir = os.path.join(tmpdir, "work")
    ensure_directory_exist(project_work_dir)

    compile = data.Compile(
        remote_id=uuid.uuid4(),
        environment=env.id,
        do_export=True,
        metadata={},
        requested_environment_variables={},
        used_environment_variables={},
        force_update=True,
    )
    await compile.insert()

    cr = CompileRun(compile, project_work_dir)

    # This should not result in a "local variable referenced before assignment" exception
    success, compile_data = await cr.run()
    assert not success
    assert compile_data is None


async def test_git_uses_environment_variables(environment_factory: EnvironmentFactory, server, client, tmpdir, monkeypatch):
    """
    Make sure that the git clone command on the compilerservice takes into account the environment variables
    set on the system.
    """
    env = await environment_factory.create_environment(main="")
    result = await client.environment_modify(id=env.id, name=env.id, branch="master")
    assert result.code == 200

    project_work_dir = os.path.join(tmpdir, "work")
    ensure_directory_exist(project_work_dir)

    compile = data.Compile(
        remote_id=uuid.uuid4(),
        environment=env.id,
        do_export=True,
        metadata={},
        requested_environment_variables={},
        used_environment_variables={},
        force_update=True,
    )
    await compile.insert()

    # Make sure git clone logs trace lines
    monkeypatch.setenv("GIT_TRACE", "1")
    cr = CompileRun(compile, project_work_dir)
    await cr.run()

    report = await data.Report.get_one(compile=compile.id, name="Cloning repository")
    # Assert presence of trace lines
    assert "trace: " in report.errstream


@pytest.mark.parametrize(
    "recompile_backoff,expected_log_message,expected_log_level",
    [
        ("2.1", "The recompile_backoff environment setting is enabled and set to 2.1 seconds", logging.INFO),
        ("0", "The recompile_backoff environment setting is disabled", logging.INFO),
    ],
)
async def test_compileservice_recompile_backoff(
    mocked_compiler_service_block,
    server,
    client,
    environment,
    caplog,
    recompile_backoff: str,
    expected_log_message: str,
    expected_log_level: int,
):
    """
    Test the recompile_backoff setting when multiple recompiles are requested in a short amount of time
    """
    with caplog.at_level(logging.DEBUG):
        env = await data.Environment.get_by_id(environment)
        await env.set(data.RECOMPILE_BACKOFF, recompile_backoff)
        compilerslice: CompilerService = server.get_slice(SLICE_COMPILER)

        # request compiles in rapid succession
        remote_id1 = uuid.uuid4()
        await compilerslice.request_recompile(
            env=env, force_update=False, do_export=False, remote_id=remote_id1, env_vars={"my_unique_var": "1"}
        )
        remote_id2 = uuid.uuid4()
        compile_id2, _ = await compilerslice.request_recompile(
            env=env, force_update=False, do_export=False, remote_id=remote_id2
        )

        remote_id3 = uuid.uuid4()
        compile_id3, _ = await compilerslice.request_recompile(
            env=env, force_update=False, do_export=True, remote_id=remote_id3
        )

        result = await client.get_compile_queue(environment)
        assert len(result.result["queue"]) == 3
        assert result.code == 200

        # Start working through it
        for i in range(3):
            await run_compile_and_wait_until_compile_is_done(compilerslice, mocked_compiler_service_block, env.id)

        LogSequence(caplog, allow_errors=False).contains(
            "inmanta.server.services.compilerservice", logging.DEBUG, "Running recompile without waiting"
        ).contains("inmanta.server.services.compilerservice", expected_log_level, expected_log_message).contains(
            "inmanta.server.services.compilerservice", logging.DEBUG, "Running recompile without waiting"
        )


async def test_compileservice_calculate_recompile_backoff_time(mocked_compiler_service_block, server):
    """
    Test the recompile backoff time calculation when the recompile_backoff environment setting is enabled
    """
    auto_recompile_wait = 2
    compilerslice: CompilerService = server.get_slice(SLICE_COMPILER)

    now = datetime.datetime.now()
    compile_requested = now - datetime.timedelta(seconds=1)
    last_compile_completed = now - datetime.timedelta(seconds=4)
    waiting_time = compilerslice._calculate_recompile_backoff_time(
        auto_recompile_wait, compile_requested, last_compile_completed, now
    )
    assert waiting_time == 0

    compile_requested = now - datetime.timedelta(seconds=0.1)
    last_compile_completed = now - datetime.timedelta(seconds=1)
    waiting_time = compilerslice._calculate_recompile_backoff_time(
        auto_recompile_wait, compile_requested, last_compile_completed, now
    )
    assert waiting_time == approx(1)

    compile_requested = now - datetime.timedelta(seconds=1)
    last_compile_completed = now - datetime.timedelta(seconds=0.1)
    waiting_time = compilerslice._calculate_recompile_backoff_time(
        auto_recompile_wait, compile_requested, last_compile_completed, now
    )
    assert waiting_time == approx(1)

    compile_requested = now - datetime.timedelta(seconds=4)
    last_compile_completed = now - datetime.timedelta(seconds=1)
    waiting_time = compilerslice._calculate_recompile_backoff_time(
        auto_recompile_wait, compile_requested, last_compile_completed, now
    )
    assert waiting_time == 0


async def test_compileservice_api(client, environment):
    # Exceed max value for limit
    result = await client.get_reports(environment, limit=APILIMIT + 1)
    assert result.code == 400
    assert result.result["message"] == f"Invalid request: limit parameter can not exceed {APILIMIT}, got {APILIMIT + 1}."

    result = await client.get_reports(environment, limit=APILIMIT)
    assert result.code == 200


@pytest.mark.parametrize(
    "message",
    ["a custom message", None],
)
async def test_notification_failed_compile_with_message(
    server, client, environment, mocked_compiler_service_block, message: Optional[str]
) -> None:
    compilerservice = server.get_slice(SLICE_COMPILER)

    result = await client.list_notifications(environment)
    assert result.code == 200
    assert len(result.result["data"]) == 0

    env = await data.Environment.get_by_id(environment)

    compile_id, _ = await compilerservice.request_recompile(
        env,
        force_update=False,
        do_export=False,
        remote_id=uuid.uuid4(),
        notify_failed_compile=True,
        failed_compile_message=message,
    )

    await run_compile_and_wait_until_compile_is_done(compilerservice, mocked_compiler_service_block, env.id, True)

    async def notification_logged() -> bool:
        result = await client.list_notifications(environment)
        assert result.code == 200
        return len(result.result["data"]) > 0

    await retry_limited(notification_logged, timeout=10)
    result = await client.list_notifications(environment)
    assert result.code == 200
    compile_failed_notification = next((item for item in result.result["data"] if item["title"] == "Compilation failed"), None)
    assert compile_failed_notification
    assert str(compile_id) in compile_failed_notification["uri"]
    if message == "a custom message":
        assert "a custom message" in compile_failed_notification["message"]
    else:
        assert "A compile has failed" in compile_failed_notification["message"]


async def test_notification_on_failed_exporting_compile(
    server, client, environment: str, mocked_compiler_service_failing_compile
) -> None:
    compilerservice = server.get_slice(SLICE_COMPILER)
    env = await data.Environment.get_by_id(uuid.UUID(environment))

    result = await client.list_notifications(env.id)
    assert result.code == 200
    assert len(result.result["data"]) == 0

    compile_id, _ = await compilerservice.request_recompile(env, force_update=False, do_export=True, remote_id=uuid.uuid4())

    async def compile_done() -> bool:
        res = await compilerservice.is_compiling(env.id)
        return res == 204

    await retry_limited(compile_done, timeout=10)

    async def notification_logged() -> bool:
        result = await client.list_notifications(env.id)
        assert result.code == 200
        return len(result.result["data"]) > 0

    await retry_limited(notification_logged, timeout=10)
    result = await client.list_notifications(env.id)
    assert result.code == 200
    compile_failed_notification = next((item for item in result.result["data"] if item["title"] == "Compilation failed"), None)
    assert compile_failed_notification
    assert str(compile_id) in compile_failed_notification["uri"]


async def test_notification_on_failed_pull_during_compile(
    server, client, environment: str, mocked_compiler_service_block
) -> None:
    env = await data.Environment.get_by_id(uuid.UUID(environment))

    compilerservice = server.get_slice(SLICE_COMPILER)

    result = await client.list_notifications(env.id)
    assert result.code == 200
    assert len(result.result["data"]) == 0

    # Do a compile
    compile_id, _ = await compilerservice.request_recompile(env, force_update=True, do_export=False, remote_id=uuid.uuid4())

    await run_compile_and_wait_until_compile_is_done(compilerservice, mocked_compiler_service_block, env.id)

    # During the next compile, the pull should fail
    compile_id, _ = await compilerservice.request_recompile(env, force_update=True, do_export=False, remote_id=uuid.uuid4())

    await run_compile_and_wait_until_compile_is_done(compilerservice, mocked_compiler_service_block, env.id, fail_on_pull=True)

    async def notification_logged() -> bool:
        result = await client.list_notifications(env.id)
        assert result.code == 200
        return len(result.result["data"]) > 0

    await retry_limited(notification_logged, timeout=10)

    # Check if the correct notification was created
    result = await client.list_notifications(env.id)
    assert result.code == 200
    compile_failed_notification = next(
        (item for item in result.result["data"] if item["title"] == "Pulling updates during compile failed"), None
    )
    assert compile_failed_notification
    assert str(compile_id) in compile_failed_notification["uri"]


@pytest.mark.slowtest
async def test_uninstall_python_packages(
    environment_factory: EnvironmentFactory, server, client, tmpdir, monkeypatch, local_module_package_index: str
) -> None:
    """
    Verify that the compiler service removes protected packages installed in the compiler venv before starting
    """
    env: data.Environment = await environment_factory.create_environment("")
    project_work_dir = os.path.join(tmpdir, "work")
    ensure_directory_exist(project_work_dir)

    async def run_compile_with_force_update() -> None:
        compile_db_record = data.Compile(
            remote_id=uuid.uuid4(),
            environment=env.id,
            used_environment_variables={},
            force_update=True,
        )
        await compile_db_record.insert()

        cr = CompileRun(compile_db_record, project_work_dir)
        await cr.run()

    # Make the compiler service create the venv
    await run_compile_with_force_update()
    venv_path = os.path.join(project_work_dir, ".env")
    assert os.path.exists(venv_path)

    # Make inmanta-module-elaboratev2module a protected package
    name_protected_pkg = "inmanta-module-elaboratev2module"

    def patch_get_protected_inmanta_packages():
        return [name_protected_pkg]

    monkeypatch.setattr(PythonEnvironment, "get_protected_inmanta_packages", patch_get_protected_inmanta_packages)

    # Install protected package in venv
    venv = PythonEnvironment(env_path=venv_path)
    assert name_protected_pkg not in venv.get_installed_packages()
    venv.install_for_config(
        requirements=[inmanta.util.parse_requirement(requirement=name_protected_pkg)],
        config=PipConfig(
            index_url=local_module_package_index,
        ),
    )
    assert name_protected_pkg in venv.get_installed_packages()

    # Run a new compile
    await run_compile_with_force_update()

    # Verify that the protected package was removed
    assert name_protected_pkg not in venv.get_installed_packages()

    # Run a new compile without any protected packages installed in the
    # venv of the compiler service.
    await run_compile_with_force_update()

    # Assert no compilation failed
    reports = await data.Report.get_list(name="Uninstall inmanta packages from the compiler venv")
    # The uninstall is executed on update. The first compile is not an update
    assert len(reports) == 2
    assert all(r.returncode == 0 for r in reports)


async def test_compiler_service_export_with_specified_exporter_plugin(
    environment_factory: EnvironmentFactory, modules_dir, server, client, tmpdir, caplog
):
    """
    Check that compiler service accepts specific exporter plugin as argument for both exporting and non-exporting compiles
    """

    used_exporter = "test_exporter"
    unused_exporter = "unused_test_exporter"

    used_module_name = used_exporter + "_module"
    unused_module_name = unused_exporter + "_module"

    def make_main():
        return f"""
import {used_module_name}
import {unused_module_name}
        """

    env = await environment_factory.create_environment(make_main())

    def make_plugin_code(exporter_name):
        return f"""
from inmanta.export import export, Exporter

@export("{exporter_name}")
def {exporter_name}(exporter: Exporter) -> None:
    print("{exporter_name} ran")
        """

    module_template: str = os.path.join(modules_dir, "minimalv1module")

    environment_factory.add_v1_module(
        used_module_name, plugin_code=make_plugin_code(used_exporter), template_dir=module_template
    )
    environment_factory.add_v1_module(
        unused_module_name, plugin_code=make_plugin_code(unused_exporter), template_dir=module_template
    )

    project_work_dir = os.path.join(tmpdir, "work")
    ensure_directory_exist(project_work_dir)

    # with export
    compile, stages = await compile_and_assert(
        env=env, project_work_dir=project_work_dir, client=client, export=True, exporter_plugin=used_exporter
    )
    out = stages["Recompiling configuration model"]["outstream"]
    assert f"{used_exporter} ran" in out
    assert f"{unused_exporter} ran" not in out
    assert compile.version is not None

    # no export
    compile, stages = await compile_and_assert(
        env=env, project_work_dir=project_work_dir, client=client, export=False, exporter_plugin=used_exporter
    )
    out = stages["Recompiling configuration model"]["outstream"]
    assert f"{used_exporter} ran" in out
    assert f"{unused_exporter} ran" not in out
    assert compile.version is None


@pytest.mark.parametrize("only_clear_environment", [True, False])
@pytest.mark.parametrize("compile_is_running", [True, False])
@pytest.mark.parametrize("no_agent", [True])
async def test_status_compilerservice_task_queue(
    server,
    client,
    environment: str,
    mocked_compiler_service_block,
    only_clear_environment: bool,
    compile_is_running: bool,
    no_agent: bool,
) -> None:
    """
    Verify that the size of the compiler queue, reported by the /serverstatus API endpoint, is correctly
    updated when an environment is cleared or deleted.

    :param only_clear_environment: If True, verify the behavior when the environment is cleared.
                                   Otherwise, verify the behavior when the environment is deleted.
    :param compile_is_running: True iff the environment will be cleared or deleted when a compile is running.
    """
    env = await data.Environment.get_by_id(uuid.UUID(environment))
    compilerservice = server.get_slice(SLICE_COMPILER)

    if not compile_is_running:
        # Halt the environment so that the compiler service doesn't pick up the requested compiles.
        result = await client.halt_environment(environment)
        assert result.code == 200

    async def verify_length_compile_queue(expected_length: int) -> bool:
        """
        Return True iff the /serverstatus endpoint returns `expected_length` as the length of the compile queue.
        """
        result = await client.get_server_status()
        assert result.code == 200
        for current_slice in result.result["data"]["slices"]:
            if current_slice["name"] == "core.compiler":
                return current_slice["status"]["task_queue"] == expected_length
        raise Exception("Status endpoint didn't report the status of the compiler service.")

    # Verify initial state
    assert await verify_length_compile_queue(expected_length=0)

    # Request two compiles
    for _ in range(2):
        await compilerservice.request_recompile(env, force_update=False, do_export=False, remote_id=uuid.uuid4())

    if compile_is_running:
        await retry_limited(verify_length_compile_queue, timeout=10, expected_length=1)
    else:
        await retry_limited(verify_length_compile_queue, timeout=10, expected_length=2)

    # Action on environment that empties the compile queue
    if only_clear_environment:
        result = await client.environment_clear(environment)
        assert result.code == 200
    else:
        result = await client.environment_delete(environment)
        assert result.code == 200

    # Verify compile queue is empty
    await retry_limited(verify_length_compile_queue, timeout=10, expected_length=0)


async def test_environment_delete_removes_env_directories_on_server(
    server,
    client,
) -> None:
    """
    Make sure the environment_delete endpoint deletes the environment directory on the server.
    """
    state_dir: Optional[str] = config.Config.get("config", "state-dir")
    assert state_dir is not None

    result = await client.create_project("env-test")
    assert result.code == 200
    project_id = result.result["project"]["id"]

    result = await client.create_environment(project_id=project_id, name="env1")
    assert result.code == 200
    env_id = result.result["environment"]["id"]

    result: Result = await client.notify_change(env_id)
    assert result.code == 200

    async def wait_for_compile() -> bool:
        result = await client.get_compile_reports(tid=env_id)
        assert result.code == 200
        if len(result.result["data"]) == 0:
            # The compile request is registered in the database asynchronously with respect to the notify_change() API call.
            # Here we check that the compile request finished.
            return False
        # Check whether the compilation finished.
        return result.result["data"][0]["completed"] is not None

    await utils.retry_limited(wait_for_compile, 15)

    env_dir = py.path.local(state_dir).join("server", str(env_id), "compiler")
    assert os.path.exists(env_dir)

    result = await client.environment_delete(env_id)
    assert result.code == 200

    assert not os.path.exists(env_dir)


async def test_overlapping_env_vars(mocked_compiler_service, server, client, environment) -> None:
    """
    Ensure that the compiler service raises an exception if a compile is requested where the same
    environment variable is present in the env_vars and the mergeable_env_vars dictionary.
    """
    env = await data.Environment.get_by_id(environment)
    compilerslice: CompilerService = server.get_slice(SLICE_COMPILER)

    expected_exception_message = (
        "Invalid compile request: The same environment variable cannot be present in the "
        "env_vars and mergeable_env_vars dictionary simultaneously: {'var'}."
    )
    with pytest.raises(ValueError, match=re.escape(expected_exception_message)):
        await compilerslice.request_recompile(
            env=env,
            force_update=False,
            do_export=False,
            remote_id=uuid.uuid4(),
            env_vars={"var": "val", "test": "123"},
            mergeable_env_vars={"var": "otherval", "somekey": "someval"},
        )


class Mockreport:

    async def update_streams(self, out: str = "", err: str = "") -> None:
        pass


async def test_venv_use_and_reuse(tmp_path, caplog):
    caplog.at_level(logging.DEBUG)

    # Set up mock
    project = tmp_path / "project"
    venv = project / ".env"
    project.mkdir()
    run = CompileRun(None, str(project))
    run.stage = Mockreport()

    # Create a venv
    await run.ensure_compiler_venv()
    assert venv.exists()
    log_contains(caplog, "inmanta.server.services.compilerservice", logging.INFO, "Creating new venv at")
    caplog.clear()

    # re-use the venv
    await run.ensure_compiler_venv()
    log_contains(caplog, "inmanta.server.services.compilerservice", logging.INFO, "Found existing venv")


async def test_venv_upgrade_version_match(tmp_path, caplog):
    """
    1. Make a venv in the old layout and upgrade it
    2. Test we can handle re-creation of the venv
    """
    caplog.at_level(logging.DEBUG)

    # Set up mock
    project = tmp_path / "project"
    project.mkdir()
    venv = project / ".env"
    run = CompileRun(None, str(project))
    run.stage = Mockreport()

    # make venv on old location, correct version
    VirtualEnv(str(venv)).init_env()

    await run.ensure_compiler_venv()
    log_contains(caplog, "inmanta.server.services.compilerservice", logging.INFO, "Moving existing venv from")
    caplog.clear()
    assert venv.exists()

    # remove actual venv
    python_version = ".".join(platform.python_version_tuple()[0:2])
    versioned_venv_dir = ".env-py" + python_version
    versioned_venv_dir_full = project / versioned_venv_dir
    shutil.rmtree(str(versioned_venv_dir_full))

    await run.ensure_compiler_venv()
    log_contains(caplog, "inmanta.server.services.compilerservice", logging.INFO, "Creating new venv at")
    assert venv.exists()


async def test_venv_upgrade_version_mismatch(tmp_path, caplog):
    # Make fake venv of wrong version

    caplog.at_level(logging.DEBUG)

    # Old setup
    project = tmp_path / "project2"
    project.mkdir()
    venv = project / ".env"

    run = CompileRun(None, str(project))
    run.stage = Mockreport()

    # This venv is a bit broken, but the code sees it wrong version
    # Because it doesn't have the right version
    venv.mkdir()
    (venv / "bin").mkdir()
    (venv / "bin" / "python").touch()

    await run.ensure_compiler_venv()
    log_contains(caplog, "inmanta.server.services.compilerservice", logging.INFO, "Discarding existing venv from")
    assert (project / ".env").exists()
