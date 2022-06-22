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

import pytest
from pkg_resources import Requirement
from pytest import MonkeyPatch

import toml
from inmanta import moduletool
from inmanta.module import DummyProject, ModuleV1, ModuleV2Metadata
from inmanta.moduletool import ModuleConverter, ModuleVersionException
from utils import log_contains


def test_module_conversion(tmpdir, caplog):
    caplog.at_level(level=logging.INFO)
    module_name = "elaboratev1module"
    path = os.path.normpath(os.path.join(__file__, os.pardir, os.pardir, "data", "modules", module_name))
    dummyproject = DummyProject()
    module_in = ModuleV1(dummyproject, path)

    assert sorted([str(r) for r in module_in.get_all_requires()]) == ["mod1==1.0", "mod2", "std"]

    ModuleConverter(module_in).convert(tmpdir)

    assert_v2_module(module_name, tmpdir)
    log_contains(
        caplog,
        "inmanta.moduletool",
        logging.INFO,
        "pyproject.toml file already exists, merging. This will remove all comments from the file",
    )
    log_contains(
        caplog,
        "inmanta.moduletool",
        logging.INFO,
        "setup.cfg file already exists, merging. This will remove all comments from the file",
    )


def test_module_conversion_in_place(tmpdir, caplog):
    caplog.at_level(level=logging.INFO)
    module_name = "elaboratev1module"
    tmpdir = os.path.join(tmpdir, module_name)
    path = os.path.normpath(os.path.join(__file__, os.pardir, os.pardir, "data", "modules", module_name))
    shutil.copytree(path, tmpdir)
    dummyproject = DummyProject()
    module_in = ModuleV1(dummyproject, tmpdir)
    ModuleConverter(module_in).convert_in_place()
    assert_v2_module(module_name, tmpdir)
    log_contains(
        caplog,
        "inmanta.moduletool",
        logging.WARNING,
        "pyproject.toml file already exists, merging. This will remove all comments from the file",
    )
    log_contains(
        caplog,
        "inmanta.moduletool",
        logging.WARNING,
        "setup.cfg file already exists, merging. This will remove all comments from the file",
    )


def test_module_conversion_in_place_minimal(tmpdir):
    module_name = "minimalv1module"
    tmpdir = os.path.join(tmpdir, module_name)
    path = os.path.normpath(os.path.join(__file__, os.pardir, os.pardir, "data", "modules", module_name))
    shutil.copytree(path, tmpdir)
    dummyproject = DummyProject()
    module_in = ModuleV1(dummyproject, tmpdir)
    ModuleConverter(module_in).convert_in_place()
    assert_v2_module(module_name, tmpdir, minimal=True)


def test_issue_3159_conversion_std_module_add_self_to_dependencies(tmpdir):
    """
    Ensure that the conversion of the std module from a V1 to a V2 module,
    doesn't include the std module as a requirement in the setup.cfg file.
    """
    clone_dir = os.path.join(tmpdir, "std")
    v2_dir = os.path.join(tmpdir, "std_v2")
    subprocess.check_call(["git", "clone", "https://github.com/inmanta/std.git", clone_dir])
    dummyproject = DummyProject()
    module_in = ModuleV1(dummyproject, clone_dir)
    ModuleConverter(module_in).convert(v2_dir)

    setup_cfg_file = os.path.join(v2_dir, "setup.cfg")
    parser = configparser.ConfigParser()
    parser.read(setup_cfg_file)
    assert parser.has_option("options", "install_requires")
    install_requires = [Requirement.parse(r) for r in parser.get("options", "install_requires").split("\n") if r]
    pkg_names = [r.name for r in install_requires]
    assert "inmanta-module-std" not in pkg_names


def test_module_conversion_in_place_cli(tmpdir, monkeypatch: MonkeyPatch):
    module_name = "elaboratev1module"
    tmpdir = os.path.join(tmpdir, module_name)
    path = os.path.normpath(os.path.join(__file__, os.pardir, os.pardir, "data", "modules", module_name))
    shutil.copytree(path, tmpdir)
    monkeypatch.chdir(tmpdir)
    moduletool.ModuleTool().v1tov2(None)
    assert_v2_module(module_name, tmpdir)

    setup_cfg_file = os.path.join(tmpdir, "setup.cfg")
    parser = configparser.ConfigParser()
    parser.read(setup_cfg_file)
    assert parser.has_option("options.packages.find", "include")

    with pytest.raises(ModuleVersionException):
        moduletool.ModuleTool().v1tov2(None)


def assert_v2_module(module_name, tmpdir, minimal=False):
    assert os.path.exists(os.path.join(tmpdir, "setup.cfg"))
    assert os.path.exists(os.path.join(tmpdir, "pyproject.toml"))
    assert os.path.exists(os.path.join(tmpdir, "MANIFEST.in"))

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

        with open(os.path.join(tmpdir, "pyproject.toml"), "r") as fht:
            contentt = toml.load(fht)

            assert set(contentt["build-system"]["requires"]) == {"jinja2", "setuptools", "wheel"}, contentt
            assert contentt["build-system"]["build-backend"] == "setuptools.build_meta"
            assert contentt["tool"]["black"]["line-length"] == 128

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
            assert raw_content["isort"]["multi_line_output"].strip() == "3"
        else:
            assert raw_content["options"]["install_requires"].strip() == """inmanta-module-std"""

    with open(os.path.join(tmpdir, "MANIFEST.in"), "r") as fh:
        assert (
            fh.read().strip()
            == f"""
include inmanta_plugins/{module_name}/setup.cfg
recursive-include inmanta_plugins/{module_name}/model *.cf
graft inmanta_plugins/{module_name}/files
graft inmanta_plugins/{module_name}/templates
        """.strip()
        )
