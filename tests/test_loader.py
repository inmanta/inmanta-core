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
import hashlib
import inspect
import os
import shutil
import sys
from typing import List, Optional, Set

import py
import pytest
from pytest import fixture

from inmanta import loader
from inmanta.loader import ModuleSource, SourceInfo
from inmanta.module import Project
from inmanta.moduletool import ModuleTool


def test_code_manager(tmpdir: py.path.local):
    """Verify the code manager"""
    original_project_dir: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "plugins_project")
    project_dir = os.path.join(tmpdir, "plugins_project")
    shutil.copytree(original_project_dir, project_dir)
    project: Project = Project(project_dir)
    Project.set(project)
    project.load()

    ModuleTool().install("single_plugin_file")
    ModuleTool().install("multiple_plugin_files")
    import inmanta_plugins.multiple_plugin_files.handlers as multi
    import inmanta_plugins.single_plugin_file as single

    mgr = loader.CodeManager()
    mgr.register_code("std::File", single.MyHandler)
    mgr.register_code("std::Directory", multi.MyHandler)

    def assert_content(source_info: SourceInfo, handler) -> str:
        filename = inspect.getsourcefile(handler)
        content: str
        with open(filename, "r", encoding="utf-8") as fd:
            content = fd.read()
            assert source_info.content == content
            assert len(source_info.hash) > 0
            return content

    # get types
    types = dict(mgr.get_types())
    assert "std::File" in types
    assert "std::Directory" in types

    single_type_list: List[SourceInfo] = types["std::File"]
    multi_type_list: List[SourceInfo] = types["std::Directory"]

    assert len(single_type_list) == 1
    single_content: str = assert_content(single_type_list[0], single.MyHandler)

    assert len(multi_type_list) == 3
    multi_content: str = assert_content(
        next(s for s in multi_type_list if s.module_name == "inmanta_plugins.multiple_plugin_files.handlers"), multi.MyHandler
    )

    # get_file_hashes
    mgr_contents: Set[str] = {mgr.get_file_content(hash) for hash in mgr.get_file_hashes()}
    assert single_content in mgr_contents
    assert multi_content in mgr_contents

    with pytest.raises(KeyError):
        mgr.get_file_content("test")

    # register type without source
    with pytest.raises(loader.SourceNotFoundException):
        mgr.register_code("test2", str)


def test_code_loader(tmp_path):
    """Test loading a new module"""
    cl = loader.CodeLoader(tmp_path)

    def deploy(code: str) -> None:
        sha1sum = hashlib.new("sha1")
        sha1sum.update(code.encode())
        hv: str = sha1sum.hexdigest()
        cl.deploy_version([ModuleSource("inmanta_plugins.inmanta_unit_test", code, hv)])

    with pytest.raises(ImportError):
        import inmanta_plugins.inmanta_unit_test  # NOQA

    deploy(
        """
def test():
    return 10
        """
    )

    import inmanta_plugins.inmanta_unit_test  # NOQA

    assert inmanta_plugins.inmanta_unit_test.test() == 10

    # deploy new version
    deploy(
        """
def test():
    return 20
        """
    )

    assert inmanta_plugins.inmanta_unit_test.test() == 20


def test_code_loader_dependency(tmp_path, caplog):
    """Test loading two modules with a dependency between them"""
    cl = loader.CodeLoader(tmp_path)

    def get_module_source(module: str, code: str) -> ModuleSource:
        sha1sum = hashlib.new("sha1")
        sha1sum.update(code.encode())
        hv: str = sha1sum.hexdigest()
        return ModuleSource(module, code, hv)

    source_init: ModuleSource = get_module_source(
        "inmanta_plugins.inmanta_unit_test_modular",
        """
        """,
    )

    source_tests: ModuleSource = get_module_source(
        "inmanta_plugins.inmanta_unit_test_modular.tests",
        """
from inmanta_plugins.inmanta_unit_test_modular.helpers import helper

def test():
    return 10 + helper()
        """,
    )

    source_helpers: ModuleSource = get_module_source(
        "inmanta_plugins.inmanta_unit_test_modular.helpers",
        """
def helper():
    return 1
        """,
    )

    cl.deploy_version([source_tests, source_helpers, source_init])

    import inmanta_plugins.inmanta_unit_test_modular.tests  # NOQA

    assert inmanta_plugins.inmanta_unit_test_modular.tests.test() == 11
    assert "ModuleNotFoundError: No module named" not in caplog.text


