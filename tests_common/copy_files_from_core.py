"""
    Copyright 2019 Inmanta

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

# Source dirs
script_dir = os.path.abspath(os.path.dirname(__file__))
tests_dir = os.path.join(script_dir, "..", "tests")
data_dir = os.path.join(tests_dir, "data")

# Destination dirs
dest_dir = os.path.join(script_dir, "src", "inmanta_tests")
dest_data_dir = os.path.join(dest_dir, "data")
os.makedirs(dest_data_dir, exist_ok=True)

# Files/Directories to copy
conftest_py = os.path.join(tests_dir, "conftest.py")
utils_py = os.path.join(tests_dir, "utils.py")
server_crt_file = os.path.join(data_dir, "server.crt")
server_open_key_file = os.path.join(data_dir, "server.open.key")
enduser_certs_dir = os.path.join(data_dir, "ca", "enduser-certs")

# Copy files
shutil.copy(conftest_py, dest_dir)
shutil.copy(utils_py, dest_dir)
shutil.copy(server_crt_file, dest_data_dir)
shutil.copy(server_open_key_file, dest_data_dir)
shutil.copytree(enduser_certs_dir, os.path.join(dest_data_dir, "ca", "enduser-certs"))
