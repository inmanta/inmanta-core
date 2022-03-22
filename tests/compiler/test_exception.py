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

import inmanta.compiler as compiler
from inmanta.ast import DoubleSetException, MultiException
from inmanta.config import Config


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

implement Host using std::none
implement Repo using std::none when host.os.name=="os"
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
        f"""could not find module badmodule (reported in import badmodule ({snippetcompiler.project_dir}/main.cf:1))
caused by:
  Could not load module badmodule
  caused by:
    inmanta.module.InvalidModuleException: Metadata file {path_modules_yml_file} does not exist
""",
    )


def test_direct_execute_error(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
        a = "A"

        typedef zz as string matching self == "{{a}}"

        entity A:
            zz aa = "A"
        end

        implement A using std::none

        A()
        """,
        "The statement Format({{{{a}}}}) can not be executed in this context (reported in Format({{{{a}}}}) ({dir}/main.cf:4))",
    )


def test_optional_value_exception(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity Test:
    number? n
    number m
end

implementation i for Test:
    self.m = self.n
end

implement Test using i

Test()
        """,
        "Optional variable accessed that has no value (attribute `n` of `__config__::Test (instantiated at {dir}/main.cf:13)`)"
        " (reported in self.n ({dir}/main.cf:8))",
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
    number n
end

implement A using std::none

x = A()
y = A()

x.n = y.n
y.n = nn

nn = mm
mm = nn
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
  The object __config__::A (instantiated at {dir}/main.cf:9) is not complete: attribute n ({dir}/main.cf:3:12) is not set
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

implement A using std::none
implement B using std::none
implement C using std::none
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

implement A using std::none
implement B using std::none
implement C using std::none
        """,
        """Could not set attribute `bs` on instance `__config__::C (instantiated at {dir}/main.cf:2)` (reported in Construct(C) ({dir}/main.cf:2))
caused by:
  Invalid class type for __config__::A (instantiated at {dir}/main.cf:3), should be __config__::B (reported in Construct(C) ({dir}/main.cf:2))""",  # noqa: E501
    )
