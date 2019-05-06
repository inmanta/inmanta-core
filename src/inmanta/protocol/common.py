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
import enum
import uuid
import logging
import json
import gzip
import io
import time

import jwt

from tornado import web
from urllib import parse
from typing import Any, Dict, List, Optional, Union, Tuple, Set, Callable, Generator, cast, TYPE_CHECKING  # noqa: F401

from inmanta import execute, const, util
from inmanta import config as inmanta_config
from inmanta.types import JsonType
from . import exceptions

if TYPE_CHECKING:
    from .endpoints import CallTarget


LOGGER: logging.Logger = logging.getLogger(__name__)


class ArgOption(object):
    """
        Argument options to transform arguments before dispatch
    """

    def __init__(self, header: Optional[str] = None, reply_header: bool = True, getter: Optional[Generator] = None) -> None:
        """
            :param header: Map this argument to a header with the following name.
            :param reply_header: If the argument is mapped to a header, this header will also be included in the reply
            :param getter: Call this method after validation and pass its return value to the method call. This may change the
                           type of the argument. This method can raise an HTTPException to return a 404 for example.
        """
        self.header = header
        self.reply_header = reply_header
        self.getter = getter


class Request(object):
    """
        A protocol request
    """

    def __init__(self, url: str, method: str, headers: Dict[str, str], body: Dict[str, Any]) -> None:
        self._url = url
        self._method = method
        self._headers = headers
        self._body = body
        self._reply_id: Optional[uuid.UUID] = None

    @property
    def body(self) -> Dict[str, Any]:
        return self._body

    @property
    def url(self) -> str:
        return self._url

    @property
    def headers(self) -> Dict[str, str]:
        return self._headers

    @property
    def method(self) -> str:
        return self._method

    def set_reply_id(self, reply_id: uuid.UUID) -> None:
        self._reply_id = reply_id

    def get_reply_id(self) -> Optional[uuid.UUID]:
        return self._reply_id

    reply_id = property(get_reply_id, set_reply_id)

    def to_dict(self) -> Dict[str, Any]:
        return_dict: Dict[str, Any] = {"url": self._url, "headers": self._headers, "body": self._body, "method": self._method}
        if self._reply_id is not None:
            return_dict["reply_id"] = self._reply_id

        return return_dict

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "Request":
        reply_id: Optional[str] = None
        if "reply_id" in value:
            reply_id = cast(str, value["reply_id"])
            del value["reply_id"]

        req = Request(**value)

        if reply_id is not None:
            req.reply_id = uuid.UUID(reply_id)

        return req


class Response(object):
    """
        A response object of a call
    """

    def __init__(self, status_code: int, headers: Dict[str, str], body: Optional[Dict[str, Any]] = None) -> None:
        self._status_code = status_code
        self._headers = headers
        self._body = body

    @property
    def body(self) -> Optional[Dict[str, Any]]:
        return self._body

    @property
    def headers(self) -> Dict[str, str]:
        return self._headers

    @property
    def status_code(self) -> int:
        return self._status_code


