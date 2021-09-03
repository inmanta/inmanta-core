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
from typing import List, Set

import py
import pytest

from inmanta.compiler.config import feature_compiler_cache
from inmanta.env import LocalPackagePath
from inmanta.module import ModuleLoadingException, ModuleNotFoundException, ModuleV1, ModuleV2, Project
from inmanta.moduletool import DummyProject, ModuleConverter


@pytest.mark.parametrize("editable_install", [True, False])
def test_v2_module_loading(editable_install: bool, tmpdir: py.path.local, snippetcompiler, capsys, modules_v2_dir: str) -> None:
    # Work around caching problem in venv
    feature_compiler_cache.set("False")
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
        snippetcompiler_clean.setup_for_snippet(f"import {module_name}", install_v2_modules=install_v2_modules, autostd=False)
        caplog.clear()
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


@pytest.mark.parametrize("allow_v1", [True, False])
def test_load_module_v1_already_installed(snippetcompiler, modules_dir: str, allow_v1: bool) -> None:
    """
    Test whether the Project.load_module() method works correctly when loading a V1 module that was already installed
    in the module path.
    """
    module_name = "elaboratev1module"
    module_dir = os.path.join(modules_dir, module_name)
    project: Project = snippetcompiler.setup_for_snippet(snippet=f"import {module_name}", add_to_module_path=[module_dir])

    assert module_name not in project.modules
    if allow_v1:
        project.load_module(module_name=module_name, install=False, allow_v1=allow_v1)
        assert module_name in project.modules
    else:
        with pytest.raises(ModuleNotFoundException, match=f"Could not find module {module_name}"):
            project.load_module(module_name=module_name, install=False, allow_v1=allow_v1)


def test_load_module_v1_module_using_install(snippetcompiler) -> None:
    """
    Test whether the Project.load_module() method works correctly when a module is only available as a V1 module
    and that module is not yet present in the module path.
    """
    module_name = "std"
    project: Project = snippetcompiler.setup_for_snippet(snippet=f"import {module_name}")
    # Remove std module in downloadpath created by other test case
    shutil.rmtree(os.path.join(project.downloadpath, module_name), ignore_errors=True)
    assert module_name not in project.modules
    assert module_name not in os.listdir(project.downloadpath)
    project.load_module(module_name=module_name, allow_v1=True)
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
        snippet=f"import {module_name}", install_v2_modules=[LocalPackagePath(module_dir, editable_install)]
    )

    assert module_name not in project.modules
    project.load_module(module_name=module_name, install=False, allow_v1=allow_v1)
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
        snippet=f"import {module_name}", python_package_source=local_module_package_index
    )
    assert module_name not in project.modules
    assert module_name not in os.listdir(project.downloadpath)
    if install:
        project.load_module(module_name=module_name, install=install, allow_v1=True)
    else:
        with pytest.raises(ModuleNotFoundException, match=f"Could not find module {module_name}"):
            project.load_module(module_name=module_name, install=install, allow_v1=True)
    assert (module_name in project.modules) == install
    assert module_name not in os.listdir(project.downloadpath)


@pytest.mark.parametrize("allow_v1", [True, False])
def test_load_module_module_not_found(snippetcompiler_clean, allow_v1: bool):
    """
    Assert behavior when a module is not found as a V1 or a V2 module.
    """
    module_name = "non_existing_module"
    snippetcompiler_clean.modules_dir = None
    project: Project = snippetcompiler_clean.setup_for_snippet(snippet=f"import {module_name}")
    with pytest.raises(ModuleNotFoundException, match=f"Could not find module {module_name}"):
        project.load_module(module_name=module_name, install=True, allow_v1=allow_v1)


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
    )

    assert module_name not in project.modules
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        project.load_module(module_name=module_name, install=False, allow_v1=True)
    assert f"Module {module_name} is installed as a V1 module and a V2 module: V1 will be ignored." in caplog.text
    assert module_name in project.modules
    assert isinstance(project.modules[module_name], ModuleV2)


@pytest.mark.parametrize("preload_v1_module", [True, False])
def test_load_module_recursive_v2_module_depends_on_v1(
    local_module_package_index: str, snippetcompiler, preload_v1_module: bool) -> None:
    """
    A V2 module cannot depend on a V1 module. This test case ensure that the load_module_recursive() method
    raises an error when a dependency of a V2 module is only available as a V1 module.

    Dependency graph:  v2_depends_on_v1 (V2)  --->  mod1 (V1)
    """
    project = snippetcompiler.setup_for_snippet(
        snippet="import v2_depends_on_v1", python_package_source=local_module_package_index
    )
    if preload_v1_module:
        project.get_module("mod1", allow_v1=True)
    assert ("mod1" in project.modules) == preload_v1_module

    with pytest.raises(ModuleLoadingException, match="could not find module mod1"):
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
        snippet="import complex_module_dependencies_mod1", autostd=False, python_package_source=local_module_package_index
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
