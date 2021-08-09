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
import argparse
import json
import os
import re
import setuptools
import shutil
import subprocess
from dataclasses import dataclass
from importlib.machinery import ModuleSpec
from typing import Dict, Iterable, List, Optional, Tuple
from unittest.mock import patch

import py
import pydantic
import pytest
import yaml
from libpip2pi.commands import dir2pi

from inmanta import env, module
from inmanta.ast import CompilerException, ModuleNotFoundException
from inmanta.config import Config
from inmanta.moduletool import ModuleTool, ProjectTool
from moduletool.common import BadModProvider, install_project


def run_module_install(python_path: str, module_path: str, editable: bool, set_path_argument: bool) -> None:
    """
    Install the Inmanta module (v2) using the `inmanta module install` command.

    :param python_path: Path to the Python executable for the environment to install the module in.
    :param module_path: Path to the inmanta module
    :param editable: Install the module in editable mode (pip install -e).
    :param set_path_argument: If true provide the module_path via the path argument, otherwise the module path is set via cwd.
    """
    if not set_path_argument:
        os.chdir(module_path)
    with patch("inmanta.env.ProcessEnv.python_path", new=python_path):
        ModuleTool().execute("install", argparse.Namespace(editable=editable, path=module_path if set_path_argument else None))


def test_bad_checkout(git_modules_dir, modules_repo):
    coroot = os.path.join(git_modules_dir, "badproject")
    subprocess.check_output(
        ["git", "clone", os.path.join(git_modules_dir, "repos", "badproject")], cwd=git_modules_dir, stderr=subprocess.STDOUT
    )
    os.chdir(coroot)
    Config.load_config()

    with pytest.raises(ModuleNotFoundException):
        ProjectTool().execute("install", [])


def test_bad_setup(git_modules_dir, modules_repo):
    coroot = os.path.join(git_modules_dir, "badprojectx")
    subprocess.check_output(
        ["git", "clone", os.path.join(git_modules_dir, "repos", "badproject"), coroot],
        cwd=git_modules_dir,
        stderr=subprocess.STDOUT,
    )
    os.chdir(coroot)
    Config.load_config()

    mod1 = os.path.join(coroot, "libs", "mod1")
    os.makedirs(mod1)
    subprocess.check_output(
        ["git", "clone", os.path.join(git_modules_dir, "repos", "mod2"), mod1], cwd=git_modules_dir, stderr=subprocess.STDOUT
    )

    with pytest.raises(ModuleNotFoundException):
        ModuleTool().execute("verify", [])


def test_complex_checkout(git_modules_dir, modules_repo):
    coroot = os.path.join(git_modules_dir, "testproject")
    subprocess.check_output(
        ["git", "clone", os.path.join(git_modules_dir, "repos", "testproject")], cwd=git_modules_dir, stderr=subprocess.STDOUT
    )
    os.chdir(coroot)
    Config.load_config()

    ProjectTool().execute("install", [])
    expected = ["mod1", "mod2", "mod3", "mod6", "mod7"]
    for i in expected:
        dirname = os.path.join(coroot, "libs", i)
        assert os.path.exists(os.path.join(dirname, "signal"))
        assert not os.path.exists(os.path.join(dirname, "badsignal"))

    assert not os.path.exists(os.path.join(coroot, "libs", "mod5"))

    # test all tools, perhaps isolate to other test case
    ModuleTool().execute("list", [])
    ModuleTool().execute("update", [])
    ModuleTool().execute("status", [])
    ModuleTool().execute("push", [])


def test_for_git_failures(git_modules_dir, modules_repo):
    coroot = os.path.join(git_modules_dir, "testproject2")
    subprocess.check_output(
        ["git", "clone", os.path.join(git_modules_dir, "repos", "testproject"), "testproject2"],
        cwd=git_modules_dir,
        stderr=subprocess.STDOUT,
    )
    os.chdir(coroot)
    Config.load_config()

    ProjectTool().execute("install", [])

    gp = module.gitprovider
    module.gitprovider = BadModProvider(gp, os.path.join(coroot, "libs", "mod6"))
    try:
        # test all tools, perhaps isolate to other test case
        ProjectTool().execute("install", [])
        ModuleTool().execute("list", [])
        ModuleTool().execute("update", [])
        ModuleTool().execute("status", [])
        ModuleTool().execute("push", [])
    finally:
        module.gitprovider = gp


