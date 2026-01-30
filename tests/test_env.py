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
from subprocess import CalledProcessError
from typing import Callable, LiteralString, Optional
from unittest.mock import patch

import py
import pytest

import inmanta.util
from inmanta import env, loader, module
from inmanta.data.model import PipConfig
from inmanta.env import Pip
from packaging import version
from utils import LogSequence, PipIndex, create_python_package


@pytest.mark.slowtest
def test_venv_pyton_env_empty_string(tmpdir, deactive_venv):
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
def test_basic_install(tmpdir, deactive_venv):
    env_dir1 = tmpdir.mkdir("env1").strpath
    venv1 = env.VirtualEnv(env_dir1)
    venv1.use_virtual_env()

    assert not venv1.are_installed(["lorem"])

    venv1.install_from_list(["lorem"])
    assert venv1.are_installed(["lorem"])

    assert not venv1.are_installed(["dummy-yummy"])

    venv1 = env.VirtualEnv(env_dir1)
    venv1.use_virtual_env()
    venv1.install_from_list(["dummy-yummy"])
    assert venv1.are_installed(["dummy-yummy"])


def test_git_based_install(tmpdir: py.path.local, deactive_venv) -> None:
    """
    Verify that the install methods can handle git-based installs over https.
    """
    venv = env.VirtualEnv(tmpdir.mkdir("env").strpath)
    venv.use_virtual_env()

    pkg_name: LiteralString = "pytest-inmanta"
    assert not venv.are_installed([pkg_name])

    try:
        venv.install_from_list([f"{pkg_name}@git+https://github.com/inmanta/{pkg_name}"])
    except CalledProcessError as ep:
        print(ep.stdout)
        raise

    assert venv.are_installed([pkg_name])


@pytest.mark.slowtest
def test_install_package_already_installed_in_parent_env(tmpdir, deactive_venv):
    """Test using and installing a package that is already present in the parent virtual environment."""
    # get all packages in the parent
    parent_installed = list(env.process_env.get_installed_packages().keys())

    # create a venv and list all packages available in the venv
    venv = env.VirtualEnv(str(tmpdir))
    venv.use_virtual_env()

    installed_packages = list(venv.get_installed_packages().keys())
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
        inmanta.util.parse_requirement(requirement=req)


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
        [inmanta.util.parse_requirement(requirement=package_name + (f"=={version}" if version is not None else ""))],
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
        [inmanta.util.parse_requirement(requirement=package_name + (f"=={version}" if version is not None else ""))],
        use_pip_config=True,
    )


@pytest.mark.slowtest
@pytest.mark.parametrize_any("use_extra_indexes_env", [False, True])
@pytest.mark.parametrize_any("use_extra_indexes", [False, True])
@pytest.mark.parametrize_any("use_system_config", [False, True])
def test_process_env_install_from_index_not_found_env_var(
    tmpvenv_active: tuple[py.path.local, py.path.local],
    monkeypatch,
    create_empty_local_package_index_factory: Callable[[str], str],
    use_extra_indexes: bool,
    use_extra_indexes_env: bool,
    use_system_config: bool,
) -> None:
    """
    Attempt to install a package that does not exist from the pip indexes defined in the env vars, in the pip config or in both.
    This if the system config are used or not.
    Assert the appropriate error is raised.
    """
    index_urls = [create_empty_local_package_index_factory()]

    if use_extra_indexes_env:
        extra_env_indexes = [
            create_empty_local_package_index_factory("extra_env1"),
            create_empty_local_package_index_factory("extra_env2"),
        ]
        # Convert list to a space-separated string for the environment variable
        monkeypatch.setenv("PIP_EXTRA_INDEX_URL", " ".join(extra_env_indexes))
        if use_system_config:
            # Include environment extra indexes in the main list for assertion
            index_urls.extend(extra_env_indexes)

    if use_extra_indexes:
        index_urls.extend(
            [
                create_empty_local_package_index_factory("extra1"),
                create_empty_local_package_index_factory("extra2"),
            ]
        )

    expected = (
        "Packages this-package-does-not-exist were not "
        "found in the given indexes. (Looking in indexes: %s)" % ", ".join(index_urls)
    )

    with pytest.raises(env.PackageNotFound, match=re.escape(expected)):
        env.process_env.install_for_config(
            [inmanta.util.parse_requirement(requirement="this-package-does-not-exist")],
            config=PipConfig(
                index_url=index_urls[0],
                # The first element should only be passed to the index_url. If there are indexes in the environment
                # they should not be passed in the extra_index_url as they are already present in PIP_EXTRA_INDEX_URL
                # (second and third element of index_urls).
                extra_index_url=index_urls[3:] if (use_system_config and use_extra_indexes_env) else index_urls[1:],
                use_system_config=use_system_config,
            ),
        )


