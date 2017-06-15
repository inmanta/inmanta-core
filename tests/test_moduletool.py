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


from _io import StringIO
import logging
import os
import shutil
import subprocess
import tempfile
import unittest
from subprocess import CalledProcessError
import re

from inmanta import module
from inmanta.config import Config
from inmanta.module import ModuleTool, Project, LocalFileRepo, RemoteRepo, gitprovider, INSTALL_MASTER, INSTALL_PRERELEASES
from inmanta.ast import CompilerException, ModuleNotFoundException
import pytest
import yaml
from pkg_resources import parse_version


def makemodule(reporoot, name, deps=[], project=False, imports=None, install_mode=None):
    path = os.path.join(reporoot, name)
    os.makedirs(path)
    mainfile = "module.yml"

    if project:
        mainfile = "project.yml"

    if imports is None:
        imports = [x[0] for x in deps]

    with open(os.path.join(path, mainfile), "w") as projectfile:
        projectfile.write("name: " + name)
        projectfile.write("\nlicense: Apache 2.0")
        projectfile.write("\nversion: '0.0.1'")

        if project:
            projectfile.write("""
modulepath: libs
downloadpath: libs
repo: %s""" % reporoot)

        if install_mode is not None:
            projectfile.write("\ninstall_mode: %s" % install_mode)
        if len(deps) != 0:
            projectfile.write("\nrequires:")
            for req in deps:
                if req[1] is not None:
                    projectfile.write("\n    - {} {}".format(req[0], req[1]))
                else:
                    projectfile.write("\n    - {}".format(req[0]))

        projectfile.write("\n")

    model = os.path.join(path, "model")
    os.makedirs(model)

    if not project:
        with open(os.path.join(model, "_init.cf"), "w") as projectfile:
            for i in imports:
                projectfile.write("import %s\n" % i)
    else:
        with open(os.path.join(path, "main.cf"), "w") as projectfile:
            for i in imports:
                projectfile.write("import %s\n" % i)

    subprocess.check_output(["git", "init"], cwd=path, stderr=subprocess.STDOUT)
    subprocess.check_output(["git", "config", "user.email", '"test@test.example"'], cwd=path, stderr=subprocess.STDOUT)
    subprocess.check_output(["git", "config", "user.name", 'Tester test'], cwd=path, stderr=subprocess.STDOUT)

    return path


def add_file(modpath, file, content, msg, version=None):
    with open(os.path.join(modpath, file), "w") as projectfile:
        projectfile.write(content)

    if version is None:
        return commitmodule(modpath, msg)
    else:
        ocd = os.curdir
        os.curdir = modpath
        subprocess.check_output(["git", "add", "*"], cwd=modpath, stderr=subprocess.STDOUT)
        ModuleTool().commit(msg, version=version, dev=False, commit_all=True)
        os.curdir = ocd


def add_file_and_compiler_constraint(modpath, file, content, msg, version, compiler_version):
    cfgfile = os.path.join(modpath, "module.yml")
    with open(cfgfile, "r") as fd:
        cfg = yaml.safe_load(fd)

    cfg["compiler_version"] = compiler_version

    with open(cfgfile, "w") as fd:
        yaml.dump(cfg, fd)
    add_file(modpath, file, content, msg, version)


def commitmodule(modpath, mesg):
    subprocess.check_output(["git", "add", "*"], cwd=modpath, stderr=subprocess.STDOUT)
    subprocess.check_output(["git", "commit", "-a", "-m", mesg], cwd=modpath, stderr=subprocess.STDOUT)
    rev = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=modpath, stderr=subprocess.STDOUT).decode("utf-8") .strip()
    return rev


def startbranch(modpath, branch):
    subprocess.check_output(["git", "checkout", "-b", branch], cwd=modpath, stderr=subprocess.STDOUT)


def add_tag(modpath, tag):
    subprocess.check_output(["git", "tag", tag], cwd=modpath, stderr=subprocess.STDOUT)


