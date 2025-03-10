"""
Copyright 2020 Inmanta

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

import common
from inmanta.module import Project


def test_collect_python_requirements(tmpdir):
    # Create project
    common.makeproject(tmpdir, "test-project", deps=[("mod1", ""), ("mod2", "")], imports=["mod1", "mod2"])
    project_dir = os.path.join(tmpdir, "test-project")
    libs_dir = os.path.join(project_dir, "libs")
    # Create mod1
    common.makemodule(libs_dir, "mod1", project=False)
    mod1 = os.path.join(libs_dir, "mod1")
    mod1_req_txt = """iplib@git+https://github.com/bartv/python3-iplib
pytest\
>=\
1.5


iplib>=0.0.1
    """
    common.add_file(mod1, "requirements.txt", mod1_req_txt, msg="initial commit")
    # Create mod2
    common.makemodule(libs_dir, "mod2", project=False)
    mod2 = os.path.join(libs_dir, "mod2")
    mod2_req_txt = """# A comment
dummy-yummy # A comment
 # Another comment

    """
    common.add_file(mod2, "requirements.txt", mod2_req_txt, msg="initial commit")

    project = Project(project_dir, venv_path=os.path.join(project_dir, ".env"))
    Project.set(project)
    project.load_module("mod1", allow_v1=True)
    project.load_module("mod2", allow_v1=True)
    reqs = project.collect_python_requirements()
    expected_reqs = ["iplib@git+https://github.com/bartv/python3-iplib", "pytest>=1.5", "iplib>=0.0.1", "dummy-yummy"]
    assert sorted(reqs) == sorted(expected_reqs)
