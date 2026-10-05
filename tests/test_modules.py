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

import configparser
import logging
import os
import pathlib
import shutil
import tempfile
import unittest
from _io import StringIO
from collections.abc import Mapping
from importlib.abc import Loader
from typing import Optional
from unittest import mock

import py
import pydantic
import pytest

import setuptools.config.setupcfg
from inmanta import const, env, module
from inmanta.ast import CompilerException
from inmanta.compiler.help.explainer import ExplainerFactory
from inmanta.data.model import InmantaModule, ModuleFileMetadata, ModuleSource, ModuleSourceMetadata, PipConfig
from inmanta.env import LocalPackagePath
from inmanta.loader import CodeManager, PluginModuleFinder, PluginModuleLoader
from inmanta.module import InmantaModuleRequirement
from inmanta.moduletool import ModuleTool
from utils import module_from_template


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

    def test_non_matching_name_v2_module(self) -> None:
        """
        Make sure the warning regarding directory name does not trigger for v2 modules, as it is not relevant there.
        """
        template_dir: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "modules_v2", "minimalv2module")
        with tempfile.TemporaryDirectory() as tmpdir:
            mod_dir: str = os.path.join(tmpdir, "not-the-module-name")
            module_from_template(template_dir, mod_dir)
            module.ModuleV2(project=module.DummyProject(), path=mod_dir)
            self.handler.flush()
            assert self.stream.getvalue().strip() == ""

    def tearDown(self):
        self.log.removeHandler(self.handler)
        self.handler.close()


def test_to_v2():
    """
    Test whether the `to_v2()` method of `ModuleV1Metadata` works correctly.
    """
    v1_metadata = module.ModuleV1Metadata(
        name="a_test_module",
        description="A description",
        version="1.2.3",
        license="Apache 2.0",
        compiler_version="4.5.6",
        requires=["module_dep_1", "module_dep_2"],
    )
    v2_metadata = v1_metadata.to_v2()
    for attr_name in ["description", "version", "license"]:
        assert v1_metadata.__getattribute__(attr_name) == v2_metadata.__getattribute__(attr_name)

    def _convert_module_to_package_name(module_name: str) -> str:
        return f"{module.ModuleV2.PKG_NAME_PREFIX}{module_name.replace('_', '-')}"

    assert _convert_module_to_package_name(v1_metadata.name) == v2_metadata.name
    assert [_convert_module_to_package_name(req) for req in v1_metadata.requires] == v2_metadata.install_requires


@pytest.mark.slowtest
def test_is_versioned(
    snippetcompiler_clean,
    modules_dir: str,
    modules_v2_dir: str,
    caplog,
    tmpdir,
    local_module_package_index,  # upstream for setuptools for isolated build
) -> None:
    """
    Test whether the warning regarding non-versioned modules is given correctly.
    """
    # Disable modules_dir
    snippetcompiler_clean.modules_dir = None

    def compile_and_assert_warning(
        module_name: str, needs_versioning_warning: bool, install_v2_modules: list[LocalPackagePath] = []
    ) -> None:
        caplog.clear()
        snippetcompiler_clean.setup_for_snippet(
            f"import {module_name}", autostd=False, install_v2_modules=install_v2_modules, index_url=local_module_package_index
        )
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


@pytest.mark.parametrize(
    "v1_module, all_python_requirements,strict_python_requirements,module_requirements,module_v2_requirements",
    [
        (
            True,
            ["jinja2~=3.2.1", "inmanta-module-v2-module==1.2.3"],
            ["jinja2~=3.2.1"],
            ["v2_module==1.2.3", "v1_module==1.1.1"],
            [InmantaModuleRequirement.parse("v2_module==1.2.3")],
        ),
        (
            False,
            ["jinja2~=3.2.1", "inmanta-module-v2-module==1.2.3"],
            ["jinja2~=3.2.1"],
            ["v2_module==1.2.3"],
            [InmantaModuleRequirement.parse("v2_module==1.2.3")],
        ),
    ],
)
def test_get_requirements(
    modules_dir: str,
    modules_v2_dir: str,
    v1_module: bool,
    all_python_requirements: list[str],
    strict_python_requirements: list[str],
    module_requirements: list[str],
    module_v2_requirements: list[str],
) -> None:
    """
    Test the different methods to get the requirements of a module.
    """
    module_name = "many_dependencies"

    if v1_module:
        module_dir = os.path.join(modules_dir, module_name)
        mod = module.ModuleV1(module.DummyProject(autostd=False), module_dir)
    else:
        module_dir = os.path.join(modules_v2_dir, module_name)
        mod = module.ModuleV2(module.DummyProject(autostd=False), module_dir)

    assert set(mod.get_all_python_requirements_as_list()) == set(all_python_requirements)
    assert set(mod.get_strict_python_requirements_as_list()) == set(strict_python_requirements)
    assert set(mod.get_module_requirements()) == set(module_requirements)
    assert set(mod.get_module_v2_requirements()) == set(module_v2_requirements)
    assert set(mod.requires()) == {module.InmantaModuleRequirement.parse(req) for req in module_requirements}


