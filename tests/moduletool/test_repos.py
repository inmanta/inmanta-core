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
import os

import pytest

from inmanta.module import InvalidMetadata, LocalFileRepo, RemoteRepo, gitprovider


def test_file_co(modules_dir, modules_repo):
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


def test_remote_repo_bad(tmpdir, modules_repo):
    repo = RemoteRepo("https://github.com/{}/{}")
    coroot = os.path.join(tmpdir, "clone_remote_good")
    with pytest.raises(InvalidMetadata) as e:
        result = repo.clone("test-repository", coroot)
        assert not result
    msg = e.value.msg
    assert msg == "Wrong repo path at https://github.com/{}/{} : should only contain at most one {} pair"


def test_local_repo_bad(tmpdir, modules_repo):
    repo = LocalFileRepo(modules_repo)
    coroot = os.path.join(tmpdir, "clone_local_good")
    result = repo.clone("thatotherthing", coroot)
    assert not result
