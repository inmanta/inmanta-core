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

import hashlib
import os
import shutil
import subprocess
import sys

try:
    import grp  # @UnresolvedImport
    import pwd
except ImportError:
    pwd = None
    grp = None


try:
    from pwd import getpwnam
except ImportError:
    getpwnam = None

try:
    from grp import getgrnam
except ImportError:
    getgrnam = None

# This code needs to stay Py2 compatible without any external libs
if False:
    from typing import Dict, List, Optional, Tuple, Union


class IOBase(object):
    """
    Base class for an IO module. This class is python2 compatible so IOs that work remote can load this module on python2.
    """

    def __init__(self, uri, config):
        # type: (str, Dict[str, Optional[str]]) -> None
        """
        Initialize the IO

        :param uri: The uri used to configure this IO
        :param config: The parsed version of the uri
        """
        self.uri = uri
        self.config = config

    def is_remote(self):
        # type: () -> bool
        """
        Are operation executed remote

        :return: Returns true if the io operations are remote.
        :rtype: bool
        """
        raise NotImplementedError()

    def close(self):
        # type: () -> None
        """
        Close any resources
        """

    def __del__(self):
        # type: () -> None
        """
        An agent caches IO instances to reuse them for multiple resources. This method is called when an item is removed
        from the cache, for example when a version in the cache is closed.
        """
        self.close()


