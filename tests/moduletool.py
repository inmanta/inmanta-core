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

    Contact: wouter@inmanta.com
"""

from impera import app
from impera import module
from _io import StringIO

import os
import logging
import unittest
import shutil

from nose.tools import raises, assert_equal, assert_true
import tempfile
import subprocess
from impera.module import ModuleTool, InvalidModuleException, Project
from impera.config import Config
import yaml


def makemodule(reporoot, name, deps, project=False):
    path = os.path.join(reporoot, name)
    os.makedirs(path)
    mainfile = "module.yml"

    if project:
        mainfile = "project.yml"

    with open(os.path.join(path, mainfile), "w") as projectfile:
        projectfile.write("name: " + name)
        projectfile.write("\nlicense: Apache 2.0")
        projectfile.write("\nversion: 1.0")

        if project:
            projectfile.write("""
modulepath: libs
downloadpath: libs""")

        if len(deps) != 0:
            projectfile.write("\nrequires:")
            for req in deps:
                if len(req) == 2:
                    mypath = os.path.join(reporoot, req[0])
                else:
                    mypath = os.path.join(reporoot, req[2])
                if req[1] != None:
                    projectfile.write("\n    {}: {}, {}".format(req[0], mypath, req[1]))
                else:
                    projectfile.write("\n    {}: {}".format(req[0], mypath, req[1]))

        projectfile.write("\n")

    model = os.path.join(path, "model")
    os.makedirs(model)

    with open(os.path.join(model, "_init.cf"), "w") as projectfile:
        pass

    subprocess.check_output(["git", "init"], cwd=path)

    return path


def addFile(modpath, file, content, msg):
    with open(os.path.join(modpath, file), "w") as projectfile:
        projectfile.write(content)
    return commitmodule(modpath, msg)


def commitmodule(modpath, mesg):
    subprocess.check_output(["git", "add", "*"], cwd=modpath)
    subprocess.check_output(["git", "commit", "--author=Tester <tester@inmanta.com>","-a", "-m", mesg], cwd=modpath)
    rev = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=modpath).decode("utf-8") .strip()
    return rev


def startbranch(modpath, branch):
    subprocess.check_output(["git", "checkout", "-b", branch], cwd=modpath, stderr=subprocess.STDOUT)


def addTag(modpath, tag):
    subprocess.check_output(["git", "tag", tag], cwd=modpath)


class testModuleTool(unittest.TestCase):
    tempdir = None
    goodIds = {}

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
        os.makedirs(reporoot)

        mod1 = makemodule(reporoot, "mod1", [("mod3", "")])
        commitmodule(mod1, "first commit")
        cls.goodIds["mod1"] = addFile(mod1, "signal", "present", "second commit")

        mod2 = makemodule(reporoot, "mod2", [])
        commitmodule(mod2, "first commit")
        startbranch(mod2, "rc1")
        cls.goodIds["mod2"] = addFile(mod2, "signal", "present", "second commit")

        mod3 = makemodule(reporoot, "mod3", [])
        commitmodule(mod3, "first commit")
        cls.goodIds["mod3"] = addFile(mod3, "signal", "present", "second commit")
        addTag(mod3, "0.1")
        addFile(mod3, "badsignal", "present", "third commit")

        mod4 = makemodule(reporoot, "mod4", [])
        commitmodule(mod4, "first commit")
        m4tag = addFile(mod4, "signal", "present", "second commit")
        cls.goodIds["mod4"] = m4tag
        addFile(mod4, "badsignal", "present", "third commit")

        mod5 = makemodule(reporoot, "mod5", [])
        commitmodule(mod5, "first commit")
        m5tag = addFile(mod5, "signal", "present", "second commit")
        cls.goodIds["mod5"] = m5tag
        addTag(mod5, "0.1")
        addFile(mod5, "badsignal", "present", "third commit")

        proj = makemodule(reporoot, "testproject",
                          [("mod1", None), ("mod2", "rc1"), ("mod3", "0.1"), ("mod4", m4tag), ("mod5", "0.1")], True)
        commitmodule(proj, "first commit")

        badproject = makemodule(reporoot, "badproject", [("mod1", "", "mod2")], True)
        commitmodule(badproject, "first commit")

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

    @raises(InvalidModuleException)
    def test_BadCheckout(self):
        coroot = os.path.join(testModuleTool.tempdir, "badproject")
        subprocess.check_output(["git", "clone", os.path.join(testModuleTool.tempdir, "repos", "badproject")],
                                cwd=testModuleTool.tempdir, stderr=subprocess.STDOUT)
        os.chdir(coroot)
        os.curdir = coroot
        Config.load_config()

        ModuleTool().execute("install", [])

    @raises(InvalidModuleException)
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

        ModuleTool().execute("verify", [])

    def test_complexCheckoutAndFreeze(self):
        coroot = os.path.join(testModuleTool.tempdir, "testproject")
        subprocess.check_output(["git", "clone", os.path.join(testModuleTool.tempdir, "repos", "testproject")],
                                cwd=testModuleTool.tempdir, stderr=subprocess.STDOUT)
        os.chdir(coroot)
        os.curdir = coroot
        Config.load_config()

        ModuleTool().execute("install", [])
        for i in ["mod1", "mod2", "mod3", "mod4"]:
            dir = os.path.join(coroot, "libs", i)
            assert_true(os.path.exists(os.path.join(dir, "signal")),
                        "could not find file: " + (os.path.join(dir, "signal")))
            assert_true(not os.path.exists(os.path.join(dir, "badsignal")),
                        "did find file: " + (os.path.join(dir, "badsignal")))

        ModuleTool().execute("freeze", [])
        assert_true(os.path.exists(os.path.join(coroot, "module.version")),
                    "could not find file: " + (os.path.join(coroot, "module.version")))

        with open(os.path.join(coroot, "module.version"), "r") as fd:
            locked = yaml.load(fd)

        reporoot = os.path.join(testModuleTool.tempdir, "repos")

        def checkmodule(name, branch):
            other = locked[name]
            assert_equal(other["hash"], testModuleTool.goodIds[name], "bad hash on module " + name)
            assert_equal(other["version"], "1.0", "bad version on module " + name)
            assert_equal(other["branch"], branch, "bad branch on module " + name)
            assert_equal(other["repo"], os.path.join(reporoot, name), "bad repo on module " + name)

        checkmodule("mod1", 'master')
        checkmodule("mod2", 'rc1')
        checkmodule("mod3", 'HEAD')
        checkmodule("mod4", 'HEAD')

    def tearDown(self):
        self.log.removeHandler(self.handler)
        self.handler.close()
