"""
    Copyright 2022 Inmanta

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
import re
import subprocess
from typing import Optional

import click
import pytest

from inmanta import const
from inmanta.module import Module, UntrackedFilesMode
from inmanta.moduletool import ModuleTool, gitprovider
from packaging.version import Version
from test_app_cli import app
from utils import module_from_template, v1_module_from_template


def get_commit_message_x_commits_ago(path: str, nb_previous_commit: int = 0) -> str:
    """
    Return the commit message for the xth commit in the past.

    :param path: The path to the git repository.
    :param nb_previous_commit: Return the commit message for this number of commits in the past.
                               0 is the previous commit, -1 the commit before the previous commit, etc.
    """
    if nb_previous_commit < 0:
        raise Exception("Argument `nb_previous_commit` should be >= 0")
    return subprocess.check_output(["git", "log", "-1", f"--skip={nb_previous_commit}", "--pretty=%B"], cwd=path).decode()


@pytest.mark.parametrize("v1_module", [True, False])
@pytest.mark.parametrize("changelog_file_exists", [True, False])
@pytest.mark.parametrize("previous_stable_version_exists", [True, False])
def test_release_stable_version(
    tmpdir,
    modules_dir: str,
    modules_v2_dir: str,
    monkeypatch,
    v1_module: bool,
    changelog_file_exists: bool,
    previous_stable_version_exists: bool,
) -> None:
    """
    Test normal scenario where `inmanta module release` is used to release a stable version of a module.
    """

    def get_changelog_content(add_new_section_for_version: Optional[str] = None) -> str:
        prefix = ""
        if add_new_section_for_version:
            prefix = f"""
V{add_new_section_for_version}
-
            """.lstrip().rstrip(
                " "
            )
        return f"""
{prefix}
V1.2.3
- Release

V1.2.2
- Release
        """.strip()

    module_name = "mod"
    path_module = os.path.join(tmpdir, module_name)
    if v1_module:
        v1_module_from_template(
            source_dir=os.path.join(modules_dir, "minimalv1module"),
            dest_dir=path_module,
            new_version=Version("1.2.3.dev0"),
            new_name=module_name,
        )
    else:
        module_from_template(
            source_dir=os.path.join(modules_v2_dir, "minimalv2module"),
            dest_dir=path_module,
            new_version=Version("1.2.3.dev0"),
            new_name=module_name,
        )
    gitprovider.git_init(repo=path_module)
    path_changelog_file = os.path.join(path_module, const.MODULE_CHANGELOG_FILE)
    if changelog_file_exists:
        with open(path_changelog_file, "w", encoding="utf-8") as fh:
            fh.write(get_changelog_content())
    gitprovider.commit(repo=path_module, message="Initial commit", add=["*"], commit_all=True)
    if previous_stable_version_exists:
        gitprovider.tag(repo=path_module, tag="1.2.2")
    else:
        assert not gitprovider.get_version_tags(repo=path_module)

    # Add a new staged file. This file should be committed when the release command is executed.
    new_file = os.path.join(path_module, "new_file")
    with open(new_file, "w", encoding="utf-8") as fh:
        fh.write("")
    gitprovider.add(repo=path_module, files=[new_file])
    # Ensure we have an uncommitted tracked file
    assert gitprovider.status(repo=path_module, untracked_files_mode=UntrackedFilesMode.NORMAL) != ""
    monkeypatch.chdir(path_module)
    app(["module", "release", "--message", "Commit changes"])
    # Ensure that all files are committed
    assert gitprovider.status(repo=path_module, untracked_files_mode=UntrackedFilesMode.NORMAL) == ""
    # Verify commit messages
    assert get_commit_message_x_commits_ago(path=path_module, nb_previous_commit=1).strip() == "Commit changes"
    assert (
        get_commit_message_x_commits_ago(path=path_module, nb_previous_commit=0).strip()
        == "Bump version to next development version"
    )
    # Verify release tags
    expected_tags = [Version("1.2.3")] if not previous_stable_version_exists else [Version("1.2.2"), Version("1.2.3")]
    assert gitprovider.get_version_tags(repo=path_module) == expected_tags
    # Verify version
    mod = Module.from_path(path_module)
    assert mod.version == Version("1.2.4.dev0")
    # Verify changelog file
    if changelog_file_exists:
        with open(path_changelog_file, "r", encoding="utf-8") as fh:
            assert fh.read() == get_changelog_content("1.2.4")
    else:
        assert not os.path.exists(path_changelog_file)


@pytest.mark.parametrize("v1_module", [True, False])
def test_release_stable_version_already_released(
    tmpdir, modules_dir: str, modules_v2_dir: str, monkeypatch, v1_module: bool
) -> None:
    """
    Ensure that a clear error message is shown when trying to release a stable version
    that was already released before.
    """
    module_name = "mod"
    path_module = os.path.join(tmpdir, module_name)
    if v1_module:
        v1_module_from_template(
            source_dir=os.path.join(modules_dir, "minimalv1module"),
            dest_dir=path_module,
            new_version=Version("1.2.3.dev0"),
            new_name=module_name,
        )
    else:
        module_from_template(
            source_dir=os.path.join(modules_v2_dir, "minimalv2module"),
            dest_dir=path_module,
            new_version=Version("1.2.3.dev0"),
            new_name=module_name,
        )
    gitprovider.git_init(repo=path_module)
    gitprovider.commit(repo=path_module, message="Initial commit", add=["*"], commit_all=True)
    gitprovider.tag(repo=path_module, tag="1.2.3")
    monkeypatch.chdir(path_module)
    module_tool = ModuleTool()
    with pytest.raises(click.ClickException) as exc_info:
        module_tool.release(dev=False, message="Commit changes")
    assert "A Git version tag already exists for version 1.2.3" in exc_info.value.message


@pytest.mark.parametrize("v1_module", [True, False])
@pytest.mark.parametrize("increment", ["major", "minor", "patch"])
@pytest.mark.parametrize("changelog_file_exists", [True, False])
def test_bump_dev_version(
    tmpdir, modules_dir: str, modules_v2_dir: str, monkeypatch, v1_module: bool, increment: str, changelog_file_exists: bool
) -> None:
    """
    Ensure that the normal scenario for the `inmanta module release --dev` command works as expected.
    """
    module_name = "mod"
    path_module = os.path.join(tmpdir, module_name)
    if v1_module:
        v1_module_from_template(
            source_dir=os.path.join(modules_dir, "minimalv1module"),
            dest_dir=path_module,
            new_version=Version("1.1.2.dev0"),
            new_name=module_name,
        )
    else:
        module_from_template(
            source_dir=os.path.join(modules_v2_dir, "minimalv2module"),
            dest_dir=path_module,
            new_version=Version("1.1.2.dev0"),
            new_name=module_name,
        )

    if changelog_file_exists:
        path_changelog_file = os.path.join(path_module, const.MODULE_CHANGELOG_FILE)
        with open(path_changelog_file, "w", encoding="utf-8") as fh:
            fh.write(
                """
