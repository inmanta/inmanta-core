"""
    Copyright 2016 Inmanta

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

import unittest
import tempfile
import shutil
import os

from inmanta.module import Project
from inmanta import compiler
from inmanta.ast import CompilerException


class SnippetTests(unittest.TestCase):
    libs = None
    env = None

    @classmethod
    def setUpClass(cls):
        cls.libs = tempfile.mkdtemp()
        cls.env = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.libs)
        shutil.rmtree(cls.env)

    def setUpForSnippet(self, snippet):
        # init project
        self.project_dir = tempfile.mkdtemp()
        os.symlink(self.__class__.env, os.path.join(self.project_dir, ".env"))

        with open(os.path.join(self.project_dir, "project.yml"), "w") as cfg:
            cfg.write(
                """
            name: snippet test
            modulepath: [%s, %s]
            downloadpath: %s
            version: 1.0
            repo: ['https://github.com/inmanta/']"""
                % (self.__class__.libs,
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "modules"),
                    self.__class__.libs))

        with open(os.path.join(self.project_dir, "main.cf"), "w") as x:
            x.write(snippet)

        Project.set(Project(self.project_dir))

    def setup_for_error(self, snippet, shouldbe):
        self.setUpForSnippet(snippet)
        try:
            compiler.do_compile()
            assert False, "Should get exception"
        except CompilerException as e:
            text = str(e)
            print(text)
            shouldbe = shouldbe.format(dir=self.project_dir)
            assert shouldbe == text

    def test_plugin_excn(self):
        self.setup_for_error(
            """
        import std
        std::template("/tet.tmpl")
""",
            "Exception in plugin std::template caused by TemplateNotFound: /tet.tmpl "
            "(reported in std::template('/tet.tmpl') ({dir}/main.cf:3))"
        )

    def test_bad_var(self):
        self.setup_for_error(
            """
        a=b
""",
            "variable b not found (reported in Assign(a, b) ({dir}/main.cf:2))"
        )

    def test_bad_type(self):
        self.setup_for_error(
            """
entity Test1:
    string a
end

Test1(a=3)
""",
            "Could not set attribute `a` on instance `__config__::Test1 (instantiated at {dir}/main.cf:6)` caused by Invalid "
            "value '3', expected String (reported in Construct(Test1) ({dir}/main.cf:6))"
        )

    def test_bad_type_2(self):
        self.setup_for_error(
            """
import std

entity Test1:
    string a
end

implement Test1 using std::none

t1 = Test1()
t1.a=3
""",
            "Could not set attribute `a` on instance `__config__::Test1 (instantiated at {dir}/main.cf:10)` caused by Invalid "
            "value '3', expected String (reported in t1.a = 3 ({dir}/main.cf:11)) (reported in t1.a = 3 ({dir}/main.cf:11))"
        )

    def test_incomplete(self):
        self.setup_for_error(
            """
import std

entity Test1:
    string a
end

implement Test1 using std::none

t1 = Test1()
""",
            "The object __config__::Test1 (instantiated at {dir}/main.cf:10) is not complete: "
            "attribute a ({dir}/main.cf:5) is not set"
        )