class MethodProperties(object):
    """
        This class stores the information from a method definition
    """

    methods: Dict[str, "MethodProperties"] = {}

    def __init__(
        self,
        function: Callable[..., Dict[str, Any]],
        method_name: str,
        index: bool,
        id: bool,
        operation: str,
        reply: bool,
        arg_options: Dict[str, ArgOption],
        timeout: Optional[int],
        server_agent: bool,
        api: Optional[bool],
        agent_server: bool,
        validate_sid: Optional[bool],
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
            :param arg_options: Options related to arguments passed to the method. The key of this dict is the name of the arg
                                to which the options apply.
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
        self._api: bool = api
        self._agent_server = agent_server
        self._validate_sid: bool = validate_sid
        self._client_types = client_types
        self._api_version = api_version
        self.function = function

        MethodProperties.methods[function.__name__] = self
        function.__method_properties__ = self

        # validate client types
        for ct in self._client_types:
            if ct not in const.VALID_CLIENT_TYPES:
                raise Exception("Invalid client type %s specified for function %s" % (ct, function))

    @property
    def operation(self) -> str:
        return self._operation

    @property
    def arg_options(self) -> Dict[str, ArgOption]:
        return self._arg_options

    @property
    def timeout(self) -> Optional[int]:
        return self._timeout

    @property
    def id(self) -> bool:
        return self._id

    @property
    def validate_sid(self) -> bool:
        return self._validate_sid

    @property
    def agent_server(self) -> bool:
        return self._agent_server

    @property
    def reply(self) -> bool:
        return self._reply

    @property
    def client_types(self) -> List[str]:
        return self._client_types

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

    def build_call(self, args: List, kwargs: Dict[str, Any] = {}) -> Request:
        """
            Build a call from the given arguments. This method returns the url, headers, and body for the call.
        """
        # create the message
        msg: Dict[str, Any] = dict(kwargs)

        # map the argument in arg to names
        argspec = inspect.getfullargspec(self.function)
        for i in range(len(args)):
            msg[argspec.args[i]] = args[i]

        url = self.get_call_url(msg)

        headers = {}

        for arg_name in list(msg.keys()):
            if isinstance(msg[arg_name], enum.Enum):  # Handle enum values "special"
                msg[arg_name] = msg[arg_name].name

            if arg_name in self.arg_options:
                opts = self.arg_options[arg_name]
                if opts.header:
                    headers[opts.header] = str(msg[arg_name])
                    del msg[arg_name]

        if self.operation not in ("POST", "PUT", "PATCH"):
            qs_map = msg.copy()
            if "id" in qs_map:
                del qs_map["id"]

            # encode arguments in url
            if len(qs_map) > 0:
                url += "?" + parse.urlencode(qs_map)

            body = None
        else:
            body = msg

        return Request(url=url, method=self.operation, headers=headers, body=body)


class UrlMethod(object):
    """
        This class holds the method definition together with the API (url, method) information

        :param properties: The properties of this method
        :param endpoint: The object on which this method is defined
        :param handler: The method to call on the endpoint
        :param method_name: The name of the method to call on the endpoint
    """

    def __init__(
        self,
        properties: MethodProperties,
        slice: "CallTarget",
        handler: Callable[..., Dict[int, Dict[str, Any]]],
        method_name: str,
    ):
        self._properties = properties
        self._handler = handler
        self._slice = slice
        self._method_name = method_name

    @property
    def properties(self) -> MethodProperties:
        return self._properties

    @property
    def handler(self) -> Callable[..., Dict[int, Dict[str, Any]]]:
        return self._handler

    @property
    def endpoint(self) -> "CallTarget":
        return self._slice

    @property
    def method_name(self) -> str:
        return self._method_name


# Util functions
def custom_json_encoder(o: object) -> Union[Dict, str, List]:
    """
        A custom json encoder that knows how to encode other types commonly used by Inmanta
    """
    if isinstance(o, execute.util.Unknown):
        return const.UNKNOWN_STRING

    # handle common python types
    return util.custom_json_encoder(o)


def attach_warnings(code: int, value: JsonType, warnings: Optional[List[str]]) -> Tuple[int, JsonType]:
    if warnings:
        meta = value.setdefault("metadata", {})
        warns = meta.setdefault("warnings", [])
        warns.extend(warnings)
    return code, value


def json_encode(value: JsonType) -> str:
    # see json_encode in tornado.escape
    return json.dumps(value, default=custom_json_encoder).replace("</", "<\\/")


def gzipped_json(value: JsonType) -> Tuple[bool, Union[bytes, str]]:
    json_string = json_encode(value)
    if len(json_string) < web.GZipContentEncoding.MIN_LENGTH:
        return False, json_string

    gzip_value = io.BytesIO()
    gzip_file = gzip.GzipFile(mode="w", fileobj=gzip_value, compresslevel=web.GZipContentEncoding.GZIP_LEVEL)

    gzip_file.write(json_string.encode())
    gzip_file.close()

    return True, gzip_value.getvalue()


def shorten(msg: str, max_len: int = 10) -> str:
    if len(msg) < max_len:
        return msg
    return msg[0: max_len - 3] + "..."


def encode_token(client_types: List[str], environment: str = None, idempotent: bool = False, expire: float = None) -> str:
    cfg = inmanta_config.AuthJWTConfig.get_sign_config()

    payload = {"iss": cfg.issuer, "aud": [cfg.audience], const.INMANTA_URN + "ct": ",".join(client_types)}

    if not idempotent:
        payload["iat"] = int(time.time())

        if cfg.expire > 0:
            payload["exp"] = int(time.time() + cfg.expire)
        elif expire is not None:
            payload["exp"] = int(time.time() + expire)

    if environment is not None:
        payload[const.INMANTA_URN + "env"] = environment

    return jwt.encode(payload, cfg.key, cfg.algo).decode()


def decode_token(token: str) -> Dict[str, str]:
    try:
        # First decode the token without verification
        header = jwt.get_unverified_header(token)
        payload = jwt.decode(token, verify=False)
    except Exception:
        raise exceptions.AccessDeniedException("Unable to decode provided JWT bearer token.")

    if "iss" not in payload:
        raise exceptions.AccessDeniedException("Issuer is required in token to validate.")

    cfg = inmanta_config.AuthJWTConfig.get_issuer(payload["iss"])
    if cfg is None:
        raise exceptions.AccessDeniedException("Unknown issuer for token")

    alg = header["alg"].lower()
    if alg == "hs256":
        key = cfg.key
    elif alg == "rs256":
        if "kid" not in header:
            raise exceptions.AccessDeniedException("A kid is required for RS256")
        kid = header["kid"]
        if kid not in cfg.keys:
            raise exceptions.AccessDeniedException(
                "The kid provided in the token does not match a known key. Check the jwks_uri or try "
                "restarting the server to load any new keys."
            )

        key = cfg.keys[kid]
    else:
        raise exceptions.AccessDeniedException("Algorithm %s is not supported." % alg)

    try:
        payload = dict(jwt.decode(token, key, audience=cfg.audience, algorithms=[cfg.algo]))
        ct_key = const.INMANTA_URN + "ct"
        payload[ct_key] = [x.strip() for x in payload[ct_key].split(",")]
    except Exception as e:
        raise exceptions.AccessDeniedException(*e.args)

    return payload


class Result(object):
    """
        A result of a method call
    """

    def __init__(self, code: int = 0, result: Dict[str, Any] = None):
        self._result = result
        self.code = code
        self._callback = None

    def get_result(self) -> Dict[str, Any]:
        """
            Only when the result is marked as available the result can be returned
        """
        if self.available():
            return self._result
        raise Exception("The result is not yet available")

    def set_result(self, value):
        if not self.available():
            self._result = value
            if self._callback:
                self._callback(self)

    def available(self) -> bool:
        return self._result is not None or self.code > 0

    def wait(self, timeout: int = 60) -> None:
        """
            Wait for the result to become available
        """
        count: float = 0
        while count < timeout:
            time.sleep(0.1)
            count += 0.1

    result = property(get_result, set_result)

    def callback(self, fnc):
        """
            Set a callback function that is to be called when the result is ready.
        """
        self._callback = fnc


class SessionManagerInterface(object):
    """
        An interface for a sessionmanager
    """
    def validate_sid(self, sid: uuid.UUID) -> bool:
        """
        Check if the given sid is a valid session
        :param sid: The session id
        :return: True if the session is valid
        """
        raise NotImplementedError()
