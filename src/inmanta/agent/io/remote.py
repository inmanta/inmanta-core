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

import threading
import logging
import time

from execnet import multi, gateway_bootstrap
from . import local
from inmanta import resources


LOGGER = logging.getLogger()


class CannotLoginException(Exception):
    pass


class RemoteException(Exception):
    def __init__(self, exception_type, msg, traceback=None):
        super().__init__(exception_type, msg, traceback)


class SshIO(local.IOBase):
    """
        This class provides handler IO methods. This io method is used when the ssh scheme is provided in the agent uri.

        The uri supports setting the hostname, user and port. In the query string the following config can be provided:
         * python: The python interpreter to use. The default value is python
         * retries: The number of retries before giving up. The default number of retries 10
         * retry_wait: The time to wait between retries for the remote target to become available. The default wait is 30s
    """
    def is_remote(self):
        return True

    def __init__(self, uri, config):
        super(SshIO, self).__init__(uri, config)
        self._host = config["host"]
        if "port" in config and config["port"] is not None:
            self._port = int(config["port"])
        else:
            self._port = 22

        if "user" in config and config["user"] is not None:
            self._user = config["user"]
        else:
            self._user = "root"

        if "retries" in config and config["retries"] is not None:
            self._retries = int(config["retries"])
        else:
            self._retries = 10

        if "retry_wait" in config and config["retry_wait"] is not None:
            self._retry_wait = int(config["retry_wait"])
        else:
            self._retry_wait = 30

        self._lock = threading.Lock()
        self._group = multi.Group()
        self._gw = None
        connect = self._build_connect_string()
        LOGGER.info("Starting execnet connection group %s", id(self._group))
        try:
            attempts = self._retries + 1
            while attempts > 0:
                try:
                    self._gw = self._group.makegateway(self._build_connect_string())
                    attempts = 0
                except gateway_bootstrap.HostNotFound as e:
                    attempts -= 1
                    if attempts == 0:
                        self._group.terminate(0.1)
                        raise resources.HostNotFoundException(hostname=self._host, user=self._user, error=e)

                    LOGGER.info("Failed to login to %s, waiting %d seconds and %d attempts left.",
                                self.uri, self._retry_wait, attempts)
                    time.sleep(self._retry_wait)

        except BrokenPipeError as e:
            LOGGER.info("Terminating execnet connection group due to exception %s", id(self._group), e)
            self._group.terminate(0.1)
            raise resources.HostNotFoundException(hostname=self._host, user=self._user, error=e)
        except AssertionError as e:
            LOGGER.info("Terminating execnet connection group due to exception %s", id(self._group), e)
            self._group.terminate(0.1)
            raise CannotLoginException()

        assert self._gw is not None
        LOGGER.info("Connected with %s", connect)

    def _build_connect_string(self):
        """
            Build the connection string for execent based on the hostname
        """
        opts = "-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o PasswordAuthentication=no"
        opts += " -p %d" % self._port

        if "python" in self.config:
            python = self.config["python"]
        else:
            python = "python"

        return "ssh=%s %s@%s//python=%s" % (opts, self._user, self._host, python)

    def _execute(self, function_name, *args, **kwargs):
        with self._lock:
            ch = self._gw.remote_exec(local)
            ch.send((function_name, args, kwargs))
            result = ch.receive()
            ch.close()

        # check if we got an exception
        if isinstance(result, dict) and "__type__" in result and result["__type__"] == "RemoteException":
            raise RemoteException(exception_type=result["exception_type"], msg=result["exception_string"],
                                  traceback=result["traceback"])

        return result

    def read_binary(self, path):
        # remoting can turn this into a string
        result = self._execute("read_binary", path)
        if isinstance(result, str):
            return result.encode()
        return result

    def __getattr__(self, name):
        """
            Proxy a function call to the local version on the other side of the channel.
        """
        def call(*args, **kwargs):
            result = self._execute(name, *args, **kwargs)
            return result

        return call

    def close(self):
        LOGGER.info("Terminating execnet connection group %s", id(self._group))
        if self._group is not None:
            self._group.terminate(0.1)
