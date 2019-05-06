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

import os
import shutil
import subprocess
import tempfile
from subprocess import CalledProcessError
import re

from inmanta import module
from inmanta.config import Config
from inmanta.module import LocalFileRepo, RemoteRepo, gitprovider, INSTALL_MASTER, INSTALL_PRERELEASES
from inmanta.ast import CompilerException, ModuleNotFoundException
import pytest
import yaml
from pkg_resources import parse_version
from inmanta.moduletool import ModuleTool
from test_app_cli import app
from inmanta.command import CLIException


def makemodule(reporoot, name, deps=[], project=False, imports=None, install_mode=None, options=""):
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


def make_module_simple(reporoot, name, depends=[], version="3.2", project=False):
    mod = makemodule(reporoot, name, depends, project=project)
    commitmodule(mod, "first commit")
    if not project:
        add_file(mod, "signal", "present", "second commit", version=version)
    return mod


def make_module_simple_deps(reporoot, name, depends=[], project=False, version="3.2"):
    return make_module_simple(reporoot, "mod" + name, [("mod" + x, None) for x in depends], project=project, version=version)


def install_project(modules_dir, name, config=True):
    subroot = tempfile.mkdtemp()
    coroot = os.path.join(subroot, name)
    subprocess.check_output(["git", "clone", os.path.join(modules_dir, "repos", name)],
                            cwd=subroot, stderr=subprocess.STDOUT)
    os.chdir(coroot)
    os.curdir = coroot
    if config:
        Config.load_config()
    return coroot


def clone_repo(source_dir, repo_name, destination_dir):
    subprocess.check_output(["git", "clone", os.path.join(source_dir, repo_name)],
                            cwd=destination_dir,
                            stderr=subprocess.STDOUT)
    subprocess.check_output(["git", "config", "user.email", '"test@test.example"'],
                            cwd=os.path.join(destination_dir, repo_name),
                            stderr=subprocess.STDOUT)
    subprocess.check_output(["git", "config", "user.name", 'Tester test'],
                            cwd=os.path.join(destination_dir, repo_name),
                            stderr=subprocess.STDOUT)


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


@pytest.fixture(scope="session")
def modules_dir():
    tempdir = tempfile.mkdtemp()
    yield tempdir
    shutil.rmtree(tempdir)


