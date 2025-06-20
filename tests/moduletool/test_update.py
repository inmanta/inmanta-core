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

import py.path
import pytest

import inmanta.util
from inmanta import env
from inmanta.data.model import PipConfig
from inmanta.env import LocalPackagePath
from inmanta.module import InmantaModuleRequirement, ModuleV2Source
from inmanta.moduletool import ProjectTool
from inmanta.parser import ParserException
from packaging.requirements import Requirement
from packaging.version import Version
from utils import PipIndex, create_python_package, module_from_template


@pytest.mark.parametrize("corrupt_module", [False, True])
@pytest.mark.slowtest
def test_module_update_with_v2_module(
    tmpdir: py.path.local,
    modules_v2_dir: str,
    snippetcompiler_clean,
    modules_repo: str,
    corrupt_module: bool,
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
        installed_packages: dict[str, Version] = env.process_env.get_installed_packages()
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
                new_requirements=(
                    [InmantaModuleRequirement(inmanta.util.parse_requirement(requirement="module2<3.0.0"))]
                    if module_name == "module1"
                    else None
                ),
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
        new_requirements=[InmantaModuleRequirement(inmanta.util.parse_requirement(requirement="module2"))],
        install=False,
        publish_index=pip_index,
        new_content_init_cf="entity" if corrupt_module else None,  # Introduce syntax error in the module
    )

    snippetcompiler_clean.setup_for_snippet(
        # Don't import module2 in the inmanta project. An import for module2 is present in module1 instead.
        # This tests whether the module update command takes into account all transitive dependencies.
        snippet="",
        autostd=False,
        install_v2_modules=[
            LocalPackagePath(path=os.path.join(tmpdir, "module2-v2.0.1")),
            LocalPackagePath(path=patched_module_dir),
        ],
        index_url=pip_index.url,
        python_requires=[Requirement("inmanta-module-module1<1.2.5")],
        install_project=False,
    )

    assert_version_installed(module_name="module1", version="1.2.3")
    assert_version_installed(module_name="module2", version="2.0.1")
    ProjectTool().update()
    assert_version_installed(module_name="module1", version="1.2.4")
    assert_version_installed(module_name="module2", version="2.2.0")


@pytest.mark.slowtest
def test_module_update_dependencies(
    tmpdir: py.path.local,
    monkeypatch,
    snippetcompiler_clean,
    modules_v2_dir: str,
) -> None:
    """
    Verify that `inmanta project update` correctly handles module's Python dependencies:
        - update should include install
        - update should update Python dependencies within module's constraints
        - update should update transitive Python dependencies
    """
    # create index with multiple versions for packages a, b and c
    index: PipIndex = PipIndex(str(tmpdir.join("index")))
    create_python_package("a", Version("1.0.0"), str(tmpdir.join("a-1.0.0")), publish_index=index)
    for v in ("1.0.0", "1.0.1", "2.0.0"):
        create_python_package(
            "b",
            Version(v),
            str(tmpdir.join(f"b-{v}")),
            requirements=[inmanta.util.parse_requirement(requirement="c")],
            publish_index=index,
        )
    for v in ("1.0.0", "2.0.0"):
        create_python_package("c", Version(v), str(tmpdir.join(f"c-{v}")), publish_index=index)

    # create my_mod
    module_from_template(
        source_dir=os.path.join(modules_v2_dir, "minimalv2module"),
        dest_dir=str(tmpdir.join("modules", "my_mod")),
        new_name="my_mod",
        new_requirements=inmanta.util.parse_requirements(["a", "b~=1.0.0"]),
        publish_index=index,
    )

    snippetcompiler_clean.setup_for_snippet(
        snippet="import my_mod",
        autostd=False,
        install_project=False,
        add_to_module_path=[str(tmpdir.join("modules"))],
        python_requires=inmanta.util.parse_requirements(["inmanta-module-my_mod"]),
        index_url=index.url,
    )

    # install b-1.0.0 and c-1.0.0
    env.process_env.install_for_config(
        [inmanta.util.parse_requirement(requirement=req) for req in ("b==1.0.0", "c==1.0.0")],
        config=PipConfig(
            index_url=index.url,
            use_system_config=False,
        ),
    )

    # run `inmanta project update` without running install first
    monkeypatch.setenv("PIP_INDEX_URL", index.url)
    ProjectTool().update()

    # Verify that:
    #   - direct dependency a has been installed
    #   - direct dependency b has been updated but not past the allowed constraint
    #   - transitive dependency c has been updated
    assert env.process_env.are_installed(("a==1.0.0", "b==1.0.1", "c==2.0.0"))


def test_module_update_syntax_error_in_project(tmpdir: py.path.local, modules_v2_dir: str, snippetcompiler_clean) -> None:
    snippetcompiler_clean.setup_for_snippet(snippet="entity", autostd=False, install_project=False)
    with pytest.raises(ParserException):
        ProjectTool().update()
