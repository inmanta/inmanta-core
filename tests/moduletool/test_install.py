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
import logging
import os
import re
import shutil
import subprocess
from datetime import datetime
from importlib.abc import Loader
from itertools import chain
from typing import Dict, Iterator, List, Optional, Tuple

import py
import pytest
import yaml
from pkg_resources import Requirement

from inmanta import compiler, const, env, loader, module
from inmanta.ast import CompilerException
from inmanta.config import Config
from inmanta.env import ConflictingRequirements, PackageNotFound, PythonEnvironment
from inmanta.module import InmantaModuleRequirement, InstallMode, ModuleLoadingException, ModuleNotFoundException
from inmanta.moduletool import DummyProject, ModuleConverter, ModuleTool, ProjectTool
from moduletool.common import BadModProvider, install_project
from packaging import version
from utils import PipIndex, log_contains, module_from_template


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

    with pytest.raises(CompilerException, match="requirement mod2<2016 on module mod2 not fulfilled, now at version 2016.1"):
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


@pytest.mark.parametrize_any("editable", [True, False])
@pytest.mark.parametrize_any("set_path_argument", [True, False])
def test_module_install(snippetcompiler_clean, modules_v2_dir: str, editable: bool, set_path_argument: bool) -> None:
    """
    Install a simple v2 module with the `inmanta module install` command. Make sure the command works with all possible values
    for its options.
    """
    # activate snippetcompiler's venv
    snippetcompiler_clean.setup_for_snippet("")

    module_path: str = os.path.join(modules_v2_dir, "minimalv2module")
    python_module_name: str = "inmanta-module-minimalv2module"

    def is_installed(name: str, only_editable: bool = False) -> bool:
        return name in env.process_env.get_installed_packages(only_editable=only_editable)

    assert not is_installed(python_module_name)
    run_module_install(module_path, editable, set_path_argument)
    assert is_installed(python_module_name, True) == editable
    if not editable:
        assert is_installed(python_module_name, False)


@pytest.mark.parametrize_any("dev", [True, False])
def test_module_install_version(
    tmpdir: py.path.local,
    snippetcompiler_clean,
    modules_v2_dir: str,
    dev: bool,
) -> None:
    """
    Make sure that the module install results in a module instance with the appropriate version information.
    :param dev: whether to add a dev tag to the version
    """
    module_name: str = "minimalv2module"
    module_path: str = os.path.join(str(tmpdir), module_name)
    module_version: version.Version = version.Version("1.2.3") if not dev else version.Version("1.2.3.dev0")

    # set up simple project and activate the snippetcompiler venv
    project: module.Project = snippetcompiler_clean.setup_for_snippet("")

    # install module
    module_from_template(
        os.path.join(modules_v2_dir, module_name),
        module_path,
        new_version=module_version,
    )
    os.chdir(project.path)
    ModuleTool().install(editable=True, path=module_path)

    # check version
    mod: module.Module = ModuleTool().get_module(module_name)
    assert mod.version == module_version


@pytest.mark.slowtest
def test_module_install_reinstall(
    tmpdir: py.path.local,
    snippetcompiler_clean,
    modules_v2_dir,
) -> None:
    """
    Verify that reinstalling a module from source installs any changes to model and Python files if the version is bumped.
    """
    module_name: str = "minimalv2module"
    module_path: str = str(tmpdir.join(module_name))
    module_from_template(
        os.path.join(modules_v2_dir, module_name),
        dest_dir=module_path,
        new_version=version.Version("1.0.0"),
    )

    # set up simple project and activate snippetcompiler venv
    snippetcompiler_clean.setup_for_snippet("")

    def new_files_exist() -> Iterator[bool]:
        return (
            os.path.exists(os.path.join(env.process_env.site_packages_dir, const.PLUGINS_PACKAGE, module_name, rel_path))
            for rel_path in [os.path.join("model", "newmod.cf"), "newmod.py"]
        )

    # install module
    ModuleTool().install(editable=False, path=module_path)

    assert not any(new_files_exist())

    # make some changes to the source and install again
    model_dir: str = os.path.join(module_path, "model")
    os.makedirs(model_dir, exist_ok=True)
    open(os.path.join(model_dir, "newmod.cf"), "w").close()
    open(os.path.join(module_path, const.PLUGINS_PACKAGE, module_name, "newmod.py"), "w").close()
    module_from_template(module_path, new_version=version.Version("2.0.0"), in_place=True)
    ModuleTool().install(editable=False, path=module_path)

    assert all(new_files_exist())


