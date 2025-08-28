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

import abc
import copy
import inspect
import json
import logging
import uuid
from collections.abc import Mapping, Sequence
from typing import Any, Dict, List, Optional, Tuple, Type, cast, get_type_hints  # noqa: F401

import pydantic
import typing_inspect
from tornado import escape

from inmanta import const, tracing, util
from inmanta.data.model import BaseModel
from inmanta.protocol import common, exceptions
from inmanta.protocol.auth import auth, providers
from inmanta.protocol.common import ReturnValue
from inmanta.server import config as server_config
from inmanta.stable_api import stable_api
from inmanta.types import Apireturn, JsonType

LOGGER: logging.Logger = logging.getLogger(__name__)

"""

RestServer  => manages tornado/handlers, marshalling, dispatching, and endpoints

ServerSlice => contributes handlers and methods

ServerSlice.server [1] -- RestServer.endpoints [1:]

"""


class CallArguments:
    """
    This class represents the call arguments for a method call.
    """

    def __init__(
        self,
        config: common.UrlMethod,
        message: dict[str, Optional[object]],
        request_headers: Mapping[str, str],
    ) -> None:
        """
        :param config: The method configuration that contains the metadata and functions to call
        :param message: The message received by the RPC call
        :param request_headers: The headers received by the RPC call
        :param handler: The handler for the call
        """
        self._config = config
        self._properties = self._config.properties
        self._message = message
        self._request_headers = request_headers
        self._argspec: inspect.FullArgSpec = inspect.getfullargspec(self._properties.function)

        self._call_args: JsonType = {}
        self._policy_engine_call_args: JsonType = {}
        self._headers: dict[str, str] = {}
        self._metadata: dict[str, object] = {}
        self._auth_token: Optional[auth.claim_type] = None
        self._auth_username: Optional[str] = None

        self._processed: bool = False

    @property
    def method_properties(self) -> common.MethodProperties:
        return self._properties

    @property
    def config(self) -> common.UrlMethod:
        return self._config

    @property
    def auth_token(self) -> auth.claim_type | None:
        return self._auth_token

    @property
    def call_args(self) -> dict[str, object]:
        """
        The arguments formatted according to the signature of the @handle method of the API endpoint.
        """
        if not self._processed:
            raise Exception("Process call first before accessing property")

        return self._call_args

    @property
    def policy_engine_call_args(self) -> dict[str, object]:
        """
        The call arguments formatted according to what the policy engine needs as input,
        i.e. the name of every parameter is the name of the parameter or header on the API.
        """
        if not self._processed:
            raise Exception("Process call first before accessing property")

        return self._policy_engine_call_args

    @property
    def auth_username(self) -> Optional[str]:
        if not self._processed:
            raise Exception("Process call first before accessing property")

        return self._auth_username

    @property
    def headers(self) -> dict[str, str]:
        if not self._processed:
            raise Exception("Process call first before accessing property")

        return self._headers

    @property
    def metadata(self) -> dict[str, object]:
        if not self._processed:
            raise Exception("Process call first before accessing property")

        return self._metadata

    def _is_header_param(self, arg: str) -> bool:
        """
        Return True if the given call argument can be provided using a header parameter.
        """
        if arg not in self._properties.arg_options:
            return False

        opts = self._properties.arg_options[arg]
        return opts.header is not None

    def _is_header_param_provided(self, arg: str) -> bool:
        """
        Return True iff a value for the given call argument was provided using a header parameter.

        :raise Exception: The given call argument is not a header parameter.
        """
        value = self._get_header_value_for(arg)
        return value is not None

    def _get_header_value_for(self, arg: str) -> Optional[str]:
        """
        Return the header value that belongs to the given call argument or None when the header was not set.

        :raise Exception: The given call argument is not a header parameter.
        """
        if not self._is_header_param(arg):
            raise Exception(f"Parameter {arg} is not a header parameter")
        opts = self._properties.arg_options[arg]
        return self._request_headers.get(opts.header)

    def _map_headers(self, arg: str) -> Optional[object]:
        if not self._is_header_param(arg):
            return None

        opts = self._properties.arg_options[arg]
        assert opts.header is not None

        value = self._request_headers.get(opts.header)
        if opts.reply_header and value is not None:
            self._headers[opts.header] = value

        return value

    def get_default_value(self, arg_name: str, arg_position: int, default_start: int) -> Optional[object]:
        """
        Get a default value for an argument
        """
        if self._argspec.defaults and default_start >= 0 and 0 <= (arg_position - default_start) < len(self._argspec.defaults):
            return self._argspec.defaults[arg_position - default_start]
        else:
            raise exceptions.BadRequest("Field '%s' is required." % arg_name)

    async def _run_getters(self, arg: str, value: Optional[object]) -> Optional[object]:
        """
        Run any available getters on value
        """
        if arg not in self._properties.arg_options or self._properties.arg_options[arg].getter is None:
            return value

        try:
            value = await self._properties.arg_options[arg].getter(value, self._metadata)
            return value
        except Exception as e:
            LOGGER.exception("Failed to use getter for arg %s", arg)
            raise e

    @staticmethod
    def _ensure_list_if_list_type(arg_type: Optional[Type[object]], arg_value: object) -> object:
        """
        Handles processing of arguments for GET requests, especially for list types encoded as URL query parameters.
        If a GET endpoint has a parameter of type list that is encoded as a URL query parameter and the specific request
        provides a list with one element, urllib doesn't parse it as a list. Map it here explicitly to a list.
        """
        if typing_inspect.is_optional_type(arg_type):
            non_none_arg_types = [arg for arg in typing_inspect.get_args(arg_type) if arg is not type(None)]
            if len(non_none_arg_types) == 1:
                arg_type = non_none_arg_types[0]

        is_generic_list = (
            arg_type and typing_inspect.is_generic_type(arg_type) and issubclass(typing_inspect.get_origin(arg_type), Sequence)
        )
        is_single_type_list = len(typing_inspect.get_args(arg_type, evaluate=True)) == 1
        arg_value_is_not_list = not isinstance(arg_value, Sequence) or isinstance(arg_value, str)

        if is_generic_list and is_single_type_list and arg_value_is_not_list:
            return [arg_value]
        return arg_value

    def _validate_argument_consistency(self, args):
        """
        Validates the consistency of arguments, ensuring they are not passed both as a header and a non-header value.
        """
        for arg in args:
            if arg in self._message and self._is_header_param(arg) and self._is_header_param_provided(arg):
                message_value = self._message[arg]
                header_value = self._get_header_value_for(arg)
                if message_value != header_value:
                    raise exceptions.BadRequest(
                        f"Value for argument {arg} was provided via a header and a non-header argument, but both values"
                        f" don't match (header={header_value}; non-header={message_value})"
                    )

    def get_call_context(self) -> Optional[str]:
        """Returns the name of the first handler argument that is of type CallContext"""
        for arg, hint in self._config.handler.__annotations__.items():
            if isinstance(hint, type) and issubclass(hint, common.CallContext):
                return arg
        return None

    async def process(self) -> None:
        """
        Process the request
        """
        args: list[str] = list(self._argspec.args)

        if "self" in args:
            args.remove("self")

        all_fields = set(self._message.keys())  # Track all processed fields to warn user
        defaults_start: int = -1
        if self._argspec.defaults is not None:
            defaults_start = len(args) - len(self._argspec.defaults)

        self._validate_argument_consistency(args)

        call_args = {}

        for i, arg in enumerate(args):
            arg_type: Optional[type[object]] = self._argspec.annotations.get(arg)
            if arg in self._message:
                # Argument is parameter in body of path of HTTP request
                value = self._message[arg]

                if arg_type and self._properties.operation == "GET":
                    value = self._ensure_list_if_list_type(arg_type, value)

                all_fields.remove(arg)

            elif arg_type and self._properties.operation == "GET" and self._is_dict_or_optional_dict(arg_type):
                # Argument is dictionary-based expression in query parameters of GET operation
                dict_prefix = f"{arg}."
                dict_with_prefixed_names = {
                    param_name: param_value
                    for param_name, param_value in self._message.items()
                    if param_name.startswith(dict_prefix) and len(param_name) > len(dict_prefix)
                }
                value = (
                    await self._get_dict_value_from_message(arg, dict_prefix, dict_with_prefixed_names)
                    if dict_with_prefixed_names
                    else None
                )

                for key in dict_with_prefixed_names.keys():
                    all_fields.remove(key)
            elif self._is_header_param(arg):
                value = self._map_headers(arg)
                if value is None:
                    value = self.get_default_value(arg, i, defaults_start)
            else:
                value = self.get_default_value(arg, i, defaults_start)

            call_args[arg] = value

        # validate types
        call_args = self._properties.validate_arguments(call_args)

        # discard session handling data
        if self._properties.agent_server and "sid" in all_fields:
            all_fields.remove("sid")

        if self._properties.varkw:
            # add all other arguments to the call args as well
            for field in all_fields:
                call_args[field] = self._message[field]

        if len(all_fields) > 0 and self._argspec.varkw is None:
            raise exceptions.BadRequest(
                "request contains fields %s that are not declared in method and no kwargs argument is provided." % all_fields
            )

        # Populate self._policy_engine_call_args
        self._policy_engine_call_args = copy.deepcopy(call_args)
        for arg_name, arg_opt in self._properties.arg_options.items():
            if arg_opt.header and arg_name in self._policy_engine_call_args:
                # Make sure we use the name of the header if the parameter was set using a header.
                # The data in the access policy needs to be structured like on the API, because
                # that is the structure that end-users know.
                self._policy_engine_call_args[arg_opt.header] = self._policy_engine_call_args[arg_name]
                del self._policy_engine_call_args[arg_name]

        for arg, value in call_args.items():
            # run getters
            value = await self._run_getters(arg, value)

            self._call_args[arg] = value

        # rename arguments if the handler requests this
        if hasattr(self._config.handler, "__protocol_mapping__"):
            for k, v in self._config.handler.__protocol_mapping__.items():
                if v in self._call_args:
                    self._call_args[k] = self._call_args[v]
                    del self._call_args[v]

        # verify if we need to inject a CallContext
        if call_context_var := self.get_call_context():
            self._call_args[call_context_var] = common.CallContext(
                request_headers=self._headers, auth_token=self._auth_token, auth_username=self._auth_username
            )

        self._processed = True

    async def _get_dict_value_from_message(
        self, arg: str, dict_prefix: str, dict_with_prefixed_names: dict[str, object]
    ) -> dict[str, object]:
        value = {k[len(dict_prefix) :]: v for k, v in dict_with_prefixed_names.items()}
        # Check if the values should be converted to lists
        type_args = self._argspec.annotations.get(arg)
        if typing_inspect.is_optional_type(type_args):
            # If optional, get the type args from the not None type argument
            dict_args = typing_inspect.get_args(typing_inspect.get_args(type_args, evaluate=True)[0], evaluate=True)
        else:
            dict_args = typing_inspect.get_args(self._argspec.annotations.get(arg), evaluate=True)
        dict_value_arg_type = (
            typing_inspect.get_origin(dict_args[1]) if typing_inspect.get_origin(dict_args[1]) else dict_args[1]
        )
        if issubclass(dict_value_arg_type, Sequence) and not issubclass(dict_value_arg_type, str):
            value = {key: [val] if not isinstance(val, Sequence) or isinstance(val, str) else val for key, val in value.items()}
        return value

    def _is_dict_or_optional_dict(self, arg_type: type[object]) -> bool:
        if typing_inspect.is_optional_type(arg_type):
            arg_type = typing_inspect.get_args(arg_type, evaluate=True)[0]
        arg_type = typing_inspect.get_origin(arg_type) if typing_inspect.get_origin(arg_type) else arg_type
        if typing_inspect.is_new_type(arg_type):
            arg_type = type(arg_type)
        return issubclass(arg_type, Mapping)

    def _validate_union_return(self, arg_type: type[object], value: object) -> None:
        """Validate a return with a union type
        :see: protocol.common.MethodProperties._validate_function_types
        """
        matching_type = None
        for t in typing_inspect.get_args(arg_type, evaluate=True):
            instanceof_type = t
            if typing_inspect.is_generic_type(t):
                instanceof_type = typing_inspect.get_origin(t)

            if isinstance(value, instanceof_type):
                if matching_type is not None:
                    raise exceptions.ServerError(
                        f"Return type is defined as a union {arg_type} for which multiple "
                        f"types match the provided value {value}"
                    )
                matching_type = t

        if matching_type is None:
            raise exceptions.BadRequest(
                f"Invalid return value, no matching type found in union {arg_type} for value type {type(value)}"
            )

        if typing_inspect.is_generic_type(matching_type):
            self._validate_generic_return(arg_type, matching_type)

    def _validate_generic_return(self, arg_type: type[object], value: object) -> None:
        """Validate List or Dict types.

        :note: we return any here because the calling function also returns any.
        """
        if issubclass(typing_inspect.get_origin(arg_type), list):
            if not isinstance(value, list):
                raise exceptions.ServerError(
                    f"Invalid return value, type needs to be a list. Argument type should be {arg_type}"
                )

            el_type = typing_inspect.get_args(arg_type, evaluate=True)[0]
            if el_type is Any:
                return
            for el in value:
                if typing_inspect.is_union_type(el_type):
                    self._validate_union_return(el_type, el)
                elif not isinstance(el, el_type):
                    raise exceptions.ServerError(f"Element {el} of returned list is not of type {el_type}.")

        elif issubclass(typing_inspect.get_origin(arg_type), dict):
            if not isinstance(value, dict):
                raise exceptions.ServerError(
                    f"Invalid return value, type needs to be a dict. Argument type should be {arg_type}"
                )

            el_type = typing_inspect.get_args(arg_type, evaluate=True)[1]
            if el_type is Any:
                return
            for k, v in value.items():
                if not isinstance(k, str):
                    raise exceptions.ServerError("Keys of return dict need to be strings.")

                if typing_inspect.is_union_type(el_type):
                    self._validate_union_return(el_type, v)
                if typing_inspect.is_generic_type(el_type):
                    self._validate_generic_return(el_type, v)
                elif not isinstance(v, el_type):
                    raise exceptions.ServerError(f"Element {v} of returned list is not of type {el_type}.")

        else:
            # This should not happen because of MethodProperties validation
            raise exceptions.BadRequest(
                f"Failed to validate generic type {arg_type} of return value, only List and Dict are supported"
            )

    async def process_return(self, result: Apireturn) -> common.Response:
        """A handler can return ApiReturn, so lets handle all possible return types and convert it to a Response

        Apireturn = Union[int, Tuple[int, Optional[JsonType]], "ReturnValue", "BaseModel"]
        """
        if "return" in self._argspec.annotations:  # new style with return type
            return_type = self._argspec.annotations["return"]

            if return_type is None:
                if result is not None:
                    raise exceptions.ServerError(
                        f"Method {self._config.method_name} returned a result but is defined as -> None"
                    )

                return common.Response.create(ReturnValue(status_code=200, response=None), envelope=False)

            # There is no obvious method to check if the return_type is a specific version of the generic ReturnValue
            # The way this is implemented in typing is different for python 3.6 and 3.7. In this code we "trust" that the
            # signature of the handler and the method definition matches and the returned value matches this return value
            # Both isubclass and isinstance fail on this type
            # This check needs to be first because isinstance fails on generic types.
            # TODO: also validate the value inside a ReturnValue
            if return_type is Any:
                return common.Response.create(
                    ReturnValue(response=result), self._config.properties.envelope, self._config.properties.envelope_key
                )

            elif typing_inspect.is_union_type(return_type):
                self._validate_union_return(return_type, result)
                return common.Response.create(
                    ReturnValue(response=result), self._config.properties.envelope, self._config.properties.envelope_key
                )

            if typing_inspect.is_generic_type(return_type):
                if isinstance(result, ReturnValue):
                    return common.Response.create(
                        result, self._config.properties.envelope, self._config.properties.envelope_key
                    )
                else:
                    self._validate_generic_return(return_type, result)
                    return common.Response.create(
                        ReturnValue(response=result), self._config.properties.envelope, self._config.properties.envelope_key
                    )

            elif isinstance(result, BaseModel):
                return common.Response.create(
                    ReturnValue(response=result), self._config.properties.envelope, self._config.properties.envelope_key
                )

            elif isinstance(result, common.VALID_SIMPLE_ARG_TYPES):
                return common.Response.create(
                    ReturnValue(response=result), self._config.properties.envelope, self._config.properties.envelope_key
                )

            else:
                raise exceptions.ServerError(
                    f"Method {self._config.method_name} returned an invalid result {result} "
                    "instead of a BaseModel or ReturnValue"
                )

        else:  # "old" style method definition
            if isinstance(result, tuple):
                if len(result) == 2:
                    code, body = result
                else:
                    raise exceptions.ServerError("Handlers for method call can only return a status code and a reply")

            elif isinstance(result, int):
                code = result
                body = None

            else:
                raise exceptions.ServerError(
                    f"Method {self._config.method_name} returned an invalid result {result} instead of a status code or tupple"
                )

            if body is not None:
                if self._config.properties.reply:
                    return common.Response.create(
                        ReturnValue(status_code=code, response=body),
                        self._config.properties.envelope,
                        self._config.properties.envelope_key,
                    )
                else:
                    LOGGER.warning("Method %s returned a result although it has no reply!")

            return common.Response.create(ReturnValue(status_code=code, response=None), envelope=False)

    def _parse_and_validate_auth_token(self) -> None:
        """Get the auth token provided by the caller and decode it.

        :return: A mapping of claims
        """
        token: str | None = None

        # Try to get token from parameters if token_param set in method properties.
        token_param = self._properties.token_param
        if token_param is not None and self._message.get(token_param):
            token = self._message[token_param]

        # Try to get token from header
        if token is None:
            token = self.get_auth_token_from_header(self._request_headers)

        if token is None:
            return None

        self._auth_token, cfg = auth.decode_token(token)

        if cfg.jwt_username_claim in self._auth_token:
            self._auth_username = str(self._auth_token[cfg.jwt_username_claim])

    @stable_api
    @classmethod
    def get_auth_token_from_header(cls, request_headers: Mapping[str, str]) -> str | None:
        header_value: Optional[str] = None

        if additional_header := server_config.server_additional_auth_header.get():
            if additional_header in request_headers:
                header_value = request_headers[additional_header]

        if header_value is None and "Authorization" in request_headers:
            # In Authorization it is parsed as a bearer token
            parts = request_headers["Authorization"].split(" ")

            if len(parts) != 2 or parts[0].lower() != "bearer":
                logging.getLogger(__name__).warning(
                    "Invalid JWT token header Authorization. A bearer token is expected, instead (%s was provided)",
                    header_value,
                )
                return None

            header_value = parts[1]

        return header_value

    def authenticate(self, auth_enabled: bool) -> None:
        """Fetch any identity information and authenticate. This will also load this authentication
        information in this instance.

        :param auth_enabled: is authentication enabled?
        """
        if not auth_enabled:
            return

        # get and validate the token. A valid token means that user is authenticated
        self._parse_and_validate_auth_token()
        if self._auth_token is None and self._config.properties.enforce_auth:
            # We only need a valid token when the endpoint enforces authentication
            raise exceptions.UnauthorizedException()

    def is_service_request(self) -> bool:
        """
        Return True iff this is a machine-to-machine request.
        """
        ct_key: str = const.INMANTA_URN + "ct"
        assert self._auth_token is not None
        client_types_token = self._auth_token[ct_key]
        return any(ct in {const.ClientType.agent.value, const.ClientType.compiler.value} for ct in client_types_token)