class BashIO(IOBase):
    """
    This class provides handler IO methods
    """

    def __init__(self, uri, config, run_as=None):
        # type: (str, Dict[str, Optional[str]], Optional[str]) -> None
        super(BashIO, self).__init__(uri, config)
        self.run_as = run_as

    def _run_as_args(self, *args):
        """
        Build the arguments to run the command as the `run_as` user
        """
        if self.run_as is None:
            return list(args)

        else:
            sudo_cmd = ["sudo", "-E"]
            ret = sudo_cmd + ["-u", self.run_as] + list(args)
            return ret

    def is_remote(self):
        # type: () -> bool
        return False

    def hash_file(self, path):
        # type: (str) -> str
        cwd = os.curdir
        if not os.path.exists(cwd):
            # When this code is executed with nosetests, curdir does not exist anymore
            cwd = "/"

        result = subprocess.Popen(self._run_as_args("sha1sum", path), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
        data = result.communicate()

        if result.returncode > 0:
            raise IOError("Failed to hash file")

        hash = data[0].decode("utf-8").strip().split(" ")[0]

        if len(hash) != 40:
            raise IOError("Invalid hash output")

        return hash

    def read(self, path):
        # type: (str) -> str
        """
        Read in the file in path and return its content as string (UTF-8)
        """
        cwd = os.curdir
        if not os.path.exists(cwd):
            # When this code is executed with nosetests, curdir does not exist anymore
            cwd = "/"

        result = subprocess.Popen(self._run_as_args("cat", path), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
        data = result.communicate()

        if result.returncode > 0:
            raise IOError()

        return data[0].decode("utf-8")

    def read_binary(self, path):
        # type: (str) -> bytes
        """
        Return the content of the file
        """
        result = subprocess.Popen(self._run_as_args("dd", "if=" + path), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        data = result.communicate()

        if result.returncode > 0:
            raise IOError()

        return data[0]

    def run(self, command, arguments=[], env=None, cwd=None, timeout=None):
        # type: (str, List[str], Optional[Dict[str,str]], Optional[str], Optional[int]) -> Tuple[str, str, int]
        """
        Execute a command with the given argument and return the result
        """
        current_env = os.environ.copy()
        if env is not None:
            current_env.update(env)

        if (not env or "PYTHONPATH" not in env) and "PYTHONPATH" in current_env:
            # Remove the inherited python path
            del current_env["PYTHONPATH"]

        cmds = [command] + arguments
        result = subprocess.Popen(
            self._run_as_args(*cmds), stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=current_env, cwd=cwd
        )

        if sys.version_info < (3, 0, 0):
            # TODO timeout is not supported
            data = result.communicate()
        else:
            data = result.communicate(timeout=timeout)

        return (data[0].strip().decode("utf-8"), data[1].strip().decode("utf-8"), result.returncode)

    def file_exists(self, path):
        # type: (str) -> bool
        """
        Check if a given file exists
        """
        result = subprocess.Popen(self._run_as_args("stat", "-t", path), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result.communicate()

        if result.returncode > 0:
            return False

        return True

    def readlink(self, path):
        # type: (str) -> str
        """
        Return the target of the path
        """
        result = subprocess.Popen(self._run_as_args("readlink", path), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        data = result.communicate()

        if result.returncode > 0:
            raise IOError()

        return data[0].decode("utf-8").strip()

    def symlink(self, source, target):
        # type: (str, str) -> bool
        """
        Symlink source to target
        """
        result = subprocess.Popen(self._run_as_args("ln", "-s", source, target), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result.communicate()

        if result.returncode > 0:
            return False

        return True

    def is_symlink(self, path):
        # type: (str) -> bool
        """
        Is the given path a symlink
        """
        result = subprocess.Popen(self._run_as_args("stat", path), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        data = result.communicate()

        if result.returncode > 0:
            raise IOError()

        if "symbolic link" in data[0].decode("utf-8").strip():
            return True

        return False

    def file_stat(self, path):
        # type: (str) -> Dict[str, Union[str, int]]
        """
        Do a statcall on a file
        """
        result = subprocess.Popen(
            self._run_as_args("stat", "-c", "%a %U %G", path), stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        data = result.communicate()

        if result.returncode > 0:
            raise IOError()

        parts = data[0].decode("utf-8").strip().split(" ")
        if len(parts) != 3:
            raise IOError()

        status = {}
        status["owner"] = parts[1]
        status["group"] = parts[2]
        status["permissions"] = int(parts[0])

        return status

    def remove(self, path):
        # type: (str) -> None
        """
        Remove a file
        """
        result = subprocess.Popen(self._run_as_args("rm", "-f", path), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result.communicate()

        if result.returncode > 0:
            raise IOError()

    def put(self, path, content):
        # type: (str, str) -> bool
        """
        Put the given content at the given path in UTF-8
        """
        result = subprocess.Popen(
            self._run_as_args("dd", "of=" + path), stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE
        )
        result.communicate(input=content)

        if result.returncode > 0:
            raise IOError()

        return True

    def chown(self, path, user=None, group=None):
        # type: (str, Optional[str], Optional[str]) -> None
        """
        Change the ownership information
        """
        args = None
        if user is not None and group is not None:
            args = ["chown", "%s:%s" % (user, group)]

        elif user is not None:
            args = ["chown", user]

        elif group is not None:
            args = ["chgrp", group]

        if args is not None:
            args.append(path)
            result = subprocess.Popen(self._run_as_args(*args), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result.communicate()

            if result.returncode > 0:
                raise Exception("Failed to set %s:%s to %s (return code %d)" % (user, group, path, result.returncode))

    def chmod(self, path, permissions):
        # type: (str, str) -> bool
        """
        Change the permissions
        """
        result = subprocess.Popen(self._run_as_args("chmod", permissions, path), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result.communicate()

        return result.returncode > 0

    def mkdir(self, path):
        # type: (str) -> bool
        """
        Create a directory
        """
        result = subprocess.Popen(self._run_as_args("mkdir", path), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result.communicate()

        return result.returncode > 0

    def rmdir(self, path):
        # type: (str) -> bool
        """
        Remove a directory
        """
        if path == "/":
            raise Exception("Please do not ask to do rm -rf /")

        if "*" in path:
            raise Exception("Do not use wildward in an rm -rf")

        result = subprocess.Popen(self._run_as_args("rm", "-rf", path), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result.communicate()

        return result.returncode > 0

    def __repr__(self):
        # type: () -> str
        if self.run_as is None:
            return "BashIO"

        else:
            return "BashIO_run_as_%s" % self.run_as

    def __str__(self):
        # type: () -> str
        return repr(self)


class LocalIO(IOBase):
    """
    This class provides handler IO methods

    This class is part of the stable API.
    """

    def is_remote(self):
        # type: () -> bool
        """
        Are operation executed remote

        :return: Returns true if the io operations are remote.
        :rtype: bool
        """
        return False

    def hash_file(self, path):
        # type: (str) -> str
        """
        Return the sha1sum of the file at path

        :param str path: The path of the file to hash the content of
        :return: The sha1sum in a hex string
        :rtype: str
        """
        sha1sum = hashlib.sha1()
        with open(path, "rb") as f:
            sha1sum.update(f.read())

        return sha1sum.hexdigest()

    def read(self, path):
        # type: (str) -> str
        """
        Read in the file in path and return its content as string

        :param str path: The path of the file to read.
        :return: The string content of the file
        :rtype: string
        """
        with open(path, "rb") as fd:
            return fd.read().decode("utf-8")

    def read_binary(self, path):
        # type: (str) -> bytes
        """
        Read in the file in path and return its content as a bytestring

        :param str path: The path of the file to read.
        :return: The byte content of the file
        :rtype: bytes
        """
        with open(path, "rb") as fd:
            return fd.read()

    def run(self, command, arguments=[], env=None, cwd=None, timeout=None):
        # type: (str, List[str], Optional[Dict[str,str]], Optional[str], Optional[int]) -> Tuple[str, str, int]
        """
        Execute a command with the given argument and return the result

        :param str command: The command to execute.
        :param list arguments: The arguments of the command
        :param dict env: A dictionary with environment variables.
        :param str cwd: The working dir to execute the command in.
        :param int timeout: The timeout for this command. This parameter is ignored if the command is executed remotely with
                            a python 2 interpreter.
        :return: A tuple with (stdout, stderr, returncode)
        :rtype: tuple
        """
        current_env = os.environ.copy()
        if env is not None:
            current_env.update(env)

        if (not env or "PYTHONPATH" not in env) and "PYTHONPATH" in current_env:
            # Remove the inherited python path
            del current_env["PYTHONPATH"]

        if sys.version_info < (3, 0, 0):
            # python < 2.7 does not support dict comprehensions
            new_env = {}
            for k, v in current_env.items():
                new_env[k.encode()] = str(v).encode()
            current_env = new_env

        cmds = [command] + arguments
        result = subprocess.Popen(cmds, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=current_env, cwd=cwd)

        if sys.version_info < (3, 0, 0):
            # TODO timeout is not supported
            data = result.communicate()
        else:
            data = result.communicate(timeout=timeout)

        return (data[0].strip().decode("utf-8"), data[1].strip().decode("utf-8"), result.returncode)

    def file_exists(self, path):
        # type: (str) -> bool
        """
        Check if a given file exists

        :param str path: The path to check if it exists.
        :return: Returns true if the file exists
        :rtype: bool
        """
        return os.path.lexists(path)

    def readlink(self, path):
        # type: (str) -> str
        """
        Return the target of the path

        :param str path: The symlink to get the target for.
        :return: The target of the symlink
        :rtype: str
        """
        return os.readlink(path)

    def symlink(self, source, target):
        # type: (str, str) -> None
        """
        Symlink source to target

        :param str source: Create a symlink of this path to target
        :param str target: The path of the symlink to create
        """
        os.symlink(source, target)

    def is_symlink(self, path):
        # type: (str) -> bool
        """
        Is the given path a symlink

        :param str path: The path of the symlink
        :return: Returns true if the given path points to a symlink
        :rtype: str
        """
        return os.path.islink(path)

    def file_stat(self, path):
        # type: (str) -> Dict[str, Union[int, str]]
        """
        Do a stat call on a file

        :param str path: The file or direct to stat
        :return: A dict with the owner, group and permissions of the given path
        :rtype: dict[str, str]
        """
        stat_result = os.stat(path)
        status = {}
        status["owner"] = pwd.getpwuid(stat_result.st_uid).pw_name
        status["group"] = grp.getgrgid(stat_result.st_gid).gr_name
        status["permissions"] = int(oct(stat_result.st_mode)[-4:])

        return status

    def remove(self, path):
        # type: (str) -> None
        """
        Remove a file

        :param str path: The path of the file to remove.
        """
        os.remove(path)

    def put(self, path, content):
        # type: (str, str) -> None
        """
        Put the given content at the given path

        :param str path: The location where to write the file
        :param bytes content: The binarystring content to write to the file.
        """
        with open(path, "wb+") as fd:
            fd.write(content)

    def _get_gid(self, name):
        # type: (str) -> Optional[int]
        """Returns a gid, given a group name."""
        # Stolen from the python3 shutil lib
        if getgrnam is None or name is None:
            return None
        try:
            result = getgrnam(name)
        except KeyError:
            result = None
        if result is not None:
            return result[2]
        return None

    def _get_uid(self, name):
        # type: (str) -> Optional[int]
        """Returns an uid, given a user name."""
        # Stolen from the python3 shutil lib
        if getpwnam is None or name is None:
            return None
        try:
            result = getpwnam(name)
        except KeyError:
            result = None
        if result is not None:
            return result[2]
        return None

    def chown(self, path, user=None, group=None):
        # type: (str, Optional[str], Optional[str]) -> None
        """
        Change the ownership of a file.

        :param str path: The path of the file or directory to change the ownership of.
        :param str user: The user to change to
        :param str group: The group to change to
        """
        # Stolen from the python3 shutil lib
        if user is None and group is None:
            raise ValueError("user and/or group must be set")

        _user = user
        _group = group

        # -1 means don't change it
        if user is None:
            _user = -1
        # user can either be an int (the uid) or a string (the system username)
        elif not isinstance(user, int):
            _user = self._get_uid(user)
            if _user is None:
                raise LookupError("no such user: {!r}".format(user))

        if group is None:
            _group = -1
        elif not isinstance(group, int):
            _group = self._get_gid(group)
            if _group is None:
                raise LookupError("no such group: {!r}".format(group))

        os.chown(path, _user, _group)

    def chmod(self, path, permissions):
        # type: (str, str) -> None
        """
        Change the permissions

        :param str path: The path of the file or directory to change the permission of.
        :param str permissions: An octal string with the permission to set.
        """
        os.chmod(path, int(permissions, 8))

    def mkdir(self, path):
        # type: (str) -> None
        """
        Create a directory

        :param str path: Create this directory. The parent needs to exist.
        """
        os.mkdir(path)

    def rmdir(self, path):
        # type: (str) -> None
        """
        Remove a directory

        :param str path: The directory to remove
        """
        shutil.rmtree(path)


if __name__ == "__channelexec__":
    global channel

    if os.getuid() == 0:
        local_io = LocalIO(uri="local:", config={})  # type: IOBase
    else:
        local_io = BashIO(uri="local:", config={}, run_as="root")

    for item in channel:  # NOQA
        if hasattr(local_io, item[0]):
            try:
                method = getattr(local_io, item[0])
                result = method(*item[1], **item[2])
                channel.send(result)  # NOQA
            except Exception as e:
                import traceback

                channel.send(  # NOQA
                    {
                        "__type__": "RemoteException",
                        "exception_type": str(e.__class__),
                        "exception_string": str(e),
                        "traceback": str(traceback.format_exc()),
                    }
                )

        else:
            raise AttributeError("Method %s is not supported" % item[0])
