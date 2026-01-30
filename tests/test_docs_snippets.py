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
import textwrap
import uuid
from collections import abc, defaultdict

import py
import pytest

import inmanta.types
from inmanta import compiler, data
from utils import v1_module_from_template, wait_until_deployment_finishes

DOCS_DIR: str = os.path.join(os.path.dirname(__file__), "..", "docs")


@pytest.mark.slowtest
async def test_docs_snippets_language_unknowns(snippetcompiler, capsys) -> None:
    """
    Test the code snippets that explain how unknowns flow through the model.
    """
    with open(os.path.join(os.path.dirname(__file__), "../docs/language/unknowns_simple.cf")) as fh:
        simple_model: str = fh.read()

    with open(os.path.join(os.path.dirname(__file__), "../docs/language/unknowns_multi.cf")) as fh:
        list_model: str = fh.read()

    # TODO: convert_unknowns typing port
    model = textwrap.dedent(f"""\
        {simple_model}

        import tests

        assert = true
        assert = std::is_unknown(a)
        assert = [1, 2, "?", 3] == tests::convert_unknowns(b, "?")
        assert = std::is_unknown(c)
        assert = d
        assert = std::is_unknown(e)
        assert = std::is_unknown(f)
        assert = std::is_unknown(g)
        assert = [1, 2, "?"] == [x == "?" ? x : x.n for x in tests::convert_unknowns(h, "?")]
        assert = [1, 2] == [x.n for x in i]
        """)
    snippetcompiler.setup_for_snippet(model, ministd=True)
    compiler.do_compile()

    out, _ = capsys.readouterr()
    assert out == textwrap.dedent("""\
        This message is printed twice! x=1
        This message is printed twice! x=2
        """)

    model = textwrap.dedent(f"""\
        {list_model}

        import tests

        assert = true
        assert = ["?", 3, "?", 5] == tests::convert_unknowns(a, "?")
        assert = std::is_unknown(b)
        assert = ["?", "?"] == tests::convert_unknowns(c, "?")
        assert = std::is_unknown(d)
        """)
    snippetcompiler.setup_for_snippet(model, ministd=True)
    compiler.do_compile()


@pytest.mark.slowtest
async def test_docs_snippet_partial_compile(
    tmpdir: py.path.local, snippetcompiler, modules_dir: str, server, client, environment: str
) -> None:
    """
    Verify that the partial compile example model is valid and is in fact equivalent to the full model it is compared to.
    """
    env_id: uuid.UUID = uuid.UUID(environment)
    snippets_dir: str = os.path.join(DOCS_DIR, "model_developers", "resource_sets")
    version: int

    handler_module_name: str = "host_handlers"
    v1_module_from_template(
        os.path.join(modules_dir, "minimalv1module"),
        str(tmpdir.join(handler_module_name)),
        new_name=handler_module_name,
        new_content_init_py=textwrap.dedent("""
            from inmanta.execute.proxy import DynamicProxy
            from inmanta.export import Exporter
            from inmanta.resources import Resource, resource

            @resource("__config__::Host", agent="agent.agentname", id_attribute="full_id")
            class Host(Resource):
                fields = ("network_id", "host_id", "full_id",)

                def get_network_id(exporter: Exporter, obj: DynamicProxy) -> int:
                    return obj.network.id

                def get_host_id(exporter: Exporter, obj: DynamicProxy) -> int:
                    return obj.id

                def get_full_id(exporter: Exporter, obj: DynamicProxy) -> tuple[int, str]:
                    return (Host.get_network_id(exporter, obj), Host.get_host_id(exporter, obj))
            """.strip("\n")),
    )

    def setup_model(base: str) -> None:
        """
        Add handlers for the base model and set up the snippetcompiler.
        """
        handlers_addition: str = f"""
            import {handler_module_name} as handler

            # add dummy agent attribute for the handler
            Host.agent [1] -- std::AgentConfig
            implementation bind_agent for Host:
                self.agent = std::AgentConfig[agentname="host_agent"]
            end
            implement Host using bind_agent
        """.strip()
        full_model: str = "\n".join((base, handlers_addition))
        snippetcompiler.setup_for_snippet(full_model, add_to_module_path=[str(tmpdir)], autostd=True)

    async def get_hosts_by_network(version: int) -> abc.Mapping[int, abc.Set[int]]:
        resources: abc.Sequence[data.Resource] = await data.Resource.get_resources_for_version(env_id, version)
        hosts_by_network: dict[int, set[int]] = defaultdict(set)
        for resource in resources:
            if resource.resource_type == inmanta.types.ResourceType("__config__::Host"):
                hosts_by_network[resource.attributes["network_id"]].add(resource.attributes["host_id"])
        return hosts_by_network

    # initial export
    with open(os.path.join(snippets_dir, "basic_example_full.cf")) as fd:
        setup_model(fd.read())
    version, _ = await snippetcompiler.do_export_and_deploy()
    hosts_by_network_full: abc.Mapping[int, abc.Set[int]] = await get_hosts_by_network(version)
    assert len(hosts_by_network_full) == 1000
    for network in hosts_by_network_full:
        assert len(hosts_by_network_full[network]) == 5

    # partial export: verify that only the example's set has changed
    with open(os.path.join(snippets_dir, "basic_example_partial.cf")) as fd:
        setup_model(fd.read())
    version, _ = await snippetcompiler.do_export_and_deploy(partial_compile=True)
    hosts_by_network_partial: abc.Mapping[int, abc.Set[int]] = await get_hosts_by_network(version)
    assert len(hosts_by_network_partial) == 1000
    for network in hosts_by_network_partial:
        assert len(hosts_by_network_partial[network]) == (1 if network == 0 else 5)

    # full equivalent export: verify that it is indeed equivalent
    with open(os.path.join(snippets_dir, "basic_example_full_result.cf")) as fd:
        setup_model(fd.read())
    version, _ = await snippetcompiler.do_export_and_deploy()
    hosts_by_network_equivalent: abc.Mapping[int, abc.Set[int]] = await get_hosts_by_network(version)
    assert hosts_by_network_equivalent == hosts_by_network_partial


