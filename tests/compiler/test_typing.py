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

from inmanta.ast import AttributeException
from inmanta.ast import TypingException
import inmanta.compiler as compiler


def test_lnr_on_double_is_defined(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    string? two
end

Test.one [0:1] -- Test

implement Test using std::none when self.one.two is defined

a = Test(two="b")
a.one = a
"""
    )
    compiler.do_compile()


def test_double_define(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    string test
    string? test
    bool test
end
"""
    )
    with pytest.raises(TypingException):
        compiler.do_compile()


def test_536_number_cast(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Network:
    number segmentation_id
end
implement Network using std::none
net1 = Network(segmentation_id="10")
"""
    )
    with pytest.raises(AttributeException):
        compiler.do_compile()
