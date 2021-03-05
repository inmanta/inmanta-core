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
import re
import datetime
import logging
from typing import Optional

import pytest

from inmanta import const
from inmanta.util import get_compiler_version
from utils import _wait_until_deployment_finishes

logger = logging.getLogger("inmanta.test.wip")


@pytest.mark.asyncio
async def test_wip(resource_container, environment, server, client, agent, clienthelper):
    """
    Send and receive events within one agent
    """
    resource_container.Provider.reset()

    version = None
    res_id_1 = None
    res_id_2 = None

    for i in range(0, 5):

        version = await clienthelper.get_version()

        res_id_1 = "test::Resource[agent1,key=key1],v=%d" % version
        res_id_2 = "test::Resource[agent1,key=key2],v=%d" % version
        res_id_3 = "test::Resource[agent1,key=key3],v=%d" % version
        
        resources = [
            {
                "key": "key1",
                "value": f"value{int((i + 1) / 2)}",
                "id": res_id_1,
                "send_event": False,
                "purged": False,
                "requires": [res_id_3, res_id_2],
            },
            {
                "key": "key2",
                "value": f"value{i}",
                "id": res_id_2,
                "send_event": True,
                "requires": [res_id_3],
                "purged": False,
            },
            {
                "key": "key3",
                "value": "value",
                "id": res_id_3,
                "send_event": True,
                "requires": [],
                "purged": False,
            },
        ]

        result = await client.put_version(
            tid=environment,
            version=version,
            resources=resources,
            unknowns=[],
            version_info={},
            compiler_version=get_compiler_version(),
        )
        assert result.code == 200

        # do a deploy
        result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
        assert result.code == 200

        result = await client.get_version(environment, version)
        assert result.code == 200

        await _wait_until_deployment_finishes(client, environment, version)

    async def get_last_change(
        resource_type: str,
        agent: str,
        key: str,
        value: str,
        before: Optional[datetime.datetime] = None,
    ):
        before = before or datetime.datetime.now()

        while before is not None:
            result = await client.get_resource_actions(
                tid=environment,
                resource_type=resource_type,
                agent=agent,
                attribute=key,
                attribute_value=value,
                limit=1,
                last_timestamp=before,
            )
            assert result.code == 200

            actions = result.result.get("data", [])

            for action in actions:
                if action.get("action", "") != "deploy":
                    continue
                change = action.get("change") or "nochange"
                if change != "nochange":
                    return {
                        "change": change,
                        "finished": action.get("finished"),
                        "version": action.get("version"),
                    }

            if len(actions) == 0:
                before = None
            else:
                before = actions[-1].get("started")

        return None

    async def get_first_change(
        resource_type: str,
        agent: str,
        key: str,
        value: str,
        after: Optional[datetime.datetime] = None,
    ):
        after = after or datetime.datetime.fromtimestamp(0)

        while after is not None:
            result = await client.get_resource_actions(
                tid=environment,
                resource_type=resource_type,
                agent=agent,
                attribute=key,
                attribute_value=value,
                limit=1,
                first_timestamp=after,
            )
            assert result.code == 200

            actions = result.result.get("data", [])
            actions.reverse()

            for action in actions:
                change = action.get("change") or "nochange"
                if change != "nochange":
                    return {
                        "change": change,
                        "finished": action.get("finished"),
                        "version": action.get("version"),
                    }

            if len(actions) == 0:
                after = None
            else:
                after = actions[-1].get("started")

        return None

    last_change_1 = await get_last_change(
        resource_type="test::Resource",
        agent="agent1",
        key="key",
        value="key1",
    )

    last_change_2 = await get_last_change(
        resource_type="test::Resource",
        agent="agent1",
        key="key",
        value="key2",
    )

    last_change_3 = await get_last_change(
        resource_type="test::Resource",
        agent="agent1",
        key="key",
        value="key3",
    )

    first_change_1 = await get_first_change(
        resource_type="test::Resource",
        agent="agent1",
        key="key",
        value="key1",
    )

    first_change_2 = await get_first_change(
        resource_type="test::Resource",
        agent="agent1",
        key="key",
        value="key2",
    )

    first_change_3 = await get_first_change(
        resource_type="test::Resource",
        agent="agent1",
        key="key",
        value="key3",
    )

    import json
    logger.info("Last change for key1: " + json.dumps(last_change_1, indent=2))
    logger.info("Last change for key2: " + json.dumps(last_change_2, indent=2))
    logger.info("Last change for key3: " + json.dumps(last_change_3, indent=2))
    logger.info("First change for key1: " + json.dumps(first_change_1, indent=2))
    logger.info("First change for key2: " + json.dumps(first_change_2, indent=2))
    logger.info("First change for key3: " + json.dumps(first_change_3, indent=2))


    async def get_dependencies(id: str) -> str:
        logger.info(id)
        result = await client.get_resource(environment, id=id, logs=True)
        assert result.code == 200

        return result.result.get("resource", {}).get("attributes", {}).get("requires")


    async def need_redeploy(
        resource_type: str,
        agent: str,
        key: str,
        value: str,
    ) -> bool:
        last_deployment = await get_last_change(resource_type, agent, key, value)
        logger.info(f"Last deployment of self: {last_deployment['finished']}")

        # Check dependencies
        dependencies = await get_dependencies(
            f"{resource_type}[{agent},{key}={value}],v={last_deployment.get('version')}"
        )

        resource_id = re.compile(r"(.*)\[(.*),(.*)=(.*)\]")

        # For each dependency, check first change after last_deployment
        # If any change, needs redeploy
        for dependency in dependencies:
            reg_match = resource_id.match(dependency)
            dep_resource_type = reg_match.group(1)
            dep_agent = reg_match.group(2)
            dep_key = reg_match.group(3)
            dep_value = reg_match.group(4)

            logger.info(f"Checking dependency {dependency}")
            first_change = await get_first_change(
                resource_type=dep_resource_type,
                agent=dep_agent,
                key=dep_key,
                value=dep_value,
                after=last_deployment["finished"],
            )
            if first_change is not None:
                logger.info(f"Last redeployment of dependency: {first_change['finished']} (version {first_change['version']})")
                return True

        return False
    
    logger.info(await need_redeploy(
        resource_type="test::Resource",
        agent="agent1",
        key="key",
        value="key1",
    ))
    logger.info(await need_redeploy(
        resource_type="test::Resource",
        agent="agent1",
        key="key",
        value="key2",
    ))
    logger.info(await need_redeploy(
        resource_type="test::Resource",
        agent="agent1",
        key="key",
        value="key3",
    ))