@pytest.fixture(scope="session")
def modules_repo(modules_dir):
    """
+--------+-------------+----------+
| Name   | Requires    | Versions |
+--------+-------------+----------+
| std    |             | 0.0.1    |
+--------+-------------+----------+
|        |             | 3.2      |
+--------+-------------+----------+
| mod1   | mod3 ~= 0.1 | 0.0.1    |
+--------+-------------+----------+
|        | mod3 ~= 0.1 | 3.2      |
+--------+-------------+----------+
| mod2   |             | 0.0.1    |
+--------+-------------+----------+
|        |             | 2016.1   |
+--------+-------------+----------+
| mod3   |             | 0.0.1    |
+--------+-------------+----------+
|        |             | 0.1      |
+--------+-------------+----------+
| badmod | mod2 < 2016 | 0.0.1    |
+--------+-------------+----------+
|        |             | 0.1      |
+--------+-------------+----------+
| mod5   |             | 0.0.1    |
+--------+-------------+----------+
|        |             | 0.1      |
+--------+-------------+----------+
| mod6   |             | 0.0.1    |
+--------+-------------+----------+
|        |             | 3.2      |
+--------+-------------+----------+
| mod7   |             | 0.0.1    |
+--------+-------------+----------+
|        |             | 3.2      |
+--------+-------------+----------+
|        |             | 3.2.1    |
+--------+-------------+----------+
|        |             | 3.2.2    |
+--------+-------------+----------+
|        |             | 4.0      |
+--------+-------------+----------+
|        |             | 4.2      |
+--------+-------------+----------+
|        |             | 4.3      |
+--------+-------------+----------+
| mod8   |             | 0.0.1    |
+--------+-------------+----------+
|        |             | 3.2      |
+--------+-------------+----------+
|        |             | 3.3.dev  |
+--------+-------------+----------+
"""
    tempdir = modules_dir

    reporoot = os.path.join(tempdir, "repos")
    os.makedirs(reporoot)

    make_module_simple(reporoot, "std")

    make_module_simple(reporoot, "mod1", depends=[("mod3", "~=0.1")])

    make_module_simple(reporoot, "mod2", version="2016.1")

    mod3 = make_module_simple(reporoot, "mod3", version="0.1")
    add_file(mod3, "badsignal", "present", "third commit")

    mod4 = make_module_simple(reporoot, "badmod", [("mod2", "<2016")])
    add_file(mod4, "badsignal", "present", "third commit")

    mod5 = make_module_simple(reporoot, "mod5", version="0.1")
    add_file(mod5, "badsignal", "present", "third commit")

    mod6 = make_module_simple(reporoot, "mod6")
    add_file(mod6, "badsignal", "present", "third commit")

    mod7 = make_module_simple(reporoot, "mod7")
    add_file(mod7, "nsignal", "present", "third commit", version="3.2.1")
    add_file(mod7, "signal", "present", "fourth commit", version="3.2.2")
    add_file_and_compiler_constraint(mod7, "badsignal", "present", "fifth commit",
                                     version="4.0", compiler_version="1000000.4")
    add_file(mod7, "badsignal", "present", "sixth commit", version="4.1")
    add_file_and_compiler_constraint(mod7, "badsignal", "present", "fifth commit",
                                     version="4.2", compiler_version="1000000.5")
    add_file(mod7, "badsignal", "present", "sixth commit", version="4.3")

    mod8 = make_module_simple(reporoot, "mod8", [])
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

    masterproject_multi_mod = makemodule(reporoot,
                                         "masterproject_multi_mod",
                                         project=True,
                                         imports=["mod2", "mod8"],
                                         install_mode=INSTALL_MASTER)
    commitmodule(masterproject_multi_mod, "first commit")

    nover = makemodule(reporoot, "nover", [])
    commitmodule(nover, "first commit")
    add_file(nover, "signal", "present", "second commit")

    noverproject = makemodule(reporoot, "noverproject", project=True, imports=["nover"])
    commitmodule(noverproject, "first commit")

    """
    for freeze, test from C
    A-> B,C,D
    C-> E,F,E::a
    C::a -> I
    E::a -> J
    E-> H
    D-> F,G
    """
    make_module_simple_deps(reporoot, "A", ["B", "C", "D"], project=True)
    make_module_simple_deps(reporoot, "B")
    c = make_module_simple_deps(reporoot, "C", ["E", "F", "E::a"], version="3.0")
    add_file(c, "model/a.cf", "import modI", "add mod C::a", "3.2")
    make_module_simple_deps(reporoot, "D", ["F", "G"])
    e = make_module_simple_deps(reporoot, "E", ["H"], version="3.0")
    add_file(e, "model/a.cf", "import modJ", "add mod E::a", "3.2")
    make_module_simple_deps(reporoot, "F")
    make_module_simple_deps(reporoot, "G")
    make_module_simple_deps(reporoot, "H")
    make_module_simple_deps(reporoot, "I")
    make_module_simple_deps(reporoot, "J")

    return reporoot


def test_file_co(modules_dir, modules_repo):
    result = """name: mod6
license: Apache 2.0
version: '3.2'
"""
    module_yaml = gitprovider.get_file_for_version(os.path.join(modules_repo, "mod6"), "3.2", "module.yml")
    assert result == module_yaml


def test_local_repo_good(modules_dir, modules_repo):
    repo = LocalFileRepo(modules_repo)
    coroot = os.path.join(modules_dir, "clone_local_good")
    result = repo.clone("mod1", coroot)
    assert result
    assert os.path.exists(os.path.join(coroot, "mod1", "module.yml"))


def test_remote_repo_good(modules_dir, modules_repo):
    repo = RemoteRepo("https://github.com/rmccue/")
    coroot = os.path.join(modules_dir, "clone_remote_good")
    result = repo.clone("test-repository", coroot)
    assert result
    assert os.path.exists(os.path.join(coroot, "test-repository", "README"))


