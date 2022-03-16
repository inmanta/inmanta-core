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
import os

import pytest

from inmanta import config, const
from inmanta.ast import ExternalException
from inmanta.const import ResourceState
from inmanta.export import DependencyCycleException


def test_id_mapping_export(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """import exp

        exp::Test(name="a", agent="b")
        """
    )

    _version, json_value = snippetcompiler.do_export()

    assert len(json_value) == 1
    resource = list(json_value.values())[0]
    assert resource.id.attribute_value == "test_value_a"


def test_unknown_agent(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """import exp
        import tests

        exp::Test(name="a", agent=tests::unknown())
        """
    )
    _version, json_value = snippetcompiler.do_export()

    assert len(json_value) == 0


def test_unknown_attribute_value(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """import exp
        import tests

        exp::Test(name=tests::unknown(), agent="b")
        """
    )
    _version, json_value = snippetcompiler.do_export()

    assert len(json_value) == 0


def test_ignore_resource(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """import exp
        import tests

        exp::Test(name="a", agent="b", managed=false)
        """
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
        """
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
        """
    )
    config.Config.set("unknown_handler", "default", "prune-resource")
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
        """
    )
    config.Config.set("unknown_handler", "default", "prune-resource")
    _version, json_value, status, model = snippetcompiler.do_export(include_status=True)

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


@pytest.mark.asyncio
async def test_empty_server_export(snippetcompiler, server, client, environment):
    snippetcompiler.setup_for_snippet(
        """
            h = std::Host(name="test", os=std::linux)
        """
    )
    await snippetcompiler.do_export_and_deploy()

    response = await client.list_versions(tid=environment)
    assert response.code == 200
    assert len(response.result["versions"]) == 1


@pytest.mark.asyncio
async def test_server_export(snippetcompiler, server, client, environment):
    snippetcompiler.setup_for_snippet(
        """
            h = std::Host(name="test", os=std::linux)
            f = std::ConfigFile(host=h, path="/etc/motd", content="test")
        """
    )
    await snippetcompiler.do_export_and_deploy()

    result = await client.list_versions(tid=environment)
    assert result.code == 200
    assert len(result.result["versions"]) == 1
    assert result.result["versions"][0]["total"] == 1


@pytest.mark.asyncio
async def test_dict_export_server(snippetcompiler, server, client, environment):
    config.Config.set("config", "environment", environment)
    snippetcompiler.setup_for_snippet(
        """
import exp

a = exp::Test2(mydict={"a":"b"}, mylist=["a","b"])
"""
    )

    await snippetcompiler.do_export_and_deploy()

    result = await client.list_versions(tid=environment)
    assert result.code == 200
    assert len(result.result["versions"]) == 1
    assert result.result["versions"][0]["total"] == 1


@pytest.mark.asyncio
async def test_old_compiler(server, client, environment):
    result = await client.put_version(tid=environment, version=123456, resources=[], unknowns=[], version_info={})
    assert result.code == 400


def test_dict_export(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import exp

a = exp::Test2(mydict={"a":"b"}, mylist=["a","b"])
"""
    )
    _version, json_value, status, model = snippetcompiler.do_export(include_status=True)

    assert len(json_value) == 1


def test_export_null_in_collection(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import exp

a = exp::Test2(mydict={"a": null}, mylist=["a",null])
"""
    )
    _version, json_value, status, model = snippetcompiler.do_export(include_status=True)

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
"""
    )
    _version, json_value, status, model = snippetcompiler.do_export(include_status=True)

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
"""
    )
    with pytest.raises(DependencyCycleException):
        snippetcompiler.do_export()


def test_bad_value_in_dep_mgmr(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import exp

a = exp::RequiresTest(do_break=1)
"""
    )
    with pytest.raises(Exception, match="Invalid id for resource xyz"):
        snippetcompiler.do_export()


def test_bad_value_in_dep_mgmr_2(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import exp

a = exp::RequiresTest(do_break=2)
"""
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
"""
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
    )
    snippetcompiler.do_export()
    tmp_file: str = os.path.join(snippetcompiler.project_dir, "dump.json")
    with open(tmp_file, "r") as f:
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
        """
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
        """
    )
    with pytest.raises(ExternalException) as e:
        snippetcompiler.do_export()
    assert (
        e.value.format_trace()
        == "Failed to get attribute 'real_name' for export on 'exp::Test3'\ncaused by:\nKeyError: 'tom'\n"
    )
