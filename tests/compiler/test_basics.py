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
import pathlib
import warnings
from typing import Optional

import py
import pytest

from inmanta import compiler, const, module
from inmanta.ast import DoubleSetException, RuntimeException
from inmanta.env import safe_parse_requirement
from inmanta.module import InstallMode
from inmanta.plugins import PluginDeprecationWarning
from packaging import version
from utils import module_from_template, v1_module_from_template


def test_str_on_instance_pos(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import std::testing

entity Hg:
end

Hg.hosts [0:] -- std::Host

implement Hg using std::none

hg = Hg()

for i in [1,2,3]:
 hg.hosts = std::Host(name="Test{{i}}", os=std::unix)
end


for i in hg.hosts:
    std::testing::NullResource(name=i.name)
end
"""
    )
    (types, _) = compiler.do_compile()
    test_resources = types["std::testing::NullResource"].get_all_instances()
    assert len(test_resources) == 3


def test_str_on_instance_neg(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import std::testing

entity Hg:
end

Hg.hosts [0:] -- std::Host

implement Hg using std::none

hg = Hg()

for i in [1,2,3]:
 hg.hosts = std::Host(name="Test", os=std::unix)
end


for i in hg.hosts:
    std::testing::NullResource(name=i.name)
end
"""
    )
    (types, _) = compiler.do_compile()
    test_resources = types["std::testing::NullResource"].get_all_instances()
    assert len(test_resources) == 1


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
  Invalid value '3', expected string (reported in Construct(Test1) ({dir}/main.cf:6))""",
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
  Invalid value '3', expected string (reported in t1.a = 3 ({dir}/main.cf:11))""",  # noqa: E501
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
    [("", None), ("@deprecated", None), ("@deprecated()", None), ('@deprecated(replaced_by="newplugin")', "newplugin")],
)
def test_modules_plugin_deprecated(
    tmpdir: str, snippetcompiler_clean, modules_dir: str, decorator: str, replaced_by: Optional[str]
) -> None:
    snippetcompiler_clean.setup_for_snippet("", install_project=True)

    v1_template_path: str = os.path.join(modules_dir, "minimalv1module")
    test_module: str = "test_module"
    libs_dir: str = os.path.join(str(tmpdir), "libs")

    test_module_plugin_contents: str = (
        f"""
from inmanta.plugins import plugin, deprecated

{decorator}
@plugin
def get_one() -> "int":
    return 1
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

   value = {test_module}::get_one()
               """.strip(),
        add_to_module_path=[libs_dir],
        autostd=False,
        install_project=False,
    )
    with warnings.catch_warnings(record=True) as w:
        compiler.do_compile()
        if decorator:
            has_warning: bool = False
            for warning in w:
                if issubclass(warning.category, PluginDeprecationWarning):
                    has_warning = True
                    if replaced_by:
                        assert (
                            f"Plugin 'test_module::get_one' is deprecated. "
                            f"It should be replaced by '{replaced_by}'" in str(warning.message)
                        )
                    else:
                        assert "Plugin 'test_module::get_one' is deprecated." in str(warning.message)
            assert has_warning
        else:
            assert not any(issubclass(warning.category, PluginDeprecationWarning) for warning in w)


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

    test_module_plugin_contents: str = (
        f"""
deprecated = lambda f=None, **kwargs: f if f is not None else deprecated
from inmanta.plugins import plugin

{decorator}
@plugin
def get_one() -> "int":
    return 1
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

    test_module_plugin_contents: str = (
        f"""
from inmanta.plugins import plugin, deprecated

{decorator1}
{decorator2}
def get_one() -> "int":
    return 1
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

    test_module_plugin_contents: str = (
        """
from inmanta.plugins import plugin, deprecated

@deprecated
@plugin("custom_name")
def get_one() -> "int":
    return 1
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

       value = {test_module}::custom_name()
                   """.strip(),
        add_to_module_path=[libs_dir],
        autostd=False,
        install_project=False,
    )

    with warnings.catch_warnings(record=True) as w:
        compiler.do_compile()
        has_warning: bool = False
        for warning in w:
            if issubclass(warning.category, PluginDeprecationWarning):
                has_warning = True
                assert "Plugin 'test_module::custom_name' is deprecated." in str(warning.message)
        assert has_warning


def test_var_not_found_in_implement(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity Test:
end
implementation test for Test:
    std::print("This is test {{n}}")
end
implement Test using test
Test()
""",
        r"variable n not found (reported in Format('This is test {{{{n}}}}') ({dir}/main.cf:5))",
    )


def test_var_not_found_in_implement_2(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity A: end
implementation a for A:
    x = y
end
implement A using a
A()
""",
        r"variable y not found (reported in x = y ({dir}/main.cf:4))",
    )


def test_var_not_found_nested_case(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity A:
end
A.x [1] -- B                # 5
entity B:
end
implementation a for A:     # 10
    x
end
implementation b for B:
    std::print(u)           # 15
end
implement A using a
implement B using b
A(x=B())
""",
        r"variable u not found (reported in std::print(u) ({dir}/main.cf:11))",
    )


def test_implementation_import_missing_error(snippetcompiler) -> None:
    """
    Verify that an error is raised when referring to something that is not imported in an implementation
    """
    snippetcompiler.setup_for_snippet(
        """
        entity A:
        end

        implementation a for A:
            test = tests::length("one")
        end

        implement A using a

        """
    )

    with pytest.raises(RuntimeException) as exception:
        snippetcompiler.do_export()
    assert "could not find type tests::length in namespace __config__" in exception.value.msg
    assert exception.value.location.lnr == 6
    assert exception.value.location.start_char == 20


@pytest.mark.parametrize("name", ["", "#", " # ", "#this is a comment"])
def test_safe_requirement(name) -> None:
    """
    Ensure that empty name requirements are not allowed in `Requirement`
    """
    with pytest.raises(AssertionError):
        safe_parse_requirement(requirement=name)


@pytest.mark.slowtest
def test_moduletool_failing(
    capsys,
    tmpdir: py.path.local,
    local_module_package_index: str,
    snippetcompiler_clean,
    modules_v2_dir: str,
) -> None:
    """
    Verify code is not loaded when python files are stored in `files`, `model` and `template` folders of a V2 module.
    """
    # set up venv
    snippetcompiler_clean.setup_for_snippet("", autostd=False)

    module_template_path: pathlib.Path = pathlib.Path(modules_v2_dir) / "failingminimalv2module"
    module_from_template(
        str(module_template_path),
        str(tmpdir.join("custom_mod_one")),
        new_name="custom_mod_one",
        new_version=version.Version("1.0.0"),
        install=True,
        editable=False,
    )

    for problematic_folder in ["files", "model", "templates"]:
        (module_template_path / problematic_folder).mkdir(exist_ok=True)
        new_file = module_template_path / problematic_folder / "afile.py"
        new_file.write_text("raise RuntimeError('This file should not be loaded')")

        # set up project with a v2 module
        snippetcompiler_clean.setup_for_snippet(
            """
    import std
    import custom_mod_one
            """.strip(),
            python_package_sources=[local_module_package_index],
            project_requires=[
                module.InmantaModuleRequirement.parse("std"),
                module.InmantaModuleRequirement.parse("custom_mod_one"),
            ],
            python_requires=[],
            install_mode=InstallMode.release,
            install_project=True,
            autostd=False,
        )

        compiler.do_compile()

        # We remove the problematic file to be sure to test the other problematic directories
        new_file.unlink()
