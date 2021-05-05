import os
import subprocess

import pytest

@pytest.fixture(scope="session")
def build_docs(tmpdir_factory):
    tmpdir = tmpdir_factory.mktemp("doctest")
    doctrees = tmpdir.join("doctrees")
    htmldir = tmpdir.join("html")
    docs_dir = os.path.dirname(os.path.abspath(__file__))
    # Ensure that all required files such as inmanta.pdf exist
    build_proc = subprocess.run(["make", "-C", docs_dir, "html", f"BUILDDIR={tmpdir}"], check=False)
    return docs_dir, doctrees, htmldir, build_proc


def test_build_docs(build_docs):
    _, _, _, build_proc = build_docs
    build_proc.check_returncode()


@pytest.mark.link_check
def test_linkcheck(build_docs):
    docs_dir, doctrees, htmldir, _ = build_docs
    # Execute link check
    subprocess.check_call(["sphinx-build", "-blinkcheck", "-d", str(doctrees), ".", str(htmldir)])
    # The link check for openapi.html is ignored in the conf.py file, since
    # a trick is used in the reference/index.rst because toctree doesn't
    # offer support for relative links to something that isn't a sphinx document.
    # This check verifies that the reference/openapi.html file is created.
    openapi_html_file = htmldir.join("reference/openapi.html")
    assert os.path.exists(openapi_html_file)
    openapi_json_file = htmldir.join("_specs/openapi.json")
    assert os.path.exists(openapi_json_file)

