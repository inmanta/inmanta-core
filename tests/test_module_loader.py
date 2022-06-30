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
import logging
import os
import shutil
import sys
from typing import List, Optional, Set

import py
import pytest
from pkg_resources import Requirement

from inmanta import plugins
from inmanta.compiler.config import feature_compiler_cache
from inmanta.const import CF_CACHE_DIR
from inmanta.env import ConflictingRequirements, LocalPackagePath, process_env
from inmanta.module import (
    DummyProject,
    InmantaModuleRequirement,
    InvalidModuleException,
    ModuleLoadingException,
    ModuleNotFoundException,
    ModuleV1,
    ModuleV2,
    ModuleV2Source,
    Project,
)
from inmanta.moduletool import ModuleConverter, ModuleTool
from packaging.version import Version
from utils import PipIndex, create_python_package, module_from_template, v1_module_from_template


@pytest.mark.parametrize_any("editable_install", [True, False])
def test_v2_module_loading(editable_install: bool, tmpdir: py.path.local, snippetcompiler, capsys, modules_v2_dir: str) -> None:
    # Work around caching problem in venv
    feature_compiler_cache.set("True")
    # Disable modules_dir
    snippetcompiler.modules_dir = None

    module_name = "elaboratev2module"
    module_dir = os.path.join(modules_v2_dir, module_name)
    module_copy_dir = os.path.join(tmpdir, "module")
    shutil.copytree(module_dir, module_copy_dir)
    assert os.path.isdir(module_copy_dir)

    snippetcompiler.setup_for_snippet(
        f"""
            import {module_name}

            {module_name}::print_message("Hello world")
        """,
        autostd=False,
        install_v2_modules=[LocalPackagePath(path=module_copy_dir, editable=editable_install)],
    )

    snippetcompiler.do_export()
    assert "Hello world" in capsys.readouterr().out

    # Make sure the cache files are created
    cache_folder = os.path.join(snippetcompiler.project_dir, CF_CACHE_DIR)
    assert len(os.listdir(cache_folder)) > 0


def test_v1_and_v2_module_installed_simultaneously(
    tmpdir: py.path.local, snippetcompiler_clean, capsys, caplog, modules_dir: str
) -> None:
    """
    When a module is installed both in V1 and V2 format, ensure that:
       * A warning is logged
       * The V2 module is loaded and not the V1 module.
    """
    # Work around caching problem in venv
    feature_compiler_cache.set("False")

    module_name = "v1_print_plugin"

    def compile_and_verify(
        expected_message: str, expect_warning: bool, install_v2_modules: List[LocalPackagePath] = []
    ) -> None:
        caplog.clear()
        snippetcompiler_clean.setup_for_snippet(f"import {module_name}", install_v2_modules=install_v2_modules, autostd=False)
        snippetcompiler_clean.do_export()
        assert expected_message in capsys.readouterr().out
        got_warning = f"Module {module_name} is installed as a V1 module and a V2 module" in caplog.text
        assert got_warning == expect_warning

    # Run compile. Only a V1 module is installed in the module path
    expected_message_v1 = "Hello world"
    compile_and_verify(expected_message=expected_message_v1, expect_warning=False)
    assert isinstance(Project.get().modules[module_name], ModuleV1)

    # Convert V1 module to V2 module and install it as well
    module_dir = os.path.join(modules_dir, module_name)
    v1_module_dir = os.path.join(tmpdir, "v1_module")
    shutil.copytree(module_dir, v1_module_dir)
    assert os.path.isdir(v1_module_dir)
    v2_module_dir = os.path.join(tmpdir, "v2_module")
    module = ModuleV1(project=DummyProject(autostd=False), path=v1_module_dir)
    ModuleConverter(module).convert(output_directory=v2_module_dir)

    # Print a different message in the V2 module, to detect which of both gets loaded
    expected_message_v2 = "Other message"
    with open(os.path.join(v2_module_dir, "model", "_init.cf"), "r+") as fd:
        content = fd.read()
        assert expected_message_v1 in content
        content = content.replace(expected_message_v1, expected_message_v2)
        assert expected_message_v2 in content
        fd.seek(0)
        fd.write(content)

    # Run compile again. V1 version and V2 version are installed simultaneously
    compile_and_verify(
        expected_message=expected_message_v2,
        expect_warning=True,
        install_v2_modules=[LocalPackagePath(path=v2_module_dir, editable=False)],
    )
    assert isinstance(Project.get().modules[module_name], ModuleV2)


