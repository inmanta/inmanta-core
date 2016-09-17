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


from _io import StringIO
import logging
import os
import shutil
import subprocess
import tempfile
import unittest

from inmanta import module
from inmanta.config import Config
from inmanta.module import ModuleTool, Project, LocalFileRepo, RemoteRepo, gitprovider, INSTALL_MASTER, INSTALL_PRERELEASES
from inmanta.ast import CompilerException, ModuleNotFoundException
import pytest
import ruamel.yaml


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
        projectfile.write("\nversion: 0.0.1")

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


def addFile(modpath, file, content, msg, version=None):
    with open(os.path.join(modpath, file), "w") as projectfile:
        projectfile.write(content)

    if version is None:
        return commitmodule(modpath, msg)
    else:
        ocd = os.curdir
        os.curdir = modpath
        subprocess.check_output(["git", "add", "*"], cwd=modpath, stderr=subprocess.STDOUT)
        ModuleTool().commit(msg, version, False, True)
        os.curdir = ocd


def addFileAndCompilerConstraint(modpath, file, content, msg, version, compiler_version):
    cfgfile = os.path.join(modpath, "module.yml")
    with open(cfgfile, "r") as fd:
        cfg = ruamel.yaml.load(fd.read(), ruamel.yaml.RoundTripLoader)

    cfg["compiler_version"] = compiler_version

    with open(cfgfile, "w") as fd:
        fd.write(ruamel.yaml.dump(cfg, Dumper=ruamel.yaml.RoundTripDumper))
    addFile(modpath, file, content, msg, version)


def commitmodule(modpath, mesg):
    subprocess.check_output(["git", "add", "*"], cwd=modpath, stderr=subprocess.STDOUT)
    subprocess.check_output(["git", "commit", "-a", "-m", mesg], cwd=modpath, stderr=subprocess.STDOUT)
    rev = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=modpath, stderr=subprocess.STDOUT).decode("utf-8") .strip()
    return rev


def startbranch(modpath, branch):
    subprocess.check_output(["git", "checkout", "-b", branch], cwd=modpath, stderr=subprocess.STDOUT)


def addTag(modpath, tag):
    subprocess.check_output(["git", "tag", tag], cwd=modpath, stderr=subprocess.STDOUT)


