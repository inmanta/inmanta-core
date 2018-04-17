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
from inmanta import config, const
import pytest


def test_id_mapping_export(snippetcompiler):
    snippetcompiler.setup_for_snippet("""import exp

        exp::Test(name="a", agent="b")
        """)

    _version, json_value = snippetcompiler.do_export()

    assert(len(json_value) == 1)
    resource = list(json_value.values())[0]
    assert(resource.id.attribute_value == "test_value_a")


def test_unknown_agent(snippetcompiler):
    snippetcompiler.setup_for_snippet("""import exp
        import tests

        exp::Test(name="a", agent=tests::unknown())
        """)
    _version, json_value = snippetcompiler.do_export()

    assert(len(json_value) == 0)


def test_unknown_attribute_value(snippetcompiler):
    snippetcompiler.setup_for_snippet("""import exp
        import tests

        exp::Test(name=tests::unknown(), agent="b")
        """)
    _version, json_value = snippetcompiler.do_export()

    assert(len(json_value) == 0)


def test_ignore_resource(snippetcompiler):
    snippetcompiler.setup_for_snippet("""import exp
        import tests

        exp::Test(name="a", agent="b", managed=false)
        """)
    _version, json_value = snippetcompiler.do_export()

    assert(len(json_value) == 0)


def test_ignore_resource_requires(snippetcompiler, caplog):
    snippetcompiler.setup_for_snippet("""import exp
        import tests

        a = exp::Test(name="a", agent="aa", managed=false)
        b = exp::Test(name="b", agent="aa", requires=a)
        c = exp::Test(name="c", agent="aa", requires=b)
        """)
    _version, json_value = snippetcompiler.do_export()
    assert(len(json_value) == 2)
    assert_count = 0
    for resource_id, resource in json_value.items():
        if resource_id.attribute_value == "test_value_b":
            assert(len(resource.requires) == 0)
            assert_count += 1

        elif resource_id.attribute_value == "test_value_c":
            assert(len(resource.requires) == 1)
            assert_count += 1

    warning = [x for x in caplog.records if x.msg ==
               "The resource %s had requirements before flattening, but not after flattening."
               " Initial set was %s. Perhaps provides relation is not wired through correctly?"]
    assert len(warning) == 0
    assert(assert_count == 2)


def test_unknown_in_id_requires(snippetcompiler, caplog):
    """
        Test to validate that resources that have an unknown in their ID attributes, are removed from requires
    """
    snippetcompiler.setup_for_snippet("""import exp
        import tests

        a = exp::Test(name=tests::unknown(), agent="aa")
        b = exp::Test(name="b", agent="aa", requires=a)
        c = exp::Test(name="c", agent="aa", requires=b)
        """)
    config.Config.set("unknown_handler", "default", "prune-resource")
    _version, json_value = snippetcompiler.do_export()

    assert(len(json_value) == 2)
    assert_count = 0
    for resource_id, resource in json_value.items():
        if resource_id.attribute_value == "test_value_b":
            assert(len(resource.requires) == 0)
            assert_count += 1

        elif resource_id.attribute_value == "test_value_c":
            assert(len(resource.requires) == 1)
            assert_count += 1

    warning = [x for x in caplog.records if x.msg ==
               "The resource %s had requirements before flattening, but not after flattening."
               " Initial set was %s. Perhaps provides relation is not wired through correctly?"]
    assert len(warning) == 0
    assert(assert_count == 2)


def test_unknown_in_attribute_requires(snippetcompiler, caplog):
    """
        Test to validate that resources that have an unknown in their ID attributes, are removed from requires
    """
    snippetcompiler.setup_for_snippet("""import exp
        import tests

        a = exp::Test(name="a", agent="aa", field1=tests::unknown())
        b = exp::Test(name="b", agent="aa", requires=a)
        c = exp::Test(name="c", agent="aa", requires=b)
        """)
    config.Config.set("unknown_handler", "default", "prune-resource")
    _version, json_value, status, model = snippetcompiler.do_export(include_status=True)

    assert len(json_value) == 3
    assert len([x for x in status.values() if x == const.ResourceState.available]) == 2
    assert len([x for x in status.values() if x == const.ResourceState.undefined]) == 1

    warning = [x for x in caplog.records if x.msg ==
               "The resource %s had requirements before flattening, but not after flattening."
               " Initial set was %s. Perhaps provides relation is not wired through correctly?"]
    assert len(warning) == 0


@pytest.mark.gen_test
def test_empty_server_export(snippetcompiler, server, client):
    snippetcompiler.setup_for_snippet("""
            h = std::Host(name="test", os=std::linux)
        """)
    snippetcompiler.do_export(deploy=True)


@pytest.mark.gen_test
def test_server_export(snippetcompiler, server, client, environment):
    config.Config.set("config", "environment", environment)
    snippetcompiler.setup_for_snippet("""
            h = std::Host(name="test", os=std::linux)
            f = std::ConfigFile(host=h, path="/etc/motd", content="test")
        """)
    snippetcompiler.do_export(deploy=True)

    result = yield client.list_versions(tid=environment)
    assert result.code == 200
    assert len(result.result["versions"]) == 1
    assert result.result["versions"][0]["total"] == 1


@pytest.mark.gen_test
def test_dict_export_server(snippetcompiler, server, client, environment):
    config.Config.set("config", "environment", environment)
    snippetcompiler.setup_for_snippet("""
import exp

a = exp::Test2(mydict={"a":"b"}, mylist=["a","b"])
""")

    snippetcompiler.do_export(deploy=True)

    result = yield client.list_versions(tid=environment)
    assert result.code == 200
    assert len(result.result["versions"]) == 1
    assert result.result["versions"][0]["total"] == 1


def test_dict_export(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
import exp

a = exp::Test2(mydict={"a":"b"}, mylist=["a","b"])
""")
    _version, json_value, status, model = snippetcompiler.do_export(include_status=True)

    assert len(json_value) == 1
    print(_version, json_value, status, model)