def test_install_for_git_failures(git_modules_dir, modules_repo):
    coroot = os.path.join(git_modules_dir, "testproject3")
    subprocess.check_output(
        ["git", "clone", os.path.join(git_modules_dir, "repos", "testproject"), "testproject3"],
        cwd=git_modules_dir,
        stderr=subprocess.STDOUT,
    )
    os.chdir(coroot)
    Config.load_config()

    gp = module.gitprovider
    module.gitprovider = BadModProvider(gp, os.path.join(coroot, "libs", "mod6"))
    try:
        with pytest.raises(ModuleNotFoundException):
            ProjectTool().execute("install", [])
    finally:
        module.gitprovider = gp


def test_for_repo_without_versions(git_modules_dir, modules_repo):
    coroot = os.path.join(git_modules_dir, "noverproject")
    subprocess.check_output(
        ["git", "clone", os.path.join(git_modules_dir, "repos", "noverproject")], cwd=git_modules_dir, stderr=subprocess.STDOUT
    )
    os.chdir(coroot)
    Config.load_config()

    ProjectTool().execute("install", [])


def test_bad_dep_checkout(git_modules_dir, modules_repo):
    coroot = os.path.join(git_modules_dir, "baddep")
    subprocess.check_output(
        ["git", "clone", os.path.join(git_modules_dir, "repos", "baddep")], cwd=git_modules_dir, stderr=subprocess.STDOUT
    )
    os.chdir(coroot)
    Config.load_config()

    with pytest.raises(CompilerException):
        ProjectTool().execute("install", [])


def test_master_checkout(git_modules_dir, modules_repo):
    coroot = install_project(git_modules_dir, "masterproject")

    ProjectTool().execute("install", [])

    dirname = os.path.join(coroot, "libs", "mod8")
    assert os.path.exists(os.path.join(dirname, "devsignal"))
    assert os.path.exists(os.path.join(dirname, "mastersignal"))


def test_dev_checkout(git_modules_dir, modules_repo):
    coroot = os.path.join(git_modules_dir, "devproject")
    subprocess.check_output(
        ["git", "clone", os.path.join(git_modules_dir, "repos", "devproject")], cwd=git_modules_dir, stderr=subprocess.STDOUT
    )
    os.chdir(coroot)
    Config.load_config()

    ProjectTool().execute("install", [])

    dirname = os.path.join(coroot, "libs", "mod8")
    assert os.path.exists(os.path.join(dirname, "devsignal"))
    assert not os.path.exists(os.path.join(dirname, "mastersignal"))


@pytest.mark.parametrize("editable", [True, False])
@pytest.mark.parametrize("set_path_argument", [True, False])
def test_module_install(tmpvenv: py.path.local, modules_dir: str, editable: bool, set_path_argument: bool) -> None:
    venv_dir, python_path = tmpvenv

    module_path: str = os.path.join(modules_dir, "minimalv2module")
    python_module_name: str = "inmanta-module-minimalv2module"

    def is_installed(name: str, only_editable: bool = False) -> bool:
        out: str = subprocess.check_output(
            [
                python_path,
                "-m",
                "pip",
                "list",
                "--format",
                "json",
                *(["--editable"] if only_editable else []),
            ]
        ).decode()
        packages: List[Dict[str, str]] = pydantic.parse_raw_as(List[Dict[str, str]], out)
        return any(package["name"] == name for package in packages)

    assert not is_installed(python_module_name)
    run_module_install(python_path, module_path, editable, set_path_argument)
    assert is_installed(python_module_name, True) == editable
    if not editable:
        assert is_installed(python_module_name, False)


def create_local_module_package_index(module_paths: Iterable[str], artifact_path: str) -> Tuple[str, List[str]]:
    """
    Creates a local pip index for one or more v2 modules. The modules are built and published to the index.
    Returns the corresponding fully qualified Python module names.

    :param module_paths: The paths to the modules to include in the index.
    :param artifact_path: The path to place any artifacts in.
    :return: A tuple of the path to the index and a list of the fully qualified Python module names.
    """
    fq_mod_names: List[str] = []
    for path in module_paths:
        ModuleTool().build(path=path, output_dir=artifact_path)
        fq_mod_names.extend(f"inmanta_plugins.{pkg}" for pkg in setuptools.find_packages(os.path.join(path, "inmanta_plugins")))
    dir2pi(argv=["dir2pi", artifact_path])
    return os.path.join(artifact_path, "simple"), fq_mod_names


