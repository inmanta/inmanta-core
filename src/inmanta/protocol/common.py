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

import enum
import gzip
import importlib
import inspect
import io
import json
import logging
import re
import time
import uuid
from collections import defaultdict
from collections.abc import Coroutine, Iterable, MutableMapping
from datetime import datetime
from enum import Enum
from functools import partial
from inspect import Parameter
from typing import TYPE_CHECKING, Any, AsyncIterator, Callable, Generic, Optional, TypeVar, Union, cast, get_type_hints
from urllib import parse

import docstring_parser
import pydantic
import typing_inspect
from pydantic import ValidationError
from pydantic.main import create_model
from tornado import web
from tornado.httpclient import HTTPRequest

from inmanta import const, execute, types, util
from inmanta.data.model import BaseModel, DateTimeNormalizerModel
from inmanta.protocol.auth import auth
from inmanta.protocol.auth.decorators import AuthorizationMetadata
from inmanta.protocol.exceptions import BadRequest, BaseHttpException
from inmanta.protocol.openapi import model as openapi_model
from inmanta.stable_api import stable_api
from inmanta.types import ArgumentTypes, HandlerType, JsonType, MethodType, ReturnTypes

if TYPE_CHECKING:
    from inmanta.protocol.rest.client import RESTClient

    from .endpoints import CallTarget


LOGGER: logging.Logger = logging.getLogger(__name__)

HTML_ENCODING = "ISO-8859-1"
UTF8_ENCODING = "UTF-8"
CONTENT_TYPE = "Content-Type"
JSON_CONTENT = "application/json"
HTML_CONTENT = "text/html"
OCTET_STREAM_CONTENT = "application/octet-stream"
ZIP_CONTENT = "application/zip"
UTF8_CHARSET = "charset=UTF-8"
HTML_CONTENT_WITH_UTF8_CHARSET = f"{HTML_CONTENT}; {UTF8_CHARSET}"


class CallContext:
    """A context variable that provides more information about the current call context"""

    request_headers: dict[str, str]
    auth_token: Optional[auth.claim_type]
    auth_username: Optional[str]

    def __init__(
        self, request_headers: dict[str, str], auth_token: Optional[auth.claim_type], auth_username: Optional[str]
    ) -> None:
        self.request_headers = request_headers
        self.auth_token = auth_token
        self.auth_username = auth_username


class ArgOption:
    """
    Argument options to transform arguments before dispatch
    """

    def __init__(
        self,
        getter: Callable[[Any, dict[str, str]], Coroutine[Any, Any, Any]],
        # Type is Any to Any because it transforms from method to handler but in the current typing there is no link
        header: Optional[str] = None,
        reply_header: bool = True,
    ) -> None:
        """
        :param header: Map this argument to a header with the following name.
        :param reply_header: If the argument is mapped to a header, this header will also be included in the reply
        :param getter: Call this method after validation and pass its return value to the method call. This may change the
                       type of the argument. This method can raise an HTTPException to return a 404 for example.
        """
        self.header = header
        self.reply_header = reply_header
        self.getter = getter


class Request:
    """
    A protocol request
    """

    def __init__(self, url: str, method: str, headers: dict[str, str], body: Optional[JsonType]) -> None:
        self._url = url
        self._method = method
        self._headers = headers
        self._body = body
        # Reply ID is used to send back the result
        # If None, no reply is expected
        #  i.e. this call will immediately return, potentially even before the request is dispatched
        self._reply_id: Optional[uuid.UUID] = None

    @property
    def body(self) -> Optional[JsonType]:
        return self._body

    @property
    def url(self) -> str:
        return self._url

    @property
    def headers(self) -> dict[str, str]:
        return self._headers

    @property
    def method(self) -> str:
        return self._method

    def set_reply_id(self, reply_id: uuid.UUID) -> None:
        self._reply_id = reply_id

    def get_reply_id(self) -> Optional[uuid.UUID]:
        return self._reply_id

    reply_id = property(get_reply_id, set_reply_id)

    def to_dict(self) -> JsonType:
        return_dict: JsonType = {"url": self._url, "headers": self._headers, "body": self._body, "method": self._method}
        if self._reply_id is not None:
            return_dict["reply_id"] = self._reply_id

        return return_dict

    @classmethod
    def from_dict(cls, value: JsonType) -> "Request":
        reply_id: Optional[str] = None
        if "reply_id" in value:
            reply_id = cast(str, value["reply_id"])
            del value["reply_id"]

        req = Request(**value)

        if reply_id is not None:
            req.reply_id = uuid.UUID(reply_id)

        return req


