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

from inmanta import resources
import pytest


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
    assert(len(Resource.fields) == 5)


def test_fields_type():
    with pytest.raises(Exception):
        class Test(resources.Resource):
            fields = ("z")


def test_fields_parent_type():
    with pytest.raises(Exception):
        class Base(resources.Resource):
            fields = ("y")

        class Test(Base):
            fields = ("z",)
