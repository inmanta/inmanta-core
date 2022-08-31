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

import asyncio
import datetime
import json
import uuid

import pytest
from pyformance import global_registry, timer

from inmanta import const
from inmanta.const import Change
from inmanta.data import Environment
from inmanta.data.model import AttributeStateChange, DesiredStateVersion
from inmanta.resources import Id
from inmanta.server import SLICE_ORCHESTRATION, SLICE_RESOURCE
from inmanta.server.services import orchestrationservice
from inmanta.server.services.resourceservice import ResourceService


@pytest.fixture(scope="function")
def database_name():
    return "inmanta"

@pytest.fixture
async def server_pre_start(server_config, postgresql_client):
    """This fixture is called by the server. Override this fixture to influence server config"""
    orchestrationservice.PERFORM_CLEANUP = False
    await postgresql_client.execute("update public.environment set halted = true;")

@pytest.fixture(scope="function")
async def clean_db(postgresql_pool, postgres_db):
    pass

async def test_resource_deploy_performance(server, client):
    result = await client.environment_list()

    env_counted = []
    for env in result.result["data"]:
        result = await client.list_desired_state_versions(
            tid = env["id"],
            limit = 1,
        )
        dvs = result.result["data"]
        if dvs:
            dv = DesiredStateVersion(**dvs[0])
            env_counted.append((dv.total, env["id"]))

    version, envid = sorted(env_counted)[-1]

    result = await client.resource_list(
        tid = envid,
        limit = 25,
    )
    env = await Environment.get_by_id(envid)
    resource_orchestrator: ResourceService = server.get_slice(SLICE_RESOURCE)

    for resource in result.result["data"]:
        rvid = Id.parse_id(resource["resource_version_id"])
        action_id = uuid.uuid4()
        print(".", end="")

        with timer("rpc.resource_deploy_start").time():
            await resource_orchestrator.resource_deploy_start(env=env, resource_id=rvid, action_id=action_id)

        with timer("rpc.resource_did_dependency_change").time():
            await resource_orchestrator.resource_did_dependency_change(env=env, resource_id=rvid)

        with timer("rpc.resource_deploy_done").time():
            await resource_orchestrator.resource_deploy_done(env=env, resource_id=rvid, action_id=action_id, status=const.ResourceState.deployed, messages=[], changes={}, change=Change.nochange)

    print(json.dumps(global_registry().dump_metrics(), indent=4))
