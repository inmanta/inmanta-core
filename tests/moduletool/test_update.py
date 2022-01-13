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
from typing import Dict, Optional

import py.path
import pytest
from pkg_resources import Requirement

from inmanta.config import Config
from inmanta.env import LocalPackagePath, process_env
from inmanta.module import InmantaModuleRequirement, InstallMode, ModuleV1, ModuleV2Source
from inmanta.moduletool import ModuleTool, ProjectTool
from inmanta.parser import ParserException
from moduletool.common import add_file, clone_repo
from packaging.version import Version
from utils import PipIndex, create_python_package, module_from_template, v1_module_from_template


@pytest.mark.parametrize_any(
    "kwargs_update_method, mod2_should_be_updated, mod8_should_be_updated",
    [({}, True, True), ({"module": "mod2"}, True, False), ({"module": "mod8"}, False, True)],
)
def test_module_update_with_install_mode_master(
    tmpdir: py.path.local,
    modules_repo: str,
    kwargs_update_method: Dict[str, str],
    mod2_should_be_updated: bool,
    mod8_should_be_updated: bool,
) -> None:
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


@pytest.mark.parametrize("corrupt_module", [False, True])
@pytest.mark.parametrize("install_mode", [InstallMode.release, InstallMode.prerelease])
@pytest.mark.slowtest
def test_module_update_with_v2_module(
    tmpdir: py.path.local,
    modules_v2_dir: str,
    snippetcompiler_clean,
    modules_repo: str,
    corrupt_module: bool,
    install_mode: InstallMode,
) -> None:
    """
    Assert that the `inmanta module update` command works correctly when executed on a project with a V2 module.

    :param corrupt_module: Whether the module to be updated contains a syntax error or not.

    Dependency graph:

        -> Inmanta project
            -> module1 (v2) -> module2 (v2)
            -> mod11 (v1)
    """
    template_module_name = "elaboratev2module"
    template_module_dir = os.path.join(modules_v2_dir, template_module_name)

    pip_index = PipIndex(artifact_dir=os.path.join(str(tmpdir), "pip-index"))

    def assert_version_installed(module_name: str, version: str) -> None:
        package_name = ModuleV2Source.get_package_name_for(module_name)
        installed_packages: Dict[str, Version] = process_env.get_installed_packages()
        assert package_name in installed_packages
        assert str(installed_packages[package_name]) == version

    for module_name, versions in {
        "module2": ["2.0.1", "2.1.0", "2.2.0", "2.2.1.dev0", "3.0.1"],
        "module1": ["1.2.4", "1.2.5"],
    }.items():
        # Module1 only has patch updates and Module2 has minor and major updates.
        # This ensure that the test covers the different types of version bumps.
        for current_version in versions:
            module_dir = os.path.join(tmpdir, f"{module_name}-v{current_version}")
            module_from_template(
                source_dir=template_module_dir,
                dest_dir=module_dir,
                new_version=Version(current_version),
                new_name=module_name,
                new_requirements=[InmantaModuleRequirement(Requirement.parse("module2<3.0.0"))]
                if module_name == "module1"
                else None,
                install=False,
                publish_index=pip_index,
                new_content_init_cf="import module2" if module_name == "module1" else None,
            )
    patched_module_dir = os.path.join(tmpdir, "module1-v1.2.3")
    module_from_template(
        source_dir=template_module_dir,
        dest_dir=patched_module_dir,
        new_version=Version("1.2.3"),
        new_name="module1",
        # Add a dependency on module2, without setting an explicit version constraint. Later version of module1
        # do set a version constraint on the dependency on module2. This way it is verified whether the module update
        # command takes into account the version constraints set in a new version of a module.
        new_requirements=[InmantaModuleRequirement(Requirement.parse("module2"))],
        install=False,
        publish_index=pip_index,
        new_content_init_cf="entity" if corrupt_module else None,  # Introduce syntax error in the module
    )

    module_path = os.path.join(tmpdir, "modulepath")
    os.mkdir(module_path)
    mod11_dir = clone_repo(modules_repo, "mod11", module_path, tag="3.2.1")

    snippetcompiler_clean.setup_for_snippet(
        # Don't import module2 in the inmanta project. An import for module2 is present in module1 instead.
        # This tests whether the module update command takes into account all transitive dependencies.
        snippet="""
        import module1
        import mod11
        """,
        autostd=False,
        install_v2_modules=[
            LocalPackagePath(path=os.path.join(tmpdir, "module2-v2.0.1")),
            LocalPackagePath(path=patched_module_dir),
        ],
        add_to_module_path=[module_path],
        python_package_sources=[pip_index.url],
        project_requires=[
            InmantaModuleRequirement.parse("module1<1.2.5"),
            InmantaModuleRequirement.parse("mod11<4.2.0"),
        ],
        install_mode=install_mode,
        install_project=False,
    )

    assert_version_installed(module_name="module1", version="1.2.3")
    assert_version_installed(module_name="module2", version="2.0.1")
    assert ModuleV1(project=None, path=mod11_dir).version == Version("3.2.1")
    ModuleTool().update()
    assert_version_installed(module_name="module1", version="1.2.4")
    assert_version_installed(module_name="module2", version="2.2.0" if install_mode == InstallMode.release else "2.2.1.dev0")
    assert ModuleV1(project=None, path=mod11_dir).version == Version("4.1.2")