def test_module_v1_code_for_transport(modules_dir: str) -> None:
    """
    A V1 module is not distributed as a python package, so its code always has to be transported to the agents.
    """
    v1 = module.ModuleV1(module.DummyProject(autostd=False), os.path.join(modules_dir, "many_dependencies"))

    code = v1.get_code_for_transport()
    # The plugins directory of a V1 module holds the inmanta_plugins.<module name> package
    assert [path for _, path in code.plugin_files] == ["inmanta_plugins/many_dependencies/__init__.py"]
    # Its packaging files are composed in memory, and declare its python requirements, see
    # test_module_v1_code_for_transport_packaging_files.
    assert {path for path, _ in code.packaging_files} == {module.ModuleV2.MODULE_FILE, module.ModuleV2.PYPROJECT_FILE}


def test_module_v1_code_for_transport_packaging_files(modules_dir: str, tmp_path: pathlib.Path) -> None:
    """
    A V1 module has no packaging files on disk, so they are composed from the metadata derived from its module.yml.
    The agent can rebuild the module from these, so they have to describe an installable python package.
    """

    def read_install_requires_with_setuptools(v1_module_dir: str) -> list[str]:
        """
        Read back the install_requires of the setup.cfg composed for the given V1 module the way setuptools does when
        pip builds the module. It parses the list differently from configparser: a value on a single line is split on
        semicolons, which also separate a requirement from its environment marker.
        """
        packaging_files = dict(
            module.ModuleV1(module.DummyProject(autostd=False), v1_module_dir).get_code_for_transport().packaging_files
        )
        setup_cfg_path = tmp_path / "setup.cfg"
        setup_cfg_path.write_bytes(packaging_files[module.ModuleV2.MODULE_FILE])
        return setuptools.config.setupcfg.read_configuration(setup_cfg_path)["options"]["install_requires"]

    module_dir = os.path.join(modules_dir, "many_dependencies")
    v1 = module.ModuleV1(module.DummyProject(autostd=False), module_dir)

    packaging_files = dict(v1.get_code_for_transport().packaging_files)
    assert set(packaging_files) == {module.ModuleV2.MODULE_FILE, module.ModuleV2.PYPROJECT_FILE}

    setup_cfg = configparser.ConfigParser()
    setup_cfg.read_string(packaging_files[module.ModuleV2.MODULE_FILE].decode("utf-8"))

    assert setup_cfg.get("metadata", "name") == f"{module.ModuleV2.PKG_NAME_PREFIX}many-dependencies"
    assert setup_cfg.get("metadata", "version") == "1.2.1"

    # setuptools only discovers the rebuilt inmanta_plugins tree with these.
    assert setup_cfg.get("options", "packages") == "find_namespace:"
    assert setup_cfg.get("options.packages.find", "include") == f"{const.PLUGINS_PACKAGE}*"

    # The install_requires are the python requirements of the module, i.e. the ones in its requirements.txt, and those
    # alone. The `requires` section of the module.yml lists inmanta modules, which may well be V1 themselves: turning
    # those into python requirements would make pip resolve an inmanta-module-<name> package that can not exist.
    assert sorted(setup_cfg.get("options", "install_requires").strip().split("\n")) == [
        "inmanta-module-v2-module==1.2.3",
        "jinja2~=3.2.1",
    ]
    assert "inmanta-module-v1-module==1.1.1" not in setup_cfg.get("options", "install_requires")
    assert sorted(read_install_requires_with_setuptools(module_dir)) == ["inmanta-module-v2-module==1.2.3", "jinja2~=3.2.1"]

    # A single requirement with an environment marker is read back as that one requirement, not split on its semicolon.
    single_requirement_module_dir = tmp_path / "single_requirement"
    shutil.copytree(module_dir, single_requirement_module_dir)
    (single_requirement_module_dir / "requirements.txt").write_text('jinja2~=3.2.1; python_version > "3.0"\n')
    assert read_install_requires_with_setuptools(str(single_requirement_module_dir)) == [
        'jinja2~=3.2.1; python_version > "3.0"'
    ]

    # pip builds the rebuilt package with the same backend as a real V2 module.
    assert b'build-backend = "setuptools.build_meta"' in packaging_files[module.ModuleV2.PYPROJECT_FILE]