def test_v1_module_depends_on_v1_and_v2_module(tmpdir: py.path.local, snippetcompiler, capsys, modules_v2_dir: str) -> None:
    module_dir = os.path.join(modules_v2_dir, "elaboratev2module")
    module_copy_dir = os.path.join(tmpdir, "module")
    shutil.copytree(module_dir, module_copy_dir)
    assert os.path.isdir(module_copy_dir)

    module_name = "v1_module_depends_on_v1_and_v2_module"
    snippetcompiler.setup_for_snippet(
        f"import {module_name}",
        autostd=False,
        install_v2_modules=[LocalPackagePath(path=module_copy_dir, editable=False)],
    )

    snippetcompiler.do_export()
    output = capsys.readouterr().out
    assert "Print from v2 module" in output
    assert "Hello world" in output


def test_install_module_no_v2_source(snippetcompiler) -> None:
    """
    Verify that attempting to install a v2 module without a v2 module source configured results in the appropriate exception.
    """
    module_name = "non_existing_module"
    with pytest.raises(Exception) as e:
        snippetcompiler.setup_for_snippet(
            snippet=f"import {module_name}",
            install_project=True,
            python_package_sources=[],
            python_requires=[
                ModuleV2Source.get_python_package_requirement(InmantaModuleRequirement.parse(module_name)),
            ],
        )
    message: str = (
        "Attempting to install a v2 module but no v2 module source is configured. Add at least one repo of type"
        ' "package" to the project config file.'
    )
    assert message in e.value.format_trace()


@pytest.mark.parametrize("allow_v1", [True, False])
def test_load_module_v1_already_installed(snippetcompiler, modules_dir: str, allow_v1: bool) -> None:
    """
    Test whether the Project.load_module() method works correctly when loading a V1 module that was already installed
    in the module path.
    """
    module_name = "elaboratev1module"
    module_dir = os.path.join(modules_dir, module_name)
    project: Project = snippetcompiler.setup_for_snippet(
        snippet=f"import {module_name}", add_to_module_path=[module_dir], install_project=False
    )

    assert module_name not in project.modules
    if allow_v1:
        project.load_module(module_name=module_name, install_v1=False, allow_v1=allow_v1)
        assert module_name in project.modules
    else:
        with pytest.raises(ModuleNotFoundException, match=f"Could not find module {module_name}"):
            project.load_module(module_name=module_name, install_v1=False, allow_v1=allow_v1)


def test_load_module_v1_module_using_install(snippetcompiler) -> None:
    """
    Test whether the Project.load_module() method works correctly when a module is only available as a V1 module
    and that module is not yet present in the module path.
    """
    module_name = "std"
    project: Project = snippetcompiler.setup_for_snippet(snippet=f"import {module_name}", install_project=False)
    # Remove std module in downloadpath created by other test case
    shutil.rmtree(os.path.join(project.downloadpath, module_name), ignore_errors=True)
    assert module_name not in project.modules
    assert module_name not in os.listdir(project.downloadpath)
    project.load_module(module_name=module_name, install_v1=True, allow_v1=True)
    assert module_name in project.modules
    assert module_name in os.listdir(project.downloadpath)


@pytest.mark.parametrize("allow_v1", [True, False])
@pytest.mark.parametrize("editable_install", [True, False])
def test_load_module_v2_already_installed(
    snippetcompiler_clean,
    modules_v2_dir: str,
    allow_v1: bool,
    editable_install: bool,
) -> None:
    """
    Test whether the Project.load_module() method works correctly when loading a V2 module that was already installed
    in the compiler venv.
    """
    module_name = "elaboratev2module"
    module_dir = os.path.join(modules_v2_dir, module_name)
    project: Project = snippetcompiler_clean.setup_for_snippet(
        snippet=f"import {module_name}",
        install_v2_modules=[LocalPackagePath(module_dir, editable_install)],
        install_project=False,
    )

    assert module_name not in project.modules
    project.load_module(module_name=module_name, install_v2=False, allow_v1=allow_v1)
    assert module_name in project.modules


