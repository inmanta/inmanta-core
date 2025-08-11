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
from typing import Optional

import py
import pytest

import inmanta.util
from inmanta import env
from inmanta.command import CLIException
from inmanta.module import ModuleV1, ModuleV2, ModuleV2Source, Project, ProjectMetadata
from inmanta.moduletool import ModuleTool
from packaging.version import Version
from utils import PipIndex, module_from_template


@pytest.mark.slowtest
def test_module_add_v2_module_to_project(
    tmpdir: py.path.local,
    snippetcompiler_clean,
    local_module_package_index: str,
    modules_v2_dir: str,
) -> None:
    """
    Add a V2 module to an inmanta project using the `inmanta module add` command.
    """
    # Ensure that versions 1.1.1 and 1.2.0 exist in the pip index.
    # Version 1.2.3 is present in the pip index exported by local_module_package_index.
    pip_index = PipIndex(artifact_dir=os.path.join(str(tmpdir), "pip-index"))
    for version in ["1.1.1", "1.2.0"]:
        module_from_template(
            source_dir=os.path.join(modules_v2_dir, "elaboratev2module"),
            dest_dir=os.path.join(tmpdir, f"elaboratev2module-v{version}"),
            new_version=Version(version),
            publish_index=pip_index,
            new_extras={"optional": [inmanta.util.parse_requirement(requirement="inmanta-module-minimalv2module")]},
        )

    # Create project
    project: Project = snippetcompiler_clean.setup_for_snippet(
        snippet="", autostd=False, index_url=local_module_package_index, extra_index_url=[pip_index.url]
    )

    requirements_txt_file = os.path.join(project.path, "requirements.txt")

    def _assert_project_state(
        pkg_name: str,
        expected_version: Version,
        project_requires_constraint: str,
        expected_pkg_from_extra: Optional[str] = None,
    ) -> None:
        installed_packages = env.process_env.get_installed_packages()
        assert pkg_name in installed_packages
        if expected_pkg_from_extra:
            assert expected_pkg_from_extra in installed_packages
        assert installed_packages[pkg_name] == expected_version
        with open(project.get_metadata_file_path(), encoding="utf-8") as fd:
            project_metadata = ProjectMetadata.parse(fd)
            assert not project_metadata.requires
        with open(requirements_txt_file, encoding="utf-8") as fd:
            assert fd.read().strip() == ModuleV2Source.get_package_name_for(project_requires_constraint)

    module_name = "elaboratev2module"
    pkg_name = "inmanta-module-elaboratev2module"
    assert pkg_name not in env.process_env.get_installed_packages().keys()

    version_constraint = f"{module_name}==1.2.3"
    ModuleTool().add(module_req=version_constraint, v2=True, override=False)
    _assert_project_state(pkg_name=pkg_name, expected_version=Version("1.2.3"), project_requires_constraint=version_constraint)

    new_version_constraint = f"{module_name}==1.2.0"
    with pytest.raises(CLIException, match="A dependency on the given module was already defined"):
        ModuleTool().add(module_req=new_version_constraint, v2=True, override=False)
    _assert_project_state(pkg_name=pkg_name, expected_version=Version("1.2.3"), project_requires_constraint=version_constraint)

    ModuleTool().add(module_req=new_version_constraint, v2=True, override=True)
    _assert_project_state(
        pkg_name=pkg_name, expected_version=Version("1.2.0"), project_requires_constraint=new_version_constraint
    )

    # Use extra optional
    new_version_constraint = f"{module_name}[optional]==1.2.0"
    ModuleTool().add(module_req=new_version_constraint, v2=True, override=True)
    _assert_project_state(
        pkg_name=pkg_name,
        expected_version=Version("1.2.0"),
        project_requires_constraint=new_version_constraint,
        expected_pkg_from_extra="inmanta-module-minimalv2module",
    )


def test_module_add_v2_module_to_v2_module(tmpdir: py.path.local, monkeypatch, modules_v2_dir: str) -> None:
    """
    Add a V2 module to a V2 module using the `inmanta module add` command.
    """
    # Create module to execute `inmanta module add` command on
    module_dir = os.path.join(tmpdir, "test")
    module_from_template(source_dir=os.path.join(modules_v2_dir, "elaboratev2module"), dest_dir=module_dir)
    monkeypatch.chdir(module_dir)

    def _assert_module_requirements(expected_requirements: list[str]) -> None:
        module_v2 = ModuleV2(project=None, path=module_dir)
        assert sorted(module_v2.metadata.install_requires) == sorted(expected_requirements)
        assert not os.path.exists(os.path.join(module_dir, "requirements.txt"))

    _assert_module_requirements(expected_requirements=[])
    installed_packages = env.process_env.get_installed_packages()

    name_dependent_module = "a_module"
    ModuleTool().add(module_req="a_module", v2=True, override=False)
    _assert_module_requirements(expected_requirements=[ModuleV2Source.get_package_name_for(name_dependent_module)])

    with pytest.raises(CLIException, match="A dependency on the given module was already defined"):
        ModuleTool().add(module_req=f"{name_dependent_module}==1.1.1", v2=True, override=False)
    _assert_module_requirements(expected_requirements=[ModuleV2Source.get_package_name_for(name_dependent_module)])

    ModuleTool().add(module_req=f"{name_dependent_module}==1.1.1", v2=True, override=True)
    _assert_module_requirements(expected_requirements=[f"{ModuleV2Source.get_package_name_for(name_dependent_module)}==1.1.1"])

    # Ensure no new packages were installed as a side-effect of `inmanta modules add`
    assert env.process_env.get_installed_packages() == installed_packages