@pytest.mark.slowtest
def test_3322_module_install_deep_data_files(tmpdir: py.path.local, snippetcompiler_clean, modules_v2_dir: str) -> None:
    """
    Verify that module installation includes data files regardless of depth in the directory structure.
    """
    # set up module directory
    module_name: str = "minimalv2module"
    module_path: str = str(tmpdir.join(module_name))
    module_from_template(
        os.path.join(modules_v2_dir, module_name),
        module_path,
    )
    deep_model_file_rel: str = os.path.join(
        "model",
        *(str(i) for i in range(10)),
        "mymod.cf",
    )
    os.makedirs(os.path.join(module_path, os.path.dirname(deep_model_file_rel)))
    open(os.path.join(module_path, deep_model_file_rel), "w").close()

    # set up simple project and activate snippetcompiler venv
    snippetcompiler_clean.setup_for_snippet("")

    # install module: non-editable mode
    ModuleTool().install(editable=False, path=module_path)

    assert os.path.exists(
        os.path.join(
            env.process_env.site_packages_dir,
            const.PLUGINS_PACKAGE,
            module_name,
            deep_model_file_rel,
        )
    )


def test_3322_module_install_preinstall_cleanup(tmpdir: py.path.local, snippetcompiler_clean, modules_v2_dir: str) -> None:
    """
    Verify that installing a module from source cleans up any old installation's data files.
    """
    # set up module directory
    module_name: str = "minimalv2module"
    module_path: str = str(tmpdir.join(module_name))
    module_from_template(
        os.path.join(modules_v2_dir, module_name),
        module_path,
        new_version=version.Version("1.0.0"),
    )
    model_file_rel: str = os.path.join("model", "mymod.cf")
    model_file_source_path: str = os.path.join(module_path, model_file_rel)
    assert not os.path.exists(model_file_source_path)
    open(model_file_source_path, "w").close()

    def model_file_installed() -> bool:
        return os.path.exists(
            os.path.join(
                env.process_env.site_packages_dir,
                const.PLUGINS_PACKAGE,
                module_name,
                model_file_rel,
            )
        )

    # set up simple project and activate snippetcompiler venv
    snippetcompiler_clean.setup_for_snippet("")

    # install module: non-editable mode
    ModuleTool().install(editable=False, path=module_path)
    assert model_file_installed()

    # remove model file and reinstall
    os.remove(model_file_source_path)
    module_from_template(
        module_path,
        new_version=version.Version("2.0.0"),
        in_place=True,
    )
    ModuleTool().install(editable=False, path=module_path)
    assert not model_file_installed()


@pytest.mark.parametrize_any(
    "install_module_names, module_dependencies",
    [
        (["minimalv2module"], []),
        # include module with _ to make sure that works as well
        (["minimalv2module", "elaboratev2module_extension"], ["elaboratev2module"]),
    ],
)
def test_project_install(
    local_module_package_index: str,
    snippetcompiler_clean,
    install_module_names: List[str],
    module_dependencies: List[str],
) -> None:
    """
    Install a simple inmanta project with `inmanta project install`. Make sure both v1 and v2 modules are installed
    as expected.
    """

    fq_mod_names: List[str] = [f"inmanta_plugins.{mod}" for mod in chain(install_module_names, module_dependencies)]

    # set up project and modules
    project: module.Project = snippetcompiler_clean.setup_for_snippet(
        "\n".join(f"import {mod}" for mod in ["std", *install_module_names]),
        autostd=False,
        python_package_sources=[local_module_package_index],
        python_requires=[Requirement.parse(module.ModuleV2Source.get_package_name_for(mod)) for mod in install_module_names],
        install_project=False,
    )

    os.chdir(project.path)
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
    v1_mod_dir: str = os.path.join(project.path, project.downloadpath)
    assert os.path.exists(v1_mod_dir)
    assert os.listdir(v1_mod_dir) == ["std"]

    # ensure we can compile
    compiler.do_compile()

    # add a dependency
    project: module.Project = snippetcompiler_clean.setup_for_snippet(
        "\n".join(f"import {mod}" for mod in ["std", *install_module_names]),
        autostd=False,
        python_package_sources=[local_module_package_index],
        python_requires=[Requirement.parse(module.ModuleV2Source.get_package_name_for(mod)) for mod in install_module_names]
        + ["lorem"],
        install_project=False,
    )

    with pytest.raises(
        expected_exception=ConflictingRequirements,
        match=re.escape("Not all required python packages are installed run 'inmanta project install' to resolve this"),
    ):
        # ensure we can compile
        compiler.do_compile()


