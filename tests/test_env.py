"""
    Copyright 2021 Inmanta

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
import glob
import logging
import os
import subprocess
import sys
from subprocess import CalledProcessError

import pytest

from inmanta import env
from utils import LogSequence


def test_basic_install(tmpdir):
    """If this test fails, try running "pip uninstall lorem dummy-yummy iplib" before running it."""
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
            ["lorem == 0.1.1", "dummy-yummy", "iplib@git+https://github.com/bartv/python3-iplib", "lorem", "iplib >=0.0.1"]
        )
    except CalledProcessError as ep:
        print(ep.stdout)
        raise
    import iplib  # NOQA


def test_install_fails(tmpdir, caplog):
    venv = env.VirtualEnv(tmpdir)
    venv.use_virtual_env()
    caplog.clear()
    package_name = "non-existing-pkg-inmanta"

    with pytest.raises(Exception):
        venv.install_from_list([package_name])

    log_sequence = LogSequence(caplog)
    log_sequence.contains("inmanta.env", logging.ERROR, f"requirements: {package_name}")


def test_install_package_already_installed_in_parent_env(tmpdir):
    """Test using and installing a package that is already present in the parent virtual environment."""
    # get all packages in the parent
    parent_installed = list(env.VirtualEnv._get_installed_packages(sys.executable).keys())

    # create a venv and list all packages available in the venv
    venv = env.VirtualEnv(tmpdir)
    venv.use_virtual_env()

    installed_packages = list(env.VirtualEnv._get_installed_packages(venv._parent_python).keys())

    # verify that the venv sees all parent packages
    assert not set(parent_installed) - set(installed_packages)

    # site dir should be empty
    site_dir = os.path.join(venv.env_path, "lib/python*/site-packages")
    dirs = glob.glob(site_dir)
    assert len(dirs) == 1
    site_dir = dirs[0]

    assert not os.listdir(site_dir)

    # test installing a package that is already present in the parent venv
    random_package = parent_installed[0]
    venv.install_from_list([random_package])

    # Assert nothing installed in the virtual env
    assert not os.listdir(site_dir)

    # report json
    subprocess.check_output([os.path.join(venv.env_path, "bin/pip"), "list"])


def test_req_parser(tmpdir):
    url = "git+https://github.com/bartv/python3-iplib"
    at_url = "iplib@" + url
    egg_url = url + "#egg=iplib"

    e = env.VirtualEnv(tmpdir)
    name, u = e._parse_line(url)
    assert name is None
    assert u == url

    name, u = e._parse_line(at_url)
    assert name == "iplib"
    assert u == egg_url

    e._parse_line(egg_url)
    assert name == "iplib"
    assert u == egg_url


def test_gen_req_file(tmpdir):
    e = env.VirtualEnv(tmpdir)
    req = [
        "lorem == 0.1.1",
        "lorem > 0.1",
        "dummy-yummy",
        "iplib@git+https://github.com/bartv/python3-iplib",
        "lorem",
        # verify support for environment markers as described in PEP 508
        "lorem;python_version<'3.7'",
        "lorem;platform_machine == 'x86_64' and platform_system == 'Linux'",
    ]

    req_lines = [x for x in e._gen_requirements_file(req).split("\n") if len(x) > 0]
    assert len(req_lines) == 3
    assert (
        'lorem == 0.1.1, > 0.1 ; python_version < "3.7" and platform_machine == "x86_64" and platform_system == "Linux"'
        in req_lines
    )
