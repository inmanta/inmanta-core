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
import inspect
import hashlib

from inmanta import loader


def test_code_manager():
    """ Verify the code manager
    """
    mgr = loader.CodeManager()
    mgr.register_code("test", test_code_manager)

    # get types
    types = mgr.get_types()
    name, type_list = next(types)
    assert name == "test"
    assert len(type_list) == 1

    source_info = type_list[0]

    def get_code():
        filename = inspect.getsourcefile(test_code_manager)
        with open(filename, "r") as fd:
            return fd.read()

    content = get_code()
    assert source_info.content == content
    assert len(source_info.hash) > 0

    with pytest.raises(Exception):
        # only available in a valid project. Other test cases with full project validate this. This one checks
        # whether we give an error.
        source_info.requires()

    # get_file_hashes
    hashes = mgr.get_file_hashes()
    mgr_content = mgr.get_file_content(next(hashes))
    assert mgr_content == content

    with pytest.raises(KeyError):
        mgr.get_file_content("test")

    # register type without source
    with pytest.raises(loader.SourceNotFoundException):
        mgr.register_code("test2", str)


def test_empty_code_loader(tmp_path):
    """ Test loading an empty cache
    """
    cl = loader.CodeLoader(tmp_path)
    cl.load_modules()


def test_code_loader(tmp_path):
    """ Test loading a new module
    """
    cl = loader.CodeLoader(tmp_path)
    code = """
def test():
    return 10
    """

    sha1sum = hashlib.new("sha1")
    sha1sum.update(code.encode())
    hv = sha1sum.hexdigest()

    with pytest.raises(ImportError):
        import inmanta_unit_test # NOQA

    cl.deploy_version(hv, "inmanta_unit_test", code)

    import inmanta_unit_test # NOQA

    assert inmanta_unit_test.test() == 10

    # reload cached code
    cl.load_modules()


def test_code_loader_import_error(tmp_path, caplog):
    """ Test loading code with an import error
    """
    cl = loader.CodeLoader(tmp_path)
    code = """
import badimmport
def test():
    return 10
    """

    sha1sum = hashlib.new("sha1")
    sha1sum.update(code.encode())
    hv = sha1sum.hexdigest()

    with pytest.raises(ImportError):
        import inmanta_bad_unit_test # NOQA

    cl.deploy_version(hv, "inmanta_bad_unit_test", code)

    assert "ModuleNotFoundError: No module named 'badimmport'" in caplog.text