@pytest.mark.parametrize_any("editable", [True, False])
@pytest.mark.slowtest
def test_project_install_preinstalled(
    local_module_package_index: str,
    snippetcompiler_clean,
    tmpdir: py.path.local,
    modules_v2_dir: str,
    editable: bool,
) -> None:
    """
    Verify that `inmanta project install` does not override preinstalled modules.
    """
    module_name: str = "minimalv2module"
    fq_mod_name: str = "inmanta_plugins.minimalv2module"

    assert env.process_env.get_module_file(fq_mod_name) is None

    # activate snippetcompiler venv
    snippetcompiler_clean.setup_for_snippet("")

    # preinstall older version of module
    module_path: str = os.path.join(str(tmpdir), module_name)
    new_version = version.Version("1.2.3.dev0")
    module_from_template(
        os.path.join(modules_v2_dir, module_name), module_path, new_version=new_version, install=True, editable=editable
    )

    def assert_module_install() -> None:
        module_info: Optional[Tuple[Optional[str], Loader]] = env.process_env.get_module_file(fq_mod_name)
        env_module_file, module_loader = module_info
        assert not isinstance(module_loader, loader.PluginModuleLoader)
        assert env_module_file is not None
        install_path: str = module_path if editable else env.process_env.site_packages_dir
        assert env_module_file == os.path.join(install_path, *fq_mod_name.split("."), "__init__.py")
        assert (
            env.process_env.get_installed_packages(only_editable=editable).get(
                f"{module.ModuleV2.PKG_NAME_PREFIX}{module_name}", None
            )
            == new_version
        )

    assert_module_install()

    # set up project and modules
    project: module.Project = snippetcompiler_clean.setup_for_snippet(
        f"import {module_name}", autostd=False, python_package_sources=[local_module_package_index]
    )

    os.chdir(project.path)
    # autostd=True reports std as an import for any module, thus requiring it to be v2 because v2 can not depend on v1
    module.Project.get().autostd = False
    ProjectTool().execute("install", [])
    assert_module_install()


