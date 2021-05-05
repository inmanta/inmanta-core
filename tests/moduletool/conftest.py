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
import tempfile

import pytest

from inmanta.module import InstallMode
from moduletool.common import (
    add_file,
    add_file_and_compiler_constraint,
    commitmodule,
    make_module_simple,
    make_module_simple_deps,
    makemodule,
    makeproject,
)


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
    +--------+-------------+----------+"""
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
    add_file_and_compiler_constraint(mod7, "badsignal", "present", "fifth commit", version="4.0", compiler_version="1000000.4")
    add_file(mod7, "badsignal", "present", "sixth commit", version="4.1")
    add_file_and_compiler_constraint(mod7, "badsignal", "present", "fifth commit", version="4.2", compiler_version="1000000.5")
    add_file(mod7, "badsignal", "present", "sixth commit", version="4.3")

    mod8 = make_module_simple(reporoot, "mod8", [])
    add_file(mod8, "devsignal", "present", "third commit", version="3.3.dev2")
    add_file(mod8, "mastersignal", "present", "last commit")

    proj = makemodule(
        reporoot, "testproject", [("mod1", None), ("mod2", ">2016"), ("mod5", None)], True, ["mod1", "mod2", "mod6", "mod7"]
    )
    # results in loading of 1,2,3,6
    commitmodule(proj, "first commit")

    badproject = makemodule(reporoot, "badproject", [("mod15", None)], True)
    commitmodule(badproject, "first commit")

    baddep = makemodule(reporoot, "baddep", [("badmod", None), ("mod2", ">2016")], True)
    commitmodule(baddep, "first commit")

    devproject = makeproject(reporoot, "devproject", imports=["mod8"], install_mode=InstallMode.prerelease)
    commitmodule(devproject, "first commit")

    masterproject = makeproject(reporoot, "masterproject", imports=["mod8"], install_mode=InstallMode.master)
    commitmodule(masterproject, "first commit")

    masterproject_multi_mod = makeproject(
        reporoot, "masterproject_multi_mod", imports=["mod2", "mod8"], install_mode=InstallMode.master
    )
    commitmodule(masterproject_multi_mod, "first commit")

    nover = makemodule(reporoot, "nover", [])
    commitmodule(nover, "first commit")
    add_file(nover, "signal", "present", "second commit")

    noverproject = makeproject(reporoot, "noverproject", imports=["nover"])
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
