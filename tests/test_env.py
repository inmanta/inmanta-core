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
import re
import subprocess
import sys
import tempfile
from importlib.abc import Loader
from re import Pattern
from subprocess import CalledProcessError
from typing import Optional
from unittest.mock import patch

import pkg_resources
import py
import pytest
from pkg_resources import Requirement

from inmanta import env, loader, module
from inmanta.data.model import PipConfig
from inmanta.env import Pip
from packaging import version
from utils import LogSequence, PipIndex, create_python_package

if "inmanta-core" in env.process_env.get_installed_packages(only_editable=True):
    pytest.skip(
        "The tests in this module will fail if it runs against inmanta-core installed in editable mode, "
        "because the build tag on the development branch is set to .dev0 by default. The inmanta package protection feature "
        "would make pip install a non-editable version of the same package. But no version with build tag .dev0 exists "
        "on the python package repository.",
        allow_module_level=True,
    )


@pytest.mark.slowtest
def test_venv_pyton_env_empty_string(tmpdir):
    """test that an exception is raised if the venv path is an empty string"""
    with pytest.raises(ValueError) as e:
        env.VirtualEnv("")
    assert e.value.args[0] == "The env_path cannot be an empty string."

    env_dir1 = tmpdir.mkdir("env1").strpath
    venv1 = env.VirtualEnv(env_dir1)
    venv1.use_virtual_env()

    env_dir2 = tmpdir.mkdir("env2").strpath
    venv2 = env.VirtualEnv(env_dir2)
    venv2.env_path = ""
    with pytest.raises(Exception) as e:
        venv2.use_virtual_env()
    assert e.value.args[0] == "The env_path cannot be an empty string."

    with pytest.raises(ValueError) as e:
        env.PythonEnvironment(python_path="")
    assert e.value.args[0] == "The python_path cannot be an empty string."

    with pytest.raises(ValueError) as e:
        env.PythonEnvironment(env_path="")
    assert e.value.args[0] == "The env_path cannot be an empty string."


@pytest.mark.slowtest
def test_basic_install(tmpdir):
    """If this test fails, try running "pip uninstall lorem dummy-yummy iplib" before running it."""
    env_dir1 = tmpdir.mkdir("env1").strpath

    with pytest.raises(ImportError):
        import lorem  # NOQA

    venv1 = env.VirtualEnv(env_dir1)

    venv1.use_virtual_env()
    venv1.install_from_list(["lorem"])
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


@pytest.mark.slowtest
def test_install_package_already_installed_in_parent_env(tmpdir):
    """Test using and installing a package that is already present in the parent virtual environment."""
    # get all packages in the parent
    parent_installed = list(env.process_env.get_installed_packages().keys())

    # create a venv and list all packages available in the venv
    venv = env.VirtualEnv(str(tmpdir))
    venv.use_virtual_env()

    installed_packages = list(env.PythonEnvironment(python_path=venv._parent_python).get_installed_packages().keys())

    # verify that the venv sees all parent packages
    assert not set(parent_installed) - set(installed_packages)

    # site dir should be empty
    site_dir = os.path.join(venv.env_path, "lib/python*/site-packages")
    dirs = glob.glob(site_dir)
    assert len(dirs) == 1
    site_dir = dirs[0]

    def _list_dir(path: str, ignore: list[str]) -> list[str]:
        return [d for d in os.listdir(site_dir) if d not in ignore]

    # site_dir should only contain a sitecustomize.py file that sets up inheritance from the parent venv
    assert not _list_dir(site_dir, ignore=["inmanta-inherit-from-parent-venv.pth", "__pycache__"])

    # test installing a package that is already present in the parent venv
    assert "more-itertools" in parent_installed
    venv.install_from_list(["more-itertools"])

    # site_dir should only contain a sitecustomize.py file that sets up inheritance from the parent venv
    assert not _list_dir(site_dir, ignore=["inmanta-inherit-from-parent-venv.pth", "__pycache__"])

    # report json
    subprocess.check_output([os.path.join(venv.env_path, "bin/pip"), "list"])


