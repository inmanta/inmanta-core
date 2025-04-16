"""
Copyright 2021 Inmanta

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

import datetime
import uuid

import pytest

from inmanta import data
from inmanta.data import Report
from inmanta.server import SLICE_COMPILER
from inmanta.server.services.compilerservice import CompilerService
from inmanta.util import parse_timestamp


def compile_ids(compile_objects):
    return [compile["id"] for compile in compile_objects]


@pytest.fixture
async def env_with_compiles(client, environment):
    compile_requested_timestamps = []
    compiles = []
    # Make sure that timestamp is never older than 7 days,
    # as such that the cleanup service doesn't delete them.
    now = datetime.datetime.now()
    for i in range(4):
        requested = now + datetime.timedelta(minutes=i)
        compile_requested_timestamps.append(requested)
        compile = data.Compile(
            id=uuid.uuid4(),
            remote_id=uuid.uuid4(),
            environment=uuid.UUID(environment),
            requested=requested,
            started=requested + datetime.timedelta(seconds=20),
            completed=requested + datetime.timedelta(seconds=40),
            do_export=True,
            force_update=False,
            metadata={"meta": 42} if i % 2 else None,
            requested_environment_variables={"TEST_ENV_VAR": "True"} if i % 2 else {},
            used_environment_variables={"TEST_ENV_VAR": "True"} if i % 2 else {},
            success=True,
            handled=True,
            version=1,
            substitute_compile_id=None,
            compile_data={"errors": [{"type": "UnexpectedException", "message": "msg"}]} if i % 2 else None,
            links={"instances": [f"my-link{i}"], f"test-{i}": [f"my-link{i}"]},
        )
        compiles.append(compile)
    compiles[1].substitute_compile_id = compiles[0].id
    compiles[2].substitute_compile_id = compiles[1].id
    for compile in compiles:
        await compile.insert()
    ids = [compile.id for compile in compiles]

    await Report(
        id=uuid.uuid4(),
        started=datetime.datetime.now(),
        completed=datetime.datetime.now(),
        command="inmanta export",
        name="name",
        errstream="error",
        outstream="success",
        returncode=0,
        compile=ids[0],
    ).insert()
    await Report(
        id=uuid.uuid4(),
        started=datetime.datetime.now(),
        completed=datetime.datetime.now(),
        command="inmanta export",
        name="another_name",
        errstream="error",
        outstream="success",
        returncode=0,
        compile=ids[0],
    ).insert()

    return environment, ids, compile_requested_timestamps


async def test_compile_details(server, client, env_with_compiles):
    environment, ids, compile_requested_timestamps = env_with_compiles

    # A compile that has no substitute_compile_id, and has reports
    result = await client.compile_details(environment, ids[0])
    assert result.code == 200
    reports = result.result["data"]["reports"]
    assert len(reports) == 2
    assert parse_timestamp(reports[0]["started"]) < parse_timestamp(reports[1]["started"])
    assert uuid.UUID(result.result["data"]["id"]) == ids[0]
    assert parse_timestamp(result.result["data"]["requested"]) == compile_requested_timestamps[0].astimezone(
        datetime.timezone.utc
    )
    # Assert that the links are correct
    links = result.result["data"]["links"]
    assert links == {"instances": ["my-link0"], "test-0": ["my-link0"]}

    # A compile that is 2 levels deep in substitutions: id2 -> id1 -> id0
    result = await client.compile_details(environment, ids[2])
    assert result.code == 200
    substituted_reports = result.result["data"]["reports"]
    assert len(substituted_reports) == 2
    assert substituted_reports == reports
    assert uuid.UUID(result.result["data"]["id"]) == ids[2]
    assert parse_timestamp(result.result["data"]["requested"]) == compile_requested_timestamps[2].astimezone(
        datetime.timezone.utc
    )
    # Assert that the links of the substitutions are also present
    # Assert that "self" is the link of the requested compile
    links = result.result["data"]["links"]
    assert links == {
        "instances": ["my-link0", "my-link1", "my-link2"],
        "test-0": ["my-link0"],
        "test-1": ["my-link1"],
        "test-2": ["my-link2"],
    }

    # A compile that has no reports
    result = await client.compile_details(environment, ids[3])
    assert result.code == 200
    assert not result.result["data"]["reports"]

    # Assert that even without a report, we still get the correct links
    links = result.result["data"]["links"]
    assert links == {"instances": ["my-link3"], "test-3": ["my-link3"]}

    # An id that doesn't exist as a compile
    result = await client.compile_details(environment, uuid.uuid4())
    assert result.code == 404

    # Test passing links via request_recompile
    env = await data.Environment.get_by_id(environment)
    compilerslice: CompilerService = server.get_slice(SLICE_COMPILER)
    compile_id, _ = await compilerslice.request_recompile(
        env, force_update=False, do_export=False, remote_id=uuid.uuid4(), links={"example-link": ["localhost:8888"]}
    )
    result = await client.compile_details(environment, compile_id)
    assert result.code == 200
    assert result.result["data"]["links"] == {"example-link": ["localhost:8888"]}
