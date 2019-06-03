"""
    Copyright 2018 Inmanta

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

import inmanta.compiler as compiler
from inmanta.ast import RuntimeException


def test_option_values(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test1:

end

entity Test2:
    bool flag=false
end

implement Test2 using std::none

Test1 test1 [1] -- [0:1] Test2 other

implementation tt for Test1:

end

implement Test1 using tt when self.other.flag == false

Test1()
"""
    )
    with pytest.raises(RuntimeException):
        compiler.do_compile()


def test_isset(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test1:

end

entity Test2:
    bool flag=false
end

implement Test2 using std::none

Test1 test1 [1] -- [0:1] Test2 other

implementation tt for Test1:

end

implement Test1 using tt when self.other is defined and self.other.flag == false

Test1(other=Test2())
"""
    )
    compiler.do_compile()
