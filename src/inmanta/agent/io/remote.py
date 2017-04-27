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

from execnet import multi, gateway_bootstrap
from . import local
from inmanta import resources
from inmanta.agent import config as cfg


class CannotLoginException(Exception):
    pass


class RemoteException(Exception):
    def __init__(self, exception_type, msg, traceback=None):
        super().__init__(exception_type, msg, traceback)


class RemoteIO(object):
    """
        This class provides handler IO methods
    """
    def is_remote(self):
        return True

    def __init__(self, host):
        self._lock = threading.Lock()
        self._gw = None
        try:
            self._gw = multi.makegateway(self._build_connect_string(host))
        except (gateway_bootstrap.HostNotFound, BrokenPipeError) as e:
            raise resources.HostNotFoundException(hostname=host, user="root", error=e)
        except AssertionError:
            raise CannotLoginException()

    def _build_connect_string(self, host):
        """
            Build the connection string for execent based on the hostname
        """
        python_path = cfg.python_binary.get()

        if "@" in host:
            username, hostname = host.split("@")
            return "ssh=%s@%s//python=%s" % (username, hostname, python_path)
        else:
            return "ssh=root@%s//python=%s" % (host, python_path)

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
        if self._gw is not None:
            self._gw.exit()

    def __del__(self):
        self.close()
