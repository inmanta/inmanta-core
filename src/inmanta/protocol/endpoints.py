"""
Copyright 2019 Inmanta

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

import asyncio
import logging
import socket
from collections.abc import Awaitable, Sequence
from typing import Callable, Optional

from inmanta import types
from inmanta.protocol import common
from inmanta.protocol.common import VersionMatch
from inmanta.protocol.rest import client
from inmanta.util import TaskHandler

LOGGER: logging.Logger = logging.getLogger(__name__)


class Endpoint(TaskHandler[None]):
    """
    An end-point in the rpc framework
    """

    def __init__(self, name: str):
        super().__init__()
        self._name: str = name
        self._targets: list[common.CallTarget] = []

    def add_call_target(self, target: common.CallTarget) -> None:
        self._targets.append(target)

    @property
    def call_targets(self) -> list[common.CallTarget]:
        return self._targets

    name = property(lambda self: self._name)

    def _get_hostname(self) -> str:
        """
        Determine the hostname of this machine
        """
        return socket.gethostname()


class Client(Endpoint):
    """
    A client that communicates with end-point based on its configuration
    """

    def __init__(
        self,
        name: str,
        timeout: int = 120,
        version_match: VersionMatch = VersionMatch.lowest,
        exact_version: int = 0,
        with_rest_client: bool = True,
        force_instance: bool = False,
    ) -> None:
        super().__init__(name)
        assert isinstance(timeout, int), "Timeout needs to be an integer value."
        LOGGER.debug("Start transport for client %s", self.name)
        if with_rest_client:
            self._transport_instance = client.RESTClient(self, connection_timout=timeout, force_instance=force_instance)
        else:
            self._transport_instance = None
        self._version_match = version_match
        self._exact_version = exact_version

    def close(self) -> None:
        """
        Closes the RESTclient instance manually. This is only needed when it is started with force_instance set to true
        """
        self._transport_instance.close()

    async def _call[R: types.ReturnTypes](
        self, method_properties: common.MethodProperties[R], args: Sequence[object], kwargs: dict[str, object]
    ) -> common.Result[R]:
        """
        Execute a call and return the result
        """
        return await self._transport_instance.call(method_properties, args, kwargs)

    def __getattr__(self, name: str) -> Callable[..., common.ClientCall]:
        """
        Return a function that will call self._call with the correct method properties associated
        """
        method = common.MethodProperties.select_method(
            name, match_constraint=self._version_match, exact_version=self._exact_version
        )

        if method is None:
            raise AttributeError("Method with name %s is not defined for this client" % name)

        def wrap(*args: object, **kwargs: object) -> common.ClientCall:
            assert method
            return common.ClientCall.create(self._call(method_properties=method, args=args, kwargs=kwargs), properties=method)

        return wrap


class SyncClient:
    """
    A synchronous client that communicates with end-point based on its configuration
    """

    def __init__(
        self,
        name: Optional[str] = None,
        timeout: int = 120,
        client: Optional[Client] = None,
        ioloop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        """
        either name or client is required.
        they can not be used at the same time

        :param name: name of the configuration to use for this endpoint. The config section used is "{name}_rest_transport"
        :param client: the client to use for this sync_client
        :param timeout: http timeout on all requests

        :param ioloop: the specific (running) ioloop to schedule this request on. The loop should run on a different thread
            than the one the client methods are called on. If no ioloop is passed, we assume there is no running ioloop in the
            context where this syncclient is used.
        """
        if (name is None) == (client is None):
            # Exactly one must be set
            raise Exception("Either name or client needs to be provided.")

        self.timeout = timeout
        self._ioloop: Optional[asyncio.AbstractEventLoop] = ioloop
        if client is None:
            assert name is not None  # Make mypy happy
            self.name = name
            self._client = Client(name, self.timeout)
        else:
            self.name = client.name
            self._client = client

    def __getattr__(self, name: str) -> Callable[..., common.Result]:
        async_method = getattr(self._client, name)
        return lambda *args, **kwargs: async_method(*args, **kwargs).sync(timeout=self.timeout, ioloop=self._ioloop)


class TypedClient(Client):
    """
    A client that returns typed data instead of JSON. Deprecated in favor of ClientCall/Result.value().
    """

    def __init__(
        self,
        name: str,
        timeout: int = 120,
        version_match: VersionMatch = VersionMatch.lowest,
        exact_version: int = 0,
        with_rest_client: bool = True,
        force_instance: bool = False,
    ) -> None:
        LOGGER.warning(
            "The TypedClient has been deprecated. Please use the normal client as `client.method_call().value()` instead"
        )
        super().__init__(name, timeout, version_match, exact_version, with_rest_client, force_instance)

    def __getattr__(self, name: str) -> Callable[..., Awaitable[types.ReturnTypes]]:
        call: Callable[..., common.ClientCall] = super().__getattr__(name)
        return lambda *args, **kwargs: call(*args, **kwargs).value()