T_co = TypeVar("T_co", bound=Union[None, ArgumentTypes], covariant=True)


class ReturnValue(Generic[T_co]):
    """
    An object that handlers can return to provide a response to a method call.
    """

    def __init__(
        self,
        status_code: int = 200,
        headers: MutableMapping[str, str] = {},
        response: Optional[T_co] = None,
        content_type: str = JSON_CONTENT,
        links: Optional[dict[str, str]] = None,
    ) -> None:
        self._status_code = status_code
        self._warnings: list[str] = []
        self._headers = headers
        self._headers[CONTENT_TYPE] = content_type
        self._content_type = content_type
        self._response = response
        self._links = links

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def headers(self) -> MutableMapping[str, str]:
        return self._headers

    def _get_without_envelope(self) -> ReturnTypes:
        """Get the body without an envelope specified"""
        if len(self._warnings):
            LOGGER.info("Got warnings for client but cannot transfer because no envelope is used.")

        if self._response is None:
            if len(self._warnings):
                return {"metadata": {"warnings": self._warnings}}
            return None

        return self._response

    def _get_with_envelope(self, envelope_key: str) -> ReturnTypes:
        """Get the body with an envelope specified"""
        response: dict[str, Any] = {}
        response[envelope_key] = self._response

        if len(self._warnings):
            response["metadata"] = {"warnings": self._warnings}
        if self._links:
            response["links"] = self._links

        return response

    def get_body(self, envelope: bool, envelope_key: str) -> ReturnTypes:
        """Get the response body.

        When the content_type of this ReturnValue is not 'application/json',
        the parameter `envelope` and `envelope_key` will be ignored. In that
        case, this method will behave as if envelope=False was used.

        :param envelope: Should the response be mapped into a data key
        :param envelope_key: The envelope key to use
        """
        if not envelope or self._headers[CONTENT_TYPE] != JSON_CONTENT:
            return self._get_without_envelope()
        else:
            return self._get_with_envelope(envelope_key)

    def add_warnings(self, warnings: list[str]) -> None:
        self._warnings.extend(warnings)

    def __repr__(self) -> str:
        return f"ReturnValue<code={self.status_code} headers=<{self.headers}> response=<{self._response}>>"

    def __str__(self) -> str:
        return repr(self)


class Response:
    """
    A response object of a call
    """

    @classmethod
    def create(
        cls,
        result: ReturnValue,
        envelope: bool,
        envelope_key: Optional[str] = None,
    ) -> "Response":
        """
        Create a response from a return value
        """
        return cls(status_code=result.status_code, headers=result.headers, body=result.get_body(envelope, envelope_key))

    def __init__(self, status_code: int, headers: MutableMapping[str, str], body: ReturnTypes = None) -> None:
        self._status_code = status_code
        self._headers = headers
        self._body = body

    @property
    def body(self) -> ReturnTypes:
        return self._body

    @property
    def headers(self) -> MutableMapping[str, str]:
        return self._headers

    @property
    def status_code(self) -> int:
        return self._status_code


class InvalidPathException(Exception):
    """This exception is raised when a path definition is invalid."""


class UrlPath:
    """Class to handle manipulation of method paths"""

    def __init__(self, path: str) -> None:
        self._path = path
        self._vars = self._parse_path()

    def _parse_path(self) -> list[str]:
        if self._path[0] != "/":
            raise InvalidPathException(f"{self._path} should start with a /")

        return re.findall("<([^<>]+)>", self._path)

    def validate_vars(self, method_vars: Iterable[str], function_name: str) -> None:
        """Are all variable defined in the method"""
        for var in self._vars:
            if var not in method_vars:
                raise InvalidPathException(f"Variable {var} in path {self._path} is not defined in function {function_name}.")

    @property
    def path(self) -> str:
        return self._path

    def generate_path(self, variables: dict[str, str]) -> str:
        """Create a path with all variables substituted"""
        path = self._path
        for var in self._vars:
            if var not in variables:
                raise KeyError(f"No value provided for variable {var}")
            path = path.replace(f"<{var}>", variables[var])

        return path

    def generate_regex_path(self) -> str:
        """Generate a path that uses regex named groups for tornado"""
        path = self._path
        for var in self._vars:
            path = path.replace(f"<{var}>", f"(?P<{var}>[^/]+)")

        return path

    def has_path_variable(self, var_name: str) -> bool:
        """
        Return True iff the given var_name is a path parameter of this UrlPath.
        """
        return var_name in self._vars


class InvalidMethodDefinition(Exception):
    """This exception is raised when the definition of a method is invalid."""


