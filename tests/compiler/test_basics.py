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
import warnings
from typing import Optional

import pytest

from inmanta import compiler, const
from inmanta.ast import DoubleSetException
from inmanta.plugins import PluginDeprecationWarning
from utils import module_from_template, v1_module_from_template


def test_str_on_instance_pos(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import std

entity Hg:
end

Hg.hosts [0:] -- std::Host

implement Hg using std::none

hg = Hg()

for i in [1,2,3]:
 hg.hosts = std::Host(name="Test{{i}}", os=std::unix)
end


for i in hg.hosts:
    std::ConfigFile(host=i, path="/fx", content="")
end
"""
    )
    (types, _) = compiler.do_compile()
    files = types["std::File"].get_all_instances()
    assert len(files) == 3


def test_str_on_instance_neg(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import std

entity Hg:
end

Hg.hosts [0:] -- std::Host

implement Hg using std::none

hg = Hg()

for i in [1,2,3]:
 hg.hosts = std::Host(name="Test", os=std::unix)
end


for i in hg.hosts:
    std::ConfigFile(host=i, path="/fx", content="")
end
"""
    )
    (types, _) = compiler.do_compile()
    files = types["std::File"].get_all_instances()
    assert len(files) == 1


def test_implements_inheritance(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    string a
end

entity TestC extends Test:
end

implementation test for Test:
    self.a = "xx"
end


implement TestC using parents
implement TestC using std::none, parents
implement TestC using std::none
implement Test using test

a = TestC()
"""
    )
    (_, scopes) = compiler.do_compile()

    root = scopes.get_child("__config__")
    assert "xx" == root.lookup("a").get_value().lookup("a").get_value()


def test_keyword_excn(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
       index = ""
""",
        "Syntax error: invalid identifier, index is a reserved keyword ({dir}/main.cf:2:8)",
    )


def test_keyword_excn2(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
       implementation index for std::Entity:
       end
""",
        "Syntax error: invalid identifier, index is a reserved keyword ({dir}/main.cf:2:23)",
    )


def test_keyword_excn3(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
       implementation aaa for index::Entity:
       end
""",
        "Syntax error: invalid identifier, index is a reserved keyword ({dir}/main.cf:2:31)",
    )


def test_cid_excn(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
       entity test:
       end
""",
        "Syntax error: Invalid identifier: Entity names must start with a capital ({dir}/main.cf:2:15)",
    )


def test_cid_excn2(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
       entity Test extends test:
       end
""",
        "Syntax error: Invalid identifier: Entity names must start with a capital ({dir}/main.cf:2:28)",
    )


def test_bad_var(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
        a=b
""",
        "variable b not found (reported in a = b ({dir}/main.cf:2))",
    )


def test_bad_type(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity Test1:
    string a
end

Test1(a=3)
""",
        """Could not set attribute `a` on instance `__config__::Test1 (instantiated at {dir}/main.cf:6)` """
        """(reported in Construct(Test1) ({dir}/main.cf:6))
caused by:
  Invalid value '3', expected String (reported in Construct(Test1) ({dir}/main.cf:6))""",
    )


def test_bad_type_2(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
import std

entity Test1:
    string a
end

implement Test1 using std::none

t1 = Test1()
t1.a=3
""",
        """Could not set attribute `a` on instance `__config__::Test1 (instantiated at {dir}/main.cf:10)` (reported in t1.a = 3 ({dir}/main.cf:11))
caused by:
  Invalid value '3', expected String (reported in t1.a = 3 ({dir}/main.cf:11))""",  # noqa: E501
    )


def test_value_set_twice(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
test = "a"
test = "b"
""",
        """value set twice:
\told value: a
\t\tset at {dir}/main.cf:2
\tnew value: b
\t\tset at {dir}/main.cf:3
 (reported in test = 'b' ({dir}/main.cf:3))""",
    )


