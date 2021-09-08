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
import configparser
import json
import os
import re
import shutil
import subprocess

from importlib.abc import Loader
from itertools import chain
from typing import Dict, Iterator, List, Optional, Set, Tuple

import py
import pytest
import yaml
from pkg_resources import Requirement
from inmanta import env, loader, module
from inmanta.ast import CompilerException
from inmanta.config import Config
from inmanta.module import ModuleLoadingException
from inmanta.moduletool import DummyProject, ModuleConverter, ModuleTool, ProjectTool
from moduletool.common import BadModProvider, install_project, module_from_template, PipIndex
from packaging import version


@pytest.fixture
def build_venv_active(tmpvenv_active: Tuple[py.path.local, py.path.local]) -> Iterator[Tuple[py.path.local, py.path.local]]:
    """
    Yields an active virtual environment that is suitable to build modules with.
    """
    env.process_env.install_from_index([Requirement.parse("build")])
    yield tmpvenv_active


def run_module_install(module_path: str, editable: bool, set_path_argument: bool) -> None:
    """
    Install the Inmanta module (v2) into the active environment using the `inmanta module install` command.

    :param module_path: Path to the inmanta module
    :param editable: Install the module in editable mode (pip install -e).
    :param set_path_argument: If true provide the module_path via the path argument, otherwise the module path is set via cwd.
    """
    if not set_path_argument:
        os.chdir(module_path)
    ModuleTool().execute("install", argparse.Namespace(editable=editable, path=module_path if set_path_argument else None))


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
    index_urls = index_urls if index_urls is not None else []
    shutil.copytree(os.path.join(projects_dir, "simple_project"), path)
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


def test_bad_checkout(git_modules_dir, modules_repo):
    coroot = os.path.join(git_modules_dir, "badproject")
    subprocess.check_output(
        ["git", "clone", os.path.join(git_modules_dir, "repos", "badproject")], cwd=git_modules_dir, stderr=subprocess.STDOUT
    )
    os.chdir(coroot)
    Config.load_config()

    with pytest.raises(ModuleLoadingException):
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

    with pytest.raises(ModuleLoadingException):
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
        with pytest.raises(ModuleLoadingException):
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

    with pytest.raises(CompilerException, match="Not all module dependencies have been met"):
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
def test_module_install(
    build_venv_active: Tuple[py.path.local, py.path.local], modules_v2_dir: str, editable: bool, set_path_argument: bool
) -> None:
    """
    Install a simple v2 module with the `inmanta module install` command. Make sure the command works with all possible values
    for its options.
    """
    module_path: str = os.path.join(modules_v2_dir, "minimalv2module")
    python_module_name: str = "inmanta-module-minimalv2module"

    def is_installed(name: str, only_editable: bool = False) -> bool:
        return name in env.process_env.get_installed_packages(only_editable=only_editable)

    assert not is_installed(python_module_name)
    run_module_install(module_path, editable, set_path_argument)
    assert is_installed(python_module_name, True) == editable
    if not editable:
        assert is_installed(python_module_name, False)


@pytest.mark.parametrize("dev", [True, False])
def test_module_install_version(
    tmpdir: py.path.local,
    tmpvenv_active: Tuple[py.path.local, py.path.local],
    projects_dir: str,
    modules_v2_dir: str,
    dev: bool,
) -> None:
    """
    Make sure that the module install results in a module instance with the appropriate version information.
    :param dev: whether to add a dev tag to the version
    """
    module_name: str = "minimalv2module"
    module_path: str = os.path.join(str(tmpdir), module_name)
    plain_version: version.Version = version.Version("1.2.3")
    full_version: version.Version = plain_version if not dev else version.Version(f"{plain_version}.dev0")

    module_from_template(
        os.path.join(modules_v2_dir, module_name),
        module_path,
        new_version=plain_version,
        dev_version=dev,
    )
    project_dir: str = os.path.join(str(tmpdir), "project")
    setup_simple_project(projects_dir, project_dir, [])
    os.chdir(project_dir)

    ModuleTool().install(editable=True, path=module_path)
    mod: module.Module = ModuleTool().get_module(module_name)
    assert mod.version == full_version