def test_local_repo_bad(modules_dir, modules_repo):
    repo = LocalFileRepo(modules_repo)
    coroot = os.path.join(modules_dir, "clone_local_good")
    result = repo.clone("thatotherthing", coroot)
    assert not result


def test_bad_checkout(modules_dir, modules_repo):
    coroot = os.path.join(modules_dir, "badproject")
    subprocess.check_output(["git", "clone", os.path.join(modules_dir, "repos", "badproject")],
                            cwd=modules_dir, stderr=subprocess.STDOUT)
    os.chdir(coroot)
    os.curdir = coroot
    Config.load_config()

    with pytest.raises(ModuleNotFoundException):
        ModuleTool().execute("install", [])


def test_bad_setup(modules_dir, modules_repo):
    coroot = os.path.join(modules_dir, "badprojectx")
    subprocess.check_output(["git", "clone", os.path.join(modules_dir, "repos", "badproject"), coroot],
                            cwd=modules_dir, stderr=subprocess.STDOUT)
    os.chdir(coroot)
    os.curdir = coroot
    Config.load_config()

    mod1 = os.path.join(coroot, "libs", "mod1")
    os.makedirs(mod1)
    subprocess.check_output(["git", "clone", os.path.join(modules_dir, "repos", "mod2"), mod1],
                            cwd=modules_dir, stderr=subprocess.STDOUT)

    with pytest.raises(ModuleNotFoundException):
        ModuleTool().execute("verify", [])


def test_complex_checkout(modules_dir, modules_repo):
    coroot = os.path.join(modules_dir, "testproject")
    subprocess.check_output(["git", "clone", os.path.join(modules_dir, "repos", "testproject")],
                            cwd=modules_dir, stderr=subprocess.STDOUT)
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


def test_for_git_failures(modules_dir, modules_repo):
    coroot = os.path.join(modules_dir, "testproject2")
    subprocess.check_output(["git", "clone", os.path.join(modules_dir, "repos", "testproject"), "testproject2"],
                            cwd=modules_dir, stderr=subprocess.STDOUT)
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


def test_install_for_git_failures(modules_dir, modules_repo):
    coroot = os.path.join(modules_dir, "testproject3")
    subprocess.check_output(["git", "clone", os.path.join(modules_dir, "repos", "testproject"), "testproject3"],
                            cwd=modules_dir, stderr=subprocess.STDOUT)
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


def test_for_repo_without_versions(modules_dir, modules_repo):
    coroot = os.path.join(modules_dir, "noverproject")
    subprocess.check_output(["git", "clone", os.path.join(modules_dir, "repos", "noverproject")],
                            cwd=modules_dir, stderr=subprocess.STDOUT)
    os.chdir(coroot)
    os.curdir = coroot
    Config.load_config()

    ModuleTool().execute("install", [])


def test_bad_dep_checkout(modules_dir, modules_repo):
    coroot = os.path.join(modules_dir, "baddep")
    subprocess.check_output(["git", "clone", os.path.join(modules_dir, "repos", "baddep")],
                            cwd=modules_dir, stderr=subprocess.STDOUT)
    os.chdir(coroot)
    os.curdir = coroot
    Config.load_config()

    with pytest.raises(CompilerException):
        ModuleTool().execute("install", [])


def test_master_checkout(modules_dir, modules_repo):
    coroot = install_project(modules_dir, "masterproject")

    ModuleTool().execute("install", [])

    dirname = os.path.join(coroot, "libs", "mod8")
    assert os.path.exists(os.path.join(dirname, "devsignal"))
    assert os.path.exists(os.path.join(dirname, "mastersignal"))


def test_dev_checkout(modules_dir, modules_repo):
    coroot = os.path.join(modules_dir, "devproject")
    subprocess.check_output(["git", "clone", os.path.join(modules_dir, "repos", "devproject")],
                            cwd=modules_dir, stderr=subprocess.STDOUT)
    os.chdir(coroot)
    os.curdir = coroot
    Config.load_config()

    ModuleTool().execute("install", [])

    dirname = os.path.join(coroot, "libs", "mod8")
    assert os.path.exists(os.path.join(dirname, "devsignal"))
    assert not os.path.exists(os.path.join(dirname, "mastersignal"))


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