@pytest.mark.parametrize("install", [True, False])
def test_load_module_v2_module_using_install(
    snippetcompiler_clean,
    local_module_package_index: str,
    install: bool,
):
    """
    Test whether the Project.load_module() method works correctly when a module is only available as a V2 module
    and that module is not yet installed in the compiler venv.
    """
    module_name = "minimalv2module"
    project: Project = snippetcompiler_clean.setup_for_snippet(
        snippet=f"import {module_name}", python_package_sources=[local_module_package_index], install_project=False
    )
    assert module_name not in project.modules
    assert module_name not in os.listdir(project.downloadpath)
    if install:
        project.load_module(module_name=module_name, install_v1=install, install_v2=install, allow_v1=True)
    else:
        with pytest.raises(ModuleNotFoundException, match=f"Could not find module {module_name}"):
            project.load_module(module_name=module_name, install_v1=install, install_v2=install, allow_v1=True)
    assert (module_name in project.modules) == install
    assert module_name not in os.listdir(project.downloadpath)


@pytest.mark.parametrize("allow_v1", [True, False])
def test_load_module_module_not_found(snippetcompiler_clean, allow_v1: bool) -> None:
    """
    Assert behavior when a module is not found as a V1 or a V2 module.
    """
    module_name = "non_existing_module"
    snippetcompiler_clean.modules_dir = None
    project: Project = snippetcompiler_clean.setup_for_snippet(
        snippet=f"import {module_name}", install_project=False, python_package_sources=["non_existing_local_index"]
    )
    with pytest.raises(ModuleNotFoundException, match=f"Could not find module {module_name}"):
        project.load_module(module_name=module_name, install_v1=allow_v1, install_v2=True, allow_v1=allow_v1)


def test_load_module_v1_and_v2_installed(
    tmpdir: py.path.local,
    snippetcompiler_clean,
    modules_dir: str,
    caplog,
) -> None:
    """
    Test whether the Project.load_module() method works correctly when the v1 and v2 version of a module are both installed.
    The V2 module should be loaded and a warning should be logged.
    """
    module_name = "minimalv1module"
    module_dir = os.path.join(modules_dir, module_name)

    # Convert v1 to v2 module
    module = ModuleV1(project=DummyProject(autostd=False), path=module_dir)
    module_dir_v2 = os.path.join(tmpdir, f"{module_name}-v2")
    ModuleConverter(module).convert(output_directory=module_dir_v2)

    # The V1 module is installed implicitly. The snippetcompiler_clean fixture adds
    # the `modules_dir` to the modulepath of the newly created project.
    project: Project = snippetcompiler_clean.setup_for_snippet(
        snippet=f"import {module_name}",
        install_v2_modules=[LocalPackagePath(module_dir_v2, editable=False)],
        install_project=False,
    )

    assert module_name not in project.modules
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        project.load_module(module_name=module_name, install_v1=False, install_v2=False, allow_v1=True)
    assert f"Module {module_name} is installed as a V1 module and a V2 module: V1 will be ignored." in caplog.text
    assert module_name in project.modules
    assert isinstance(project.modules[module_name], ModuleV2)


