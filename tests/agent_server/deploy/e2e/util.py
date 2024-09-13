"""
    Copyright 2024 Inmanta

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

import utils
from inmanta.protocol import Client
from utils import retry_limited


async def _wait_until_deployment_finishes(client: Client, environment: str, version: int = -1, timeout: int = 10) -> None:
    """Interface kept for backward compat"""

    async def done():
        result = await client.resource_list(environment, deploy_summary=True)
        assert result.code == 200
        summary = result.result["metadata"]["deploy_summary"]
        # {'by_state': {'available': 3, 'cancelled': 0, 'deployed': 12, 'deploying': 0, 'failed': 0, 'skipped': 0,
        #               'skipped_for_undefined': 0, 'unavailable': 0, 'undefined': 0}, 'total': 15}
        print(summary)
        available = summary["by_state"]["available"]
        deploying = summary["by_state"]["deploying"]
        return available + deploying == 0

    await retry_limited(done, 10)


async def wait_full_success(client: Client, environment: str, version: int = -1, timeout: int = 10) -> None:
    """Interface kept for backward compat"""

    async def done():
        result = await client.resource_list(environment, deploy_summary=True)
        assert result.code == 200
        summary = result.result["metadata"]["deploy_summary"]
        # {'by_state': {'available': 3, 'cancelled': 0, 'deployed': 12, 'deploying': 0, 'failed': 0, 'skipped': 0,
        #               'skipped_for_undefined': 0, 'unavailable': 0, 'undefined': 0}, 'total': 15}
        print(summary)
        total = summary["total"]
        success = summary["by_state"]["deployed"]
        return total == success

    await retry_limited(done, 10)


class ClientHelper(utils.ClientHelper):

    async def wait_for_deployed(self, version: int = -1) -> None:
        await _wait_until_deployment_finishes(self.client, self.environment)
