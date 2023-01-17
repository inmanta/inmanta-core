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
import json
import logging
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, MutableMapping, Optional, Tuple, Type, cast  # noqa: F401

import pydantic
import typing_inspect
from tornado import escape

from inmanta import const, util
from inmanta.data.model import BaseModel
from inmanta.protocol import common, exceptions
from inmanta.protocol.common import ReturnValue
from inmanta.types import Apireturn, JsonType

LOGGER: logging.Logger = logging.getLogger(__name__)
INMANTA_MT_HEADER = "X-Inmanta-tid"

"""

RestServer  => manages tornado/handlers, marshalling, dispatching, and endpoints

ServerSlice => contributes handlers and methods

ServerSlice.server [1] -- RestServer.endpoints [1:]

"""


def authorize_request(
    auth_data: Optional[MutableMapping[str, str]], metadata: Dict[str, str], message: JsonType, config: common.UrlMethod
) -> None:
    """
    Authorize a request based on the given data
    """
    if auth_data is None:
        return

    # Enforce environment restrictions
    env_key: str = const.INMANTA_URN + "env"
    if env_key in auth_data:
        if env_key not in metadata:
            raise exceptions.UnauthorizedException("The authorization token is scoped to a specific environment.")

        if metadata[env_key] != "all" and auth_data[env_key] != metadata[env_key]:
            raise exceptions.UnauthorizedException("The authorization token is not valid for the requested environment.")

    # Enforce client_types restrictions
    ok: bool = False
    ct_key: str = const.INMANTA_URN + "ct"
    for ct in auth_data[ct_key]:
        if ct in config.properties.client_types:
            ok = True

    if not ok:
        raise exceptions.UnauthorizedException(
            "The authorization token does not have a valid client type for this call."
            + " (%s provided, %s expected" % (auth_data[ct_key], config.properties.client_types)
        )


class CallArguments(object):
    """
    This class represents the call arguments for a method call.
    """

    def __init__(
        self, properties: common.MethodProperties, message: Dict[str, Optional[object]], request_headers: Mapping[str, str]
    ) -> None:
        """
        :param method_config: The method configuration that contains the metadata and functions to call
        :param message: The message recieved by the RPC call
        :param request_headers: The headers received by the RPC call
        """
        self._properties = properties
        self._message = message
        self._request_headers = request_headers
        self._argspec: inspect.FullArgSpec = inspect.getfullargspec(self._properties.function)

        self._call_args: JsonType = {}
        self._headers: Dict[str, str] = {}
        self._metadata: Dict[str, object] = {}

        self._processed: bool = False

    @property
    def call_args(self) -> Dict[str, object]:
        if not self._processed:
            raise Exception("Process call first before accessing property")

        return self._call_args

    @property
    def headers(self) -> Dict[str, str]:
        if not self._processed:
            raise Exception("Process call first before accessing property")

        return self._headers

    @property
    def metadata(self) -> Dict[str, object]:
        if not self._processed:
            raise Exception("Process call first before accessing property")

        return self._metadata

    def _is_header_param(self, arg: str) -> bool:
        if arg not in self._properties.arg_options:
            return False

        opts = self._properties.arg_options[arg]

        if opts.header is None:
            return False

        return True

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

    async def process(self) -> None:
        """
        Process the message
        """
        args: List[str] = list(self._argspec.args)

        if "self" in args:
            args.remove("self")

        all_fields = set(self._message.keys())  # Track all processed fields to warn user
        defaults_start: int = -1
        if self._argspec.defaults is not None:
            defaults_start = len(args) - len(self._argspec.defaults)

        call_args = {}

        for i, arg in enumerate(args):
            # get value from headers, defaults or message
            value = self._map_headers(arg)
            if value is None:
                if not self._is_header_param(arg):
                    arg_type: Optional[Type[object]] = self._argspec.annotations.get(arg)
                    if arg in self._message:
                        if (
                            arg_type
                            and self._properties.operation == "GET"
                            and typing_inspect.is_generic_type(arg_type)
                            and issubclass(typing_inspect.get_origin(arg_type), list)
                            and not isinstance(self._message[arg], list)
                            and len(typing_inspect.get_args(arg_type, evaluate=True)) == 1
                            and isinstance(self._message[arg], typing_inspect.get_args(arg_type)[0])
                        ):
                            # If a GET endpoint has a parameter of type list that is encoded as a URL query parameter and the
                            # specific request provides a list with one element, urllib doesn't parse it as a list.
                            # Map it here explicitly to a list.
                            value = [self._message[arg]]
                        else:
                            value = self._message[arg]
                        all_fields.remove(arg)
                    # Pre-process dict params for GET
                    elif arg_type and self._properties.operation == "GET" and self._is_dict_or_optional_dict(arg_type):
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

                    else:  # get default value
                        value = self.get_default_value(arg, i, defaults_start)
                else:  # get default value
                    value = self.get_default_value(arg, i, defaults_start)

            call_args[arg] = value

        # validate types
        call_args = self._properties.validate_arguments(call_args)

        for arg, value in call_args.items():
            # run getters
            value = await self._run_getters(arg, value)

            self._call_args[arg] = value

        # discard session handling data
        if self._properties.agent_server and "sid" in all_fields:
            all_fields.remove("sid")

        if self._properties.varkw:
            # add all other arguments to the call args as well
            for field in all_fields:
                self._call_args[field] = self._message[field]

        if len(all_fields) > 0 and self._argspec.varkw is None:
            raise exceptions.BadRequest(
                "request contains fields %s that are not declared in method and no kwargs argument is provided." % all_fields
            )

        self._processed = True

    async def _get_dict_value_from_message(
        self, arg: str, dict_prefix: str, dict_with_prefixed_names: Dict[str, object]
    ) -> Dict[str, object]:
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
        if issubclass(dict_value_arg_type, list):
            value = {key: [val] if not isinstance(val, list) else val for key, val in value.items()}
        return value

    def _is_dict_or_optional_dict(self, arg_type: Type[object]) -> bool:
        if typing_inspect.is_optional_type(arg_type):
            arg_type = typing_inspect.get_args(arg_type, evaluate=True)[0]
        arg_type = typing_inspect.get_origin(arg_type) if typing_inspect.get_origin(arg_type) else arg_type
        if typing_inspect.is_new_type(arg_type):
            arg_type = type(arg_type)
        return issubclass(arg_type, dict)

    def _validate_union_return(self, arg_type: Type[object], value: object) -> None:
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

    def _validate_generic_return(self, arg_type: Type[object], value: object) -> None:
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

    async def process_return(self, config: common.UrlMethod, result: Apireturn) -> common.Response:
        """A handler can return ApiReturn, so lets handle all possible return types and convert it to a Response

        Apireturn = Union[int, Tuple[int, Optional[JsonType]], "ReturnValue", "BaseModel"]
        """
        if "return" in self._argspec.annotations:  # new style with return type
            return_type = self._argspec.annotations["return"]

            if return_type is None:
                if result is not None:
                    raise exceptions.ServerError(f"Method {config.method_name} returned a result but is defined as -> None")

                return common.Response.create(ReturnValue(status_code=200, response=None), envelope=False)

            # There is no obvious method to check if the return_type is a specific version of the generic ReturnValue
            # The way this is implemented in typing is different for python 3.6 and 3.7. In this code we "trust" that the
            # signature of the handler and the method definition matches and the returned value matches this return value
            # Both isubclass and isinstance fail on this type
            # This check needs to be first because isinstance fails on generic types.
            # TODO: also validate the value inside a ReturnValue
            if return_type is Any:
                return common.Response.create(
                    ReturnValue(response=result), config.properties.envelope, config.properties.envelope_key
                )

            elif typing_inspect.is_union_type(return_type):
                self._validate_union_return(return_type, result)
                return common.Response.create(
                    ReturnValue(response=result), config.properties.envelope, config.properties.envelope_key
                )

            if typing_inspect.is_generic_type(return_type):
                if isinstance(result, ReturnValue):
                    return common.Response.create(result, config.properties.envelope, config.properties.envelope_key)
                else:
                    self._validate_generic_return(return_type, result)
                    return common.Response.create(
                        ReturnValue(response=result), config.properties.envelope, config.properties.envelope_key
                    )

            elif isinstance(result, BaseModel):
                return common.Response.create(
                    ReturnValue(response=result), config.properties.envelope, config.properties.envelope_key
                )

            elif isinstance(result, common.VALID_SIMPLE_ARG_TYPES):
                return common.Response.create(
                    ReturnValue(response=result), config.properties.envelope, config.properties.envelope_key
                )

            else:
                raise exceptions.ServerError(
                    f"Method {config.method_name} returned an invalid result {result} instead of a BaseModel or ReturnValue"
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
                    f"Method {config.method_name} returned an invalid result {result} instead of a status code or tupple"
                )

            if body is not None:
                if config.properties.reply:
                    return common.Response.create(
                        ReturnValue(status_code=code, response=body),
                        config.properties.envelope,
                        config.properties.envelope_key,
                    )
                else:
                    LOGGER.warning("Method %s returned a result although it has no reply!")

            return common.Response.create(ReturnValue(status_code=code, response=None), envelope=False)