@pytest.mark.parametrize(
    "install_module_names, module_dependencies",
    [
        (["minimalv2module"], []),
        # include module with _ to make sure that works as well
        (["minimalv2module", "elaboratev2module_extension"], ["elaboratev2module"]),
    ],
)
def test_project_install(
    local_module_package_index: str,
    tmpvenv_active: Tuple[py.path.local, py.path.local],
    tmpdir: py.path.local,
    projects_dir: str,
    install_module_names: List[str],
    module_dependencies: List[str],
) -> None:
    """
    Install a simple inmanta project with `inmanta project install`. Make sure both v1 and v2 modules are installed
    as expected.
    """
    fq_mod_names: List[str] = [f"inmanta_plugins.{mod}" for mod in chain(install_module_names, module_dependencies)]

    # set up project and modules
    project_path: str = os.path.join(tmpdir, "project")
    metadata: module.ProjectMetadata = setup_simple_project(
        projects_dir, project_path, ["std", *install_module_names], index_urls=[local_module_package_index]
    )

    os.chdir(project_path)
    for fq_mod_name in fq_mod_names:
        assert env.process_env.get_module_file(fq_mod_name) is None
    # autostd=True reports std as an import for any module, thus requiring it to be v2 because v2 can not depend on v1
    module.Project.get().autostd = False
    ProjectTool().execute("install", [])
    for fq_mod_name in fq_mod_names:
        module_info: Optional[Tuple[Optional[str], Loader]] = env.process_env.get_module_file(fq_mod_name)
        env_module_file, module_loader = module_info
        assert not isinstance(module_loader, loader.PluginModuleLoader)
        assert env_module_file is not None
        assert env_module_file == os.path.join(env.process_env.site_packages_dir, *fq_mod_name.split("."), "__init__.py")
    v1_mod_dir: str = os.path.join(project_path, metadata.downloadpath)
    assert os.path.exists(v1_mod_dir)
    assert os.listdir(v1_mod_dir) == ["std"]


@pytest.mark.parametrize("editable", [True, False])
def test_project_install_preinstalled(
    local_module_package_index: str,
    build_venv_active: Tuple[py.path.local, py.path.local],
    tmpdir: py.path.local,
    modules_v2_dir: str,
    projects_dir: str,
    editable: bool,
) -> None:
    """
    Verify that `inmanta project install` does not override preinstalled modules.
    """
    module_name: str = "minimalv2module"
    fq_mod_name: str = "inmanta_plugins.minimalv2module"

    assert env.process_env.get_module_file(fq_mod_name) is None

    # preinstall older version of module
    module_path: str = os.path.join(str(tmpdir), module_name)
    metadata: module.ModuleV2Metadata = module_from_template(
        os.path.join(modules_v2_dir, module_name), module_path, dev_version=True, install=True, editable=editable
    )

    def assert_module_install() -> None:
        module_info: Optional[Tuple[Optional[str], Loader]] = env.process_env.get_module_file(fq_mod_name)
        env_module_file, module_loader = module_info
        assert not isinstance(module_loader, loader.PluginModuleLoader)
        assert env_module_file is not None
        install_path: str = module_path if editable else env.process_env.site_packages_dir
        assert env_module_file == os.path.join(install_path, *fq_mod_name.split("."), "__init__.py")
        assert env.process_env.get_installed_packages(only_editable=editable).get(
            f"{module.ModuleV2.PKG_NAME_PREFIX}{module_name}", None
        ) == version.Version(metadata.version + ".dev0")

    assert_module_install()

    # set up project and modules
    project_path: str = os.path.join(str(tmpdir), "project")
    setup_simple_project(projects_dir, project_path, ["std", module_name], index_urls=[local_module_package_index])

    os.chdir(project_path)
    # autostd=True reports std as an import for any module, thus requiring it to be v2 because v2 can not depend on v1
    module.Project.get().autostd = False
    ProjectTool().execute("install", [])
    assert_module_install()


