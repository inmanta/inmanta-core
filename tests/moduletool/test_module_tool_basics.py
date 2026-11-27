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

import argparse
import os
import subprocess
import warnings
from collections.abc import Iterator

import py
import pytest

from inmanta import module
from inmanta.module import InvalidMetadata, ModuleDeprecationWarning, ModuleV2Metadata
from inmanta.moduletool import ModuleTool, gitprovider
from moduletool.common import add_file
from packaging import version
from utils import module_from_template


@pytest.fixture
def tmp_working_dir(tmpdir: py.path.local) -> Iterator[py.path.local]:
    cwd = os.getcwd()
    os.chdir(str(tmpdir))
    yield tmpdir
    os.chdir(cwd)


def test_get_module_v2(tmp_working_dir: py.path.local):
    metadata_file: str = tmp_working_dir.join("setup.cfg")
    metadata_file.write("""
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
        """.strip())
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


def test_rewrite(tmpdir):
    module_path = tmpdir.join("mod").mkdir()
    model = module_path.join("model").mkdir()
    model.join("_init.cf").write("\n")

    metadata_file: str = module_path.join("setup.cfg")

    def metadata_contents(version: str, version_tag: str = "") -> str:
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
[egg_info]
tag_build = {version_tag}
        """

    metadata_file.write(metadata_contents("1.2"))
    mod = module.ModuleV2(None, module_path.strpath)

    assert mod.version == version.Version("1.2")

    # Only rewrite version
    mod.rewrite_version("1.3.1")
    assert mod.version == version.Version("1.3.1")
    assert metadata_file.read().strip() == metadata_contents("1.3.1").strip()

    # Rewrite version and version_tag
    mod.rewrite_version("2.1.2", version_tag="dev0")
    assert mod.version == version.Version("2.1.2.dev0")
    assert metadata_file.read().strip() == metadata_contents("2.1.2", version_tag="dev0").strip()


def test_substitute_version_v2_modules() -> None:
    """
    Test the behavior of the `ModuleV2Metadata._substitute_version()` method.
    """
    expected_result = """
[metadata]
name = inmanta-module-mod
version = 4.5.6
license = ASL
[egg_info]
tag_build = dev0
    """.strip()

    metadata_file_content = """
[metadata]
name = inmanta-module-mod
version = 1.2.3
license = ASL
    """.strip()
    result = ModuleV2Metadata._substitute_version(source=metadata_file_content, new_version="4.5.6", version_tag="dev0").strip()
    assert result == expected_result

    metadata_file_content = """
[metadata]
name = inmanta-module-mod
version = 1.2.3
license = ASL
[egg_info]
    """.strip()
    result = ModuleV2Metadata._substitute_version(source=metadata_file_content, new_version="4.5.6", version_tag="dev0").strip()
    assert result == expected_result

    metadata_file_content = """
[metadata]
name = inmanta-module-mod
version = 1.2.3
license = ASL
[egg_info]
tag_build = dev999
    """.strip()
    result = ModuleV2Metadata._substitute_version(source=metadata_file_content, new_version="4.5.6", version_tag="dev0").strip()
    assert result == expected_result

    expected_result = """
[metadata]
name = inmanta-module-mod
version = 4.5.6
license = ASL
[egg_info]
tag_build = dev0
tag_date = 0
tag_svn_revision = 0
[flake8]
ignore = H405,H404,H302,H306,H301,H101,H801,E402,W503,E252,E203
    """.strip()

    metadata_file_content = """