def test_gen_req_file():
    """
    These are all examples used in older testcases that did not work correctly before
    They are supported now

    This testcase now only verifies they are all correctly parsed
    """

    reqs = [
        "lorem == 0.1.1",
        "lorem > 0.1",
        "dummy-yummy",
        "iplib@git+https://github.com/bartv/python3-iplib",
        "lorem",
        # verify support for environment markers as described in PEP 508
        "lorem;python_version<'3.7'",
        "lorem;platform_machine == 'x86_64' and platform_system == 'Linux'",
        "lorem == 0.1;python_version=='3.7'",
        "lorem == 0.2;python_version=='3.9'",
        "dep[opt]",
        "dep[otheropt]",
    ]

    # make sure they all parse
    for req in reqs:
        pkg_resources.parse_requirements(req)


def test_environment_python_version_multi_digit(tmpdir: py.path.local) -> None:
    """
    Make sure the constructor for env.Environment can handle multi-digit minor versions of Python to ensure compatibility with
    Python 3.10+.
    """
    with patch("sys.version_info", new=(3, 123, 0)):
        # python version is not included in path on windows
        with patch("sys.platform", new="linux"):
            assert env.PythonEnvironment(env_path=str(tmpdir)).site_packages_dir == os.path.join(
                str(tmpdir), "lib", "python3.123", "site-packages"
            )


@pytest.mark.slowtest
@pytest.mark.parametrize_any("version", [None, version.Version("8.6.0")])
def test_process_env_install_from_index(
    tmpdir: str,
    tmpvenv_active: tuple[py.path.local, py.path.local],
    version: Optional[version.Version],
) -> None:
    """
    Install a package from a pip index into the process_env. Assert any version specs are respected.
    """
    package_name: str = "more-itertools"
    assert package_name not in env.process_env.get_installed_packages()
    env.process_env.install_for_config(
        [Requirement.parse(package_name + (f"=={version}" if version is not None else ""))],
        config=PipConfig(
            use_system_config=True,  # we need an upstream for some packages
        ),
    )
    installed: dict[str, version.Version] = env.process_env.get_installed_packages()
    assert package_name in installed
    if version is not None:
        assert installed[package_name] == version
    # legacy method
    # We call it here to make sure the legacy compatibility works
    # It massages the inputs to get to the same call as the one above.
    # It should hit the cache there and return here.
    # Cheap and fast test
    env.process_env.install_from_index(
        [Requirement.parse(package_name + (f"=={version}" if version is not None else ""))],
        use_pip_config=True,
    )


@pytest.mark.slowtest
def test_process_env_install_from_index_not_found(
    tmpvenv_active: tuple[py.path.local, py.path.local], local_module_package_index: str
) -> None:
    """
    Attempt to install a package that does not exist from a pip index. Assert the appropriate error is raised.
    """
    with pytest.raises(env.PackageNotFound, match="Packages this-package-does-not-exist were not found in the given indexes."):
        # pass use_system_config=False for security reasons (anyone could publish this package to PyPi)
        env.process_env.install_for_config(
            [Requirement.parse("this-package-does-not-exist")],
            config=PipConfig(
                index_url=local_module_package_index,
            ),
        )


@pytest.mark.slowtest
def test_process_env_install_from_index_conflicting_reqs(
    tmpdir: str, tmpvenv_active: tuple[py.path.local, py.path.local]
) -> None:
    """
    Attempt to install a package with conflicting version requirements from a pip index. Make sure this fails and the
    package remains uninstalled.
    """
    package_name: str = "more-itertools"
    with pytest.raises(env.ConflictingRequirements) as e:
        env.process_env.install_for_config(
            [Requirement.parse(f"{package_name}{version}") for version in [">8.5", "<=8"]],
            config=PipConfig(
                use_system_config=True,  # we need an upstream for some packages
            ),
        )
    assert "conflicting dependencies" in e.value.msg
    assert package_name not in env.process_env.get_installed_packages()


@pytest.mark.slowtest
@pytest.mark.parametrize("editable", [True, False])
def test_process_env_install_from_source(
    tmpvenv_active: tuple[py.path.local, py.path.local],
    modules_v2_dir: str,
    editable: bool,
) -> None:
    """
    Install a package from source into the process_env. Make sure the editable option actually results in an editable install.
    """
    package_name: str = "inmanta-module-minimalv2module"
    project_dir: str = os.path.join(modules_v2_dir, "minimalv2module")
    assert package_name not in env.process_env.get_installed_packages()
    env.process_env.install_from_source([env.LocalPackagePath(path=project_dir, editable=editable)])
    assert package_name in env.process_env.get_installed_packages()
    if editable:
        assert package_name in env.process_env.get_installed_packages(only_editable=True)


