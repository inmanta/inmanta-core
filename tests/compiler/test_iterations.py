"""
    Copyright 2019 Inmanta

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
from inmanta.ast import CompilerException


def test_max_iterations(snippetcompiler, monkeypatch):
    monkeypatch.setenv("INMANTA_MAX_ITERATIONS", "1")

    with pytest.raises(CompilerException) as e:
        snippetcompiler.setup_for_snippet(
            """
    import std

    entity Hg:
    end

    Hg.hosts [0:] -- std::Host

    implement Hg using std::none

    hg = Hg()

    for i in [1,2,3]:
     hg.hosts = std::Host(name="Test{{i}}", os=std::unix)
    end


    for i in hg.hosts:
        std::ConfigFile(host=i, path="/fx", content="")
    end
    """
        )

        (types, _) = compiler.do_compile()

    assert "Could not complete model, max_iterations 1 reached." in str(e.value)