@pytest.mark.parametrize("preinstall_v2", [True, False])
def test_project_install_modules_cache_invalid(
    caplog,
    local_module_package_index: str,
    snippetcompiler_clean,
    tmpdir: py.path.local,
    modules_dir: str,
    modules_v2_dir: str,
    preinstall_v2: bool,
) -> None:
    """
    Verify that introducing invalidities in the modules cache results in the appropriate exception and warnings.

    :param preinstall_v2: Whether the preinstalled module should be a v2.
    """
    module_name: str = "minimalv1module"
    fq_mod_name: str = "inmanta_plugins.minimalv1module"
    index: PipIndex = PipIndex(artifact_dir=os.path.join(str(tmpdir), ".custom-index"))

    assert env.process_env.get_module_file(fq_mod_name) is None

    # prepare v2 module
    v2_template_path: str = os.path.join(str(tmpdir), module_name)
    v1: module.ModuleV1 = module.ModuleV1(project=DummyProject(autostd=False), path=os.path.join(modules_dir, module_name))
    v2_version: version.Version = version.Version(str(v1.version.major + 1) + ".0.0")
    ModuleConverter(v1).convert(output_directory=v2_template_path)
    module_from_template(
        v2_template_path, os.path.join(str(tmpdir), module_name, "stable"), new_version=v2_version, publish_index=index
    )

    # prepare second module that depends on stable v2 version of first module
    new_module_name: str = f"{module_name}2"
    module_from_template(
        v2_template_path,
        os.path.join(str(tmpdir), new_module_name),
        new_name=new_module_name,
        # requires stable version, not currently installed dev version
        new_requirements=[module.InmantaModuleRequirement.parse(f"{module_name}>={v2_version}")],
        install=False,
        publish_index=index,
    )

    # preinstall module
    if preinstall_v2:
        # set up project, including activation of venv
        snippetcompiler_clean.setup_for_snippet("")
        # install older v2 module
        module_from_template(
            v2_template_path,
            os.path.join(str(tmpdir), module_name, "dev"),
            new_version=v2_version,
            dev_version=True,
            install=True,
        )
    else:
        # install module as v1
        snippetcompiler_clean.setup_for_snippet(
            f"import {module_name}",
            autostd=False,
        )
        ProjectTool().execute("install", [])

    # set up project for installation
    snippetcompiler_clean.setup_for_snippet(
        f"""
        import {new_module_name}
        import {module_name}
        """,
        autostd=False,
        python_package_sources=[index.url, local_module_package_index],
    )

    if not preinstall_v2:
        # populate project.modules[module_name]
        module.Project.get().get_module(module_name, install=False, allow_v1=True)

    os.chdir(module.Project.get().path)
    with pytest.raises(
        CompilerException,
        match=(
            "Not all modules were loaded correctly as a result of transient dependencies."
            " A recompile should load them correctly."
        ),
    ):
        ProjectTool().execute("install", [])

    message: str = (
        f"Compiler has loaded module {module_name}=={v2_version}.dev0 but {module_name}=={v2_version} has"
        " later been installed as a side effect."
        if preinstall_v2
        else f"Compiler has loaded module {module_name} as v1 but it has later been installed as v2 as a side effect."
    )

    assert message in (rec.message for rec in caplog.records)