def test_2312_code_loader_missing_init(tmp_path) -> None:
    cl = loader.CodeLoader(tmp_path)

    code: str = """
def test():
    return 10
        """
    sha1sum = hashlib.new("sha1")
    sha1sum.update(code.encode())
    hv: str = sha1sum.hexdigest()
    cl.deploy_version([ModuleSource("inmanta_plugins.my_module.my_sub_mod", code, hv)])

    import inmanta_plugins.my_module.my_sub_mod as sm

    assert sm.test() == 10


def test_code_loader_import_error(tmp_path, caplog):
    """Test loading code with an import error"""
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
        import inmanta_bad_unit_test  # NOQA

    cl.deploy_version([ModuleSource("inmanta_plugins.inmanta_bad_unit_test", code, hv)])

    assert "ModuleNotFoundError: No module named 'badimmport'" in caplog.text


@fixture(scope="function")
def module_path(tmpdir):
    module_finder = loader.PluginModuleFinder([str(tmpdir)])
    sys.meta_path.insert(0, module_finder)
    yield str(tmpdir)
    sys.meta_path.remove(module_finder)


def test_venv_path(tmpdir: py.path.local):
    original_project_dir: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "plugins_project")
    project_dir = os.path.join(tmpdir, "plugins_project")
    shutil.copytree(original_project_dir, project_dir)

    def load_project(venv_path: Optional[str]) -> None:
        if venv_path is None:
            project: Project = Project(project_dir)
        else:
            project: Project = Project(project_dir, venv_path=venv_path)
        Project.set(project)
        project.load()

    # Use default venv dir
    default_venv_dir = os.path.join(project_dir, ".env")
    shutil.rmtree(default_venv_dir, ignore_errors=True)
    assert not os.path.exists(default_venv_dir)
    load_project(venv_path=None)
    assert os.path.exists(default_venv_dir)
    shutil.rmtree(default_venv_dir)

    # Use non-default venv dir
    non_default_venv_dir = os.path.join(project_dir, "non-default-venv-dir")
    assert not os.path.exists(default_venv_dir)
    assert not os.path.exists(non_default_venv_dir)
    load_project(venv_path=non_default_venv_dir)
    assert not os.path.exists(default_venv_dir)
    assert os.path.exists(non_default_venv_dir)
    shutil.rmtree(non_default_venv_dir)

    # venv_path points to symlink
    os.mkdir(non_default_venv_dir)
    symlink_dir = os.path.join(project_dir, "symlink-dir")
    os.symlink(non_default_venv_dir, symlink_dir)
    for p in [non_default_venv_dir, symlink_dir]:
        assert os.path.exists(p)
        assert not os.path.exists(os.path.join(p, "bin", "python"))
    assert not os.path.islink(non_default_venv_dir)
    assert os.path.islink(symlink_dir)
    load_project(venv_path=symlink_dir)
    for p in [non_default_venv_dir, symlink_dir]:
        assert os.path.exists(os.path.join(p, "bin", "python"))


def test_module_loader(module_path, tmpdir, capsys):
    """
    Verify that the loader.PluginModuleFinder and loader.PluginModuleLoader load modules correctly.
    """
    origin_mod_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "modules", "submodule")
    mod_dir = tmpdir.join(os.path.basename(origin_mod_dir))
    shutil.copytree(origin_mod_dir, mod_dir)

    capsys.readouterr()  # Clear buffers

    from inmanta_plugins.submodule import test

    assert test() == "test"
    (stdout, stderr) = capsys.readouterr()
    assert stdout.count("#loading inmanta_plugins.submodule#") == 1
    assert stdout.count("#loading inmanta_plugins.submodule.submod#") == 0
    assert stdout.count("#loading inmanta_plugins.submodule.pkg#") == 0
    assert stdout.count("#loading inmanta_plugins.submodule.pkg.submod2#") == 0

    from inmanta_plugins.submodule.submod import test_submod

    assert test_submod() == "test_submod"
    (stdout, stderr) = capsys.readouterr()
    assert stdout.count("#loading inmanta_plugins.submodule#") == 0
    assert stdout.count("#loading inmanta_plugins.submodule.submod#") == 1
    assert stdout.count("#loading inmanta_plugins.submodule.pkg#") == 0
    assert stdout.count("#loading inmanta_plugins.submodule.pkg.submod2#") == 0

    from inmanta_plugins.submodule.pkg import test_pkg

    assert test_pkg() == "test_pkg -- test_submod2"
    (stdout, stderr) = capsys.readouterr()
    assert stdout.count("#loading inmanta_plugins.submodule#") == 0
    assert stdout.count("#loading inmanta_plugins.submodule.submod#") == 0
    assert stdout.count("#loading inmanta_plugins.submodule.pkg#") == 1
    assert stdout.count("#loading inmanta_plugins.submodule.pkg.submod2#") == 1

    with pytest.raises(ImportError):
        from inmanta_plugins.tests import doesnotexist  # NOQA


