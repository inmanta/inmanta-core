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

    Contact: bart@inmanta.com
"""
import tempfile

from inmanta import env


def test2VirtualEnv():
    env_dir1 = tempfile.mkdtemp()
    env_dir2 = tempfile.mkdtemp()

    venv1 = env.VirtualEnv(env_dir1)
    venv1.use_virtual_env()
    venv1.install(["python-novaclient"])

    venv2 = env.VirtualEnv(env_dir2)
    venv2.use_virtual_env()
    venv2.install(["python-neutronclient"])
