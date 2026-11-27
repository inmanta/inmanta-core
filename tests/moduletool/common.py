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
import subprocess

from inmanta.moduletool import ModuleTool


def add_file(
    modpath,
    file,
    content,
    msg,
    revision: bool = False,
    patch: bool = False,
    minor: bool = False,
    major: bool = False,
    dev=False,
):
    """
    Add a file for a given module.
    If no semver flag is set (revision, patch, minor or major) the newly added file will be commited
    but the module will not be released.

    If one of the semver flags is set to True, this module will be released with the appropriate increment.

    :param modpath: The path to the module
    :param file: The file's name
    :param content: The content to write to file
    :param msg: Commit message
    :param revision: Set this flag to perform a bump on the revision semver number
    :param patch: Set this flag to perform a bump on the patch semver number
    :param minor: Set this flag to perform a bump on the minor semver number
    :param major: Set this flag to perform a bump on the major semver number
    :param dev: When set along with one of the semver flags, only perform a dev release after creating
        this file (i.e. don't tag this version). If set to False, perform a stable release (i.e. tag
        this version) followed by a dev release with the minimal required increment.
    """
    with open(os.path.join(modpath, file), "w", encoding="utf-8") as projectfile:
        projectfile.write(content)

    old_cwd = os.getcwd()
    os.chdir(modpath)
    subprocess.check_output(["git", "add", "*"], cwd=modpath, stderr=subprocess.STDOUT)
    ModuleTool().release(dev=dev, message=msg, revision=revision, patch=patch, minor=minor, major=major, commit_all=True)
    os.chdir(old_cwd)
