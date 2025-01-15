"""
    Copyright 2025 Inmanta

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
from datetime import timedelta

from inmanta import const, data
from inmanta.util import retry_limited


async def test_notification_mechanism(agent, environment, clienthelper, client, resource_container):
    """
    Test signaling of server to scheduler

    detailed tests of the update proper are in test_timer_handling
    """
    await clienthelper.set_auto_deploy(True)
    result = await client.set_setting(environment, data.AUTOSTART_AGENT_REPAIR_INTERVAL, 3600)
    assert result.code == 200
    result = await client.set_setting(environment, data.AUTOSTART_AGENT_DEPLOY_INTERVAL, 60)
    assert result.code == 200

    rid1 = "test::Resource[agent1,key=1]"
    rid2 = "test::Resource[agent1,key=2]"

    # one deployed
    # one failed
    # one undeployable
    version = await clienthelper.get_version()

    resources = [
        {
            "key": "1",
            "id": rid1 + f",v={version}",
            "requires": [],
            "value": "vx",
            const.RESOURCE_ATTRIBUTE_SEND_EVENTS: False,
            "purged": False,
        },
        {
            "key": "2",
            "id": rid2 + f",v={version}",
            "requires": [],
            "value": "vx",
            const.RESOURCE_ATTRIBUTE_SEND_EVENTS: False,
            "purged": False,
        },
    ]

    resource_container.Provider.set_fail("agent1", "1", 10)

    await clienthelper.put_version_simple(resources, version, wait_for_released=True)
    await clienthelper.wait_for_deployed()
    last_deploy_time_approx = datetime.datetime.now().astimezone()

    tm = agent.scheduler._timer_manager

    def is_approx(rid: str, seconds: int) -> None:
        time = tm.resource_timers[rid].next_scheduled_time
        assert abs(time - last_deploy_time_approx - timedelta(seconds=seconds)) < timedelta(milliseconds=200)

    # All per resource
    assert tm.global_periodic_repair_task is None
    assert tm.global_periodic_deploy_task is None
    is_approx(rid1, 60)
    is_approx(rid2, 3600)

    result = await client.set_setting(environment, data.AUTOSTART_AGENT_REPAIR_INTERVAL, 36000)
    assert result.code == 200
    result = await client.set_setting(environment, data.AUTOSTART_AGENT_DEPLOY_INTERVAL, 600)
    assert result.code == 200

    async def is_done() -> bool:
        try:
            assert tm.global_periodic_repair_task is None
            assert tm.global_periodic_deploy_task is None
            is_approx(rid1, 600)
            is_approx(rid2, 36000)
            return True
        except AssertionError:
            return False

    await retry_limited(is_done, 1)