@pytest.mark.parametrize_any("use_system_config", [True, False])
def test_process_env_install_no_index(tmpdir: py.path.local, monkeypatch, use_system_config: bool, deactive_venv) -> None:
    """
    Attempt to install a package that does not exist with --no-index.
    To have --no-index set in the pip cmd, the config should not contain an index_url,
    we should not be using the system config and a path needs to be specified.
    it can also be set in the env_vars
    Assert the appropriate error is raised.
    """
    if use_system_config:
        monkeypatch.setenv("PIP_NO_INDEX", "true")

    setup_py_content = """
from setuptools import setup
setup(name="test")
"""
    # Write the minimal setup.py content to the temporary directory
    setup_py_path = os.path.join(tmpdir, "setup.py")
    with open(setup_py_path, "w") as setup_file:
        setup_file.write(setup_py_content)

    # We have two possible errors:
    # we install two packages, that fail differently
    # The order of failure is not fixed
    expected = re.escape("Packages this-package-does-not-exist were not found. No indexes were used.")
    other_expected = r"Packages setuptools.*were not found\. No indexes were used\."

    with pytest.raises(env.PackageNotFound, match=f"{expected}|{other_expected}"):
        deactive_venv.install_for_config(
            requirements=[inmanta.util.parse_requirement(requirement="this-package-does-not-exist")],
            paths=[env.LocalPackagePath(path=str(tmpdir))],
            config=PipConfig(use_system_config=use_system_config),
            add_inmanta_requires=False,
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
            [inmanta.util.parse_requirement(requirement=f"{package_name}{version}") for version in [">8.5", "<=8"]],
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
    env.process_env.install_for_config([inmanta.util.parse_requirement(requirement=package_name)], pip_config)
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
        add_inmanta_requires=False,
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
    name: str, version: version.Version, requirements: list[inmanta.util.CanonicalRequirement], local_module_package_index: str
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
            fd.write(f"""
[metadata]
name = {name}
version = {version}

{req_string}
                """.strip())
        with open(os.path.join(tmpdir, "pyproject.toml"), "w") as fd:
            fd.write("""
[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"
                """.strip())
        env.process_env.install_for_config(
            requirements=[],
            paths=[env.LocalPackagePath(path=str(tmpdir), editable=False)],
            config=PipConfig(
                use_system_config=False,
                index_url=local_module_package_index,
            ),
        )


@pytest.mark.slowtest
def test_override_inmanta_package(tmpvenv_active_inherit: env.VirtualEnv) -> None:
    """
    Ensure that an ActiveEnv cannot override the main inmanta packages: inmanta-service-orchestrator, inmanta, inmanta-core.
    """
    installed_pkgs = tmpvenv_active_inherit.get_installed_packages()
    assert "inmanta-core" in installed_pkgs, "The inmanta-core package should be installed to run the tests"

    inmanta_requirements = inmanta.util.parse_requirement(requirement="inmanta-core==4.0.0")
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
        parsed_requirement = inmanta.util.parse_requirement(requirement=requirement)
        for r in [requirement, parsed_requirement]:
            assert tmpvenv_active_inherit.are_installed(requirements=[r]) == installed

    _assert_install("inmanta-module-elaboratev2module==1.2.3", installed=False)
    tmpvenv_active_inherit.install_for_config(
        requirements=[inmanta.util.parse_requirement(requirement="inmanta-module-elaboratev2module==1.2.3")],
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
        log_sequence.contains("inmanta.env", logging.INFO, f"Initializing virtual environment at {env_dir1}")


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
            "optional-pkg": [inmanta.util.parse_requirement(requirement="dep[optional-dep]")],
        },
    )
    create_python_package(
        name="dep",
        pkg_version=version.Version("1.0.0"),
        path=os.path.join(tmpdir, "dep"),
        publish_index=pip_index,
        optional_dependencies={
            "optional-dep": [inmanta.util.parse_requirement(requirement="pkg[optional-pkg]")],
        },
    )

    requirements = [inmanta.util.parse_requirement(requirement="pkg[optional-pkg]")]
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
            fd.write("""
inmanta-module-std

                """)
        with open(requirement2, "w") as fd:
            fd.write("""
inmanta-module-net

inmanta-module-ip
                """)
        with open(constraint1, "w") as fd:
            fd.write("""
inmanta-module-std
                """)
        with open(constraint2, "w") as fd:
            fd.write("""

inmanta-module-ip
inmanta-module-net


                """)
        caplog.clear()
        Pip.run_pip_install_command_from_config(
            python_path=env.process_env.python_path,
            constraints_files=[constraint1, constraint2],
            requirements_files=[requirement1, requirement2],
            config=PipConfig(use_system_config=True),
        )

        assert all(record.name == "inmanta.pip" for record in caplog.records)
        python_path: str = tmpvenv_active_inherit.python_path
        assert f"""
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
""".strip() in caplog.messages
