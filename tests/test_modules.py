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
import unittest
from unittest import mock

import pytest

from _io import StringIO
from inmanta import module


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
