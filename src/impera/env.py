"""
    Copyright 2015 Impera

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Contect: bart@impera.io
"""

import sys
import os
import subprocess
import tempfile


class VirtualEnv(object):
    """
        Creates and uses a virtual environment for this process
    """
    def __init__(self, env_path):
        self.env_path = env_path
        self.virtual_python = None
        self.virtual_pip = None

    def init_env(self):
        """
            Init the virtual environment
        """
        python_exec = sys.executable
        python_name = os.path.basename(sys.executable)

        # check if the virtual env exists
        python_bin = os.path.join(self.env_path, "bin", python_name)

        if not os.path.exists(python_bin):
            virtualenv_path = "/usr/bin/virtualenv"
            if not os.path.exists(virtualenv_path):
                raise Exception("Unable to find virtualenv script (%s does not exist)" % virtualenv_path)

            subprocess.call(["/usr/bin/virtualenv", "-p", python_exec, self.env_path])

        # set the path to the python and the pip executables
        self.virtual_python = python_bin
        self.virtual_pip = os.path.join(self.env_path, "bin", "pip")

    def use_virtual_env(self):
        """
            Use the virtual environment
        """
        self.init_env()

        activate_file = os.path.join(self.env_path, "bin/activate_this.py")
        if os.path.exists(activate_file):
            with open(activate_file) as f:
                code = compile(f.read(), activate_file, 'exec')
                exec(code, {"__file__": activate_file})
        else:
            print("Unable to activate virtual environment because %s does not exist." % activate_file)

    def install(self, requirements):
        """
            Install the given list of requirements in the virtual environment
        """
        cmd = [self.virtual_pip, "install"]
        for require in requirements:
            cmd.append(require)

        subprocess.call(cmd)

    def install_from_file(self, requirements_file: str) -> None:
        """
            Install requirements in the given requirements file
        """
        if os.path.exists(requirements_file):
            cmd = [self.virtual_pip, "install", "-r", requirements_file]
            subprocess.call(cmd)

    def install_from_list(self, requirements_list: list) -> None:
        """
            Install requirements from a list of requirement strings
        """
        try:
            requirements_file = tempfile.mktemp()
            with open(requirements_file, "w+") as fd:
                fd.write("\n".join(requirements_list))
                fd.close()

            self.install_from_file(requirements_file)
        finally:
            os.remove(requirements_file)
