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

    Contact: bart@impera.io
"""

import hashlib
import os
import pwd
import subprocess
import grp


try:
    from pwd import getpwnam
except ImportError:
    getpwnam = None

try:
    from grp import getgrnam
except ImportError:
    getgrnam = None


class LocalIO(object):
    """
        This class provides handler IO methods
    """
    def is_remote(self):
        return False

    def hash_file(self, path):
        sha1sum = hashlib.sha1()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(32768), b''):
                sha1sum.update(chunk)

        return sha1sum.hexdigest()

    def read(self, path):
        """
            Read in the file in path and return its content as string
        """
        with open(path, "rb") as fd:
            return str(fd.read().decode())

    def read_binary(self, path):
        """
            Return the content of the file
        """
        with open(path, "rb") as fd:
            return fd.read()

    def run(self, command, arguments=[], env=None):
        """
            Execute a command with the given argument and return the result
        """
        cmds = [command] + arguments
        result = subprocess.Popen(cmds, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)

        data = result.communicate()

        return (data[0].strip().decode("utf-8"), data[1].strip().decode("utf-8"), result.returncode)

    def file_exists(self, path):
        """
            Check if a given file exists
        """
        return os.path.exists(path)

    def readlink(self, path):
        """
            Return the target of the path
        """
        return os.readlink(path)

    def symlink(self, source, target):
        """
            Symlink source to target
        """
        return os.symlink(source, target)

    def is_symlink(self, path):
        """
            Is the given path a symlink
        """
        return os.path.islink(path)

    def file_stat(self, path):
        """
            Do a statcall on a file
        """
        stat_result = os.stat(path)
        status = {}
        status["owner"] = pwd.getpwuid(stat_result.st_uid).pw_name
        status["group"] = grp.getgrgid(stat_result.st_gid).gr_name
        status["permissions"] = int(oct(stat_result.st_mode)[-4:])

        return status

    def remove(self, path):
        """
            Remove a file
        """
        return os.remove(path)

    def put(self, path, content):
        """
            Put the given content at the given path
        """
        with open(path, "wb+") as fd:
            fd.write(content.encode())

    def _get_gid(self, name):
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
        """
            Change the ownership information
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
        """
            Change the permissions
        """
        os.chmod(path, permissions)

    def mkdir(self, path):
        """
            Create a directory
        """
        os.mkdir(path)

    def rmdir(self, path):
        """
            Remove a directory
        """
        os.rmdir(path)

    def close(self):
        pass


if __name__ == '__channelexec__':
    global channel
    local_io = LocalIO()
    for item in channel:  # NOQA
        if hasattr(local_io, item[0]):
            try:
                method = getattr(local_io, item[0])
                result = method(*item[1])
                channel.send(result)  # NOQA
            except Exception as e:
                import traceback
                channel.send(str(traceback.format_exc()))  # NOQA
                pass

        else:
            raise AttributeError("Method %s is not supported" % item[0])
