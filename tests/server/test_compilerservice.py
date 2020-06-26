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
import shutil
import subprocess
import uuid
from asyncio import Semaphore
from typing import List

import pytest

from inmanta import config, data
from inmanta.const import ParameterSource
from inmanta.data import Compile, Report
from inmanta.deploy import cfg_env
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

        async def run(self):
            self.started = True
            await self.lock.acquire()
            self.done = True
            return True

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
        await cs.request_recompile(env, False, False, u1)
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
async def test_compile_runner(server, tmpdir, client):
    # create project, printing env
    project_source_dir = os.path.join(tmpdir, "src")

    project_template = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "project")

    shutil.copytree(project_template, project_source_dir)
    subprocess.check_output(["git", "init"], cwd=project_source_dir)
    subprocess.check_output(["git", "add", "*"], cwd=project_source_dir)
    subprocess.check_output(["git", "config", "user.name", "Unit"], cwd=project_source_dir)
    subprocess.check_output(["git", "config", "user.email", "unit@test.example"], cwd=project_source_dir)
    subprocess.check_output(["git", "commit", "-m", "unit test"], cwd=project_source_dir)

    testmarker_env = "TESTMARKER"
    no_marker = "__no__marker__"
    marker_print = "_INM_MM:"
    marker_print2 = "_INM_MM2:"
    marker_print3 = "_INM_MM3:"

    def make_main(marker_print):
        # add main.cf
        with open(os.path.join(project_source_dir, "main.cf"), "w", encoding="utf-8") as fd:
            fd.write(
                f"""
    marker = std::get_env("{testmarker_env}","{no_marker}")
    std::print("{marker_print} {{{{marker}}}}")

    host = std::Host(name="test", os=std::linux)
    std::ConfigFile(host=host, path="/etc/motd", content="1234")
    """
            )

        subprocess.check_output(["git", "add", "main.cf"], cwd=project_source_dir)
        subprocess.check_output(["git", "commit", "-m", "unit test 2"], cwd=project_source_dir)

    make_main(marker_print)
    subprocess.check_output("git checkout -b alt".split(), cwd=project_source_dir)
    make_main(marker_print2)

    project_work_dir = os.path.join(tmpdir, "work")
    ensure_directory_exist(project_work_dir)

    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url=project_source_dir, repo_branch="master")
    await env.insert()

    env2 = data.Environment(name="devalt", project=project.id, repo_url=project_source_dir, repo_branch="alt")
    await env2.insert()

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
    assert stages["switching branch from master to alt"]["returncode"] == 0
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

    make_main(marker_print3)
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
async def test_e2e_recompile_failure(compilerservice: CompilerService):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    u1 = uuid.uuid4()
    await compilerservice.request_recompile(env, False, False, u1)
    u2 = uuid.uuid4()
    await compilerservice.request_recompile(env, False, False, u2)

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


@pytest.mark.asyncio(timeout=90)
async def test_compileservice_queue(mocked_compiler_service_block, server, client, environment):
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
    compile_id1 = uuid.uuid4()
    await compilerslice.request_recompile(env=env, force_update=False, do_export=False, remote_id=compile_id1)

    # api should return one
    result = await client.get_compile_queue(environment)
    assert len(result.result["queue"]) == 1
    assert result.result["queue"][0]["remote_id"] == str(compile_id1)
    assert result.code == 200

    # request a compile
    compile_id2 = uuid.uuid4()
    await compilerslice.request_recompile(env=env, force_update=False, do_export=False, remote_id=compile_id2)

    # api should return two
    result = await client.get_compile_queue(environment)
    assert len(result.result["queue"]) == 2
    assert result.result["queue"][1]["remote_id"] == str(compile_id2)
    assert result.code == 200

    # finish a compile and wait for service to take on next
    current_task = compilerslice._recompiles[env.id]

    run = mocked_compiler_service_block.get()
    run.block = False

    while current_task is compilerslice._recompiles[env.id]:
        await asyncio.sleep(0.01)

    # api should return one when ready
    result = await client.get_compile_queue(environment)
    assert len(result.result["queue"]) == 1
    assert result.code == 200

    # finish a compile
    current_task = compilerslice._recompiles[env.id]

    run = mocked_compiler_service_block.get()
    run.block = False

    while env.id in compilerslice._recompiles and current_task is compilerslice._recompiles[env.id]:
        await asyncio.sleep(0.01)

    # return

    # api should return none
    result = await client.get_compile_queue(environment)
    assert len(result.result["queue"]) == 0
    assert result.code == 200


