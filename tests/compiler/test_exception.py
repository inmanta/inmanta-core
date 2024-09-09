"""
    Copyright 2019 Inmanta

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
import re
import textwrap

import pytest

from inmanta import compiler
from inmanta.ast import DoubleSetException, MultiException, NotFoundException
from inmanta.config import Config
from inmanta.execute import scheduler


def test_multi_excn(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity Repo:
    string name
end

entity Host:
    string name
end

entity OS:
    string name
end

Repo.host [1] -- Host
Host.os [1] -- OS

host = Host(name="x")

Repo(host=host,name="epel")

implement Host using none
implement Repo using none when host.os.name=="os"

implementation none for std::Entity:
end
""",
        """Reported 2 errors
error 0:
  The object __config__::Host (instantiated at {dir}/main.cf:17) is not complete: attribute os ({dir}/main.cf:15:6) is not set
error 1:
  Unable to select implementation for entity Repo (reported in __config__::Repo (instantiated at {dir}/main.cf:19) ({dir}/main.cf:19))""",  # noqa: E501
    )


def test_module_error(snippetcompiler):
    modpath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "modules", "badmodule")
    path_modules_yml_file = os.path.join(modpath, "module.yml")
    snippetcompiler.setup_for_error(
        "import badmodule",
        f"""Failed to load module badmodule (reported in import badmodule ({snippetcompiler.project_dir}/main.cf:1))
caused by:
  Metadata file {path_modules_yml_file} does not exist
        """.strip(),
    )


def test_direct_execute_error(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
        a = "A"

        typedef zz as string matching self == "{{a}}"

        entity A:
            zz aa = "A"
        end

        implement A using none

        A()

        implementation none for std::Entity:
        end
        """,
        (
            "The statement Format('{{{{a}}}}') can not be executed in this context"
            " (reported in Format('{{{{a}}}}') ({dir}/main.cf:4))"
        ),
    )


def test_plugin_exception(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
import tests
tests::raise_exception('my message')
        """,
        """  PluginException in plugin tests::raise_exception
  Test: my message (reported in tests::raise_exception('my message') ({dir}/main.cf:3))
  caused by:
    inmanta_plugins.tests.TestPluginException: my message
""",
        indent_offset=1,
    )


def test_dataflow_exception(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
x = 0
x = 1
        """,
    )
    Config.set("compiler", "datatrace_enable", "true")
    try:
        compiler.do_compile()
    except DoubleSetException as e:
        assert e.msg.strip() == (
            """
value set twice:
	old value: 0
		set at {dir}/main.cf:2
	new value: 1
		set at {dir}/main.cf:3

data trace:
x
├── 0
│   SET BY `x = 0`
│   AT {dir}/main.cf:2
└── 1
    SET BY `x = 1`
    AT {dir}/main.cf:3
            """.strip().format(  # noqa: W191, E101
                dir=snippetcompiler.project_dir
            )
        )


def test_dataflow_multi_exception(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity A:
    int n
end

implement A using none

x = A()
y = A()

x.n = y.n
y.n = nn

nn = mm
mm = nn

implementation none for std::Entity:
end
        """,
    )
    Config.set("compiler", "datatrace_enable", "true")
    try:
        compiler.do_compile()
    except MultiException as e:
        assert e.format_trace(indent="  ").strip() == (
            """
Reported 1 errors
error 0:
  The object __config__::A (instantiated at {dir}/main.cf:9) is not complete: attribute n ({dir}/main.cf:3:9) is not set
data trace:
attribute n on __config__::A instance
SUBTREE for __config__::A instance:
    CONSTRUCTED BY `A()`
    AT {dir}/main.cf:9
└── nn
    SET BY `y.n = nn`
    AT {dir}/main.cf:12
    EQUIVALENT TO {{mm, nn}} DUE TO STATEMENTS:
        `nn = mm` AT {dir}/main.cf:14
        `mm = nn` AT {dir}/main.cf:15
            """.strip().format(
                dir=snippetcompiler.project_dir
            )
        )


def test_assignment_failed_on_gradual(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
c1 = C()
c1.bs += c1.ac
c1.ac = A()

entity A:
end

entity B extends A:
end

entity C:
end

C.ac [0:] -- A
C.bs [0:] -- B

implement A using none
implement B using none
implement C using none

implementation none for std::Entity:
end
        """,
        """Could not set attribute `bs` on instance `__config__::C (instantiated at {dir}/main.cf:2)` (reported in c1.bs = c1.ac ({dir}/main.cf:3))
caused by:
  Invalid class type for __config__::A (instantiated at {dir}/main.cf:4), should be __config__::B (reported in c1.bs = c1.ac ({dir}/main.cf:3))""",  # noqa: E501
    )


def test_assignment_failed_on_gradual_ctor(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
c1 = C(bs = c1.ac)
c1.ac = A()

entity A:
end

entity B extends A:
end

entity C:
end

C.ac [0:] -- A
C.bs [0:] -- B

implement A using none
implement B using none
implement C using none

implementation none for std::Entity:
end
        """,
        """Could not set attribute `bs` on instance `__config__::C (instantiated at {dir}/main.cf:2)` (reported in Construct(C) ({dir}/main.cf:2))
caused by:
  Invalid class type for __config__::A (instantiated at {dir}/main.cf:3), should be __config__::B (reported in Construct(C) ({dir}/main.cf:2))""",  # noqa: E501
    )


def test_exception_default_constructors(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
typedef MyType as A(n = 42)

entity A:
    int n
    int m
end

implement A using std::none
        """,
        """Syntax error: The use of default constructors is no longer supported ({dir}/main.cf:2:9)""",
    )


def test_multi_line_constructor(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity ManyFields:
    string a
    string b
    string c
end

implement ManyFields using none

ManyFields(
    a = "A",
    b = "B",
    c = "C",
    d = "D",
)

implementation none for std::Entity:
end
""",
        """no attribute d on type __config__::ManyFields (reported in d ({dir}/main.cf:14:5))""",  # noqa: E501
    )


def load_types() -> None:
    comp: compiler.Compiler = compiler.Compiler()
    sched: scheduler.Scheduler = scheduler.Scheduler()

    (statements, blocks) = comp.compile()
    sched.define_types(comp, statements, blocks)


@pytest.mark.parametrize_any(
    "namespace",
    [
        "doesnotexist",
        "doesnotexist::doesnotexist",
        "std::doesnotexist",
        "alias::can_not_access_subnamespace_on_alias",
    ],
)
def test_reference_nonexisting_namespace(snippetcompiler, namespace: str) -> None:
    """
    Verify that an appropriate exception is raised when a namespace is referenced that doesn't exist in the model.
    The exception should be raised even in the type checking phase for diagnostic purposes (e.g. VSCode language server).
    """
    # AST loading should succeed
    snippetcompiler.setup_for_snippet(
        textwrap.dedent(
            f"""
            import std as alias

            {namespace}::x
            """.strip(
                "\n"
            )
        ),
        install_project=True,
    )
    with pytest.raises(
        NotFoundException,
        match=re.escape(
            f"Namespace {namespace} not found.\nTry importing it with `import {namespace}`"
            f" (reported in {namespace}::x ({snippetcompiler.project_dir}/main.cf:3:1))"
        ),
    ):
        load_types()


def test_namespace_alias(snippetcompiler) -> None:
    """
    Verify that referencing an import alias does not get mistakenly interpreted as referencing a non-existing namespace.
    """
    snippetcompiler.setup_for_snippet(
        """
        import std as alias

        alias::x
        alias::count([])
        """,
        install_project=True,
    )
    # verify that this does not fail
    load_types()
