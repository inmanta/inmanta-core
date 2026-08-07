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
import logging
import os
import shutil
import sys
from collections.abc import Iterator
from configparser import ConfigParser
from logging import DEBUG
from types import ModuleType
from typing import Optional

import py
import pytest
from pytest import fixture

import utils
from inmanta import compiler, const, env, loader, moduletool
from inmanta.data.model import InmantaModule, ModuleSourceMetadata
from inmanta.env import PipConfig
from inmanta.loader import ModuleSource, SourceNotFoundException
from inmanta.module import Project
from inmanta.resources import Id


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


@fixture(scope="function")
def plugins_project(tmpdir: py.path.local, deactive_venv) -> Iterator[Project]:
    """
    A project with the single_plugin_file and multiple_plugin_files v2 modules loaded. All modules in the project's libs
    directory are installed in editable mode. non_imported_plugin_file is installed but deliberately not loaded.
    """
    original_project_dir: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "plugins_project")
    project_dir = os.path.join(tmpdir, "plugins_project")
    shutil.copytree(original_project_dir, project_dir)
    project: Project = Project(project_dir, venv_path=os.path.join(project_dir, ".env"))

    Project.set(project)

    project.use_virtual_env()
    # The plugin modules are v2 modules, installed editable from the project's libs directory.
    for module_name in ("single_plugin_file", "multiple_plugin_files", "non_imported_plugin_file"):
        project.virtualenv.install_for_config(
            requirements=[],
            paths=[env.LocalPackagePath(path=os.path.join(project_dir, "libs", module_name), editable=True)],
            config=PipConfig(use_system_config=True),
        )

    project.load()

    project.load_module("single_plugin_file")
    project.load_module("multiple_plugin_files")

    yield project


def test_code_manager(plugins_project: Project):
    """Verify the code manager"""
    expected_dependencies = {"inmanta-module-std", "lorem"}

    # non_imported_plugin_file was not loaded in the project
    # we check that a warning is produced when we attempt to register
    # some of its code

    import inmanta_plugins.multiple_plugin_files.handlers as multi
    import inmanta_plugins.non_imported_plugin_file as non_imported
    import inmanta_plugins.single_plugin_file as single

    mgr = loader.CodeManager(resources={})
    mgr.register_code(
        "std::testing::NullResource",
        single.MyHandler,
    )
    mgr.register_code(
        "multiple_plugin_files::NullResourceBis",
        multi.MyHandler,
    )

    with pytest.raises(SourceNotFoundException) as excinfo:
        mgr.register_code(
            "non_imported_plugin_file::NullResourceBis",
            non_imported.MyHandler,
        )

    exception_message = (
        "Module non_imported_plugin_file is imported in plugin code but not in model code. "
        "Either remove the unused import, or make sure to import the module in model code."
    )
    assert exception_message in str(excinfo.value)

    module_version_info = mgr.get_module_version_info()
    assert "multiple_plugin_files" in module_version_info.keys()
    assert "single_plugin_file" in module_version_info.keys()

    # The python requirements of a module are not transported: they are declared in its setup.cfg, which is persisted so
    # that the agent can reconstruct the module as an installable python package and let pip resolve them.
    single_plugin_file: InmantaModule = module_version_info["single_plugin_file"]
    assert single_plugin_file.requirements is None
    assert single_plugin_file.setup_cfg_hash is not None
    setup_cfg = ConfigParser()
    setup_cfg.read_string(mgr.get_file_content(single_plugin_file.setup_cfg_hash).decode())
    assert set(setup_cfg["options"]["install_requires"].split()) == expected_dependencies

    assert len(single_plugin_file.python_files_metadata) == 1
    assert len(module_version_info["multiple_plugin_files"].python_files_metadata) == 3

    with pytest.raises(KeyError):
        mgr.get_file_content("test")

    # register type without source
    with pytest.raises(loader.SourceNotFoundException):
        mgr.register_code(
            "test2",
            str,
        )


