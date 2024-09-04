import hashlib
import json
import uuid
from typing import Collection, Mapping, Set

from inmanta.agent import executor
from inmanta.agent.code_manager import CodeManager
from inmanta.agent.executor import ExecutorBlueprint, ResourceDetails, ResourceInstallSpec
from inmanta.data import ResourceIdStr
from inmanta.data.model import LEGACY_PIP_DEFAULT, ResourceType
from inmanta.deploy.state import ResourceDetails
from inmanta.protocol.common import custom_json_encoder
from inmanta.resources import Id
from inmanta.types import JsonType


def make_requires(resources: Mapping[ResourceIdStr, ResourceDetails]) -> Mapping[ResourceIdStr, Set[ResourceIdStr]]:
    return {k: {req for req in resource.attributes.get("requires", [])} for k, resource in resources.items()}


def convert_resource(resource: JsonType) -> ResourceDetails:

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
    return {rd.rid: rd for rd in (convert_resource(r) for r in resources)}


dummyblueprint = ExecutorBlueprint(
    pip_config=LEGACY_PIP_DEFAULT,
    requirements=[],
    python_version=(3, 11),
    sources=[],
)


class DummyCodeManager(CodeManager):

    async def get_code(
        self, environment: uuid.UUID, version: int, resource_types: Collection[ResourceType]
    ) -> tuple[Collection[ResourceInstallSpec], executor.FailedResources]:
        return ([ResourceInstallSpec(rt, version, dummyblueprint) for rt in resource_types], {})
