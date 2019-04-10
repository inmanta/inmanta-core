"""
    Copyright 2018 Inmanta

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
import subprocess
import shutil


PG_CTL_BIN = 'pg_ctl'
INITDB_BIN = 'initdb'


def find_executable(executable):
    """
        Scan PATH for an executable.
    """
    for path in os.environ.get('PATH', '').split(os.pathsep):
        path = os.path.abspath(path)
        executable_path = os.path.join(path, executable)
        if os.path.isfile(executable_path):
            return executable_path


class PostgresProc(object):

    def __init__(self, port, pg_ctl_bin=None, initdb_bin=None, db_path=None):
        self.port = port
        self.db_path = db_path
        if self.db_path:
            if os.path.exists(self.db_path) and os.path.isfile(self.db_path):
                raise AssertionError('DB path should be a directory, but it is a file.')

        self.pg_ctl_bin = pg_ctl_bin or find_executable(PG_CTL_BIN)
        assert self.pg_ctl_bin, 'Could not find "{}" in system PATH. Make sure you have PostgreSQL installed.'\
                                .format(PG_CTL_BIN)
        self.initdb_bin = initdb_bin or find_executable(INITDB_BIN)
        assert self.initdb_bin, 'Could not find "{}" in system PATH. Make sure you have PostgreSQL installed.' \
                                .format(INITDB_BIN)

    def start(self):
        """
            Start DB.

            :return: `True` if instance has been started or `False` if it could not start.
        """
        if self.running():
            return True

        try:
            self._create_db_path()
            self._init_db()
            self._create_sockets_dir(self.db_path)
            old_wc = os.getcwd()
            os.chdir(self.db_path)
            args = [self.pg_ctl_bin, "start", "-D", ".",
                    "-o", "-p " + str(self.port) + " -k " + "sockets", "-s"]
            process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            process.communicate()
            return process.returncode == 0
        except Exception:
            return False
        finally:
            if old_wc is not None:
                os.chdir(old_wc)

    def _create_db_path(self):
        if self.db_path:
            if not os.path.exists(self.db_path):
                os.mkdir(self.db_path)
            self._db_path_is_temporary = False
        else:
            self.db_path = tempfile.mkdtemp()
            self._db_path_is_temporary = True

    def _create_sockets_dir(self, parent_dir):
        sockets_dir = os.path.join(parent_dir, "sockets")
        os.mkdir(sockets_dir)
        return sockets_dir

    def _init_db(self):
        os.chmod(self.db_path, 0o700)

        args = [self.initdb_bin, "-D", self.db_path, "--auth-host", "trust", "-U", "postgres"]
        process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        process.communicate()
        if process.returncode != 0:
            raise Exception("Failed to initialize db path.")

    def stop(self):
        if not self.running():
            return
        args = [self.pg_ctl_bin, "stop", "-D", self.db_path, "-m", "immediate", "-s"]
        process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        process.communicate()
        if process.returncode != 0:
            raise Exception("Failed to stop embedded db.")
        if self._db_path_is_temporary:
            shutil.rmtree(self.db_path)
            self.db_path = None

    def running(self):
        if self.db_path is None:
            return False
        args = [self.pg_ctl_bin, "status", "-D", self.db_path, "-s"]
        process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        process.communicate()
        return process.returncode == 0

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args, **kwargs):
        self.stop()