@pytest.mark.slowtest
def test_project_install_modules_cache_invalid(
    caplog,
    local_module_package_index: str,
    snippetcompiler_clean,
    tmpdir: py.path.local,
    modules_dir: str,
    modules_v2_dir: str,
) -> None:
    """
    Verify that introducing invalidities in the modules cache results in the appropriate exception and warnings.

    - preinstall old (v1 or v2) version of {dependency_module}
    - install project with {main_module} that depends on {dependency_module}>={v2_version}
    """
    main_module: str = "main_module"
    dependency_module: str = "minimalv1module"
    fq_mod_name: str = "inmanta_plugins.minimalv1module"
    index: PipIndex = PipIndex(artifact_dir=os.path.join(str(tmpdir), ".custom-index"))
    libs_dir: str = os.path.join(str(tmpdir), "libs")
    os.makedirs(libs_dir)

    assert env.process_env.get_module_file(fq_mod_name) is None

    # prepare most recent v2 module
    v2_template_path: str = os.path.join(str(tmpdir), dependency_module)
    v1: module.ModuleV1 = module.ModuleV1(
        project=DummyProject(autostd=False), path=os.path.join(modules_dir, dependency_module)
    )
    v2_version: version.Version = version.Version(str(v1.version.major + 1) + ".0.0")
    ModuleConverter(v1).convert(output_directory=v2_template_path)
    module_from_template(
        v2_template_path, os.path.join(str(tmpdir), dependency_module, "stable"), new_version=v2_version, publish_index=index
    )

    # prepare main module that depends on stable v2 version of first module
    module_from_template(
        v2_template_path,
        os.path.join(str(tmpdir), main_module),
        new_name=main_module,
        new_content_init_cf=f"import {dependency_module}",
        # requires stable version, not currently installed dev version
        new_requirements=[module.InmantaModuleRequirement.parse(f"{dependency_module}>={v2_version}")],
        install=False,
        publish_index=index,
    )

    # preinstall module
    # set up project, including activation of venv before installing the module
    snippetcompiler_clean.setup_for_snippet("", install_project=False)
    # install older v2 module
    module_from_template(
        v2_template_path,
        os.path.join(str(tmpdir), dependency_module, "dev"),
        new_version=version.Version(f"{v2_version}.dev0"),
        install=True,
    )

    # set up project for installation
    project: module.Project = snippetcompiler_clean.setup_for_snippet(
        f"import {main_module}",
        autostd=False,
        install_project=False,
        add_to_module_path=[libs_dir],
        python_package_sources=[index.url, local_module_package_index],
        # make sure main module gets installed, pulling in newest version of dependency module
        python_requires=[Requirement.parse(module.ModuleV2Source.get_package_name_for(main_module))],
    )

    # populate project.modules[dependency_module] to force the error conditions in this simplified example
    project.get_module(dependency_module, allow_v1=True)

    os.chdir(project.path)
    with pytest.raises(
        CompilerException,
        match=(
            "Not all modules were loaded correctly as a result of transitive dependencies."
            " A recompile should load them correctly."
        ),
    ):
        ProjectTool().execute("install", [])

    message: str = (
        f"Compiler has loaded module {dependency_module}=={v2_version}.dev0 but {dependency_module}=={v2_version} has"
        " later been installed as a side effect."
    )

    assert message in (rec.message for rec in caplog.records)


@pytest.mark.parametrize_any("autostd", [True, False])
def test_project_install_incompatible_versions(
    caplog,
    snippetcompiler_clean,
    tmpdir: py.path.local,
    modules_dir: str,
    modules_v2_dir: str,
    autostd: bool,
) -> None:
    """
    Verify that introducing module version incompatibilities results in the appropriate exception and warnings.
    Make sure this works both for autostd (no explicit import) and for standard modules.
    """
    v2_mod_name: str = "std" if autostd else "v2mod"

    # declare conflicting module parameters
    current_version: version.Version = version.Version("1.0.0")
    req_v1_on_v1: module.InmantaModuleRequirement = module.InmantaModuleRequirement.parse("v1mod1>42")
    req_v1_on_v2: module.InmantaModuleRequirement = module.InmantaModuleRequirement.parse(f"{v2_mod_name}>10000")

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
        os.path.join(str(tmpdir), v2_mod_name),
        new_version=current_version,
        new_name=v2_mod_name,
        publish_index=index,
    )

    # set up project
    snippetcompiler_clean.setup_for_snippet(
        """
        import v1mod2
        import v1mod1
        %s
        """
        % (f"import {v2_mod_name}" if not autostd else ""),
        autostd=autostd,
        install_project=False,
        add_to_module_path=[v1_modules_path],
        python_package_sources=[index.url],
        python_requires=[Requirement.parse(module.ModuleV2Source.get_package_name_for(v2_mod_name))],
    )

    # install project
    os.chdir(module.Project.get().path)
    with pytest.raises(CompilerException) as excinfo:
        ProjectTool().execute("install", [])

    assert f"""
The following requirements were not satisfied:
\t* requirement {req_v1_on_v2} on module {v2_mod_name} not fulfilled, now at version {current_version}.
\t* requirement {req_v1_on_v1} on module v1mod1 not fulfilled, now at version {current_version}.
Run `inmanta project update` to resolve this.
    """.strip() in str(
        excinfo.value
    )