@pytest.mark.parametrize("preload_v1_module", [True, False])
def test_load_module_recursive_v2_module_depends_on_v1(
    local_module_package_index: str, snippetcompiler, preload_v1_module: bool
) -> None:
    """
    A V2 module cannot depend on a V1 module. This test case ensure that the load_module_recursive() method
    raises an error when a dependency of a V2 module is only available as a V1 module.

    Dependency graph:  v2_depends_on_v1 (V2)  --->  mod1 (V1)
    """
    project = snippetcompiler.setup_for_snippet(
        snippet="import v2_depends_on_v1",
        python_package_sources=[local_module_package_index],
        python_requires=[Requirement.parse("inmanta-module-v2-depends-on-v1")],
        install_project=False,
    )
    if preload_v1_module:
        project.get_module("mod1", allow_v1=True)
    assert ("mod1" in project.modules) == preload_v1_module

    with pytest.raises(ModuleLoadingException, match="Failed to load module mod1"):
        project.load_module_recursive(install=True)


def test_load_module_recursive_complex_module_dependencies(local_module_package_index: str, snippetcompiler) -> None:
    """
    Test whether the load_module_recursive() method works correctly when complex, circular dependencies exist between modules.

    Dependency graph:

    complex_module_dependencies_mod1  --------------------->  complex_module_dependencies_mod2
           |   ^                      <---------------------             |   ^
           |   |                                                         |   |
           v   |                                                         v   |
    complex_module_dependencies_mod1::submod                  complex_module_dependencies_mod2::submod
    """
    project = snippetcompiler.setup_for_snippet(
        snippet="import complex_module_dependencies_mod1",
        autostd=False,
        python_package_sources=[local_module_package_index],
        python_requires=[Requirement.parse("inmanta-module-complex-module-dependencies-mod1")],
        install_project=False,
    )
    assert "complex_module_dependencies_mod1" not in project.modules
    assert "complex_module_dependencies_mod2" not in project.modules
    loaded_namespaces: Set[str] = set(ns for ns, _, _ in project.load_module_recursive(install=True))
    assert "complex_module_dependencies_mod1" in project.modules
    assert "complex_module_dependencies_mod2" in project.modules
    expected_namespaces = {
        "complex_module_dependencies_mod1",
        "complex_module_dependencies_mod1::submod",
        "complex_module_dependencies_mod2",
        "complex_module_dependencies_mod2::submod",
    }
    assert loaded_namespaces == expected_namespaces


def test_load_import_based_v2_project(local_module_package_index: str, snippetcompiler_clean) -> None:
    """
    A project needs to explicitly list its v2 dependencies in order to be able to load them. Import-based loading is not
    allowed.
    """
    module_name: str = "minimalv2module"

    def load(requires: Optional[List[Requirement]] = None) -> None:
        project: Project = snippetcompiler_clean.setup_for_snippet(
            f"import {module_name}",
            autostd=False,
            install_project=False,
            python_package_sources=[local_module_package_index],
            # make sure that even listing the requirement in project.yml does not suffice
            project_requires=[InmantaModuleRequirement.parse(module_name)],
            python_requires=requires,
        )
        project.load_module_recursive(install=True)

    with pytest.raises(ModuleLoadingException, match=f"Failed to load module {module_name}"):
        load()
    # assert that it doesn't raise an error with explicit requirements set
    load([Requirement.parse(ModuleV2Source.get_package_name_for(module_name))])