class BadModProvider(object):

    def __init__(self, parent, badname):
        self.parent = parent
        self.badname = badname

    def __getattr__(self, method_name):
        def delegator(*args, **kw):
            if args[0] == self.badname:
                raise CalledProcessError(128, "XX")
            return getattr(self.parent, method_name)(*args, **kw)
        return delegator


class TestModuleTool(unittest.TestCase):
    tempdir = None

    def __init__(self, methodName='runTest'):  # noqa: H803
        unittest.TestCase.__init__(self, methodName)

        self.stream = None
        self.handler = None
        self.log = None

    @classmethod
    def setUpClass(cls):
        super(TestModuleTool, cls).setUpClass()
        cls.oldcwd = os.getcwd()
        cls.tempdir = tempfile.mkdtemp()

        reporoot = os.path.join(cls.tempdir, "repos")
        cls.reporoot = reporoot
        os.makedirs(reporoot)

        std = makemodule(reporoot, "std", [])
        commitmodule(std, "first commit")
        add_file(std, "signal", "present", "second commit", version="3.2")

        mod1 = makemodule(reporoot, "mod1", [("mod3", "~=0.1")])
        commitmodule(mod1, "first commit")
        add_file(mod1, "signal", "present", "second commit", version="3.2")

        mod2 = makemodule(reporoot, "mod2", [])
        commitmodule(mod2, "first commit")
        add_file(mod2, "signal", "present", "second commit", version="2016.1")

        mod3 = makemodule(reporoot, "mod3", [])
        commitmodule(mod3, "first commit")
        add_file(mod3, "signal", "present", "second commit", version="0.1")
        add_file(mod3, "badsignal", "present", "third commit")

        mod4 = makemodule(reporoot, "badmod", [("mod2", "<2016")])
        commitmodule(mod4, "first commit")
        add_file(mod4, "signal", "present", "second commit", version="0.1")
        add_file(mod4, "badsignal", "present", "third commit")

        mod5 = makemodule(reporoot, "mod5", [])
        commitmodule(mod5, "first commit")
        add_file(mod5, "signal", "present", "second commit", version="0.1")
        add_file(mod5, "badsignal", "present", "third commit")

        mod6 = makemodule(reporoot, "mod6", [])
        commitmodule(mod6, "first commit")
        add_file(mod6, "signal", "present", "second commit", version="3.2")
        add_file(mod6, "badsignal", "present", "third commit")

        mod7 = makemodule(reporoot, "mod7", [])
        commitmodule(mod7, "first commit")
        add_file(mod7, "nsignal", "present", "second commit", version="3.2")
        add_file(mod7, "nsignal", "present", "third commit", version="3.2.1")
        add_file(mod7, "signal", "present", "fourth commit", version="3.2.2")
        add_file_and_compiler_constraint(mod7, "badsignal", "present", "fifth commit",
                                         version="4.0", compiler_version="1000000.4")
        add_file(mod7, "badsignal", "present", "sixth commit", version="4.1")
        add_file_and_compiler_constraint(mod7, "badsignal", "present", "fifth commit",
                                         version="4.2", compiler_version="1000000.5")
        add_file(mod7, "badsignal", "present", "sixth commit", version="4.3")

        mod8 = makemodule(reporoot, "mod8", [])
        commitmodule(mod8, "first commit")
        add_file(mod8, "signal", "present", "second commit", version="3.2")
        add_file(mod8, "devsignal", "present", "third commit", version="3.3.dev2")
        add_file(mod8, "mastersignal", "present", "last commit")

        proj = makemodule(reporoot, "testproject",
                          [("mod1", None), ("mod2", ">2016"), ("mod5", None)], True, ["mod1", "mod2", "mod6", "mod7"])
        # results in loading of 1,2,3,6
        commitmodule(proj, "first commit")

        badproject = makemodule(reporoot, "badproject", [("mod15", None)], True)
        commitmodule(badproject, "first commit")

        baddep = makemodule(reporoot, "baddep", [("badmod", None), ("mod2", ">2016")], True)
        commitmodule(baddep, "first commit")

        devproject = makemodule(reporoot, "devproject", project=True, imports=["mod8"], install_mode=INSTALL_PRERELEASES)
        commitmodule(devproject, "first commit")

        masterproject = makemodule(reporoot, "masterproject", project=True, imports=["mod8"], install_mode=INSTALL_MASTER)
        commitmodule(masterproject, "first commit")

        nover = makemodule(reporoot, "nover", [])
        commitmodule(nover, "first commit")
        add_file(nover, "signal", "present", "second commit")

        noverproject = makemodule(reporoot, "noverproject", project=True, imports=["nover"])
        commitmodule(noverproject, "first commit")

    @classmethod
    def tearDownClass(cls):
        super(TestModuleTool, cls).tearDownClass()
        shutil.rmtree(cls.tempdir)
        os.chdir(cls.oldcwd)

    def setUp(self):
        self.stream = StringIO()
        self.handler = logging.StreamHandler(self.stream)
        self.log = logging.getLogger(module.__name__)

        for handler in self.log.handlers:
            self.log.removeHandler(handler)

        self.log.addHandler(self.handler)

        Project._project = None

    def test_file_co(self):
        result = """name: mod6
license: Apache 2.0
version: '3.2'
"""
        module_yaml = gitprovider.get_file_for_version(os.path.join(TestModuleTool.reporoot, "mod6"), "3.2", "module.yml")
        assert result == module_yaml

    def test_local_repo_good(self):
        repo = LocalFileRepo(TestModuleTool.reporoot)
        coroot = os.path.join(TestModuleTool.tempdir, "clone_local_good")
        result = repo.clone("mod1", coroot)
        assert result
        assert os.path.exists(os.path.join(coroot, "mod1", "module.yml"))

    def test_remote_repo_good(self):
        repo = RemoteRepo("https://github.com/rmccue/")
        coroot = os.path.join(TestModuleTool.tempdir, "clone_remote_good")
        result = repo.clone("test-repository", coroot)
        assert result
        assert os.path.exists(os.path.join(coroot, "test-repository", "README"))

    def test_local_repo_bad(self):
        repo = LocalFileRepo(TestModuleTool.reporoot)
        coroot = os.path.join(TestModuleTool.tempdir, "clone_local_good")
        result = repo.clone("thatotherthing", coroot)
        assert not result

    def test_bad_checkout(self):
        coroot = os.path.join(TestModuleTool.tempdir, "badproject")
        subprocess.check_output(["git", "clone", os.path.join(TestModuleTool.tempdir, "repos", "badproject")],
                                cwd=TestModuleTool.tempdir, stderr=subprocess.STDOUT)
        os.chdir(coroot)
        os.curdir = coroot
        Config.load_config()

        with pytest.raises(ModuleNotFoundException):
            ModuleTool().execute("install", [])

    def test_bad_setup(self):
        coroot = os.path.join(TestModuleTool.tempdir, "badprojectx")
        subprocess.check_output(["git", "clone", os.path.join(TestModuleTool.tempdir, "repos", "badproject"), coroot],
                                cwd=TestModuleTool.tempdir, stderr=subprocess.STDOUT)
        os.chdir(coroot)
        os.curdir = coroot
        Config.load_config()

        mod1 = os.path.join(coroot, "libs", "mod1")
        os.makedirs(mod1)
        subprocess.check_output(["git", "clone", os.path.join(TestModuleTool.tempdir, "repos", "mod2"), mod1],
                                cwd=TestModuleTool.tempdir, stderr=subprocess.STDOUT)

        with pytest.raises(ModuleNotFoundException):
            ModuleTool().execute("verify", [])

    def test_complex_checkout(self):
        coroot = os.path.join(TestModuleTool.tempdir, "testproject")
        subprocess.check_output(["git", "clone", os.path.join(TestModuleTool.tempdir, "repos", "testproject")],
                                cwd=TestModuleTool.tempdir, stderr=subprocess.STDOUT)
        os.chdir(coroot)
        os.curdir = coroot
        Config.load_config()

        ModuleTool().execute("install", [])
        expected = ["mod1", "mod2", "mod3", "mod6", "mod7"]
        for i in expected:
            dirname = os.path.join(coroot, "libs", i)
            assert os.path.exists(os.path.join(dirname, "signal"))
            assert not os.path.exists(os.path.join(dirname, "badsignal"))

        assert not os.path.exists(os.path.join(coroot, "libs", "mod5"))

        # test all tools, perhaps isolate to other test case
        ModuleTool().execute("list", [])
        ModuleTool().execute("update", [])
        ModuleTool().execute("status", [])
        ModuleTool().execute("push", [])

    def test_for_git_failures(self):
        coroot = os.path.join(TestModuleTool.tempdir, "testproject2")
        subprocess.check_output(["git", "clone", os.path.join(TestModuleTool.tempdir, "repos", "testproject"), "testproject2"],
                                cwd=TestModuleTool.tempdir, stderr=subprocess.STDOUT)
        os.chdir(coroot)
        os.curdir = coroot
        Config.load_config()

        ModuleTool().execute("install", [])

        gp = module.gitprovider
        module.gitprovider = BadModProvider(gp, os.path.join(coroot, "libs", "mod6"))
        try:
            # test all tools, perhaps isolate to other test case
            ModuleTool().execute("install", [])
            ModuleTool().execute("list", [])
            ModuleTool().execute("update", [])
            ModuleTool().execute("status", [])
            ModuleTool().execute("push", [])
        finally:
            module.gitprovider = gp

    def test_install_for_git_failures(self):
        coroot = os.path.join(TestModuleTool.tempdir, "testproject3")
        subprocess.check_output(["git", "clone", os.path.join(TestModuleTool.tempdir, "repos", "testproject"), "testproject3"],
                                cwd=TestModuleTool.tempdir, stderr=subprocess.STDOUT)
        os.chdir(coroot)
        os.curdir = coroot
        Config.load_config()

        gp = module.gitprovider
        module.gitprovider = BadModProvider(gp, os.path.join(coroot, "libs", "mod6"))
        try:
            with pytest.raises(ModuleNotFoundException):
                ModuleTool().execute("install", [])
        finally:
            module.gitprovider = gp

    def test_for_repo_without_versions(self):
        coroot = os.path.join(TestModuleTool.tempdir, "noverproject")
        subprocess.check_output(["git", "clone", os.path.join(TestModuleTool.tempdir, "repos", "noverproject")],
                                cwd=TestModuleTool.tempdir, stderr=subprocess.STDOUT)
        os.chdir(coroot)
        os.curdir = coroot
        Config.load_config()

        ModuleTool().execute("install", [])

    def test_bad_dep_checkout(self):
        coroot = os.path.join(TestModuleTool.tempdir, "baddep")
        subprocess.check_output(["git", "clone", os.path.join(TestModuleTool.tempdir, "repos", "baddep")],
                                cwd=TestModuleTool.tempdir, stderr=subprocess.STDOUT)
        os.chdir(coroot)
        os.curdir = coroot
        Config.load_config()

        with pytest.raises(CompilerException):
            ModuleTool().execute("install", [])

    def test_master_checkout(self):
        coroot = os.path.join(TestModuleTool.tempdir, "masterproject")
        subprocess.check_output(["git", "clone", os.path.join(TestModuleTool.tempdir, "repos", "masterproject")],
                                cwd=TestModuleTool.tempdir, stderr=subprocess.STDOUT)
        os.chdir(coroot)
        os.curdir = coroot
        Config.load_config()

        ModuleTool().execute("install", [])

        dirname = os.path.join(coroot, "libs", "mod8")
        assert os.path.exists(os.path.join(dirname, "devsignal"))
        assert os.path.exists(os.path.join(dirname, "mastersignal"))

    def test_dev_checkout(self):
        coroot = os.path.join(TestModuleTool.tempdir, "devproject")
        subprocess.check_output(["git", "clone", os.path.join(TestModuleTool.tempdir, "repos", "devproject")],
                                cwd=TestModuleTool.tempdir, stderr=subprocess.STDOUT)
        os.chdir(coroot)
        os.curdir = coroot
        Config.load_config()

        ModuleTool().execute("install", [])

        dirname = os.path.join(coroot, "libs", "mod8")
        assert os.path.exists(os.path.join(dirname, "devsignal"))
        assert not os.path.exists(os.path.join(dirname, "mastersignal"))

    def tearDown(self):
        self.log.removeHandler(self.handler)
        self.handler.close()


