import pytest
from py._path.local import LocalPath
import tempfile
from inmanta.config import Config
import os
import uuid
from inmanta.module import Project
import inmanta.compiler as compiler

shared_env = tempfile.mkdtemp()
shared_libs = tempfile.mkdtemp()

def pytest_collect_file(parent, path):
    if path.ext == ".snip":
        return SnipFile(path, parent)
    if path.basename == "main.cf":
        return SnipDir(LocalPath(path.dirname), parent)

class SnipFile(pytest.File):
    def collect(self):
        name = self.fspath.basename
        spec = self.fspath
        yield SnipFileItem(name, self, spec)
    
class SnipDir(pytest.File):
    def collect(self):
        name = self.fspath.basename
        spec = self.fspath
        yield SnipDirItem(name, self, str(spec))
        
    
class SnipDirItem(pytest.Item):
    def __init__(self, name, parent, filename):
        super(SnipDirItem, self).__init__(name, parent)
        self.filename = filename
        Config.load_config()
        Config.set("config", "environment", str(uuid.uuid4()))  

    def run_project(self, root):
        project_dir = root
        env = os.path.join(project_dir, ".env")
        if os.path.exists(env):
            os.remove(env)
        os.symlink(shared_env, env)

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
            repo: ['https://github.com/inmanta/']
            install_mode: prerelease"""
                % (shared_libs, shared_libs))

        Project.set(Project(project_dir))
        compiler.do_compile()
        os.remove(project)
        
    def runtest(self):
        self.run_project(self.filename)
    
class SnipFileItem(pytest.Item):
    def __init__(self, name, parent, filename):
        super(SnipFileItem, self).__init__(name, parent)
        self.filename = filename
        Config.load_config()
        Config.set("config", "environment", str(uuid.uuid4()))
        
    def run_snippet(self, snippet):
        project_dir = tempfile.mkdtemp()
        os.symlink(shared_env, os.path.join(project_dir, ".env"))

        with open(os.path.join(project_dir, "project.yml"), "w") as cfg:
            cfg.write(
                """
            name: snippet test
            modulepath: %s
            downloadpath: %s
            version: 1.0
            repo: ['https://github.com/inmanta/']
            install_mode: prerelease
            """
                % (shared_libs, shared_libs))

        with open(os.path.join(project_dir, "main.cf"), "w") as x:
            x.write(snippet)

        Project.set(Project(project_dir))
        compiler.do_compile()

    def runtest(self):
        self.run_snippet(self.filename.read())