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

import logging
import os

import pytest

from inmanta import compiler
from inmanta.ast import DoubleSetException, MultiException
from utils import log_contains, v1_module_from_template


def test_modules_compiler_finalizer(
    tmpdir: str,
    snippetcompiler_clean,
    modules_dir: str,
) -> None:
    """
    verify that the finalizers are called at the end of the compilation.
    """
    snippetcompiler_clean.setup_for_snippet("", install_project=True)

    v1_template_path: str = os.path.join(modules_dir, "minimalv1module")
    test_module: str = "test_module"
    libs_dir: str = os.path.join(str(tmpdir), "libs")

    test_module_plugin_contents: str = (
        """
from inmanta.plugins import plugin
from inmanta import compiler

connection1 = None
connection2 = None

@plugin
def connect1() -> "string":
   global connection1
   connection1 = "connected"
   return connection1

@plugin
def connect2() -> "string":
   global connection2
   connection2 = "connected"
   compiler.finalizer(finalize2)
   return connection2

@compiler.finalizer
def finalize1():
    global connection1
    if connection1:
        connection1 = "closed"

def finalize2():
    global connection2
    if connection2:
        connection2 = "closed"
        """.strip()
    )

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
   was_connected1 = {test_module}::connect1() == 'connected'
   was_connected2 = {test_module}::connect2() == 'connected'
               """.strip(),
        add_to_module_path=[libs_dir],
        autostd=True,
        install_project=False,
    )

    (_, scopes) = compiler.do_compile()
    root = scopes.get_child("__config__")
    assert root.lookup("was_connected1").get_value()  # verify that the value of connection1 was changed before the finalizer
    assert root.lookup("was_connected2").get_value()  # verify that the value of connection2 was changed before the finalizer
    import inmanta_plugins.test_module

    assert inmanta_plugins.test_module.connection1 == "closed"
    assert inmanta_plugins.test_module.connection2 == "closed"


def test_modules_compiler_exception_finalizer(tmpdir: str, snippetcompiler_clean, modules_dir: str) -> None:
    """
    verify that the finalizers are called even if there is an exception raised during compilation
    """
    snippetcompiler_clean.setup_for_snippet("", install_project=True)

    v1_template_path: str = os.path.join(modules_dir, "minimalv1module")
    test_module: str = "test_module"
    libs_dir: str = os.path.join(str(tmpdir), "libs")

    test_module_plugin_contents: str = (
        """
from inmanta import compiler

connection = None

@compiler.finalizer
def finalize():
    global connection
    connection = "closed"
        """.strip()
    )

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
   a = 1
   a = 2
               """.strip(),
        add_to_module_path=[libs_dir],
        autostd=True,
        install_project=False,
    )

    with pytest.raises(DoubleSetException):
        compiler.do_compile()
    import inmanta_plugins.test_module

    assert inmanta_plugins.test_module.connection == "closed"


@pytest.mark.parametrize("compile_exception", ["", "a = 2"])
def test_modules_compiler_finalizer_exception(
    tmpdir: str,
    snippetcompiler_clean,
    clean_reset,
    modules_dir: str,
    caplog,
    compile_exception: str,
) -> None:
    """
    verify that the exceptions in the finalizer are raised if there are no exceptions during the compilation,
    and that they are logged if there is an exception during compilation.
    """
    snippetcompiler_clean.setup_for_snippet("", install_project=True)

    v1_template_path: str = os.path.join(modules_dir, "minimalv1module")
    test_module: str = "test_module"
    libs_dir: str = os.path.join(str(tmpdir), "libs")

    test_module_plugin_contents: str = (
        """
from inmanta import compiler

@compiler.finalizer
def finalize1():
    connection = 3/0

@compiler.finalizer
def finalize2():
    raise Exception("big mistake")
        """.strip()
    )

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
   a = 1
   {compile_exception}""".strip(),
        add_to_module_path=[libs_dir],
        autostd=True,
        install_project=False,
    )

    if compile_exception:
        with caplog.at_level(logging.ERROR):
            with pytest.raises(DoubleSetException):
                compiler.do_compile()
            log_contains(
                caplog,
                "inmanta.compiler",
                logging.ERROR,
                "Finalizer failed: division by zero",
            )
            log_contains(
                caplog,
                "inmanta.compiler",
                logging.ERROR,
                "Finalizer failed: big mistake",
            )
    else:
        with pytest.raises(MultiException) as e:
            compiler.do_compile()
        assert str(e.value) == "Reported 2 errors:\n\tFinalizer failed: division by zero\n\tFinalizer failed: big mistake"
