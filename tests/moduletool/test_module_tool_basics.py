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
import asyncio
import os
import re
import shutil
import subprocess
import sys
import warnings
from typing import Iterator, Type

import py
import pytest
import yaml
from pkg_resources import parse_version

from inmanta import module
from inmanta.module import (
    InmantaModuleRequirement,
    InvalidMetadata,
    InvalidModuleException,
    MetadataDeprecationWarning,
    Project,
)
from inmanta.moduletool import ModuleTool
from inmanta.parser import ParserException
from moduletool.common import add_file, commitmodule, install_project, make_module_simple, makeproject
from packaging import version
from test_app_cli import app


@pytest.fixture
def tmp_working_dir(tmpdir: py.path.local) -> Iterator[py.path.local]:
    cwd = os.getcwd()
    os.chdir(str(tmpdir))
    yield tmpdir
    os.chdir(cwd)


def test_versioning():
    mt = ModuleTool()

    newversion = mt.determine_new_version(parse_version("1.2.3"), None, False, False, True, False)
    assert str(newversion) == "1.2.4"
    newversion = mt.determine_new_version(parse_version("1.2.3"), None, False, True, False, False)
    assert str(newversion) == "1.3.0"
    newversion = mt.determine_new_version(parse_version("1.2.3"), None, True, False, False, False)
    assert str(newversion) == "2.0.0"
    newversion = mt.determine_new_version(parse_version("1.2.3"), None, True, True, False, False)
    assert newversion is None
    newversion = mt.determine_new_version(parse_version("1.2.3"), None, True, False, True, False)
    assert newversion is None
    newversion = mt.determine_new_version(parse_version("1.2.3"), None, True, True, True, False)
    assert newversion is None
    newversion = mt.determine_new_version(parse_version("1.2.3.dev025"), None, False, False, True, False)
    assert str(newversion) == "1.2.3"
    newversion = mt.determine_new_version(parse_version("1.2.3.dev025"), None, False, False, False, False)
    assert str(newversion) == "1.2.3"

    newversion = mt.determine_new_version(parse_version("1.2.3"), None, False, False, True, True)
    assert re.search("1.2.4.dev[0-9]+", str(newversion))
    newversion = mt.determine_new_version(parse_version("1.2.3"), None, False, True, False, True)
    assert re.search("1.3.0.dev[0-9]+", str(newversion))
    newversion = mt.determine_new_version(parse_version("1.2.3"), None, True, False, False, True)
    assert re.search("2.0.0.dev[0-9]+", str(newversion))
    newversion = mt.determine_new_version(parse_version("1.2.3"), None, True, True, False, True)
    assert newversion is None
    newversion = mt.determine_new_version(parse_version("1.2.3"), None, True, False, True, True)
    assert newversion is None
    newversion = mt.determine_new_version(parse_version("1.2.3"), None, True, True, True, True)
    assert newversion is None
    newversion = mt.determine_new_version(parse_version("1.2.3.dev025"), None, False, False, True, True)
    assert re.search("1.2.3.dev[0-9]+", str(newversion))
    newversion = mt.determine_new_version(parse_version("1.2.3.dev025"), None, False, False, False, True)
    assert re.search("1.2.3.dev[0-9]+", str(newversion))


def test_get_module_v1(tmp_working_dir: py.path.local):
    metadata_file: str = tmp_working_dir.join("module.yml")
    metadata_file.write(
        """
name: mod
license: ASL
version: 1.2.3
compiler_version: 2017.2
        """.strip()
    )

    mt = ModuleTool()
    mod: module.Module = mt.get_module()
    assert mod.GENERATION == module.ModuleGeneration.V1


