"""
    Copyright 2020 Inmanta

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

from compiler.dataflow.conftest import DataflowTestHelper


def test_1974_dataflow_model_entity_extend(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
entity A:
    int n
end

entity B extends A:
    int n = 1
end

implement A using std::none
implement B using std::none

B()
        """,
    )
