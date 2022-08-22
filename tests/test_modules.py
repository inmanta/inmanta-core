"""
    Copyright 2017 Inmanta

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

import logging
import os
import shutil
import tempfile
import unittest
from importlib.abc import Loader
from typing import List, Mapping, Optional, Tuple, Type
from unittest import mock

import py
import pytest

from _io import StringIO
from inmanta import const, env, module
from inmanta.ast import CompilerException
from inmanta.compiler.help.explainer import ExplainerFactory
from inmanta.env import LocalPackagePath
from inmanta.loader import PluginModuleFinder, PluginModuleLoader
from inmanta.module import InmantaModuleRequirement
from inmanta.moduletool import ModuleTool
from utils import module_from_template


def test_module():
    good_mod_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "modules", "mod1")
    module.ModuleV1(project=mock.Mock(), path=good_mod_dir)


def test_bad_module():
    bad_mod_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "modules", "mod2")
    with pytest.raises(module.ModuleMetadataFileNotFound):
        module.ModuleV1(project=mock.Mock(), path=bad_mod_dir)


class TestModuleName(unittest.TestCase):
    def __init__(self, methodName="runTest"):  # noqa: N803
        unittest.TestCase.__init__(self, methodName)

        self.stream = None
        self.handler = None
        self.log = None

    def setUp(self):
        self.stream = StringIO()
        self.handler = logging.StreamHandler(self.stream)
        self.log = logging.getLogger(module.__name__)

        for handler in self.log.handlers:
            self.log.removeHandler(handler)

        self.log.addHandler(self.handler)

    def test_wrong_name(self):
        mod_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "modules", "mod3")
        module.ModuleV1(project=mock.Mock(), path=mod_dir)

        self.handler.flush()
        assert "The name in the module file (mod1) does not match the directory name (mod3)" in self.stream.getvalue().strip()

    def test_non_matching_name_v2_module(self) -> None:
        """
        Make sure the warning regarding directory name does not trigger for v2 modules, as it is not relevant there.
        """
        template_dir: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "modules_v2", "minimalv2module")
        with tempfile.TemporaryDirectory() as tmpdir:
            mod_dir: str = os.path.join(tmpdir, "not-the-module-name")
            module_from_template(template_dir, mod_dir)
            module.ModuleV2(project=module.DummyProject(), path=mod_dir)
            self.handler.flush()
            assert self.stream.getvalue().strip() == ""

    def tearDown(self):
        self.log.removeHandler(self.handler)
        self.handler.close()


def test_to_v2():
    """
    Test whether the `to_v2()` method of `ModuleV1Metadata` works correctly.
    """
    v1_metadata = module.ModuleV1Metadata(
        name="a_test_module",
        description="A description",
        version="1.2.3",
        license="Apache 2.0",
        compiler_version="4.5.6",
        requires=["module_dep_1", "module_dep_2"],
    )
    v2_metadata = v1_metadata.to_v2()
    for attr_name in ["description", "version", "license"]:
        assert v1_metadata.__getattribute__(attr_name) == v2_metadata.__getattribute__(attr_name)

    def _convert_module_to_package_name(module_name: str) -> str:
        return f"{module.ModuleV2.PKG_NAME_PREFIX}{module_name.replace('_', '-')}"

    assert _convert_module_to_package_name(v1_metadata.name) == v2_metadata.name
    assert [_convert_module_to_package_name(req) for req in v1_metadata.requires] == v2_metadata.install_requires


@pytest.mark.slowtest
def test_is_versioned(snippetcompiler_clean, modules_dir: str, modules_v2_dir: str, caplog, tmpdir) -> None:
    """
    Test whether the warning regarding non-versioned modules is given correctly.
    """
    # Disable modules_dir
    snippetcompiler_clean.modules_dir = None

    def compile_and_assert_warning(
        module_name: str, needs_versioning_warning: bool, install_v2_modules: List[LocalPackagePath] = []
    ) -> None:
        caplog.clear()
        snippetcompiler_clean.setup_for_snippet(f"import {module_name}", autostd=False, install_v2_modules=install_v2_modules)
        snippetcompiler_clean.do_export()
        warning_message = f"Module {module_name} is not version controlled, we recommend you do this as soon as possible."
        assert (warning_message in caplog.text) is needs_versioning_warning

    # V1 module
    module_name_v1 = "mod1"
    module_dir = os.path.join(modules_dir, module_name_v1)
    module_copy_dir = os.path.join(snippetcompiler_clean.libs, module_name_v1)
    shutil.copytree(module_dir, module_copy_dir)
    dot_git_dir = os.path.join(module_copy_dir, ".git")
    assert not os.path.exists(dot_git_dir)
    compile_and_assert_warning(module_name_v1, needs_versioning_warning=True)
    os.mkdir(dot_git_dir)
    compile_and_assert_warning(module_name_v1, needs_versioning_warning=False)

    # V2 module
    module_name_v2 = "elaboratev2module"
    module_dir = os.path.join(modules_v2_dir, module_name_v2)
    module_copy_dir = os.path.join(tmpdir, module_name_v2)
    shutil.copytree(module_dir, module_copy_dir)
    dot_git_dir = os.path.join(module_copy_dir, ".git")
    assert not os.path.exists(dot_git_dir)
    # Non-editable install can never be checked for versioning
    compile_and_assert_warning(
        module_name_v2,
        needs_versioning_warning=False,
        install_v2_modules=[LocalPackagePath(path=module_copy_dir, editable=False)],
    )
    compile_and_assert_warning(
        module_name_v2,
        needs_versioning_warning=True,
        install_v2_modules=[LocalPackagePath(path=module_copy_dir, editable=True)],
    )
    os.mkdir(dot_git_dir)
    # Non-editable install can never be checked for versioning
    compile_and_assert_warning(
        module_name_v2,
        needs_versioning_warning=False,
        install_v2_modules=[LocalPackagePath(path=module_copy_dir, editable=False)],
    )
    compile_and_assert_warning(
        module_name_v2,
        needs_versioning_warning=False,
        install_v2_modules=[LocalPackagePath(path=module_copy_dir, editable=True)],
    )


@pytest.mark.parametrize(
    "v1_module, all_python_requirements,strict_python_requirements,module_requirements,module_v2_requirements",
    [
        (
            True,
            ["jinja2~=3.2.1", "inmanta-module-v2-module==1.2.3"],
            ["jinja2~=3.2.1"],
            ["v2_module==1.2.3", "v1_module==1.1.1"],
            [InmantaModuleRequirement.parse("v2_module==1.2.3")],
        ),
        (
            False,
            ["jinja2~=3.2.1", "inmanta-module-v2-module==1.2.3"],
            ["jinja2~=3.2.1"],
            ["v2_module==1.2.3"],
            [InmantaModuleRequirement.parse("v2_module==1.2.3")],
        ),
    ],
)
def test_get_requirements(
    modules_dir: str,
    modules_v2_dir: str,
    v1_module: bool,
    all_python_requirements: List[str],
    strict_python_requirements: List[str],
    module_requirements: List[str],
    module_v2_requirements: List[str],
) -> None:
    """
    Test the different methods to get the requirements of a module.
    """
    module_name = "many_dependencies"

    if v1_module:
        module_dir = os.path.join(modules_dir, module_name)
        mod = module.ModuleV1(module.DummyProject(autostd=False), module_dir)
    else:
        module_dir = os.path.join(modules_v2_dir, module_name)
        mod = module.ModuleV2(module.DummyProject(autostd=False), module_dir)

    assert set(mod.get_all_python_requirements_as_list()) == set(all_python_requirements)
    assert set(mod.get_strict_python_requirements_as_list()) == set(strict_python_requirements)
    assert set(mod.get_module_requirements()) == set(module_requirements)
    assert set(mod.get_module_v2_requirements()) == set(module_v2_requirements)
    assert set(mod.requires()) == set(module.InmantaModuleRequirement.parse(req) for req in module_requirements)


@pytest.mark.parametrize("editable", [True, False])
def test_module_v2_source_get_installed_module_editable(
    # Use clean snippetcompiler (separate venv) because this test installs test packages into the snippetcompiler venv.
    snippetcompiler_clean,
    modules_v2_dir: str,
    editable: bool,
) -> None:
    """
    Make sure ModuleV2Source.get_installed_module identifies editable installations correctly.
    """
    module_name: str = "minimalv2module"
    module_dir: str = os.path.join(modules_v2_dir, module_name)
    snippetcompiler_clean.setup_for_snippet(
        f"import {module_name}",
        autostd=False,
        install_v2_modules=[env.LocalPackagePath(path=module_dir, editable=editable)],
    )

    source: module.ModuleV2Source = module.ModuleV2Source(urls=[])
    mod: Optional[module.ModuleV2] = source.get_installed_module(module.DummyProject(autostd=False), module_name)
    assert mod is not None
    # os.path.realpath because snippetcompiler uses symlinks
    assert os.path.realpath(mod.path) == (
        module_dir if editable else os.path.join(env.process_env.site_packages_dir, "inmanta_plugins", module_name)
    )
    assert mod._is_editable_install == editable


def test_module_v2_source_path_for_v1(snippetcompiler) -> None:
    """
    Make sure ModuleV2Source.path_for does not include modules loaded by the v1 module loader.
    """
    # install and load std as v1
    snippetcompiler.setup_for_snippet("import std")
    module.Project.get().load_plugins()

    # make sure the v1 module finder is configured and discovered by env.process_env
    assert PluginModuleFinder.MODULE_FINDER is not None
    module_info: Optional[Tuple[Optional[str], Loader]] = env.process_env.get_module_file("inmanta_plugins.std")
    assert module_info is not None
    path, loader = module_info
    assert path is not None
    assert isinstance(loader, PluginModuleLoader)

    source: module.ModuleV2Source = module.ModuleV2Source(urls=[])
    assert source.path_for("std") is None


def test_module_v2_from_v1_path(
    local_module_package_index: str,
    modules_v2_dir: str,
    snippetcompiler_clean,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Verify that attempting to load a v2 module from the v1 modules path fails with an appropriate message when a v2 module is
    found in a v1 module source.
    """
    with pytest.raises(module.ModuleLoadingException) as excinfo:
        snippetcompiler_clean.setup_for_snippet("import minimalv2module", add_to_module_path=[modules_v2_dir])
    cause: CompilerException = excinfo.value.__cause__
    assert cause.msg == (
        "Module at %s looks like a v2 module. Please have a look at the documentation on how to use v2 modules."
        % os.path.join(modules_v2_dir, "minimalv2module")
    )
    assert (
        ExplainerFactory().explain_and_format(excinfo.value, plain=True).strip()
        == (
            f"""
Exception explanation
=====================
This error occurs when a v2 module was found in v1 modules path. To resolve this you should either convert this module to be v1 or install it as a v2 module and set up your project accordingly.

If you want to use the module as a v1 module, make sure to use the v1 cookiecutter template to create new modules.

If you want to use the module as a v2 module:
- set up your project with a module source of type "package" (see documentation)
- if you would like to work in editable mode on a local copy of the module, run `inmanta module install -e {modules_v2_dir}/minimalv2module`
- run `inmanta module add --v2 minimalv2module` to add the module as a dependency and to install the module if required.
        """  # noqa: E501
        ).strip()
    )

    # verify that adding it as a v2 resolves the issue
    project: module.Project = snippetcompiler_clean.setup_for_snippet(
        "",
        autostd=False,
        python_package_sources=[local_module_package_index],
        install_project=False,
    )
    os.chdir(project.path)
    project_init = module.Project.__init__

    # patch Project.__init__ to set autostd=False because v2 std does not exist yet
    def project_init_nostd(self, *args, **kwargs) -> None:
        project_init(self, *args, autostd=False, **{key: value for key, value in kwargs.items() if key != "autostd"})

    monkeypatch.setattr(module.Project, "__init__", project_init_nostd)
    ModuleTool().add("minimalv2module", v2=True)
    snippetcompiler_clean.setup_for_snippet(
        "import minimalv2module",
        autostd=False,
        # run with the same module path
        add_to_module_path=[modules_v2_dir],
        python_package_sources=[local_module_package_index],
        install_project=True,
    )


