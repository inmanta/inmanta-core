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
import logging
import os
import shutil
import subprocess
import tempfile
from typing import Optional

PG_CTL_BIN = "pg_ctl"
INITDB_BIN = "initdb"


LOGGER = logging.getLogger(__name__)


def find_executable(executable: str) -> Optional[str]:
    """
    Scan PATH for an executable.
    """
    for path in os.environ.get("PATH", "").split(os.pathsep):
        path = os.path.abspath(path)
        executable_path = os.path.join(path, executable)
        if os.path.isfile(executable_path):
            return executable_path

    # fall back to pg_config
    try:
        bindir = subprocess.check_output(["pg_config", "--bindir"], universal_newlines=True).strip()
        binpath = os.path.join(bindir, executable)
        if os.path.isfile(binpath):
            return binpath
    except FileNotFoundError:
        return None

    return None


class PostgresProc(object):
    def __init__(
        self, port: int, pg_ctl_bin: Optional[str] = None, initdb_bin: Optional[str] = None, db_path: Optional[str] = None
    ) -> None:
        self.port = port
        self.db_path = db_path
        if self.db_path:
            if os.path.exists(self.db_path) and os.path.isfile(self.db_path):
                raise AssertionError("DB path should be a directory, but it is a file.")

        ctl_bin = pg_ctl_bin or find_executable(PG_CTL_BIN)
        assert ctl_bin, f"Could not find '{PG_CTL_BIN}' or pg_config in system PATH. Make sure you have PostgreSQL installed."
        self.pg_ctl_bin: str = ctl_bin

        initdb_bin = initdb_bin or find_executable(INITDB_BIN)
        assert (
            initdb_bin
        ), f"Could not find '{INITDB_BIN}' or pg_config in system PATH. Make sure you have PostgreSQL installed."
        self.initdb_bin: str = initdb_bin

    def start(self) -> bool:
        """
        Start DB.

        :return: `True` if instance has been started or `False` if it could not start.
        """
        if self.running():
            return True

        try:
            old_wc = os.getcwd()
            self._create_db_path()
            assert self.db_path
            self._init_db()
            self._create_sockets_dir(self.db_path)

            os.chdir(self.db_path)
            args = [self.pg_ctl_bin, "start", "-D", ".", "-o", "-p " + str(self.port) + " -k " + "sockets", "-s"]
            process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            process.communicate()
            return process.returncode == 0
        except Exception:
            LOGGER.exception("Failed to initialize the database.")
            return False
        finally:
            if old_wc is not None:
                os.chdir(old_wc)

    def _create_db_path(self) -> None:
        """Create the data directory to store the postgres data in"""
        if self.db_path:
            if not os.path.exists(self.db_path):
                os.mkdir(self.db_path)
            self._db_path_is_temporary = False
        else:
            self.db_path = tempfile.mkdtemp()
            self._db_path_is_temporary = True

    def _create_sockets_dir(self, parent_dir: str) -> str:
        sockets_dir = os.path.join(parent_dir, "sockets")
        if not os.path.exists(sockets_dir):
            os.mkdir(sockets_dir)
        return sockets_dir

    def _init_db(self) -> None:
        """Init the database if it is not a valid postgres data directory"""
        assert self.db_path
        if os.path.exists(os.path.join(self.db_path, "PG_VERSION")):
            return

        os.chmod(self.db_path, 0o700)
        args = [self.initdb_bin, "-D", self.db_path, "--auth-host", "trust", "-U", "postgres"]
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        if process.returncode != 0:
            LOGGER.error("Failed to initialize db path")
            LOGGER.error("out: %s", out)
            LOGGER.error("err: %s", err)
            raise Exception("Failed to initialize db path.")

    def stop(self) -> None:
        if not self.running() or not self.db_path:
            return
        args = [self.pg_ctl_bin, "stop", "-D", self.db_path, "-m", "immediate", "-s"]
        process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        process.communicate()
        if process.returncode != 0:
            raise Exception("Failed to stop embedded db.")
        if self._db_path_is_temporary and self.db_path:
            shutil.rmtree(self.db_path)
            self.db_path = None

    def running(self) -> bool:
        if self.db_path is None:
            return False
        args = [self.pg_ctl_bin, "status", "-D", self.db_path, "-s"]
        process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        process.communicate()
        return process.returncode == 0
