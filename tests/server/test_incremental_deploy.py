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

from re import sub

import pytest

from inmanta import data


def strip_version(v):
    return sub(",v=[0-9]+", "", v)


@pytest.mark.slowtest
async def test_release_stuck(
    server,
    environment,
    clienthelper,
    client,
    project_default,
):
    async def make_version() -> int:
        version = await clienthelper.get_version()
        rvid = f"test::Resource[agent1,key=key1],v={version}"
        resources = [
            {
                "key": "key1",
                "value": "value1",
                "id": rvid,
                "change": False,
                "send_event": True,
                "purged": False,
                "requires": [],
                "purge_on_delete": False,
            },
        ]
        await clienthelper.put_version_simple(resources, version, wait_for_released=True)
        return version

        # set auto deploy and push

    result = await client.set_setting(environment, data.AUTO_DEPLOY, True)
    assert result.code == 200

    #  a version v1 is deploying
    await make_version()

    #  a version v2 is deploying
    await make_version()

    # Delete environment
    result = await client.environment_delete(environment)
    assert result.code == 200

    # Re-create
    result = await client.create_environment(project_id=project_default, name="env", environment_id=environment)
    assert result.code == 200
    result = await client.set_setting(environment, data.AUTO_DEPLOY, True)
    assert result.code == 200

    await make_version()
    # This will time-out when there is a run_ahead_lock still in place
    await make_version()