VALID_URL_ARG_TYPES = (Enum, uuid.UUID, str, float, int, bool, datetime)
VALID_SIMPLE_ARG_TYPES = (BaseModel, Enum, uuid.UUID, str, float, int, bool, datetime, bytes, pydantic.AnyUrl)


class MethodProperties:
    """
    This class stores the information from a method definition
    """

    methods: dict[str, list["MethodProperties"]] = defaultdict(list)

    @classmethod
    def register_method(cls, properties: "MethodProperties") -> None:
        """
        Register new method properties. Multiple properties on a method is supported but the (URL, API version) combination has
        to be unique.
        """
        current_list = [(x.path, x.api_version) for x in cls.methods[properties.function.__name__]]
        if (properties.path, properties.api_version) in current_list:
            raise Exception(
                f"Method {properties.function.__name__} already has a "
                f"method definition for api path {properties.path} and API version {properties.api_version}"
            )
        if (
            cls.methods[properties.function_name]
            and cls.methods[properties.function_name][-1].authorization_metadata is not None
        ):
            raise Exception(
                f"Method {properties.function_name} has a @method/@typedmethod annotation above an @auth annotation."
                " The @auth method always needs to be defined above the @method/@typedmethod annotations."
            )

        cls.methods[properties.function_name].append(properties)

    def __init__(
        self,
        function: MethodType,
        path: str,
        operation: str,
        reply: bool,
        arg_options: dict[str, ArgOption],
        timeout: Optional[int],
        server_agent: bool,
        api: Optional[bool],
        agent_server: bool,
        validate_sid: Optional[bool],
        client_types: list[const.ClientType],
        api_version: int,
        api_prefix: str,
        envelope: bool,
        typed: bool = False,
        envelope_key: str = const.ENVELOPE_KEY,
        strict_typing: bool = True,
        enforce_auth: bool = True,
        varkw: bool = False,
        token_param: str | None = None,
    ) -> None:
        """
        Decorator to identify a method as a RPC call. The arguments of the decorator are used by each transport to build
        and model the protocol.

        :param path: The path in the url
        :param operation: The type of HTTP operation (verb)
        :param timeout: nr of seconds before request it terminated
        :param api: This is a call from the client to the Server (True if not server_agent and not agent_server)
        :param server_agent: This is a call from the Server to the Agent (reverse http channel through long poll)
        :param agent_server: This is a call from the Agent to the Server
        :param validate_sid: This call requires a valid session, true by default if agent_server and not api
        :param client_types: The allowed client types for this call
        :param arg_options: Options related to arguments passed to the method. The key of this dict is the name of the arg
                            to which the options apply.
        :param api_version: The version of the api this method belongs to
        :param api_prefix: The prefix of the method: /<prefix>/v<version>/<method_name>
        :param envelope: Put the response of the call under an envelope key.
        :param typed: Is the method definition typed or not
        :param envelope_key: The envelope key to use
        :param strict_typing: If true, does not allow `Any` when validating argument types
        :param enforce_auth: When set to true authentication is enforced on this endpoint. When set to false, authentication is
                             not enforced, even if auth is enabled.
        :param varkw: If true, additional arguments are allowed and will be dispatched to the handler. The handler is
                      responsible for the validation.
        :param reply: If False, this is a fire-and-forget query: we will not wait for any result, just deliver the call
        :param token_param: The parameter that contains the authorization token or None if the authorization token
                            should be retrieved from the Authorization header.
        """
        if api is None:
            api = not server_agent and not agent_server

        if validate_sid is None:
            validate_sid = agent_server and not api

        assert not (enforce_auth and server_agent), "Can not authenticate the return channel"

        self._path = UrlPath(path)
        self.path = path
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
        self._api_prefix = api_prefix
        self._envelope = envelope
        self._envelope_key = envelope_key
        self._strict_typing = strict_typing
        self._enforce_auth = enforce_auth
        self.function = function
        self.function_name = function.__name__
        self._varkw: bool = varkw
        self._varkw_name: Optional[str] = None
        self._return_type: Optional[type] = None
        self.token_param = token_param

        self._parsed_docstring = docstring_parser.parse(text=function.__doc__, style=docstring_parser.DocstringStyle.REST)
        self._docstring_parameter_map = {p.arg_name: p.description for p in self._parsed_docstring.params}

        # validate client types
        for ct in self._client_types:
            if ct not in [client_type for client_type in const.ClientType]:
                raise InvalidMethodDefinition(f"Invalid client type {ct} specified for function {function}")

        self._validate_function_types(typed)
        self.argument_validator = self.arguments_to_pydantic()

        if not hasattr(self.function, "__method_properties__"):
            self.function.__method_properties__ = []
        self.function.__method_properties__.append(self)

        self.authorization_metadata: AuthorizationMetadata | None = None

    @classmethod
    def get_open_policy_agent_data(cls) -> dict[str, object]:
        """
        Return the information about the different endpoints that exist
        in the format used as data to Open Policy Agent.
        """
        endpoints = {}
        for method_properties_list in cls.methods.values():
            for method_properties in method_properties_list:
                auth_metadata = method_properties.authorization_metadata
                if auth_metadata is None:
                    continue
                endpoint_id = f"{method_properties.operation} {method_properties.get_full_path()}"
                environment_param = (
                    method_properties._get_argument_name_for_policy_engine(auth_metadata.environment_param)
                    if auth_metadata.environment_param
                    else None
                )
                endpoints[endpoint_id] = {
                    "client_types": [c.value for c in method_properties.client_types],
                    "auth_label": auth_metadata.auth_label.value,
                    "read_only": auth_metadata.read_only,
                    "environment_param": environment_param,
                }
        return {"endpoints": endpoints}

    def _get_argument_name_for_policy_engine(self, arg_name: str) -> str:
        """
        Return the name for the given argument as it should be fed into the access policy.

        :param arg_name: The name of the argument as mentioned in the method annotated with @method or @typedmethod.
        """
        if arg_name in self.arg_options and self.arg_options[arg_name].header:
            # Make sure we use the name of the header if the parameter was set using a header.
            # The data in the access policy needs to be structured like on the API, because
            # that is the structure that end-users know.
            header_name = self.arg_options[arg_name].header
            assert header_name is not None  # Make mypy happy
            return header_name
        else:
            return arg_name

    def is_external_interface(self) -> bool:
        """
        Returns False iff this endpoint is exclusively used by other software components
        (agent, scheduler, compiler, etc.).
        """
        if self._agent_server or self._server_agent:
            return False
        machine_to_machine_client_types = {const.ClientType.agent, const.ClientType.compiler}
        return len(set(self.client_types) - machine_to_machine_client_types) > 0

    @property
    def varkw(self) -> bool:
        """Does the method allow for a variable number of key/value arguments."""
        return self._varkw

    @property
    def enforce_auth(self) -> bool:
        return self._enforce_auth

    @property
    def return_type(self) -> type:
        if self._return_type is None:
            raise InvalidMethodDefinition("Only typed methods have a return type")
        return self._return_type

    def validate_arguments(self, values: dict[str, Any]) -> dict[str, Any]:
        """
        Validate methods arguments. Values is a dict with key/value pairs for the arguments (similar to kwargs). This method
        validates and converts types if required (e.g. str to int). The returns value has the correct typing to dispatch
        to method handlers.
        """
        try:
            out = self.argument_validator(**values)
            return {f: getattr(out, f) for f in self.argument_validator.model_fields.keys()}
        except ValidationError as e:
            error_msg = f"Failed to validate argument\n{str(e)}"
            LOGGER.exception(error_msg)
            raise BadRequest(error_msg, {"validation_errors": e.errors()})

    def arguments_to_pydantic(self) -> type[pydantic.BaseModel]:
        """
        Convert the method arguments to a pydantic model that allows to validate a message body with pydantic
        """
        sig = inspect.signature(self.function)

        def to_tuple(param: Parameter) -> tuple[object, Optional[object]]:
            if param.annotation is Parameter.empty:
                return (Any, param.default if param.default is not Parameter.empty else None)
            if param.default is not Parameter.empty:
                return (param.annotation, param.default)
            else:
                return (param.annotation, None)

        return create_model(
            f"{self.function_name}_arguments",
            **{param.name: to_tuple(param) for param in sig.parameters.values() if param.name != self._varkw_name},
            __base__=DateTimeNormalizerModel,
        )

    def arguments_in_url(self) -> bool:
        return self.operation == "GET"

    def _validate_function_types(self, typed: bool) -> None:
        """Validate the type hints used in the method definition.

        For arguments the following types are supported:
        - Simpletypes: BaseModel, datetime, Enum, uuid.UUID, str, float, int, bool
        - Simpletypes includes Any iff strict_typing == False
        - List[Simpletypes]: A list of simple types
        - Dict[str, Simpletypes]: A dict with string keys and simple types

        For return types:
        - Everything for arguments
        - None is allowed
        - ReturnValue with a type parameter. The type must be the allowed types for arguments or none
        """
        type_hints = get_type_hints(self.function)

        # TODO: only primitive types are allowed in the path
        # TODO: body and get does not work
        self._path.validate_vars(type_hints.keys(), str(self.function))

        if self.token_param is not None and self.token_param not in type_hints:
            raise InvalidMethodDefinition(f"token_param ({self.token_param}) is missing in parameters of method.")

        if not typed:
            return

        # now validate the arguments and return type
        full_spec = inspect.getfullargspec(self.function)
        for arg in full_spec.args:
            if arg not in type_hints:
                raise InvalidMethodDefinition(f"{arg} in function {self.function} has no type annotation.")
            self._validate_type_arg(
                arg, type_hints[arg], strict=self.strict_typing, allow_none_type=True, in_url=self.arguments_in_url()
            )

        if self.varkw:
            # check if a varkw is added to the method and has the type object
            if full_spec.varkw is None:
                raise InvalidMethodDefinition(
                    f"varkw is set to true in the annotation but there is no ** variable in method {self.function}. "
                    "Add `**kwargs: object` for example."
                )

            self._varkw_name = full_spec.varkw

            # if the variable is there, it needs to have the type object. All other specialisations need to be validated
            # by the handler itself.
            if type_hints[full_spec.varkw] is not object:
                raise InvalidMethodDefinition(f"The arguments **{full_spec.varkw} should have `object` as type annotation.")

        elif full_spec.varkw is not None:
            raise InvalidMethodDefinition(
                f"A key/value argument is only allowed when `varkw` is set to true in method {self.function}."
            )

        self._return_type = self._validate_return_type(type_hints["return"], strict=self.strict_typing)

    def _validate_return_type(self, arg_type: type, *, strict: bool = True) -> type:
        """Validate the return type"""
        # Note: we cannot call issubclass on a generic type!
        arg = "return type"

        def is_return_value_type(arg_type: type) -> bool:
            if typing_inspect.is_generic_type(arg_type):
                origin = typing_inspect.get_origin(arg_type)
                assert origin is not None  # Make mypy happy
                return types.issubclass(origin, ReturnValue)
            else:
                return False

        if is_return_value_type(arg_type):
            return_type = typing_inspect.get_args(arg_type, evaluate=True)[0]
            self._validate_type_arg(arg, return_type, strict=strict, allow_none_type=True)
            return return_type

        elif (
            not typing_inspect.is_generic_type(arg_type)
            and isinstance(arg_type, type)
            and types.issubclass(arg_type, ReturnValue)
        ):
            raise InvalidMethodDefinition("ReturnValue should have a type specified.")

        else:
            self._validate_type_arg(arg, arg_type, allow_none_type=True, strict=strict)
            return arg_type

    def _validate_type_arg(
        self, arg: str, arg_type: type, *, strict: bool = True, allow_none_type: bool = False, in_url: bool = False
    ) -> None:
        """Validate the given type arg recursively

        :param arg: The name of the argument
        :param arg_type: The annotated type fo the argument
        :param strict: If true, does not allow `Any`
        :param allow_none_type: If true, allow `None` as the type for this argument
        :param in_url: This argument is passed in the URL
        """
        if typing_inspect.is_new_type(arg_type):
            return self._validate_type_arg(
                arg,
                arg_type.__supertype__,
                strict=strict,
                allow_none_type=allow_none_type,
                in_url=in_url,
            )

        if arg_type is Any:
            if strict:
                raise InvalidMethodDefinition(f"Invalid type for argument {arg}: Any type is not allowed in strict mode")
            return

        if typing_inspect.is_union_type(arg_type):
            # Make sure there is only one list and one dict in the union, otherwise we cannot process the arguments
            cnt: dict[str, int] = defaultdict(int)
            for sub_arg in typing_inspect.get_args(arg_type, evaluate=True):
                self._validate_type_arg(arg, sub_arg, strict=strict, allow_none_type=allow_none_type, in_url=in_url)

                if typing_inspect.is_generic_type(sub_arg):
                    cnt[sub_arg.__name__] += 1

            for name, n in cnt.items():
                if n > 1:
                    raise InvalidMethodDefinition(f"Union of argument {arg} can contain only one generic {name}")

        elif typing_inspect.is_generic_type(arg_type):
            orig = typing_inspect.get_origin(arg_type)
            assert orig is not None  # Make mypy happy
            is_literal_type: bool = typing_inspect.is_literal_type(orig)

            if not is_literal_type and not types.issubclass(orig, (list, dict)):
                raise InvalidMethodDefinition(f"Type {arg_type} of argument {arg} can only be generic List, Dict or Literal")

            args = typing_inspect.get_args(arg_type, evaluate=True)
            if len(args) == 0:
                raise InvalidMethodDefinition(
                    f"Type {arg_type} of argument {arg} must have a type parameter:"
                    " non-parametrized List, Dict or Literal is not allowed."
                )
            elif is_literal_type:  # A generic Literal
                if not all(isinstance(a, Enum) for a in args):
                    raise InvalidMethodDefinition(f"Type {arg_type} of argument {arg} must be an instance of an Enum.")
            elif len(args) == 1:  # A generic list
                unsubscripted_arg = typing_inspect.get_origin(args[0]) if typing_inspect.get_origin(args[0]) else args[0]
                assert unsubscripted_arg is not None  # Make mypy happy
                if in_url and (types.issubclass(unsubscripted_arg, dict) or types.issubclass(unsubscripted_arg, list)):
                    raise InvalidMethodDefinition(
                        f"Type {arg_type} of argument {arg} is not allowed for {self.operation}, "
                        f"lists of dictionaries and lists of lists are not supported for GET requests"
                    )
                self._validate_type_arg(arg, args[0], strict=strict, allow_none_type=allow_none_type, in_url=in_url)

            elif len(args) == 2:  # Generic Dict
                if not types.issubclass(args[0], str):
                    raise InvalidMethodDefinition(
                        f"Type {arg_type} of argument {arg} must be a Dict with str keys and not {args[0].__name__}"
                    )
                unsubscripted_dict_value_arg = (
                    typing_inspect.get_origin(args[1]) if typing_inspect.get_origin(args[1]) else args[1]
                )
                assert unsubscripted_dict_value_arg is not None  # Make mypy happy
                if in_url and (typing_inspect.is_union_type(args[1]) or types.issubclass(unsubscripted_dict_value_arg, dict)):
                    raise InvalidMethodDefinition(
                        f"Type {arg_type} of argument {arg} is not allowed for {self.operation}, "
                        f"nested dictionaries and union types for dictionary values are not supported for GET requests"
                    )

                self._validate_type_arg(arg, args[1], strict=strict, allow_none_type=True, in_url=in_url)

            elif len(args) > 2:
                raise InvalidMethodDefinition(f"Failed to validate type {arg_type} of argument {arg}.")

        elif not in_url and types.issubclass(arg_type, VALID_SIMPLE_ARG_TYPES):
            pass
        elif in_url and types.issubclass(arg_type, VALID_URL_ARG_TYPES):
            pass
        elif allow_none_type and types.issubclass(arg_type, type(None)):
            # A check for optional arguments
            pass
        elif issubclass(arg_type, CallContext):
            raise InvalidMethodDefinition("CallContext should only be defined in the handler, not the method.")
        else:
            valid_types = ", ".join([x.__name__ for x in VALID_SIMPLE_ARG_TYPES])
            raise InvalidMethodDefinition(
                f"Type {arg_type.__name__} of argument {arg} must be one of {valid_types} or a List of these types or a "
                "Dict with str keys and values of these types."
            )

    @property
    def operation(self) -> str:
        return self._operation

    @property
    @stable_api
    def arg_options(self) -> dict[str, ArgOption]:
        return self._arg_options

    @property
    def timeout(self) -> Optional[int]:
        return self._timeout

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
    def client_types(self) -> list[const.ClientType]:
        return self._client_types

    @property
    def envelope(self) -> bool:
        return self._envelope

    @property
    def envelope_key(self) -> str:
        return self._envelope_key

    @property
    def strict_typing(self) -> bool:
        return self._strict_typing

    @property
    def api_version(self) -> int:
        return self._api_version

    @stable_api
    def get_long_method_description(self) -> Optional[str]:
        """
        Return the full description present in the docstring of the method, excluding the first paragraph.
        """
        return self._parsed_docstring.long_description

    @stable_api
    def get_short_method_description(self) -> Optional[str]:
        """
        Return the first paragraph of the description present in the docstring of the method.
        """
        return self._parsed_docstring.short_description

    def get_description_for_param(self, param_name: str) -> Optional[str]:
        """
        Return the description for a certain parameter present in the docstring.
        """
        return self._docstring_parameter_map.get(param_name, None)

    def _get_http_status_code_for_exception(self, exception_name: str) -> int:
        """
        Returns the HTTP status code for a given exception. Exceptions can be
        specified in two different ways:

        1) A fully qualified path to the exception.
        2) The name of the exception if the exception is defined in the
           inmanta.protocol.exceptions module.

        Status code 500 is returned for exceptions which don't extend BaseHttpException.
        """
        if "." in exception_name:
            # Exception name was specified with fully-qualified path
            splitted_exception_name = exception_name.rsplit(".", maxsplit=1)
            module_path = splitted_exception_name[0]
            cls_name = splitted_exception_name[1]
        else:
            # Exception should be located in the inmanta.protocol.exceptions module
            module_path = "inmanta.protocol.exceptions"
            cls_name = exception_name

        try:
            module = importlib.import_module(module_path)
            cls = module.__getattribute__(cls_name)
            if not inspect.isclass(cls) or BaseHttpException not in cls.mro():
                return 500
            cls_instance = cls()
            return cls_instance.to_status()
        except Exception:
            return 500

    def get_description_foreach_http_status_code(self) -> dict[int, str]:
        """
        This method return a mapping from the HTTP status code to
        the associated description specified in the docstring using
        the :returns: and :raises <exception>: statements.
        """
        result = {}

        # Get description for return statement
        if self._parsed_docstring.returns is not None and self._parsed_docstring.returns.description is not None:
            result[200] = self._parsed_docstring.returns.description
        else:
            result[200] = ""

        # Get descriptions for raises statements
        for raise_statement in self._parsed_docstring.raises:
            exception_name = raise_statement.type_name
            status_code = self._get_http_status_code_for_exception(exception_name)
            result[status_code] = raise_statement.description if raise_statement.description is not None else ""

        return result

    def get_call_headers(self) -> set[str]:
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
        url = "/%s/v%d" % (self._api_prefix, self._api_version)
        return url + self._path.generate_regex_path()

    def get_full_path(self) -> str:
        """
        Return the path of this endpoint including the api prefix and version number.
        """
        return f"/{self._api_prefix}/v{self._api_version}{self._path.path}"

    def get_call_url(self, msg: dict[str, str]) -> str:
        """
        Create a calling url for the client
        """
        url = "/%s/v%d" % (self._api_prefix, self._api_version)
        return url + self._path.generate_path({k: parse.quote(str(v), safe="") for k, v in msg.items()})

    def build_call(self, args: list[object], kwargs: dict[str, object] = {}) -> Request:
        """
        Build a call from the given arguments. This method returns the url, headers, and body for the call.
        """
        # create the message
        msg: dict[str, Any] = dict(kwargs)

        # map the argument in arg to names
        argspec = inspect.getfullargspec(self.function)
        for i in range(len(args)):
            msg[argspec.args[i]] = args[i]

        path_params = {k for k, v in msg.items() if v is not None and f"<{k}>" in self._path.path}

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
            qs_map = {k: v for k, v in msg.items() if v is not None and k not in path_params}
            # Preprocess dict and list parameters for GET
            params_to_add = {}
            already_processed_params = []
            for query_param_name, query_param_value in qs_map.items():
                if isinstance(query_param_value, dict):
                    # Add parameters from the dict as separate parameters for example
                    # param = { "key1": "val1", "key2": "val2" } to param.key1=val1 and param.key2=val2
                    params_to_add = {**params_to_add, **self._encode_dict_for_get(query_param_name, query_param_value)}
                    already_processed_params.append(query_param_name)
            for param in already_processed_params:
                del qs_map[param]
            qs_map.update(params_to_add)
            # encode arguments in url
            if len(qs_map) > 0:
                url += "?" + parse.urlencode(qs_map, True)

            body = None
        else:
            body = msg

        return Request(url=url, method=self.operation, headers=headers, body=body)

    def _encode_dict_for_get(
        self, query_param_name: str, query_param_value: dict[str, Union[Any, list[Any]]]
    ) -> dict[str, str]:
        """Dicts are encoded in the following manner: param = {'ab': 1, 'cd': 2} to param.abc=1&param.cd=2"""
        sub_dict = {f"{query_param_name}.{key}": value for key, value in query_param_value.items()}
        return sub_dict

    @stable_api
    def get_openapi_parameter_type_for(self, param_name: str) -> Optional[openapi_model.ParameterType]:
        """
        Return the openapi ParameterType for the parameter with the given param_name or None when the parameter
        with the given name is not an OpenAPI parameter (but a RequestBodyParameter for example).
        """
        if param_name in self.arg_options and self.arg_options[param_name].header:
            return openapi_model.ParameterType.header
        elif self._path.has_path_variable(param_name):
            return openapi_model.ParameterType.path
        elif self.arguments_in_url():
            return openapi_model.ParameterType.query
        else:
            return None