def test_module_v1_code_for_transport_packaging_files_percent(modules_dir: str) -> None:
    """
    A module.yml is free to contain a `%`, which setup.cfg reads as an interpolation marker. It has to make it into the
    packaging files unchanged, since setuptools reads them back with interpolation enabled.
    """
    v1 = module.ModuleV1(module.DummyProject(autostd=False), os.path.join(modules_dir, "many_dependencies"))
    v1.metadata.description = "Manages 100% of the fleet"

    packaging_files = dict(v1.get_code_for_transport().packaging_files)

    setup_cfg = configparser.ConfigParser()
    setup_cfg.read_string(packaging_files[module.ModuleV2.MODULE_FILE].decode("utf-8"))
    assert setup_cfg.get("metadata", "description") == "Manages 100% of the fleet"


def test_module_v1_code_for_transport_without_plugins(modules_dir: str) -> None:
    """
    A V1 module that defines no plugins at all has no plugin directory: it has no plugin files to transport.
    """
    v1 = module.ModuleV1(module.DummyProject(autostd=False), os.path.join(modules_dir, "minimalv1module"))

    assert v1.get_plugin_dir() is None
    assert v1.get_code_for_transport().plugin_files == []


@pytest.mark.parametrize("editable", [True, False])
def test_module_v2_code_for_transport(modules_v2_dir: str, editable: bool) -> None:
    """
    The code of a V2 module only has to be transported when it is installed in editable mode. A package installed module
    is installed by the agents with pip.
    """
    v2 = module.ModuleV2(
        module.DummyProject(autostd=False),
        os.path.join(modules_v2_dir, "many_dependencies"),
        is_editable_install=editable,
    )

    code = v2.get_code_for_transport()
    if not editable:
        assert code is None
        return
    assert code is not None
    assert [path for _, path in code.plugin_files] == ["inmanta_plugins/many_dependencies/__init__.py"]
    # The packaging files are transported as they are on disk, and declare the python requirements of the module
    assert dict(code.packaging_files) == dict(v2.get_metadata_files())
    assert module.ModuleV2.MODULE_FILE in dict(code.packaging_files)


def test_module_code_for_transport_paths(modules_v2_dir: str, tmp_path: pathlib.Path) -> None:
    """
    Every transported file keeps the exact path it has in the python package tree of its module, so a package whose
    only file is its __init__.py stays a package: it is not mistaken for a plain module, which would resolve its
    relative imports against another package.
    """
    module_dir = tmp_path / "minimalv2module"
    shutil.copytree(os.path.join(modules_v2_dir, "minimalv2module"), module_dir)
    plugin_dir = module_dir / const.PLUGINS_PACKAGE / "minimalv2module"
    (plugin_dir / "handlers.py").write_text("")
    (plugin_dir / "sub").mkdir()
    (plugin_dir / "sub" / "__init__.py").write_text("from .. import handlers\n")

    v2 = module.ModuleV2(module.DummyProject(autostd=False), str(module_dir), is_editable_install=True)
    code = v2.get_code_for_transport()
    assert code is not None

    sources = {
        path: ModuleSource.from_path(absolute_path=absolute_path, path=path) for absolute_path, path in code.plugin_files
    }
    assert {path: source.metadata.name for path, source in sources.items()} == {
        "inmanta_plugins/minimalv2module/__init__.py": "inmanta_plugins.minimalv2module",
        "inmanta_plugins/minimalv2module/handlers.py": "inmanta_plugins.minimalv2module.handlers",
        "inmanta_plugins/minimalv2module/sub/__init__.py": "inmanta_plugins.minimalv2module.sub",
    }


