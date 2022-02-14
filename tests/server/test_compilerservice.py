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
import logging
import os
import queue
import shutil
import subprocess
import uuid
from asyncio import Semaphore
from typing import AsyncIterator, List, Optional, Tuple

import pytest
from pytest import approx

import inmanta.ast.export as ast_export
import inmanta.data.model as model
from inmanta import config, data
from inmanta.const import ParameterSource
from inmanta.data import APILIMIT, Compile, Report
from inmanta.deploy import cfg_env
from inmanta.protocol import Result
from inmanta.server import SLICE_COMPILER, SLICE_SERVER
from inmanta.server import config as server_config
from inmanta.server import protocol
from inmanta.server.bootloader import InmantaBootloader
from inmanta.server.protocol import Server
from inmanta.server.services.compilerservice import CompilerService, CompileRun, CompileStateListener
from inmanta.util import ensure_directory_exist
from utils import LogSequence, report_db_index_usage, retry_limited, wait_for_version

logger = logging.getLogger("inmanta.test.server.compilerservice")


@pytest.fixture
async def compilerservice(server_config, init_dataclasses_and_load_schema):
    server = Server()
    cs = CompilerService()
    await cs.prestart(server)
    await cs.start()
    yield cs
    await cs.prestop()
    await cs.stop()


@pytest.fixture
async def environment_factory(tmpdir) -> AsyncIterator["EnvironmentFactory"]:
    """
    Provides a factory for environments with a main.cf file.
    """
    yield EnvironmentFactory(str(tmpdir))


class EnvironmentFactory:
    def __init__(self, dir: str) -> None:
        self.src_dir: str = os.path.join(dir, "src")
        self.project: data.Project = data.Project(name="test")
        self._ready: bool = False

    async def setup(self) -> None:
        if self._ready:
            return

        project_template = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "project")
        shutil.copytree(project_template, self.src_dir)

        # Set up git
        subprocess.check_output(["git", "init"], cwd=self.src_dir)
        subprocess.check_output(["git", "add", "*"], cwd=self.src_dir)
        subprocess.check_output(["git", "config", "user.name", "Unit"], cwd=self.src_dir)
        subprocess.check_output(["git", "config", "user.email", "unit@test.example"], cwd=self.src_dir)
        subprocess.check_output(["git", "commit", "-m", "unit test"], cwd=self.src_dir)

        await self.project.insert()

        self._ready = True

    async def create_environment(self, main: str) -> data.Environment:
        await self.setup()
        branch: str = str(uuid.uuid4())
        subprocess.check_output(["git", "checkout", "-b", branch], cwd=self.src_dir)
        self.write_main(main)
        environment: data.Environment = data.Environment(
            name=branch, project=self.project.id, repo_url=self.src_dir, repo_branch=branch
        )
        await environment.insert()
        return environment

    def write_main(self, main: str, environment: Optional[data.Environment] = None) -> None:
        if environment is not None:
            subprocess.check_output(["git", "checkout", environment.repo_branch], cwd=self.src_dir)
        with open(os.path.join(self.src_dir, "main.cf"), "w", encoding="utf-8") as fd:
            fd.write(main)
        subprocess.check_output(["git", "add", "main.cf"], cwd=self.src_dir)
        subprocess.check_output(["git", "commit", "-m", "write main.cf", "--allow-empty"], cwd=self.src_dir)