# v1 plugin loader overrides loader paths so verify that it doesn't interfere with env.process_env installs
@pytest.mark.parametrize("v1_plugin_loader", [True, False])
@pytest.mark.parametrize("package_name", ["lorem", "more-itertools", "inmanta-module-minimalv2module"])
@pytest.mark.slowtest
def test_active_env_get_module_file(
    local_module_package_index: str,
    tmpdir: py.path.local,
    tmpvenv_active: tuple[py.path.local, py.path.local],
    v1_plugin_loader: bool,
    package_name: str,
) -> None:
    """
    Test the env.ActiveEnv.get_module_file() command on a newly installed package. Make sure it works regardless of whether we
    install a dependency of inmanta-core (which is already installed in the encapsulating development venv), a new package or an
    inmanta module (namespace package).
    """
    venv_dir, _ = tmpvenv_active

    if package_name.startswith(module.ModuleV2.PKG_NAME_PREFIX):
        module_name = "inmanta_plugins." + package_name[len(module.ModuleV2.PKG_NAME_PREFIX) :].replace("-", "_")
        index = str(local_module_package_index)
        pip_config = PipConfig(
            index_url=index,
        )

    else:
        module_name = package_name.replace("-", "_")
        pip_config = PipConfig(
            use_system_config=True,
        )

    # unload module if already loaded from encapsulating development venv
    if module_name in sys.modules:
        loaded = [sub for sub in sys.modules.keys() if sub.startswith(module_name)]
        for sub in loaded:
            del sys.modules[sub]
    importlib.invalidate_caches()

    if v1_plugin_loader:
        loader.PluginModuleFinder.configure_module_finder([os.path.join(str(tmpdir), "libs")])

    assert env.ActiveEnv.get_module_file(module_name) is None
    env.process_env.install_for_config([Requirement.parse(package_name)], pip_config)
    assert package_name in env.process_env.get_installed_packages()
    module_info: Optional[tuple[Optional[str], Loader]] = env.ActiveEnv.get_module_file(module_name)
    assert module_info is not None
    module_file, mod_loader = module_info
    assert module_file is not None
    assert not isinstance(mod_loader, loader.PluginModuleLoader)
    assert module_file == os.path.join(env.process_env.site_packages_dir, *module_name.split("."), "__init__.py")
    # verify that the package was installed in the development venv
    assert str(venv_dir) in module_file
    importlib.import_module(module_name)
    assert module_name in sys.modules
    assert sys.modules[module_name].__file__ == module_file


@pytest.mark.slowtest
def test_active_env_get_module_file_editable_namespace_package(
    tmpdir: str,
    tmpvenv_active: tuple[py.path.local, py.path.local],
    modules_v2_dir: str,
    local_module_package_index,
) -> None:
    """
    Verify that get_module_file works after installing an editable namespace package in an active environment.
    """
    package_name: str = "inmanta-module-minimalv2module"
    module_name: str = "inmanta_plugins.minimalv2module"

    assert env.ActiveEnv.get_module_file(module_name) is None
    project_dir: str = os.path.join(modules_v2_dir, "minimalv2module")
    env.process_env.install_for_config(
        requirements=[],
        paths=[env.LocalPackagePath(path=project_dir, editable=True)],
        config=PipConfig(use_system_config=False, index_url=local_module_package_index),
    )
    assert package_name in env.process_env.get_installed_packages()
    module_info: Optional[tuple[Optional[str], Loader]] = env.ActiveEnv.get_module_file(module_name)
    assert module_info is not None
    module_file, mod_loader = module_info
    assert module_file is not None
    assert not isinstance(mod_loader, loader.PluginModuleLoader)
    assert module_file == os.path.join(modules_v2_dir, "minimalv2module", *module_name.split("."), "__init__.py")
    importlib.import_module(module_name)
    assert module_name in sys.modules
    assert sys.modules[module_name].__file__ == module_file
    # legacy method
    # We call it here to make sure the legacy compatibility works
    # It massages the inputs to get to the same call as the one above.
    # It should hit the cache there and return here.
    # Cheap and fast test
    env.process_env.install_from_source(
        paths=[env.LocalPackagePath(path=project_dir, editable=True)],
    )


