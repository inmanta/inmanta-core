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

import logging
from subprocess import CalledProcessError

import pytest

from inmanta import env
from utils import LogSequence


def test_basic_install(tmpdir):
    """If this test fails, try running "pip uninstall lorem dummy-yummy iplib" before running it.
    """

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
    exception_raised = False
    try:
        venv.install_from_list([package_name])
    except Exception:
        exception_raised = True

    assert exception_raised
    log_sequence = LogSequence(caplog)
    log_sequence.contains("inmanta.env", logging.ERROR, f"requirements: {package_name}")


def test_install_package_already_installed_in_parent_env(tmpdir):
    venv = env.VirtualEnv(tmpdir)
    venv.use_virtual_env()
    installed_packages = [
        p for p in env.VirtualEnv._get_installed_packages(venv._parent_python).keys() if p != "pip" and p != "setuptools"
    ]
    random_package = installed_packages[0]
    venv.install_from_list([random_package])

    # Assert not installed in virtual_python venv
    assert random_package not in env.VirtualEnv._get_installed_packages(venv.virtual_python).keys()


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
    req = ["lorem == 0.1.1", "lorem > 0.1", "dummy-yummy", "iplib@git+https://github.com/bartv/python3-iplib", "lorem"]

    req_lines = [x for x in e._gen_requirements_file(req).split("\n") if len(x) > 0]
    assert len(req_lines) == 3


def test_remove_requirements_present_in_parent_env(tmpdir):
    v = env.VirtualEnv(tmpdir)
    v.use_virtual_env()

    # Verify parsing works
    reqs = [
        "lorem == 0.1.1",
        "lorem > 0.1",
        "lorem >= 1.1,<1.5",
        "dummy-yummy",
        "iplib@git+https://github.com/bartv/python3-iplib",
    ]
    assert v._remove_requirements_present_in_parent_env(reqs) == reqs

    installed_packages = {
        k: v for k, v in env.VirtualEnv._get_installed_packages(v._parent_python).items() if k != "pip" and k != "setuptools"
    }
    package = next(iter(installed_packages.keys()))
    package_version = installed_packages[package]
    splitted_package_version = package_version.split(".", maxsplit=1)
    newer_package_version = f"{int(splitted_package_version[0]) + 1}.{splitted_package_version[1]}"

    # Package is present in parent venv and constraint is met
    reqs = [f"{package}=={package_version}", "non_existing_package==1.1.1"]
    reqs_after_removal = ["non_existing_package==1.1.1"]
    assert v._remove_requirements_present_in_parent_env(reqs) == reqs_after_removal

    reqs = [f"{package}>={package_version},<{newer_package_version}", "non_existing_package==1.1.1"]
    assert v._remove_requirements_present_in_parent_env(reqs) == reqs_after_removal

    # Package is present in parent venv, but constraint isn't met
    reqs = [f"{package}=={newer_package_version}", "non_existing_package==1.1.1"]
    assert v._remove_requirements_present_in_parent_env(reqs) == reqs

    reqs = [f"{package}>{package_version}", "non_existing_package==1.1.1"]
    assert v._remove_requirements_present_in_parent_env(reqs) == reqs
