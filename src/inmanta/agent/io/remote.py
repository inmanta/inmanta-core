"""
    Copyright 2016 Inmanta

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

from execnet import multi, gateway_bootstrap
from . import local
from inmanta import resources
from inmanta.agent import config as cfg


class RemoteIO(object):
    """
        This class provides handler IO methods
    """

    def is_remote(self):
        return True

    def __init__(self, host):
        python_path = cfg.python_binary.get()
        try:
            self._gw = multi.makegateway("ssh=root@%s//python=%s" % (host, python_path))
        except (gateway_bootstrap.HostNotFound, BrokenPipeError) as e:
            raise resources.HostNotFoundException(hostname=host, user="root", error=e)

    def _execute(self, function_name, *args):
        ch = self._gw.remote_exec(local)
        ch.send((function_name, args))
        result = ch.receive()
        ch.close()
        return result

    def read_binary(self, path):
        # remoting can turn this into a string
        result = self._execute("read_binary", path)
        if isinstance(result, str):
            return result.encode()
        return result

    def __getattr__(self, name):
        """
            Proxy a function call to the local version on the otherside of the
            channel.
        """
        def call(*args):
            result = self._execute(name, *args)
            return result

        return call

    def close(self):
        self._gw.exit()