def setup_simple_project(
    projects_dir: str, path: str, imports: List[str], *, index_urls: Optional[List[str]] = None, github_source: bool = True
) -> module.ProjectMetadata:
    """
    Set up a simple project that imports the given modules and declares the given Python indexes as module sources.

    :param projects_dir: The path to the test projects directory. This is used as a source for the initial project frame.
    :param path: The path to the directory to create the project in.
    :param imports: The modules to import in the project.
    :param index_urls: The urls to any Python indexes to declare as module source.
    :param github_source: Whether to add the inmanta github as a module source.
    """
    shutil.copytree(os.path.join(projects_dir, "simple_project"), path)
    project_config_path: str = os.path.join(path, module.Project.PROJECT_FILE)
    metadata: module.ProjectMetadata
    with open(os.path.join(path, module.Project.PROJECT_FILE), "r+") as fh:
        metadata = module.ProjectMetadata.parse(fh.read())
        metadata.repo = [
            *(module.ModuleRepoInfo(type=module.ModuleRepoType.package, url=index) for index in index_urls),
            *(
                [module.ModuleRepoInfo(type=module.ModuleRepoType.git, url="https://github.com/inmanta/")]
                if github_source
                else []
            ),
        ]
        fh.seek(0)
        # use BaseModel.json instead of BaseModel.dict to correctly serialize attributes
        fh.write(yaml.dump(json.loads(metadata.json())))
        fh.truncate()
    with open(os.path.join(path, "main.cf"), "w") as fh:
        fh.write("\n".join(f"import {module_name}" for module_name in imports))
    return metadata


# TODO: test compilation? Not part of moduletool => compiler tests? Also test trying to compiler without install.
# TODO: test more edge cases!
@pytest.mark.parametrize(
    "install_module_names, module_dependencies",
    [
        (["minimalv2module"], []),
        (["minimalv2module", "elaboratev2module_extension"], ["elaboratev2module"]),
    ]
)
def test_project_install(
    tmpvenv: Tuple[py.path.local, py.path.local],
    tmpdir: py.path.local,
    projects_dir: str,
    modules_dir: str,
    install_module_names: List[str],
    module_dependencies: List[str],
) -> None:
    venv_dir, python_path = tmpvenv

    # set up project and modules
    pip_index_path, fq_mod_names = create_local_module_package_index(
        (os.path.join(modules_dir, module_name) for module_name in install_module_names), os.path.join(tmpdir, ".index")
    )
    fq_mod_names.extend(f"inmanta_plugins.{dep}" for dep in module_dependencies)
    project_path: str = os.path.join(tmpdir, "project")
    metadata: module.ProjectMetadata = setup_simple_project(
        projects_dir, project_path, ["std", *install_module_names], index_urls=[pip_index_path]
    )

    # TODO: this is a hack, additionally it probably won't work with the module loading since it uses importlib to load
    # set up importlib mock to have it run against the mocked active environment
    find_spec_script: str = os.path.join(tmpdir, "find_spec.py")
    with open(find_spec_script, "w") as fh:
        fh.write(
            """
import json
import sys
from typing import Optional

import importlib.util
from importlib.machinery import ModuleSpec


spec: Optional[ModuleSpec]
try:
    spec = importlib.util.find_spec(sys.argv[1])
except ModuleNotFoundError:
    spec = None

print(json.dumps({"origin": spec.origin}) if spec is not None else "null")
            """
        )
    subprocess.check_output([str(python_path), "-m", "pip", "install", "importlib"])

    @dataclass
    class ModuleSpecMock:
        origin: Optional[str]

    def find_spec(module: str) -> Optional[ModuleSpecMock]:
        print(module)
        return pydantic.parse_raw_as(
            Optional[ModuleSpecMock], subprocess.check_output([str(python_path), find_spec_script, module]).decode()
        )

    os.chdir(project_path)
    with patch("inmanta.env.ProcessEnv.python_path", new=str(python_path)):
        with patch("importlib.util.find_spec", new=find_spec):
            for fq_mod_name in fq_mod_names:
                assert env.ProcessEnv.get_module_file(fq_mod_name) is None
            # autostd=True reports std as an import for any module, thus requiring it to be v2 because v2 can not depend on v1
            module.Project.get().autostd = False
            ProjectTool().execute("install", [])
            for fq_mod_name in fq_mod_names:
                print("fq_mod_name", fq_mod_name)
                env_module_file: Optional[str] = env.ProcessEnv.get_module_file(fq_mod_name)
                assert env_module_file is not None
                assert re.fullmatch(
                    os.path.join(venv_dir, "lib", r"python3\.\d+", "site-packages", *fq_mod_name.split("."), r"__init__\.py"),
                    env_module_file,
                )
            v1_mod_dir: str = os.path.join(project_path, metadata.downloadpath)
            assert os.path.exists(v1_mod_dir)
            assert os.listdir(v1_mod_dir) == ["std"]
