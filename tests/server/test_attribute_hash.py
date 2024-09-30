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

import uuid

import pytest

from inmanta.data import Resource


@pytest.mark.fundamental
def test_attribute_hash():
    """
    Increment calculation requires an attribute hash.

    This testcase verifies the basic correctness of this hash

    see issue 5306
    """
    base_resource = {
        "a": [1, 2, 3],
        "b": {"a": "b", "c": "d"},
        "X": "z",
    }

    reordered_same = {
        "X": "z",
        "b": {"c": "d", "a": "b"},
        "a": [1, 2, 3],
    }

    other = {
        "X": "z",
        "b": {"c": "d", "a": []},
        "a": [1, 2, 3],
    }

    env = uuid.uuid4()

    def get_hash(attributes) -> str:
        r = Resource.new(environment=env, resource_version_id="test::Test[a,b=c],v=3", attributes=attributes)
        r.make_hash()
        return r.attribute_hash

    assert get_hash(base_resource) == get_hash(reordered_same)

    assert get_hash(base_resource) != get_hash(other)
