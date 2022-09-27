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
import shutil
from typing import Dict, List, Optional

import pytest

from inmanta import config, const
from inmanta.ast import CompilerException, ExternalException
from inmanta.const import ResourceState
from inmanta.data import Resource
from inmanta.export import DependencyCycleException
from utils import LogSequence, v1_module_from_template


async def assert_resource_set_assignment(environment, assignment: Dict[str, Optional[str]]) -> None:
    """
    Verify whether the resources on the server are assignment to the resource sets given via the assignment argument.

    :param environment
    :param assignment: Map the value of name attribute of resource Res to the resource set that resource is expected to
                       belong to.
    """
    resources = await Resource.get_resources_in_latest_version(environment=environment)
    assert len(resources) == len(assignment)
    actual_assignment = {r.attributes["name"]: r.resource_set for r in resources}
    assert actual_assignment == assignment


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
        """
    )
    await snippetcompiler.do_export_and_deploy()

    response = await client.list_versions(tid=environment)
    assert response.code == 200
    assert len(response.result["versions"]) == 1


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
    _version, json_value, status = snippetcompiler.do_export(include_status=True)

    assert len(json_value) == 1


def test_export_null_in_collection(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import exp

a = exp::Test2(mydict={"a": null}, mylist=["a",null])
"""
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
"""
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


async def test_resource_set(snippetcompiler, modules_dir: str, tmpdir, environment) -> None:
    """
    Test that resource sets are exported correctly, when a full compile or an incremental compile is done.
    """

    async def export_model(
        model: str,
        partial_compile: bool,
        resource_sets_to_remove: Optional[List[str]] = None,
    ) -> None:
        init_py = """
from inmanta.resources import (
    Resource,
    resource,
)
@resource("modulev1::Res", agent="name", id_attribute="name")
class Res(Resource):
    fields = ("name",)
"""

        module_name: str = "minimalv1module"
        module_path: str = str(tmpdir.join("modulev1"))
        if os.path.exists(module_path):
            shutil.rmtree(module_path)
        v1_module_from_template(
            os.path.join(modules_dir, module_name),
            module_path,
            new_content_init_cf=model,
            new_content_init_py=init_py,
            new_name="modulev1",
        )

        snippetcompiler.setup_for_snippet(
            """
    import modulev1
            """,
            add_to_module_path=[str(tmpdir)],
        )
        await snippetcompiler.do_export_and_deploy(
            partial_compile=partial_compile,
            resource_sets_to_remove=resource_sets_to_remove,
        )

    # Full compile
    await export_model(
        model="""
entity Res extends std::Resource:
    string name
end
implement Res using std::none
a = Res(name="the_resource_a")
b = Res(name="the_resource_b")
c = Res(name="the_resource_c")
d = Res(name="the_resource_d")
e = Res(name="the_resource_e")
y = Res(name="the_resource_y")
z = Res(name="the_resource_z")
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
    entity Res extends std::Resource:
        string name
    end
    implement Res using std::none
    a = Res(name="the_resource_a")
    c2 = Res(name="the_resource_c2")
    f = Res(name="the_resource_f")
    # y is a shared resource, identical to the one in previous compile
    y = Res(name="the_resource_y")
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


async def test_resource_in_multiple_resource_sets(snippetcompiler, modules_dir: str, tmpdir, environment) -> None:
    """
    test that an error is raised if a resource is in multiple
    resource_sets
    """
    init_cf = """
entity Res extends std::Resource:
    string name
end

implement Res using std::none

a = Res(name="the_resource_a")
std::ResourceSet(name="resource_set_1", resources=[a])
std::ResourceSet(name="resource_set_2", resources=[a])
"""
    init_py = """
from inmanta.resources import (
    Resource,
    resource,
)
@resource("modulev1::Res", agent="name", id_attribute="name")
class Res(Resource):
    fields = ("name",)
"""
    module_name: str = "minimalv1module"
    module_path: str = str(tmpdir.join("modulev1"))
    v1_module_from_template(
        os.path.join(modules_dir, module_name),
        module_path,
        new_content_init_cf=init_cf,
        new_content_init_py=init_py,
        new_name="modulev1",
    )
    snippetcompiler.setup_for_snippet(
        """
import modulev1
        """,
        add_to_module_path=[str(tmpdir)],
    )
    with pytest.raises(CompilerException) as e:
        await snippetcompiler.do_export_and_deploy()
    assert str(e.value).startswith(
        "resource 'modulev1::Res[the_resource_a,name=the_resource_a]' can not be part of multiple " "ResourceSets:"
    )


async def test_resource_not_exported(snippetcompiler, caplog, environment) -> None:
    """
    test that a warning is logged if a resource that is not exported is in a resource_set
    """
    snippetcompiler.setup_for_snippet(
        """
std::ResourceSet(name="resource_set_1", resources=[std::Resource()])
implement std::Resource using std::none
"""
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


async def test_empty_resource_set_removal(snippetcompiler, modules_dir: str, tmpdir, environment) -> None:
    """
    When a partial compile is ran, the exporter should trigger a deletion of each ResourceSet, defined in the partial model,
    that doesn't have any resources associated
    """

    async def export_model(
        model: str,
        partial_compile: bool,
        resource_sets_to_remove: Optional[List[str]] = None,
    ) -> None:
        init_py = """
from inmanta.resources import (
    Resource,
    resource,
)
@resource("modulev1::Res", agent="name", id_attribute="name")
class Res(Resource):
    fields = ("name",)
"""

        module_name: str = "minimalv1module"
        module_path: str = str(tmpdir.join("modulev1"))
        if os.path.exists(module_path):
            shutil.rmtree(module_path)
        v1_module_from_template(
            os.path.join(modules_dir, module_name),
            module_path,
            new_content_init_cf=model,
            new_content_init_py=init_py,
            new_name="modulev1",
        )

        snippetcompiler.setup_for_snippet(
            """
    import modulev1
            """,
            add_to_module_path=[str(tmpdir)],
        )
        await snippetcompiler.do_export_and_deploy(
            partial_compile=partial_compile,
            resource_sets_to_remove=resource_sets_to_remove,
        )

    # Full compile
    await export_model(
        model="""
entity Res extends std::Resource:
    string name
end

implement Res using std::none

a = Res(name="the_resource_a")
b = Res(name="the_resource_b")
c = Res(name="the_resource_c")
d = Res(name="the_resource_d")
e = Res(name="the_resource_e")
z = Res(name="the_resource_z")
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
    entity Res extends std::Resource:
        string name
    end

    implement Res using std::none

    a = Res(name="the_resource_a")
    c2 = Res(name="the_resource_c2")
    f = Res(name="the_resource_f")
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
