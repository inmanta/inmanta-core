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
import subprocess
import sys

import pytest

from inmanta.module import Project


@pytest.mark.parametrize_any("run", range(5))
def test_compiler_determinism_3034(snippetcompiler, run: int):
    """
    Verify that a certain snippet that used to trigger nondeterministic behavior is now deterministic.
    The snippet used here is an unstable one in the sense that its success is dependent on execution order. The purpose of this
    test is not to verify that it succeeds but to verify that it either always succeeds or always fails. With the current
    compiler implementation it happens to always succeed.
    """
    snippetcompiler.setup_for_snippet(
        """
entity A:
end

A.list [0:] -- A
A.optional [0:1] -- A

implementation a for A:
    self.optional = A()
end

implement A using std::none
# freezing A.optional before A.list would cause a ModifiedAfterFreezeException
implement A using a when std::count(self.list) > 0

a = A(list=A())
test = a.optional
        """
    )
    # fork new Python interpreter to force new Python hash seed, which is a source for nondeterminism
    subprocess.check_output([sys.executable, "-m", "inmanta.app", "compile"], cwd=Project.get()._path)
