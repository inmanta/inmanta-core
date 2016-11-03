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
import tempfile

from inmanta import env
import pytest
from subprocess import CalledProcessError


def test_basic_install(tmpdir):
    env_dir1 = tmpdir.mkdir("env1").strpath

    with pytest.raises(ImportError):
        import lorem

    venv1 = env.VirtualEnv(env_dir1)

    venv1.use_virtual_env()
    venv1._install(["lorem"])
    import lorem
    s = lorem.sentence()


def test_basic_install_syntax(tmpdir):
    env_dir1 = tmpdir.mkdir("env1").strpath
    with pytest.raises(ImportError):
        import yummy

    venv1 = env.VirtualEnv(env_dir1)

    venv1.use_virtual_env()
    venv1.install_from_list(["dummy-yummy"])
    import yummy


def test_full_install_syntax(tmpdir):
    env_dir1 = tmpdir.mkdir("env1").strpath
    with pytest.raises(ImportError):
        import iplib

    venv1 = env.VirtualEnv(env_dir1)

    venv1.use_virtual_env()
    try:
        venv1.install_from_list(
            ["lorem == 0.1.1", "dummy-yummy", "iplib@git+https://github.com/bartv/python3-iplib", "lorem"])
    except CalledProcessError as ep:
        print(ep.stdout)
        raise
    import iplib