@pytest.mark.slowtest
def test_project_install_incompatible_dependencies(
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
        new_requirements=[Requirement.parse("lorem~=0.0.1")],
        publish_index=index,
    )
    v2mod2: module.ModuleV2Metadata = module_from_template(
        v2_template_path,
        os.path.join(str(tmpdir), "v2mod2"),
        new_name="v2mod2",
        new_requirements=[Requirement.parse("lorem~=0.1.1")],
        publish_index=index,
    )

    # set up project
    snippetcompiler_clean.setup_for_snippet(
        f"""
        import {module.ModuleV2.get_name_from_metadata(v2mod1)}
        import {module.ModuleV2.get_name_from_metadata(v2mod2)}
        """,
        autostd=False,
        install_project=False,
        python_package_sources=[index.url, "https://pypi.org/simple"],
        python_requires=[
            Requirement.parse(module.ModuleV2Source.get_package_name_for(module.ModuleV2.get_name_from_metadata(metadata)))
            for metadata in [v2mod1, v2mod2]
        ],
    )

    # install project
    os.chdir(module.Project.get().path)
    with pytest.raises(env.ConflictingRequirements) as e:
        ProjectTool().execute("install", [])
    assert "lorem~=0.0.1 and lorem~=0.1.1 because these package versions have conflicting dependencies" in e.value.msg


def test_project_install_requirement_not_loaded(
    caplog,
    snippetcompiler,
) -> None:
    """
    Verify that installing a project with a module requirement does not fail if the module is not loaded in the project's AST.
    """
    module_name: str = "thismoduledoesnotexist"
    with caplog.at_level(logging.WARNING):
        # make sure the project installation does not fail on verification
        snippetcompiler.setup_for_snippet(
            "",
            project_requires=[module.InmantaModuleRequirement.parse(module_name)],
            install_project=True,
        )

    message: str = "Module thismoduledoesnotexist is present in requires but it is not used by the model."
    assert message in (rec.message for rec in caplog.records)


@pytest.mark.parametrize_any("install_mode", [None, InstallMode.release, InstallMode.prerelease, InstallMode.master])
def test_project_install_with_install_mode(
    tmpdir: py.path.local, modules_v2_dir: str, snippetcompiler_clean, install_mode: Optional[str]
) -> None:
    """
    Test whether the `inmanta module install` command takes into account the `install_mode` configured on the inmanta project.
    """
    index: PipIndex = PipIndex(artifact_dir=os.path.join(str(tmpdir), ".custom-index"))

    module_template_path: str = os.path.join(modules_v2_dir, "elaboratev2module")
    module_name: str = "mod"
    package_name: str = module.ModuleV2Source.get_package_name_for(module_name)
    for module_version in ["1.0.0", "1.0.1.dev0"]:
        module_from_template(
            module_template_path,
            os.path.join(str(tmpdir), f"mod-{module_version}"),
            new_name=module_name,
            new_version=version.Version(module_version),
            publish_index=index,
        )

    # set up project
    snippetcompiler_clean.setup_for_snippet(
        f"import {module_name}",
        autostd=False,
        python_package_sources=[index.url],
        python_requires=[Requirement.parse(package_name)],
        install_mode=install_mode,
    )

    os.chdir(module.Project.get().path)
    ProjectTool().execute("install", [])

    if install_mode is None or install_mode == InstallMode.release:
        expected_version = version.Version("1.0.0")
    else:
        expected_version = version.Version("1.0.1.dev0")
    installed_packages: Dict[str, version.Version] = env.process_env.get_installed_packages()
    assert package_name in installed_packages
    assert installed_packages[package_name] == expected_version