def test_freeze_basic(modules_dir, modules_repo):
    install_project(modules_dir, "modA")
    modtool = ModuleTool()
    cmod = modtool.get_module("modC")
    assert cmod.get_freeze("modC", recursive=False, mode="==") == {"std": "== 3.2", "modE": "== 3.2", "modF": "== 3.2"}
    assert cmod.get_freeze("modC", recursive=True, mode="==") == {
        "std": "== 3.2", "modE": "== 3.2", "modF": "== 3.2", "modH": "== 3.2", "modJ": "== 3.2"}

    assert cmod.get_freeze("modC::a", recursive=False, mode="==") == {"std": "== 3.2", "modI": "== 3.2"}


def test_project_freeze_basic(modules_dir, modules_repo):
    install_project(modules_dir, "modA")
    modtool = ModuleTool()
    proj = modtool.get_project()
    assert proj.get_freeze(recursive=False, mode="==") == {"std": "== 3.2",
                                                           "modB": "== 3.2", "modC": "== 3.2", "modD": "== 3.2"}
    assert proj.get_freeze(recursive=True, mode="==") == {
        "std": "== 3.2",
        "modB": "== 3.2",
        "modC": "== 3.2",
        "modD": "== 3.2",
        "modE": "== 3.2",
        "modF": "== 3.2",
        "modG": "== 3.2",
        "modH": "== 3.2",
        "modJ": "== 3.2"}


def test_project_freeze_bad(modules_dir, modules_repo, capsys, caplog):
    coroot = install_project(modules_dir, "baddep", config=False)

    with pytest.raises(CLIException) as e:
        app(["project", "freeze"])

    assert e.value.exitcode == 1
    assert str(e.value) == "Could not load project"

    out, err = capsys.readouterr()

    assert len(err) == 0, err
    assert len(out) == 0, out
    assert "requirement mod2<2016 on module mod2 not fullfilled, now at version 2016.1" in caplog.text

    assert os.path.getsize(os.path.join(coroot, "project.yml")) != 0


def test_project_freeze(modules_dir, modules_repo, capsys):
    coroot = install_project(modules_dir, "modA")

    app(["project", "freeze", "-o", "-"])

    out, err = capsys.readouterr()

    assert os.path.getsize(os.path.join(coroot, "project.yml")) != 0
    assert len(err) == 0, err
    assert out == """name: modA
license: Apache 2.0
version: 0.0.1
modulepath: libs
downloadpath: libs
repo: %s
requires:
- modB ~= 3.2
- modC ~= 3.2
- modD ~= 3.2
- std ~= 3.2
""" % modules_repo


def test_project_freeze_odd_opperator(modules_dir, modules_repo, capsys, caplog):
    coroot = install_project(modules_dir, "modA")

    app(["project", "freeze", "-o", "-", "--operator", "xxx"])

    out, err = capsys.readouterr()

    assert os.path.getsize(os.path.join(coroot, "project.yml")) != 0
    assert len(err) == 0, err
    assert out == """name: modA
license: Apache 2.0
version: 0.0.1
modulepath: libs
downloadpath: libs
repo: %s
requires:
- modB xxx 3.2
- modC xxx 3.2
- modD xxx 3.2
- std xxx 3.2
""" % modules_repo

    assert "Operator xxx is unknown, expecting one of ['==', '~=', '>=']" in caplog.text


