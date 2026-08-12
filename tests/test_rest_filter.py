"""
Copyright 2026 Inmanta
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

from inmanta.graphql.rest_filter import graphql_input
from inmanta.graphql.schema import CoreResourceFilter


def test_graphql_input_accepts_class_or_dotted_path() -> None:
    """graphql_input accepts either a class or a dotted-path string, both resolving to the same class."""
    assert graphql_input(CoreResourceFilter)._resolve_class() is CoreResourceFilter
    assert graphql_input("inmanta.graphql.schema.CoreResourceFilter")._resolve_class() is CoreResourceFilter
