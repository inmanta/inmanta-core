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
import py
import textwrap
import uuid
from collections import defaultdict
from collections import abc

import pytest

from inmanta import data
from inmanta.data import model
from inmanta.export import ResourceDict
from inmanta.protocol.common import Result
from utils import v1_module_from_template


DOCS_DIR: str = os.path.join(os.path.dirname(__file__), "..", "docs")


@pytest.mark.slowtest
async def test_docs_snippet_partial_compile(
    tmpdir: py.path.local, snippetcompiler, modules_dir: str, server, client, environment: str
) -> None:
    """
    Verify that the partial compile example model is valid and is in fact equivalent to the full model it is compared to.
    """
    env_id: uuid.UUID = uuid.UUID(environment)
    snippets_dir: str = os.path.join(DOCS_DIR, "resource_sets")
    version: int

    handler_module_name: str = "router_handlers"
    v1_module_from_template(
        os.path.join(modules_dir, "minimalv1module"),
        str(tmpdir.join(handler_module_name)),
        new_name=handler_module_name,
        new_content_init_py=textwrap.dedent(
            """
            from inmanta.execute.proxy import DynamicProxy
            from inmanta.export import Exporter
            from inmanta.resources import Resource, resource

            @resource("__config__::Router", agent="agent.agentname", id_attribute="full_id")
            class Router(Resource):
                fields = ("network_id", "router_id", "full_id",)

                def get_network_id(exporter: Exporter, obj: DynamicProxy) -> int:
                    return obj.network.id

                def get_router_id(exporter: Exporter, obj: DynamicProxy) -> int:
                    return obj.id

                def get_full_id(exporter: Exporter, obj: DynamicProxy) -> tuple[int, int]:
                    return (Router.get_network_id(exporter, obj), Router.get_router_id(exporter, obj))
            """.strip("\n")
        ),
    )

    def setup_model(base: str) -> None:
        """
        Add handlers for the base model and set up the snippetcompiler.
        """
        handlers_addition: str = f"""
            import {handler_module_name} as handler

            Router.agent [1] -- std::AgentConfig
            implementation bind_agent for Router:
                self.agent = std::AgentConfig[agentname="router_agent"]
            end
            implement Router using bind_agent
        """.strip()
        full_model: str = "\n".join((base, handlers_addition))
        snippetcompiler.setup_for_snippet(full_model, add_to_module_path=[str(tmpdir)])

    async def get_routers_by_network(version: int) -> abc.Mapping[int, abc.Set[int]]:
        resources: abc.Sequence[data.Resource] = await data.Resource.get_resources_for_version(env_id, version)
        routers_by_network: dict[int, set[int]] = defaultdict(set)
        for resource in resources:
            if resource.resource_type == model.ResourceType("__config__::Router"):
                routers_by_network[resource.attributes["network_id"]].add(resource.attributes["router_id"])
        return routers_by_network

    # initial export
    with open(os.path.join(snippets_dir, "basic_example_full.cf")) as fd:
        setup_model(fd.read())
    version, _ = await snippetcompiler.do_export_and_deploy()
    routers_by_network_full: abc.Mapping[int, abc.Set[int]] = await get_routers_by_network(version)
    assert len(routers_by_network_full) == 1000
    for network in routers_by_network_full:
        assert len(routers_by_network_full[network]) == 5

    # partial export: verify that only the example's set has changed
    with open(os.path.join(snippets_dir, "basic_example_partial.cf")) as fd:
        setup_model(fd.read())
    version, _ = await snippetcompiler.do_export_and_deploy(partial_compile=True)
    routers_by_network_partial: abc.Mapping[int, abc.Set[int]] = await get_routers_by_network(version)
    assert len(routers_by_network_partial) == 1000
    for network in routers_by_network_partial:
        assert len(routers_by_network_partial[network]) == (1 if network == 0 else 5)

    # full equivalent export: verify that it is indeed equivalent
    with open(os.path.join(snippets_dir, "basic_example_full_result.cf")) as fd:
        setup_model(fd.read())
    version, _ = await snippetcompiler.do_export_and_deploy()
    routers_by_network_equivalent: abc.Mapping[int, abc.Set[int]] = await get_routers_by_network(version)
    assert routers_by_network_equivalent == routers_by_network_partial