def test_modules_v2_compile(tmpdir: str, snippetcompiler_clean, modules_dir: str, modules_v2_dir: str) -> None:
    # activate compiler venv and install std module (#3297)
    snippetcompiler_clean.setup_for_snippet("", install_project=True)

    v1_template_path: str = os.path.join(modules_dir, "minimalv1module")
    v2_template_path: str = os.path.join(modules_v2_dir, "minimalv2module")
    libs_dir: str = os.path.join(str(tmpdir), "libs")

    # main module, used as proxy to load test module's model and plugins
    main_module: str = "main"
    # module under test
    test_module: str = "test_module"

    def test_module_plugin_contents(value: int) -> str:
        """
        Returns the contents of the plugin file for the test module.
        """
        return f"""
from inmanta.plugins import plugin


VALUE: str = {value}

@plugin
def get_value() -> "int":
    return VALUE
        """.strip()

    # The model for the test module, regardless of value
    test_module_model: str = f"value = {test_module}::get_value()"

    # install main module (make it v1 so there are no restrictions on what it can depend on)
    v1_module_from_template(
        v1_template_path,
        os.path.join(libs_dir, f"{main_module}"),
        new_name=main_module,
        new_content_init_cf=f"""
import {test_module}

# test variable import
test_module_value = {test_module}::value
# test plugin call
test_module_value = {test_module}::get_value()
# test intermodule Python imports
test_module_value = {main_module}::get_test_module_value()
        """.strip(),
        new_content_init_py=f"""
from inmanta.plugins import plugin
from {const.PLUGINS_PACKAGE}.{test_module} import VALUE


@plugin
def get_test_module_value() -> "int":
    return VALUE
        """.strip(),
    )

    def verify_compile(expected_value: int) -> None:
        """
        Verify compilation by importing main module and checking its variable's value.
        """
        snippetcompiler_clean.setup_for_snippet(
            f"""
import {main_module}

# make sure imported variable has expected value (these statements will produce compiler error if it doesn't)
value = {main_module}::test_module_value
value = {expected_value}
            """.strip(),
            add_to_module_path=[libs_dir],
            # set autostd=False because no v2 std exists at the time of writing
            autostd=False,
            install_project=False,
        )
        compiler.do_compile()

    # install test module as v1 and verify compile
    v1_module_from_template(
        v1_template_path,
        os.path.join(libs_dir, test_module),
        new_name=test_module,
        new_content_init_cf=test_module_model,
        new_content_init_py=test_module_plugin_contents(1),
    )
    verify_compile(1)

    # install module as v2 (on top of v1) and verify compile
    v2_module_path: str = os.path.join(str(tmpdir), test_module)
    module_from_template(
        v2_template_path,
        v2_module_path,
        new_name=test_module,
        new_content_init_cf=test_module_model,
        new_content_init_py=test_module_plugin_contents(2),
        install=True,
        editable=True,  # ! this is editable for the next test step
    )
    verify_compile(2)

    # verify editable mode for plugins
    with open(os.path.join(v2_module_path, const.PLUGINS_PACKAGE, test_module, "__init__.py"), "w") as fh:
        fh.write(test_module_plugin_contents(3))
    verify_compile(3)

    # verify editable mode for model
    with open(os.path.join(v2_module_path, "model", "_init.cf"), "w") as fh:
        fh.write("value = 4")
    # can't just verify_compile(4) because the plugin is still at 3 and promoting it to 4 would not test changes in the model
    with pytest.raises(DoubleSetException) as excinfo:
        verify_compile(3)
    assert excinfo.value.newvalue == 4


@pytest.mark.parametrize(
    "erroneous_statement,error_at_char",
    [
        (
            "bool CRC18",
            6,
        ),
        (
            "bool CRC18=false",
            6,
        ),
        (
            "bool? CRC18",
            7,
        ),
        (
            "bool? CRC18=null",
            7,
        ),
        (
            "bool[] CRC18",
            8,
        ),
        (
            "bool[] CRC18=[false]",
            8,
        ),
        (
            "bool[]? CRC18",
            9,
        ),
        (
            "bool[]? CRC18=null",
            9,
        ),
        (
            "int CRC18=null",
            5,
        ),
        (
            "dict CRC18",
            6,
        ),
        (
            "dict CRC18={'invalid':'identifier'}",
            6,
        ),
        (
            "dict CRC18=null",
            6,
        ),
        (
            "dict? CRC18",
            7,
        ),
        (
            "dict? CRC18={'invalid':'identifier'}",
            7,
        ),
        (
            "dict? CRC18=null",
            7,
        ),
    ],
)
def test_attributes_starting_with_capital_letter(snippetcompiler, erroneous_statement, error_at_char):
    expected_error = (
        "Syntax error: Invalid identifier: attribute names must start with a lower case character "
        "({dir}/main.cf:3:"
        f"{error_at_char})"
    )
    snippetcompiler.setup_for_error(
        f"""
entity A:
{erroneous_statement}
end
""",
        expected_error,
    )


