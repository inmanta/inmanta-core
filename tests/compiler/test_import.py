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

from inmanta.module import ModuleLoadingException


def test_issue_120_bad_import(snippetcompiler):
    with pytest.raises(ModuleLoadingException) as excinfo:
        snippetcompiler.setup_for_snippet("""import ip::ip""")
    assert excinfo.value.location.lnr == 1


def test_issue_120_bad_import_extra(snippetcompiler):
    with pytest.raises(ModuleLoadingException) as excinfo:
        snippetcompiler.setup_for_snippet("""import slorpf""")
    assert excinfo.value.location.lnr == 1


def test_1480_1767_invalid_repo(snippetcompiler_clean):
    snippetcompiler_clean.repo = "some_invalid_url"
    snippetcompiler_clean.setup_for_error(
        """

        """,
        "Failed to load module std (reported in import std (__internal__:1:1))"
        "\ncaused by:"
        "\n  Could not find module std. Please make sure to add any module v2 requirements with `inmanta module add --v2` and"
        " to install all the project's dependencies with `inmanta project install`.",
    )