@pytest.mark.slowtest
def test_module_update_dependencies(
    tmpdir: py.path.local,
    snippetcompiler_clean,
    modules_dir: str,
) -> None:
    """
    Verify that `inmanta project update` correctly handles module's Python dependencies:
        - update should include install
        - update should update Python dependencies within module's constraints
        - update should update transitive Python dependencies
    """
    snippetcompiler_clean.setup_for_snippet(
        snippet="import my_mod",
        autostd=False,
        install_project=False,
        add_to_module_path=[str(tmpdir.join("modules"))],
    )

    # create index with multiple versions for packages a, b and c
    index: PipIndex = PipIndex(str(tmpdir.join("index")))
    create_python_package("a", Version("1.0.0"), str(tmpdir.join("a-1.0.0")), publish_index=index)
    for v in ("1.0.0", "1.0.1", "2.0.0"):
        create_python_package(
            "b", Version(v), str(tmpdir.join(f"b-{v}")), requirements=[Requirement.parse("c")], publish_index=index
        )
    for v in ("1.0.0", "2.0.0"):
        create_python_package("c", Version(v), str(tmpdir.join(f"c-{v}")), publish_index=index)

    # install b-1.0.0 and c-1.0.0
    process_env.install_from_index([Requirement.parse(req) for req in ("b==1.0.0", "c==1.0.0")], index_urls=[index.url])

    # create my_mod
    v1_module_from_template(
        source_dir=os.path.join(modules_dir, "minimalv1module"),
        dest_dir=str(tmpdir.join("modules", "my_mod")),
        new_name="my_mod",
        new_requirements=[Requirement.parse(req) for req in ("a", "b~=1.0.0")],
    )

    # run `inmanta project update` without running install first
    environ_index: Optional[str] = os.environ.get("PIP_INDEX_URL", None)
    try:
        os.environ["PIP_INDEX_URL"] = index.url
        ProjectTool().update()
    finally:
        if environ_index is None:
            del os.environ["PIP_INDEX_URL"]
        else:
            os.environ["PIP_INDEX_URL"] = environ_index

    # Verify that:
    #   - direct dependency a has been installed
    #   - direct depdendency b has been updated but not past the allowed constraint
    #   - transitive dependency c has been updated
    assert process_env.are_installed(("a==1.0.0", "b==1.0.1", "c==2.0.0"))


def test_module_update_syntax_error_in_project(tmpdir: py.path.local, modules_v2_dir: str, snippetcompiler_clean) -> None:
    snippetcompiler_clean.setup_for_snippet(snippet="entity", autostd=False, install_project=False)
    with pytest.raises(ParserException):
        ModuleTool().update()
