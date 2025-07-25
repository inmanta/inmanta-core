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
import importlib.abc
import importlib.machinery
import importlib.util
import os
import shutil
import sys
from logging import DEBUG
from types import ModuleType
from typing import Optional

import py
import pytest
from pytest import fixture

import utils
from inmanta import const, env, loader, moduletool
from inmanta.data.model import ModuleSourceMetadata
from inmanta.env import PipConfig
from inmanta.loader import ModuleSource, SourceNotFoundException
from inmanta.module import Project


def get_module_source(module: str, code: str) -> ModuleSource:
    data = code.encode()
    sha1sum = hashlib.new("sha1")
    sha1sum.update(data)
    hv: str = sha1sum.hexdigest()
    return ModuleSource(
        metadata=ModuleSourceMetadata(
            name=module,
            hash_value=hv,
            is_byte_code=False,
        ),
        source=data,
    )


@pytest.mark.parametrize(
    "install_all_dependencies,expected_dependencies",
    [
        (True, {"inmanta-module-std", "lorem"}),
        (False, {"lorem"}),
    ],
)
def test_code_manager(tmpdir: py.path.local, deactive_venv, install_all_dependencies, expected_dependencies):
    """Verify the code manager"""
    original_project_dir: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "plugins_project")
    project_dir = os.path.join(tmpdir, "plugins_project")
    shutil.copytree(original_project_dir, project_dir)
    project: Project = Project(project_dir, venv_path=os.path.join(project_dir, ".env"))
    project._metadata.agent_install_dependency_modules = install_all_dependencies

    Project.set(project)
    project.install_modules()
    project.load()

    project.load_module("single_plugin_file", allow_v1=True)
    project.load_module("multiple_plugin_files", allow_v1=True)

    # non_imported_plugin_file was not loaded in the project
    # we check that a warning is produced when we attempt to register
    # some of its code

    import inmanta_plugins.multiple_plugin_files.handlers as multi
    import inmanta_plugins.non_imported_plugin_file as non_imported
    import inmanta_plugins.single_plugin_file as single

    mgr = loader.CodeManager()
    mgr.register_code("std::testing::NullResource", single.MyHandler)
    mgr.register_code("multiple_plugin_files::NullResourceBis", multi.MyHandler)

    with pytest.raises(SourceNotFoundException) as excinfo:
        mgr.register_code("non_imported_plugin_file::NullResourceBis", non_imported.MyHandler)

    exception_message = (
        "Module non_imported_plugin_file is imported in plugin code but not in model code. "
        "Either remove the unused import, or make sure to import the module in model code."
    )
    assert exception_message in str(excinfo.value)

    module_version_info = mgr.get_module_version_info()
    assert "multiple_plugin_files" in module_version_info.keys()
    assert "single_plugin_file" in module_version_info.keys()

    assert set(module_version_info["single_plugin_file"].requirements) == expected_dependencies
    assert len(module_version_info["single_plugin_file"].files_in_module) == 1
    assert len(module_version_info["multiple_plugin_files"].files_in_module) == 3

    with pytest.raises(KeyError):
        mgr.get_file_content("test")

    # register type without source
    with pytest.raises(loader.SourceNotFoundException):
        mgr.register_code("test2", str)


def test_code_loader(tmp_path, caplog):
    """
    Test code loader capabilities:
        - test code loader cache
        - test that an exception is raised when re-loading a module with different content
    """
    caplog.set_level(DEBUG)

    cl = loader.CodeLoader(tmp_path)

    with pytest.raises(ImportError):
        import inmanta_plugins.inmanta_unit_test  # NOQA

    code = """
def test():
    return 10
    """
    source_1 = get_module_source("inmanta_plugins.inmanta_unit_test", code)

    # Ensure source is present on disk
    cl.deploy_version([source_1])

    assert any("Deploying code " in message for message in caplog.messages)
    caplog.clear()

    # First manual load to be able to check the content remains untouched
    import inmanta_plugins.inmanta_unit_test  # NOQA

    assert inmanta_plugins.inmanta_unit_test.test() == 10

    # deploy same version
    cl.deploy_version([source_1])

    assert inmanta_plugins.inmanta_unit_test.test() == 10
    assert any("Deploying code " in message for message in caplog.messages)
    assert any(
        f"Not deploying code (hv={source_1.metadata.hash_value}, module={source_1.metadata.name}) "
        "because it is already on disk" in message
        for message in caplog.messages
    )
    caplog.clear()

    # Load the module to register it in the loader cache
    cl.load_module(source_1.metadata.name, source_1.metadata.hash_value)
    # Subsequent deploys of the same module will result in a cache hit
    cl.deploy_version([source_1])
    assert any(
        f"Not deploying code (hv={source_1.metadata.hash_value}, module={source_1.metadata.name}) because of cache hit"
        in message
        for message in caplog.messages
    )
    caplog.clear()

    # deploy new version
    code = """
def test():
    return 20
        """
    source_2 = get_module_source("inmanta_plugins.inmanta_unit_test", code)
    cl.deploy_version([source_2])

    assert any("Deploying code " in message for message in caplog.messages)

    with pytest.raises(Exception):
        cl.load_module(source_2.metadata.name, source_2.metadata.hash_value)
        assert any(
            f"The content of module {source_2.metadata.name} changed since it was last imported." in message
            for message in caplog.messages
        )

    assert inmanta_plugins.inmanta_unit_test.test() == 10


