"""
    Copyright 2021 Inmanta

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
import shutil
from typing import Dict

import py.path
import pytest
from pkg_resources import Requirement

from inmanta.config import Config
from inmanta.env import LocalPackagePath, process_env
from inmanta.module import ModuleV2
from inmanta.moduletool import ModuleTool
from moduletool.common import PipIndex, add_file, clone_repo, module_from_template
from packaging.version import Version
from inmanta.parser import ParserException


@pytest.mark.parametrize(
    "kwargs_update_method, mod2_should_be_updated, mod8_should_be_updated",
    [({}, True, True), ({"module": "mod2"}, True, False), ({"module": "mod8"}, False, True)],
)
def test_module_update_with_install_mode_master(
    tmpdir, modules_repo, kwargs_update_method, mod2_should_be_updated, mod8_should_be_updated
):
    # Make a copy of masterproject_multi_mod
    masterproject_multi_mod = tmpdir.join("masterproject_multi_mod")
    clone_repo(modules_repo, "masterproject_multi_mod", tmpdir)
    libs_folder = os.path.join(masterproject_multi_mod, "libs")
    os.mkdir(libs_folder)

    # Set masterproject_multi_mod as current project
    os.chdir(masterproject_multi_mod)
    Config.load_config()

    # Dependencies masterproject_multi_mod
    for mod in ["mod2", "mod8"]:
        # Clone mod in root tmpdir
        clone_repo(modules_repo, mod, tmpdir)

        # Clone mod from root of tmpdir into libs folder of masterproject_multi_mod
        clone_repo(tmpdir, mod, libs_folder)

        # Update module in root of tmpdir by adding an extra file
        file_name_extra_file = "test_file"
        path_mod = os.path.join(tmpdir, mod)
        add_file(path_mod, file_name_extra_file, "test", "Second commit")

        # Assert test_file not present in libs folder of masterproject_multi_mod
        path_extra_file = os.path.join(libs_folder, mod, file_name_extra_file)
        assert not os.path.exists(path_extra_file)

    # Update module(s) of masterproject_multi_mod
    ModuleTool().update(**kwargs_update_method)

    # Assert availability of test_file in masterproject_multi_mod
    extra_file_mod2 = os.path.join(libs_folder, "mod2", file_name_extra_file)
    assert os.path.exists(extra_file_mod2) == mod2_should_be_updated
    extra_file_mod8 = os.path.join(libs_folder, "mod8", file_name_extra_file)
    assert os.path.exists(extra_file_mod8) == mod8_should_be_updated


@pytest.mark.parametrize("corrupt_module", [True, False])
def test_module_update_with_v2_module(
    tmpdir: py.path.local, modules_v2_dir: str, snippetcompiler_clean, corrupt_module: bool
) -> None:
    """
    Assert that the `inmanta module update` command works correctly when executed on a project with a V2 module.

    :param corrupt_module: Whether the module to be updated contains a syntax error or not.
    """
    module_name = "elaboratev2module"
    original_elaboratev2module_dir = os.path.join(modules_v2_dir, module_name)  # Has version 1.2.3
    patched_elaboratev2module_dir = os.path.join(tmpdir, module_name)
    shutil.copytree(original_elaboratev2module_dir, patched_elaboratev2module_dir)

    if corrupt_module:
        model_file = os.path.join(patched_elaboratev2module_dir, "model", "_init.cf")
        with open(model_file, "w", encoding="utf-8") as fd:
            # Introduce syntax error in the module
            fd.write("""
entity:
    string message
end
            """)

    def assert_version_installed(module_name: str, version: str) -> None:
        package_name = ModuleV2.get_package_name_for(module_name)
        installed_packages: Dict[str, Version] = process_env.get_installed_packages()
        assert package_name in installed_packages
        assert str(installed_packages[package_name]) == version

    pip_index = PipIndex(artifact_dir=os.path.join(str(tmpdir), "pip-index"))
    for version in ["1.2.4", "1.2.5"]:
        mod_dir = os.path.join(tmpdir, f"elaboratev2module-v{version}")
        module_from_template(
            source_dir=original_elaboratev2module_dir,
            dest_dir=mod_dir,
            new_version=Version(version),
            install=False,
            publish_index=pip_index,
        )

    snippetcompiler_clean.setup_for_snippet(
        snippet="import elaboratev2module",
        autostd=False,
        install_v2_modules=[LocalPackagePath(path=patched_elaboratev2module_dir)],
        python_package_sources=[pip_index.url],
        project_requires=[Requirement.parse(f"{module_name}<1.2.5")],
    )

    assert_version_installed(module_name=module_name, version="1.2.3")
    ModuleTool().update()
    assert_version_installed(module_name=module_name, version="1.2.4")


# TODO:
#  * Test constraint at module level instead of only the project level
#  * Test constraint on V1 module

def test_module_update_syntax_error_in_project(
    tmpdir: py.path.local, modules_v2_dir: str, snippetcompiler_clean
) -> None:
    snippetcompiler_clean.setup_for_snippet(snippet="entity", autostd=False)
    with pytest.raises(ParserException):
        ModuleTool().update()
