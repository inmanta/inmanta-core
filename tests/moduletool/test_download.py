"""
Copyright 2025 Inmanta

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
import subprocess
import sys
import tempfile

import pytest

import packaging.utils
from inmanta import env, module, moduletool
from libpip2pi.commands import dir2pi
from packaging import version
from utils import module_from_template


@pytest.fixture(scope="session")
def pip_index(modules_v2_dir: str) -> str:
    """
    Returns the path to a pip index that contains several version for the same python package.
    """
    with tempfile.TemporaryDirectory() as root_dir:
        source_dir = os.path.join(root_dir, "source")
        build_dir = os.path.join(root_dir, "build")
        index_dir = os.path.join(build_dir, "simple")

        modules_to_build = [
            ("elaboratev2module", version.Version("1.2.3"), False),
            ("elaboratev2module", version.Version("2.3.4"), False),
            ("elaboratev2module", version.Version("2.3.5"), True),
            ("minimalv2module", version.Version("1.1.1"), False),
        ]

        for module_name, mod_version, is_prerelease in modules_to_build:
            template_dir = os.path.join(modules_v2_dir, module_name)
            module_dir = os.path.join(source_dir, module_name)
            module_from_template(
                source_dir=template_dir,
                dest_dir=module_dir,
                new_version=mod_version,
            )
            moduletool.ModuleTool().build(
                path=module_dir,
                output_dir=build_dir,
                dev_build=is_prerelease,
                wheel=True,
                sdist=True,
            )
            shutil.rmtree(module_dir)

        # The setuptools and wheel packages are required by `pip download`
        subprocess.check_call([sys.executable, "-m", "pip", "download", "setuptools", "wheel"], cwd=build_dir)
        dir2pi(argv=["dir2pi", build_dir])
        yield index_dir


def execute_module_download(module_req: str, install: bool, download_dir: str | None) -> str:
    """
    Executes the `inmanta module download` command and returns the ModuleV2 object for the
    downloaded module.
    """
    if download_dir is None:
        download_dir = os.getcwd()
    module_name: str = module.InmantaModuleRequirement.parse(module_req).name
    assert not os.listdir(download_dir)
    m = moduletool.ModuleTool()
    m.download(module_req=module_req, install=install, directory=download_dir)
    files = os.listdir(download_dir)
    assert len(files) == 1
    assert files[0] == module_name
    return module.ModuleV2(project=None, path=os.path.join(download_dir, module_name))


def assert_files_in_module(
    module_dir: str, module_name: str, has_files_dir: bool, has_templates_dir: bool, has_tests_dir: bool
) -> None:
    """
    Verify that the directory structure of the extracted python package is correct.

    :param has_files_dir: True iff the given module has a files directory.
    :param has_templates_dir: True iff the given module has a templates directory.
    :param has_tests_dir: True iff the given module has a tests directory.
    """
    assert os.path.exists(os.path.join(module_dir, "inmanta_plugins"))
    for file_or_dir, must_exist_in_root_dir in [
        ("tests", has_tests_dir),
        ("files", has_files_dir),
        ("templates", has_templates_dir),
        ("setup.cfg", True),
    ]:
        assert not os.path.exists(os.path.join(module_dir, "inmanta_plugins", module_name, file_or_dir))
        assert os.path.exists(os.path.join(module_dir, file_or_dir)) == must_exist_in_root_dir


def test_module_download(tmpdir, monkeypatch, tmpvenv_active, pip_index: str):
    """
    Test the `inmanta module download` command with a version constraint.
    """
    monkeypatch.setenv("PIP_INDEX_URL", pip_index)
    monkeypatch.setenv("PIP_PRE", "false")
    download_dir = os.path.join(tmpdir, "download")

    # Test download package without constraint
    os.mkdir(download_dir)
    mod: module.ModuleV2 = execute_module_download(module_req="elaboratev2module", install=False, download_dir=download_dir)
    assert_files_in_module(
        module_dir=mod.path, module_name="elaboratev2module", has_files_dir=True, has_templates_dir=True, has_tests_dir=True
    )
    assert mod.version == version.Version("2.3.4")
    shutil.rmtree(download_dir)

    # Test download package with constraint
    os.mkdir(download_dir)
    mod: module.ModuleV2 = execute_module_download(
        module_req="elaboratev2module~=1.2.0", install=False, download_dir=download_dir
    )
    assert_files_in_module(
        module_dir=mod.path, module_name="elaboratev2module", has_files_dir=True, has_templates_dir=True, has_tests_dir=True
    )
    assert mod.version == version.Version("1.2.3")
    shutil.rmtree(download_dir)

    # Test download package with --pre
    os.mkdir(download_dir)
    monkeypatch.setenv("PIP_PRE", "true")
    mod: module.ModuleV2 = execute_module_download(module_req="elaboratev2module", install=False, download_dir=download_dir)
    assert_files_in_module(
        module_dir=mod.path, module_name="elaboratev2module", has_files_dir=True, has_templates_dir=True, has_tests_dir=True
    )
    assert mod.version.base_version == "2.3.5"
    assert mod.version.is_prerelease
    shutil.rmtree(download_dir)

    # Test downloading a package that doesn't have any of the optional directories
    # (e.g. files, templates, tests).
    monkeypatch.setenv("PIP_PRE", "false")
    os.mkdir(download_dir)
    mod: module.ModuleV2 = execute_module_download(module_req="minimalv2module", install=False, download_dir=download_dir)
    assert_files_in_module(
        module_dir=mod.path, module_name="minimalv2module", has_files_dir=False, has_templates_dir=False, has_tests_dir=False
    )
    assert mod.version == version.Version("1.1.1")


def test_module_download_cwd(tmpdir, monkeypatch, tmpvenv_active, pip_index: str):
    """
    Test the `inmanta module download` command when downloading to the current working directory.
    """
    monkeypatch.setenv("PIP_INDEX_URL", pip_index)
    monkeypatch.setenv("PIP_PRE", "false")
    download_dir = os.path.join(tmpdir, "download")
    os.mkdir(download_dir)
    monkeypatch.chdir(download_dir)
    mod: module.ModuleV2 = execute_module_download(module_req="elaboratev2module", install=False, download_dir=None)
    assert_files_in_module(
        module_dir=mod.path, module_name="elaboratev2module", has_files_dir=True, has_templates_dir=True, has_tests_dir=True
    )


def test_module_download_install(tmpdir, monkeypatch, tmpvenv_active, pip_index: str):
    """
    Test the install option of the `inmanta module download` command.
    """
    monkeypatch.setenv("PIP_INDEX_URL", pip_index)
    monkeypatch.setenv("PIP_PRE", "false")
    download_dir = os.path.join(tmpdir, "download")
    os.mkdir(download_dir)
    pkg_name = "inmanta-module-minimalv2module"
    pkgs_installed_in_editable_mode: dict[packaging.utils.NormalizedName, version.Version]
    pkgs_installed_in_editable_mode = env.process_env.get_installed_packages(only_editable=True)
    assert pkg_name not in pkgs_installed_in_editable_mode
    execute_module_download(module_req="minimalv2module", install=True, download_dir=download_dir)
    pkgs_installed_in_editable_mode = env.process_env.get_installed_packages(only_editable=True)
    assert pkg_name in pkgs_installed_in_editable_mode
    assert pkgs_installed_in_editable_mode[pkg_name] == version.Version("1.1.1")


@pytest.mark.parametrize("install", [True, False])
def test_project_download(pip_index: str, snippetcompiler_clean, install: bool):
    """
    Test the `inmanta project download` command and its --install option.
    """
    snippetcompiler_clean.setup_for_snippet(
        snippet="",
        install_project=False,
        python_requires=[
            module.InmantaModuleRequirement.parse("elaboratev2module").get_python_package_requirement(),
            module.InmantaModuleRequirement.parse("minimalv2module").get_python_package_requirement(),
        ],
        use_pip_config_file=False,
        index_url=pip_index,
    )
    downloadpath = snippetcompiler_clean.project.downloadpath
    assert not os.path.exists(downloadpath) or not os.listdir(downloadpath)
    pkgs_installed_in_editable_mode = env.process_env.get_installed_packages(only_editable=False)
    assert "inmanta-module-minimalv2module" not in pkgs_installed_in_editable_mode
    assert "inmanta-module-elaboratev2module" not in pkgs_installed_in_editable_mode

    project_tool = moduletool.ProjectTool()
    project_tool.download(install=install)

    assert len(os.listdir(downloadpath)) == 2
    pkgs_installed_in_editable_mode = env.process_env.get_installed_packages(only_editable=True)
    if install:
        assert ("inmanta-module-minimalv2module" in pkgs_installed_in_editable_mode) == install
        assert pkgs_installed_in_editable_mode["inmanta-module-minimalv2module"] == version.Version("1.1.1")
        assert ("inmanta-module-elaboratev2module" in pkgs_installed_in_editable_mode) == install
        assert pkgs_installed_in_editable_mode["inmanta-module-elaboratev2module"] == version.Version("2.3.4")
    else:
        assert "inmanta-module-minimalv2module" not in pkgs_installed_in_editable_mode
        assert "inmanta-module-elaboratev2module" not in pkgs_installed_in_editable_mode
    assert_files_in_module(
        module_dir=os.path.join(downloadpath, "minimalv2module"),
        module_name="minimalv2module",
        has_files_dir=False,
        has_templates_dir=False,
        has_tests_dir=False,
    )
    assert_files_in_module(
        module_dir=os.path.join(downloadpath, "elaboratev2module"),
        module_name="elaboratev2module",
        has_files_dir=True,
        has_templates_dir=True,
        has_tests_dir=True,
    )


@pytest.mark.parametrize("already_installed", [True, False])
def test_project_download_with_version_constraint(pip_index: str, snippetcompiler_clean, already_installed: bool):
    """
    Verify that the `inmanta project download` command correctly takes into account version constraints.

    :param already_installed: Whether the Inmanta module is already installed in the venv before running
                              the `inmanta project download` command.
    """
    snippetcompiler_clean.setup_for_snippet(
        snippet="",
        install_project=already_installed,
        python_requires=[
            module.InmantaModuleRequirement.parse("elaboratev2module~=1.0").get_python_package_requirement(),
        ],
        use_pip_config_file=False,
        index_url=pip_index,
    )
    downloadpath = snippetcompiler_clean.project.downloadpath
    assert not os.path.exists(downloadpath) or not os.listdir(downloadpath)

    project_tool = moduletool.ProjectTool()
    project_tool.download(install=True)

    assert len(os.listdir(downloadpath)) == 1
    pkgs_installed_in_editable_mode = env.process_env.get_installed_packages(only_editable=True)
    assert pkgs_installed_in_editable_mode["inmanta-module-elaboratev2module"] == version.Version("1.2.3")


def test_project_download_pip_config(pip_index: str, snippetcompiler_clean):
    """
    Verify that the `inmanta project download` command takes into account the pip configuration
    """
    snippetcompiler_clean.setup_for_snippet(
        snippet="",
        install_project=False,
        python_requires=[
            module.InmantaModuleRequirement.parse("elaboratev2module").get_python_package_requirement(),
        ],
        use_pip_config_file=False,
        index_url=pip_index,
        pre=True,
    )
    downloadpath = snippetcompiler_clean.project.downloadpath
    assert not os.path.exists(downloadpath) or not os.listdir(downloadpath)

    project_tool = moduletool.ProjectTool()
    project_tool.download(install=True)

    assert len(os.listdir(downloadpath)) == 1
    pkgs_installed_in_editable_mode = env.process_env.get_installed_packages(only_editable=True)
    assert (
        pkgs_installed_in_editable_mode["inmanta-module-elaboratev2module"].base_version
        == version.Version("2.3.5").base_version
    )


def test_project_download_no_project(tmpdir, monkeypatch):
    """
    Ensure proper error reporting if the `inmanta project download` command is not executed on
    an Inmanta project.
    """
    monkeypatch.chdir(tmpdir)
    project_tool = moduletool.ProjectTool()
    with pytest.raises(module.ProjectNotFoundException) as excinfo:
        project_tool.download(install=False)

    assert "Unable to find an inmanta project" in str(excinfo.value)
