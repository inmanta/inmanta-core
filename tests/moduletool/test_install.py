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

import logging
import os
import shutil
import subprocess
from datetime import datetime
from typing import List

import py
import pytest
from pkg_resources import Requirement

from inmanta import module
from inmanta.ast import CompilerException
from inmanta.command import CLIException
from inmanta.config import Config
from inmanta.env import CommandRunner
from inmanta.module import InmantaModuleRequirement, InstallMode, ModuleLoadingException, ModuleNotFoundException
from inmanta.moduletool import ModuleTool, ProjectTool
from packaging import version
from utils import LogSequence, PipIndex, log_contains, module_from_template

LOGGER = logging.getLogger(__name__)


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


def test_module_install() -> None:
    """
    Verify that the "inmanta module install commands raises an exception"
    """

    with pytest.raises(
        CLIException,
        match="The 'inmanta module install' command is no longer supported. For development mode "
        "installation, use 'pip install -e .'. For a regular installation, first run 'inmanta module build' and then 'pip install'.",
    ):
        ModuleTool().execute("install", [])


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
            module.InmantaModuleRequirement.parse("std~=4.1.7,<4.1.8"),
            module.InmantaModuleRequirement.parse("custom_mod_one>0"),
        ],
        python_requires=[
            module.InmantaModuleRequirement.parse("custom_mod_one<999").get_python_package_requirement(),
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
| std            | v1   | yes      | 4.1.7          | 4.1.7          | yes     |
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
| std            | v1   | yes      | 4.1.7          | 4.1.7          | yes     |
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


@pytest.mark.slowtest
def test_real_time_logging(caplog):
    """
    Make sure the logging in run_command_and_stream_output happens in real time
    """
    caplog.set_level(logging.DEBUG)

    cmd: List[str] = ["sh -c 'echo one && sleep 1 && echo two'"]
    return_code: int
    output: List[str]
    return_code, output = CommandRunner(LOGGER).run_command_and_stream_output(cmd, shell=True)
    assert return_code == 0

    assert "one" in caplog.records[0].message
    assert "one" in output[0]
    first_log_line_time: datetime = datetime.fromtimestamp(caplog.records[0].created)

    assert "two" in caplog.records[-1].message
    assert "two" in output[-1]
    last_log_line_time: datetime = datetime.fromtimestamp(caplog.records[-1].created)

    # "two" should be logged at least one second after "one"
    delta: float = (last_log_line_time - first_log_line_time).total_seconds()
    expected_delta = 1
    fault_tolerance = 0.1
    assert abs(delta - expected_delta) <= fault_tolerance


@pytest.mark.slowtest
def test_pip_output(local_module_package_index: str, snippetcompiler_clean, caplog, modules_v2_dir, tmpdir):
    """
    This test checks that pip's output is correctly logged on module install.
    """
    caplog.set_level(logging.DEBUG)

    index: PipIndex = PipIndex(artifact_dir=os.path.join(str(tmpdir), ".custom-index"))

    modone: module.ModuleV2Metadata = module_from_template(
        os.path.join(modules_v2_dir, "minimalv2module"),
        os.path.join(str(tmpdir), "modone"),
        new_version=version.Version("3.1.2"),
        new_name="modone",
        install=False,
        publish_index=index,
    )
    modtwo: module.ModuleV2Metadata = module_from_template(
        os.path.join(modules_v2_dir, "minimalv2module"),
        os.path.join(str(tmpdir), "modtwo"),
        new_version=version.Version("2.2.2"),
        new_name="modtwo",
        new_requirements=[InmantaModuleRequirement.parse("modone")],
        install=False,
        publish_index=index,
    )

    modules = ["modone", "modtwo"]
    v2_requirements = [Requirement.parse(module.ModuleV2Source.get_package_name_for(mod)) for mod in modules]

    snippetcompiler_clean.setup_for_snippet(
        f"""
        import {module.ModuleV2.get_name_from_metadata(modone)}
        import {module.ModuleV2.get_name_from_metadata(modtwo)}
        """,
        autostd=False,
        index_url=local_module_package_index,
        extra_index_url=[index.url],
        python_requires=v2_requirements,
        install_project=True,
    )

    expected_logs = [
        ("Successfully installed inmanta-module-modone-3.1.2", logging.DEBUG),
        ("Successfully installed inmanta-module-modtwo-2.2.2", logging.DEBUG),
    ]

    for message, level in expected_logs:
        log_contains(
            caplog,
            "inmanta.pip",
            level,
            message,
        )


@pytest.mark.slowtest
def test_git_clone_output(snippetcompiler_clean, caplog, modules_v2_dir):
    """
    This test checks that git clone output is correctly logged on module install.
    """
    caplog.set_level(logging.DEBUG)

    project = snippetcompiler_clean.setup_for_snippet(
        """
        import std
        """,
        autostd=False,
        install_project=True,
    )

    expected_logs = [
        ("Cloning into '%s'..." % os.path.join(project.downloadpath, "std"), logging.DEBUG),
    ]

    for message, level in expected_logs:
        log_contains(
            caplog,
            "inmanta.module",
            level,
            message,
        )


@pytest.mark.slowtest
def test_no_matching_distribution(local_module_package_index: str, snippetcompiler_clean, caplog, modules_v2_dir, tmpdir):
    """
    Make sure the logs contain the correct message when no matching distribution is found during install.
    """
    caplog.set_level(logging.DEBUG)

    index: PipIndex = PipIndex(artifact_dir=os.path.join(str(tmpdir), ".custom-index"))

    # Scenario 1
    # parent_module requires child_module v3.3.3 which is not installed yet.

    parent_module: module.ModuleV2Metadata = module_from_template(
        os.path.join(modules_v2_dir, "minimalv2module"),
        os.path.join(str(tmpdir), "parent_module"),
        new_version=version.Version("1.2.3"),
        new_name="parent_module",
        install=False,
        new_requirements=[InmantaModuleRequirement.parse("child_module==3.3.3")],
        publish_index=index,
    )

    with pytest.raises(ModuleNotFoundException):
        snippetcompiler_clean.setup_for_snippet(
            f"""
            import {module.ModuleV2.get_name_from_metadata(parent_module)}
            """,
            autostd=False,
            index_url=local_module_package_index,
            extra_index_url=[index.url],
            python_requires=[Requirement.parse(module.ModuleV2Source.get_package_name_for("parent_module"))],
            install_project=True,
        )
    log_contains(
        caplog,
        "inmanta.pip",
        logging.DEBUG,
        "No matching distribution found for inmanta-module-child-module==3.3.3",
    )

    # Scenario 2
    # parent_module requires child_module v3.3.3 but the index only has v1.1.1

    # Prepare the required module with a low version:

    module_from_template(
        os.path.join(modules_v2_dir, "minimalv2module"),
        os.path.join(str(tmpdir), "child_module"),
        new_version=version.Version("1.1.1"),
        new_name="child_module",
        install=False,
        publish_index=index,
    )

    with pytest.raises(ModuleNotFoundException):
        snippetcompiler_clean.setup_for_snippet(
            f"""
            import {module.ModuleV2.get_name_from_metadata(parent_module)}
            """,
            autostd=False,
            index_url=local_module_package_index,
            extra_index_url=[index.url],
            python_requires=[Requirement.parse(module.ModuleV2Source.get_package_name_for("parent_module"))],
            install_project=True,
        )

    log_contains(
        caplog,
        "inmanta.pip",
        logging.DEBUG,
        "No matching distribution found for inmanta-module-child-module==3.3.3",
    )

    shutil.rmtree(os.path.join(str(tmpdir), "child_module"))

    # Scenario 3
    # parent_module requires child_module v3.3.3 which is present in the index.

    # Prepare the required module with the correct version:
    module_from_template(
        os.path.join(modules_v2_dir, "minimalv2module"),
        os.path.join(str(tmpdir), "child_module"),
        new_version=version.Version("3.3.3"),
        new_name="child_module",
        install=False,
        publish_index=index,
    )

    snippetcompiler_clean.setup_for_snippet(
        f"""
        import {module.ModuleV2.get_name_from_metadata(parent_module)}
        """,
        autostd=False,
        index_url=local_module_package_index,
        extra_index_url=[index.url],
        python_requires=[Requirement.parse(module.ModuleV2Source.get_package_name_for("parent_module"))],
        install_project=True,
    )
    log_contains(
        caplog,
        "inmanta.pip",
        logging.DEBUG,
        "Successfully installed inmanta-module-child-module-3.3.3 inmanta-module-parent-module-1.2.3",
    )


def test_version_snapshot(local_module_package_index: str, snippetcompiler_clean, caplog, modules_v2_dir, tmpdir):
    """
    Make sure the logs contain the correct version snapshot after each module installation.
    """
    caplog.set_level(logging.DEBUG)

    index: PipIndex = PipIndex(artifact_dir=os.path.join(str(tmpdir), ".custom-index"))
    print(os.environ["PIP_INDEX_URL"])
    print(os.environ["PIP_EXTRA_INDEX_URL"])

    # Prepare the modules:
    # module a with version 1.0.0 and 5.0.0
    # module b that depends on module a>=1.0.0
    # module c that depends on module a==1.0.0

    module_from_template(
        os.path.join(modules_v2_dir, "minimalv2module"),
        os.path.join(str(tmpdir), "module_a"),
        new_version=version.Version("1.0.0"),
        new_name="module_a",
        install=False,
        publish_index=index,
    )
    module_from_template(
        os.path.join(modules_v2_dir, "minimalv2module"),
        os.path.join(str(tmpdir), "module_a_hi"),
        new_version=version.Version("5.0.0"),
        new_name="module_a",
        install=False,
        publish_index=index,
    )
    module_b: module.ModuleV2Metadata = module_from_template(
        os.path.join(modules_v2_dir, "minimalv2module"),
        os.path.join(str(tmpdir), "module_b"),
        new_version=version.Version("1.2.3"),
        new_name="module_b",
        install=False,
        new_requirements=[InmantaModuleRequirement.parse("module_a>=1.0.0")],
        publish_index=index,
    )
    module_c: module.ModuleV2Metadata = module_from_template(
        os.path.join(modules_v2_dir, "minimalv2module"),
        os.path.join(str(tmpdir), "module_c"),
        new_version=version.Version("8.8.8"),
        new_name="module_c",
        install=False,
        new_requirements=[InmantaModuleRequirement.parse("module_a==1.0.0")],
        publish_index=index,
    )

    # Scenario 1
    # Installing module b
    snippetcompiler_clean.setup_for_snippet(
        f"""
        import {module.ModuleV2.get_name_from_metadata(module_b)}
        """,
        autostd=False,
        index_url=local_module_package_index,
        extra_index_url=[index.url],
        python_requires=[Requirement.parse(module.ModuleV2Source.get_package_name_for("module_b"))],
        install_project=True,
    )

    # We expect the latest version for a and b to be newly added
    log_contains(
        caplog,
        "inmanta.module",
        logging.DEBUG,
        (
            """\
Modules versions after installation:
+ module_a: 5.0.0
+ module_b: 1.2.3"""
        ),
    )

    # Scenario 2
    # Installing module c in the same environment
    snippetcompiler_clean.setup_for_snippet(
        f"""
        import {module.ModuleV2.get_name_from_metadata(module_c)}
        """,
        autostd=False,
        index_url=local_module_package_index,
        extra_index_url=[index.url],
        python_requires=[Requirement.parse(module.ModuleV2Source.get_package_name_for("module_c"))],
        install_project=True,
    )

    # We expect :
    # - a to be downgraded to a compatible version
    # - b to remain unchanged
    # - c to be installed with the latest version

    log_contains(
        caplog,
        "inmanta.module",
        logging.DEBUG,
        (
            """\
Modules versions after installation:
+ module_a: 1.0.0
- module_a: 5.0.0
+ module_c: 8.8.8"""
        ),
    )


@pytest.mark.slowtest
def test_constraints_logging_v2(modules_v2_dir, tmpdir, caplog, snippetcompiler_clean, local_module_package_index):
    """
    Test that the version constraints are appropriately logged on module install.
    """
    caplog.set_level(logging.DEBUG)
    index: PipIndex = PipIndex(artifact_dir=os.path.join(str(tmpdir), ".custom-index"))

    module_from_template(
        os.path.join(modules_v2_dir, "minimalv2module"),
        os.path.join(str(tmpdir), "module_a_low"),
        new_version=version.Version("8.8.8"),
        new_name="module_a",
        install=False,
        publish_index=index,
    )

    module_from_template(
        os.path.join(modules_v2_dir, "minimalv2module"),
        os.path.join(str(tmpdir), "module_a_high"),
        new_version=version.Version("9.9.9"),
        new_name="module_a",
        install=False,
        publish_index=index,
    )

    module_from_template(
        os.path.join(modules_v2_dir, "minimalv2module"),
        os.path.join(str(tmpdir), "module_b"),
        new_version=version.Version("8.8.8"),
        new_requirements=[
            InmantaModuleRequirement.parse("module_a<10.10.10"),
            InmantaModuleRequirement.parse("module_a>=0.0.0"),
        ],
        new_name="module_b",
        install=False,
        publish_index=index,
    )

    snippetcompiler_clean.setup_for_snippet(
        """
        import module_a
        import module_b
        """,
        autostd=False,
        index_url=local_module_package_index,
        extra_index_url=[index.url],
        python_requires=[
            Requirement.parse(module.ModuleV2Source.get_package_name_for(mod)) for mod in ["module_b", "module_a"]
        ],
        install_project=True,
        project_requires=[
            module.InmantaModuleRequirement.parse("module_a<9.9.9"),
            module.InmantaModuleRequirement.parse("module_a>1.1.1"),
        ],
    )

    expected_log_messages = [
        "Installing module module_a (v2) (with constraints module_a<9.9.9 module_a>1.1.1 module_a<10.10.10 module_a>=0.0.0).",
        "Installing module module_b (v2) (with no version constraints)",
    ]

    for log_message in expected_log_messages:
        log_contains(
            caplog,
            "inmanta.module",
            logging.DEBUG,
            log_message,
        )


@pytest.mark.slowtest
def test_constraints_logging_v1(caplog, snippetcompiler_clean, local_module_package_index):
    caplog.set_level(logging.DEBUG)

    snippetcompiler_clean.setup_for_snippet(
        """
        import std
        """,
        autostd=False,
        install_project=True,
        project_requires=[
            module.InmantaModuleRequirement.parse("std>0.0"),
            module.InmantaModuleRequirement.parse("std>=0.0"),
            module.InmantaModuleRequirement.parse("std==4.1.7"),
            module.InmantaModuleRequirement.parse("std<=100.0.0"),
            module.InmantaModuleRequirement.parse("std<100.0.0"),
        ],
        index_url=local_module_package_index,
    )
    log_contains(
        caplog,
        "inmanta.module",
        logging.DEBUG,
        "Installing module std (v1) (with constraints std>0.0 std>=0.0 std==4.1.7 std<=100.0.0 std<100.0.0)",
    )