@pytest.mark.slowtest
def test_moduletool_list(
    capsys, tmpdir: py.path.local, local_module_package_index: str, snippetcompiler_clean, modules_v2_dir: str
) -> None:
    """
    Verify that `inmanta module list` correctly lists all installed modules, both v1 and v2.
    """
    # set up venv
    snippetcompiler_clean.setup_for_snippet("", autostd=False)

    module_template_path: str = os.path.join(modules_v2_dir, "minimalv2module")
    module_from_template(
        module_template_path,
        str(tmpdir.join("custom_mod_one")),
        new_name="custom_mod_one",
        new_version=version.Version("1.0.0"),
        install=True,
        editable=False,
    )
    module_from_template(
        module_template_path,
        str(tmpdir.join("custom_mod_two")),
        new_name="custom_mod_two",
        new_version=version.Version("1.0.0"),
        new_content_init_cf="import custom_mod_one",
        new_requirements=[module.InmantaModuleRequirement.parse("custom_mod_one~=1.0")],
        install=True,
        editable=True,
    )

    # set up project with a v1 and a v2 module
    project: module.Project = snippetcompiler_clean.setup_for_snippet(
        """
import std
import custom_mod_one
import custom_mod_two
        """.strip(),
        python_package_sources=[local_module_package_index],
        project_requires=[
            module.InmantaModuleRequirement.parse("std~=3.0,<3.0.16"),
            module.InmantaModuleRequirement.parse("custom_mod_one>0"),
        ],
        python_requires=[
            module.ModuleV2Source.get_python_package_requirement(module.InmantaModuleRequirement.parse("custom_mod_one<999")),
        ],
        install_mode=InstallMode.release,
        autostd=False,
    )

    capsys.readouterr()
    ModuleTool().list()
    out, err = capsys.readouterr()
    assert (
        out.strip()
        == """
+----------------+------+----------+----------------+----------------+---------+
|      Name      | Type | Editable |   Installed    |  Expected in   | Matches |
|                |      |          |    version     |    project     |         |
+================+======+==========+================+================+=========+
| custom_mod_one | v2   | no       | 1.0.0          | >0,<999,~=1.0  | yes     |
| custom_mod_two | v2   | yes      | 1.0.0          | *              | yes     |
| std            | v1   | yes      | 3.0.15         | 3.0.15         | yes     |
+----------------+------+----------+----------------+----------------+---------+
    """.strip()
    )

    # install incompatible version for custom_mod_one
    module_from_template(
        str(tmpdir.join("custom_mod_one")),
        new_version=version.Version("2.0.0"),
        install=True,
        editable=False,
        in_place=True,
    )
    project.invalidate_state("custom_mod_one")
    capsys.readouterr()
    ModuleTool().list()
    out, err = capsys.readouterr()
    assert (
        out.strip()
        == """
+----------------+------+----------+----------------+----------------+---------+
|      Name      | Type | Editable |   Installed    |  Expected in   | Matches |
|                |      |          |    version     |    project     |         |
+================+======+==========+================+================+=========+
| custom_mod_one | v2   | no       | 2.0.0          | >0,<999,~=1.0  | no      |
| custom_mod_two | v2   | yes      | 1.0.0          | *              | yes     |
| std            | v1   | yes      | 3.0.15         | 3.0.15         | yes     |
+----------------+------+----------+----------------+----------------+---------+
    """.strip()
    )


def test_install_project_with_install_mode_master(tmpdir: py.path.local, snippetcompiler, modules_repo, capsys) -> None:
    """
    Ensure that an appropriate exception message is returned when a module installed in a project is not in-line with
    the version constraint on the project and the install_mode of the project is set to master.
    """
    mod_with_multiple_version = os.path.join(modules_repo, "mod11")
    mod_with_multiple_version_copy = os.path.join(tmpdir, "mod11")
    shutil.copytree(mod_with_multiple_version, mod_with_multiple_version_copy)
    snippetcompiler.setup_for_snippet(
        snippet="import mod11",
        autostd=False,
        install_project=False,
        add_to_module_path=[str(tmpdir)],
        project_requires=[InmantaModuleRequirement(Requirement.parse("mod11==3.2.1"))],
        install_mode=InstallMode.master,
    )

    with pytest.raises(CompilerException) as excinfo:
        ProjectTool().execute("update", [])

    assert """
The following requirements were not satisfied:
\t* requirement mod11==3.2.1 on module mod11 not fulfilled, now at version 4.2.0.
The release type of the project is set to 'master'. Set it to a value that is appropriate for the version constraint
    """.strip() in str(
        excinfo.value
    )


