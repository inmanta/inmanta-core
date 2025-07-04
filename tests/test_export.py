"""
Copyright 2017 Inmanta

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

import json
import logging
import os
from collections.abc import Mapping
from typing import Optional

import pytest

import inmanta.resources
from inmanta import config, const, module
from inmanta.ast import CompilerException, ExternalException, RuntimeException
from inmanta.const import ResourceState
from inmanta.data import Environment, Resource
from inmanta.export import DependencyCycleException
from inmanta.module import InmantaModuleRequirement
from inmanta.server import SLICE_RESOURCE
from inmanta.server.server import Server
from utils import LogSequence


async def assert_resource_set_assignment(environment, assignment: dict[str, Optional[str]]) -> None:
    """
    Verify whether the resources on the server are assigned to the resource sets given via the assignment argument.

    :param environment: environment uuid
    :param assignment: Map the value of name attribute of resource Res to the resource set that resource is expected to
                       belong to.
    """
    resources = await Resource.get_resources_in_latest_version(environment=environment)
    assert len(resources) == len(assignment)
    actual_assignment = {r.attributes["key"]: r.resource_set for r in resources}
    assert actual_assignment == assignment


def test_attribute_mapping_export(snippetcompiler):
    """
    Verify Python-defined attribute mapping between model resource and exported resource.
    """
    snippetcompiler.setup_for_snippet(
        """\
        import exp

        exp::Test(name="a", agent="x")
        exp::Test(name="b", agent="x", send_event=false, receive_events=true)
        exp::Test(name="c", agent="x", send_event=true, receive_events=false)
        """,
        autostd=True,
        project_requires=[module.InmantaModuleRequirement.parse("std>=6.1")],
    )

    _version, json_value = snippetcompiler.do_export()

    assert len(json_value) == 3
    resources: Mapping[str, Mapping[str, object]] = {
        resource.name: {
            # base resource mapping
            const.RESOURCE_ATTRIBUTE_SEND_EVENTS: getattr(resource, const.RESOURCE_ATTRIBUTE_SEND_EVENTS),
            const.RESOURCE_ATTRIBUTE_RECEIVE_EVENTS: getattr(resource, const.RESOURCE_ATTRIBUTE_RECEIVE_EVENTS),
            # custom mapping
            "mapped": resource.mapped,
        }
        for resource in json_value.values()
    }
    assert resources == {
        "a": {
            "mapped": "mapped_value_a",
            const.RESOURCE_ATTRIBUTE_SEND_EVENTS: True,
            const.RESOURCE_ATTRIBUTE_RECEIVE_EVENTS: True,
        },
        "b": {
            "mapped": "mapped_value_b",
            const.RESOURCE_ATTRIBUTE_SEND_EVENTS: False,
            const.RESOURCE_ATTRIBUTE_RECEIVE_EVENTS: True,
        },
        "c": {
            "mapped": "mapped_value_c",
            const.RESOURCE_ATTRIBUTE_SEND_EVENTS: True,
            const.RESOURCE_ATTRIBUTE_RECEIVE_EVENTS: False,
        },
    }


def test_id_mapping_export(snippetcompiler):
    """
    Verify id mapping for a virtual id value, i.e. not a field of the resource.
    """
    snippetcompiler.setup_for_snippet(
        """import exp

        exp::Test(name="a", agent="b")
        """,
        autostd=True,
    )

    _version, json_value = snippetcompiler.do_export()

    assert len(json_value) == 1
    resource = list(json_value.values())[0]
    assert not hasattr(resource, resource.id.attribute)
    assert resource.id.attribute_value == "test_value_a"


def test_unknown_agent(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """import exp
        import tests

        exp::Test(name="a", agent=tests::unknown())
        """,
        autostd=True,
    )
    _version, json_value = snippetcompiler.do_export()

    assert len(json_value) == 0


def test_unknown_attribute_value(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """import exp
        import tests

        exp::Test(name=tests::unknown(), agent="b")
        """,
        autostd=True,
    )
    _version, json_value = snippetcompiler.do_export()

    assert len(json_value) == 0


def test_ignore_resource(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """import exp
        import tests

        exp::Test(name="a", agent="b", managed=false)
        """,
        autostd=True,
    )
    _version, json_value = snippetcompiler.do_export()

    assert len(json_value) == 0


def test_ignore_resource_requires(snippetcompiler, caplog):
    snippetcompiler.setup_for_snippet(
        """import exp
        import tests

        a = exp::Test(name="a", agent="aa", managed=false)
        b = exp::Test(name="b", agent="aa", requires=a)
        c = exp::Test(name="c", agent="aa", requires=b)
        """,
        autostd=True,
    )
    _version, json_value = snippetcompiler.do_export()
    assert len(json_value) == 2
    assert_count = 0
    for resource_id, resource in json_value.items():
        if resource_id.attribute_value == "test_value_b":
            assert len(resource.requires) == 0
            assert_count += 1

        elif resource_id.attribute_value == "test_value_c":
            assert len(resource.requires) == 1
            assert_count += 1

    warning = [
        x
        for x in caplog.records
        if x.msg == "The resource %s had requirements before flattening, but not after flattening."
        " Initial set was %s. Perhaps provides relation is not wired through correctly?"
    ]
    assert len(warning) == 0
    assert assert_count == 2


def test_unknown_in_id_requires(snippetcompiler, caplog):
    """
    Test to validate that resources that have an unknown in their ID attributes, are removed from requires
    """
    snippetcompiler.setup_for_snippet(
        """import exp
        import tests

        a = exp::Test(name=tests::unknown(), agent="aa")
        b = exp::Test(name="b", agent="aa", requires=a)
        c = exp::Test(name="c", agent="aa", requires=b)
        """,
        autostd=True,
    )
    _version, json_value = snippetcompiler.do_export()

    assert len(json_value) == 2
    assert_count = 0
    for resource_id, resource in json_value.items():
        if resource_id.attribute_value == "test_value_b":
            assert len(resource.requires) == 0
            assert_count += 1

        elif resource_id.attribute_value == "test_value_c":
            assert len(resource.requires) == 1
            assert_count += 1

    warning = [
        x
        for x in caplog.records
        if x.msg == "The resource %s had requirements before flattening, but not after flattening."
        " Initial set was %s. Perhaps provides relation is not wired through correctly?"
    ]
    assert len(warning) == 0
    assert assert_count == 2


def test_unknown_in_attribute_requires(snippetcompiler, caplog):
    """
    Test to validate that resources that have an unknown in their ID attributes, are removed from requires
    """
    snippetcompiler.setup_for_snippet(
        """import exp
        import tests

        a = exp::Test(name="a", agent="aa", field1=tests::unknown())
        b = exp::Test(name="b", agent="aa", requires=a)
        c = exp::Test(name="c", agent="aa", requires=b)
        """,
        autostd=True,
    )
    _version, json_value, status = snippetcompiler.do_export(include_status=True)

    assert len(json_value) == 3
    assert len([x for x in status.values() if x == const.ResourceState.available]) == 2
    assert len([x for x in status.values() if x == const.ResourceState.undefined]) == 1

    warning = [
        x
        for x in caplog.records
        if x.msg == "The resource %s had requirements before flattening, but not after flattening."
        " Initial set was %s. Perhaps provides relation is not wired through correctly?"
    ]
    assert len(warning) == 0


async def test_empty_server_export(snippetcompiler, server, client, environment):
    snippetcompiler.setup_for_snippet(
        """
            h = std::Host(name="test", os=std::linux)
        """,
        extra_index_url=["example.inmanta.com/index"],
        autostd=True,
    )
    await snippetcompiler.do_export_and_deploy()

    response = await client.list_versions(tid=environment)
    assert response.code == 200
    assert len(response.result["versions"]) == 1
    assert response.result["versions"][0]["pip_config"] == {
        "extra-index-url": ["example.inmanta.com/index"],
        "index-url": None,
        "pre": None,
        "use-system-config": False,
    }


async def test_server_export(snippetcompiler, server: Server, client, environment):
    snippetcompiler.setup_for_snippet(
        """
            import std::testing
            f = std::testing::NullResource(name="test")
        """,
        autostd=True,
    )
    await snippetcompiler.do_export_and_deploy()

    result = await client.list_versions(tid=environment)
    assert result.code == 200
    assert len(result.result["versions"]) == 1
    assert result.result["versions"][0]["total"] == 1

    version = result.result["versions"][0]["version"]
    result = await client.get_version(tid=environment, id=result.result["versions"][0]["version"])
    assert result.code == 200

    for res in result.result["resources"]:
        res["attributes"]["id"] = res["id"]
        resource = inmanta.resources.Resource.deserialize(res["attributes"])
        assert resource.version == resource.id.version == version

    resources = await server.get_slice(SLICE_RESOURCE).get_resources_in_latest_version(
        environment=await Environment.get_by_id(environment)
    )

    assert resources[0].attributes["version"] == version


async def test_dict_export_server(snippetcompiler, server, client, environment):
    config.Config.set("config", "environment", environment)
    snippetcompiler.setup_for_snippet(
        """
