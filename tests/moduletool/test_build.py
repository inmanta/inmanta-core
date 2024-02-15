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

    Contact: code@inmanta.com
"""

import importlib.util
import logging
import os
import re
import shutil
import subprocess
import sys
import zipfile
from importlib.machinery import ModuleSpec
from types import ModuleType
from typing import Optional

import pytest
from pytest import MonkeyPatch

from inmanta import moduletool
from inmanta.const import CF_CACHE_DIR
from inmanta.module import ModuleMetadataFileNotFound
from inmanta.moduletool import ModuleBuildFailedError, V2ModuleBuilder
from packaging import version
from utils import v1_module_from_template


def run_module_build_soft(
    module_path: str,
    set_path_argument: bool,
    output_dir: Optional[str] = None,
    dev_build: bool = False,
    byte_code: bool = False,
) -> str:
    if not set_path_argument:
        module_path = None
    return moduletool.ModuleTool().build(module_path, output_dir, dev_build=dev_build, byte_code=byte_code)


def run_module_build(module_path: str, set_path_argument: bool, output_dir: Optional[str] = None) -> None:
    """
    Build the Inmanta module using the `inmanta module build` command.

    :param module_path: Path to the inmanta module
    :param set_path_argument: If true provide the module_path via the path argument, otherwise the module path is set via cwd.
    :param output_dir: The output directory where the resulting Python package will be stored.
    """
    cmd = [sys.executable, "-m", "inmanta.app", "module", "build"]
    if output_dir:
        cmd.extend(["-o", output_dir])
    if set_path_argument:
        cmd.append(module_path)
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    else:
        subprocess.check_output(cmd, cwd=module_path, stderr=subprocess.STDOUT)


@pytest.mark.parametrize_any(
    "module_name, is_v2_module, set_path_argument, byte_code",
    [
        ("minimalv2module", True, True, False),
        ("minimalv2module", True, False, False),
        ("elaboratev2module", True, True, False),
        ("elaboratev2module", True, False, False),
        ("elaboratev1module", False, False, False),
        ("elaboratev1module", False, False, True),
    ],
)
def test_build_v2_module(
    tmpdir,
    modules_dir: str,
    modules_v2_dir: str,
    module_name: str,
    is_v2_module: bool,
    set_path_argument: bool,
    byte_code: bool,
    monkeypatch: MonkeyPatch,
    disable_isolated_env_builder_cache: None,  # Test the code path used in production
) -> None:
    """
    Build a V2 package and verify that the required files are present in the resulting wheel.
    """
    module_dir: str
    if is_v2_module:
        module_dir = os.path.join(modules_v2_dir, module_name)
    else:
        module_dir = os.path.join(modules_dir, module_name)
    module_copy_dir = os.path.join(tmpdir, "module")
    shutil.copytree(module_dir, module_copy_dir)
    assert os.path.isdir(module_copy_dir)

    if not set_path_argument:
        monkeypatch.chdir(module_copy_dir)
    run_module_build_soft(module_copy_dir, set_path_argument, byte_code=byte_code)

    dist_dir = os.path.join(module_copy_dir, "dist")
    dist_dir_content = os.listdir(dist_dir)
    assert len(dist_dir_content) == 1
    wheel_file = os.path.join(dist_dir, dist_dir_content[0])
    assert wheel_file.endswith(".whl")

    extract_dir = os.path.join(tmpdir, "extract")
    with zipfile.ZipFile(wheel_file) as zip:
        zip.extractall(extract_dir)

    if byte_code:
        assert "linux_x86_64" in wheel_file
    else:
        assert "none-any" in wheel_file

    assert os.path.exists(os.path.join(extract_dir, "inmanta_plugins", module_name, "setup.cfg"))
    assert os.path.exists(
        os.path.join(extract_dir, "inmanta_plugins", module_name, "__init__.py" if not byte_code else "__init__.pyc")
    )
    assert os.path.exists(os.path.join(extract_dir, "inmanta_plugins", module_name, "model", "_init.cf"))

    if "elaborate" in module_name:
        assert os.path.exists(os.path.join(extract_dir, "inmanta_plugins", module_name, "files", "test.txt"))
        assert os.path.exists(os.path.join(extract_dir, "inmanta_plugins", module_name, "templates", "template.txt.j2"))
        assert os.path.exists(os.path.join(extract_dir, "inmanta_plugins", module_name, "model", "other.cf"))
        assert os.path.exists(os.path.join(extract_dir, "inmanta_plugins", module_name, "py.typed"))
        assert os.path.exists(
            os.path.join(
                extract_dir, "inmanta_plugins", module_name, "other_module.py" if not byte_code else "other_module.pyc"
            )
        )
        assert os.path.exists(
            os.path.join(
                extract_dir, "inmanta_plugins", module_name, "subpkg", "__init__.py" if not byte_code else "__init__.pyc"
            )
        )


def test_build_v2_module_set_output_directory(tmpdir, modules_v2_dir: str) -> None:
    """
    Verify that the output_dir argument of the `inmanta module build` command works correctly.
    """
    module_dir = os.path.join(modules_v2_dir, "minimalv2module")
    module_copy_dir = os.path.join(tmpdir, "module")
    shutil.copytree(module_dir, module_copy_dir)
    assert os.path.isdir(module_copy_dir)

    output_dir = os.path.join(tmpdir, "output")
    run_module_build(module_copy_dir, set_path_argument=True, output_dir=output_dir)

    assert os.path.exists(output_dir)
    assert len(os.listdir(output_dir)) == 1
    assert not os.path.exists(os.path.join(module_copy_dir, "dist"))


def test_build_v2_module_incomplete_package_data(tmpdir, modules_v2_dir: str, caplog) -> None:
    """
    Verify that a warning is shown when a data file present in module namespace package is not packaged, because
    it's not mentioned in the `options.package_data` section of the setup.cfg
    """
    module_dir = os.path.join(modules_v2_dir, "minimalv2module")
    module_copy_dir = os.path.join(tmpdir, "module")
    shutil.copytree(module_dir, module_copy_dir)
    assert os.path.isdir(module_copy_dir)

    # Rewrite the MANIFEST.in file
    manifest_file: str = os.path.join(module_copy_dir, "MANIFEST.in")
    lines: list[str]
    with open(manifest_file) as fd:
        lines = fd.read().splitlines()
    with open(manifest_file, "w") as fd:
        fd.write("\n".join(line for line in lines if "/model" not in line))

    # load the module to make sure pycache files are ignored in the warning
    source_dir: str = os.path.join(module_copy_dir, "inmanta_plugins", "minimalv2module")
    spec: ModuleSpec = importlib.util.spec_from_file_location(
        "inmanta_plugins.minimalv2module", os.path.join(source_dir, "__init__.py")
    )
    mod: ModuleType = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert os.path.isfile(
        os.path.join(
            source_dir, "__pycache__", "__init__.cpython-%s.pyc" % "".join(str(digit) for digit in sys.version_info[:2])
        )
    )

    # write some garbage .cfc and pyc files to verify those are ignored as well
    open(os.path.join(source_dir, "test.pyc"), "w").close()
    cfcache_dir: str = os.path.join(module_copy_dir, "model", "__cfcache__")
    os.makedirs(cfcache_dir, exist_ok=True)
    open(os.path.join(cfcache_dir, "test.cfc"), "w").close()
    dot_cfcache_dir: str = os.path.join(module_copy_dir, CF_CACHE_DIR)
    os.makedirs(dot_cfcache_dir, exist_ok=True)
    open(os.path.join(dot_cfcache_dir, "test2.cfc"), "w").close()

    with caplog.at_level(logging.WARNING):
        V2ModuleBuilder(module_copy_dir).build(os.path.join(module_copy_dir, "dist"))
        assert (
            "The following files are present in the inmanta_plugins/minimalv2module directory on disk, but were not "
            "packaged: ['model/_init.cf']. Update you MANIFEST.in file if they need to be packaged."
        ) in caplog.messages


def test_build_invalid_module(tmpdir, modules_v2_dir: str):
    """
    Execute a build when the setup.cfg file is missing
    """
    module_dir = os.path.join(modules_v2_dir, "minimalv2module")
    module_copy_dir = os.path.join(tmpdir, "module")
    shutil.copytree(module_dir, module_copy_dir)
    assert os.path.isdir(module_copy_dir)

    setup_cfg_file = os.path.join(module_copy_dir, "setup.cfg")
    assert os.path.exists(setup_cfg_file)
    os.remove(setup_cfg_file)

    with pytest.raises(ModuleMetadataFileNotFound, match=f"Metadata file {setup_cfg_file} does not exist"):
        V2ModuleBuilder(module_copy_dir).build(os.path.join(module_copy_dir, "dist"))


def test_build_with_existing_model_directory(tmpdir, modules_v2_dir: str):
    """
    Ensure the module build process raises a proper exception if the model directory
    already exists in inmanta_plugins/<module_name>/
    """
    module_name = "minimalv2module"
    module_dir = os.path.join(modules_v2_dir, module_name)
    module_copy_dir = os.path.join(tmpdir, "module")
    shutil.copytree(module_dir, module_copy_dir)
    assert os.path.isdir(module_copy_dir)

    # Simulate the existence of a model directory in inmanta_plugins/<module_name>/
    python_pkg_dir = os.path.join(module_copy_dir, "inmanta_plugins", module_name)
    model_dir_path = os.path.join(python_pkg_dir, "model")
    os.makedirs(model_dir_path)
    assert os.path.exists(model_dir_path)  # Ensure the model directory exists

    with pytest.raises(
        Exception,
        match="There is already a model directory in %s. "
        "The `inmanta_plugins.minimalv2module.model` package is reserved for bundling the inmanta model files. "
        "Please use a different name for this Python package." % python_pkg_dir,
    ):
        V2ModuleBuilder(module_copy_dir).build(os.path.join(module_copy_dir, "dist"))


def test_create_dev_build_of_v2_module(tmpdir, modules_v2_dir: str) -> None:
    """
    Test whether the functionality to create a development build of a module, works correctly.
    """
    module_name = "minimalv2module"
    module_dir = os.path.join(modules_v2_dir, module_name)
    module_copy_dir = os.path.join(tmpdir, module_name)
    shutil.copytree(module_dir, module_copy_dir)
    path_to_wheel = run_module_build_soft(module_copy_dir, set_path_argument=True, dev_build=True)
    assert re.search(r"\.dev[0-9]{14}", path_to_wheel)


@pytest.mark.parametrize_any("explicit", [True, False])
def test_create_dev_build_of_pre_tagged_module(tmpdir, modules_dir: str, explicit: bool) -> None:
    """
    Test whether the functionality to create a development build of a module that already has a dev tag, works correctly.
    """
    module_name = "mypretaggedmodule"
    new_mod_dir: str = str(tmpdir.join(module_name))
    # start from a v1 module with a tag
    v1_module_from_template(
        os.path.join(modules_dir, "minimalv1module"),
        new_mod_dir,
        new_name=module_name,
        new_version=version.Version("1.2.3.dev0"),
    )
    path_to_wheel = run_module_build_soft(new_mod_dir, set_path_argument=True, dev_build=explicit)
    if explicit:
        assert re.search(r"1.2.3\.dev[0-9]{14}", path_to_wheel)
    else:
        assert "1.2.3.dev0" in path_to_wheel


@pytest.mark.slowtest
@pytest.mark.parametrize_any(
    "module_name, is_empty",
    [
        ("minimalv1module", True),
        ("minimalv1module", False),
        ("elaboratev1module", True),
        ("elaboratev1module", False),
    ],
)
def test_build_v1_module_existing_plugin_dir(tmpdir, modules_dir: str, module_name, is_empty) -> None:
    """
    Verify that an exception is thrown if the inmanta_plugins/{module_name} directory already exists and is not empty
    and that the build succeeds if the directory already exists and is empty
    """
    module_dir = os.path.join(modules_dir, module_name)
    module_copy_dir = os.path.join(tmpdir, module_name)
    shutil.copytree(module_dir, module_copy_dir)

    assert os.path.isdir(module_copy_dir)

    inmanta_plugins_path = os.path.join(module_copy_dir, "inmanta_plugins")
    os.mkdir(inmanta_plugins_path)
    my_module_path = os.path.join(inmanta_plugins_path, module_name)
    os.mkdir(my_module_path)

    assert os.path.isdir(my_module_path)

    if not is_empty:
        with open(os.path.join(my_module_path, "smt.txt"), "w") as fh:
            fh.write("test")

        with pytest.raises(
            ModuleBuildFailedError,
            match=f"Could not build module: inmanta_plugins/{module_name} directory already exists and is not empty",
        ):
            moduletool.ModuleTool().build(module_copy_dir)
    else:
        moduletool.ModuleTool().build(module_copy_dir)

        dist_dir = os.path.join(module_copy_dir, "dist")
        dist_dir_content = os.listdir(dist_dir)
        assert len(dist_dir_content) == 1
        wheel_file = os.path.join(dist_dir, dist_dir_content[0])
        assert wheel_file.endswith(".whl")
        extract_dir = os.path.join(tmpdir, "extract")
        with zipfile.ZipFile(wheel_file) as z:
            z.extractall(extract_dir)

        assert not os.path.exists(os.path.join(extract_dir, "plugins"))
        assert os.path.exists(os.path.join(extract_dir, "inmanta_plugins", module_name, "setup.cfg"))
        assert os.path.exists(os.path.join(extract_dir, "inmanta_plugins", module_name, "__init__.py"))
        assert os.path.exists(os.path.join(extract_dir, "inmanta_plugins", module_name, "model", "_init.cf"))

        if "elaborate" in module_name:
            assert os.path.exists(os.path.join(extract_dir, "inmanta_plugins", module_name, "files", "test.txt"))
            assert os.path.exists(os.path.join(extract_dir, "inmanta_plugins", module_name, "templates", "template.txt.j2"))
            assert os.path.exists(os.path.join(extract_dir, "inmanta_plugins", module_name, "model", "other.cf"))
            assert os.path.exists(os.path.join(extract_dir, "inmanta_plugins", module_name, "py.typed"))
            assert os.path.exists(os.path.join(extract_dir, "inmanta_plugins", module_name, "other_module.py"))
            assert os.path.exists(os.path.join(extract_dir, "inmanta_plugins", module_name, "subpkg", "__init__.py"))