def test_project_install_incompatible_versions(
    caplog,
    snippetcompiler_clean,
    tmpdir: py.path.local,
    modules_dir: str,
    modules_v2_dir: str,
) -> None:
    """
    Verify that introducing module version incompatibilities results in the appropriate exception and warnings.
    """
    # declare conflicting module parameters
    current_version: version.Version = version.Version("1.0.0")
    req_v1_on_v1: module.InmantaModuleRequirement = module.InmantaModuleRequirement.parse("v1mod1>42")
    req_v1_on_v2: module.InmantaModuleRequirement = module.InmantaModuleRequirement.parse("v2mod>42")

    # prepare v1 modules
    v1_modules_path: str = os.path.join(str(tmpdir), "libs")
    v1mod1_path: str = os.path.join(v1_modules_path, "v1mod1")
    shutil.copytree(os.path.join(modules_dir, "minimalv1module"), v1mod1_path)
    with open(os.path.join(v1mod1_path, module.ModuleV1.MODULE_FILE), "r+") as fh:
        config: Dict[str, object] = yaml.safe_load(fh)
        config["name"] = "v1mod1"
        config["version"] = str(current_version)
        fh.seek(0)
        yaml.dump(config, fh)
    v1mod2_path: str = os.path.join(v1_modules_path, "v1mod2")
    shutil.copytree(os.path.join(modules_dir, "minimalv1module"), v1mod2_path)
    with open(os.path.join(v1mod2_path, module.ModuleV1.MODULE_FILE), "r+") as fh:
        config: Dict[str, object] = yaml.safe_load(fh)
        config["name"] = "v1mod2"
        config["requires"] = [str(req_v1_on_v2), str(req_v1_on_v1)]
        fh.seek(0)
        yaml.dump(config, fh)

    # prepare v2 module
    index: PipIndex = PipIndex(artifact_dir=os.path.join(str(tmpdir), ".custom-index"))
    module_from_template(
        os.path.join(modules_v2_dir, "minimalv2module"),
        os.path.join(str(tmpdir), "v2mod"),
        new_version=current_version,
        new_name="v2mod",
        publish_index=index,
    )

    # set up project
    snippetcompiler_clean.setup_for_snippet(
        """
        import v1mod2
        import v1mod1
        import v2mod
        """,
        autostd=False,
        add_to_module_path=[v1_modules_path],
        python_package_sources=[index.url],
    )

    # install project
    os.chdir(module.Project.get().path)
    with pytest.raises(
        CompilerException, match="Not all module dependencies have been met. Run `inmanta modules update` to resolve this."
    ):
        ProjectTool().execute("install", [])

    log_messages: Set[str] = {rec.message for rec in caplog.records}
    expected: Set[str] = {
        f"requirement {req_v1_on_v1} on module v1mod1 not fulfilled, now at version {current_version}",
        f"requirement {req_v1_on_v2} on module v2mod not fulfilled, now at version {current_version}",
    }
    assert expected.issubset(log_messages)


def test_project_install_incompatible_dependencies(
    caplog,
    snippetcompiler_clean,
    tmpdir: py.path.local,
    modules_dir: str,
    modules_v2_dir: str,
) -> None:
    """
    Verify that introducing version incompatibilities in the Python environment results in the appropriate exception and
    warnings.
    """
    index: PipIndex = PipIndex(artifact_dir=os.path.join(str(tmpdir), ".custom-index"))

    # prepare v2 modules
    v2_template_path: str = os.path.join(modules_v2_dir, "minimalv2module")
    v2mod1: module.ModuleV2Metadata = module_from_template(
        v2_template_path,
        os.path.join(str(tmpdir), "v2mod1"),
        new_name="v2mod1",
        new_requirements=[Requirement.parse("more-itertools~=7.0")],
        publish_index=index,
    )
    v2mod2: module.ModuleV2Metadata = module_from_template(
        v2_template_path,
        os.path.join(str(tmpdir), "v2mod2"),
        new_name="v2mod2",
        new_requirements=[Requirement.parse("more-itertools~=8.0")],
        publish_index=index,
    )

    # set up project
    snippetcompiler_clean.setup_for_snippet(
        f"""
        import {module.ModuleV2.get_name_from_metadata(v2mod1)}
        import {module.ModuleV2.get_name_from_metadata(v2mod2)}
        """,
        autostd=False,
        python_package_sources=[index.url, "https://pypi.org/simple"],
    )

    # install project
    os.chdir(module.Project.get().path)
    with pytest.raises(
        CompilerException,
        match=(
            "Not all installed modules are compatible: requirements conflicts were found. Please resolve any conflicts before"
            " attempting another compile. Run `pip check` to check for any incompatibilities."
        ),
    ):
        ProjectTool().execute("install", [])

    assert any(
        re.match("Incompatibility between constraint more-itertools~=[78].0 and installed version [78]\\..*", rec.message)
        is not None
        for rec in caplog.records
    )