@pytest.mark.slowtest
async def test_docs_snippets_unmanaged_resources_basic(
    tmpdir: py.path.local, snippetcompiler, modules_dir: str, server, client, environment: str, agent, clienthelper
) -> None:
    """
    Test the basic_example code snippets used in the documentation to explain the usage of unmanaged_resources.
    """
    result = await client.set_setting(environment, data.AUTO_DEPLOY, True)
    assert result.code == 200

    cf_file_path = os.path.join(os.path.dirname(__file__), "../docs/model_developers/unmanaged_resources/basic_example.cf")
    with open(cf_file_path) as fh:
        cf_file_content = fh.read()

    attributes_discovered_resources = [{"host": "localhost", "interface_name": "eth0", "ip_address": "10.10.10.10"}]
    init_py_path = os.path.join(
        os.path.dirname(__file__), "../docs/model_developers/unmanaged_resources/basic_example_handler.py"
    )
    with open(init_py_path) as fh:
        init_py_content = fh.read()
    init_py_content = init_py_content.replace("raise NotImplementedError()", f"return {attributes_discovered_resources}")

    module_name = "my_module"
    v1_module_from_template(
        source_dir=os.path.join(modules_dir, "minimalv1module"),
        dest_dir=str(tmpdir.join(module_name)),
        new_name=module_name,
        new_content_init_cf=cf_file_content,
        new_content_init_py=init_py_content,
    )

    model = textwrap.dedent("""
        import my_module

        host = std::Host(ip="127.0.0.1", name="agent1", os=std::linux)
        my_module::InterfaceDiscovery(host=host)
        """)
    snippetcompiler.setup_for_snippet(model, add_to_module_path=[str(tmpdir)], use_pip_config_file=True, autostd=True)
    version, _ = await snippetcompiler.do_export_and_deploy()

    await clienthelper.wait_for_released(version)
    await wait_until_deployment_finishes(client, environment, version=version)

    result = await client.discovered_resources_get_batch(tid=environment)
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert result.result["data"][0]["discovered_resource_id"] == "my_module::Interface[localhost,interface_name=eth0]"
    assert result.result["data"][0]["values"] == attributes_discovered_resources[0]


@pytest.mark.slowtest
async def test_docs_snippets_unmanaged_resources_shared_attributes(
    tmpdir: py.path.local, snippetcompiler, modules_dir: str, server, client, environment: str, agent, clienthelper
) -> None:
    """
    Test the shared_attributes_example code snippets used in the documentation to explain the usage of unmanaged_resources.
    """
    result = await client.set_setting(environment, data.AUTO_DEPLOY, True)
    assert result.code == 200

    cf_file_path = os.path.join(
        os.path.dirname(__file__), "../docs/model_developers/unmanaged_resources/shared_attributes_example.cf"
    )
    with open(cf_file_path) as fh:
        cf_file_content = fh.read()

    attributes_discovered_resources = [
        {"host": "localhost", "interface_name": "eth0", "ip_address": "10.10.10.10"},
        {"host": "localhost", "interface_name": "eth1", "ip_address": "20.20.20.20"},
    ]
    init_py_path = os.path.join(
        os.path.dirname(__file__), "../docs/model_developers/unmanaged_resources/shared_attributes_example_handler.py"
    )
    with open(init_py_path) as fh:
        init_py_content = fh.read()
    init_py_content = init_py_content.replace("raise NotImplementedError()", "pass", 6)
    init_py_content = init_py_content.replace("raise NotImplementedError()", f"return {attributes_discovered_resources}")

    module_name = "my_module"
    v1_module_from_template(
        source_dir=os.path.join(modules_dir, "minimalv1module"),
        dest_dir=str(tmpdir.join(module_name)),
        new_name=module_name,
        new_content_init_cf=cf_file_content,
        new_content_init_py=init_py_content,
    )

    model = textwrap.dedent("""
        import my_module

        host = std::Host(ip="127.0.0.1", name="agent1", os=std::linux)
        credentials = my_module::Credentials(username="test", password="test")
        my_module::InterfaceDiscovery(name_filter="eth[1-9]", host=host, credentials=credentials)
        """)
    snippetcompiler.setup_for_snippet(model, add_to_module_path=[str(tmpdir)], use_pip_config_file=True, autostd=True)
    version, _ = await snippetcompiler.do_export_and_deploy()

    await clienthelper.wait_for_released(version)

    await wait_until_deployment_finishes(client, environment, version=version)

    result = await client.discovered_resources_get_batch(tid=environment)
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert result.result["data"][0]["discovered_resource_id"] == "my_module::Interface[localhost,interface_name=eth1]"
    assert result.result["data"][0]["values"] == attributes_discovered_resources[1]