def create_install_package(
    name: str, version: version.Version, requirements: list[Requirement], local_module_package_index: str
) -> None:
    """
    Creates and installs a simple package with specified requirements. Creates package in a temporary directory and
    cleans it up after install.

    :param name: Package name.
    :param version: Version for this package.
    :param requirements: Requirements on other packages. Required packages must already be installed when calling this function.
    :param local_module_package_index: upstream index to get setuptools and wheel
    """
    req_string: str = (
        "" if len(requirements) == 0 else ("[options]\ninstall_requires=" + "\n    ".join(str(req) for req in requirements))
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "setup.cfg"), "w") as fd:
            fd.write(
                f"""
[metadata]
name = {name}
version = {version}

{req_string}
                """.strip()
            )
        with open(os.path.join(tmpdir, "pyproject.toml"), "w") as fd:
            fd.write(
                """
[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"
                """.strip()
            )
        env.process_env.install_for_config(
            requirements=[],
            paths=[env.LocalPackagePath(path=str(tmpdir), editable=False)],
            config=PipConfig(
                use_system_config=False,
                index_url=local_module_package_index,
            ),
        )


@pytest.mark.slowtest
def test_active_env_check_basic(
    caplog,
    tmpdir: str,
    tmpvenv_active_inherit: str,
    local_module_package_index,  # upstream for setuptools for isolated build
) -> None:
    """
    Verify that the env.ActiveEnv.check() method detects all possible forms of incompatibilities within the environment.
    """
    caplog.set_level(logging.WARNING)

    in_scope_test: Pattern[str] = re.compile("test-package-.*")
    in_scope_nonext: Pattern[str] = re.compile("nonexistant-package")

    error_msg: str = "Incompatibility between constraint"

    def assert_all_checks(expect_test: tuple[bool, str] = (True, ""), expect_nonext: tuple[bool, str] = (True, "")) -> None:
        """
        verify what the check method for 2 different scopes: for an existing package and a non existing one.

        param: expect_test: Tuple with as first value a bool and as second value a string. The bool is true if the execution
        will not raise an error, false if it will raise an error. The second argument is the warning message that can be find
        in the logs.
        param: expect_nonext: Tuple with as first value a bool and as second value a string. The bool is true if the execution
        will not raise an error, false if it will raise an error. The second argument is the warning message that can be find
        in the logs.
        """
        for in_scope, expect in [(in_scope_test, expect_test), (in_scope_nonext, expect_nonext)]:
            caplog.clear()
            if expect[0]:
                env.ActiveEnv.check(in_scope)
                if expect[1] == "":
                    assert error_msg not in {rec.message for rec in caplog.records}
                else:
                    assert expect[1] in {rec.message for rec in caplog.records}
            else:
                with pytest.raises(env.ConflictingRequirements) as e:
                    env.ActiveEnv.check(in_scope)
                assert expect[1] in e.value.get_message()

    assert_all_checks()
    create_install_package("test-package-one", version.Version("1.0.0"), [], local_module_package_index)
    assert_all_checks()
    create_install_package(
        "test-package-two", version.Version("1.0.0"), [Requirement.parse("test-package-one~=1.0")], local_module_package_index
    )
    assert_all_checks()
    create_install_package("test-package-one", version.Version("2.0.0"), [], local_module_package_index)
    assert_all_checks(
        expect_test=(
            False,
            "Incompatibility between constraint test-package-one~=1.0 and installed version 2.0.0 (from test-package-two)",
        ),
        expect_nonext=(True, error_msg + " test-package-one~=1.0 and installed version 2.0.0 (from test-package-two)"),
    )


