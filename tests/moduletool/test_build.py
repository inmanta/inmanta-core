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
import shutil
import os
import sys
import pytest
import subprocess
import zipfile


@pytest.mark.parametrize("set_module_path", [True, False])
def test_build_v2_module(tmpdir, monkeypatch, set_module_path: bool) -> None:
    module_dir = os.path.normpath(os.path.join(__file__, os.pardir, "data", "modules", "v2module"))
    module_copy_dir = os.path.join(tmpdir, "module")
    shutil.copytree(module_dir, module_copy_dir)
    assert os.path.isdir(module_copy_dir)

    if set_module_path:
        cmd = [sys.executable, "-m", "inmanta.app", "module", "build", "--module-path", module_copy_dir]
    else:
        monkeypatch.chdir(module_copy_dir)
        cmd = [sys.executable, "-m", "inmanta.app", "module", "build"]

    subprocess.check_call(cmd)

    dist_dir = os.path.join(module_copy_dir, "dist")
    dist_dir_content = os.listdir(dist_dir)
    assert len(dist_dir) == 1
    wheel_file = dist_dir_content[0]
    assert wheel_file.endswith(".whl")

    extract_dir = os.path.join(tmpdir, "extract")
    with zipfile.ZipFile(wheel_file) as zip:
        zip.extractall(extract_dir)

    assert os.path.exists(os.path.join(extract_dir, "inmanta_plugins", "v2module", "setup.cfg"))
    assert os.path.exists(os.path.join(extract_dir, "inmanta_plugins", "v2module", "__init__.py"))
    assert os.path.exists(os.path.join(extract_dir, "inmanta_plugins", "v2module", "model", "_init.cf"))
    assert os.path.exists(os.path.join(extract_dir, "inmanta_plugins", "v2module", "files", "test.txt"))
    assert os.path.exists(os.path.join(extract_dir, "inmanta_plugins", "v2module", "templates", "template.txt.j2"))