@pytest.mark.asyncio
async def test_scheduler(server_config, init_dataclasses_and_load_schema, caplog):
    """Test the scheduler part in isolation, mock out compile runner and listen to state updates"""

    class Collector(CompileStateListener):
        """
        Collect all state updates, optionally hang the processing of listeners
        """

        def __init__(self):
            self.seen = []
            self.preseen = []
            self.lock = Semaphore(1)

        def reset(self):
            self.seen = []
            self.preseen = []

        async def compile_done(self, compile: data.Compile):
            self.preseen.append(compile)
            print("Got compile done for ", compile.remote_id)
            async with self.lock:
                self.seen.append(compile)

        async def hang(self):
            await self.lock.acquire()

        def release(self):
            self.lock.release()

        def verify(self, envs: uuid.UUID):
            assert sorted([x.remote_id for x in self.seen]) == sorted(envs)
            self.reset()

    class HangRunner(object):
        """
        compile runner mock, hang until released
        """

        def __init__(self):
            self.lock = Semaphore(0)
            self.started = False
            self.done = False
            self.version = None

        async def run(self, force_update: Optional[bool] = False):
            self.started = True
            await self.lock.acquire()
            self.done = True
            return True, None

        def release(self):
            self.lock.release()

    class HookedCompilerService(CompilerService):
        """
        hook in the hangrunner
        """

        def __init__(self):
            super(HookedCompilerService, self).__init__()
            self.locks = {}

        def _get_compile_runner(self, compile: data.Compile, project_dir: str):
            print("Get Run: ", compile.remote_id, compile.id)
            runner = HangRunner()
            self.locks[compile.remote_id] = runner
            return runner

        def get_runner(self, remote_id: uuid.UUID) -> HangRunner:
            return self.locks.get(remote_id)

    # manual setup of server
    server = Server()
    cs = HookedCompilerService()
    await cs.prestart(server)
    await cs.start()
    collector = Collector()
    cs.add_listener(collector)

    async def request_compile(env: data.Environment) -> uuid.UUID:
        """Request compile for given env, return remote_id"""
        u1 = uuid.uuid4()
        # add unique environment variables to prevent merging in request_recompile
        await cs.request_recompile(env, False, False, u1, env_vars={"uuid": str(u1)})
        results = await data.Compile.get_by_remote_id(env.id, u1)
        assert len(results) == 1
        assert results[0].remote_id == u1
        print("request: ", u1, results[0].id)
        return u1

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

    async def check_compile_in_sequence(env: data.Environment, remote_ids: List[uuid.UUID], idx: int):
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

            cs.get_runner(current).release()
            await asyncio.sleep(0)
            await retry_limited(lambda: cs.get_runner(current).done, 1)

        else:

            async def isdone():
                return await cs.is_compiling(env.id) == 204

            await retry_limited(isdone, 1)

    # run through env1, entire sequence
    for i in range(4):
        await check_compile_in_sequence(env1, e1, i)
    collector.verify(e1)
    print("env1 done")

    print("env2 ", e2)
    # make event collector hang
    await collector.hang()
    # progress two steps into env2
    for i in range(2):
        await check_compile_in_sequence(env2, e2, i)

    assert not collector.seen
    print(collector.preseen)
    await retry_limited(lambda: len(collector.preseen) == 2, 1)

    # test server restart
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
    await cs.start()
    collector = Collector()
    cs.add_listener(collector)

    # complete the sequence, expect re-run of third compile
    for i in range(3):
        print(i)
        await check_compile_in_sequence(env2, e2[2:], i)

    # all are re-run, entire sequence present
    collector.verify(e2)

    await report_db_index_usage()


