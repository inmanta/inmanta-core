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

import hashlib
import json
import uuid
from typing import Collection, Mapping, Set

import utils
from inmanta.agent import executor
from inmanta.agent.code_manager import CodeManager
from inmanta.agent.executor import ExecutorBlueprint, ResourceInstallSpec
from inmanta.data import ResourceIdStr
from inmanta.data.model import LEGACY_PIP_DEFAULT, ResourceType
from inmanta.deploy.state import ResourceDetails
from inmanta.protocol import Client
from inmanta.protocol.common import custom_json_encoder
from inmanta.resources import Id
from inmanta.types import JsonType
from utils import retry_limited


def make_requires(resources: Mapping[ResourceIdStr, ResourceDetails]) -> Mapping[ResourceIdStr, Set[ResourceIdStr]]:
    """Convert resources from the scheduler input format to its requires format"""
    return {k: {req for req in resource.attributes.get("requires", [])} for k, resource in resources.items()}


def convert_resource(resource: JsonType) -> ResourceDetails:
    """Convert a resource, in the form they are pushed by the compiler to the format expected by the scheduler"""
    attributes = {}
    for field, value in resource.items():
        if field not in {"id", "version"}:
            attributes[field] = value

    id = Id.parse_id(resource["id"])
    rid = id.resource_str()

    out = {"id": id.resource_version_str(), "model": id.version, "attributes": attributes}

    cleaned_requires = []
    for req in attributes["requires"]:
        theid = Id.parse_id(req)
        cleaned_requires.append(theid.resource_str())
    attributes["requires"] = cleaned_requires

    character = json.dumps(
        {k: v for k, v in attributes.items() if k not in ["requires", "provides", "version"]},
        default=custom_json_encoder,
        sort_keys=True,  # sort the keys for stable hashes when using dicts, see #5306
    )
    m = hashlib.md5()
    m.update(rid.encode("utf-8"))
    m.update(character.encode("utf-8"))
    attribute_hash = m.hexdigest()

    return ResourceDetails(attributes=out, attribute_hash=attribute_hash)


def convert_resources(resources: list[JsonType]) -> Mapping[ResourceIdStr, ResourceDetails]:
    """Convert a set of resources, as they would be pushed to the server, to input for the scheduler"""
    return {rd.rid: rd for rd in (convert_resource(r) for r in resources)}


dummyblueprint = ExecutorBlueprint(
    pip_config=LEGACY_PIP_DEFAULT,
    requirements=[],
    python_version=(3, 11),
    sources=[],
)


class DummyCodeManager(CodeManager):
    """Code manager that prentend no code is ever needed"""

    async def get_code(
        self, environment: uuid.UUID, version: int, resource_types: Collection[ResourceType]
    ) -> tuple[Collection[ResourceInstallSpec], executor.FailedResources]:
        return ([ResourceInstallSpec(rt, version, dummyblueprint) for rt in resource_types], {})


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
