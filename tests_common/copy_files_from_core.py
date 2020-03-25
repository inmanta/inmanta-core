#!/bin/env python3
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
import fileinput
import os
import shutil

# Source dirs
script_dir = os.path.abspath(os.path.dirname(__file__))
tests_dir = os.path.join(script_dir, "..", "tests")
data_dir = os.path.join(tests_dir, "data")
db_dir = os.path.join(tests_dir, "db")

# Destination dirs
dest_dir = os.path.join(script_dir, "src", "inmanta_tests")
dest_data_dir = os.path.join(dest_dir, "data")
dest_db_dir = os.path.join(dest_dir, "db")


def cleanup_dir(directory: str):
    if os.path.exists(directory):
        shutil.rmtree(directory)
    os.makedirs(directory, exist_ok=True)


# cleanup
cleanup_dir(dest_data_dir)
cleanup_dir(dest_db_dir)

# Files/Directories to copy
conftest_py = os.path.join(tests_dir, "conftest.py")
dest_conftest_py = os.path.join(dest_dir, "conftest.py")
utils_py = os.path.join(tests_dir, "utils.py")
dest_utils_py = os.path.join(dest_dir, "utils.py")
server_crt_file = os.path.join(data_dir, "server.crt")
server_open_key_file = os.path.join(data_dir, "server.open.key")
enduser_certs_dir = os.path.join(data_dir, "ca", "enduser-certs")
simple_project_dir = os.path.join(data_dir, "simple_project")
db_common_py = os.path.join(db_dir, "common.py")
dest_db_common_py = os.path.join(dest_db_dir, "common.py")
dump_tool_py = os.path.join(db_dir, "dump_tool.py")
dest_dump_tool_py = os.path.join(dest_db_dir, "dump_tool.py")
dest_simple_project_dir = os.path.join(dest_db_dir, "simple_project")


def remove_file_if_exists(filename: str):
    if os.path.exists(filename):
        os.remove(filename)


remove_file_if_exists(dest_conftest_py)
remove_file_if_exists(dest_utils_py)
remove_file_if_exists(dest_db_common_py)
remove_file_if_exists(dest_dump_tool_py)

# Copy files
shutil.copy(conftest_py, dest_dir)
shutil.copy(utils_py, dest_dir)
shutil.copy(server_crt_file, dest_data_dir)
shutil.copy(server_open_key_file, dest_data_dir)
shutil.copytree(enduser_certs_dir, os.path.join(dest_data_dir, "ca", "enduser-certs"))
shutil.copy(db_common_py, dest_db_common_py)
shutil.copy(dump_tool_py, dest_dump_tool_py)
shutil.copytree(simple_project_dir, dest_simple_project_dir)

# Fix import
with fileinput.input(dest_dump_tool_py, inplace=True) as f:
    for line in f:
        if line.startswith("from utils"):
            print("from inmanta_tests.utils" + line[len("from utils") :], end="")
        else:
            print(line, end="")