def test_module_add_v2_module_to_v1_module(tmpdir: py.path.local, modules_dir: str, monkeypatch) -> None:
    """
    Add a V2 module to a V1 module using the `inmanta module add` command.
    """
    original_module_dir = os.path.join(modules_dir, "mod1")
    module_dir = os.path.join(tmpdir, "mod1")
    shutil.copytree(original_module_dir, module_dir)
    requirements_txt_file = os.path.join(module_dir, "requirements.txt")
    monkeypatch.chdir(module_dir)

    def _assert_module_requirements(expected_requirement: str) -> None:
        module_v1 = ModuleV1(project=None, path=module_dir)
        assert module_v1.metadata.requires == []
        with open(requirements_txt_file, encoding="utf-8") as fd:
            assert fd.read().strip() == expected_requirement

    assert not os.path.exists(requirements_txt_file)
    installed_packages = env.process_env.get_installed_packages()

    name_dependent_module = "a_module"
    ModuleTool().add(module_req=name_dependent_module, v2=True, override=False)
    _assert_module_requirements(expected_requirement=ModuleV2Source.get_package_name_for(name_dependent_module))

    with pytest.raises(CLIException, match="A dependency on the given module was already defined"):
        ModuleTool().add(module_req=f"{name_dependent_module}==1.1.1", v2=True, override=False)
    _assert_module_requirements(expected_requirement=ModuleV2Source.get_package_name_for(name_dependent_module))

    ModuleTool().add(module_req=f"{name_dependent_module}==1.1.1", v2=True, override=True)
    _assert_module_requirements(expected_requirement=f"{ModuleV2Source.get_package_name_for(name_dependent_module)}==1.1.1")

    # Ensure no new packages were installed as a side-effect of `inmanta modules add`
    assert env.process_env.get_installed_packages() == installed_packages


@pytest.mark.slowtest
def test_module_add_preinstalled(tmpdir: py.path.local, modules_v2_dir: str, snippetcompiler_clean) -> None:
    """
    Verify that `inmanta module add` respects preinstalled modules when they're compatible and logs a warning when they're
    not.
    """
    module_name: str = "mymodule"
    pip_index = PipIndex(artifact_dir=str(tmpdir.join("pip-index")))
    snippetcompiler_clean.setup_for_snippet(snippet="", autostd=False, index_url=pip_index.url)

    # preinstall 1.0.0, don't publish to index
    module_from_template(
        os.path.join(modules_v2_dir, "minimalv2module"),
        str(tmpdir.join(module_name, "1.0.0")),
        new_name=module_name,
        new_version=Version("1.0.0"),
        install=True,
    )
    # publish 1.1.0 and 2.0.0 to index
    module_from_template(
        os.path.join(modules_v2_dir, "minimalv2module"),
        str(tmpdir.join(module_name, "1.1.0")),
        new_name=module_name,
        new_version=Version("1.1.0"),
        install=False,
        publish_index=pip_index,
    )
    module_from_template(
        os.path.join(modules_v2_dir, "minimalv2module"),
        str(tmpdir.join(module_name, "2.0.0")),
        new_name=module_name,
        new_version=Version("2.0.0"),
        install=False,
        publish_index=pip_index,
    )

    # verify that compatible constraint does not reinstall or update
    ModuleTool().add(module_req=f"{module_name}~=1.0", v2=True, override=True)
    assert ModuleTool().get_module(module_name).version == Version("1.0.0")

    # verify that incompatible constraint reinstalls
    ModuleTool().add(module_req=f"{module_name}~=2.0", v2=True, override=True)
    assert ModuleTool().get_module(module_name).version == Version("2.0.0")


def test_module_add_v2_wrong_name_error(tmpdir: py.path.local, monkeypatch, modules_v2_dir: str) -> None:
    """
    Test the error messages of v2 modules when adding with a wrong name. (issue #3556)
    """
    # Create module to execute `inmanta module add` command on
    module_dir = os.path.join(tmpdir, "test")
    module_from_template(source_dir=os.path.join(modules_v2_dir, "elaboratev2module"), dest_dir=module_dir)
    monkeypatch.chdir(module_dir)

    with pytest.raises(ValueError, match="Invalid Inmanta module requirement: Inmanta module names use '_', not '-'."):
        ModuleTool().add(module_req="a-module", v2=True, override=False)

    with pytest.raises(
        ValueError, match="Invalid Inmanta module requirement: Use the Inmanta module name instead of the Python package name"
    ):
        ModuleTool().add(module_req="inmanta-module-a-module", v2=True, override=False)