@pytest.mark.parametrize("v1", [True, False])
@pytest.mark.parametrize("explicit_dependency", [True, False])
def test_load_import_based_v2_module(
    local_module_package_index: str,
    snippetcompiler_clean,
    modules_dir: str,
    modules_v2_dir: str,
    tmpdir: py.path.local,
    v1: bool,
    explicit_dependency: bool,
) -> None:
    """
    A module needs to explicitly list its v2 dependencies in order to be able to load them. Import-based loading is not
    allowed.
    """
    main_module_name: str = "mymodule"
    dependency_module_name: str = "minimalv2module"
    index: PipIndex = PipIndex(os.path.join(str(tmpdir), ".my-index"))
    libs_dir: str = os.path.join(str(tmpdir), "libs")
    os.makedirs(libs_dir)

    model: str = f"import {dependency_module_name}"
    requirements: List[InmantaModuleRequirement] = (
        [InmantaModuleRequirement.parse(dependency_module_name)] if explicit_dependency else []
    )

    if v1:
        v1_module_from_template(
            os.path.join(modules_dir, "minimalv1module"),
            os.path.join(libs_dir, main_module_name),
            new_name=main_module_name,
            new_content_init_cf=model,
            new_requirements=requirements,
        )
    else:
        module_from_template(
            os.path.join(modules_v2_dir, "minimalv2module"),
            os.path.join(str(tmpdir), main_module_name),
            new_name=main_module_name,
            new_content_init_cf=model,
            new_requirements=requirements,
            install=False,
            publish_index=index,
        )

    project: Project = snippetcompiler_clean.setup_for_snippet(
        f"import {main_module_name}",
        autostd=False,
        install_project=False,
        add_to_module_path=[libs_dir],
        python_package_sources=[local_module_package_index, index.url],
        # make sure that even listing the requirement in project.yml does not suffice
        project_requires=[InmantaModuleRequirement.parse(dependency_module_name)],
        python_requires=[] if v1 else [Requirement.parse(ModuleV2Source.get_package_name_for(main_module_name))],
    )

    if explicit_dependency:
        # assert that it doesn't raise an error with explicit requirements set
        project.load_module_recursive(install=True)
    else:
        with pytest.raises(ModuleLoadingException, match=f"Failed to load module {dependency_module_name}"):
            project.load_module_recursive(install=True)


def test_module_unload(
    local_module_package_index: str,
    snippetcompiler,
) -> None:
    """
    Verify that Module.unload removes it from the project, unloads its Python modules and deregisters its plugins.
    """
    project: Project = snippetcompiler.setup_for_snippet(
        """
import minimalv2module
import elaboratev2module
        """.strip(),
        python_package_sources=[local_module_package_index],
        python_requires=[
            ModuleV2Source.get_python_package_requirement(InmantaModuleRequirement.parse("minimalv2module")),
            ModuleV2Source.get_python_package_requirement(InmantaModuleRequirement.parse("elaboratev2module")),
        ],
        autostd=False,
    )
    project.load()

    assert "minimalv2module" in project.modules
    assert "elaboratev2module" in project.modules

    assert "inmanta_plugins.minimalv2module" in sys.modules
    assert "inmanta_plugins.elaboratev2module" in sys.modules

    assert "elaboratev2module::print_message" in plugins.PluginMeta.get_functions()

    project.modules["elaboratev2module"].unload()

    assert "minimalv2module" in project.modules
    assert "elaboratev2module" not in project.modules

    assert "inmanta_plugins.minimalv2module" in sys.modules
    assert "inmanta_plugins.elaboratev2module" not in sys.modules

    assert "elaboratev2module::print_message" not in plugins.PluginMeta.get_functions()


def test_project_has_v2_requirements_on_non_imported_module(
    snippetcompiler,
    local_module_package_index: str,
) -> None:
    """
    A Project has a module V2 requirement on a module that it doesn't import.
    Ensure that the non-imported module is not loaded.
    """
    dependency = "elaboratev2module"
    project: Project = snippetcompiler.setup_for_snippet(
        snippet="",  # Don't import elaboratev2module
        python_package_sources=[local_module_package_index],
        python_requires=[
            ModuleV2Source.get_python_package_requirement(InmantaModuleRequirement.parse(dependency)),
        ],
        autostd=False,
    )
    project.load_module_recursive()
    assert dependency not in project.modules


def test_module_has_v2_requirements_on_non_imported_module(snippetcompiler, local_module_package_index: str) -> None:
    """
    A module has a module V2 requirement on a module that it doesn't import.
    Ensure that the non-imported module is not loaded.

    Scenario: module dependency_but_no_import has dependency on minimalv2module
              but dependency_but_no_import doesn't import minimalv2module.
    """
    project: Project = snippetcompiler.setup_for_snippet(
        snippet="import dependency_but_no_import",
        python_package_sources=[local_module_package_index],
        python_requires=[
            ModuleV2Source.get_python_package_requirement(InmantaModuleRequirement.parse("dependency_but_no_import")),
        ],
        autostd=False,
    )
    project.load_module_recursive()
    assert "minimalv2module" not in project.modules


