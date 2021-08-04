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
import pytest
import py
import os
from inmanta.env import LocalPackagePath
import shutil
from inmanta.compiler.config import feature_compiler_cache


@pytest.mark.parametrize("editable_install", [True, False])
def test_v2_module_loading(
    editable_install: bool, tmpdir: py.path.local, snippetcompiler_no_module_dir, capsys
) -> None:
    # Work around caching problem in venv
    feature_compiler_cache.set("False")

    module_name = "elaboratev2module"
    module_dir = os.path.normpath(os.path.join(__file__, os.pardir, "data", "modules", module_name))
    module_copy_dir = os.path.join(tmpdir, "module")
    shutil.copytree(module_dir, module_copy_dir)
    assert os.path.isdir(module_copy_dir)

    snippetcompiler_no_module_dir.setup_for_snippet(
        f"""
            import {module_name}

            {module_name}::print_message("hello world")
        """,
        autostd=False,
        install_v2_modules=[LocalPackagePath(path=module_copy_dir, editable=editable_install)],
    )

    snippetcompiler_no_module_dir.do_export()
    assert "hello world" in capsys.readouterr().out


# def test_v1_and_v2_module_installed_simultaneously(tmpdir: py.path.local, snippetcompiler, capsys) -> None:
#     # Work around caching problem in venv
#     feature_compiler_cache.set("False")
#     #
#     module_name = "elaboratev2module"
#     # module_dir = os.path.normpath(os.path.join(__file__, os.pardir, "data", "modules", module_name))
#     # module_copy_dir = os.path.join(tmpdir, "module")
#     # shutil.copytree(module_dir, module_copy_dir)
#     # assert os.path.isdir(module_copy_dir)
#
#     snippetcompiler.setup_for_snippet(
#         f"""
#             import {module_name}
#
#             {module_name}::print_message("hello world")
#         """,
#         autostd=False,
#         # install_v2_modules=[LocalPackagePath(path=module_copy_dir, editable=editable_install)],
#     )
#
#     snippetcompiler.do_export()
#     assert "hello world" in capsys.readouterr().out