@pytest.mark.asyncio
@pytest.mark.slowtest
async def test_compile_runner(environment_factory: EnvironmentFactory, server, client, tmpdir):
    testmarker_env = "TESTMARKER"
    no_marker = "__no__marker__"
    marker_print = "_INM_MM:"
    marker_print2 = "_INM_MM2:"
    marker_print3 = "_INM_MM3:"

    def make_main(marker_print):
        return f"""
    marker = std::get_env("{testmarker_env}","{no_marker}")
    std::print("{marker_print} {{{{marker}}}}")

    host = std::Host(name="test", os=std::linux)
    std::ConfigFile(host=host, path="/etc/motd", content="1234")
        """

    env = await environment_factory.create_environment(make_main(marker_print))
    env2 = await environment_factory.create_environment(make_main(marker_print2))

    project_work_dir = os.path.join(tmpdir, "work")
    ensure_directory_exist(project_work_dir)

    async def compile_and_assert(env, export=True, meta={}, env_vars={}, update=False):
        compile = data.Compile(
            remote_id=uuid.uuid4(),
            environment=env.id,
            do_export=export,
            metadata=meta,
            environment_variables=env_vars,
            force_update=update,
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

    # with export
    compile, stages = await compile_and_assert(env, True, meta={"type": "Test"})
    assert stages["Init"]["returncode"] == 0
    assert stages["Cloning repository"]["returncode"] == 0
    assert stages["Recompiling configuration model"]["returncode"] == 0
    out = stages["Recompiling configuration model"]["outstream"]
    assert f"{marker_print} {no_marker}" in out
    assert len(stages) == 3
    assert compile.version is not None

    # no export
    compile, stages = await compile_and_assert(env, False)
    assert stages["Init"]["returncode"] == 0
    assert stages["Recompiling configuration model"]["returncode"] == 0
    out = stages["Recompiling configuration model"]["outstream"]
    assert f"{marker_print} {no_marker}" in out
    assert len(stages) == 2
    assert compile.version is None

    # env vars
    marker = str(uuid.uuid4())
    compile, stages = await compile_and_assert(env, False, env_vars={testmarker_env: marker})
    assert len(compile.request.environment_variables) == 1
    assert stages["Init"]["returncode"] == 0
    assert f"Using extra environment variables during compile TESTMARKER='{marker}'" in stages["Init"]["outstream"]
    assert stages["Recompiling configuration model"]["returncode"] == 0
    out = stages["Recompiling configuration model"]["outstream"]
    assert f"{marker_print} {marker}" in out
    assert len(stages) == 2
    assert compile.version is None

    # switch branch
    compile, stages = await compile_and_assert(env2, False)
    assert stages["Init"]["returncode"] == 0
    assert stages[f"switching branch from {env.repo_branch} to {env2.repo_branch}"]["returncode"] == 0
    assert stages["Recompiling configuration model"]["returncode"] == 0
    out = stages["Recompiling configuration model"]["outstream"]
    assert f"{marker_print2} {no_marker}" in out
    assert len(stages) == 3
    assert compile.version is None

    # update with no update
    compile, stages = await compile_and_assert(env2, False, update=True)
    assert stages["Init"]["returncode"] == 0
    assert stages["Fetching changes"]["returncode"] == 0
    assert stages["Pulling updates"]["returncode"] == 0
    assert stages["Updating modules"]["returncode"] == 0
    assert stages["Recompiling configuration model"]["returncode"] == 0
    out = stages["Recompiling configuration model"]["outstream"]
    assert f"{marker_print2} {no_marker}" in out
    assert len(stages) == 5
    assert compile.version is None

    environment_factory.write_main(make_main(marker_print3))
    compile, stages = await compile_and_assert(env2, False, update=True)
    assert stages["Init"]["returncode"] == 0
    assert stages["Fetching changes"]["returncode"] == 0
    assert stages["Pulling updates"]["returncode"] == 0
    assert stages["Updating modules"]["returncode"] == 0
    assert stages["Recompiling configuration model"]["returncode"] == 0
    out = stages["Recompiling configuration model"]["outstream"]
    assert f"{marker_print3} {no_marker}" in out
    assert len(stages) == 5
    assert compile.version is None


@pytest.mark.asyncio
async def test_compilerservice_compile_data(environment_factory: EnvironmentFactory, client, server) -> None:
    async def get_compile_data(main: str) -> model.CompileData:
        env: data.Environment = await environment_factory.create_environment(main)
        result: Result = await client.notify_change(env.id)
        assert result.code == 200

        async def compile_done():
            return (await client.is_compiling(env.id)).code == 204

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

    errors0: List[ast_export.Error] = (await get_compile_data("x = 0")).errors
    assert len(errors0) == 0

    errors1: List[ast_export.Error] = (await get_compile_data("x = 0 x = 1")).errors
    assert len(errors1) == 1
    error: ast_export.Error = errors1[0]
    assert error.category == ast_export.ErrorCategory.runtime
    assert error.type == "inmanta.ast.DoubleSetException"
    assert error.message == "value set twice:\n\told value: 0\n\t\tset at ./main.cf:1\n\tnew value: 1\n\t\tset at ./main.cf:1\n"


@pytest.mark.asyncio
async def test_e2e_recompile_failure(compilerservice: CompilerService):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    u1 = uuid.uuid4()
    await compilerservice.request_recompile(env, False, False, u1, env_vars={"my_unique_var": str(u1)})
    u2 = uuid.uuid4()
    await compilerservice.request_recompile(env, False, False, u2, env_vars={"my_unique_var": str(u2)})

    assert await compilerservice.is_compiling(env.id) == 200

    async def compile_done():
        res = await compilerservice.is_compiling(env.id)
        print(res)
        return res == 204

    await retry_limited(compile_done, 10)

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
        assert "project found in" in init["outstream"] and "and no repository set" in init["outstream"]

        # compile
        comp = reports["Recompiling configuration model"]
        assert "Unable to find an inmanta project (project.yml expected)" in comp["errstream"]
        assert comp["returncode"] == 1
        return report["requested"], report["started"], report["completed"]

    r1, s1, f1 = assert_report(u1)
    r2, s2, f2 = assert_report(u2)

    assert r2 > r1
    assert r1 < s1 < f1
    assert r2 < s2 < f2
    assert f1 < s2


@pytest.mark.asyncio(timeout=90)
async def test_server_recompile(server, client, environment, monkeypatch):
    """
    Test a recompile on the server and verify recompile triggers
    """
    config.Config.set("server", "auto-recompile-wait", "0")

    project_dir = os.path.join(server.get_slice(SLICE_SERVER)._server_storage["environments"], str(environment))
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
        host = std::Host(name="test", os=std::linux)
        std::ConfigFile(host=host, path="/etc/motd", content="1234")
        std::print(std::get_env("{key_env_var}"))
"""
        )

    logger.info("request a compile")
    result = await client.notify_change(environment)
    assert result.code == 200

    logger.info("wait for 1")
    versions = await wait_for_version(client, environment, 1)
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
    await client.set_param(environment, id="param1", value="test", source=ParameterSource.plugin)
    versions = await wait_for_version(client, environment, 1)
    assert versions["count"] == 1

    logger.info("request second compile")
    # set a new parameter and request a recompile
    await client.set_param(environment, id="param2", value="test", source=ParameterSource.plugin, recompile=True)
    logger.info("wait for 2")
    versions = await wait_for_version(client, environment, 2)
    assert versions["versions"][0]["version_info"]["export_metadata"]["type"] == "param"
    assert versions["count"] == 2

    # update the parameter to the same value -> no compile
    await client.set_param(environment, id="param2", value="test", source=ParameterSource.plugin, recompile=True)
    versions = await wait_for_version(client, environment, 2)
    assert versions["count"] == 2

    # update the parameter to a new value
    await client.set_param(environment, id="param2", value="test2", source=ParameterSource.plugin, recompile=True)
    versions = await wait_for_version(client, environment, 3)
    logger.info("wait for 3")
    assert versions["count"] == 3

    # clear the environment
    state_dir = server_config.state_dir.get()
    project_dir = os.path.join(state_dir, "server", "environments", environment)
    assert os.path.exists(project_dir)

    await client.clear_environment(environment)

    assert not os.path.exists(project_dir)


async def run_compile_and_wait_until_compile_is_done(
    compiler_service: CompilerService, compiler_queue: queue.Queue, env_id: uuid.UUID
) -> None:
    """
    Unblock the first compile in the compiler queue and wait until the compile finishes.
    """
    current_task = compiler_service._recompiles[env_id]

    # prevent race conditions where compile request is not yet in queue
    await retry_limited(lambda: not compiler_queue.empty(), timeout=10)
    run = compiler_queue.get(block=True)
    run.block = False

    def _is_compile_finished() -> bool:
        if env_id not in compiler_service._recompiles:
            return True
        if current_task is not compiler_service._recompiles[env_id]:
            return True
        return False

    await retry_limited(_is_compile_finished, timeout=10)


@pytest.mark.asyncio(timeout=90)
async def test_compileservice_queue(mocked_compiler_service_block: queue.Queue, server, client, environment):
    """
    Test the inspection of the compile queue. The compile runner is mocked out so the "started" field does not have the
    correct value in this test.
    """
    env = await data.Environment.get_by_id(environment)
    config.Config.set("server", "auto-recompile-wait", "0")
    compilerslice: CompilerService = server.get_slice(SLICE_COMPILER)

    result = await client.get_compile_queue(environment)
    assert len(result.result["queue"]) == 0
    assert result.code == 200

    # request a compile
    remote_id1 = uuid.uuid4()
    await compilerslice.request_recompile(
        env=env, force_update=False, do_export=False, remote_id=remote_id1, env_vars={"my_unique_var": "1"}
    )

    # api should return one
    result = await client.get_compile_queue(environment)
    assert len(result.result["queue"]) == 1
    assert result.result["queue"][0]["remote_id"] == str(remote_id1)
    assert result.code == 200

    # request a compile
    remote_id2 = uuid.uuid4()
    compile_id2, _ = await compilerslice.request_recompile(env=env, force_update=False, do_export=False, remote_id=remote_id2)

    # api should return two
    result = await client.get_compile_queue(environment)
    assert len(result.result["queue"]) == 2
    assert result.result["queue"][1]["remote_id"] == str(remote_id2)
    assert result.code == 200

    # request a compile with do_export=True
    remote_id3 = uuid.uuid4()
    compile_id3, _ = await compilerslice.request_recompile(env=env, force_update=False, do_export=True, remote_id=remote_id3)

    result = await client.get_compile_queue(environment)
    assert len(result.result["queue"]) == 3
    assert result.result["queue"][2]["remote_id"] == str(remote_id3)
    assert result.code == 200

    # request a compile with do_export=False -> expect merge with compile2
    remote_id4 = uuid.uuid4()
    compile_id4, _ = await compilerslice.request_recompile(env=env, force_update=False, do_export=False, remote_id=remote_id4)

    result = await client.get_compile_queue(environment)
    assert len(result.result["queue"]) == 4
    assert result.result["queue"][3]["remote_id"] == str(remote_id4)
    assert result.code == 200

    # request a compile with do_export=True -> expect merge with compile3, expect force_update == True for the compile
    remote_id5 = uuid.uuid4()
    compile_id5, _ = await compilerslice.request_recompile(env=env, force_update=True, do_export=True, remote_id=remote_id5)
    remote_id6 = uuid.uuid4()
    compile_id6, _ = await compilerslice.request_recompile(env=env, force_update=False, do_export=True, remote_id=remote_id6)

    result = await client.get_compile_queue(environment)
    assert len(result.result["queue"]) == 6
    assert result.result["queue"][4]["remote_id"] == str(remote_id5)
    assert result.result["queue"][5]["remote_id"] == str(remote_id6)
    assert result.code == 200

    # finish a compile and wait for service to take on next
    await run_compile_and_wait_until_compile_is_done(compilerslice, mocked_compiler_service_block, env.id)

    # api should return five when ready
    result = await client.get_compile_queue(environment)
    assert len(result.result["queue"]) == 5
    assert result.result["queue"][0]["remote_id"] == str(remote_id2)
    assert result.code == 200

    # finish second compile
    await run_compile_and_wait_until_compile_is_done(compilerslice, mocked_compiler_service_block, env.id)

    assert await compilerslice.get_report(compile_id2) == await compilerslice.get_report(compile_id4)

    # finish third compile
    # prevent race conditions where compile is not yet in queue
    await retry_limited(lambda: not mocked_compiler_service_block.empty(), timeout=10)
    run = mocked_compiler_service_block.get(block=True)
    result = await client.get_compile_queue(environment)
    assert len(result.result["queue"]) == 3
    assert result.result["queue"][0]["remote_id"] == str(remote_id3)
    assert result.code == 200
    run.block = False

    while env.id in compilerslice._recompiles:
        await asyncio.sleep(0.2)

    assert await compilerslice.get_report(compile_id3) == await compilerslice.get_report(compile_id5)
    assert await compilerslice.get_report(compile_id3) == await compilerslice.get_report(compile_id6)

    # api should return none
    result = await client.get_compile_queue(environment)
    assert len(result.result["queue"]) == 0
    assert result.code == 200


@pytest.mark.asyncio
async def test_compilerservice_halt(mocked_compiler_service_block, server, client, environment: uuid.UUID) -> None:
    config.Config.set("server", "auto-recompile-wait", "0")
    compilerslice: CompilerService = server.get_slice(SLICE_COMPILER)

    result = await client.get_compile_queue(environment)
    assert result.code == 200
    assert len(result.result["queue"]) == 0

    await client.halt_environment(environment)

    env = await data.Environment.get_by_id(environment)
    assert env is not None
    await compilerslice.request_recompile(env=env, force_update=False, do_export=False, remote_id=uuid.uuid4())

    result = await client.get_compile_queue(environment)
    assert result.code == 200
    assert len(result.result["queue"]) == 1

    result = await client.is_compiling(environment)
    assert result.code == 204

    await client.resume_environment(environment)
    result = await client.is_compiling(environment)
    assert result.code == 200


@pytest.fixture(scope="function")
async def server_with_frequent_cleanups(server_pre_start, server_config, async_finalizer):
    config.Config.set("server", "compiler-report-retention", "60")
    config.Config.set("server", "cleanup-compiler-reports_interval", "1")
    ibl = InmantaBootloader()
    await ibl.start()
    yield ibl.restserver
    await asyncio.wait_for(ibl.stop(), 15)


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
async def old_and_new_compile_report(server_with_frequent_cleanups, environment_for_cleanup) -> Tuple[uuid.UUID, uuid.UUID]:
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
        "environment_variables": {},
        "success": True,
        "handled": True,
        "version": 1,
    }
    await Compile(**old_compile).insert()
    compile_id_new = uuid.uuid4()
    new_compile = {**old_compile, "id": compile_id_new, "requested": now, "started": now, "completed": now}
    await Compile(**new_compile).insert()

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
    await Report(**report1).insert()
    await Report(**report2).insert()
    yield compile_id_old, compile_id_new


@pytest.mark.asyncio
async def test_compileservice_cleanup(
    server_with_frequent_cleanups,
    client_for_cleanup,
    environment_for_cleanup,
    old_and_new_compile_report: Tuple[uuid.UUID, uuid.UUID],
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


@pytest.mark.asyncio
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
        environment_variables={},
        force_update=True,
    )
    await compile.insert()

    cr = CompileRun(compile, project_work_dir)

    # This should not result in a "local variable referenced before assignment" exception
    success, compile_data = await cr.run()
    assert not success
    assert compile_data is None


@pytest.mark.asyncio
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
        environment_variables={},
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


@pytest.mark.asyncio(timeout=90)
async def test_compileservice_auto_recompile_wait(mocked_compiler_service_block, server, client, environment, caplog):
    """
    Test the auto-recompile-wait setting when multiple recompiles are requested in a short amount of time
    """
    with caplog.at_level(logging.DEBUG):
        env = await data.Environment.get_by_id(environment)
        config.Config.set("server", "auto-recompile-wait", "2")
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
        ).contains(
            "inmanta.server.services.compilerservice",
            logging.INFO,
            "server-auto-recompile-wait is enabled and set to 2 seconds",
        ).contains(
            "inmanta.server.services.compilerservice", logging.DEBUG, "Running recompile without waiting"
        )


@pytest.mark.asyncio
async def test_compileservice_calculate_auto_recompile_wait(mocked_compiler_service_block, server):
    """
    Test the recompile waiting time calculation when auto-recompile-wait configuration option is enabled
    """
    auto_recompile_wait = 2
    config.Config.set("server", "auto-recompile-wait", str(auto_recompile_wait))
    compilerslice: CompilerService = server.get_slice(SLICE_COMPILER)

    now = datetime.datetime.now()
    compile_requested = now - datetime.timedelta(seconds=1)
    last_compile_completed = now - datetime.timedelta(seconds=4)
    waiting_time = compilerslice._calculate_recompile_wait(auto_recompile_wait, compile_requested, last_compile_completed, now)
    assert waiting_time == 0

    compile_requested = now - datetime.timedelta(seconds=0.1)
    last_compile_completed = now - datetime.timedelta(seconds=1)
    waiting_time = compilerslice._calculate_recompile_wait(auto_recompile_wait, compile_requested, last_compile_completed, now)
    assert waiting_time == approx(1)

    compile_requested = now - datetime.timedelta(seconds=1)
    last_compile_completed = now - datetime.timedelta(seconds=0.1)
    waiting_time = compilerslice._calculate_recompile_wait(auto_recompile_wait, compile_requested, last_compile_completed, now)
    assert waiting_time == approx(1)

    compile_requested = now - datetime.timedelta(seconds=4)
    last_compile_completed = now - datetime.timedelta(seconds=1)
    waiting_time = compilerslice._calculate_recompile_wait(auto_recompile_wait, compile_requested, last_compile_completed, now)
    assert waiting_time == 0


@pytest.mark.asyncio
async def test_compileservice_api(client, environment):
    # Exceed max value for limit
    result = await client.get_reports(environment, limit=APILIMIT + 1)
    assert result.code == 400
    assert result.result["message"] == f"Invalid request: limit parameter can not exceed {APILIMIT}, got {APILIMIT+1}."

    result = await client.get_reports(environment, limit=APILIMIT)
    assert result.code == 200
