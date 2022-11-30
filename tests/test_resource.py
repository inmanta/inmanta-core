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

from inmanta import resources
from inmanta.ast import ExternalException
from inmanta.resources import PARSE_ID_REGEX, PARSE_RVID_REGEX, Id, ResourceException, resource


class Base(resources.Resource):
    fields = ("a", "b", "c")

    @staticmethod
    def get_a(exporter, resource):
        return resource.a


@resources.resource("test_resource::Resource", agent="a", id_attribute="b")
class Resource(Base):
    fields = ("c", "d")
    map = {"d": lambda _, x: x.d}


def test_field_merge():
    assert len(Resource.fields) == 5


def test_fields_type():
    with pytest.raises(Exception):

        class Test(resources.Resource):
            fields = "z"


def test_fields_parent_type():
    with pytest.raises(Exception):

        class Base(resources.Resource):
            fields = "y"

        class Test(Base):
            fields = ("z",)


def test_resource_base(snippetcompiler):

    import inmanta.resources

    @resource("__config__::XResource", agent="agent", id_attribute="key")
    class MyResource(inmanta.resources.Resource):
        """
        A file on a filesystem
        """

        fields = ("key", "value", "agent")

    snippetcompiler.setup_for_snippet(
        """
        entity XResource:
            string key
            string agent
            string value
        end

        implement XResource using none

        implementation none for XResource:
        end

        XResource(key="key", agent="agent", value="value")
        """,
        autostd=False,
    )
    _version, json_value = snippetcompiler.do_export()

    assert len(json_value) == 1
    myresource = next(json_value.values().__iter__())

    assert myresource.key == "key"
    assert myresource.agent == "agent"
    assert myresource.value == "value"


def test_resource_base_with_method_key(snippetcompiler):

    import inmanta.resources

    @resource("__config__::XResource", agent="agent", id_attribute="key")
    class MyResource(inmanta.resources.Resource):
        """
        A file on a filesystem
        """

        fields = ("key", "value", "agent", "serialize")

        @staticmethod
        def get_serialize(_exporter, resource):
            return resource.key

    snippetcompiler.setup_for_snippet(
        """
        entity XResource:
            string key
            string agent
            string value
        end

        implement XResource using none

        implementation none for XResource:
        end

        XResource(key="key", agent="agent", value="value")
        """,
        autostd=False,
    )
    with pytest.raises(ResourceException):
        snippetcompiler.do_export()


def test_resource_with_keyword(snippetcompiler):

    import inmanta.resources

    @resource("__config__::YResource", agent="agent", id_attribute="key")
    class MyResource(inmanta.resources.Resource):
        """
        A file on a filesystem
        """

        fields = ("key", "value", "agent", "model")

        @staticmethod
        def get_model(_exporter, resource):
            return resource.key

    snippetcompiler.setup_for_snippet(
        """
         entity YResource:
             string key
             string agent
             string value
         end

         implement YResource using none

         implementation none for YResource:
         end

         YResource(key="key", agent="agent", value="value")
         """,
        autostd=False,
    )

    with pytest.raises(ResourceException):
        snippetcompiler.do_export()


def test_resource_with_private_method(snippetcompiler):

    import inmanta.resources

    @resource("__config__::YResource", agent="agent", id_attribute="key")
    class MyResource(inmanta.resources.Resource):
        """
        A file on a filesystem
        """

        fields = ("__setattr__", "key", "value", "agent")

    snippetcompiler.setup_for_snippet(
        """
        entity YResource:
            string key
            string agent
            string value
        end

        implement YResource using none

        implementation none for YResource:
        end

        YResource(key="key", agent="agent", value="value")
        """,
        autostd=False,
    )

    with pytest.raises(ResourceException):
        snippetcompiler.do_export()


def test_object_to_id(snippetcompiler):
    import inmanta.resources

    @resource("__config__::MYResource", agent="agent", id_attribute="key")
    class MyResource(inmanta.resources.Resource):
        fields = ("key", "value", "agent")

    snippetcompiler.setup_for_snippet(
        """
        import tests
        entity MYResource:
            string key
            string agent
            string value
        end

        implement MYResource using std::none

        x = MYResource(key="key", agent="agent", value="value")
        std::print(tests::get_id(x))
        """
    )

    snippetcompiler.do_export()


def test_resource_invalid_agent_name_annotation():

    import inmanta.resources

    with pytest.raises(ResourceException):

        @resource("__config__::XResource", agent=42, id_attribute="key")
        class MyResource(inmanta.resources.Resource):
            """
            A file on a filesystem
            """

            fields = ("key", "value", "agent")