class UrlMethod:
    """
    This class holds the method definition together with the API (url, method) information

    :param properties: The properties of this method
    :param endpoint: The object on which this method is defined
    :param handler: The method to call on the endpoint
    :param method_name: The name of the method to call on the endpoint
    """

    def __init__(self, properties: MethodProperties, slice: "CallTarget", handler: HandlerType, method_name: str):
        self._properties = properties
        self._handler = handler
        self._slice = slice
        self._method_name = method_name

    @property
    def properties(self) -> MethodProperties:
        return self._properties

    @property
    def handler(self) -> HandlerType:
        return self._handler

    @property
    def endpoint(self) -> "CallTarget":
        return self._slice

    @property
    def method_name(self) -> str:
        return self._method_name

    @property
    def short_method_description(self) -> Optional[str]:
        """
        Return the first paragraph of the description present in the docstring of the method
        """
        return self._properties.get_short_method_description()

    @property
    def long_method_description(self) -> Optional[str]:
        """
        Return the full description present in the docstring of the method, excluding the first paragraph.
        """
        return self._properties.get_long_method_description()

    def get_operation(self) -> str:
        return self._properties.operation

    def get_path(self) -> str:
        """
        Returns the path part of the URL. Parameters in this path are templated using the <param> notation.
        """
        return self._properties.get_full_path()


