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
import inspect
from typing import Callable, Dict, List, Optional, TypeVar

from inmanta import const
from inmanta.types import Apireturn, HandlerType, MethodType

from . import common

FuncT = TypeVar("FuncT", bound=HandlerType)


class handle(object):  # noqa: N801
    """
    Decorator for subclasses of an endpoint to handle protocol methods

    :param method: A subclass of method that defines the method
    :param api_version: When specific this handler is only associated with a method of the specific api verision. If the
                        version is not defined, the handler is not associated with a rest endpoint.
    :param kwargs: Map arguments in the message from one name to an other
    """

    def __init__(self, method: Callable[..., Apireturn], api_version: Optional[int] = None, **kwargs: str) -> None:
        self.method = method
        self.mapping: Dict[str, str] = kwargs
        self._api_version = api_version

    def __call__(self, function: FuncT) -> FuncT:
        """
        The wrapping
        """
        if not inspect.iscoroutinefunction(function):
            raise ValueError(f"{function} is not an async function. Only async def functions may handle requests.")

        function.__protocol_method__ = self.method
        function.__protocol_mapping__ = self.mapping
        function.__api_version__ = self._api_version
        return function


MethodT = TypeVar("MethodT", bound=MethodType)


def method(
    path: str,
    operation: str = "POST",
    reply: bool = True,
    arg_options: Dict[str, common.ArgOption] = {},
    timeout: Optional[int] = None,
    server_agent: bool = False,
    api: Optional[bool] = None,
    agent_server: bool = False,
    validate_sid: Optional[bool] = None,
    client_types: List[const.ClientType] = [const.ClientType.api],
    api_version: int = 1,
    api_prefix: str = "api",
    envelope: bool = False,
    envelope_key: str = const.ENVELOPE_KEY,
) -> Callable[..., Callable]:
    """
    Decorator to identify a method as a RPC call. The arguments of the decorator are used by each transport to build
    and model the protocol.

    :param path: The url path to use for this call. This path can contain parameter names of the function. These names
        should be enclosed in < > brackets.
    :param operation: The type of HTTP operation (verb).
    :param timeout: nr of seconds before request it terminated.
    :param api: This is a call from the client to the Server (True if not server_agent and not agent_server).
    :param server_agent: This is a call from the Server to the Agent (reverse http channel through long poll).
    :param agent_server: This is a call from the Agent to the Server.
    :param validate_sid: This call requires a valid session, true by default if agent_server and not api
    :param client_types: The allowed client types for this call.
        The valid values are defined by the :const:`inmanta.const.ClientType` enum.
    :param arg_options: Options related to arguments passed to the method. The key of this dict is the name of the arg to
        which the options apply. The value is another dict that can contain the following options:

            header: Map this argument to a header with the following name.
            reply_header: If the argument is mapped to a header, this header will also be included in the reply
            getter: Call this method after validation and pass its return value to the method call. This may change the
            type of the argument. This method can raise an HTTPException to return a 404 for example.

    :param api_version: The version of the api this method belongs to.
    :param api_prefix: The prefix of the method: /<prefix>/v<version>/<method_name>.
    :param envelope: Put the response of the call under an envelope with key envelope_key.
    :param envelope_key: The envelope key to use.

    """

    def wrapper(func: MethodT) -> MethodT:
        properties = common.MethodProperties(
            func,
            path,
            operation,
            reply,
            arg_options,
            timeout,
            server_agent,
            api,
            agent_server,
            validate_sid,
            client_types,
            api_version,
            api_prefix,
            envelope,
            False,
            envelope_key,
        )
        common.MethodProperties.register_method(properties)
        return func

    return wrapper


def typedmethod(
    path: str,
    operation: str = "POST",
    reply: bool = True,
    arg_options: Dict[str, common.ArgOption] = {},
    timeout: Optional[int] = None,
    server_agent: bool = False,
    api: Optional[bool] = None,
    agent_server: bool = False,
    validate_sid: Optional[bool] = None,
    client_types: List[const.ClientType] = [const.ClientType.api],
    api_version: int = 1,
    api_prefix: str = "api",
    envelope_key: str = const.ENVELOPE_KEY,
    strict_typing: bool = True,
    varkw: bool = False,
) -> Callable[..., Callable]:
    """
    Decorator to identify a method as a RPC call. The arguments of the decorator are used by each transport to build
    and model the protocol.

    :param path: The url path to use for this call. This path can contain parameter names of the function. These names
                 should be enclosed in < > brackets.
    :param operation: The type of HTTP operation (verb)
    :param timeout: nr of seconds before request it terminated
    :param api: This is a call from the client to the Server (True if not server_agent and not agent_server)
    :param server_agent: This is a call from the Server to the Agent (reverse http channel through long poll)
    :param agent_server: This is a call from the Agent to the Server
    :param validate_sid: This call requires a valid session, true by default if agent_server and not api
    :param client_types: The allowed client types for this call.
            The valid values are defined by the :const:`inmanta.const.ClientType` enum.
    :param arg_options: Options related to arguments passed to the method. The key of this dict is the name of the arg to
        which the options apply. The value is another dict that can contain the following options:
            header: Map this argument to a header with the following name.
            reply_header: If the argument is mapped to a header, this header will also be included in the reply
            getter: Call this method after validation and pass its return value to the method call. This may change the
                    type of the argument. This method can raise an HTTPException to return a 404 for example.
    :param api_version: The version of the api this method belongs to
    :param api_prefix: The prefix of the method: /<prefix>/v<version>/<method_name>
    :param envelope_key: The envelope key to use.
    :param strict_typing: If true, does not allow `Any`. Setting this option to False is heavily discouraged except for some
        few very specific cases where the type system does not allow the strict type to be specified, for example in case of
        infinite recursion.
    :param varkw: If true, additional arguments are allowed and will be dispatched to the handler. The handler is
                  responsible for the validation.
    """

    def wrapper(func: MethodT) -> MethodT:
        properties = common.MethodProperties(
            func,
            path,
            operation,
            reply,
            arg_options,
            timeout,
            server_agent,
            api,
            agent_server,
            validate_sid,
            client_types,
            api_version,
            api_prefix,
            True,
            True,
            envelope_key,
            strict_typing=strict_typing,
            varkw=varkw,
        )
        common.MethodProperties.register_method(properties)
        return func

    return wrapper
