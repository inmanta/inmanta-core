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


@resources.resource("exp::Test", agent="agent", id_attribute="test")
class Test(resources.ManagedResource):
    """
        This class represents a service on a system.
    """
    fields = ("name", "agent", "field1")

    @staticmethod
    def get_test(exp, obj):
        return "test_value_" + obj.name


@resources.resource("exp::Test2", agent="agent", id_attribute="name")
class Test2(resources.PurgeableResource):
    """
        This class represents a service on a system.
    """
    fields = ("name", "agent", "mydict", "mylist")
