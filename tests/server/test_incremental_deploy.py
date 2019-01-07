"""
    Copyright 2016 Inmanta

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
import pytest
import time
from inmanta.server import SLICE_SERVER
import uuid
from datetime import datetime
from inmanta import data, const
from inmanta.const import ResourceState
import logging


@pytest.mark.asyncio
async def test_deploy(server, environment, caplog):
    """
        Test basic deploy mechanism mocking
    """
    with caplog.at_level(logging.WARNING):
        # acquire raw server
        serverdirect = server.get_endpoint(SLICE_SERVER)

        # acquire env object
        env = await data.Environment.get_by_id(uuid.UUID(environment))

        version = int(time.time())

        def make_resources(version):
            return [
                {
                    "key": "key1",
                    "id": "test::Resource[agent1,key=key1],v=%d" % version,
                    "send_event": False,
                    "purged": False,
                    "requires": [],
                },
                {
                    "key": "key2",
                    "id": "test::Resource[agent1,key=key2],v=%d" % version,
                    "send_event": False,
                    "requires": ["test::Resource[agent1,key=key2],v=%d" % version],
                    "purged": False,
                },
                {
                    "key": "key3",
                    "id": "test::Resource[agent1,key=key3],v=%d" % version,
                    "send_event": False,
                    "requires": ["test::Resource[agent2,key=key4],v=%d" % version],
                    "purged": True,
                },
                {
                    "key": "key4",
                    "id": "test::Resource[agent2,key=key4],v=%d" % version,
                    "send_event": False,
                    "requires": [],
                },
            ]

        resources = make_resources(version)
        res = await serverdirect.put_version(
            env=env,
            version=version,
            resources=resources,
            unknowns=[],
            version_info={},
            resource_state={},
        )
        assert res == 200

        result, _ = await serverdirect.release_version(env, version, push=False)
        assert result == 200

        resource_ids = [x["id"] for x in resources]

        # Start the deploy
        action_id = uuid.uuid4()
        now = datetime.now()
        result = await serverdirect.resource_action_update(
            env,
            resource_ids,
            action_id,
            const.ResourceAction.deploy,
            now,
            now,
            status=ResourceState.deployed,
            messages=[],
            changes={},
            change=None,
            send_events=False,
        )
        assert result == 200

        result, payload = await serverdirect.get_version(env, version)
        assert result == 200
        assert payload["model"].done == len(resources)

        # second, identical check_version
        v2 = version + 1
        resources = make_resources(v2)
        res = await serverdirect.put_version(
            env=env,
            version=v2,
            resources=resources,
            unknowns=[],
            version_info={},
            resource_state={},
        )
        assert res == 200

        result, payload = await serverdirect.get_resource_increment_for_agent(
            env, "agent1"
        )
        assert len(payload["resources"]) == 0

    for record in caplog.records:
        assert record.levelname != "WARNING"