[metadata]
name = inmanta-module-mod
version = 1.2.3
license = ASL
[egg_info]
tag_build = rc123
tag_date = 0
tag_svn_revision = 0
[flake8]
ignore = H405,H404,H302,H306,H301,H101,H801,E402,W503,E252,E203
    """.strip()
    result = ModuleV2Metadata._substitute_version(source=metadata_file_content, new_version="4.5.6", version_tag="dev0").strip()
    assert result == expected_result


@pytest.fixture(scope="function")
def module_without_tags(tmpdir: py.path.local, modules_v2_dir: str) -> str:
    """
    A module in a git repository with a single release, 4.0.0.
    """
    mod_no_tag = str(tmpdir.join("mod_no_tag"))
    module_from_template(
        os.path.join(modules_v2_dir, "minimalv2module"), mod_no_tag, new_name="mod_no_tag", new_version=version.Version("4.0.0")
    )
    gitprovider.git_init(repo=mod_no_tag)
    gitprovider.commit(repo=mod_no_tag, message="first commit", add=["*"], commit_all=True)
    add_file(mod_no_tag, "signal", "present", "second commit")
    return mod_no_tag


@pytest.mark.parametrize(
    "dev",
    [False, True],
)
def test_commit_no_tags(module_without_tags, dev):
    version_tag_in_output = not dev
    add_file(module_without_tags, "dummyfile", "Content", "Commit without tags", major=True, dev=dev)
    output = subprocess.check_output(["git", "tag", "-l"], cwd=module_without_tags, stderr=subprocess.STDOUT)
    # Base version:
    assert "4.0.0" in str(output)
    # Check we only tag v5 when performing stable release
    assert ("5.0.0" in str(output)) is version_tag_in_output


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
def inmanta_module_v2(tmpdir):
    yield InmantaModule(tmpdir, "setup.cfg")


def test_module_v2_metadata(inmanta_module_v2: InmantaModule) -> None:
    inmanta_module_v2.write_metadata_file("""
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
        """)
    mod: module.ModuleV2 = module.ModuleV2(None, inmanta_module_v2.get_root_dir_of_module())
    assert mod.metadata.name == "inmanta-module-mod1"
    assert mod.metadata.version == "1.2.3"
    assert mod.metadata.license == "Apache 2.0"


@pytest.mark.parametrize("deprecated", ["", "deprecated: true", "deprecated: false"])
def test_module_v2_deprecation(inmanta_module_v2: InmantaModule, deprecated):
    inmanta_module_v2.write_metadata_file(f"""
[metadata]
name = inmanta-module-mod1
version = 1.2.3
license = Apache 2.0
{deprecated}
        """)
    with warnings.catch_warnings(record=True) as w:
        module.ModuleV2(None, inmanta_module_v2.get_root_dir_of_module())
        assert len(w) == 1 if deprecated == "deprecated: true" else len(w) == 0
        if len(w):
            warning = w[0]
            assert issubclass(warning.category, ModuleDeprecationWarning)
            assert "Module mod1 has been deprecated" in str(warning.message)


@pytest.mark.parametrize("underscore", [True, False])
def test_module_v2_name_underscore(inmanta_module_v2: InmantaModule, underscore: bool):
    """
    Test module v2 metadata parsing with respect to module naming rules about dashes and underscores.
    """
    separator: str = "_" if underscore else "-"
    inmanta_module_v2.write_metadata_file(f"""
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
        """)
    if underscore:
        with pytest.raises(InvalidMetadata):
            module.ModuleV2(None, inmanta_module_v2.get_root_dir_of_module())
    else:
        module.ModuleV2(None, inmanta_module_v2.get_root_dir_of_module())


@pytest.mark.parametrize_any(
    "version, error_msg",
    [
        ("0.0.1.dev0", "setup.cfg version should be a base version without tag. Use egg_info.tag_build to configure a tag"),
        ("hello", "Version hello is not PEP440 compliant"),
    ],
)
def test_module_v2_invalid_version(inmanta_module_v2: InmantaModule, version: str, error_msg: str):
    """
    Test module v2 metadata parsing with respect to module naming rules about dashes and underscores.
    """
    inmanta_module_v2.write_metadata_file(f"""
[metadata]
name = inmanta-module-mymod
version = {version}
license = Apache 2.0

[options]
install_requires =
  inmanta-modules-net ~=0.2.4
  inmanta-modules-std >1.0,<2.5

  cookiecutter~=1.7.0
  cryptography>1.0,<3.5
packages = find_namespace:
        """)
    with pytest.raises(InvalidMetadata) as e:
        module.ModuleV2(None, inmanta_module_v2.get_root_dir_of_module())
    assert (
        f"Metadata defined in {inmanta_module_v2.get_metadata_file_path()} is invalid:\n"
        "  1 validation error for ModuleV2Metadata\n"
        "  version\n"
        f"    Value error, {error_msg} [type=value_error, input_value='{version}', input_type=str]\n" in str(e.value)
    )


def test_moduletool_create_v2(tmp_working_dir: py.path.local) -> None:
    """
    Verify that `inmanta module create` creates a valid v2 module with expected parameters.
    """
    ModuleTool().execute("create", argparse.Namespace(name="my_module", no_input=True))
    mod: module.ModuleV2 = module.ModuleV2(project=None, path=str(tmp_working_dir.join("my-module")))
    assert mod.name == "my_module"
