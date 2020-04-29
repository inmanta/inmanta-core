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
import pytest

from inmanta import config, const
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
    print(_version, json_value, status, model)


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