@pytest.fixture(scope="function")
async def server_with_frequent_cleanups(server_pre_start, server_config, async_finalizer):
    config.Config.set("server", "compiler-report-retention", "2")
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
async def old_compile_report(server_with_frequent_cleanups, environment_for_cleanup):
    now = datetime.datetime.now()
    time_of_compile = now - datetime.timedelta(days=30)
    compile_id = uuid.UUID("c00cc33f-f70f-4800-ad01-ff042f67118f")
    old_compile = {
        "id": compile_id,
        "remote_id": uuid.UUID("c9a10da1-9bf6-4152-8461-98adc02c4cee"),
        "environment": uuid.UUID(environment_for_cleanup),
        "requested": time_of_compile,
        "started": time_of_compile,
        "completed": time_of_compile,
        "do_export": True,
        "force_update": True,
        "metadata": {"type": "api", "message": "Recompile trigger through API call"},
        "environment_variables": {},
        "success": True,
        "handled": True,
        "version": 1,
    }
    await Compile(**old_compile).insert()
    new_compile = {**old_compile, "id": uuid.uuid4(), "requested": now, "started": now, "completed": now}
    await Compile(**new_compile).insert()

    report1 = {
        "id": uuid.UUID("2baa0175-9169-40c5-a546-64d646f62da6"),
        "started": time_of_compile,
        "completed": time_of_compile,
        "command": "",
        "name": "Init",
        "errstream": "",
        "outstream": "Using extra environment variables during compile \n",
        "returncode": 0,
        "compile": compile_id,
    }
    report2 = {
        **report1,
        "id": uuid.UUID("2a86d2a0-666f-4cca-b0a8-13e0379128d5"),
        "command": "python -m inmanta.app -vvv export -X",
        "name": "Recompiling configuration model",
    }
    await Report(**report1).insert()
    await Report(**report2).insert()
    yield compile_id


@pytest.mark.asyncio
async def test_compileservice_cleanup(
    server_with_frequent_cleanups, client_for_cleanup, environment_for_cleanup, old_compile_report
):
    # There is a new and an older report in the database
    result = await client_for_cleanup.get_reports(environment_for_cleanup)
    assert result.code == 200
    assert len(result.result["reports"]) == 2

    result = await client_for_cleanup.get_report(old_compile_report)
    assert result.code == 200
    assert len(result.result["report"]["reports"]) > 0

    compilerslice: CompilerService = server_with_frequent_cleanups.get_slice(SLICE_COMPILER)
    await compilerslice._cleanup()

    # The old report is deleted after cleanup
    result = await client_for_cleanup.get_report(old_compile_report)
    assert result.code == 404
    reports_after_cleanup = await Report.get_list(compile=old_compile_report)
    assert len(reports_after_cleanup) == 0

    # The new report is still there
    result = await client_for_cleanup.get_reports(environment_for_cleanup)
    assert result.code == 200
    assert len(result.result["reports"]) == 1


@pytest.mark.slowtest
@pytest.mark.asyncio
async def test_compileservice_cleanup_on_trigger(client_for_cleanup, environment_for_cleanup, old_compile_report):
    # Two reports are in the table
    result = await client_for_cleanup.get_reports(environment_for_cleanup)
    assert result.code == 200
    assert len(result.result["reports"]) == 2

    result = await client_for_cleanup.get_report(old_compile_report)
    assert result.code == 200
    assert len(result.result["report"]["reports"]) > 0

    await asyncio.sleep(3)

    # Both reports should be deleted after the triggered cleanup
    result = await client_for_cleanup.get_reports(environment_for_cleanup)
    assert result.code == 200
    assert len(result.result["reports"]) == 0
