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

from _io import StringIO
import os
import logging
import unittest
from unittest import mock

from inmanta import module
import pytest


def test_module():
    good_mod_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "modules", "mod1")
    module.Module(project=mock.Mock(), path=good_mod_dir)


def test_bad_module():
    bad_mod_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "modules", "mod2")
    with pytest.raises(module.InvalidModuleException):
        module.Module(project=mock.Mock(), path=bad_mod_dir)


class TestModuleName(unittest.TestCase):
    def __init__(self, methodName='runTest'):  # noqa: H803
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
        module.Module(project=mock.Mock(), path=mod_dir)

        self.handler.flush()
        assert("The name in the module file (mod1) does not match the directory name (mod3)" in self.stream.getvalue().strip())

    def tearDown(self):
        self.log.removeHandler(self.handler)
        self.handler.close()
