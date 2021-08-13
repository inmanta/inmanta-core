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

import logging
import os
import shutil
import unittest
from typing import List
from unittest import mock

import pytest

from _io import StringIO
from inmanta import module
from inmanta.env import LocalPackagePath


def test_module():
    good_mod_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "modules", "mod1")
    module.ModuleV1(project=mock.Mock(), path=good_mod_dir)


def test_bad_module():
    bad_mod_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "modules", "mod2")
    with pytest.raises(module.ModuleMetadataFileNotFound):
        module.ModuleV1(project=mock.Mock(), path=bad_mod_dir)


class TestModuleName(unittest.TestCase):
    def __init__(self, methodName="runTest"):  # noqa: N803
        unittest.TestCase.__init__(self, methodName)

        self.stream = None
        self.handler = None
        self.log = None

    def setUp(self):
        self.stream = StringIO()
        self.handler = logging.StreamHandler(self.stream)
        self.log = logging.getLogger(module.__name__)

        for handler in self.log.handlers:
            self.log.removeHandler(handler)

        self.log.addHandler(self.handler)

    def test_wrong_name(self):
        mod_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "modules", "mod3")
        module.ModuleV1(project=mock.Mock(), path=mod_dir)

        self.handler.flush()
        assert "The name in the module file (mod1) does not match the directory name (mod3)" in self.stream.getvalue().strip()

    def tearDown(self):
        self.log.removeHandler(self.handler)
        self.handler.close()


def test_to_v2():
    """
    Test whether the `to_v2()` method of `ModuleV1Metadata` works correctly.
    """
    v1_metadata = module.ModuleV1Metadata(
        name="test",
        description="A description",
        version="1.2.3",
        license="Apache 2.0",
        compiler_version="4.5.6",
        requires=["mod1", "mod2"],
    )
    v2_metadata = v1_metadata.to_v2()
    for attr_name in ["description", "version", "license"]:
        assert v1_metadata.__getattribute__(attr_name) == v2_metadata.__getattribute__(attr_name)
    assert f"{module.ModuleV2.PKG_NAME_PREFIX}{v1_metadata.name}" == v2_metadata.name
    assert [f"{module.ModuleV2.PKG_NAME_PREFIX}{req}" for req in v1_metadata.requires] == v2_metadata.install_requires


def test_is_versioned(snippetcompiler_clean, modules_dir: str, modules_v2_dir: str, caplog, tmpdir) -> None:
    """
    Test whether the warning regarding non-versioned modules is given correctly.
    """
    # Disable modules_dir
    snippetcompiler_clean.modules_dir = None

    def compile_and_assert_warning(
        module_name: str, needs_versioning_warning: bool, install_v2_modules: List[LocalPackagePath] = []
    ) -> None:
        snippetcompiler_clean.setup_for_snippet(f"import {module_name}", autostd=False, install_v2_modules=install_v2_modules)
        caplog.clear()
        snippetcompiler_clean.do_export()
        warning_message = f"Module {module_name} is not version controlled, we recommend you do this as soon as possible."
        assert (warning_message in caplog.text) is needs_versioning_warning

    # V1 module
    module_name_v1 = "mod1"
    module_dir = os.path.join(modules_dir, module_name_v1)
    module_copy_dir = os.path.join(snippetcompiler_clean.libs, module_name_v1)
    shutil.copytree(module_dir, module_copy_dir)
    dot_git_dir = os.path.join(module_copy_dir, ".git")
    assert not os.path.exists(dot_git_dir)
    compile_and_assert_warning(module_name_v1, needs_versioning_warning=True)
    os.mkdir(dot_git_dir)
    compile_and_assert_warning(module_name_v1, needs_versioning_warning=False)

    # V2 module
    module_name_v2 = "elaboratev2module"
    module_dir = os.path.join(modules_v2_dir, module_name_v2)
    module_copy_dir = os.path.join(tmpdir, module_name_v2)
    shutil.copytree(module_dir, module_copy_dir)
    dot_git_dir = os.path.join(module_copy_dir, ".git")
    assert not os.path.exists(dot_git_dir)
    # Non-editable install can never be checked for versioning
    compile_and_assert_warning(
        module_name_v2,
        needs_versioning_warning=False,
        install_v2_modules=[LocalPackagePath(path=module_copy_dir, editable=False)],
    )
    compile_and_assert_warning(
        module_name_v2,
        needs_versioning_warning=True,
        install_v2_modules=[LocalPackagePath(path=module_copy_dir, editable=True)],
    )
    os.mkdir(dot_git_dir)
    # Non-editable install can never be checked for versioning
    compile_and_assert_warning(
        module_name_v2,
        needs_versioning_warning=False,
        install_v2_modules=[LocalPackagePath(path=module_copy_dir, editable=False)],
    )
    compile_and_assert_warning(
        module_name_v2,
        needs_versioning_warning=False,
        install_v2_modules=[LocalPackagePath(path=module_copy_dir, editable=True)],
    )