@pytest.mark.slowtest
def test_project_requirements_dont_overwrite_core_requirements_source(
    snippetcompiler_clean,
    local_module_package_index: str,
    modules_v2_dir: str,
    tmpdir: py.path.local,
) -> None:
    """
    A project has a requirement that is also a requirement of core
    but with another version. The requirements of core should not be
    overwritten. The module gets installed from source
    """
    if "inmanta-core" in process_env.get_installed_packages(only_editable=True):
        pytest.skip(
            "This test would fail if it runs against an inmanta-core installed in editable mode, because the build tag "
            "on the development branch is set to .dev0. The inmanta package protection feature would make pip "
            "install a non-editable version of the same package. But no version with build tag .dev0 exists on the python "
            "package repository."
        )

    # Create the module
    module_name: str = "minimalv2module"
    module_path: str = str(tmpdir.join(module_name))
    module_from_template(
        os.path.join(modules_v2_dir, module_name), module_path, new_requirements=[Requirement.parse("Jinja2==2.11.3")]
    )

    # Activate the snippetcompiler venv
    project: Project = snippetcompiler_clean.setup_for_snippet("")
    active_env = project.virtualenv
    jinja2_version_before = active_env.get_installed_packages()["Jinja2"].base_version

    # Install the module
    with pytest.raises(InvalidModuleException) as e:
        ModuleTool().install(editable=False, path=module_path)

    assert ("these package versions have conflicting dependencies.") in str(e.value.msg)

    jinja2_version_after = active_env.get_installed_packages()["Jinja2"].base_version
    assert jinja2_version_before == jinja2_version_after


@pytest.mark.slowtest
def test_project_requirements_dont_overwrite_core_requirements_index(
    snippetcompiler_clean,
    modules_v2_dir: str,
    tmpdir: py.path.local,
) -> None:
    """
    A module from index has a requirement that is also a requirement of core
    but with another version. The requirements of core should not be
    overwritten. The module gets installed from index.
    """
    if "inmanta-core" in process_env.get_installed_packages(only_editable=True):
        pytest.skip(
            "This test would fail if it runs against an inmanta-core installed in editable mode, because the build tag "
            "on the development branch is set to .dev0. The inmanta package protection feature would make pip "
            "install a non-editable version of the same package. But no version with build tag .dev0 exists on the python "
            "package repository."
        )
    # Create the module
    module_name: str = "minimalv2module"
    module_path: str = str(tmpdir.join(module_name))
    index: PipIndex = PipIndex(artifact_dir=os.path.join(str(tmpdir), ".custom-index"))
    module_from_template(
        os.path.join(modules_v2_dir, module_name),
        module_path,
        new_requirements=[Requirement.parse("Jinja2==2.11.3")],
        publish_index=index,
    )

    # Setup project
    project: Project = snippetcompiler_clean.setup_for_snippet(
        "",
        install_project=False,
        python_package_sources=[index.url, "https://pypi.org/simple"],
        python_requires=[ModuleV2Source.get_python_package_requirement(InmantaModuleRequirement.parse(module_name))],
        autostd=False,
    )

    active_env = project.virtualenv
    jinja2_version_before = active_env.get_installed_packages()["Jinja2"].base_version

    # Install project
    with pytest.raises(ConflictingRequirements):
        project.install_modules()

    jinja2_version_after = active_env.get_installed_packages()["Jinja2"].base_version
    assert jinja2_version_before == jinja2_version_after


