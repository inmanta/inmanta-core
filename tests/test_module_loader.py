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
import os
import shutil
from typing import List

import py
import pytest

from inmanta.compiler.config import feature_compiler_cache
from inmanta.env import LocalPackagePath
from inmanta.module import ModuleV1, ModuleV2, Project
from inmanta.moduletool import DummyProject, ModuleConverter


@pytest.mark.parametrize("editable_install", [True, False])
def test_v2_module_loading(
    editable_install: bool, tmpdir: py.path.local, snippetcompiler, capsys, modules_v2_dir: str
) -> None:
    # Work around caching problem in venv
    feature_compiler_cache.set("False")
    # Disable modules_dir
    snippetcompiler.modules_dir = None

    module_name = "elaboratev2module"
    module_dir = os.path.join(modules_v2_dir, module_name)
    module_copy_dir = os.path.join(tmpdir, "module")
    shutil.copytree(module_dir, module_copy_dir)
    assert os.path.isdir(module_copy_dir)

    snippetcompiler.setup_for_snippet(
        f"""
            import {module_name}

            {module_name}::print_message("Hello world")
        """,
        autostd=False,
        install_v2_modules=[LocalPackagePath(path=module_copy_dir, editable=editable_install)],
    )

    snippetcompiler.do_export()
    assert "Hello world" in capsys.readouterr().out


def test_v1_and_v2_module_installed_simultaneously(
    tmpdir: py.path.local, snippetcompiler_clean, capsys, caplog, modules_dir: str
) -> None:
    """
    When a module is installed both in V1 and V2 format, ensure that:
       * A warning is logged
       * The V2 module is loaded and not the V1 module.
    """
    # Work around caching problem in venv
    feature_compiler_cache.set("False")

    module_name = "v1_print_plugin"

    def compile_and_verify(
        expected_message: str, expect_warning: bool, install_v2_modules: List[LocalPackagePath] = []
    ) -> None:
        snippetcompiler_clean.setup_for_snippet(f"import {module_name}", install_v2_modules=install_v2_modules, autostd=False)
        caplog.clear()
        snippetcompiler_clean.do_export()
        assert expected_message in capsys.readouterr().out
        got_warning = f"Module {module_name} is installed as a V1 module and a V2 module" in caplog.text
        assert got_warning == expect_warning

    # Run compile. Only a V1 module is installed in the module path
    expected_message_v1 = "Hello world"
    compile_and_verify(expected_message=expected_message_v1, expect_warning=False)
    assert isinstance(Project.get().modules[module_name], ModuleV1)

    # Convert V1 module to V2 module and install it as well
    module_dir = os.path.join(modules_dir, module_name)
    v1_module_dir = os.path.join(tmpdir, "v1_module")
    shutil.copytree(module_dir, v1_module_dir)
    assert os.path.isdir(v1_module_dir)
    v2_module_dir = os.path.join(tmpdir, "v2_module")
    module = ModuleV1(project=DummyProject(autostd=False), path=v1_module_dir)
    ModuleConverter(module).convert(output_directory=v2_module_dir)

    # Print a different message in the V2 module, to detect which of both gets loaded
    expected_message_v2 = "Other message"
    with open(os.path.join(v2_module_dir, "model", "_init.cf"), "r+") as fd:
        content = fd.read()
        assert expected_message_v1 in content
        content = content.replace(expected_message_v1, expected_message_v2)
        assert expected_message_v2 in content
        fd.seek(0)
        fd.write(content)

    # Run compile again. V1 version and V2 version are installed simultaneously
    compile_and_verify(
        expected_message=expected_message_v2,
        expect_warning=True,
        install_v2_modules=[LocalPackagePath(path=v2_module_dir, editable=False)],
    )
    assert isinstance(Project.get().modules[module_name], ModuleV2)


def test_v1_module_depends_on_v1_and_v2_module(tmpdir: py.path.local, snippetcompiler, capsys, modules_v2_dir: str) -> None:
    module_dir = os.path.join(modules_v2_dir, "elaboratev2module")
    module_copy_dir = os.path.join(tmpdir, "module")
    shutil.copytree(module_dir, module_copy_dir)
    assert os.path.isdir(module_copy_dir)

    module_name = "v1_module_depends_on_v1_and_v2_module"
    snippetcompiler.setup_for_snippet(
        f"import {module_name}",
        install_v2_modules=[LocalPackagePath(path=module_copy_dir, editable=False)],
    )

    snippetcompiler.do_export()
    output = capsys.readouterr().out
    assert "Print from v2 module" in output
    assert "Hello world" in output