@pytest.mark.slowtest
def test_active_env_check_constraints(caplog, tmpvenv_active_inherit: str, local_module_package_index) -> None:
    """
    Verify that the env.ActiveEnv.check() method's constraints parameter is taken into account as expected.
    """
    caplog.set_level(logging.WARNING)
    in_scope: Pattern[str] = re.compile("test-package-.*")
    constraints: list[Requirement] = [Requirement.parse("test-package-one~=1.0")]

    env.ActiveEnv.check(in_scope)

    caplog.clear()
    with pytest.raises(env.ConflictingRequirements):
        env.ActiveEnv.check(in_scope, constraints)

    caplog.clear()
    create_install_package("test-package-one", version.Version("1.0.0"), [], local_module_package_index)
    env.ActiveEnv.check(in_scope, constraints)
    assert "Incompatibility between constraint" not in caplog.text

    # Add an unrelated package to the venv, that should not matter
    # setup for #4761
    caplog.clear()
    create_install_package(
        "ext-package-one", version.Version("1.0.0"), [Requirement.parse("test-package-one==1.0")], local_module_package_index
    )
    env.ActiveEnv.check(in_scope, constraints)
    assert "Incompatibility between constraint" not in caplog.text

    caplog.clear()
    v: version.Version = version.Version("2.0.0")
    create_install_package("test-package-one", v, [], local_module_package_index)
    # test for #4761
    # without additional constrain, this is not a hard failure
    # except for the unrelated package, which should produce a warning
    env.ActiveEnv.check(in_scope, [])
    assert (
        "Incompatibility between constraint test-package-one==1.0 and installed version 2.0.0 (from ext-package-one)"
        in caplog.text
    )

    caplog.clear()
    with pytest.raises(env.ConflictingRequirements):
        env.ActiveEnv.check(in_scope, constraints)


@pytest.mark.slowtest
def test_override_inmanta_package(tmpvenv_active_inherit: env.VirtualEnv) -> None:
    """
    Ensure that an ActiveEnv cannot override the main inmanta packages: inmanta-service-orchestrator, inmanta, inmanta-core.
    """
    installed_pkgs = tmpvenv_active_inherit.get_installed_packages()
    assert "inmanta-core" in installed_pkgs, "The inmanta-core package should be installed to run the tests"

    inmanta_requirements = Requirement.parse("inmanta-core==4.0.0")
    with pytest.raises(env.ConflictingRequirements) as excinfo:
        tmpvenv_active_inherit.install_for_config(
            requirements=[inmanta_requirements],
            config=PipConfig(
                use_system_config=True,  # we need some upstream
            ),
        )
    match = re.search(
        r"Cannot install (inmanta-core==4\.0\.0 and inmanta-core=.*|inmanta-core=.* and inmanta-core==4\.0\.0) because these "
        r"package versions have conflicting dependencies",
        excinfo.value.msg,
    )
    assert match is not None


@pytest.mark.slowtest
@pytest.mark.parametrize("invalid_char", ['"', "$", "`"])
def test_invalid_chars_in_venv_path(tmpdir, invalid_char: str) -> None:
    """
    Test that an error is raised when attempting to create a venv with invalid chars in its path.
    """
    venv_name = f"test{invalid_char}test"
    venv_dir = os.path.join(tmpdir, venv_name)

    with pytest.raises(ValueError) as excinfo:
        env.VirtualEnv(venv_dir)
    assert (
        f"Cannot create virtual environment because the provided path `{venv_dir}` contains an"
        f" invalid character (`{invalid_char}`)."
    ) in str(excinfo.value)


@pytest.mark.slowtest
def test_cache_on_active_env(tmpvenv_active_inherit: env.ActiveEnv, local_module_package_index: str) -> None:
    """
    Test whether the cache on an active env works correctly.
    """

    def _assert_install(requirement: str, installed: bool) -> None:
        parsed_requirement = Requirement.parse(requirement)
        for r in [requirement, parsed_requirement]:
            assert tmpvenv_active_inherit.are_installed(requirements=[r]) == installed

    _assert_install("inmanta-module-elaboratev2module==1.2.3", installed=False)
    tmpvenv_active_inherit.install_for_config(
        requirements=[Requirement.parse("inmanta-module-elaboratev2module==1.2.3")],
        config=PipConfig(
            index_url=local_module_package_index,
        ),
    )
    _assert_install("inmanta-module-elaboratev2module==1.2.3", installed=True)
    _assert_install("inmanta-module-elaboratev2module~=1.2.0", installed=True)
    _assert_install("inmanta-module-elaboratev2module<1.2.4", installed=True)
    _assert_install("inmanta-module-elaboratev2module>1.2.3", installed=False)
    _assert_install("inmanta-module-elaboratev2module==1.2.4", installed=False)


