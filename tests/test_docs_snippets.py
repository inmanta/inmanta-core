"""
    Copyright 2022 Inmanta

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

"""
Tests to verify correctness/compatibility of code snippets in the docs.
"""

import os
import uuid
from collections import defaultdict
from collections import abc

import pytest

from inmanta import data
from inmanta.data import model
from inmanta.export import ResourceDict
from inmanta.protocol.common import Result


DOCS_DIR: str = os.path.join(os.path.dirname(__file__), "..", "docs")


@pytest.mark.slowtest
async def test_docs_snippet_partial_compile(snippetcompiler, server, client, environment: str) -> None:
    """
    Verify that the partial compile example model is valid and is in fact equivalent to the full model it is compared to.
    """
    env_id: uuid.UUID = uuid.UUID(environment)
    snippets_dir: str = os.path.join(DOCS_DIR, "resource_sets")
    version: int

    def build_model(base: str) -> str:
        """
        Create a model from the base one, adding exportable resources.
        """
        resources_addition: str = """
            host = std::Host(name="test", os=std::linux)

            implementation std_resources for Router:
                file = std::ConfigFile(
                    host=host, path="{{ self.network.id }}-{{ self.id }}", content=""
                )
                set = std::ResourceSet(name="network-{{ self.network.id }}")
                set.resources += file
            end

            implement Router using std_resources
        """.strip()
        return "\n".join((base, resources_addition))

    async def get_routers_by_network(version: int) -> abc.Mapping[int, abc.Set[int]]:
        resources: abc.Sequence[data.Resource] = await data.Resource.get_resources_for_version(env_id, version)
        routers_by_network: dict[int, set[int]] = defaultdict(set)
        for resource in resources:
            if resource.resource_type == model.ResourceType("std::File"):
                network, router = (int(i) for i in resource.attributes["path"].split("-", maxsplit=1))
                routers_by_network[network].add(router)
        return routers_by_network

    # initial export
    with open(os.path.join(snippets_dir, "basic_example_full.cf")) as fd:
        snippetcompiler.setup_for_snippet(build_model(fd.read()))
    version, _ = await snippetcompiler.do_export_and_deploy()
    routers_by_network_full: abc.Mapping[int, abc.Set[int]] = await get_routers_by_network(version)
    assert len(routers_by_network_full) == 1000
    for network in routers_by_network_full:
        assert len(routers_by_network_full[network]) == 5

    # partial export: verify that only the example's set has changed
    with open(os.path.join(snippets_dir, "basic_example_partial.cf")) as fd:
        snippetcompiler.setup_for_snippet(build_model(fd.read()))
    version, _ = await snippetcompiler.do_export_and_deploy(partial_compile=True)
    routers_by_network_partial: abc.Mapping[int, abc.Set[int]] = await get_routers_by_network(version)
    assert len(routers_by_network_partial) == 1000
    for network in routers_by_network_partial:
        assert len(routers_by_network_partial[network]) == (1 if network == 0 else 5)

    # full equivalent export: verify that it is indeed equivalent
    with open(os.path.join(snippets_dir, "basic_example_full_result.cf")) as fd:
        snippetcompiler.setup_for_snippet(build_model(fd.read()))
    version, _ = await snippetcompiler.do_export_and_deploy()
    routers_by_network_equivalent: abc.Mapping[int, abc.Set[int]] = await get_routers_by_network(version)
    assert routers_by_network_equivalent == routers_by_network_partial
