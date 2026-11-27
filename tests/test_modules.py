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

import os
import pathlib
import shutil
from collections.abc import Mapping
from typing import Optional

import py
import pydantic
import pytest

from inmanta import const, env, module
from inmanta.ast import CompilerException
from inmanta.data.model import InmantaModule, ModuleFileMetadata, ModuleSourceMetadata, PipConfig
from inmanta.env import LocalPackagePath
from inmanta.loader import CodeManager
from inmanta.module import InmantaModuleRequirement


@pytest.mark.slowtest
def test_is_versioned(
    snippetcompiler_clean,
    modules_v2_dir: str,
    caplog,
    tmpdir,
    local_module_package_index,  # upstream for setuptools for isolated build
) -> None:
    """
    Test whether the warning regarding non-versioned modules is given correctly.
    """

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


def test_get_requirements(modules_v2_dir: str) -> None:
    """
    Test the different methods to get the requirements of a module.
    """
    mod = module.ModuleV2(module.DummyProject(autostd=False), os.path.join(modules_v2_dir, "many_dependencies"))

    assert set(mod.get_all_python_requirements_as_list()) == {"jinja2~=3.2.1", "inmanta-module-v2-module==1.2.3"}
    assert set(mod.get_strict_python_requirements_as_list()) == {"jinja2~=3.2.1"}
    assert set(mod.get_module_requirements()) == {"v2_module==1.2.3"}
    assert set(mod.get_module_v2_requirements()) == {InmantaModuleRequirement.parse("v2_module==1.2.3")}
    assert set(mod.requires()) == {module.InmantaModuleRequirement.parse("v2_module==1.2.3")}


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
    # The python files and the packaging files are transported as they are on disk. The packaging files declare the
    # python requirements of the module.
    module_dir = pathlib.Path(modules_v2_dir, "many_dependencies")
    assert dict(code.files) == {
        "inmanta_plugins/many_dependencies/__init__.py": (
            module_dir / "inmanta_plugins" / "many_dependencies" / "__init__.py"
        ).read_bytes(),
        module.ModuleV2.MODULE_FILE: (module_dir / "setup.cfg").read_bytes(),
        const.PYPROJECT_TOML_FILE: (module_dir / "pyproject.toml").read_bytes(),
    }


def test_module_code_for_transport_paths(modules_v2_dir: str, tmp_path: pathlib.Path) -> None:
    """
    The exporter transports each python file of an editable module under its path in the python package tree of the
    module, nested packages included.
    """
    module_dir = tmp_path / "minimalv2module"
    shutil.copytree(os.path.join(modules_v2_dir, "minimalv2module"), module_dir)
    plugin_dir = module_dir / const.PLUGINS_PACKAGE / "minimalv2module"
    (plugin_dir / "handlers.py").write_text("")
    (plugin_dir / "sub").mkdir()
    (plugin_dir / "sub" / "__init__.py").write_text("")

    v2 = module.ModuleV2(module.DummyProject(autostd=False), str(module_dir), is_editable_install=True)
    code = v2.get_code_for_transport()
    assert code is not None

    assert sorted(path for path, _ in code.files) == [
        "inmanta_plugins/minimalv2module/__init__.py",
        "inmanta_plugins/minimalv2module/handlers.py",
        "inmanta_plugins/minimalv2module/sub/__init__.py",
        const.PYPROJECT_TOML_FILE,
        module.ModuleV2.MODULE_FILE,
    ]


def test_module_v2_code_for_transport_without_pyproject(modules_v2_dir: str, tmp_path: pathlib.Path) -> None:
    """
    An editable module without a pyproject.toml can not be exported: the agent installs the module with
    `pip install -e`, which refuses a source tree without one.
    """
    module_dir = tmp_path / "minimalv2module"
    shutil.copytree(os.path.join(modules_v2_dir, "minimalv2module"), module_dir)
    (module_dir / const.PYPROJECT_TOML_FILE).unlink()

    v2 = module.ModuleV2(module.DummyProject(autostd=False), str(module_dir), is_editable_install=True)
    with pytest.raises(module.InvalidModuleException, match="has no pyproject.toml"):
        v2.get_code_for_transport()


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