# Shared
class RESTBase(util.TaskHandler):
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

    async def _execute_call(
        self,
        kwargs: Dict[str, str],
        http_method: str,
        config: common.UrlMethod,
        message: Dict[str, object],
        request_headers: Mapping[str, str],
        auth: Optional[MutableMapping[str, str]] = None,
    ) -> common.Response:
        try:
            if kwargs is None or config is None:
                raise Exception("This method is unknown! This should not occur!")

            # create message that contains all arguments
            message.update(kwargs)

            if config.properties.validate_sid:
                if "sid" not in message:
                    raise exceptions.BadRequest("this is an agent to server call, it should contain an agent session id")

                sid = uuid.UUID(message["sid"])
                if not isinstance(sid, uuid.UUID) or not self.validate_sid(sid):
                    raise exceptions.BadRequest("the sid %s is not valid." % message["sid"])

            arguments = CallArguments(config.properties, message, request_headers)
            await arguments.process()
            authorize_request(auth, arguments.metadata, arguments.call_args, config)

            # rename arguments if handler requests this
            call_args = arguments.call_args
            if hasattr(config.handler, "__protocol_mapping__"):
                for k, v in config.handler.__protocol_mapping__.items():
                    if v in call_args:
                        call_args[k] = call_args[v]
                        del call_args[v]

            LOGGER.debug(
                "Calling method %s(%s)",
                config.handler,
                ", ".join(["%s='%s'" % (name, common.shorten(str(value))) for name, value in arguments.call_args.items()]),
            )

            result = await config.handler(**arguments.call_args)
            return await arguments.process_return(config, result)
        except pydantic.ValidationError:
            LOGGER.exception(f"The handler {config.handler} caused a validation error in a data model (pydantic).")
            raise exceptions.ServerError("data validation error.")

        except exceptions.BaseHttpException:
            LOGGER.debug("An HTTP Error occurred", exc_info=True)
            raise

        except Exception as e:
            LOGGER.exception("An exception occured during the request.")
            raise exceptions.ServerError(str(e.args))