@pytest.mark.slowtest
def test_basic_logging(tmpdir, caplog):
    with caplog.at_level(logging.INFO):
        env_dir1 = tmpdir.mkdir("env1").strpath

        venv1 = env.VirtualEnv(env_dir1)

        venv1.use_virtual_env()

        log_sequence = LogSequence(caplog)
        log_sequence.assert_not("inmanta.env", logging.INFO, f"Creating new virtual environment in {env_dir1}")
        log_sequence.contains("inmanta.env", logging.INFO, f"Using virtual environment at {env_dir1}")


@pytest.mark.slowtest
def test_are_installed_dependency_cycle_on_extra(tmpdir, tmpvenv_active_inherit: env.VirtualEnv) -> None:
    """
    Ensure that the `ActiveEnv.are_installed()` method doesn't go into an infinite loop when there is a circular dependency
    involving an extra.

    Dependency loop:
        pkg[optional]
           -> dep[optional]
               -> pkg[optional]
    """
    pip_index = PipIndex(artifact_dir=str(tmpdir))
    create_python_package(
        name="pkg",
        pkg_version=version.Version("1.0.0"),
        path=os.path.join(tmpdir, "pkg"),
        publish_index=pip_index,
        optional_dependencies={
            "optional-pkg": [Requirement.parse("dep[optional-dep]")],
        },
    )
    create_python_package(
        name="dep",
        pkg_version=version.Version("1.0.0"),
        path=os.path.join(tmpdir, "dep"),
        publish_index=pip_index,
        optional_dependencies={
            "optional-dep": [Requirement.parse("pkg[optional-pkg]")],
        },
    )

    requirements = [Requirement.parse("pkg[optional-pkg]")]
    tmpvenv_active_inherit.install_for_config(
        requirements=requirements,
        config=PipConfig(
            index_url=pip_index.url,
        ),
    )
    assert tmpvenv_active_inherit.are_installed(requirements=requirements)


@pytest.mark.slowtest
def test_pip_logs(caplog, tmpvenv_active_inherit: str) -> None:
    """
    Verify the logs of a pip install:
        - all records start with 'inmanta.pip'
        - content of requirements and constraints files are logged
        - the pip command is logged
    """
    caplog.set_level(logging.DEBUG)

    with tempfile.TemporaryDirectory() as tmpdir:
        requirement1 = os.path.join(tmpdir, "requirement1.txt")
        requirement2 = os.path.join(tmpdir, "requirement2.txt")
        constraint1 = os.path.join(tmpdir, "constraint1.txt")
        constraint2 = os.path.join(tmpdir, "constraint2.txt")
        with open(requirement1, "w") as fd:
            fd.write(
                """
inmanta-module-std

                """
            )
        with open(requirement2, "w") as fd:
            fd.write(
                """
inmanta-module-net

inmanta-module-ip
                """
            )
        with open(constraint1, "w") as fd:
            fd.write(
                """
inmanta-module-std
                """
            )
        with open(constraint2, "w") as fd:
            fd.write(
                """

inmanta-module-ip
inmanta-module-net


                """
            )
        caplog.clear()
        Pip.run_pip_install_command_from_config(
            python_path=env.process_env.python_path,
            constraints_files=[constraint1, constraint2],
            requirements_files=[requirement1, requirement2],
            config=PipConfig(use_system_config=True),
        )

        assert all(record.name == "inmanta.pip" for record in caplog.records)
        python_path: str = tmpvenv_active_inherit.python_path
        assert (
            f"""
Content of requirements files:
    {requirement1}:
        inmanta-module-std
    {requirement2}:
        inmanta-module-net
        inmanta-module-ip
Content of constraints files:
    {constraint1}:
        inmanta-module-std
    {constraint2}:
        inmanta-module-ip
        inmanta-module-net
Pip command: {python_path} -m pip install -c {constraint1} -c {constraint2} -r {requirement1} -r {requirement2}
""".strip()
            in caplog.messages
        )