@pytest.mark.slowtest
def test_module_v2_incorrect_install_warning(
    tmpdir: py.path.local,
    modules_v2_dir: str,
    snippetcompiler_clean,
    caplog,
) -> None:
    """
    Verify that attempting to load a v2 module that has been installed from source with `pip install` rather than
    `inmanta module install` results in an appropriate error or warning.
    """
    # set up project and activate project venv
    snippetcompiler_clean.setup_for_snippet("")

    # prepare module
    module_dir: str = str(tmpdir.join("mymodule"))
    shutil.copytree(os.path.join(modules_v2_dir, "minimalv2module"), module_dir)

    def verify_exception(expected: Optional[str]) -> None:
        """
        Verify AST loading fails with the expected message, or succeeds if expected is None.
        """
        if expected is None:
            snippetcompiler_clean.setup_for_snippet("import minimalv2module", autostd=False)
            return
        with pytest.raises(module.ModuleLoadingException) as excinfo:
            snippetcompiler_clean.setup_for_snippet("import minimalv2module", autostd=False)
        cause: CompilerException = excinfo.value.__cause__
        assert cause.msg == expected

    # install module from source without using `inmanta module install`
    env.process_env.install_from_source([env.LocalPackagePath(path=module_dir, editable=False)])
    module_path = os.path.join(env.process_env.site_packages_dir, const.PLUGINS_PACKAGE, "minimalv2module")
    verify_exception(
        f"Invalid module at {module_path}: found module package but it has no setup.cfg. "
        "This occurs when you install or build modules from"
        " source incorrectly. Always use the `inmanta module install` and `inmanta module build` commands to respectively"
        " install and build modules from source. Make sure to uninstall the broken package first."
    )

    # include setup.cfg in package to circumvent error
    shutil.copy(os.path.join(module_dir, "setup.cfg"), os.path.join(module_dir, const.PLUGINS_PACKAGE, "minimalv2module"))
    env.process_env.install_from_source([env.LocalPackagePath(path=module_dir, editable=False)])
    verify_exception(
        "The module at %s contains no _init.cf file. This occurs when you install or build modules from source"
        " incorrectly. Always use the `inmanta module install` and `inmanta module build` commands to respectively install and"
        " build modules from source. Make sure to uninstall the broken package first." % module_path
    )
    os.remove(os.path.join(module_dir, const.PLUGINS_PACKAGE, "minimalv2module", "setup.cfg"))

    # verify that proposed solution works: editable install doesn't require uninstall first
    ModuleTool().install(editable=True, path=module_dir)
    verify_exception(None)