# Shared
class RESTBase(util.TaskHandler[None], abc.ABC):
    """
    Base class for REST based client and servers
    """

    _id: str

    @property
    def id(self) -> str:
        return self._id

    def _decode(self, body: bytes) -> Optional[JsonType]:
        """
        Decode a response body
        """
        result = None
        if body is not None and len(body) > 0:
            result = cast(JsonType, json.loads(escape.to_basestring(body)))

        return result

    def validate_sid(self, sid: uuid.UUID) -> bool:
        raise NotImplementedError()

    def is_auth_enabled(self) -> bool:
        """
        Return True iff authentication is enabled.
        """
        raise NotImplementedError()

    async def _execute_call(
        self,
        config: common.UrlMethod,
        message: dict[str, object],
        request_headers: Mapping[str, str],
    ) -> common.Response:
        try:
            if config is None:
                raise Exception("This method is unknown! This should not occur!")

            if config.properties.validate_sid:
                if "sid" not in message or not isinstance(message["sid"], str):
                    raise exceptions.BadRequest("this is an agent to server call, it should contain an agent session id")

                if not self.validate_sid(uuid.UUID(str(message["sid"]))):
                    raise exceptions.BadRequest("the sid %s is not valid." % message["sid"])

            # First check if the call is authenticated, then process the request so we can handle it and then authorize it.
            # Authorization might need data from the request but we do not want to process it before we are sure the call
            # is authenticated.
            arguments = CallArguments(config, message, request_headers)
            is_auth_enabled: bool = self.is_auth_enabled()
            arguments.authenticate(auth_enabled=is_auth_enabled)
            await arguments.process()
            authorization_provider = self.get_authorization_provider()
            if authorization_provider:
                await authorization_provider.authorize_request(arguments)

            LOGGER.debug(
                "Calling method %s(%s) user=%s",
                config.method_name,
                ", ".join([f"{name}={common.shorten(str(value))}" for name, value in arguments.call_args.items()]),
                arguments.auth_username if arguments.auth_username else "<>",
            )

            with tracing.span("Calling method " + config.method_name, arguments=arguments.call_args):
                result = await config.handler(**arguments.call_args)

            return await arguments.process_return(result)
        except pydantic.ValidationError:
            LOGGER.exception(f"The handler {config.handler} caused a validation error in a data model (pydantic).")
            raise exceptions.ServerError("data validation error.")

        except exceptions.BaseHttpException:
            LOGGER.debug("An HTTP Error occurred", exc_info=True)
            raise

        except Exception as e:
            LOGGER.exception("An exception occurred during the request.")
            raise exceptions.ServerError(str(e.args))

    @abc.abstractmethod
    def get_authorization_provider(self) -> providers.AuthorizationProvider | None:
        """
        Returns the authorization provider or None if we are not running on the server.
        """
        raise NotImplementedError()
