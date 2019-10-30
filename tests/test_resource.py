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
from inmanta.resources import ResourceException, resource


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
