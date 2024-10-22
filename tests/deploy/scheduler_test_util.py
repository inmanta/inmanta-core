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

import uuid
from typing import Collection, Mapping, Set

from inmanta.agent import executor
from inmanta.agent.code_manager import CodeManager
from inmanta.agent.executor import ExecutorBlueprint, ResourceInstallSpec
from inmanta.data import ResourceIdStr
from inmanta.data.model import LEGACY_PIP_DEFAULT, ResourceType
from inmanta.deploy.state import ResourceDetails


def make_requires(resources: Mapping[ResourceIdStr, ResourceDetails]) -> Mapping[ResourceIdStr, Set[ResourceIdStr]]:
    """Convert resources from the scheduler input format to its requires format"""
    return {k: {req for req in resource.attributes.get("requires", [])} for k, resource in resources.items()}


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