def test_resource_invalid_agent_name_attribute_type(snippetcompiler):
    import inmanta.resources

    @resource("__config__::MYResource", agent="agent", id_attribute="key")
    class MyResource(inmanta.resources.Resource):
        fields = ("key", "value", "agent")

    snippetcompiler.setup_for_snippet(
        """
        import tests
        entity MYResource:
            string key
            int agent
            string value
        end

        implement MYResource using std::none

        x = MYResource(key="key", agent=47, value="value")
        std::print(tests::get_id(x))
        """
    )
    with pytest.raises(ExternalException):
        snippetcompiler.do_export()


def test_resource_invalid_agent_name_entity(snippetcompiler):
    import inmanta.resources

    @resource("__config__::MYResource", agent="agent", id_attribute="key")
    class MyResource(inmanta.resources.Resource):
        fields = ("key", "value", "agent")

    snippetcompiler.setup_for_snippet(
        """
        import tests

        entity AgentResource:
        end

        entity MYResource:
            string key
            string value
        end
        MYResource.agent [1] -- AgentResource.myresource [1]

        implement MYResource using std::none
        implement AgentResource using std::none

        x = MYResource(key="key", agent=AgentResource(), value="value")
        std::print(tests::get_id(x))
        """
    )
    with pytest.raises(ExternalException):
        snippetcompiler.do_export()


def test_is_resource_version_id():
    """
    Test whether the is_resource_version_id() method of the Id class works correctly.
    """
    assert Id.is_resource_version_id("test::Resource[agent,key=id],v=3")
    assert Id.is_resource_version_id("test::mod::Resource[agent,key=id],v=3")
    assert not Id.is_resource_version_id("test::Resource[agent,key=id]")
    assert not Id.is_resource_version_id("test::mod::Resource[agent,key=id]")
    assert not Id.is_resource_version_id("test::Resource")


def test_parse_id_regex():
    result = PARSE_ID_REGEX.search("test::Resource[agent,key=id],v=3")
    assert result is not None
    assert result.group("id") == "test::Resource[agent,key=id]"
    assert result.group("type") == "test::Resource"
    assert result.group("ns") == "test"
    assert result.group("class") == "Resource"
    assert result.group("hostname") == "agent"
    assert result.group("attr") == "key"
    assert result.group("value") == "id"
    assert result.group("version") == "3"

    result = PARSE_ID_REGEX.search("test::submodule::Resource[agent,key=id],v=3")
    assert result is not None
    assert result.group("id") == "test::submodule::Resource[agent,key=id]"
    assert result.group("type") == "test::submodule::Resource"
    assert result.group("ns") == "test::submodule"
    assert result.group("class") == "Resource"
    assert result.group("hostname") == "agent"
    assert result.group("attr") == "key"
    assert result.group("value") == "id"
    assert result.group("version") == "3"

    result = PARSE_ID_REGEX.search("test::Resource[agent,key=id]")
    assert result is not None
    assert result.group("id") == "test::Resource[agent,key=id]"
    assert result.group("type") == "test::Resource"
    assert result.group("ns") == "test"
    assert result.group("class") == "Resource"
    assert result.group("hostname") == "agent"
    assert result.group("attr") == "key"
    assert result.group("value") == "id"
    assert result.group("version") is None

    result = PARSE_ID_REGEX.search("test::submodule::Resource[agent,key=id]")
    assert result is not None
    assert result.group("id") == "test::submodule::Resource[agent,key=id]"
    assert result.group("type") == "test::submodule::Resource"
    assert result.group("ns") == "test::submodule"
    assert result.group("class") == "Resource"
    assert result.group("hostname") == "agent"
    assert result.group("attr") == "key"
    assert result.group("value") == "id"
    assert result.group("version") is None


def test_parse_rvid_regex():
    result = PARSE_RVID_REGEX.search("test::Resource[agent,key=id],v=3")
    assert result is not None
    assert result.group("id") == "test::Resource[agent,key=id]"
    assert result.group("type") == "test::Resource"
    assert result.group("ns") == "test"
    assert result.group("class") == "Resource"
    assert result.group("hostname") == "agent"
    assert result.group("attr") == "key"
    assert result.group("value") == "id"
    assert result.group("version") == "3"

    result = PARSE_RVID_REGEX.search("test::submodule::Resource[agent,key=id],v=3")
    assert result is not None
    assert result.group("id") == "test::submodule::Resource[agent,key=id]"
    assert result.group("type") == "test::submodule::Resource"
    assert result.group("ns") == "test::submodule"
    assert result.group("class") == "Resource"
    assert result.group("hostname") == "agent"
    assert result.group("attr") == "key"
    assert result.group("value") == "id"
    assert result.group("version") == "3"

    result = PARSE_RVID_REGEX.search("test::Resource[agent,key=id]")
    assert result is None

    result = PARSE_RVID_REGEX.search("test::submodule::Resource[agent,key=id]")
    assert result is None
