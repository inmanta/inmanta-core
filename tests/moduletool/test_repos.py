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

import os
import pathlib
import subprocess

import pytest

from inmanta.module import UntrackedFilesMode, gitprovider


@pytest.fixture
def git_repo(tmp_path: pathlib.Path) -> str:
    """
    A git repository with a tracked file and the version tags 3.2.1, 4.0.0.dev0 and 4.0.0.
    """
    repo = str(tmp_path / "repo")
    os.makedirs(repo)
    gitprovider.git_init(repo=repo)
    for tag in ["3.2.1", "4.0.0.dev0", "4.0.0"]:
        with open(os.path.join(repo, "file"), "w", encoding="utf-8") as fh:
            fh.write(tag)
        gitprovider.commit(repo=repo, message=f"release version {tag}", add=["file"], commit_all=True)
        gitprovider.tag(repo=repo, tag=tag)
    return repo


def test_gitprovider_get_version_tags(git_repo: str) -> None:
    """
    Verify that the get_version_tags() method of the gitprovider works correctly.
    """
    all_versions = [str(v) for v in gitprovider.get_version_tags(repo=git_repo)]
    assert all_versions == ["3.2.1", "4.0.0.dev0", "4.0.0"]
    stable_versions = [str(v) for v in gitprovider.get_version_tags(repo=git_repo, only_return_stable_versions=True)]
    assert stable_versions == ["3.2.1", "4.0.0"]


def test_gitprovider_status(git_repo: str) -> None:
    """
    Verify that the status() method of the gitprovider works correctly.
    """
    # Verify behavior on a clean working tree
    assert "" == gitprovider.status(repo=git_repo)
    # Verify behavior when untracked file is present
    untracked_file = os.path.join(git_repo, "untracked_file")
    with open(untracked_file, "w", encoding="utf-8"):
        pass
    assert "" == gitprovider.status(repo=git_repo, untracked_files_mode=UntrackedFilesMode.NO)
    assert "untracked_file" in gitprovider.status(repo=git_repo, untracked_files_mode=UntrackedFilesMode.NORMAL)
    os.remove(untracked_file)
    # Verify behavior when tracked file is present
    tracked_file = os.path.join(git_repo, "file")
    with open(tracked_file, "w", encoding="utf-8") as fh:
        fh.write("new content")
    assert "file" in gitprovider.status(repo=git_repo, untracked_files_mode=UntrackedFilesMode.NO)
    assert "file" in gitprovider.status(repo=git_repo, untracked_files_mode=UntrackedFilesMode.NORMAL)


def test_commit_raise_exc_when_nothing_to_commit(git_repo: str) -> None:
    """
    Verify the behavior of the commit() method of the gitprovider. Ensure that the
    `raise_exc_when_nothing_to_commit` argument works as expected.
    """
    # Verify that exception is raised when nothing to commit
    try:
        gitprovider.commit(repo=git_repo, message="test", commit_all=True)
    except subprocess.SubprocessError:
        pass
    else:
        raise Exception("No exception was raised!")
    # Verify that disabling the exception works
    gitprovider.commit(repo=git_repo, message="test", commit_all=True, raise_exc_when_nothing_to_commit=False)
    # Ensure that commit still happens when raising exceptions is disabled
    tracked_file = os.path.join(git_repo, "file")
    with open(tracked_file, "w", encoding="utf-8") as fh:
        fh.write("new content")
    assert "" != gitprovider.status(repo=git_repo)
    gitprovider.commit(repo=git_repo, message="test", commit_all=True, raise_exc_when_nothing_to_commit=False)
    assert "" == gitprovider.status(repo=git_repo)
    # Verify the behavior when only untracked files are present
    untracked_file = os.path.join(git_repo, "untracked_file")
    with open(untracked_file, "w", encoding="utf-8"):
        pass
    assert "" != gitprovider.status(repo=git_repo)
    gitprovider.commit(repo=git_repo, message="test", commit_all=True, raise_exc_when_nothing_to_commit=False)
    assert "" != gitprovider.status(repo=git_repo)
