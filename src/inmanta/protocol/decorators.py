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
from asyncio import Future
from . import common

from typing import Any, Dict, List, Optional, Tuple, Set, Callable, Generator  # noqa: F401


class handle(object):  # noqa: N801
    """
        Decorator for subclasses of an endpoint to handle protocol methods

        :param method A subclass of method that defines the method
        :param kwargs: Map arguments in the message from one name to an other
    """

    def __init__(self, method: Callable[..., Any], **kwargs: str) -> None:
        self.method = method
        self.mapping: Dict[str, str] = kwargs

    def __call__(self, function: Callable[..., Future]):
        """
            The wrapping
        """
        function.__protocol_method__ = self.method
        function.__protocol_mapping__ = self.mapping
        return function


def method(
    method_name: str,
    index: bool = False,
    id: bool = False,
    operation: str = "POST",
    reply: bool = True,
    arg_options: Dict[str, common.ArgOption] = {},
    timeout: Optional[int] = None,
    server_agent: bool = False,
    api: bool = None,
    agent_server: bool = False,
    validate_sid: bool = None,
    client_types: List[str] = ["public"],
    api_version: int = 1,
) -> Callable[..., Callable]:
    """
        Decorator to identify a method as a RPC call. The arguments of the decorator are used by each transport to build
        and model the protocol.

        :param index: A method that returns a list of resources. The url of this method is only the method/resource name.
        :param id: This method requires an id of a resource. The python function should have an id parameter.
        :param operation: The type of HTTP operation (verb)
        :param timeout: nr of seconds before request it terminated
        :param api This is a call from the client to the Server (True if not server_agent and not agent_server)
        :param server_agent: This is a call from the Server to the Agent (reverse http channel through long poll)
        :param agent_server: This is a call from the Agent to the Server
        :param validate_sid: This call requires a valid session, true by default if agent_server and not api
        :param client_types: The allowed client types for this call
        :param arg_options Options related to arguments passed to the method. The key of this dict is the name of the arg to
            which the options apply. The value is another dict that can contain the following options:
                header: Map this argument to a header with the following name.
                reply_header: If the argument is mapped to a header, this header will also be included in the reply
                getter: Call this method after validation and pass its return value to the method call. This may change the
                        type of the argument. This method can raise an HTTPException to return a 404 for example.
    """

    def wrapper(func: Callable[..., Dict[str, Any]]) -> Callable[..., Dict[str, Any]]:
        common.MethodProperties(
            func,
            method_name,
            index,
            id,
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
        )
        return func

    return wrapper
