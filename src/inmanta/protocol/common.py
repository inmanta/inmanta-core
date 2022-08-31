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
from datetime import datetime
from enum import Enum
from inspect import Parameter
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Coroutine,
    Dict,
    Generic,
    Iterable,
    List,
    MutableMapping,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    get_type_hints,
)
from urllib import parse

import docstring_parser
import jwt
import pydantic
import typing_inspect
from pydantic.error_wrappers import ValidationError
from pydantic.main import create_model
from tornado import web

from inmanta import config as inmanta_config
from inmanta import const, execute, types, util
from inmanta.data.model import BaseModel, validator_timezone_aware_timestamps
from inmanta.protocol.exceptions import BadRequest, BaseHttpException
from inmanta.stable_api import stable_api
from inmanta.types import ArgumentTypes, HandlerType, JsonType, MethodType, ReturnTypes, StrictNonIntBool

from . import exceptions

if TYPE_CHECKING:
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


class ArgOption(object):
    """
    Argument options to transform arguments before dispatch
    """

    def __init__(
        self,
        getter: Callable[[Any, Dict[str, str]], Coroutine[Any, Any, Any]],
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


class Request(object):
    """
    A protocol request
    """

    def __init__(self, url: str, method: str, headers: Dict[str, str], body: Optional[JsonType]) -> None:
        self._url = url
        self._method = method
        self._headers = headers
        self._body = body
        self._reply_id: Optional[uuid.UUID] = None

    @property
    def body(self) -> Optional[JsonType]:
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


T = TypeVar("T", bound=Union[None, ArgumentTypes])


class ReturnValue(Generic[T]):
    """
    An object that handlers can return to provide a response to a method call.
    """

    def __init__(
        self,
        status_code: int = 200,
        headers: MutableMapping[str, str] = {},
        response: Optional[T] = None,
        content_type: str = JSON_CONTENT,
        links: Optional[Dict[str, str]] = None,
    ) -> None:
        self._status_code = status_code
        self._warnings: List[str] = []
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
        response: Dict[str, Any] = {}
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

    def add_warnings(self, warnings: List[str]) -> None:
        self._warnings.extend(warnings)

    def __repr__(self) -> str:
        return f"ReturnValue<code={self.status_code} headers=<{self.headers}> response=<{self._response}>>"

    def __str__(self) -> str:
        return repr(self)


class Response(object):
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


class UrlPath(object):
    """Class to handle manipulation of method paths"""

    def __init__(self, path: str) -> None:
        self._path = path
        self._vars = self._parse_path()

    def _parse_path(self) -> List[str]:
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

    def generate_path(self, variables: Dict[str, str]) -> str:
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


class InvalidMethodDefinition(Exception):
    """This exception is raised when the definition of a method is invalid."""


VALID_URL_ARG_TYPES = (Enum, uuid.UUID, str, float, int, bool, datetime)
VALID_SIMPLE_ARG_TYPES = (BaseModel, Enum, uuid.UUID, str, float, int, StrictNonIntBool, datetime, bytes)


class MethodArgumentsBaseModel(pydantic.BaseModel):

    _normalize_timestamps: ClassVar[classmethod] = pydantic.validator("*", allow_reuse=True)(
        validator_timezone_aware_timestamps
    )


class MethodProperties(object):
    """
    This class stores the information from a method definition
    """

    methods: Dict[str, List["MethodProperties"]] = defaultdict(list)

    @classmethod
    def register_method(cls, properties: "MethodProperties") -> None:
        """Register new method properties. Multiple properties on a method is supported but versions have to be unique."""
        current_list = [x.api_version for x in cls.methods[properties.function.__name__]]
        if properties.api_version in current_list:
            raise Exception(
                f"Method {properties.function.__name__} already has a "
                f"method definition for api version {properties.api_version}"
            )

        cls.methods[properties.function.__name__].append(properties)

    def __init__(
        self,
        function: MethodType,
        path: str,
        operation: str,
        reply: bool,
        arg_options: Dict[str, ArgOption],
        timeout: Optional[int],
        server_agent: bool,
        api: Optional[bool],
        agent_server: bool,
        validate_sid: Optional[bool],
        client_types: List[const.ClientType],
        api_version: int,
        api_prefix: str,
        envelope: bool,
        typed: bool = False,
        envelope_key: str = const.ENVELOPE_KEY,
        strict_typing: bool = True,
        varkw: bool = False,
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
        :param varkw: If true, additional arguments are allowed and will be dispatched to the handler. The handler is
                      responsible for the validation.
        """
        if api is None:
            api = not server_agent and not agent_server

        if validate_sid is None:
            validate_sid = agent_server and not api

        self._path = UrlPath(path)
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
        self.function = function
        self._varkw: bool = varkw
        self._varkw_name: Optional[str] = None

        self._parsed_docstring = docstring_parser.parse(text=function.__doc__, style=docstring_parser.DocstringStyle.REST)
        self._docstring_parameter_map = {p.arg_name: p.description for p in self._parsed_docstring.params}

        # validate client types
        for ct in self._client_types:
            if ct not in [client_type for client_type in const.ClientType]:
                raise InvalidMethodDefinition("Invalid client type %s specified for function %s" % (ct, function))

        self._validate_function_types(typed)
        self.argument_validator = self.arguments_to_pydantic()

    @property
    def varkw(self) -> bool:
        """Does the method allow for a variable number of key/value arguments."""
        return self._varkw

    def validate_arguments(self, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate methods arguments. Values is a dict with key/value pairs for the arguments (similar to kwargs). This method
        validates and converts types if required (e.g. str to int). The returns value has the correct typing to dispatch
        to method handlers.
        """
        try:
            out = self.argument_validator(**values)
            return {f: getattr(out, f) for f in out.__fields__.keys()}
        except ValidationError as e:
            error_msg = f"Failed to validate argument\n{str(e)}"
            LOGGER.exception(error_msg)
            raise BadRequest(error_msg, {"validation_errors": e.errors()})

    def arguments_to_pydantic(self) -> Type[pydantic.BaseModel]:
        """
        Convert the method arguments to a pydantic model that allows to validate a message body with pydantic
        """
        sig = inspect.signature(self.function)

        def to_tuple(param: Parameter) -> Tuple[object, Optional[object]]:
            if param.annotation is Parameter.empty:
                return (Any, param.default if param.default is not Parameter.empty else None)
            if param.default is not Parameter.empty:
                return (param.annotation, param.default)
            else:
                return (param.annotation, None)

        return create_model(
            f"{self.function.__name__}_arguments",
            **{param.name: to_tuple(param) for param in sig.parameters.values() if param.name != self._varkw_name},
            __base__=MethodArgumentsBaseModel,
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

        self._validate_return_type(type_hints["return"], strict=self.strict_typing)

    def _validate_return_type(self, arg_type: Type, *, strict: bool = True) -> None:
        """Validate the return type"""
        # Note: we cannot call issubclass on a generic type!
        arg = "return type"

        def is_return_value_type(arg_type: Type) -> bool:
            if typing_inspect.is_generic_type(arg_type):
                origin = typing_inspect.get_origin(arg_type)
                assert origin is not None  # Make mypy happy
                return types.issubclass(origin, ReturnValue)
            else:
                return False

        if is_return_value_type(arg_type):
            self._validate_type_arg(
                arg, typing_inspect.get_args(arg_type, evaluate=True)[0], strict=strict, allow_none_type=True
            )

        elif (
            not typing_inspect.is_generic_type(arg_type)
            and isinstance(arg_type, type)
            and types.issubclass(arg_type, ReturnValue)
        ):
            raise InvalidMethodDefinition("ReturnValue should have a type specified.")

        else:
            self._validate_type_arg(arg, arg_type, allow_none_type=True, strict=strict)

    def _validate_type_arg(
        self, arg: str, arg_type: Type, *, strict: bool = True, allow_none_type: bool = False, in_url: bool = False
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
            cnt: Dict[str, int] = defaultdict(lambda: 0)
            for sub_arg in typing_inspect.get_args(arg_type, evaluate=True):
                self._validate_type_arg(arg, sub_arg, strict=strict, allow_none_type=allow_none_type, in_url=in_url)

                if typing_inspect.is_generic_type(sub_arg):
                    # there is a difference between python 3.6 and >=3.7
                    if hasattr(sub_arg, "__name__"):
                        cnt[sub_arg.__name__] += 1
                    else:
                        cnt[sub_arg._name] += 1

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
                    f"Type {arg_type} of argument {arg} must be have a subtype plain List, Dict or Literal is not allowed."
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
        else:
            valid_types = ", ".join([x.__name__ for x in VALID_SIMPLE_ARG_TYPES])
            raise InvalidMethodDefinition(
                f"Type {arg_type.__name__} of argument {arg} must be a either {valid_types} or a List of these types or a "
                "Dict with str keys and values of these types."
            )

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
    def validate_sid(self) -> bool:
        return self._validate_sid

    @property
    def agent_server(self) -> bool:
        return self._agent_server

    @property
    def reply(self) -> bool:
        return self._reply

    @property
    def client_types(self) -> List[const.ClientType]:
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

    def get_long_method_description(self) -> Optional[str]:
        """
        Return the full description present in the docstring of the method, excluding the first paragraph.
        """
        return self._parsed_docstring.long_description

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

    def get_description_foreach_http_status_code(self) -> Dict[int, str]:
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
            result[status_code] = raise_statement.description

        return result

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
        url = "/%s/v%d" % (self._api_prefix, self._api_version)
        return url + self._path.generate_regex_path()

    def get_call_url(self, msg: Dict[str, str]) -> str:
        """
        Create a calling url for the client
        """
        url = "/%s/v%d" % (self._api_prefix, self._api_version)
        return url + self._path.generate_path({k: parse.quote(str(v), safe="") for k, v in msg.items()})

    def build_call(self, args: List[object], kwargs: Dict[str, object] = {}) -> Request:
        """
        Build a call from the given arguments. This method returns the url, headers, and body for the call.
        """
        # create the message
        msg: Dict[str, Any] = dict(kwargs)

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
        self, query_param_name: str, query_param_value: Dict[str, Union[Any, List[Any]]]
    ) -> Dict[str, str]:
        """Dicts are encoded in the following manner: param = {'ab': 1, 'cd': 2} to param.abc=1&param.cd=2"""
        sub_dict = {f"{query_param_name}.{key}": value for key, value in query_param_value.items()}
        return sub_dict


class UrlMethod(object):
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


# Util functions
def custom_json_encoder(o: object) -> Union[ReturnTypes, util.JSONSerializable]:
    """
    A custom json encoder that knows how to encode other types commonly used by Inmanta
    """
    if isinstance(o, execute.util.Unknown):
        return const.UNKNOWN_STRING

    # handle common python types
    return util.api_boundary_json_encoder(o)


def attach_warnings(code: int, value: Optional[JsonType], warnings: Optional[List[str]]) -> Tuple[int, JsonType]:
    if value is None:
        value = {}
    if warnings:
        meta = value.setdefault("metadata", {})
        warns = meta.setdefault("warnings", [])
        warns.extend(warnings)
    return code, value


def json_encode(value: ReturnTypes) -> str:
    """Our json encode is able to also serialize other types than a dict."""
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
    return msg[0 : max_len - 3] + "..."


def encode_token(
    client_types: List[str], environment: Optional[str] = None, idempotent: bool = False, expire: Optional[float] = None
) -> str:
    cfg = inmanta_config.AuthJWTConfig.get_sign_config()
    if cfg is None:
        raise Exception("No JWT signing configuration available.")

    payload: Dict[str, Any] = {"iss": cfg.issuer, "aud": [cfg.audience], const.INMANTA_URN + "ct": ",".join(client_types)}

    if not idempotent:
        payload["iat"] = int(time.time())

        if cfg.expire > 0:
            payload["exp"] = int(time.time() + cfg.expire)
        elif expire is not None:
            payload["exp"] = int(time.time() + expire)

    if environment is not None:
        payload[const.INMANTA_URN + "env"] = environment

    return jwt.encode(payload, cfg.key, cfg.algo)


def decode_token(token: str) -> Dict[str, str]:
    try:
        # First decode the token without verification
        header = jwt.get_unverified_header(token)
        payload = jwt.decode(token, options={"verify_signature": False})
    except Exception:
        raise exceptions.Forbidden("Unable to decode provided JWT bearer token.")

    if "iss" not in payload:
        raise exceptions.Forbidden("Issuer is required in token to validate.")

    cfg = inmanta_config.AuthJWTConfig.get_issuer(payload["iss"])
    if cfg is None:
        raise exceptions.Forbidden("Unknown issuer for token")

    alg = header["alg"].lower()
    if alg == "hs256":
        key = cfg.key
    elif alg == "rs256":
        if "kid" not in header:
            raise exceptions.Forbidden("A kid is required for RS256")
        kid = header["kid"]
        if kid not in cfg.keys:
            raise exceptions.Forbidden(
                "The kid provided in the token does not match a known key. Check the jwks_uri or try "
                "restarting the server to load any new keys."
            )

        key = cfg.keys[kid]
    else:
        raise exceptions.Forbidden("Algorithm %s is not supported." % alg)

    try:
        payload = dict(jwt.decode(token, key, audience=cfg.audience, algorithms=[cfg.algo]))
        ct_key = const.INMANTA_URN + "ct"
        payload[ct_key] = [x.strip() for x in payload[ct_key].split(",")]
    except Exception as e:
        raise exceptions.Forbidden(*e.args)

    return payload


@stable_api
class Result(object):
    """
    A result of a method call
    """

    def __init__(self, code: int = 0, result: Optional[JsonType] = None) -> None:
        self._result = result
        self.code = code
        """
        The result code of the method call.
        """
        self._callback: Optional[Callable[["Result"], None]] = None

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
