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
import glob
import tempfile
import os
from inmanta.module import Project
import inmanta.compiler as compiler
from inmanta.config import Config


class CompilerFixture():

    def __init__(self):
        self.libs = tempfile.mkdtemp()
        self.env = tempfile.mkdtemp()
        Config.load_config()
        Config.set("config", "environment", "0000")

    def run_snippet(self, snippet):
        project_dir = tempfile.mkdtemp()
        os.symlink(self.env, os.path.join(project_dir, ".env"))

        with open(os.path.join(project_dir, "project.yml"), "w") as cfg:
            cfg.write(
                """
            name: snippet test
            modulepath: %s
            downloadpath: %s
            version: 1.0
            repo: ['git@git.inmanta.com:modules/', 'git@git.inmanta.com:config/']"""
                % (self.libs, self.libs))

        with open(os.path.join(project_dir, "main.cf"), "w") as x:
            x.write(snippet)

        Project.set(Project(project_dir))
        compiler.do_compile()

    def run_file(self, filename):
        with open(filename, "r") as f:
            self.run_snippet(f.read())


def test_snippets():
    """ Test all code snippets in *.snip files"""
    fixture = CompilerFixture()
    for i in glob.glob("*.snip"):
        try:
            fixture.run_file(i)
        except Exception as e:
            print("=" * 20)
            print(i)
            print(e)
            print("=" * 20)


if __name__ == '__main__':
    test_snippets()
