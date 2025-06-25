"""
Copyright 2025 Inmanta

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

import socket
from typing import Any

from tornado import netutil


class LoopResolverWithUnixSocketSuppport(netutil.DefaultLoopResolver):
    """
    A custom Tornado resolver that allows the Tornado client to connect to a UNIX socket.
    It extends the default Resolver (DefaultLoopResolver) in that it maps certain hostnames
    to a unix socket on disk. All other hostnames will resolve using the logic from
    DefaultLoopResolver.

    Inspired by: https://github.com/tornadoweb/tornado/issues/2671#issuecomment-499190469
    """

    _unix_sockets: dict[str, str] = {}
    """
    :param unix_sockets: A dictionary mapping hostnames to a unix socket on disk.
    """

    @classmethod
    def register_unix_socket(cls, hostname: str, path_unix_socket: str) -> None:
        """
        Make this Resolver resolve the given hostname to the given unix socket.
        """
        cls._unix_sockets[hostname] = path_unix_socket

    @classmethod
    def clear_unix_socket_registry(cls) -> None:
        """
        Clear all mappings from hostname to unix socket.
        """
        cls._unix_sockets.clear()

    async def resolve(self, host: str, port: int, family: socket.AddressFamily = socket.AF_UNSPEC) -> list[tuple[int, Any]]:
        if host in self._unix_sockets:
            return [(socket.AF_UNIX, self._unix_sockets[host])]
        return await super().resolve(host, port, family)


# Configure Tornado with our custom Resolver.
netutil.Resolver.configure(LoopResolverWithUnixSocketSuppport)