def test_get_module_v2(tmp_working_dir: py.path.local):
    metadata_file: str = tmp_working_dir.join("setup.cfg")
    metadata_file.write(
        """
[metadata]
name = inmanta-module-mod
version = 1.2.3
license = ASL

[options]
install_requires =
  inmanta-modules-net ~=0.2.4
  inmanta-modules-std >1.0,<2.5

  cookiecutter~=1.7.0
  cryptography>1.0,<3.5
        """.strip()
    )
    model_dir: py.path.local = tmp_working_dir.join("model")
    os.makedirs(str(model_dir))
    open(str(model_dir.join("_init.cf")), "w").close()

    mt = ModuleTool()
    mod: module.Module = mt.get_module()
    assert mod.GENERATION == module.ModuleGeneration.V2


def test_get_module_metadata_file_not_found(tmp_working_dir: py.path.local):
    mt = ModuleTool()
    with pytest.raises(module.InvalidModuleException, match="No module can be found at "):
        mt.get_module()


@pytest.mark.parametrize("module_type", [module.ModuleV1, module.ModuleV2])
def test_rewrite(tmpdir, module_type: Type[module.Module]):
    v1: bool = module_type.GENERATION == module.ModuleGeneration.V1
    module_path = tmpdir.join("mod").mkdir()
    model = module_path.join("model").mkdir()
    model.join("_init.cf").write("\n")

    metadata_file: str = module_path.join("module.yml" if v1 else "setup.cfg")

    def metadata_contents(version: str) -> str:
        if v1:
            return f"""
name: mod
license: ASL
version: {version}
compiler_version: 2017.2
            """.strip()
        else:
            return f"""
[metadata]
name = inmanta-module-mod
version = {version}
license = ASL

[options]
install_requires =
  inmanta-modules-net ~=0.2.4
  inmanta-modules-std >1.0,<2.5

  cookiecutter~=1.7.0
  cryptography>1.0,<3.5
            """.strip()

    metadata_file.write(metadata_contents("1.2"))
    mod = module_type(None, module_path.strpath)

    assert mod.version == version.Version("1.2")
    if v1:
        assert mod.compiler_version == "2017.2"

    mod.rewrite_version("1.3.1")
    assert mod.version == version.Version("1.3.1")
    if v1:
        assert mod.compiler_version == "2017.2"
    assert metadata_file.read().strip() == metadata_contents("1.3.1")


def test_module_corruption(git_modules_dir, modules_repo):
    mod9 = make_module_simple(modules_repo, "mod9", [("mod10", None)])
    add_file(mod9, "signal", "present", "third commit", version="3.3")
    add_file(mod9, "model/b.cf", "import mod9", "fourth commit", version="4.0")

    mod10 = make_module_simple(modules_repo, "mod10", [])
    add_file(mod10, "signal", "present", "a commit", version="3.3")
    # syntax error
    add_file(mod10, "model/_init.cf", "SomeInvalidThings", "a commit", version="3.5")
    # fix it
    add_file(mod10, "model/_init.cf", "", "a commit", version="3.6")
    add_file(mod10, "secondsignal", "import mod9", "b commit", version="4.0")
    add_file(mod10, "badsignal", "import mod9", "c commit", version="5.0")

    p9 = makeproject(modules_repo, "proj9", [("mod9", "==3.3"), ("mod10", "==3.3")], ["mod9"])
    commitmodule(p9, "first commit")

    # setup project
    proj = install_project(git_modules_dir, "proj9")
    app(["project", "install"])
    print(os.listdir(proj))

    # unfreeze deps to allow update
    projectyml = os.path.join(proj, "project.yml")
    assert os.path.exists(projectyml)

    with open(projectyml, "r", encoding="utf-8") as fh:
        pyml = yaml.safe_load(fh)

    pyml["requires"] = ["mod10 == 3.5"]

    with open(projectyml, "w", encoding="utf-8") as fh:
        yaml.dump(pyml, fh)

    # clear cache
    Project._project = None

    with pytest.raises(ParserException):
        # mod 10 is updated to a version that contains a syntax error
        app(["modules", "update"])

    # unfreeze deps to allow update
    pyml["requires"] = ["mod10 == 4.0"]

    with open(projectyml, "w", encoding="utf-8") as fh:
        yaml.dump(pyml, fh)

    # overwrite main to import unknown sub module
    main = os.path.join(proj, "main.cf")
    assert os.path.exists(main)

    with open(main, "w", encoding="utf-8") as fh:
        fh.write("import mod9::b")

    # clear cache
    Project._project = None

    # attempt to update
    app(["modules", "update"])

    # Additional output
    Project._project = None
    app(["modules", "list"])

    # Verify
    m9dir = os.path.join(proj, "libs", "mod9")
    assert os.path.exists(os.path.join(m9dir, "model", "b.cf"))
    m10dir = os.path.join(proj, "libs", "mod10")
    assert os.path.exists(os.path.join(m10dir, "secondsignal"))
    # should not be lastest version
    assert not os.path.exists(os.path.join(m10dir, "badsignal"))