def test_module_install_logging(local_module_package_index: str, snippetcompiler_clean, caplog) -> None:
    """
    Make sure the module's informations are displayed when it is being installed for both v1 and v2 modules.
    """

    caplog.set_level(logging.INFO)

    v1_module = "minimalv1module"
    v2_module = "minimalv2module"

    v2_requirements = [Requirement.parse(module.ModuleV2Source.get_package_name_for(v2_module))]

    # set up project and modules
    project: module.Project = snippetcompiler_clean.setup_for_snippet(
        "\n".join(f"import {mod}" for mod in ["std", v1_module, v2_module]),
        autostd=False,
        python_package_sources=[local_module_package_index],
        python_requires=v2_requirements,
        install_project=False,
    )

    os.chdir(project.path)

    # autostd=True reports std as an import for any module, thus requiring it to be v2 because v2 can not depend on v1
    module.Project.get().autostd = False
    ProjectTool().execute("install", [])

    # ensure we can compile
    compiler.do_compile()

    expected_logs = [
        ("Installing module minimalv2module (v2)", logging.INFO),
        ("Successfully installed module minimalv2module (v2) version", logging.INFO),
        ("Installing module std (v1)", logging.INFO),
        ("Successfully installed module std (v1) version", logging.INFO),
    ]

    for message, level in expected_logs:
        log_contains(
            caplog,
            "inmanta.module",
            level,
            message,
        )


def test_real_time_logging(caplog):
    """
    Make sure the logging in _run_command_and_stream_output happens in real time
    """
    caplog.set_level(logging.DEBUG)

    cmd: List[str] = ["sh -c 'echo one && sleep 1 && echo two'"]
    return_code: int
    output: List[str]
    return_code, output = PythonEnvironment._run_command_and_stream_output(cmd, shell=True)
    assert return_code == 0

    assert "one" in caplog.records[0].message
    assert "one" in output[0]
    first_log_line_time: datetime = datetime.fromtimestamp(caplog.records[0].created)

    assert "two" in caplog.records[-1].message
    assert "two" in output[-1]
    last_log_line_time: datetime = datetime.fromtimestamp(caplog.records[-1].created)

    # "two" should be logged at least one second after "one"
    delta: float = (last_log_line_time - first_log_line_time).total_seconds()
    assert delta >= 1


def test_no_matching_distribution(local_module_package_index: str, snippetcompiler_clean, caplog):
    """ """
    caplog.set_level(logging.DEBUG)

    v2_module = "no_matching_dependency"

    v2_requirements = [Requirement.parse(module.ModuleV2Source.get_package_name_for(v2_module))]

    # set up project and modules
    project: module.Project = snippetcompiler_clean.setup_for_snippet(
        "\n".join(f"import {mod}" for mod in ["std", v2_module]),
        autostd=False,
        python_package_sources=[local_module_package_index],
        python_requires=v2_requirements,
        install_project=False,
    )

    os.chdir(project.path)

    # autostd=True reports std as an import for any module, thus requiring it to be v2 because v2 can not depend on v1
    # module.Project.get().autostd = False
    with pytest.raises(ModuleNotFoundException):
        ProjectTool().execute("install", [])

    expected_logs = [
        ("No matching distribution found for inmanta-module-v2-module==1234567.1234567.1234567", logging.DEBUG),
    ]

    for message, level in expected_logs:
        log_contains(
            caplog,
            "inmanta.env",
            level,
            message,
        )


def test_constraints_sandbox(local_module_package_index: str, snippetcompiler_clean, caplog):
    """ """
    caplog.set_level(logging.DEBUG)

    v2_module = "module_v2_with_version_constraints"

    v2_requirements = [Requirement.parse(module.ModuleV2Source.get_package_name_for(v2_module))]

    # set up project and modules
    project: module.Project = snippetcompiler_clean.setup_for_snippet(
        "\n".join(f"import {mod}" for mod in [v2_module, "minimalv2module"]),
        autostd=False,
        python_package_sources=[local_module_package_index],
        python_requires=v2_requirements,
        install_project=True,
    )