def test_code_manager_agents_for_multiple_resource_types(plugins_project: Project, monkeypatch) -> None:
    """
    Verify that the load set of an Inmanta module accumulates over all register_code() calls for that module. The
    multiple_plugin_files module provides a handler for both NullResourceBis and NullResourceTer. Each of those resource
    types is managed by a different agent, so both agents have to load the module.
    """
    import inmanta_plugins.multiple_plugin_files.handlers as multi

    resources = [
        Id("multiple_plugin_files::NullResourceBis", "agent1", "name", "resource1"),
        Id("multiple_plugin_files::NullResourceTer", "agent2", "name", "resource2"),
        # No code of multiple_plugin_files is registered for this type, so agent3 doesn't have to load it.
        Id("std::testing::NullResource", "agent3", "name", "resource3"),
    ]

    def register_handlers() -> InmantaModule:
        mgr = loader.CodeManager(resources=resources)
        mgr.register_code("multiple_plugin_files::NullResourceBis", multi.MyHandler)
        mgr.register_code("multiple_plugin_files::NullResourceTer", multi.MyHandlerTer)
        return mgr.get_module_version_info()["multiple_plugin_files"]

    # [editable install mode]
    module_info = register_handlers()
    assert module_info.editable_install
    assert sorted(module_info.load_module_on_agents) == ["agent1", "agent2"]

    # [package install mode] pretend none of the modules in this project were installed in editable mode
    monkeypatch.setattr(Project, "get_editable_installed_inmanta_modules", lambda self: [])

    module_info = register_handlers()
    assert not module_info.editable_install
    assert sorted(module_info.load_module_on_agents) == ["agent1", "agent2"]


def test_code_manager_v1_module(snippetcompiler) -> None:
    """
    A V1 module is not distributed as a python package, so the agent can not install it with pip. Its source always has to
    be transported, like the source of a V2 module installed in editable mode.
    """
    snippetcompiler.setup_for_snippet(
        """
        import successhandlermodule

        successhandlermodule::SuccessResource(name="test", agent="agent1")
        """,
        autostd=True,
    )
    compiler.do_compile()

    import inmanta_plugins.successhandlermodule as v1_module

    resources = [
        Id("successhandlermodule::SuccessResource", "agent1", "name", "test"),
        # No code of successhandlermodule is registered for this type, so agent2 doesn't have to load it
        Id("std::testing::NullResource", "agent2", "name", "other"),
    ]
    mgr = loader.CodeManager(resources=resources)
    mgr.register_code("successhandlermodule::SuccessResource", v1_module.SuccessResourceHandler)

    module_info = mgr.get_module_version_info()["successhandlermodule"]
    assert module_info.editable_install
    # The source of the module and its requirements are transported, no pip requirement is registered for the module
    assert module_info.files_in_module
    assert module_info.requirements is not None

    # agent2 does not manage a resource type of this module, so it does not load it. The server derives from
    # editable_install that the source still has to be installed on it.
    assert sorted(module_info.load_module_on_agents) == ["agent1"]


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
    Verify that the agent code loader prefers its loaded code over code in the Python venv. The finder is configured
    lazily, when the first module source is installed on disk (the old-style / iso9 install path), not on construction.
    """
    loader.PluginModuleFinder.reset()
    assert not isinstance(sys.meta_path[0], loader.PluginModuleFinder)
    cl = loader.CodeLoader(code_dir=str(tmpdir))
    # Constructing the code loader does not configure the finder: the new-style (iso10) load path imports from the venv.
    assert not isinstance(sys.meta_path[0], loader.PluginModuleFinder)
    # Installing a module source on disk configures the finder.
    cl.deploy_version([get_module_source("inmanta_plugins.my_module", "value = 1")])
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
        # This test only verifies venv path handling, so just create the venv without installing modules.
        project.use_virtual_env()

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
    stdout, stderr = capsys.readouterr()
    assert stdout.count("#loading inmanta_plugins.submodule#") == 1
    assert stdout.count("#loading inmanta_plugins.submodule.submod#") == 0
    assert stdout.count("#loading inmanta_plugins.submodule.pkg#") == 0
    assert stdout.count("#loading inmanta_plugins.submodule.pkg.submod2#") == 0

    from inmanta_plugins.submodule.submod import test_submod

    assert test_submod() == "test_submod"
    stdout, stderr = capsys.readouterr()
    assert stdout.count("#loading inmanta_plugins.submodule#") == 0
    assert stdout.count("#loading inmanta_plugins.submodule.submod#") == 1
    assert stdout.count("#loading inmanta_plugins.submodule.pkg#") == 0
    assert stdout.count("#loading inmanta_plugins.submodule.pkg.submod2#") == 0

    from inmanta_plugins.submodule.pkg import test_pkg

    assert test_pkg() == "test_pkg -- test_submod2"
    stdout, stderr = capsys.readouterr()
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
    project_yml.write("""