@pytest.fixture(scope="function")
def module_without_tags(modules_repo):
    mod_no_tag = make_module_simple(modules_repo, "mod-no-tag")
    yield mod_no_tag
    shutil.rmtree(mod_no_tag)


@pytest.mark.parametrize(
    "dev, tag, version_tag_in_output",
    [(True, True, True), (True, False, False), (False, True, True), (False, False, True)],
)
def test_commit_no_tags(git_modules_dir, module_without_tags, dev, tag, version_tag_in_output):
    add_file(module_without_tags, "dummyfile", "Content", "Commit without tags", version="5.0", dev=dev, tag=tag)
    output = subprocess.check_output(["git", "tag", "-l"], cwd=module_without_tags, stderr=subprocess.STDOUT)
    assert ("5.0" in str(output)) is version_tag_in_output


@pytest.mark.asyncio
async def test_version_argument(modules_repo):
    make_module_simple(modules_repo, "mod-version", [], "1.2")
    module_path = os.path.join(modules_repo, "mod-version")

    mod = module.ModuleV1(None, module_path)
    assert mod.version == version.Version("1.2")

    args = [sys.executable, "-m", "inmanta.app", "module", "commit", "-m", "msg", "-v", "1.3.1", "-r"]
    process = await asyncio.subprocess.create_subprocess_exec(
        *args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=module_path
    )
    try:
        await asyncio.wait_for(process.communicate(), timeout=30)
    except asyncio.TimeoutError as e:
        process.kill()
        await process.communicate()
        raise e

    # Make sure exitcode is zero
    assert process.returncode == 0

    # Verify changes
    assert mod._get_metadata_from_disk().version == "1.3.1"


class InmantaModule:
    def __init__(self, module_dir: py.path.local, metadata_file: str) -> None:
        self._module_path = module_dir.join("mod").mkdir()
        model = self._module_path.join("model").mkdir()
        model.join("_init.cf").write("\n")
        self._metadata_file = self._module_path.join(metadata_file)

    def write_metadata_file(self, content: str) -> None:
        self._metadata_file.write(content)

    def get_root_dir_of_module(self) -> str:
        return self._module_path.strpath

    def get_metadata_file_path(self) -> str:
        return self._metadata_file.strpath


@pytest.fixture
def inmanta_module_v1(tmpdir):
    yield InmantaModule(tmpdir, "module.yml")


@pytest.fixture
def inmanta_module_v2(tmpdir):
    yield InmantaModule(tmpdir, "setup.cfg")


def test_module_version_non_pep440_complient(inmanta_module_v1):
    inmanta_module_v1.write_metadata_file(
        """
name: mod
license: ASL
version: non_pep440_value
compiler_version: 2017.2
    """
    )
    with pytest.raises(InvalidModuleException) as e:
        module.ModuleV1(None, inmanta_module_v1.get_root_dir_of_module())

    cause = e.value.__cause__
    assert isinstance(cause, InvalidMetadata)
    assert "Version non_pep440_value is not PEP440 compliant" in cause.msg


def test_invalid_yaml_syntax_in_module_yml(inmanta_module_v1):
    inmanta_module_v1.write_metadata_file(
        """
test:
 - first
 second
"""
    )
    with pytest.raises(InvalidModuleException) as e:
        module.ModuleV1(None, inmanta_module_v1.get_root_dir_of_module())

    cause = e.value.__cause__
    assert isinstance(cause, InvalidMetadata)
    assert f"Invalid yaml syntax in {inmanta_module_v1.get_metadata_file_path()}" in cause.msg


