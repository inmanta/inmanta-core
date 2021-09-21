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
import unittest
from importlib.abc import Loader
from typing import List, Optional, Tuple
from unittest import mock

import pytest

from _io import StringIO
from inmanta import env, module
from inmanta.env import LocalPackagePath
from inmanta.loader import PluginModuleFinder, PluginModuleLoader
from inmanta.module import InmantaModuleRequirement


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
    snippetcompiler,
    modules_v2_dir: str,
    editable: bool,
) -> None:
    """
    Make sure ModuleV2Source.get_installed_module identifies editable installations correctly.
    """
    module_name: str = "minimalv2module"
    module_dir: str = os.path.join(modules_v2_dir, module_name)
    snippetcompiler.setup_for_snippet(
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