class testModuleTool(unittest.TestCase):
    tempdir = None

    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)

        self.stream = None
        self.handler = None
        self.log = None

    @classmethod
    def setUpClass(cls):
        super(testModuleTool, cls).setUpClass()
        cls.tempdir = tempfile.mkdtemp()

        reporoot = os.path.join(cls.tempdir, "repos")
        cls.reporoot = reporoot
        os.makedirs(reporoot)

        std = makemodule(reporoot, "std", [])
        commitmodule(std, "first commit")
        addFile(std, "signal", "present", "second commit", version="3.2")

        mod1 = makemodule(reporoot, "mod1", [("mod3", "~=0.1")])
        commitmodule(mod1, "first commit")
        addFile(mod1, "signal", "present", "second commit", version="3.2")

        mod2 = makemodule(reporoot, "mod2", [])
        commitmodule(mod2, "first commit")
        addFile(mod2, "signal", "present", "second commit", version="2106.1")

        mod3 = makemodule(reporoot, "mod3", [])
        commitmodule(mod3, "first commit")
        addFile(mod3, "signal", "present", "second commit", version="0.1")
        addFile(mod3, "badsignal", "present", "third commit")

        mod4 = makemodule(reporoot, "badmod", [("mod2", "<2016")])
        commitmodule(mod4, "first commit")
        addFile(mod4, "signal", "present", "second commit", version="0.1")
        addFile(mod4, "badsignal", "present", "third commit")

        mod5 = makemodule(reporoot, "mod5", [])
        commitmodule(mod5, "first commit")
        addFile(mod5, "signal", "present", "second commit", version="0.1")
        addFile(mod5, "badsignal", "present", "third commit")

        mod6 = makemodule(reporoot, "mod6", [])
        commitmodule(mod6, "first commit")
        addFile(mod6, "signal", "present", "second commit", version="3.2")
        addFile(mod6, "badsignal", "present", "third commit")

        mod7 = makemodule(reporoot, "mod7", [])
        commitmodule(mod7, "first commit")
        addFile(mod7, "nsignal", "present", "second commit", version="3.2")
        addFile(mod7, "nsignal", "present", "third commit", version="3.2.1")
        addFile(mod7, "signal", "present", "fourth commit", version="3.2.2")
        addFileAndCompilerConstraint(mod7, "badsignal", "present", "fifth commit", version="4.0", compiler_version="1000000.4")
        addFile(mod7, "badsignal", "present", "sixth commit", version="4.1")
        addFileAndCompilerConstraint(mod7, "badsignal", "present", "fifth commit", version="4.2", compiler_version="1000000.5")
        addFile(mod7, "badsignal", "present", "sixth commit", version="4.3")

        mod8 = makemodule(reporoot, "mod8", [])
        commitmodule(mod8, "first commit")
        addFile(mod8, "signal", "present", "second commit", version="3.2")
        addFile(mod8, "devsignal", "present", "third commit", version="3.3.dev2")
        addFile(mod8, "mastersignal", "present", "last commit")

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

    @classmethod
    def tearDownClass(cls):
        super(testModuleTool, cls).tearDownClass()
        shutil.rmtree(cls.tempdir)

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
        assert result == gitprovider.get_file_for_version(os.path.join(testModuleTool.reporoot, "mod6"), "3.2", "module.yml")

    def test_localRepo_good(self):
        repo = LocalFileRepo(testModuleTool.reporoot)
        coroot = os.path.join(testModuleTool.tempdir, "clone_local_good")
        result = repo.clone("mod1", coroot)
        assert result
        assert os.path.exists(os.path.join(coroot, "mod1", "module.yml"))

    def test_remoteRepo_good(self):
        repo = RemoteRepo("https://github.com/rmccue/")
        coroot = os.path.join(testModuleTool.tempdir, "clone_remote_good")
        result = repo.clone("test-repository", coroot)
        assert result
        assert os.path.exists(os.path.join(coroot, "test-repository", "README"))

    def test_localRepo_bad(self):
        repo = LocalFileRepo(testModuleTool.reporoot)
        coroot = os.path.join(testModuleTool.tempdir, "clone_local_good")
        result = repo.clone("thatotherthing", coroot)
        assert not result

    def test_BadCheckout(self):
        coroot = os.path.join(testModuleTool.tempdir, "badproject")
        subprocess.check_output(["git", "clone", os.path.join(testModuleTool.tempdir, "repos", "badproject")],
                                cwd=testModuleTool.tempdir, stderr=subprocess.STDOUT)
        os.chdir(coroot)
        os.curdir = coroot
        Config.load_config()

        with pytest.raises(ModuleNotFoundException):
            ModuleTool().execute("install", [])

    def test_BadSetup(self):
        coroot = os.path.join(testModuleTool.tempdir, "badprojectx")
        subprocess.check_output(["git", "clone", os.path.join(testModuleTool.tempdir, "repos", "badproject"), coroot],
                                cwd=testModuleTool.tempdir, stderr=subprocess.STDOUT)
        os.chdir(coroot)
        os.curdir = coroot
        Config.load_config()

        mod1 = os.path.join(coroot, "libs", "mod1")
        os.makedirs(mod1)
        subprocess.check_output(["git", "clone", os.path.join(testModuleTool.tempdir, "repos", "mod2"), mod1],
                                cwd=testModuleTool.tempdir, stderr=subprocess.STDOUT)

        with pytest.raises(ModuleNotFoundException):
            ModuleTool().execute("verify", [])

    def test_complexCheckout(self):
        coroot = os.path.join(testModuleTool.tempdir, "testproject")
        subprocess.check_output(["git", "clone", os.path.join(testModuleTool.tempdir, "repos", "testproject")],
                                cwd=testModuleTool.tempdir, stderr=subprocess.STDOUT)
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

    def test_badDepCheckout(self):
        coroot = os.path.join(testModuleTool.tempdir, "baddep")
        subprocess.check_output(["git", "clone", os.path.join(testModuleTool.tempdir, "repos", "baddep")],
                                cwd=testModuleTool.tempdir, stderr=subprocess.STDOUT)
        os.chdir(coroot)
        os.curdir = coroot
        Config.load_config()

        with pytest.raises(CompilerException):
            ModuleTool().execute("install", [])

    def test_MasterCheckout(self):
        coroot = os.path.join(testModuleTool.tempdir, "masterproject")
        subprocess.check_output(["git", "clone", os.path.join(testModuleTool.tempdir, "repos", "masterproject")],
                                cwd=testModuleTool.tempdir, stderr=subprocess.STDOUT)
        os.chdir(coroot)
        os.curdir = coroot
        Config.load_config()

        ModuleTool().execute("install", [])

        dirname = os.path.join(coroot, "libs", "mod8")
        assert os.path.exists(os.path.join(dirname, "devsignal"))
        assert os.path.exists(os.path.join(dirname, "mastersignal"))

    def test_DevCheckout(self):
        coroot = os.path.join(testModuleTool.tempdir, "devproject")
        subprocess.check_output(["git", "clone", os.path.join(testModuleTool.tempdir, "repos", "devproject")],
                                cwd=testModuleTool.tempdir, stderr=subprocess.STDOUT)
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
