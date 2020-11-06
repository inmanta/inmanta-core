import os
import subprocess
import pytest

@pytest.fixture
def build_docs(tmpdir):
    doctrees = tmpdir.join("doctrees")
    htmldir = tmpdir.join("html")
    docs_dir = os.path.dirname(os.path.abspath(__file__))
    # Ensure that all required files such as inmanta.pdf exist
    subprocess.check_call(["make", "-C", docs_dir, "html", f"BUILDDIR={tmpdir}"])
    return docs_dir, doctrees, htmldir


def test_linkcheck(build_docs):
    docs_dir, doctrees, htmldir = build_docs
    # Execute link check
    subprocess.check_call(["sphinx-build", "-blinkcheck", "-d", str(doctrees), ".", str(htmldir)])
    # The link check for openapi.html is ignored in the conf.py file, since
    # a trick is used in the reference/index.rst because toctree doesn't
    # offer support for relative links to something that isn't a sphinx document.
    # This check verifies that the reference/openapi.html file is created.
    openapi_html_file = htmldir.join("reference/openapi.html")
    assert os.path.exists(openapi_html_file)

