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

from inmanta.agent import executor
from inmanta.agent.code_manager import CodeManager
from inmanta.agent.executor import ExecutorBlueprint, ResourceInstallSpec
from inmanta.data import ResourceIdStr
from inmanta.data.model import LEGACY_PIP_DEFAULT, ResourceType
from inmanta.deploy.state import ResourceDetails
from inmanta.protocol.common import custom_json_encoder
from inmanta.resources import Id
from inmanta.types import JsonType


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

    return ResourceDetails(out, attribute_hash)


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