V1.1.2
- Test

V1.1.1
- Mentioning the other version 1.1.2, 1.2.0, 2.0.0

V1.1.0
- Release

V1.0.0
- Release
            """.strip()
            )

    gitprovider.git_init(repo=path_module)
    gitprovider.commit(repo=path_module, message="Initial commit", add=["*"], commit_all=True)
    for tag in ["1.0.0", "1.1.0", "1.1.1", "3.0.0"]:
        gitprovider.tag(repo=path_module, tag=tag)

    def assert_module_state(expected_version: str, expected_commit_message: str) -> None:
        """
        Verify that the module has the state as expected after running the `inmanta module release command`.

        :param expected_version: The expected fully qualified version (version number + version tag).
        :param expected_commit_message: The commit message expected for the latest commit.
        """
        assert Module.from_path(path_module).version == Version(expected_version)
        path_changelog_file = os.path.join(path_module, const.MODULE_CHANGELOG_FILE)
        if changelog_file_exists:
            with open(path_changelog_file, "r", encoding="utf-8") as fh:
                # Ensure that only the first occurrence of the version number in the
                # changelog file got replaced.
                stable_version_number = expected_version.rsplit(".", maxsplit=1)[0]
                assert len(re.findall(re.escape(stable_version_number), fh.read())) == 2
        else:
            assert not os.path.exists(path_changelog_file)
        assert get_commit_message_x_commits_ago(path=path_module, nb_previous_commit=0).strip() == expected_commit_message

    monkeypatch.chdir(path_module)
    module_tool = ModuleTool()
    module_tool.release(dev=True, patch=True, message="Commit patch increment")
    # The version number is already a patch increment ahead of the previous stable release.
    # There's no need for a new commit to bump the version.
    assert_module_state("1.1.2.dev0", expected_commit_message="Initial commit")
    module_tool.release(dev=True, minor=True, message="Commit minor increment")
    assert_module_state("1.2.0.dev0", expected_commit_message="Commit minor increment")
    module_tool.release(dev=True, major=True, message="Commit major increment")
    assert_module_state("2.0.0.dev0", expected_commit_message="Commit major increment")


@pytest.mark.parametrize(
    "initial_version, after_patch_increment, after_minor_increment, after_major_increment",
    [
        ("1.1.2.dev0", "1.1.2.dev", "1.1.2.dev", "2.0.0.dev"),
        ("1.0.1.4.6.dev0", "1.0.1.4.6.dev0", "1.1.0.0.0.dev0", "2.0.0.0.0.dev0"),
    ],
)
def test_bump_dev_version_distance_already_met(
    tmpdir,
    modules_dir: str,
    monkeypatch,
    initial_version: str,
    after_patch_increment: str,
    after_minor_increment: str,
    after_major_increment: str,
) -> None:
    """
    Ensure that the `inmanta module release --dev` command doesn't increment the version when
    the current version is already sufficiently separated from the previous stable release.
    This test also verifies the behavior when the release part of the version number is longer
    than three numbers.
    """
    module_name = "mod"
    path_module = os.path.join(tmpdir, module_name)
    v1_module_from_template(
        source_dir=os.path.join(modules_dir, "minimalv1module"),
        dest_dir=path_module,
        new_version=Version(initial_version),
        new_name=module_name,
    )
    gitprovider.git_init(repo=path_module)
    gitprovider.commit(repo=path_module, message="Initial commit", add=["*"], commit_all=True)
    gitprovider.tag(repo=path_module, tag="1.0.0")

    monkeypatch.chdir(path_module)
    module_tool = ModuleTool()
    module_tool.release(dev=True, patch=True, message="Commit changes")
    assert str(Module.from_path(path_module).version) == str(Version(after_patch_increment))
    module_tool.release(dev=True, minor=True, message="Commit changes")
    assert str(Module.from_path(path_module).version) == str(Version(after_minor_increment))
    module_tool.release(dev=True, major=True, message="Commit changes")
    assert str(Module.from_path(path_module).version) == str(Version(after_major_increment))


def test_failed_to_bump_version_in_changelog_file(tmpdir, modules_dir: str, monkeypatch, caplog) -> None:
    """
    Ensure that a warning is logged when a changelog file is present but the `inmanta module release`
    could not bump the version in the changelog, because the version was not found in the file.
    """
    module_name = "mod"
    path_module = os.path.join(tmpdir, module_name)
    v1_module_from_template(
        source_dir=os.path.join(modules_dir, "minimalv1module"),
        dest_dir=path_module,
        new_version=Version("1.0.1.dev0"),
        new_name=module_name,
    )
    path_changelog_file = os.path.join(path_module, const.MODULE_CHANGELOG_FILE)
    with open(path_changelog_file, "w", encoding="utf-8") as fh:
        # Ensure version number is not present in the changelog file
        fh.write("")
    gitprovider.git_init(repo=path_module)
    gitprovider.commit(repo=path_module, message="Initial commit", add=["*"], commit_all=True)
    gitprovider.tag(repo=path_module, tag="1.0.0")
    # Execute release command
    monkeypatch.chdir(path_module)
    module_tool = ModuleTool()
    with caplog.at_level(logging.WARNING):
        module_tool.release(dev=True, minor=True, message="commit message")
    # Verify warning was logged
    assert "Failed to bump the version number in the changelog file from 1.0.1 to 1.1.0" in caplog.text


def test_too_many_version_bump_arguments() -> None:
    """
    Ensure that the `inmanta release` command raises an error when more than one
    of the options --major, --minor or --patch is passed to the command.
    """
    module_tool = ModuleTool()
    with pytest.raises(click.UsageError) as exc_info:
        module_tool.release(dev=False, minor=True, major=True, message="Commit changes")
    assert "Only one of --patch, --minor and --major arguments can be set at the same time." in exc_info.value.message


def test_epoch_value_larger_than_zero(tmpdir, modules_dir: str, monkeypatch) -> None:
    """
    Ensure that an exception is raised when the epoch value of the module is larger than zero.
    Epoch values different from zero are not supported at the moment.
    """
    path_module = os.path.join(tmpdir, "mod")
    v1_module_from_template(
        source_dir=os.path.join(modules_dir, "minimalv1module"),
        dest_dir=path_module,
        new_version=Version("1!1.2.3.dev0"),
        new_name="mod",
    )
    gitprovider.git_init(repo=path_module)
    gitprovider.commit(repo=path_module, message="Initial commit", add=["*"], commit_all=True)
    monkeypatch.chdir(path_module)
    module_tool = ModuleTool()
    with pytest.raises(click.ClickException) as exc_info:
        module_tool.release(dev=True, minor=True, message="Commit changes")
    assert "Version with an epoch value larger than zero are not supported by this tool." in exc_info.value.message


def test_not_a_git_repository(tmpdir, modules_dir: str, monkeypatch) -> None:
    """
    Ensure that a clear error message is returned when the `git release` command is executed on a directory
    that is not a git repository.
    """
    module_name = "mod"
    path_module = os.path.join(tmpdir, module_name)
    v1_module_from_template(
        source_dir=os.path.join(modules_dir, "minimalv1module"),
        dest_dir=path_module,
        new_version=Version("1.2.3.dev0"),
        new_name=module_name,
    )
    monkeypatch.chdir(path_module)
    module_tool = ModuleTool()
    with pytest.raises(click.ClickException) as exc_info:
        module_tool.release(dev=False, message="Commit changes")
    assert f"Directory {path_module} is not a git repository" in exc_info.value.message
