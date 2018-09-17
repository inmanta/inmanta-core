"""
    Copyright 2018 Inmanta
    Copyright 2013 Roman Kalyakin (Mongobox)

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
import tempfile
import copy
import subprocess
import time
import sys
import shutil
import socket


MONGOD_BIN = 'mongod'
DEFAULT_ARGS = [
    # don't flood stdout, we're not reading it
    "--quiet",
    # save the port
    # disable unused.
    "--nounixsocket",
    # use a smaller default file size
    "--smallfiles",
    # journaling on by default in 2.0 and makes it to slow
    # for tests, can causes failures in jenkins
    "--nojournal",
    # disable scripting
    "--noscripting",
]
STARTUP_TIME = 0.4
START_CHECK_ATTEMPTS = 200


def find_executable(executable):
    """
        Scan PATH for an executable.
    """
    for path in os.environ.get('PATH', '').split(os.pathsep):
        path = os.path.abspath(path)
        executable_path = os.path.join(path, executable)
        if os.path.isfile(executable_path):
            return executable_path


class MongoProc(object):
    """
        Class to start and manage a mongodb server process
    """
    def __init__(self, port, mongod_bin=None, log_path=None, db_path=None, prealloc=False, auth=False):
        self.mongod_bin = mongod_bin or find_executable(MONGOD_BIN)
        assert self.mongod_bin, 'Could not find "{}" in system PATH. Make sure you have MongoDB installed.'.format(MONGOD_BIN)

        self.port = port
        self.log_path = log_path or os.devnull
        self.prealloc = prealloc
        self.db_path = db_path
        self.auth = auth

        if self.db_path:
            if os.path.exists(self.db_path) and os.path.isfile(self.db_path):
                raise AssertionError('DB path should be a directory, but it is a file.')

        self.process = None

    def start(self):
        """
            Start MongoDB.

            :return: `True` if instance has been started or `False` if it could not start.
        """
        if self.db_path:
            if not os.path.exists(self.db_path):
                os.mkdir(self.db_path)
            self._db_path_is_temporary = False
        else:
            self.db_path = tempfile.mkdtemp()
            self._db_path_is_temporary = True

        args = copy.copy(DEFAULT_ARGS)
        args.insert(0, self.mongod_bin)

        args.extend(['--dbpath', self.db_path])
        args.extend(['--port', str(self.port)])
        args.extend(['--logpath', self.log_path])

        if self.auth:
            args.append("--auth")

        if not self.prealloc:
            args.append("--noprealloc")

        self.process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

        return self._wait_till_started()

    def stop(self):
        if not self.process:
            return

        # Not sure if there should be more checks for
        # other platforms.
        if sys.platform == 'darwin':
            self.process.kill()
        else:
            os.kill(self.process.pid, 9)
        self.process.wait()

        if self._db_path_is_temporary:
            shutil.rmtree(self.db_path)
            self.db_path = None

        self.process = None

    def running(self):
        return self.process is not None

    def _wait_till_started(self):
        attempts = 0
        while self.process.poll() is None and attempts < START_CHECK_ATTEMPTS:
            attempts += 1
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                try:
                    s.connect(('localhost', int(self.port)))
                    return True
                except (IOError, socket.error):
                    time.sleep(0.25)
            finally:
                s.close()

        self.stop()
        return False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args, **kwargs):
        self.stop()