import exp

a = exp::Test2(mydict={"a":"b"}, mylist=["a","b"])
""",
        autostd=True,
    )

    await snippetcompiler.do_export_and_deploy()

    result = await client.list_versions(tid=environment)
    assert result.code == 200
    assert len(result.result["versions"]) == 1
    assert result.result["versions"][0]["total"] == 1


async def test_old_compiler(server, client, environment):
    result = await client.put_version(
        tid=environment,
        version=123456,
        resources=[],
        unknowns=[],
        version_info={},
        module_version_info={},
    )
    assert result.code == 400


def test_dict_export(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import exp

a = exp::Test2(mydict={"a":"b"}, mylist=["a","b"])
""",
        autostd=True,
    )
    _version, json_value, status = snippetcompiler.do_export(include_status=True)

    assert len(json_value) == 1


def test_export_null_in_collection(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import exp

a = exp::Test2(mydict={"a": null}, mylist=["a",null])
""",
        autostd=True,
    )
    _version, json_value, status = snippetcompiler.do_export(include_status=True)

    assert len(json_value) == 1
    json_dict = snippetcompiler.get_exported_json()
    resource = json_dict[0]
    assert resource["mylist"] == ["a", None]
    assert resource["mydict"] == {"a": None}


def test_export_unknown_in_collection(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import exp
import tests

a = exp::Test2(mydict={"a": tests::unknown()}, mylist=["a"])
b = exp::Test2(name="idb", mydict={"a": "b"}, mylist=["a", tests::unknown()])
""",
        autostd=True,
    )
    _version, json_value, status = snippetcompiler.do_export(include_status=True)

    assert len(json_value) == 2
    assert status["exp::Test2[agenta,name=ida]"] == ResourceState.undefined
    assert status["exp::Test2[agenta,name=idb]"] == ResourceState.undefined


