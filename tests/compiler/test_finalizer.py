"""
    Copyright 2018 Inmanta

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
from typing import Optional

from inmanta import compiler
from utils import module_from_template, v1_module_from_template


def test_modules_compiler_finalizer(
    tmpdir: str,
    snippetcompiler_clean,
    modules_dir: str,
) -> None:
    snippetcompiler_clean.setup_for_snippet("", install_project=True)

    v1_template_path: str = os.path.join(modules_dir, "minimalv1module")
    test_module: str = "test_module"
    libs_dir: str = os.path.join(str(tmpdir), "libs")

    test_module_plugin_contents: str = f"""
from inmanta.plugins import plugin
from inmanta import compiler

@plugin
def get_one() -> "string":
    return "one"

@compiler.finalizer
def finalize():
    print("end")
        """.strip()

    v1_module_from_template(
        v1_template_path,
        os.path.join(libs_dir, f"{test_module}"),
        new_name=test_module,
        new_content_init_cf="",  # original .cf needs std
        new_content_init_py=test_module_plugin_contents,
    )

    snippetcompiler_clean.setup_for_snippet(
        f"""
   import {test_module}
   value = {test_module}::get_one()
   std::print(value)
               """.strip(),
        add_to_module_path=[libs_dir],
        autostd=True,
        install_project=False,
    )

    compiler.do_compile()