def test_versioning():
    mt = ModuleTool()

    newversion = mt.determine_new_version(parse_version("1.2.3"), None, False, False, True, False)
    assert str(newversion) == "1.2.4"
    newversion = mt.determine_new_version(parse_version("1.2.3"), None, False, True, False, False)
    assert str(newversion) == "1.3.0"
    newversion = mt.determine_new_version(parse_version("1.2.3"), None, True, False, False, False)
    assert str(newversion) == "2.0.0"
    newversion = mt.determine_new_version(parse_version("1.2.3"), None, True, True, False, False)
    assert newversion is None
    newversion = mt.determine_new_version(parse_version("1.2.3"), None, True, False, True, False)
    assert newversion is None
    newversion = mt.determine_new_version(parse_version("1.2.3"), None, True, True, True, False)
    assert newversion is None
    newversion = mt.determine_new_version(parse_version("1.2.3.dev025"), None, False, False, True, False)
    assert str(newversion) == "1.2.3"
    newversion = mt.determine_new_version(parse_version("1.2.3.dev025"), None, False, False, False, False)
    assert str(newversion) == "1.2.3"

    newversion = mt.determine_new_version(parse_version("1.2.3"), None, False, False, True, True)
    assert re.search("1.2.4.dev[0-9]+", str(newversion))
    newversion = mt.determine_new_version(parse_version("1.2.3"), None, False, True, False, True)
    assert re.search("1.3.0.dev[0-9]+", str(newversion))
    newversion = mt.determine_new_version(parse_version("1.2.3"), None, True, False, False, True)
    assert re.search("2.0.0.dev[0-9]+", str(newversion))
    newversion = mt.determine_new_version(parse_version("1.2.3"), None, True, True, False, True)
    assert newversion is None
    newversion = mt.determine_new_version(parse_version("1.2.3"), None, True, False, True, True)
    assert newversion is None
    newversion = mt.determine_new_version(parse_version("1.2.3"), None, True, True, True, True)
    assert newversion is None
    newversion = mt.determine_new_version(parse_version("1.2.3.dev025"), None, False, False, True, True)
    assert re.search("1.2.3.dev[0-9]+", str(newversion))
    newversion = mt.determine_new_version(parse_version("1.2.3.dev025"), None, False, False, False, True)
    assert re.search("1.2.3.dev[0-9]+", str(newversion))


def test_rewrite(tmpdir):
    module_path = tmpdir.join("mod").mkdir()
    model = module_path.join("model").mkdir()
    model.join("_init.cf").write("\n")

    module_yml = module_path.join("module.yml")
    module_yml.write("""
name: mod
license: ASL
version: 1.2
compiler_version: 2017.2
    """)

    mod = module.Module(None, module_path.strpath)

    assert mod.version == "1.2"
    assert mod.compiler_version == "2017.2"

    mod.rewrite_version("1.3.1")
    assert mod.version == "1.3.1"
    assert mod.compiler_version == "2017.2"
