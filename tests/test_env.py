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

from subprocess import CalledProcessError


from inmanta import env
import pytest


def test_basic_install(tmpdir):
    env_dir1 = tmpdir.mkdir("env1").strpath

    with pytest.raises(ImportError):
        import lorem  # NOQA

    venv1 = env.VirtualEnv(env_dir1)

    venv1.use_virtual_env()
    venv1._install(["lorem"])
    import lorem  # NOQA
    lorem.sentence()

    with pytest.raises(ImportError):
        import yummy  # NOQA

    venv1 = env.VirtualEnv(env_dir1)

    venv1.use_virtual_env()
    venv1.install_from_list(["dummy-yummy"])
    import yummy  # NOQA

    with pytest.raises(ImportError):
        import iplib  # NOQA

    venv1 = env.VirtualEnv(env_dir1)

    venv1.use_virtual_env()
    try:
        venv1.install_from_list(
            ["lorem == 0.1.1", "dummy-yummy", "iplib@git+https://github.com/bartv/python3-iplib", "lorem", "iplib >=0.0.1"])
    except CalledProcessError as ep:
        print(ep.stdout)
        raise
    import iplib  # NOQA


def test_req_parser(tmpdir):
    url = "git+https://github.com/bartv/python3-iplib"
    at_url = "iplib@" + url
    egg_url = url + "#egg=iplib"

    e = env.VirtualEnv(tmpdir)
    name, u = e._parse_line(url)
    assert(name is None)
    assert(u == url)

    name, u = e._parse_line(at_url)
    assert(name == "iplib")
    assert(u == egg_url)

    e._parse_line(egg_url)
    assert(name == "iplib")
    assert(u == egg_url)


def test_gen_req_file(tmpdir):
    e = env.VirtualEnv(tmpdir)
    req = ["lorem == 0.1.1", "lorem > 0.1", "dummy-yummy", "iplib@git+https://github.com/bartv/python3-iplib", "lorem"]

    req_lines = [x for x in e._gen_requirements_file(req).split("\n") if len(x) > 0]
    assert(len(req_lines) == 3)
