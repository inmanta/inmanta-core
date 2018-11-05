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

from inmanta.ast import ModuleNotFoundException
import inmanta.compiler as compiler


def test_issue_120_bad_import(snippetcompiler):
    snippetcompiler.setup_for_snippet("""import ip::ip""")
    try:
        compiler.do_compile()
        raise AssertionError("Should get exception")
    except ModuleNotFoundException as e:
        assert e.location.lnr == 1


def test_issue_120_bad_import_extra(snippetcompiler):
    snippetcompiler.setup_for_snippet("""import slorpf""")
    try:
        compiler.do_compile()
        raise AssertionError("Should get exception")
    except ModuleNotFoundException as e:
        assert e.location.lnr == 1