def test_1934_cycle_in_dep_mgmr(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import exp

a = exp::RequiresTest()
b = exp::RequiresTest(name="idb")
a.requires += b
""",
        autostd=True,
    )
    with pytest.raises(DependencyCycleException):
        snippetcompiler.do_export()


def test_bad_value_in_dep_mgmr(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import exp

a = exp::RequiresTest(do_break=1)
""",
        autostd=True,
    )
    with pytest.raises(Exception, match="Invalid id for resource xyz"):
        snippetcompiler.do_export()


def test_bad_value_in_dep_mgmr_2(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import exp

a = exp::RequiresTest(do_break=2)
""",
        autostd=True,
    )
    with pytest.raises(
        Exception,
        match="A dependency manager inserted the object <object object at .*> of type <class 'object'> "
        "into a requires relation. However, only string, Resource or Id are allowable types",
    ):
        snippetcompiler.do_export()


def test_bad_value_in_dep_mgmr_3(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import exp

a = exp::RequiresTest(do_break=3)
""",
        autostd=True,
    )
    with pytest.raises(
        Exception,
        match="A dependency manager inserted a resource id without version this is not allowed aa::Bbbb\\[agent,name=agent\\]",
    ):
        snippetcompiler.do_export()


def test_2121_wrapped_proxy_serialize(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import exp

dct = {"a": 1, "b": 2}

x = exp::WrappedProxyTest(
    name = "my_wrapped_proxy_test",
    agent = "my_agent",
    my_list = [1, 2, 3],
    my_dict = {
        "dct": dct,
    }
)
        """,
        autostd=True,
    )
    snippetcompiler.do_export()
    tmp_file: str = os.path.join(snippetcompiler.project_dir, "dump.json")
    with open(tmp_file) as f:
        export: dict = json.loads(f.read())
        my_dict: dict = {"dct": {"a": 1, "b": 2}}
        assert len(export) == 1
        print(export[0])
        assert export[0]["wrapped_proxies"] == {
            "my_list": [1, 2, 3],
            "my_dict": my_dict,
            "deep_dict": {"multi_level": my_dict},
        }


def test_2121_wrapped_self_serialize(snippetcompiler):
    """
    Make sure DynamicProxies representing an entity are not serialized.
    """
    snippetcompiler.setup_for_snippet(
        """
import exp

exp::WrappedSelfTest(
    name = "my_wrapped_self_test",
    agent = "my_agent",
)
        """,
        autostd=True,
    )
    with pytest.raises(ExternalException) as e:
        snippetcompiler.do_export()
    assert "not JSON serializable" in e.value.format_trace()


def test_3787_key_error_export(snippetcompiler):
    """
    Check the error message of an export with a KeyError
    The Key error happens in get_real_name() of class Test3
    """
    snippetcompiler.setup_for_snippet(
        """
import exp

exp::Test3(
    name="tom",
    names={
        "bob": "alice",
        "alice": "bob",
    },
    agent=std::AgentConfig(
        autostart=true,
        agentname="bob",
        uri="local:",
    ),
)
        """,
        autostd=True,
    )
    with pytest.raises(ExternalException) as e:
        snippetcompiler.do_export()
    assert (
        e.value.format_trace()
        == "Failed to get attribute 'real_name' for export on 'exp::Test3'\ncaused by:\nKeyError: 'tom'\n"
    )


@pytest.mark.parametrize(
    "soft_delete",
    [True, False],
)
async def test_resource_set(snippetcompiler, modules_dir: str, environment, client, agent, soft_delete: bool) -> None:
    """
    Test that resource sets are exported correctly, when a full compile or an incremental compile is done.
    """

    async def export_model(
        model: str,
        partial_compile: bool,
        resource_sets_to_remove: Optional[list[str]] = None,
    ) -> None:
        snippetcompiler.setup_for_snippet(
            model,
            extra_index_url=["example.inmanta.com/index"],
            autostd=True,
        )
        await snippetcompiler.do_export_and_deploy(
            partial_compile=partial_compile,
            resource_sets_to_remove=resource_sets_to_remove,
            soft_delete=soft_delete,
        )

    # Full compile
    await export_model(
        model="""
import test_resources

a = test_resources::Resource(value="A", agent="A", key="the_resource_a")
b = test_resources::Resource(value="A", agent="A", key="the_resource_b")
c = test_resources::Resource(value="A", agent="A", key="the_resource_c")
d = test_resources::Resource(value="A", agent="A", key="the_resource_d")
e = test_resources::Resource(value="A", agent="A", key="the_resource_e")
y = test_resources::Resource(value="A", agent="A", key="the_resource_y")
z = test_resources::Resource(value="A", agent="A", key="the_resource_z")
std::ResourceSet(name="resource_set_1", resources=[a,c])
std::ResourceSet(name="resource_set_2", resources=[b])
std::ResourceSet(name="resource_set_3", resources=[d, e])
        """,
        partial_compile=False,
    )
    await assert_resource_set_assignment(
        environment,
        assignment={
            "the_resource_a": "resource_set_1",
            "the_resource_b": "resource_set_2",
            "the_resource_c": "resource_set_1",
            "the_resource_d": "resource_set_3",
            "the_resource_e": "resource_set_3",
            "the_resource_y": None,
            "the_resource_z": None,
        },
    )

    # Partial compile
    await export_model(
        model="""
    import test_resources

    a = test_resources::Resource(value="A", agent="A", key="the_resource_a")
    c2 = test_resources::Resource(value="A", agent="A", key="the_resource_c2")
    f = test_resources::Resource(value="A", agent="A", key="the_resource_f")
    # y is a shared resource, identical to the one in previous compile
    y = test_resources::Resource(value="A", agent="A", key="the_resource_y")
    # z is a shared resource not present in this model
    std::ResourceSet(name="resource_set_1", resources=[a,c2])
    std::ResourceSet(name="resource_set_4", resources=[f])
            """,
        partial_compile=True,
        resource_sets_to_remove=["resource_set_2"],
    )
    await assert_resource_set_assignment(
        environment,
        assignment={
            "the_resource_a": "resource_set_1",
            "the_resource_c2": "resource_set_1",
            "the_resource_d": "resource_set_3",
            "the_resource_e": "resource_set_3",
            "the_resource_f": "resource_set_4",
            "the_resource_y": None,
            "the_resource_z": None,
        },
    )

    # Test soft_delete option

    model = """
        import test_resources

        g = test_resources::Resource(value="A", agent="A", key="the_resource_g")
        std::ResourceSet(name="resource_set_5", resources=[g])

        """
    if not soft_delete:
        with pytest.raises(
            Exception,
            match=(
                "Invalid request: Following resource sets are present in the removed resource"
                " sets and in the resources that are exported: {'resource_set_5'}"
            ),
        ):
            await export_model(
                model=model,
                partial_compile=True,
                resource_sets_to_remove=["resource_set_5"],
            )

    else:
        await export_model(
            model=model,
            partial_compile=True,
            resource_sets_to_remove=["resource_set_5"],
        )
        await assert_resource_set_assignment(
            environment,
            assignment={
                "the_resource_a": "resource_set_1",
                "the_resource_c2": "resource_set_1",
                "the_resource_d": "resource_set_3",
                "the_resource_e": "resource_set_3",
                "the_resource_f": "resource_set_4",
                "the_resource_g": "resource_set_5",  # Check it didn't get removed
                "the_resource_y": None,
                "the_resource_z": None,
            },
        )

    response = await client.list_versions(tid=environment)
    assert response.code == 200

    # One of the 3 partial compiles is expected to fail when soft_delete is true:
    assert len(response.result["versions"]) == 2 + soft_delete
    last_version_nr = 0
    expected_pip_config = {
        "extra-index-url": ["example.inmanta.com/index"],
        "index-url": None,
        "pre": None,
        "use-system-config": False,
    }
    for version in response.result["versions"]:
        assert version["pip_config"] == expected_pip_config, f"failed for version: {version['version']}"
        last_version_nr = version["version"]

    # abusing this setup to test get_pip_config
    response = await agent._client.get_pip_config(tid=environment, version=last_version_nr)
    assert response.code == 200
    assert response.result["data"] == expected_pip_config

    response = await agent._client.get_pip_config(tid=environment, version=500)
    assert response.code == 404


async def test_resource_in_multiple_resource_sets(snippetcompiler, environment) -> None:
    """
    test that an error is raised if a resource is in multiple
    resource_sets
    """
    model = """
import test_resources

a = test_resources::Resource(value="A", agent="A", key="the_resource_a")
std::ResourceSet(name="resource_set_1", resources=[a])
std::ResourceSet(name="resource_set_2", resources=[a])
"""

    snippetcompiler.setup_for_snippet(
        model,
        autostd=True,
    )
    with pytest.raises(CompilerException) as e:
        await snippetcompiler.do_export_and_deploy()
    assert str(e.value).startswith(
        "resource 'test_resources::Resource[A,key=the_resource_a]' can not be part of multiple " "ResourceSets:"
    )


async def test_resource_not_exported(snippetcompiler, caplog, environment) -> None:
    """
    test that a warning is logged if a resource that is not exported is in a resource_set
    """
    snippetcompiler.setup_for_snippet(
        """
std::ResourceSet(name="resource_set_1", resources=[std::Resource()])
implement std::Resource using std::none
""",
        autostd=True,
    )
    caplog.clear()
    caplog.set_level(logging.WARNING)
    await snippetcompiler.do_export_and_deploy()
    cwd = snippetcompiler.project_dir

    msg: str = (
        f"resource std::Resource (instantiated at {cwd}/main.cf:2) is part of ResourceSet resource_set_1 "
        f"but will not be exported."
    )

    log_sequence = LogSequence(caplog)
    log_sequence.contains("inmanta.export", logging.WARNING, msg)


async def test_empty_resource_set_removal(snippetcompiler, environment) -> None:
    """
    When a partial compile is ran, the exporter should trigger a deletion of each ResourceSet, defined in the partial model,
    that doesn't have any resources associated
    """

    async def export_model(
        model: str,
        partial_compile: bool,
        resource_sets_to_remove: Optional[list[str]] = None,
    ) -> None:
        snippetcompiler.setup_for_snippet(model, autostd=True)
        await snippetcompiler.do_export_and_deploy(
            partial_compile=partial_compile,
            resource_sets_to_remove=resource_sets_to_remove,
        )

    # Full compile
    await export_model(
        model="""
import test_resources

a = test_resources::Resource(value="A", agent="A", key="the_resource_a")
b = test_resources::Resource(value="A", agent="A", key="the_resource_b")
c = test_resources::Resource(value="A", agent="A", key="the_resource_c")
d = test_resources::Resource(value="A", agent="A", key="the_resource_d")
e = test_resources::Resource(value="A", agent="A", key="the_resource_e")
z = test_resources::Resource(value="A", agent="A", key="the_resource_z")
std::ResourceSet(name="resource_set_1", resources=[a,c])
std::ResourceSet(name="resource_set_2", resources=[b])
std::ResourceSet(name="resource_set_3", resources=[d, e])
        """,
        partial_compile=False,
    )
    await assert_resource_set_assignment(
        environment,
        assignment={
            "the_resource_a": "resource_set_1",
            "the_resource_b": "resource_set_2",
            "the_resource_c": "resource_set_1",
            "the_resource_d": "resource_set_3",
            "the_resource_e": "resource_set_3",
            "the_resource_z": None,
        },
    )

    # Partial compile
    await export_model(
        model="""
    import test_resources


    a = test_resources::Resource(value="A", agent="A", key="the_resource_a")
    c2 = test_resources::Resource(value="A", agent="A", key="the_resource_c2")
    f = test_resources::Resource(value="A", agent="A", key="the_resource_f")
    std::ResourceSet(name="resource_set_1", resources=[a,c2])
    std::ResourceSet(name="resource_set_4", resources=[f])
    std::ResourceSet(name="resource_set_3", resources=[])
            """,
        partial_compile=True,
        resource_sets_to_remove=["resource_set_2"],
    )
    await assert_resource_set_assignment(
        environment,
        assignment={
            "the_resource_a": "resource_set_1",
            "the_resource_c2": "resource_set_1",
            "the_resource_f": "resource_set_4",
            "the_resource_z": None,
        },
    )


def test_attribute_value_of_id_has_str_type(snippetcompiler):
    """
    Verify that the id.attribute_value field of resources emitted by the exporter have the type str.
    Even if the type in the model is different.
    """
    snippetcompiler.setup_for_snippet(
        """
        import testmodule_integer_id

        testmodule_integer_id::Test(
            id_attr=123,
            agent="internal",
        )
        """,
        autostd=True,
    )
    version, resource_dct = snippetcompiler.do_export()
    resources = list(resource_dct.values())
    assert len(resources) == 1
    id_attribute_value = resources[0].id.attribute_value
    assert isinstance(id_attribute_value, str)
    assert id_attribute_value == "123"


async def test_export_duplicate(resource_container, snippetcompiler):
    """
    The exported should provide a compilation error when a resource is defined twice in a model
    """
    snippetcompiler.setup_for_snippet(
        """
        import test

        test::Resource(key="test", value="foo")
        test::Resource(key="test", value="bar")
    """,
        autostd=True,
    )

    with pytest.raises(CompilerException) as exc:
        snippetcompiler.do_export()

    assert "exists more than once in the configuration model" in str(exc.value)


async def test_resource_inherits_from_decorator(snippetcompiler, local_module_package_index):
    """
    Verify that a clear error message is shown to the user if a resource inherits
    from the resource decorator instead of the Resource class.
    """
    requirement = InmantaModuleRequirement.parse("invalid_resource_def")
    snippetcompiler.setup_for_snippet(
        "import invalid_resource_def",
        install_project=True,
        index_url=local_module_package_index,
        python_requires=[requirement.get_python_package_requirement()],
        autostd=False,
    )

    with pytest.raises(RuntimeException) as exc:
        snippetcompiler.do_export()

    assert (
        "Resource inmanta_plugins.invalid_resource_def.Test is inheriting from the inmanta.resources.resource decorator."
        " Did you intend to inherit from inmanta.resources.Resource instead?"
    ) in str(exc.value)
