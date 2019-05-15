import asyncio
import logging
import uuid
from asyncio import Semaphore

import pytest
from typing import List

from inmanta import data
from inmanta.server.compilerservice import CompilerService
from inmanta.server.protocol import Server
from utils import retry_limited, log_contains


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
    caplog.set_level(logging.WARNING)
    class HangRunner(object):
        def __init__(self):
            self.lock = Semaphore(0)
            self.started = False
            self.done = False

        async def run(self):
            self.started = True
            await self.lock.acquire()
            self.done = True
            return True

        def release(self):
            self.lock.release()

    class HookedCompilerService(CompilerService):
        def __init__(self):
            super(HookedCompilerService, self).__init__()
            self.locks = {}

        def _get_compile_runner(self, compile: data.Compile, project_dir: str):
            print("X: ", compile.remote_id, compile.id)
            runner = HangRunner()
            self.locks[compile.remote_id] = runner
            return runner

        def get_runner(self, remote_id: uuid.UUID) -> HangRunner:
            return self.locks.get(remote_id)

    server = Server()
    cs = HookedCompilerService()
    await cs.prestart(server)
    await cs.start()

    async def request_compile(env: data.Environment) -> uuid.UUID:
        u1 = uuid.uuid4()
        await cs.request_recompile(env, False, False, u1)
        results = await data.Compile.get_by_remote_id(u1)
        assert len(results) == 1
        assert results[0].remote_id == u1
        print(u1, results[0].id)
        return u1

    project = data.Project(name="test")
    await project.insert()

    env1 = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env1.insert()

    env2 = data.Environment(name="dev2", project=project.id, repo_url="", repo_branch="")
    await env2.insert()

    print()
    e1 = [await request_compile(env1) for i in range(3)]
    e2 = [await request_compile(env2) for i in range(4)]
    print(e1)

    async def check_stage(env: data.Environment, remote_ids: List[uuid.UUID], idx: int):
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

    for i in range(4):
        await check_stage(env1, e1, i)

    for i in range(2):
        print(i)
        await check_stage(env2, e2, i)

    # test server restart
    await cs.prestop()
    await cs.stop()

    log_contains(caplog, "inmanta.util", logging.WARNING, "was cancelled")

    cs = HookedCompilerService()
    await cs.prestart(server)
    await cs.start()

    for i in range(3):
        print(i)
        await check_stage(env2, e2[2:], i)


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
        assert "Creating project directory for environment" in init["outstream"]

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
