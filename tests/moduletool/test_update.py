"""
    Copyright 2017 Inmanta

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
import os

import pytest

from inmanta.config import Config
from inmanta.moduletool import ModuleTool
from moduletool.common import add_file, clone_repo


@pytest.mark.parametrize_any(
    "kwargs_update_method, mod2_should_be_updated, mod8_should_be_updated",
    [({}, True, True), ({"module": "mod2"}, True, False), ({"module": "mod8"}, False, True)],
)
def test_module_update_with_install_mode_master(
    tmpdir, modules_dir, modules_repo, kwargs_update_method, mod2_should_be_updated, mod8_should_be_updated
):
    # Make a copy of masterproject_multi_mod
    masterproject_multi_mod = tmpdir.join("masterproject_multi_mod")
    clone_repo(modules_repo, "masterproject_multi_mod", tmpdir)
    libs_folder = os.path.join(masterproject_multi_mod, "libs")
    os.mkdir(libs_folder)

    # Set masterproject_multi_mod as current project
    os.chdir(masterproject_multi_mod)
    Config.load_config()

    # Dependencies masterproject_multi_mod
    for mod in ["mod2", "mod8"]:
        # Clone mod in root tmpdir
        clone_repo(modules_repo, mod, tmpdir)

        # Clone mod from root of tmpdir into libs folder of masterproject_multi_mod
        clone_repo(tmpdir, mod, libs_folder)

        # Update module in root of tmpdir by adding an extra file
        file_name_extra_file = "test_file"
        path_mod = os.path.join(tmpdir, mod)
        add_file(path_mod, file_name_extra_file, "test", "Second commit")

        # Assert test_file not present in libs folder of masterproject_multi_mod
        path_extra_file = os.path.join(libs_folder, mod, file_name_extra_file)
        assert not os.path.exists(path_extra_file)

    # Update module(s) of masterproject_multi_mod
    ModuleTool().update(**kwargs_update_method)

    # Assert availability of test_file in masterproject_multi_mod
    extra_file_mod2 = os.path.join(libs_folder, "mod2", file_name_extra_file)
    assert os.path.exists(extra_file_mod2) == mod2_should_be_updated
    extra_file_mod8 = os.path.join(libs_folder, "mod8", file_name_extra_file)
    assert os.path.exists(extra_file_mod8) == mod8_should_be_updated