@pytest.mark.slowtest
def test_module_conflicting_dependencies_with_v2_modules(
    snippetcompiler_clean,
    modules_v2_dir: str,
    tmpdir: py.path.local,
) -> None:
    """
    Show an error message when installing a module that breaks the dependencies
    of another one. minimalv2module depends on y~=1.0.0 which requires x~=1.0.0.
    after the install of minimalv2module we try to install minimalv2module2 which
    requires x~=2.0.0. The y~=1.0.0 requirement is now broken as python package x
    has now version 2.0.0 and y needs 1.0.0.
    """
    index: PipIndex = PipIndex(artifact_dir=os.path.join(str(tmpdir), ".custom-index"))

    # Create an python package x with version 1.0.0
    create_python_package("x", Version("1.0.0"), str(tmpdir.join("x-1.0.0")), publish_index=index)

    # Create an python package x with version 2.0.0
    create_python_package("x", Version("2.0.0"), str(tmpdir.join("x-2.0.0")), publish_index=index)

    # Create an python package y with version 1.0.0 that depends on x~=1.0.0
    create_python_package(
        "y", Version("1.0.0"), str(tmpdir.join("y-1.0.0")), requirements=[Requirement.parse("x~=1.0.0")], publish_index=index
    )

    # Create the first module
    module_name1: str = "minimalv2module"
    module_path1: str = str(tmpdir.join(module_name1))
    module_from_template(
        os.path.join(modules_v2_dir, module_name1),
        module_path1,
        new_requirements=[Requirement.parse("y~=1.0.0")],
        publish_index=index,
    )

    # Create the second module
    module_name2: str = "minimalv2module2"
    module_path2: str = str(tmpdir.join(module_name2))
    module_from_template(
        os.path.join(modules_v2_dir, "minimalv2module"),
        module_path2,
        new_name="minimalv2module2",
        new_requirements=[Requirement.parse("x~=2.0.0")],
        publish_index=index,
    )

    req1 = ModuleV2Source.get_python_package_requirement(InmantaModuleRequirement.parse(module_name1))
    req2 = ModuleV2Source.get_python_package_requirement(InmantaModuleRequirement.parse(module_name2))
    # Setup project
    project: Project = snippetcompiler_clean.setup_for_snippet(
        "",
        install_project=False,
        python_package_sources=[index.url],
        python_requires=[req1, req2],
        autostd=False,
    )

    msg: str = "Module dependency resolution conflict:"
    # Install project
    with pytest.raises(ConflictingRequirements) as e:
        project.install_modules()
    assert e.value.args[0].startswith(msg)


@pytest.mark.slowtest
def test_module_conflicting_dependencies_with_v1_module(
    snippetcompiler_clean,
    modules_dir: str,
    modules_v2_dir: str,
    tmpdir: py.path.local,
) -> None:
    """
    Show an error message when installing a module that breaks the dependencies
    of another one. modulev1 depends on y~=1.0.0.
    after the install of modulev1 we try to install minimalv2module2 which
    requires y~=2.0.0. those 2 requirements conflict which each other.
    """
    index: PipIndex = PipIndex(artifact_dir=os.path.join(str(tmpdir), ".custom-index"))
    # Create an python package x with version 1.0.0
    create_python_package("y", Version("1.0.0"), str(tmpdir.join("y-1.0.0")), publish_index=index)

    # Create an python package x with version 2.0.0
    create_python_package("y", Version("2.0.0"), str(tmpdir.join("y-2.0.0")), publish_index=index)

    # Create the first module
    module_name1: str = "minimalv1module"
    module_path1: str = str(tmpdir.join("modulev1"))
    v1_module_from_template(
        os.path.join(modules_dir, module_name1),
        module_path1,
        new_name="modulev1",
        new_requirements=[Requirement.parse("y~=1.0.0")],
    )

    # Create the second module
    module_name2: str = "minimalv2module"
    module_path2: str = str(tmpdir.join(module_name2))
    module_from_template(
        os.path.join(modules_v2_dir, module_name2),
        module_path2,
        new_requirements=[Requirement.parse("y~=2.0.0")],
        publish_index=index,
    )

    req = ModuleV2Source.get_python_package_requirement(InmantaModuleRequirement.parse(module_name2))

    # Setup project
    project: Project = snippetcompiler_clean.setup_for_snippet(
        "import modulev1",
        install_project=False,
        python_package_sources=[index.url],
        python_requires=[req],
        autostd=False,
        add_to_module_path=[str(tmpdir)],
    )

    # Install project
    msg: str = "Module dependency resolution conflict:"
    with pytest.raises(ConflictingRequirements) as e:
        project.install_modules()
    assert e.value.args[0].startswith(msg)
