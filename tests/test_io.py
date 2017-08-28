"""
    Copyright 2016 Inmanta

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Contact: bart@inmanta.com
"""

import os
import pwd
import shutil
import subprocess
import tempfile

import pytest

import grp
from inmanta.agent.io import parse_agent_uri
from inmanta.agent.io.local import BashIO
from inmanta.agent.io.local import LocalIO


io_list = [LocalIO("local:", {}), BashIO("local:", {}), BashIO("local:", {}, run_as="root")]


@pytest.yield_fixture(scope="module")
def testdir():
    testdir = tempfile.mkdtemp()
    yield testdir
    shutil.rmtree(testdir)


@pytest.mark.parametrize("io", io_list)
def test_check_hash(io, testdir):
    filename = os.path.join(testdir, "hashfile")
    with open(filename, "w+") as fd:
        fd.write("test")

    assert io.hash_file(filename) == "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3"


@pytest.mark.parametrize("io", io_list)
def test_check_read(io, testdir):
    test_str = "hello é"
    filename = os.path.join(testdir, "readfile")
    with open(filename, "wb+") as fd:
        fd.write(test_str.encode())

    assert io.read(filename) == test_str


@pytest.mark.parametrize("io", io_list)
def test_check_read_binary(io, testdir):
    test_str = b'\1\2\3\4\5\6'
    filename = os.path.join(testdir, "readbinaryfile")
    with open(filename, "wb+") as fd:
        fd.write(test_str)

    result = io.read_binary(filename)

    assert isinstance(result, bytes)
    assert result == test_str


@pytest.mark.parametrize("io", io_list)
def test_check_run(io, testdir):
    result = io.run("echo", ["world"])
    assert result[2] == 0
    assert result[0] == "world"

    # check cwd
    os.makedirs(os.path.join(testdir, "check_run" + str(io)))
    out, _, _ = io.run("ls", [], cwd=testdir)
    assert "check_run" + str(io) in out


@pytest.mark.parametrize("io", io_list)
def test_check_run_env(io, testdir):
    value = "testenvmagicstring"
    result = io.run("env", env={"TEST_ENV": value})

    assert value in result[0]


@pytest.mark.parametrize("io", io_list)
def test_check_file_exists(io, testdir):
    assert io.file_exists(testdir)
    assert not io.file_exists("/blablablablablalbla")

    filename = os.path.join(testdir, "testfile" + str(io))
    assert not io.file_exists(filename)

    with open(filename, "w+") as fd:
        fd.write("")

    assert io.file_exists(filename)


@pytest.mark.parametrize("io", io_list)
def test_check_symlink(io, testdir):
    dst = os.path.join(testdir, "ln" + str(io))
    io.symlink(testdir, dst)

    assert os.path.exists(dst)
    assert os.path.islink(dst)
    assert os.readlink(dst) == testdir


@pytest.mark.parametrize("io", io_list)
def test_check_readlink(io, testdir):
    dst = os.path.join(testdir, "rdln" + str(io))
    os.symlink(testdir, dst)

    assert io.readlink(dst) == testdir


@pytest.mark.parametrize("io", io_list)
def test_check_is_symlink(io, testdir):
    dst = os.path.join(testdir, "isln" + str(io))
    os.symlink(testdir, dst)

    assert io.is_symlink(dst)
    assert not io.is_symlink(testdir)


@pytest.mark.parametrize("io", io_list)
def test_check_mkdir(io, testdir):
    mkdir = os.path.join(testdir, "dir" + str(io))
    io.mkdir(mkdir)

    assert os.path.exists(mkdir)
    assert os.path.isdir(mkdir)


@pytest.mark.parametrize("io", io_list)
def test_check_rmdir(io, testdir):
    path = os.path.join(testdir, "rmdir" + str(io))
    os.mkdir(path)
    assert(os.path.exists(path))

    path2 = os.path.join(path, "testfile" + str(io))
    with open(path2, "w+") as fd:
        fd.write("")
    assert(os.path.exists(path2))

    io.rmdir(path)

    assert not os.path.exists(path)
    assert not os.path.exists(path2)


@pytest.mark.parametrize("io", io_list)
def test_check_filestat(io, testdir):
    stat = io.file_stat("/etc")
    assert stat["permissions"] == 755
    assert stat["owner"] == "root"
    assert stat["group"] == "root"


@pytest.mark.parametrize("io", io_list)
def test_check_chown(io, testdir):
    # chown to the same user so we do not need root to run this test
    path = os.path.join(testdir, "chown" + str(io))
    with open(path, "w+") as fd:
        fd.write("")

    assert os.path.exists(path)

    user = pwd.getpwuid(os.getuid())[0]
    groups = [grp.getgrgid(g).gr_name for g in os.getgroups()]

    if len(groups) == 0:
        # fix for jenkins docker
        groups = [user]

    io.chown(path, user)
    stat = io.file_stat(path)
    assert stat["owner"] == user

    io.chown(path, user, groups[0])
    stat = io.file_stat(path)
    assert stat["owner"] == user
    assert stat["group"] == groups[0]

    io.chown(path, None, groups[0])
    stat = io.file_stat(path)
    assert stat["group"] == groups[0]


@pytest.mark.parametrize("io", io_list)
def test_check_put(io, testdir):
    path = os.path.join(testdir, "put" + str(io))
    io.put(path, b"hello")

    with open(path, "rb") as fd:
        assert b"hello" == fd.read()


@pytest.mark.parametrize("io", io_list)
def test_check_chmod(io, testdir):
    path = os.path.join(testdir, "chmod" + str(io))
    with open(path, "w+") as fd:
        fd.write("Test\n")

    st = os.stat(path)
    mode = str(oct(st.st_mode))[-4:]

    io.chmod(path, "0755")

    st = os.stat(path)
    new_mode = str(oct(st.st_mode))[-4:]

    assert mode != new_mode
    assert "0755" == new_mode


@pytest.mark.parametrize("io", io_list)
def test_hash_dir(io, testdir):
    dir_path = os.path.join(testdir, "dir")
    if not os.path.exists(dir_path):
        io.mkdir(dir_path)

    with pytest.raises(Exception):
        io.hash_file(dir_path)


@pytest.mark.parametrize("io", io_list)
def test_timeout(io):
    with pytest.raises(subprocess.TimeoutExpired):
        io.run("sleep", ["0.1"], timeout=0.05)


def test_uri_parse():
    scheme, config = parse_agent_uri("local:")
    assert scheme == "local"
    assert len(config) == 0

    scheme, config = parse_agent_uri("ssh://ec2-user@1.2.3.4:22")
    assert scheme == "ssh"
    assert len(config) == 3
    assert config["user"] == "ec2-user"
    assert config["port"] == "22"
    assert config["host"] == "1.2.3.4"

    scheme, config = parse_agent_uri("")
    assert scheme == "local"
    assert len(config) == 0

    scheme, config = parse_agent_uri("hostname")
    assert scheme == "ssh"
    assert len(config) == 3
    assert config["host"] == "hostname"

    scheme, config = parse_agent_uri("localhost")
    assert scheme == "local"

    scheme, config = parse_agent_uri("ssh://ec2-user@1.2.3.4:22?python=/usr/bin/python2")
    assert scheme == "ssh"
    assert len(config) == 4
    assert config["user"] == "ec2-user"
    assert config["port"] == "22"
    assert config["host"] == "1.2.3.4"
    assert config["python"] == "/usr/bin/python2"
