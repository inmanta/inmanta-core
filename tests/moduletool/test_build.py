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
import configparser
import logging
import os
import shutil
import subprocess
import sys
import zipfile
from typing import Optional

import pytest

from inmanta.module import ModuleMetadataFileNotFound
from inmanta.moduletool import V2ModuleBuilder


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


@pytest.mark.parametrize(
    "module_name,set_path_argument",
    [
        ("minimalv2module", True),
        ("minimalv2module", False),
        ("elaboratev2module", True),
        ("elaboratev2module", False),
    ],
)
def test_build_v2_module(tmpdir, module_name: str, set_path_argument: bool) -> None:
    """
    Build a V2 package and verify that the required files are present in the resulting wheel.
    """
    module_dir = os.path.normpath(os.path.join(__file__, os.pardir, os.pardir, "data", "modules", module_name))
    module_copy_dir = os.path.join(tmpdir, "module")
    shutil.copytree(module_dir, module_copy_dir)
    assert os.path.isdir(module_copy_dir)

    run_module_build(module_copy_dir, set_path_argument)

    dist_dir = os.path.join(module_copy_dir, "dist")
    dist_dir_content = os.listdir(dist_dir)
    assert len(dist_dir_content) == 1
    wheel_file = os.path.join(dist_dir, dist_dir_content[0])
    assert wheel_file.endswith(".whl")

    extract_dir = os.path.join(tmpdir, "extract")
    with zipfile.ZipFile(wheel_file) as zip:
        zip.extractall(extract_dir)

    assert os.path.exists(os.path.join(extract_dir, "inmanta_plugins", module_name, "setup.cfg"))
    assert os.path.exists(os.path.join(extract_dir, "inmanta_plugins", module_name, "__init__.py"))
    assert os.path.exists(os.path.join(extract_dir, "inmanta_plugins", module_name, "model", "_init.cf"))

    if module_name == "elaboratev2module":
        assert os.path.exists(os.path.join(extract_dir, "inmanta_plugins", module_name, "files", "test.txt"))
        assert os.path.exists(os.path.join(extract_dir, "inmanta_plugins", module_name, "templates", "template.txt.j2"))
        assert os.path.exists(os.path.join(extract_dir, "inmanta_plugins", module_name, "model", "other.cf"))
        assert os.path.exists(os.path.join(extract_dir, "inmanta_plugins", module_name, "other_module.py"))
        assert os.path.exists(os.path.join(extract_dir, "inmanta_plugins", module_name, "subpkg", "__init__.py"))

    # A second invocation of the build command should raise an exception
    # because the dist directory already exists
    with pytest.raises(subprocess.CalledProcessError) as excinfo:
        run_module_build(module_copy_dir, set_path_argument)
    assert f"Non-empty output directory {dist_dir}" in excinfo.value.stdout.decode()


def test_build_v2_module_set_output_directory(tmpdir) -> None:
    """
    Verify that the output_dir argument of the `inmanta module build` command works correctly.
    """
    module_dir = os.path.normpath(os.path.join(__file__, os.pardir, os.pardir, "data", "modules", "minimalv2module"))
    module_copy_dir = os.path.join(tmpdir, "module")
    shutil.copytree(module_dir, module_copy_dir)
    assert os.path.isdir(module_copy_dir)

    output_dir = os.path.join(tmpdir, "output")
    run_module_build(module_copy_dir, set_path_argument=True, output_dir=output_dir)

    assert os.path.exists(output_dir)
    assert len(os.listdir(output_dir)) == 1
    assert not os.path.exists(os.path.join(module_copy_dir, "dist"))


def test_build_v2_module_incomplete_package_data(tmpdir, caplog) -> None:
    """
    Verify that a warning is shown when a data file present in module namespace package is not packaged, because
    it's not mentioned in the `options.package_data` section of the setup.cfg
    """
    module_dir = os.path.normpath(os.path.join(__file__, os.pardir, os.pardir, "data", "modules", "minimalv2module"))
    module_copy_dir = os.path.join(tmpdir, "module")
    shutil.copytree(module_dir, module_copy_dir)
    assert os.path.isdir(module_copy_dir)

    # Rewrite the setup.cfg file
    setup_cfg_file = os.path.join(module_copy_dir, "setup.cfg")
    config_parser = configparser.ConfigParser()
    config_parser.read(setup_cfg_file)
    config_parser.set("options.package_data", "inmanta_plugins.minimalv2module", "setup.cfg")
    with open(setup_cfg_file, "w") as fd:
        config_parser.write(fd)

    with caplog.at_level(logging.WARNING):
        V2ModuleBuilder(module_copy_dir).build()
        assert (
            "The following files are present in the inmanta_plugins/minimalv2module directory on disk, but were not "
            "packaged: ['model/_init.cf']. Update you setup.cfg file if they need to be packaged."
        ) in caplog.messages


def test_build_invalid_module(tmpdir):
    """
    Execute a build when the setup.cfg file is missing
    """
    module_dir = os.path.normpath(os.path.join(__file__, os.pardir, os.pardir, "data", "modules", "minimalv2module"))
    module_copy_dir = os.path.join(tmpdir, "module")
    shutil.copytree(module_dir, module_copy_dir)
    assert os.path.isdir(module_copy_dir)

    setup_cfg_file = os.path.join(module_copy_dir, "setup.cfg")
    assert os.path.exists(setup_cfg_file)
    os.remove(setup_cfg_file)

    with pytest.raises(ModuleMetadataFileNotFound, match=f"Metadata file {setup_cfg_file} does not exist"):
        V2ModuleBuilder(module_copy_dir).build()
