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
import subprocess

import pytest

from inmanta.module import CompositeModuleRepo, InvalidMetadata, LocalFileRepo, RemoteRepo, UntrackedFilesMode, gitprovider


def test_file_co(git_modules_dir, modules_repo):
    result = """name: mod6
license: Apache 2.0
version: '3.2'
"""
    module_yaml = gitprovider.get_file_for_version(os.path.join(modules_repo, "mod6"), "3.2", "module.yml")
    assert result == module_yaml


def test_local_repo_good(tmpdir, modules_repo):
    repo = LocalFileRepo(modules_repo)
    coroot = os.path.join(tmpdir, "clone_local_good")
    result = repo.clone("mod1", coroot)
    assert result
    assert os.path.exists(os.path.join(coroot, "mod1", "module.yml"))


def test_remote_repo_good(tmpdir, modules_repo):
    repo = RemoteRepo("https://github.com/rmccue/")
    coroot = os.path.join(tmpdir, "clone_remote_good")
    result = repo.clone("test-repository", coroot)
    assert result
    assert os.path.exists(os.path.join(coroot, "test-repository", "README"))


def test_remote_repo_good2(tmpdir, modules_repo):
    repo = RemoteRepo("https://github.com/rmccue/{}")
    coroot = os.path.join(tmpdir, "clone_remote_good")
    result = repo.clone("test-repository", coroot)
    assert result
    assert os.path.exists(os.path.join(coroot, "test-repository", "README"))
    assert not repo.is_empty()


def test_remote_repo_bad(tmpdir, modules_repo):
    repo = RemoteRepo("https://github.com/{}/{}")
    coroot = os.path.join(tmpdir, "clone_remote_good")
    with pytest.raises(InvalidMetadata) as e:
        result = repo.clone("test-repository", coroot)
        assert not result
    msg = e.value.msg
    assert msg == "Wrong repo path at https://github.com/{}/{} : should only contain at most one {} pair"
    assert not repo.is_empty()


def test_local_repo_bad(tmpdir, modules_repo):
    repo = LocalFileRepo(modules_repo)
    coroot = os.path.join(tmpdir, "clone_local_good")
    result = repo.clone("thatotherthing", coroot)
    assert not result


def test_gitprovider_get_version_tags(tmpdir, modules_repo: str) -> None:
    """
    Verify that the get_version_tags() method of the gitprovider works correctly.
    """
    repo = LocalFileRepo(modules_repo)
    coroot = os.path.join(tmpdir, "clone")
    success = repo.clone("mod12", coroot)
    assert success
    git_repo_clone = os.path.join(coroot, "mod12")
    all_versions = [str(v) for v in gitprovider.get_version_tags(repo=git_repo_clone)]
    assert all_versions == ["3.2.1", "4.0.0.dev0", "4.0.0"]
    stable_versions = [str(v) for v in gitprovider.get_version_tags(repo=git_repo_clone, only_return_stable_versions=True)]
    assert stable_versions == ["3.2.1", "4.0.0"]


def test_gitprovider_status(tmpdir, modules_repo: str) -> None:
    """
    Verify that the status() method of the gitprovider works correctly.
    """
    repo = LocalFileRepo(modules_repo)
    coroot = os.path.join(tmpdir, "clone")
    success = repo.clone("mod12", coroot)
    assert success
    # Verify behavior on clean checkout
    git_repo_clone = os.path.join(coroot, "mod12")
    assert "" == gitprovider.status(repo=git_repo_clone)
    # Verify behavior when untracked file is present
    untracked_file = os.path.join(git_repo_clone, "untracked_file")
    with open(untracked_file, "w", encoding="utf-8"):
        pass
    assert "" == gitprovider.status(repo=git_repo_clone, untracked_files_mode=UntrackedFilesMode.NO)
    assert "untracked_file" in gitprovider.status(repo=git_repo_clone, untracked_files_mode=UntrackedFilesMode.NORMAL)
    os.remove(untracked_file)
    # Verify behavior when tracked file is present
    tracked_file = os.path.join(git_repo_clone, "file")
    with open(tracked_file, "w", encoding="utf-8") as fh:
        fh.write("new content")
    assert "file" in gitprovider.status(repo=git_repo_clone, untracked_files_mode=UntrackedFilesMode.NO)
    assert "file" in gitprovider.status(repo=git_repo_clone, untracked_files_mode=UntrackedFilesMode.NORMAL)


def test_commit_raise_exc_when_nothing_to_commit(tmpdir, modules_repo: str) -> None:
    """
    Verify the behavior of the commit() method of the gitprovider. Ensure that the
    `raise_exc_when_nothing_to_commit` argument works as expected.
    """
    repo = LocalFileRepo(modules_repo)
    coroot = os.path.join(tmpdir, "clone")
    success = repo.clone("mod12", coroot)
    assert success
    git_repo_clone = os.path.join(coroot, "mod12")
    # Verify that exception is raised when nothing to commit
    try:
        gitprovider.commit(repo=git_repo_clone, message="test", commit_all=True)
    except subprocess.SubprocessError:
        pass
    else:
        raise Exception("No exception was raised!")
    # Verify that disabling the exception works
    gitprovider.commit(repo=git_repo_clone, message="test", commit_all=True, raise_exc_when_nothing_to_commit=False)
    # Ensure that commit still happens when raising exceptions is disabled
    tracked_file = os.path.join(git_repo_clone, "file")
    with open(tracked_file, "w", encoding="utf-8") as fh:
        fh.write("new content")
    assert "" != gitprovider.status(repo=git_repo_clone)
    gitprovider.commit(repo=git_repo_clone, message="test", commit_all=True, raise_exc_when_nothing_to_commit=False)
    assert "" == gitprovider.status(repo=git_repo_clone)
    # Verify the behavior when only untracked files are present
    untracked_file = os.path.join(git_repo_clone, "untracked_file")
    with open(untracked_file, "w", encoding="utf-8"):
        pass
    assert "" != gitprovider.status(repo=git_repo_clone)
    gitprovider.commit(repo=git_repo_clone, message="test", commit_all=True, raise_exc_when_nothing_to_commit=False)
    assert "" != gitprovider.status(repo=git_repo_clone)


def test_composite_repo_empty():
    repo = LocalFileRepo("test")

    empty = CompositeModuleRepo([])
    assert empty.is_empty()

    also_empty = CompositeModuleRepo([empty])
    assert also_empty.is_empty()

    composed = CompositeModuleRepo([repo])
    assert not composed.is_empty()

    composed = CompositeModuleRepo([repo, empty])
    assert not composed.is_empty()