def test_code_loader_dependency(tmp_path, caplog, deactive_venv):
    """Test loading two modules with a dependency between them"""
    cl = loader.CodeLoader(tmp_path)

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

    code = """
def test():
    return 10
        """
    cl.deploy_version([get_module_source("inmanta_plugins.my_module.my_sub_mod", code)])

    import inmanta_plugins.my_module.my_sub_mod as sm

    assert sm.test() == 10


def test_code_loader_import_error(tmp_path, caplog, deactive_venv):
    """Test loading code with an import error"""
    cl = loader.CodeLoader(tmp_path)
    code = """
import badimmport
def test():
    return 10
    """

    with pytest.raises(ImportError):
        import inmanta_plugins.inmanta_bad_unit_test  # NOQA

    caplog.clear()
    cl.deploy_version([get_module_source("inmanta_plugins.inmanta_bad_unit_test", code)])

    with pytest.raises(ModuleNotFoundError):
        import inmanta_plugins.inmanta_bad_unit_test  # NOQA

        assert "ModuleNotFoundError: No module named 'badimmport'" in caplog.text


@fixture(scope="function")
def module_path(tmpdir):
    """
    Remark: Don't use this fixture in combination with instances of the Project class
            or the CodeLoader class as it would reset the config of the PluginModuleFinder.
    """
    loader.PluginModuleFinder.configure_module_finder(modulepaths=[str(tmpdir)])
    yield str(tmpdir)
    loader.PluginModuleFinder.reset()


@pytest.mark.slowtest
@pytest.mark.parametrize(
    "prefer_finder, reload",
    [(True, False), (False, False), (True, True)],
)
def test_plugin_module_finder(
    tmpdir: py.path.local,
    tmpvenv_active_inherit: env.VirtualEnv,
    modules_dir: str,
    prefer_finder: bool,
    reload: bool,
) -> None:
    """
    Verify correct behavior of the PluginModuleFinder class, especially with respect to preference when a module is present
    both in the normal venv and in the finder's module path.
    The different scenarios are tested via parametrization rather than in a single test case to force proper cleanup in
    between.

    :param prefer_finder: Configure the custom module finder to be preferred over the default finders.
    :param reload: Instead of only importing the module at the end, already import it before setting up the finder and reload
        it after, checking that the change of source works as expected.
    """
    module: str = "mymodule"
    python_module: str = f"{const.PLUGINS_PACKAGE}.{module}"

    # set up libs dir for the custom module finder
    libs_dir: py.path.local = tmpdir.mkdir("libs")
    module_dir: py.path.local = libs_dir.join(module)
    utils.v1_module_from_template(
        os.path.join(modules_dir, "minimalv1module"),
        str(module_dir),
        new_name=module,
        new_content_init_py="where = 'libs'",
    )

    # install module in venv
    venv_module_dir: py.path.local = tmpdir.join("mymodule_for_venv")
    utils.v1_module_from_template(
        str(module_dir),
        str(venv_module_dir),
        new_content_init_py="where = 'venv'",
    )
    mod_artifact_paths = moduletool.ModuleTool().build(path=str(venv_module_dir), wheel=True)
    env.process_env.install_for_config(
        requirements=[],
        paths=[env.LocalPackagePath(path=mod_artifact_paths[0])],
        config=PipConfig(use_system_config=True),
    )

    module_to_reload: Optional[ModuleType] = None
    if reload:
        # load it once before setting up the finder
        module_to_reload = importlib.import_module(python_module)

    # set up module finder
    assert not any(isinstance(finder, loader.PluginModuleFinder) for finder in sys.meta_path)
    loader.PluginModuleFinder.configure_module_finder(modulepaths=[str(libs_dir)], prefer=prefer_finder)

    # verify that the correct module will be loaded: either the one from the venv or the one in libs, depending on parameters
    assert isinstance(sys.meta_path[0 if prefer_finder else -1], loader.PluginModuleFinder)
    # reload now to refresh ModuleSpec and associated loader
    if reload:
        assert module_to_reload is not None
        importlib.reload(module_to_reload)
    spec: Optional[importlib.machinery.ModuleSpec] = importlib.util.find_spec(python_module)
    assert spec is not None
    assert spec.loader is not None
    assert isinstance(spec.loader, loader.PluginModuleLoader) == prefer_finder

    # verify that import works and imports the correct module
    mod: ModuleType
    if reload:
        assert module_to_reload is not None
        mod = module_to_reload
    else:
        mod = importlib.import_module(python_module)
    assert mod.where == "libs" if prefer_finder else "venv"