def test_plugin_loading_on_project_load(tmpdir, capsys):
    """
    Load all plugins via the Project.load() method call and verify that no
    module is loaded twice when an import statement is used.
    """
    main_cf = tmpdir.join("main.cf")
    main_cf.write("import submodule")

    project_yml = tmpdir.join("project.yml")
    project_yml.write(
        """
name: test
modulepath: libs
downloadpath: libs
repo: https://github.com/inmanta/inmanta.git
install_mode: master
    """
    )

    tmpdir.mkdir("libs")
    origin_mod_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "modules", "submodule")
    mod_dir = tmpdir.join("libs", os.path.basename(origin_mod_dir))
    shutil.copytree(origin_mod_dir, mod_dir)

    project = Project(tmpdir, autostd=False)
    Project.set(project)
    project.load()

    (stdout, stderr) = capsys.readouterr()
    assert stdout.count("#loading inmanta_plugins.submodule#") == 1
    assert stdout.count("#loading inmanta_plugins.submodule.submod#") == 1
    assert stdout.count("#loading inmanta_plugins.submodule.pkg#") == 1
    assert stdout.count("#loading inmanta_plugins.submodule.pkg.submod2#") == 1

    from inmanta_plugins.submodule import test

    assert test() == "test"
    (stdout, stderr) = capsys.readouterr()
    assert "#loading" not in stdout

    from inmanta_plugins.submodule.submod import test_submod

    assert test_submod() == "test_submod"
    (stdout, stderr) = capsys.readouterr()
    assert "#loading" not in stdout

    from inmanta_plugins.submodule.pkg import test_pkg

    assert test_pkg() == "test_pkg -- test_submod2"
    (stdout, stderr) = capsys.readouterr()
    assert "#loading" not in stdout


def test_plugin_loading_old_format(tmpdir, capsys):
    """
    Ensure the code loader ignores code formatted in the old on disk format (pre Inmanta 2020.4).
    (See issue: #2162)
    """
    # Create directory structure code dir
    code_dir = tmpdir
    modules_dir = tmpdir.join(loader.MODULE_DIR)
    modules_dir.mkdir()

    # Create source files using pre Inmanta 2020.4 format
    old_format_source_file = modules_dir.join("inmanta_plugins.old_format.py")
    old_format_source_file.write("")

    # Assert code using the pre inmanta 2020.4 format is ignored
    loader.CodeLoader(code_dir)
    with pytest.raises(ImportError):
        import inmanta_plugins.old_format  # NOQA

    # Add newly formatted code next the pre Inmanta 2020.4 format
    new_format_mod_dir = modules_dir.join("new_format")
    new_format_mod_dir.mkdir()
    new_format_plugins_dir = new_format_mod_dir.join("plugins")
    new_format_plugins_dir.mkdir()
    new_format_source_file = new_format_plugins_dir.join("__init__.py")
    new_format_source_file.write(
        """
def test():
    return 10
    """
    )

    # Assert newly formatted code is loaded and code using the pre inmanta 2020.4 format is ignored
    loader.CodeLoader(code_dir)
    import inmanta_plugins.new_format as mod  # NOQA

    assert mod.test() == 10
    with pytest.raises(ImportError):
        import inmanta_plugins.old_format  # NOQA