def test_unpack_null_dictionary(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
hello_world = "Hello World!"
dct = null
hi_world = std::replace(hello_world, **dct)
std::print(hi_world)
""",
        (
            "The ** operator can only be applied to dictionaries (reported in "
            "std::replace(hello_world,**dct) ({dir}/main.cf:4))"
        ),
    )


@pytest.mark.parametrize_any(
    "decorator, replaced_by",
    [("", None), ("@deprecated", None), ("@deprecated()", None), ('@deprecated(replaced_by="newplugin")', '"newplugin"')],
)
def test_modules_plugin_deprecated(
    tmpdir: str, snippetcompiler_clean, modules_dir: str, decorator: str, replaced_by: Optional[str]
) -> None:
    snippetcompiler_clean.setup_for_snippet("", install_project=True)

    v1_template_path: str = os.path.join(modules_dir, "minimalv1module")
    test_module: str = "test_module"
    libs_dir: str = os.path.join(str(tmpdir), "libs")

    test_module_plugin_contents: str = f"""
from inmanta.plugins import plugin, deprecated

{decorator}
@plugin
def get_one() -> "int":
    return 1
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
               """.strip(),
        add_to_module_path=[libs_dir],
        autostd=False,
        install_project=False,
    )
    with warnings.catch_warnings(record=True) as w:
        compiler.do_compile()
        assert len(w) == 1 if decorator else len(w) == 0
        if len(w):
            warning = w[0]
            assert issubclass(warning.category, PluginDeprecationWarning)
            if replaced_by:
                replaced_by_name = replaced_by.replace('"', "")
                assert (
                    f"Plugin 'get_one' in module 'inmanta_plugins.test_module' is deprecated. It should be "
                    f"replaced by '{replaced_by_name}'" in str(warning.message)
                )
            else:
                assert "Plugin 'get_one' in module 'inmanta_plugins.test_module' is deprecated." in str(warning.message)


@pytest.mark.parametrize_any(
    "decorator",
    ["@deprecated", "@deprecated()", '@deprecated(replaced_by="newplugin")'],
)
def test_modules_failed_import_deprecated(tmpdir: str, snippetcompiler_clean, modules_dir: str, decorator: str) -> None:
    """
    to ensure backwards compatibility of modules when using the @deprecated decorator
    a little piece of code is proposed in the docs:
    try:
        from inmanta.plugins import deprecated
    except ImportError:
        deprecated = lambda f=None, **kwargs: f if f is not None else deprecated
    if deprecated can't be imported the decorator should just be ignored and not crash de compilation.
    this test verifies the lambda expression works as expected
    """
    snippetcompiler_clean.setup_for_snippet("", install_project=True)

    v1_template_path: str = os.path.join(modules_dir, "minimalv1module")
    test_module: str = "test_module"
    libs_dir: str = os.path.join(str(tmpdir), "libs")

    test_module_plugin_contents: str = f"""
deprecated = lambda f=None, **kwargs: f if f is not None else deprecated
from inmanta.plugins import plugin

{decorator}
@plugin
def get_one() -> "int":
    return 1
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
                   """.strip(),
        add_to_module_path=[libs_dir],
        autostd=False,
        install_project=False,
    )

    compiler.do_compile()


@pytest.mark.parametrize_any(
    "decorator1,decorator2",
    [("@plugin", "@deprecated"), ("", "@deprecated")],
)
def test_modules_fail_deprecated(
    tmpdir: str, snippetcompiler_clean, modules_dir: str, decorator1: str, decorator2: str
) -> None:
    """
    Test that en exception is raised when the @deprecated decorator is wrongly used
    """
    snippetcompiler_clean.setup_for_snippet("", install_project=True)

    v1_template_path: str = os.path.join(modules_dir, "minimalv1module")
    test_module: str = "test_module"
    libs_dir: str = os.path.join(str(tmpdir), "libs")

    test_module_plugin_contents: str = f"""
from inmanta.plugins import plugin, deprecated

{decorator1}
{decorator2}
def get_one() -> "int":
    return 1
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
                   """.strip(),
        add_to_module_path=[libs_dir],
        autostd=False,
        install_project=False,
    )

    with pytest.raises(Exception) as e:
        compiler.do_compile()
    assert (
        "Can not deprecate 'get_one': The '@deprecated' decorator should be used in combination with the "
        "'@plugin' decorator and should be placed at the top." in e.value.msg
    )


def test_modules_plugin_custom_name_deprecated(
    tmpdir: str,
    snippetcompiler_clean,
    modules_dir: str,
) -> None:
    """
    Test that a plugin with a custom name can be deprecated
    """
    snippetcompiler_clean.setup_for_snippet("", install_project=True)

    v1_template_path: str = os.path.join(modules_dir, "minimalv1module")
    test_module: str = "test_module"
    libs_dir: str = os.path.join(str(tmpdir), "libs")

    test_module_plugin_contents: str = f"""
from inmanta.plugins import plugin, deprecated

@deprecated
@plugin("custom_name")
def get_one() -> "int":
    return 1
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

       value = {test_module}::custom_name()
                   """.strip(),
        add_to_module_path=[libs_dir],
        autostd=False,
        install_project=False,
    )
    with warnings.catch_warnings(record=True) as w:
        compiler.do_compile()
        assert len(w) == 1
        warning = w[0]
        assert issubclass(warning.category, PluginDeprecationWarning)
        assert "Plugin 'custom_name' in module 'inmanta_plugins.test_module' is deprecated." in str(warning.message)
