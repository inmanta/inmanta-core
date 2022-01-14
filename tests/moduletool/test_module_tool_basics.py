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
import logging
import os
import re
import shutil
import subprocess
import sys
import warnings

import pytest
import yaml
from pkg_resources import Requirement, parse_version

from inmanta import compiler, module
from inmanta.module import InvalidMetadata, MetadataDeprecationWarning, Project
from inmanta.moduletool import ModuleTool
from inmanta.parser import ParserException
from moduletool.common import add_file, commitmodule, install_project, make_module_simple, makeproject
from test_app_cli import app
from utils import log_contains, no_error_in_logs


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


def test_rewrite(tmpdir):
    module_path = tmpdir.join("mod").mkdir()
    model = module_path.join("model").mkdir()
    model.join("_init.cf").write("\n")

    module_yml = module_path.join("module.yml")
    module_yml.write(
        """
name: mod
license: ASL
version: 1.2
compiler_version: 2017.2
    """
    )

    mod = module.Module(None, module_path.strpath)

    assert mod.version == "1.2"
    assert mod.compiler_version == "2017.2"

    mod.rewrite_version("1.3.1")
    assert mod.version == "1.3.1"
    assert mod.compiler_version == "2017.2"


def test_module_corruption(modules_dir, modules_repo):
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
    proj = install_project(modules_dir, "proj9")
    app(["modules", "install"])
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

    # attempt to update, mod10 is wrong, but only after the update
    app(["modules", "update"])

    with pytest.raises(ParserException):
        # clear cache
        Project._project = None
        # attempt to update, mod10 is wrong, can not be fixed
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
def test_commit_no_tags(modules_dir, module_without_tags, dev, tag, version_tag_in_output):
    add_file(module_without_tags, "dummyfile", "Content", "Commit without tags", version="5.0", dev=dev, tag=tag)
    output = subprocess.check_output(["git", "tag", "-l"], cwd=module_without_tags, stderr=subprocess.STDOUT)
    assert ("5.0" in str(output)) is version_tag_in_output


@pytest.mark.asyncio
async def test_version_argument(modules_repo):
    make_module_simple(modules_repo, "mod-version", [], "1.2")
    module_path = os.path.join(modules_repo, "mod-version")

    mod = module.Module(None, module_path)
    assert mod.version == "1.2"

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


@pytest.fixture
def inmanta_module(tmpdir):
    class InmantaModule:
        def __init__(self) -> None:
            self._module_path = tmpdir.join("mod").mkdir()
            model = self._module_path.join("model").mkdir()
            model.join("_init.cf").write("\n")
            self._module_yml = self._module_path.join("module.yml")

        def write_module_yml_file(self, content: str) -> None:
            self._module_yml.write(content)

        def get_root_dir_of_module(self) -> str:
            return self._module_path.strpath

        def get_path_module_yml_file(self) -> str:
            return self._module_yml.strpath

    yield InmantaModule()


@pytest.mark.asyncio
async def test_module_version_non_pep440_complient(inmanta_module):
    inmanta_module.write_module_yml_file(
        """
name: mod
license: ASL
version: non_pep440_value
compiler_version: 2017.2
    """
    )
    with pytest.raises(InvalidMetadata, match="Version non_pep440_value is not PEP440 compliant"):
        module.Module(None, inmanta_module.get_root_dir_of_module())


@pytest.mark.asyncio
async def test_invalid_yaml_syntax_in_module_yml(inmanta_module):
    inmanta_module.write_module_yml_file(
        """
test:
 - first
 second
"""
    )
    with pytest.raises(InvalidMetadata, match=f"Invalid yaml syntax in {inmanta_module.get_path_module_yml_file()}"):
        module.Module(None, inmanta_module.get_root_dir_of_module())


@pytest.mark.asyncio
async def test_module_requires(inmanta_module):
    inmanta_module.write_module_yml_file(
        """
name: mod
license: ASL
version: 1.0.0
requires:
    - std
    - ip > 1.0.0
        """
    )
    mod: module.Module = module.Module(None, inmanta_module.get_root_dir_of_module())
    assert mod.requires() == [Requirement.parse("std"), Requirement.parse("ip > 1.0.0")]


@pytest.mark.asyncio
async def test_module_requires_single(inmanta_module):
    inmanta_module.write_module_yml_file(
        """
name: mod
license: ASL
version: 1.0.0
requires: std > 1.0.0
        """
    )
    mod: module.Module = module.Module(None, inmanta_module.get_root_dir_of_module())
    assert mod.requires() == [Requirement.parse("std > 1.0.0")]


@pytest.mark.asyncio
async def test_module_requires_legacy(inmanta_module):
    inmanta_module.write_module_yml_file(
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
        mod = module.Module(None, inmanta_module.get_root_dir_of_module())
        assert len(w) == 1
        warning = w[0]
        assert issubclass(warning.category, MetadataDeprecationWarning)
        assert "yaml dictionary syntax for specifying module requirements has been deprecated" in str(warning.message)
    assert mod.requires() == [Requirement.parse("std"), Requirement.parse("ip > 1.0.0")]


@pytest.mark.asyncio
async def test_module_requires_legacy_invalid(inmanta_module):
    inmanta_module.write_module_yml_file(
        """
name: mod
license: ASL
version: 1.0.0
requires:
    std: ip
        """
    )
    with pytest.raises(InvalidMetadata, match="Invalid legacy requires"):
        module.Module(None, inmanta_module.get_root_dir_of_module())


def test_project_repo_type_module_v2(modules_dir, modules_repo, caplog):
    """LOOK TO REMOVE MODULES_DIR
    Tests that repos that are strings and repos that are dict with
    type 'git' are accepted and that repos with another type
    will raise a warning. (issue #3565)
    """
    projectdir = makeproject(modules_repo, "project_repo_type_module_v2", [], [])
    Project.set(Project(projectdir, autostd=True))

    projectyml = os.path.join(projectdir, "project.yml")
    with open(projectyml, "r", encoding="utf-8") as fh:
        pyml = yaml.safe_load(fh)

    # repo is a string instance (accepted)
    Project._project = None
    with caplog.at_level(logging.WARNING):
        compiler.do_compile()
    no_error_in_logs(caplog, levels=(logging.ERROR, logging.WARNING))

    # repo is a dict instance with type git (accepted)
    Project._project = None
    repo = {"url": "https://github.com/inmanta/", "type": "git"}
    pyml["repo"] = repo

    with open(projectyml, "w", encoding="utf-8") as fh:
        yaml.dump(pyml, fh)
    with caplog.at_level(logging.WARNING):
        compiler.do_compile()
    no_error_in_logs(caplog, levels=(logging.ERROR, logging.WARNING))

    # repo is a dict instance with type package (raises warning)
    Project._project = None
    repo = {"url": "https://github.com/inmanta/", "type": "package"}
    pyml["repo"] = repo

    with open(projectyml, "w", encoding="utf-8") as fh:
        yaml.dump(pyml, fh)
    with caplog.at_level(logging.WARNING):
        compiler.do_compile()
    warning = "Repos of type package where introduced in Modules v2, which are not supported by current Inmanta version."
    log_contains(caplog, "inmanta.module", logging.WARNING, warning)