# Util functions
def custom_json_encoder(o: object, tz_aware: bool = True) -> Union[ReturnTypes, util.JSONSerializable]:
    """
    A custom json encoder that knows how to encode other types commonly used by Inmanta
    """
    if isinstance(o, execute.util.Unknown):
        return const.UNKNOWN_STRING

    # handle common python types
    return util.api_boundary_json_encoder(o, tz_aware)


def attach_warnings(code: int, value: Optional[JsonType], warnings: Optional[list[str]]) -> tuple[int, JsonType]:
    if value is None:
        value = {}
    if warnings:
        meta = value.setdefault("metadata", {})
        warns = meta.setdefault("warnings", [])
        warns.extend(warnings)
    return code, value


def json_encode(value: object, tz_aware: bool = True) -> str:
    """Our json encode is able to also serialize other types than a dict."""
    # see json_encode in tornado.escape
    return json.dumps(value, default=partial(custom_json_encoder, tz_aware=tz_aware)).replace("</", "<\\/")


def gzipped_json(value: JsonType) -> tuple[bool, Union[bytes, str]]:
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
    return msg[0 : max_len - 3] + "..."


@stable_api
class Result:
    """
    A result of a method call
    """

    def __init__(
        self,
        code: int = 0,
        result: Optional[JsonType] = None,
        *,
        client: Optional["RESTClient"] = None,
        method_properties: Optional[MethodProperties] = None,
        environment: Optional[str] = None,
    ) -> None:
        """
        :param code: HTTP response code.
        :param result: HTTP response as a dictionary.
        :param client: A client that can perform HTTP requests.
        :param method_properties: The MethodProperties of the method called initially to produce this result.
        :param environment: The environment in which the initial call was performed, if any.
        """
        self._result = result
        self.code = code
        self._client: Optional["RESTClient"] = client

        self._callback: Optional[Callable[["Result"], None]] = None
        self._method_properties: Optional[MethodProperties] = method_properties
        self._environment = environment

    def get_result(self) -> Optional[JsonType]:
        """
        Only when the result is marked as available the result can be returned
        """
        if self.available():
            return self._result
        raise Exception("The result is not yet available")

    @property
    def result(self) -> Optional[JsonType]:
        return self.get_result()

    @result.setter
    def set_result(self, value: Optional[JsonType]) -> None:
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

    def callback(self, fnc: Callable[["Result"], None]) -> None:
        """
        Set a callback function that is to be called when the result is ready.
        """
        self._callback = fnc

    async def all(self) -> AsyncIterator[types.JsonType]:
        """
        Helper method to iterate over all individual items in this result object.
        This method will start at the first page and follow paging links.
        """

        if self._method_properties is None or self._client is None:
            raise Exception(
                "The all() method cannot be called on this Result object. Make sure you "
                "set the client and method_properties parameters when constructing "
                "a Result object manually (e.g. outside of a regular API call)."
            )

        result = self
        while result.code == 200:
            if not result.result:
                return

            page = result.result.get(self._method_properties.envelope_key, [])
            for item in page:
                yield item

            next_link_url = result.result.get("links", {}).get("next")

            if not next_link_url:
                return

            server_url = self._client._get_client_config()
            url = server_url + next_link_url
            headers = {"X-Inmanta-tid": self._environment} if self._environment else None
            request = HTTPRequest(url=url, method="GET", headers=headers)
            result = self._client._decode_response(
                await self._client.client.fetch(request), self._method_properties, self._environment
            )


class SessionManagerInterface:
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