def test_from_path(tmpdir: py.path.local, projects_dir: str, modules_dir: str, modules_v2_dir: str) -> None:
    """
    Verify that ModuleLike.from_path() and subclass overrides work as expected.
    """

    def check(
        path: str,
        *,
        subdir: Optional[str] = None,
        expected: Mapping[Type[module.ModuleLike], Optional[Type[module.ModuleLike]]],
    ) -> None:
        """
        Check the functionality for the given path and expected outcomes.

        :param path: The path to the root of the module like directory.
        :param subdir: The subpath to pass to `from_path`, relative to `path`.
        :param expected: Key-value pairs where keys represent the classes to call the method on and values the expected type
            for the return value.
        """
        full_path: str = os.path.join(path, *([subdir] if subdir is not None else []))
        for cls, tp in expected.items():
            result: Optional[module.ModuleLike] = cls.from_path(full_path)
            assert (result is None) is (tp is None)
            if tp is not None:
                assert isinstance(result, tp)
                assert result.path == path

    # project checks
    check(
        os.path.join(projects_dir, "simple_project"),
        expected={
            module.ModuleLike: module.Project,
            module.Project: module.Project,
            module.Module: None,
            module.ModuleV1: None,
            module.ModuleV2: None,
        },
    )

    # module v1 checks
    check(
        os.path.join(modules_dir, "minimalv1module"),
        expected={
            module.ModuleLike: module.ModuleV1,
            module.Project: None,
            module.Module: module.ModuleV1,
            module.ModuleV1: module.ModuleV1,
            module.ModuleV2: None,
        },
    )

    # module v2 checks
    check(
        os.path.join(modules_v2_dir, "minimalv2module"),
        expected={
            module.ModuleLike: module.ModuleV2,
            module.Project: None,
            module.Module: module.ModuleV2,
            module.ModuleV1: None,
            module.ModuleV2: module.ModuleV2,
        },
    )

    check(str(tmpdir), expected={module.ModuleLike: None})

    # advanced setup: project with modules in libs dir
    project_dir: str = str(tmpdir.join("project"))
    shutil.copytree(os.path.join(projects_dir, "simple_project"), project_dir)
    libs_dir: str = os.path.join(project_dir, "libs")
    os.makedirs(libs_dir, exist_ok=True)
    module_dir: str = os.path.join(libs_dir, "minimalv1module")
    shutil.copytree(os.path.join(modules_dir, "minimalv1module"), module_dir)
    check(module_dir, expected={module.ModuleLike: module.ModuleV1})
    check(libs_dir, expected={module.ModuleLike: None})
    check(project_dir, expected={module.ModuleLike: module.Project})
