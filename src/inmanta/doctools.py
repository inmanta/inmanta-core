"""
    Copyright 2017 Inmanta

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
import uuid
import sys

from inmanta.module import Project
import inmanta.compiler as compiler
from inmanta.config import Config


class CompilerFixture(object):

    def __init__(self):
        self.libs = tempfile.mkdtemp()
        self.env = tempfile.mkdtemp()
        Config.load_config()
        Config.set("config", "environment", str(uuid.uuid4()))

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

    def run_project(self, root):
        project_dir = root
        env = os.path.join(project_dir, ".env")
        if os.path.exists(env):
            os.remove(env)
        os.symlink(self.env, env)

        project = os.path.join(project_dir, "project.yml")
        if os.path.exists(project):
            os.remove(project)
        with open(project, "w") as cfg:
            cfg.write(
                """
            name: snippet test
            modulepath: [libs,%s]
            downloadpath: %s
            version: 1.0
            repo: ['git@git.inmanta.com:modules/', 'git@git.inmanta.com:config/']"""
                % (self.libs, self.libs))

        Project.set(Project(project_dir))
        compiler.do_compile()
        os.remove(project)

    def run_file(self, filename):
        with open(filename, "r") as f:
            self.run_snippet(f.read())


def test_snippets():
    """Test all code snippets in *.snip files."""
    here = os.getcwd()
    fixture = CompilerFixture()
    fail = False
    for i in glob.glob(here + "/*.snip"):
        print("=" * 20)
        print(i)
        try:
            fixture.run_file(i)
        except Exception as e:
            print(e)
            fail = True
        print("=" * 20)

    for i in os.listdir(here):
        try:
            x = os.path.join(here, i)
            print("=" * 20)
            print(x)
            if os.path.isdir(x):
                fixture.run_project(x)
        except Exception as e:
            print(e)
            fail = True
        print("=" * 20)
    return fail

if __name__ == '__main__':
    if not test_snippets():
        sys.exit(1)
