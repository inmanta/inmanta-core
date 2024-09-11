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
        total = summary["total"]
        available = summary["by_state"]["available"]
        deploying = summary["by_state"]["deploying"]
        return available + deploying == 0

    await retry_limited(done, 10)