def test_module_version_covers_paths() -> None:
    """
    Moving a file to another path yields another module version, even though no content changed.
    """
    before = [ModuleFileMetadata(path="inmanta_plugins/mod/sub.py", hash_value="h")]
    after = [ModuleFileMetadata(path="inmanta_plugins/mod/sub/__init__.py", hash_value="h")]
    assert CodeManager.get_module_version(before) != CodeManager.get_module_version(after)

    # A change to a packaging file alone yields another version as well: the module would be rebuilt differently
    sources = [ModuleFileMetadata(path="inmanta_plugins/mod/__init__.py", hash_value="h")]
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


def test_inmanta_module_files_match_install_mode() -> None:
    """
    An editable installed module has to carry its files, its setup.cfg and pyproject.toml included, for the agent to
    rebuild it. A package installed module carries none: the agent installs it from the package index.
    """
    source = ModuleFileMetadata(path="inmanta_plugins/mod/__init__.py", hash_value="h")
    setup_cfg = ModuleFileMetadata(path=const.SETUP_CFG_FILE, hash_value="s")
    pyproject_toml = ModuleFileMetadata(path=const.PYPROJECT_TOML_FILE, hash_value="p")

    def make(*, editable_install: bool, files_in_module: list[ModuleFileMetadata] | None) -> InmantaModule:
        return InmantaModule(
            name="mod",
            version="1.0.0",
            files_in_module=files_in_module,
            load_module_on_agents=[],
            editable_install=editable_install,
        )

    make(editable_install=True, files_in_module=[source, setup_cfg, pyproject_toml])
    make(editable_install=False, files_in_module=None)

    for editable_install, files_in_module, error in (
        (True, None, "has to carry its files"),
        (True, [source, pyproject_toml], "has to carry its files"),
        (True, [source, setup_cfg], "has to carry its files"),
        (False, [source, setup_cfg, pyproject_toml], "can not carry files"),
    ):
        with pytest.raises(pydantic.ValidationError, match=error):
            make(editable_install=editable_install, files_in_module=files_in_module)


def test_inmanta_module_extras_validation() -> None:
    """
    The agents put the extras of a module in a pip requirement, so only valid extra names are accepted. They are
    normalized, deduplicated and sorted.
    """

    def make(extras: list[str]) -> InmantaModule:
        return InmantaModule(
            name="mod",
            version="1.0.0",
            files_in_module=None,
            load_module_on_agents=[],
            editable_install=False,
            extras=extras,
        )

    assert make(["Feature_X", "a.b", "feature-x", "b"]).extras == ["a-b", "b", "feature-x"]
    assert make([]).extras == []

    for extra in (
        "x,evil",
        "a]==1.0",
        'x] @ https://example.com/x.whl ; os_name=="posix"',
        "",
        " a",
        "-a",
        "a-",
        "a b",
        # Non-ASCII letters whose case folds to an ASCII letter
        "ı",
        "featurſ",
    ):
        with pytest.raises(pydantic.ValidationError, match="Invalid extra name"):
            make(["valid", extra])


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


@pytest.mark.slowtest
def test_module_v2_incorrect_install_warning(
    tmpdir: py.path.local,
    modules_v2_dir: str,
    snippetcompiler_clean,
    local_module_package_index: str,
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
    pip_config = PipConfig(index_url=local_module_package_index)

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
        requirements=[], paths=[env.LocalPackagePath(path=module_dir, editable=False)], config=pip_config
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
        requirements=[], paths=[env.LocalPackagePath(path=module_dir, editable=False)], config=pip_config
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
        config=pip_config,
    )
    verify_exception(None)


def test_from_path(tmpdir: py.path.local, projects_dir: str, modules_v2_dir: str) -> None:
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
            module.ModuleV2: module.ModuleV2,
        },
    )

    check(str(tmpdir), expected={module.ModuleLike: None})

    # advanced setup: project with modules in libs dir
    project_dir: str = str(tmpdir.join("project"))
    shutil.copytree(os.path.join(projects_dir, "simple_project"), project_dir)
    libs_dir: str = os.path.join(project_dir, "libs")
    os.makedirs(libs_dir, exist_ok=True)
    module_dir: str = os.path.join(libs_dir, "minimalv2module")
    shutil.copytree(os.path.join(modules_v2_dir, "minimalv2module"), module_dir)
    check(module_dir, expected={module.ModuleLike: module.ModuleV2})
    check(libs_dir, expected={module.ModuleLike: None})
    check(project_dir, expected={module.ModuleLike: module.Project})
