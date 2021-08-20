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
import importlib
import logging
import os
import subprocess
import sys
from importlib.abc import Loader
from subprocess import CalledProcessError
from typing import Dict, List, Optional, Tuple
from unittest.mock import patch

import py
import pydantic
import pytest
from pkg_resources import Requirement

from inmanta import env, loader, module
from packaging import version
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


@pytest.mark.parametrize("version", [None, version.Version("8.6.0")])
def test_processenv_install_from_index(
    tmpvenv_active: Tuple[py.path.local, py.path.local], version: Optional[version.Version]
) -> None:
    venv_dir, python_path = tmpvenv_active
    package_name: str = "more-itertools"
    assert package_name not in env.get_installed_packages(python_path)
    with patch("inmanta.env.ProcessEnv.python_path", new=str(python_path)):
        env.ProcessEnv.install_from_index([Requirement.parse(package_name + (f"=={version}" if version is not None else ""))])
    installed: Dict[str, version.Version] = env.get_installed_packages(python_path)
    assert package_name in installed
    if version is not None:
        assert installed[package_name] == version


def test_processenv_install_from_indexes_conflicting_reqs(tmpvenv_active: Tuple[py.path.local, py.path.local]) -> None:
    venv_dir, python_path = tmpvenv_active
    package_name: str = "more-itertools"
    with patch("inmanta.env.ProcessEnv.python_path", new=str(python_path)):
        with pytest.raises(subprocess.CalledProcessError) as e:
            env.ProcessEnv.install_from_index([Requirement.parse(f"{package_name}{version}") for version in [">8.5", "<=8"]])
        assert "conflicting dependencies" in e.value.stderr.decode()
    assert package_name not in env.get_installed_packages(python_path)


@pytest.mark.parametrize("editable", [True, False])
def test_processenv_install_from_source(
    tmpdir: py.path.local, tmpvenv_active: Tuple[py.path.local, py.path.local], modules_v2_dir: str, editable: bool
) -> None:
    venv_dir, python_path = tmpvenv_active
    package_name: str = "inmanta-module-minimalv2module"
    project_dir: str = os.path.join(modules_v2_dir, "minimalv2module")
    assert package_name not in env.get_installed_packages(python_path)
    with patch("inmanta.env.ProcessEnv.python_path", new=str(python_path)):
        env.ProcessEnv.install_from_source([env.LocalPackagePath(path=project_dir, editable=editable)])
    assert package_name in env.get_installed_packages(python_path)
    if editable:
        assert any(
            package["name"] == package_name
            for package in pydantic.parse_raw_as(
                List[Dict[str, str]],
                subprocess.check_output([python_path, "-m", "pip", "list", "--editable", "--format", "json"]).decode(),
            )
        )


# v1 plugin loader overrides loader paths so verify that it doesn't interfere with ProcessEnv installs
@pytest.mark.parametrize("v1_plugin_loader", [True, False])
# make sure installation works regardless of whether we install a dependency of inmanta-core (wich is already installed in
# the encapsulating development venv), a new package or an inmanta module
@pytest.mark.parametrize("package_name", ["tinykernel", "more-itertools", "inmanta-module-minimalv2module"])
def test_processenv_get_module_file(
    local_module_package_index: str,
    tmpdir: py.path.local,
    tmpvenv_active: Tuple[py.path.local, py.path.local],
    v1_plugin_loader: bool,
    package_name: str,
) -> None:
    venv_dir, python_path = tmpvenv_active

    if package_name.startswith(module.ModuleV2.PKG_NAME_PREFIX):
        module_name = "inmanta_plugins." + package_name[len(module.ModuleV2.PKG_NAME_PREFIX) :].replace("-", "_")
        index = str(local_module_package_index)
    else:
        module_name = package_name.replace("-", "_")
        index = None

    # unload module if already loaded from encapsulating development venv
    if module_name in sys.modules:
        loaded = [sub for sub in sys.modules.keys() if sub.startswith(module_name)]
        for sub in loaded:
            del sys.modules[sub]
    importlib.invalidate_caches()

    if v1_plugin_loader:
        loader.PluginModuleFinder.configure_module_finder([str(tmpdir)])

    with patch("inmanta.env.ProcessEnv.python_path", new=str(python_path)):
        assert env.ProcessEnv.get_module_file(module_name) is None
        env.ProcessEnv.install_from_index([Requirement.parse(package_name)], index_urls=[index] if index is not None else None)
        assert package_name in env.get_installed_packages(python_path)
        module_info: Optional[Tuple[str, Loader]] = env.ProcessEnv.get_module_file(module_name)
        assert module_info is not None
        module_file, mod_loader = module_info
        assert not isinstance(mod_loader, loader.PluginModuleLoader)
        assert module_file == os.path.join(env.ProcessEnv.get_site_packages_dir(), *module_name.split("."), "__init__.py")
        importlib.import_module(module_name)
        assert module_name in sys.modules
        assert sys.modules[module_name].__file__ == module_file


# TODO: test ProcessEnv.check