def test_code_loader_prefer_finder(tmpdir: py.path.local, deactive_venv) -> None:
    """
    Verify that the agent code loader prefers its loaded code over code in the Python venv.
    """
    loader.PluginModuleFinder.reset()
    assert not isinstance(sys.meta_path[0], loader.PluginModuleFinder)
    loader.CodeLoader(code_dir=str(tmpdir))
    # it suffices to verify that the module finder is first in the meta path:
    # `test_plugin_module_finder` verifies the actual loader behavior
    assert isinstance(sys.meta_path[0], loader.PluginModuleFinder)


def test_venv_path(tmpdir: py.path.local, projects_dir: str, deactive_venv):
    original_project_dir: str = os.path.join(projects_dir, "plugins_project")
    project_dir = os.path.join(tmpdir, "plugins_project")
    shutil.copytree(original_project_dir, project_dir)

    def load_project(venv_path: str) -> None:
        project: Project = Project(project_dir, venv_path=venv_path)
        Project.set(project)
        # don't load full project, only AST so we don't have to deal with module finder cleanup
        project.install_modules()

    # Use non-default venv dir
    non_default_venv_dir = os.path.join(project_dir, "non-default-venv-dir")
    assert not os.path.exists(non_default_venv_dir)
    load_project(venv_path=non_default_venv_dir)
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


def test_module_loader(module_path: str, capsys, modules_dir: str):
    """
    Verify that the loader.PluginModuleFinder and loader.PluginModuleLoader load modules correctly.
    """
    origin_mod_dir = os.path.join(modules_dir, "submodule")
    mod_dir = os.path.join(module_path, os.path.basename(origin_mod_dir))
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


def test_module_unload(module_path: str, modules_dir: str) -> None:
    """
    Verify that the unload_inmanta_plugins function correctly unloads modules.
    """
    for mod in ["submodule", "elaboratev1module"]:
        origin_mod_dir = os.path.join(modules_dir, mod)
        mod_dir = os.path.join(module_path, os.path.basename(origin_mod_dir))
        shutil.copytree(origin_mod_dir, mod_dir)

    import inmanta_plugins.elaboratev1module  # noqa: F401
    import inmanta_plugins.submodule.submod  # noqa: F401

    assert "inmanta_plugins" in sys.modules
    assert "inmanta_plugins.elaboratev1module" in sys.modules
    assert "inmanta_plugins.submodule" in sys.modules
    assert "inmanta_plugins.submodule.submod" in sys.modules

    loader.unload_inmanta_plugins("submodule")

    assert "inmanta_plugins" in sys.modules
    assert "inmanta_plugins.elaboratev1module" in sys.modules

    assert "inmanta_plugins.submodule" not in sys.modules
    assert "inmanta_plugins.submodule.submod" not in sys.modules

    # make sure that it does not fail on a module with no plugins
    loader.unload_inmanta_plugins("doesnotexist")

    assert "inmanta_plugins" in sys.modules
    assert "inmanta_plugins.elaboratev1module" in sys.modules

    loader.unload_inmanta_plugins()

    assert "inmanta_plugins" not in sys.modules
    assert "inmanta_plugins.elaboratev1module" not in sys.modules


def test_plugin_loading_on_project_load(tmpdir, capsys, deactive_venv):
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

    project = Project(tmpdir, autostd=False, venv_path=os.path.join(tmpdir, ".env"))
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