name: test
modulepath: libs
downloadpath: libs
repo: https://github.com/inmanta/inmanta.git
install_mode: master
    """)

    tmpdir.mkdir("libs")
    origin_mod_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "modules", "submodule")
    mod_dir = tmpdir.join("libs", os.path.basename(origin_mod_dir))
    shutil.copytree(origin_mod_dir, mod_dir)

    project = Project(tmpdir, autostd=False, venv_path=os.path.join(tmpdir, ".env"))
    Project.set(project)
    project.load()

    stdout, stderr = capsys.readouterr()
    assert stdout.count("#loading inmanta_plugins.submodule#") == 1
    assert stdout.count("#loading inmanta_plugins.submodule.submod#") == 1
    assert stdout.count("#loading inmanta_plugins.submodule.pkg#") == 1
    assert stdout.count("#loading inmanta_plugins.submodule.pkg.submod2#") == 1

    from inmanta_plugins.submodule import test

    assert test() == "test"
    stdout, stderr = capsys.readouterr()
    assert "#loading" not in stdout

    from inmanta_plugins.submodule.submod import test_submod

    assert test_submod() == "test_submod"
    stdout, stderr = capsys.readouterr()
    assert "#loading" not in stdout

    from inmanta_plugins.submodule.pkg import test_pkg

    assert test_pkg() == "test_pkg -- test_submod2"
    stdout, stderr = capsys.readouterr()
    assert "#loading" not in stdout


def test_plugin_loading_old_format(tmpdir, capsys):
    """
    Ensure the code loader ignores code formatted in the old on disk format (pre Inmanta 2020.4).
    (See issue: #2162)
    """
    # Create directory structure code dir
    modules_dir = tmpdir.join(loader.MODULE_DIR)
    modules_dir.mkdir()

    # Create source files using pre Inmanta 2020.4 format
    old_format_source_file = modules_dir.join("inmanta_plugins.old_format.py")
    old_format_source_file.write("")

    # Set up the plugin module finder to resolve modules from the on-disk code dir, as the old-style (iso9) install path
    # does. CodeLoader no longer configures the finder on construction; it is configured when code is installed on disk.
    loader.PluginModuleFinder.reset()
    loader.PluginModuleFinder.configure_module_finder(modulepaths=[str(modules_dir)], prefer=True)

    # Assert code using the pre inmanta 2020.4 format is ignored
    with pytest.raises(ImportError):
        import inmanta_plugins.old_format  # NOQA

    # Add newly formatted code next the pre Inmanta 2020.4 format
    new_format_mod_dir = modules_dir.join("new_format")
    new_format_mod_dir.mkdir()
    new_format_plugins_dir = new_format_mod_dir.join("plugins")
    new_format_plugins_dir.mkdir()
    new_format_source_file = new_format_plugins_dir.join("__init__.py")
    new_format_source_file.write("""
def test():
    return 10
    """)

    # Assert newly formatted code is loaded and code using the pre inmanta 2020.4 format is ignored
    import inmanta_plugins.new_format as mod  # NOQA

    assert mod.test() == 10
    with pytest.raises(ImportError):
        import inmanta_plugins.old_format  # NOQA


def test_convert_module_to_editable_relative_path():
    """
    The reconstruction path helper materializes each python module as a package (a directory with an __init__ file),
    honoring the byte-code flag, and never produces a path for the top-level inmanta_plugins namespace package itself.
    """
    assert (
        loader.convert_module_to_editable_relative_path("inmanta_plugins.my_mod", is_byte_code=False)
        == "inmanta_plugins/my_mod/__init__.py"
    )
    assert (
        loader.convert_module_to_editable_relative_path("inmanta_plugins.my_mod.my_submod", is_byte_code=False)
        == "inmanta_plugins/my_mod/my_submod/__init__.py"
    )
    assert (
        loader.convert_module_to_editable_relative_path("inmanta_plugins.my_mod.my_submod", is_byte_code=True)
        == "inmanta_plugins/my_mod/my_submod/__init__.pyc"
    )
    with pytest.raises(Exception, match="not part of the inmanta_plugins package"):
        loader.convert_module_to_editable_relative_path("some.other.package", is_byte_code=False)


def test_deploy_and_load_on_disk_code_install(tmp_path, caplog):
    """
    The on disk code install writes every transported source to disk and imports all of them. Import failures are
    recorded per module without preventing the healthy modules from loading.
    """
    caplog.set_level(DEBUG)
    cl = loader.CodeLoader(tmp_path)

    healthy = get_module_source("inmanta_plugins.on_disk_ok", "value = 42")
    broken = get_module_source("inmanta_plugins.on_disk_broken", "raise RuntimeError('boom')")

    failed = cl.deploy_and_load(
        [],
        logging.getLogger(__name__).getChild("agent1"),
        on_disk_code_install=loader.OnDiskCodeInstall(module_sources=[healthy, broken]),
    )

    # The healthy module was written to disk and imported from there.
    import inmanta_plugins.on_disk_ok  # NOQA

    assert inmanta_plugins.on_disk_ok.value == 42
    assert sorted(os.listdir(cl.mod_dir)) == ["on_disk_broken", "on_disk_ok"]

    # Only the broken import is reported, keyed by inmanta module name -> python module name.
    assert set(failed) == {"on_disk_broken"}
    assert set(failed["on_disk_broken"]) == {"inmanta_plugins.on_disk_broken"}
    assert isinstance(failed["on_disk_broken"]["inmanta_plugins.on_disk_broken"], loader.ModuleImportException)


def test_list_python_files(tmp_path) -> None:
    """
    list_python_files returns every python file of a plugin directory, prefers byte code over source, and ignores the
    non-python content a v2 module ships inside its python package.
    """
    plugin_dir = tmp_path / "inmanta_plugins" / "my_mod"
    (plugin_dir / "sub").mkdir(parents=True)
    (plugin_dir / "__pycache__").mkdir()
    # Both a .py and a .pyc file exist for this python module: only the byte code is picked up
    (plugin_dir / "__init__.py").touch()
    (plugin_dir / "__init__.pyc").touch()
    (plugin_dir / "byte_code_only.pyc").touch()
    (plugin_dir / "sub" / "__init__.py").touch()
    (plugin_dir / "__pycache__" / "cached.py").touch()
    # A v2 module ships its non-python content inside its python package
    for non_python_dir in ("files", "templates"):
        (plugin_dir / non_python_dir / "nested").mkdir(parents=True)
        (plugin_dir / non_python_dir / "nested" / "not_a_plugin.py").touch()
    # A directory named model, files or templates that has an __init__ file is a python package rather than module
    # content, so its code is part of the module. This is what a plugin submodule model.py becomes once an editable
    # module has been reconstructed on the agent, where every python module is materialized as a package.
    (plugin_dir / "model").mkdir()
    (plugin_dir / "model" / "__init__.py").touch()
    # A directory whose name merely starts with one of those names is a regular python package
    (plugin_dir / "models").mkdir()
    (plugin_dir / "models" / "__init__.py").touch()
    # Only the top level directories are excluded: a nested one is a regular python package as well
    (plugin_dir / "sub" / "model").mkdir()
    (plugin_dir / "sub" / "model" / "__init__.py").touch()

    assert sorted(loader.list_python_files(str(plugin_dir))) == [
        str(plugin_dir / "__init__.pyc"),
        str(plugin_dir / "byte_code_only.pyc"),
        str(plugin_dir / "model" / "__init__.py"),
        str(plugin_dir / "models" / "__init__.py"),
        str(plugin_dir / "sub" / "__init__.py"),
        str(plugin_dir / "sub" / "model" / "__init__.py"),
    ]


def test_discover_installed_inmanta_module(plugins_project: Project) -> None:
    """
    The python files of an inmanta module installed in the active python environment can be discovered without any of
    its metadata being transported: the module name is enough.
    """
    plugin_dir: str = loader.get_installed_plugin_dir("multiple_plugin_files")
    assert plugin_dir == os.path.join(
        plugins_project.path, "libs", "multiple_plugin_files", "inmanta_plugins", "multiple_plugin_files"
    )

    discovered = dict(loader.discover_plugin_files(plugin_dir, "multiple_plugin_files"))
    assert set(discovered.values()) == {
        "inmanta_plugins.multiple_plugin_files",
        "inmanta_plugins.multiple_plugin_files.handlers",
        "inmanta_plugins.multiple_plugin_files.helpers",
    }
    # The discovered files are the ones that make up the module, not a reconstruction of them
    assert all(os.path.isfile(path) for path in discovered)

    with pytest.raises(SourceNotFoundException):
        loader.get_installed_plugin_dir("not_an_installed_module")


def test_deploy_and_load_from_venv(plugins_project: Project, tmp_path) -> None:
    """
    An inmanta module that the agent installed in its venv is loaded by discovering its python files there: no source is
    transported for it. This covers both install modes: multiple_plugin_files is installed in editable mode and
    single_plugin_file as a package.

    A module that is not installed is reported as a failure without affecting the others.
    """
    # The project fixture installs all the modules of this project in editable mode. Replace one of them by a package
    # install, so that both install modes are covered.
    plugins_project.virtualenv.install_for_config(
        requirements=[],
        paths=[env.LocalPackagePath(path=os.path.join(plugins_project.path, "libs", "single_plugin_file"), editable=False)],
        config=PipConfig(use_system_config=True),
    )

    # The legacy PluginModuleFinder plays no part in this load path. Reset the one the project configured, so that any
    # attempt to configure it during the load stands out. The deactive_venv fixture resets it again on teardown.
    loader.PluginModuleFinder.reset()

    cl = loader.CodeLoader(tmp_path)

    fq_module_names = [
        "inmanta_plugins.multiple_plugin_files",
        "inmanta_plugins.multiple_plugin_files.handlers",
        "inmanta_plugins.multiple_plugin_files.helpers",
        "inmanta_plugins.single_plugin_file",
    ]
    # The project fixture loaded these modules in this process, unload them to verify deploy_and_load imports them itself
    for inmanta_module_name in ("multiple_plugin_files", "single_plugin_file"):
        loader.unload_inmanta_plugins(inmanta_module_name)
    assert not any(fq_module_name in sys.modules for fq_module_name in fq_module_names)

    failed = cl.deploy_and_load(
        ["multiple_plugin_files", "single_plugin_file", "not_an_installed_module"],
        logging.getLogger(__name__).getChild("agent1"),
    )

    # All the python files of the installed modules were imported, even the ones no handler lives in
    assert all(fq_module_name in sys.modules for fq_module_name in fq_module_names)

    # Both install modes really are covered: the module installed in editable mode was imported from the checkout it is
    # installed from, the package installed one from the site packages of the venv.
    assert sys.modules["inmanta_plugins.multiple_plugin_files"].__file__.startswith(os.path.join(plugins_project.path, "libs"))
    assert sys.modules["inmanta_plugins.single_plugin_file"].__file__.startswith(plugins_project.virtualenv.site_packages_dir)

    # The code was imported straight from the venv: nothing was written to the on-disk module dir and the legacy finder
    # was never configured.
    assert os.listdir(cl.mod_dir) == []
    assert not any(isinstance(finder, loader.PluginModuleFinder) for finder in sys.meta_path)

    # The module that is not installed is reported against its top level python module: it has no known files
    assert set(failed) == {"not_an_installed_module"}
    assert set(failed["not_an_installed_module"]) == {"inmanta_plugins.not_an_installed_module"}
    assert isinstance(failed["not_an_installed_module"]["inmanta_plugins.not_an_installed_module"], SourceNotFoundException)