def test_module_source_metadata_path() -> None:
    """
    The path of a transported file determines the python module it defines and whether it holds byte code.
    """
    package = ModuleSourceMetadata(path="inmanta_plugins/mod/sub/__init__.py", hash_value="h")
    assert package.name == "inmanta_plugins.mod.sub"
    assert not package.is_byte_code

    plain_module = ModuleSourceMetadata(path="inmanta_plugins/mod/sub.py", hash_value="h")
    assert plain_module.name == "inmanta_plugins.mod.sub"
    assert plain_module.get_inmanta_module_name() == "mod"

    byte_code = ModuleSourceMetadata(path="inmanta_plugins/mod/__init__.pyc", hash_value="h")
    assert byte_code.name == "inmanta_plugins.mod"
    assert byte_code.is_byte_code

    for invalid_path in ("/inmanta_plugins/mod/__init__.py", "inmanta_plugins/../mod.py", "inmanta_plugins/mod/setup.cfg"):
        with pytest.raises(pydantic.ValidationError):
            ModuleSourceMetadata(path=invalid_path, hash_value="h")


def test_module_version_covers_paths() -> None:
    """
    Moving a file to another path yields another module version, even though no content changed.
    """
    before = [ModuleSourceMetadata(path="inmanta_plugins/mod/sub.py", hash_value="h")]
    after = [ModuleSourceMetadata(path="inmanta_plugins/mod/sub/__init__.py", hash_value="h")]
    assert CodeManager.get_module_version(before) != CodeManager.get_module_version(after)

    # A change to a packaging file alone yields another version as well: the module would be rebuilt differently
    sources = [ModuleSourceMetadata(path="inmanta_plugins/mod/__init__.py", hash_value="h")]
    assert CodeManager.get_module_version(
        [*sources, ModuleFileMetadata(path=const.SETUP_CFG_FILE, hash_value="a")]
    ) != CodeManager.get_module_version([*sources, ModuleFileMetadata(path=const.SETUP_CFG_FILE, hash_value="b")])


def test_module_file_metadata_path() -> None:
    """
    Any file inside the python package tree of a module can be transported, but only a python file defines a python
    module.
    """
    assert not ModuleFileMetadata(path=const.SETUP_CFG_FILE, hash_value="h").is_python_source()
    assert ModuleFileMetadata(path="inmanta_plugins/mod/__init__.pyc", hash_value="h").is_python_source()

    for invalid_path in ("/setup.cfg", "../setup.cfg"):
        with pytest.raises(pydantic.ValidationError):
            ModuleFileMetadata(path=invalid_path, hash_value="h")


def test_inmanta_module_files_match_install_mode() -> None:
    """
    An editable installed module has to carry its files, its setup.cfg included, for the agent to rebuild it. A package
    installed module carries none: the agent installs it from the package index.
    """
    source = ModuleSourceMetadata(path="inmanta_plugins/mod/__init__.py", hash_value="h")
    setup_cfg = ModuleFileMetadata(path=const.SETUP_CFG_FILE, hash_value="s")

    def make(*, editable_install: bool, files_in_module: list[ModuleFileMetadata] | None) -> InmantaModule:
        return InmantaModule(
            name="mod",
            version="1.0.0",
            files_in_module=files_in_module,
            requirements=[],
            load_module_on_agents=[],
            editable_install=editable_install,
        )

    make(editable_install=True, files_in_module=[source, setup_cfg])
    make(editable_install=False, files_in_module=None)

    for editable_install, files_in_module in ((True, None), (True, [source]), (False, [source, setup_cfg])):
        with pytest.raises(pydantic.ValidationError):
            make(editable_install=editable_install, files_in_module=files_in_module)


@pytest.mark.parametrize("editable", [True, False])
def test_module_v2_source_get_installed_module_editable(
    # Use clean snippetcompiler (separate venv) because this test installs test packages into the snippetcompiler venv.
    snippetcompiler_clean,
    modules_v2_dir: str,
    editable: bool,
    local_module_package_index,  # upstream for setuptools for isolated build
) -> None:
    """
    Make sure ModuleV2Source.get_installed_module identifies editable installations correctly.
    """
    module_name: str = "minimalv2module"
    module_dir: str = os.path.join(modules_v2_dir, module_name)
    snippetcompiler_clean.setup_for_snippet(
        f"import {module_name}",
        autostd=False,
        install_v2_modules=[env.LocalPackagePath(path=module_dir, editable=editable)],
        index_url=local_module_package_index if editable else None,
    )

    source: module.ModuleV2Source = module.ModuleV2Source()
    mod: Optional[module.ModuleV2] = source.get_installed_module(module.DummyProject(autostd=False), module_name)
    assert mod is not None
    # os.path.realpath because snippetcompiler uses symlinks
    assert os.path.realpath(mod.path) == (
        module_dir if editable else os.path.join(env.process_env.site_packages_dir, "inmanta_plugins", module_name)
    )
    assert mod._is_editable_install == editable


