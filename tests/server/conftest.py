"""
Copyright 2022 Inmanta

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
import uuid
from collections import abc
from typing import Optional

import pytest
import yaml

import utils
from inmanta import data, module


@pytest.fixture
async def environment_factory(tmpdir) -> abc.AsyncIterator["EnvironmentFactory"]:
    """
    Provides a factory for environments with a main.cf file.
    """
    yield EnvironmentFactory(str(tmpdir.join("environment_factory")))


class EnvironmentFactory:
    def __init__(self, dir: str, project_name: str = "test") -> None:
        self.src_dir: str = os.path.join(dir, "src")
        self.modules_dir: str = os.path.join(dir, "modules")
        self.project: data.Project = data.Project(name=project_name)
        self._ready: bool = False

    async def setup(self) -> None:
        if self._ready:
            return

        project_template = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "project")
        shutil.copytree(project_template, self.src_dir)

        # Set up git
        subprocess.check_output(["git", "init"], cwd=self.src_dir)
        subprocess.check_output(["git", "add", "*"], cwd=self.src_dir)
        subprocess.check_output(["git", "config", "user.name", "Unit"], cwd=self.src_dir)
        subprocess.check_output(["git", "config", "user.email", "unit@test.example"], cwd=self.src_dir)
        subprocess.check_output(["git", "commit", "-m", "unit test"], cwd=self.src_dir)

        await self.project.insert()

        self._ready = True

    async def create_environment(self, main: str = "", *, name: Optional[str] = None) -> data.Environment:
        """
        A new environment is created on the server each time this method is invoked, but all these environments
        use the same source directory on disk. It's the responsibility of the user to make sure that no concurrent
        compilation are done of each of these environments.
        """
        await self.setup()
        branch: str = name if name is not None else str(uuid.uuid4())
        subprocess.check_output(["git", "checkout", "-b", branch], cwd=self.src_dir)
        self.write_main(main)
        environment: data.Environment = data.Environment(
            name=branch, project=self.project.id, repo_url=self.src_dir, repo_branch=branch
        )
        await environment.insert()
        return environment

    def write_main(self, main: str, environment: Optional[data.Environment] = None) -> None:
        self.write_file(path="main.cf", content=main, environment=environment)

    def write_file(self, path: str, content: str, environment: Optional[data.Environment] = None) -> None:
        if environment is not None:
            subprocess.check_output(["git", "checkout", environment.repo_branch], cwd=self.src_dir)
        with open(os.path.join(self.src_dir, path), "w", encoding="utf-8") as fd:
            fd.write(content)
        subprocess.check_output(["git", "add", path], cwd=self.src_dir)
        subprocess.check_output(["git", "commit", "-m", f"write {path}", "--allow-empty"], cwd=self.src_dir)

    def add_v2_module(self, module_name: str, *, plugin_code: str, template_dir: str, index: utils.PipIndex) -> None:
        """
        Publish a V2 module, made from the given template, to the given package index. The project requires the module
        and installs it from that index. The project changes are committed to the branch that is checked out, which is the
        branch of the last created environment.

        :param plugin_code: The content of the module's __init__.py file.
        """
        utils.module_from_template(
            source_dir=template_dir,
            dest_dir=os.path.join(self.modules_dir, module_name),
            new_content_init_py=plugin_code,
            new_name=module_name,
            publish_index=index,
        )

        with open(os.path.join(self.src_dir, "project.yml"), encoding="utf-8") as fd:
            project_yml = yaml.safe_load(fd)
        extra_index_urls: list[str] = project_yml["pip"].setdefault("extra-index-url", [])
        if index.url not in extra_index_urls:
            extra_index_urls.append(index.url)
        self.write_file(path="project.yml", content=yaml.safe_dump(project_yml))

        requirements_txt = os.path.join(self.src_dir, "requirements.txt")
        requirements: str = ""
        if os.path.exists(requirements_txt):
            with open(requirements_txt, encoding="utf-8") as fd:
                requirements = fd.read()
        requirement: str = module.ModuleV2Source.get_package_name_for(module_name)
        self.write_file(path="requirements.txt", content=f"{requirements}{requirement}\n")
