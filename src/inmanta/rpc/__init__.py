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
import inspect

from urllib import parse

from typing import Any, Dict, Sequence, List, Optional, Union, Tuple, Set, Callable, Awaitable  # noqa: F401


class ArgOption(object):
    """
        Argument options to transform arguments before dispatch
    """

    def __init__(self, header: Optional[str] = None, reply_header: bool = True, getter: Optional[Awaitable] = None) -> None:
        """
            :param header: Map this argument to a header with the following name.
            :param reply_header: If the argument is mapped to a header, this header will also be included in the reply
            :param getter: Call this method after validation and pass its return value to the method call. This may change the
                           type of the argument. This method can raise an HTTPException to return a 404 for example.
        """
        self.header = header
        self.reply_header = reply_header
        self.getter = getter


def method(
    method_name: str,
    index: bool = False,
    id: bool = False,
    operation: str = "POST",
    reply: bool = True,
    arg_options: Dict[str, ArgOption] = {},
    timeout: Optional[int] = None,
    server_agent: bool = False,
    api: bool = True,
    agent_server: bool = False,
    validate_sid: bool = False,
    client_types: List[str] = ["public"],
    api_version: int = 1,
):
    def wrapper(func: Callable[..., Dict[str, Any]]) -> Callable[..., Dict[str, Any]]:
        MethodProperties(
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


class MethodProperties(object):
    """
        This class stores the information from a method definition
    """

    _methods: Dict[str, "MethodProperties"] = {}

    def __init__(
        self,
        function: Callable[..., Dict[str, Any]],
        method_name,
        index: bool,
        id: bool,
        operation: str,
        reply: bool,
        arg_options: Dict[str, ArgOption],
        timeout: Optional[int],
        server_agent: bool,
        api: bool,
        agent_server: bool,
        validate_sid: bool,
        client_types: List[str],
        api_version: int,
    ) -> None:
        """
            Decorator to identify a method as a RPC call. The arguments of the decorator are used by each transport to build
            and model the protocol.

            :param method_name: The method name in the url
            :param index: A method that returns a list of resources. The url of this method is only the method/resource name.
            :param id: This method requires an id of a resource. The python function should have an id parameter.
            :param operation: The type of HTTP operation (verb)
            :param timeout: nr of seconds before request it terminated
            :param api This is a call from the client to the Server (True if not server_agent and not agent_server)
            :param server_agent: This is a call from the Server to the Agent (reverse http channel through long poll)
            :param agent_server: This is a call from the Agent to the Server
            :param validate_sid: This call requires a valid session, true by default if agent_server and not api
            :param client_types: The allowed client types for this call
            :param arg_options: Options related to arguments passed to the method. The key of this dict is the name of the arg to
                                which the options apply.
            :param api_version: The version of the api this method belongs to

        """
        if api is None:
            api = not server_agent and not agent_server

        if validate_sid is None:
            validate_sid = agent_server and not api

        self._method_name = method_name
        self._index = index
        self._id = id
        self._operation = operation
        self._reply = reply
        self._arg_options = arg_options
        self._timeout = timeout
        self._server_agent = server_agent
        self._api = api
        self._agent_server = agent_server
        self._validate_sid = validate_sid
        self._client_types = client_types
        self._api_version = api_version
        self.function = function

        MethodProperties._methods[function.__name__] = self
        function.__method_properties__ = self

    def get_call_headers(self) -> Set[str]:
        """
            Returns the set of headers required to create call
        """
        headers = set()
        headers.add("Authorization")

        for arg in self._arg_options.values():
            if arg.header is not None:
                headers.add(arg.header)

        return headers

    def old_props(self) -> Dict[str, Any]:
        """
            Generate old style properties to be used during the refactor
        """
        return {
            "index": self._index,
            "id": self._id,
            "reply": self._reply,
            "operation": self._operation,
            "timeout": self._timeout,
            "api": self._api,
            "server_agent": self._server_agent,
            "agent_server": self._agent_server,
            "validate_sid": self._validate_sid,
            "arg_options": self._arg_options,
            "client_types": self._client_types,
            "method_name": self._method_name,
            "method": self.function,
        }

    def get_listen_url(self) -> str:
        """
            Create a listen url for this method
        """
        url = "/api/v%d" % self._api_version

        if self._id:
            url += "/%s/(?P<id>[^/]+)" % self._method_name
        elif self._index:
            url += "/%s" % self._method_name
        else:
            url += "/%s" % self._method_name

        return url

    def get_call_url(self, msg: Dict[str, str]) -> str:
        """
             Create a calling url for the client
        """
        url = "/api/v%d" % self._api_version

        if self._id:
            url += "/%s/%s" % (self._method_name, parse.quote(str(msg["id"]), safe=""))
        elif self._index:
            url += "/%s" % self._method_name
        else:
            url += "/%s" % self._method_name

        return url


class UrlMethod(object):
    """
        This class holds the method definition together with the API (url, method) information
    """