def test_module_v2_source_path_for_v1(snippetcompiler) -> None:
    """
    Make sure ModuleV2Source.path_for does not include modules loaded by the v1 module loader.
    """
    # load tests module
    snippetcompiler.setup_for_snippet("import tests")
    module.Project.get().load_plugins()

    # make sure the v1 module finder is configured and discovered by env.process_env
    assert PluginModuleFinder.MODULE_FINDER is not None
    module_info: Optional[tuple[Optional[str], Loader]] = env.process_env.get_module_file("inmanta_plugins.tests")
    assert module_info is not None
    path, loader = module_info
    assert path is not None
    assert isinstance(loader, PluginModuleLoader)

    source: module.ModuleV2Source = module.ModuleV2Source()
    assert source.path_for("tests") is None


def test_module_v2_from_v1_path(
    local_module_package_index: str,
    modules_v2_dir: str,
    snippetcompiler_clean,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Verify that attempting to load a v2 module from the v1 modules path fails with an appropriate message when a v2 module is
    found in a v1 module source.
    """
    with pytest.raises(module.ModuleLoadingException) as excinfo:
        snippetcompiler_clean.setup_for_snippet("import minimalv2module", add_to_module_path=[modules_v2_dir])
    cause: CompilerException = excinfo.value.__cause__
    assert cause.msg == (
        "Module at %s looks like a v2 module. Please have a look at the documentation on how to use v2 modules."
        % os.path.join(modules_v2_dir, "minimalv2module")
    )
    assert ExplainerFactory().explain_and_format(excinfo.value, plain=True).strip() == (f"""
Exception explanation
=====================
This error occurs when a v2 module was found in v1 modules path. To resolve this you should either convert this module to be v1 or install it as a v2 module and set up your project accordingly.

If you want to use the module as a v1 module, make sure to use the v1 cookiecutter template to create new modules.

If you want to use the module as a v2 module:
- set up your project with a module source of type "package" (see documentation)
- if you would like to work in editable mode on a local copy of the module, run `inmanta module install -e {modules_v2_dir}/minimalv2module`
- run `inmanta module add --v2 minimalv2module` to add the module as a dependency and to install the module if required.
        """).strip()  # noqa: E501

    # verify that adding it as a v2 resolves the issue
    project: module.Project = snippetcompiler_clean.setup_for_snippet(
        "",
        autostd=False,
        index_url=local_module_package_index,
        install_project=False,
    )
    os.chdir(project.path)
    project_init = module.Project.__init__

    # patch Project.__init__ to set autostd=False because v2 std does not exist yet
    def project_init_nostd(self, *args, **kwargs) -> None:
        project_init(self, *args, autostd=False, **{key: value for key, value in kwargs.items() if key != "autostd"})

    monkeypatch.setattr(module.Project, "__init__", project_init_nostd)
    ModuleTool().add("minimalv2module", v2=True)
    snippetcompiler_clean.setup_for_snippet(
        "import minimalv2module",
        autostd=False,
        # run with the same module path
        add_to_module_path=[modules_v2_dir],
        python_package_sources=[local_module_package_index],
        install_project=True,
    )


@pytest.mark.slowtest
def test_module_v2_incorrect_install_warning(
    tmpdir: py.path.local,
    modules_v2_dir: str,
    snippetcompiler_clean,
    caplog,
) -> None:
    """
    Verify that attempting to load a v2 module that has been installed from source with `pip install` rather than
    `inmanta module install` results in an appropriate error or warning.
    """
    # set up project and activate project venv
    snippetcompiler_clean.setup_for_snippet("")

    # prepare module
    module_dir: str = str(tmpdir.join("mymodule"))
    shutil.copytree(os.path.join(modules_v2_dir, "minimalv2module"), module_dir)

    def verify_exception(expected: Optional[str]) -> None:
        """
        Verify AST loading fails with the expected message, or succeeds if expected is None.
        """
        if expected is None:
            snippetcompiler_clean.setup_for_snippet("import minimalv2module", autostd=False)
            return
        with pytest.raises(module.ModuleLoadingException) as excinfo:
            snippetcompiler_clean.setup_for_snippet("import minimalv2module", autostd=False)
        cause: CompilerException = excinfo.value.__cause__
        assert cause.msg == expected

    # install module from source without using `inmanta module install`
    env.process_env.install_for_config(
        requirements=[], paths=[env.LocalPackagePath(path=module_dir, editable=False)], config=PipConfig(use_system_config=True)
    )
    module_path = os.path.join(env.process_env.site_packages_dir, const.PLUGINS_PACKAGE, "minimalv2module")
    verify_exception(
        f"Invalid module at {module_path}: found module package but it has no setup.cfg. "
        "This occurs when you install or build modules from source incorrectly. "
        "Always use the `inmanta module build` command followed by `pip install ./dist/<dist-package>` to "
        "respectively build a module from source and install the distribution "
        "package. Make sure to uninstall the broken package first."
    )

    # include setup.cfg in package to circumvent error
    shutil.copy(os.path.join(module_dir, "setup.cfg"), os.path.join(module_dir, const.PLUGINS_PACKAGE, "minimalv2module"))
    env.process_env.install_for_config(
        requirements=[], paths=[env.LocalPackagePath(path=module_dir, editable=False)], config=PipConfig(use_system_config=True)
    )
    verify_exception(
        "The module at %s contains no _init.cf file. This occurs when you install or build modules from source"
        " incorrectly. Always use the `inmanta module build` command followed by `pip install ./dist/<dist-package>` to"
        " respectively build a module from source and install the distribution package."
        " Make sure to uninstall the broken package first." % module_path
    )
    os.remove(os.path.join(module_dir, const.PLUGINS_PACKAGE, "minimalv2module", "setup.cfg"))

    # verify that proposed solution works: editable install doesn't require uninstall first
    env.process_env.install_for_config(
        requirements=[],
        paths=[env.LocalPackagePath(path=module_dir, editable=True)],
        config=PipConfig(use_system_config=True),
    )
    verify_exception(None)


def test_from_path(tmpdir: py.path.local, projects_dir: str, modules_dir: str, modules_v2_dir: str) -> None:
    """
    Verify that ModuleLike.from_path() and subclass overrides work as expected.
    """

    def check(
        path: str,
        *,
        subdir: Optional[str] = None,
        expected: Mapping[type[module.ModuleLike], Optional[type[module.ModuleLike]]],
    ) -> None:
        """
        Check the functionality for the given path and expected outcomes.

        :param path: The path to the root of the module like directory.
        :param subdir: The subpath to pass to `from_path`, relative to `path`.
        :param expected: Key-value pairs where keys represent the classes to call the method on and values the expected type
            for the return value.
        """
        full_path: str = os.path.join(path, *([subdir] if subdir is not None else []))
        for cls, tp in expected.items():
            result: Optional[module.ModuleLike] = cls.from_path(full_path)
            assert (result is None) is (tp is None)
            if tp is not None:
                assert isinstance(result, tp)
                assert result.path == path

    # project checks
    check(
        os.path.join(projects_dir, "simple_project"),
        expected={
            module.ModuleLike: module.Project,
            module.Project: module.Project,
            module.Module: None,
            module.ModuleV1: None,
            module.ModuleV2: None,
        },
    )

    # module v1 checks
    check(
        os.path.join(modules_dir, "minimalv1module"),
        expected={
            module.ModuleLike: module.ModuleV1,
            module.Project: None,
            module.Module: module.ModuleV1,
            module.ModuleV1: module.ModuleV1,
            module.ModuleV2: None,
        },
    )

    # module v2 checks
    check(
        os.path.join(modules_v2_dir, "minimalv2module"),
        expected={
            module.ModuleLike: module.ModuleV2,
            module.Project: None,
            module.Module: module.ModuleV2,
            module.ModuleV1: None,
            module.ModuleV2: module.ModuleV2,
        },
    )

    check(str(tmpdir), expected={module.ModuleLike: None})

    # advanced setup: project with modules in libs dir
    project_dir: str = str(tmpdir.join("project"))
    shutil.copytree(os.path.join(projects_dir, "simple_project"), project_dir)
    libs_dir: str = os.path.join(project_dir, "libs")
    os.makedirs(libs_dir, exist_ok=True)
    module_dir: str = os.path.join(libs_dir, "minimalv1module")
    shutil.copytree(os.path.join(modules_dir, "minimalv1module"), module_dir)
    check(module_dir, expected={module.ModuleLike: module.ModuleV1})
    check(libs_dir, expected={module.ModuleLike: None})
    check(project_dir, expected={module.ModuleLike: module.Project})
