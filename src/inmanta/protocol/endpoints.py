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
from asyncio import run_coroutine_threadsafe
from collections import abc
from collections.abc import Coroutine
from typing import Any, Callable, Optional

from inmanta import config as inmanta_config
from inmanta import types, util
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

    def close(self):
        """
        Closes the RESTclient instance manually. This is only needed when it is started with force_instance set to true
        """
        self._transport_instance.close()

    async def _call(
        self, method_properties: common.MethodProperties, args: tuple[object, ...], kwargs: dict[str, object]
    ) -> common.Result:
        """
        Execute a call and return the result
        """
        result = await self._transport_instance.call(method_properties, args, kwargs)
        return result

    def __getattr__(self, name: str) -> Callable[..., Coroutine[Any, Any, common.Result]]:
        """
        Return a function that will call self._call with the correct method properties associated
        """
        method = common.MethodProperties.select_method(
            name, match_constraint=self._version_match, exact_version=self._exact_version
        )

        if method is None:
            raise AttributeError("Method with name %s is not defined for this client" % name)

        def wrap(*args: object, **kwargs: object) -> Coroutine[Any, Any, common.Result]:
            assert method
            method.function(*args, **kwargs)
            return self._call(method_properties=method, args=args, kwargs=kwargs)

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
        def async_call(*args: list[object], **kwargs: dict[str, object]) -> common.Result:
            method: Callable[..., abc.Awaitable[common.Result]] = getattr(self._client, name)
            with_timeout: abc.Awaitable[common.Result] = asyncio.wait_for(method(*args, **kwargs), self.timeout)

            try:
                if self._ioloop is None:
                    # no loop is running: create a loop for this thread if it doesn't exist already and run it
                    return util.ensure_event_loop().run_until_complete(with_timeout)
                else:
                    # loop is running on different thread
                    return run_coroutine_threadsafe(with_timeout, self._ioloop).result()
            except TimeoutError:
                raise ConnectionRefusedError()

        return async_call


class TypedClient(Client):
    """A client that returns typed data instead of JSON"""

    async def _call(
        self, method_properties: common.MethodProperties, args: list[object], kwargs: dict[str, object]
    ) -> types.ReturnTypes:
        """Execute a call and return the result"""
        return common.typed_process_response(method_properties, await super()._call(method_properties, args, kwargs))
