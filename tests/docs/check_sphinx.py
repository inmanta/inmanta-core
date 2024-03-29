"""
    Copyright 2024 Inmanta

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

import os
import subprocess

import pytest

docs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", "docs"))


@pytest.fixture(scope="session")
def build_docs(tmpdir_factory):
    tmpdir = tmpdir_factory.mktemp("doctest")
    doctrees = tmpdir.join("doctrees")
    htmldir = tmpdir.join("html")
    # Ensure that all required files such as inmanta.pdf exist
    build_proc = subprocess.run(["make", "html", f"BUILDDIR={tmpdir}"], check=False, cwd=docs_dir)
    return docs_dir, doctrees, htmldir, build_proc


def test_build_docs(build_docs):
    _, _, _, build_proc = build_docs
    build_proc.check_returncode()


@pytest.mark.link_check
def test_linkcheck(build_docs):
    docs_dir, doctrees, htmldir, _ = build_docs
    # Execute link check
    subprocess.check_call(["sphinx-build", "-blinkcheck", "-d", str(doctrees), ".", str(htmldir)], cwd=docs_dir)
    # The link check for openapi.html is ignored in the conf.py file, since
    # a trick is used in the reference/index.rst because toctree doesn't
    # offer support for relative links to something that isn't a sphinx document.
    # This check verifies that the reference/openapi.html file is created.
    openapi_html_file = htmldir.join("reference/openapi.html")
    assert os.path.exists(openapi_html_file)
    openapi_json_file = htmldir.join("_specs/openapi.json")
    assert os.path.exists(openapi_json_file)
