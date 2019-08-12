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
    snippetcompiler.setup_for_error(
        "import badmodule",
        """could not find module badmodule (reported in import badmodule ({dir}/main.cf:1))
caused by:
  Could not load module badmodule
  caused by:
    inmanta.module.InvalidModuleException: Module %s is not a valid inmanta configuration module. Make sure that a model/_init.cf file exists and a module.yml definition file.
"""  # noqa: E501
        % modpath,
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
        """Could not set attribute `aa` on instance `__config__::A (instantiated at {dir}/main.cf:12)` (reported in Construct(A) ({dir}/main.cf:12))
caused by:
  The statement Format({{{{a}}}}) can not be executed in this context (reported in Format({{{{a}}}}) ({dir}/main.cf:4))""",  # noqa: E501
    )