def test_module_requires(inmanta_module_v1):
    inmanta_module_v1.write_metadata_file(
        """
name: mod
license: ASL
version: 1.0.0
requires:
    - std
    - ip > 1.0.0
        """
    )
    mod: module.Module = module.ModuleV1(None, inmanta_module_v1.get_root_dir_of_module())
    assert mod.requires() == [InmantaModuleRequirement.parse("std"), InmantaModuleRequirement.parse("ip > 1.0.0")]


def test_module_requires_single(inmanta_module_v1):
    inmanta_module_v1.write_metadata_file(
        """
name: mod
license: ASL
version: 1.0.0
requires: std > 1.0.0
        """
    )
    mod: module.Module = module.ModuleV1(None, inmanta_module_v1.get_root_dir_of_module())
    assert mod.requires() == [InmantaModuleRequirement.parse("std > 1.0.0")]


def test_module_requires_legacy(inmanta_module_v1):
    inmanta_module_v1.write_metadata_file(
        """
name: mod
license: ASL
version: 1.0.0
requires:
    std: std
    ip: ip > 1.0.0
        """
    )
    mod: module.Module
    with warnings.catch_warnings(record=True) as w:
        mod = module.ModuleV1(None, inmanta_module_v1.get_root_dir_of_module())
        assert len(w) == 1
        warning = w[0]
        assert issubclass(warning.category, MetadataDeprecationWarning)
        assert "yaml dictionary syntax for specifying module requirements has been deprecated" in str(warning.message)
    assert mod.requires() == [InmantaModuleRequirement.parse("std"), InmantaModuleRequirement.parse("ip > 1.0.0")]


def test_module_requires_legacy_invalid(inmanta_module_v1):
    inmanta_module_v1.write_metadata_file(
        """
name: mod
license: ASL
version: 1.0.0
requires:
    std: ip
        """
    )
    with pytest.raises(InvalidModuleException) as e:
        module.ModuleV1(None, inmanta_module_v1.get_root_dir_of_module())

    cause = e.value.__cause__
    assert isinstance(cause, InvalidMetadata)
    assert "Invalid legacy requires" in cause.msg


def test_module_v2_metadata(inmanta_module_v2: InmantaModule) -> None:
    inmanta_module_v2.write_metadata_file(
        """
[metadata]
name = inmanta-module-mod1
version = 1.2.3
license = Apache 2.0

[options]
install_requires =
  inmanta-modules-net ~=0.2.4
  inmanta-modules-std >1.0,<2.5

  cookiecutter~=1.7.0
  cryptography>1.0,<3.5
        """
    )
    mod: module.ModuleV2 = module.ModuleV2(None, inmanta_module_v2.get_root_dir_of_module())
    assert mod.metadata.name == "inmanta-module-mod1"
    assert mod.metadata.version == "1.2.3"
    assert mod.metadata.license == "Apache 2.0"


@pytest.mark.parametrize("underscore", [True, False])
def test_module_v2_name_underscore(inmanta_module_v2: InmantaModule, underscore: bool):
    """
    Test module v2 metadata parsing with respect to module naming rules about dashes and underscores.
    """
    separator: str = "_" if underscore else "-"
    inmanta_module_v2.write_metadata_file(
        f"""
[metadata]
name = inmanta-module-my{separator}mod
version = 1.2.3
license = Apache 2.0

[options]
install_requires =
  inmanta-modules-net ~=0.2.4
  inmanta-modules-std >1.0,<2.5

  cookiecutter~=1.7.0
  cryptography>1.0,<3.5
packages = find_namespace:
        """
    )
    if underscore:
        with pytest.raises(InvalidModuleException):
            module.ModuleV2(None, inmanta_module_v2.get_root_dir_of_module())
    else:
        module.ModuleV2(None, inmanta_module_v2.get_root_dir_of_module())
