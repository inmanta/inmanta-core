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
import os
import shutil

import pytest
from pytest import MonkeyPatch

from inmanta import moduletool
from inmanta.module import DummyProject, ModuleV1, ModuleV2Metadata
from inmanta.moduletool import ModuleConverter, ModuleVersionException


def test_module_conversion(tmpdir):
    module_name = "elaboratev1module"
    path = os.path.normpath(os.path.join(__file__, os.pardir, os.pardir, "data", "modules", module_name))
    dummyproject = DummyProject()
    module_in = ModuleV1(dummyproject, path)

    assert sorted([str(r) for r in module_in.get_all_requires()]) == ["mod1==1.0", "mod2", "std"]

    ModuleConverter(module_in).convert(tmpdir)

    assert_v2_module(module_name, tmpdir)


def test_module_conversion_in_place(tmpdir):
    module_name = "elaboratev1module"
    tmpdir = os.path.join(tmpdir, module_name)
    path = os.path.normpath(os.path.join(__file__, os.pardir, os.pardir, "data", "modules", module_name))
    shutil.copytree(path, tmpdir)
    dummyproject = DummyProject()
    module_in = ModuleV1(dummyproject, tmpdir)
    ModuleConverter(module_in).convert_in_place()
    assert_v2_module(module_name, tmpdir)


def test_module_conversion_in_place_minimal(tmpdir):
    module_name = "minimalv1module"
    tmpdir = os.path.join(tmpdir, module_name)
    path = os.path.normpath(os.path.join(__file__, os.pardir, os.pardir, "data", "modules", module_name))
    shutil.copytree(path, tmpdir)
    dummyproject = DummyProject()
    module_in = ModuleV1(dummyproject, tmpdir)
    ModuleConverter(module_in).convert_in_place()
    assert_v2_module(module_name, tmpdir, minimal=True)


def test_module_conversion_in_place_cli(tmpdir, monkeypatch: MonkeyPatch):
    module_name = "elaboratev1module"
    tmpdir = os.path.join(tmpdir, module_name)
    path = os.path.normpath(os.path.join(__file__, os.pardir, os.pardir, "data", "modules", module_name))
    shutil.copytree(path, tmpdir)
    monkeypatch.chdir(tmpdir)
    moduletool.ModuleTool().v1tov2(None)
    assert_v2_module(module_name, tmpdir)

    with pytest.raises(ModuleVersionException):
        moduletool.ModuleTool().v1tov2(None)


def assert_v2_module(module_name, tmpdir, minimal=False):
    assert os.path.exists(os.path.join(tmpdir, "setup.cfg"))
    assert os.path.exists(os.path.join(tmpdir, "pyproject.toml"))

    assert not os.path.exists(os.path.join(tmpdir, "requirements.txt"))
    assert not os.path.exists(os.path.join(tmpdir, "module.yml"))

    assert os.path.exists(os.path.join(tmpdir, "model", "_init.cf"))
    assert os.path.exists(os.path.join(tmpdir, "inmanta_plugins", module_name, "__init__.py"))

    if not minimal:
        assert os.path.exists(os.path.join(tmpdir, "files", "test.txt"))
        assert os.path.exists(os.path.join(tmpdir, "templates", "template.txt.j2"))
        assert os.path.exists(os.path.join(tmpdir, "model", "other.cf"))
        assert os.path.exists(os.path.join(tmpdir, "inmanta_plugins", module_name, "other_module.py"))
        assert os.path.exists(os.path.join(tmpdir, "inmanta_plugins", module_name, "subpkg", "__init__.py"))

    with open(os.path.join(tmpdir, "setup.cfg"), "r") as fh:
        content = fh.read()
        meta = ModuleV2Metadata.parse(content)
        assert meta.name == "inmanta-module-" + module_name
        assert meta.version == "1.2"

        raw_content = configparser.ConfigParser()
        raw_content.read_string(content)
        # Don't emit None values
        assert "None" not in content
        if not minimal:
            assert (
                raw_content["options"]["install_requires"].strip()
                == """inmanta-module-mod1==1.0
inmanta-module-mod2
inmanta-module-std
jinja2"""
            )
        else:
            assert raw_content["options"]["install_requires"].strip() == """inmanta-module-std"""