def test_project_options_in_config(modules_dir, modules_repo, capsys):
    coroot = install_project(modules_dir, "modA")
    with open("project.yml", "w") as fh:
        fh.write("""name: modA
license: Apache 2.0
version: 0.0.1
modulepath: libs
downloadpath: libs
repo: %s
freeze_recursive: true
freeze_operator: ==
""" % modules_repo)

    def verify():
        out, err = capsys.readouterr()

        assert os.path.getsize(os.path.join(coroot, "project.yml")) != 0
        assert len(err) == 0, err
        assert len(out) == 0, out

        with open("project.yml", "r") as fh:
            assert fh.read() == ("""name: modA
license: Apache 2.0
version: 0.0.1
modulepath: libs
downloadpath: libs
repo: %s
freeze_recursive: true
freeze_operator: ==
requires:
- modB == 3.2
- modC == 3.2
- modD == 3.2
- modE == 3.2
- modF == 3.2
- modG == 3.2
- modH == 3.2
- modJ == 3.2
- std == 3.2
""" % modules_repo)

    app(["project", "freeze"])
    verify()
    app(["project", "freeze"])
    verify()


def test_module_freeze(modules_dir, modules_repo, capsys):
    coroot = install_project(modules_dir, "modA")

    def verify():
        out, err = capsys.readouterr()

        assert os.path.getsize(os.path.join(coroot, "project.yml")) != 0
        assert len(err) == 0, err
        assert out == ("""name: modC
license: Apache 2.0
version: '3.2'
requires:
- modE ~= 3.2
- modF ~= 3.2
- modI ~= 3.2
- std ~= 3.2
""")

    app(["module", "-m", "modC", "freeze", "-o", "-"])
    verify()


def test_module_freeze_self(modules_dir, modules_repo, capsys):
    coroot = install_project(modules_dir, "modA")

    def verify():
        out, err = capsys.readouterr()

        assert os.path.getsize(os.path.join(coroot, "project.yml")) != 0
        assert len(err) == 0, err
        assert out == ("""name: modC
license: Apache 2.0
version: '3.2'
requires:
- modE ~= 3.2
- modF ~= 3.2
- modI ~= 3.2
- std ~= 3.2
""")
    modp = os.path.join(coroot, "libs/modC")
    app(["module", "install"])
    os.chdir(modp)
    os.curdir = modp
    app(["module", "freeze", "-o", "-"])
    verify()


@pytest.mark.parametrize("kwargs_update_method, mod2_should_be_updated, mod8_should_be_updated",
                         [({}, True, True),
                          ({"module": "mod2"}, True, False),
                          ({"module": "mod8"}, False, True)])
def test_module_update_with_install_mode_master(tmpdir, modules_dir, modules_repo,
                                                kwargs_update_method, mod2_should_be_updated, mod8_should_be_updated):
    # Make a copy of masterproject_multi_mod
    masterproject_multi_mod = tmpdir.join("masterproject_multi_mod")
    clone_repo(modules_repo, "masterproject_multi_mod", tmpdir)
    libs_folder = os.path.join(masterproject_multi_mod, "libs")
    os.mkdir(libs_folder)

    # Set masterproject_multi_mod as current project
    os.chdir(masterproject_multi_mod)
    os.curdir = masterproject_multi_mod
    Config.load_config()

    # Dependencies masterproject_multi_mod
    for mod in ["mod2", "mod8"]:
        # Clone mod in root tmpdir
        clone_repo(modules_repo, mod, tmpdir)

        # Clone mod from root of tmpdir into libs folder of masterproject_multi_mod
        clone_repo(tmpdir, mod, libs_folder)

        # Update module in root of tmpdir by adding an extra file
        file_name_extra_file = "test_file"
        path_mod = os.path.join(tmpdir, mod)
        add_file(path_mod, file_name_extra_file, "test", "Second commit")

        # Assert test_file not present in libs folder of masterproject_multi_mod
        path_extra_file = os.path.join(libs_folder, mod, file_name_extra_file)
        assert not os.path.exists(path_extra_file)

    # Update module(s) of masterproject_multi_mod
    ModuleTool().update(**kwargs_update_method)

    # Assert availability of test_file in masterproject_multi_mod
    extra_file_mod2 = os.path.join(libs_folder, "mod2", file_name_extra_file)
    assert os.path.exists(extra_file_mod2) == mod2_should_be_updated
    extra_file_mod8 = os.path.join(libs_folder, "mod8", file_name_extra_file)
    assert os.path.exists(extra_file_mod8) == mod8_should_be_updated
