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
import inspect
import json
import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional, Tuple, Type, cast  # noqa: F401

import pydantic
import typing_inspect
from tornado import escape

from inmanta import config as inmanta_config
from inmanta import const, util
from inmanta.data.model import BaseModel
from inmanta.protocol import common, exceptions
from inmanta.protocol.common import ReturnValue
from inmanta.types import Apireturn, JsonType

LOGGER: logging.Logger = logging.getLogger(__name__)
INMANTA_MT_HEADER = "X-Inmanta-tid"
CONTENT_TYPE = "Content-Type"
JSON_CONTENT = "application/json"

"""

RestServer  => manages tornado/handlers, marshalling, dispatching, and endpoints

ServerSlice => contributes handlers and methods

ServerSlice.server [1] -- RestServer.endpoints [1:]

"""


def authorize_request(auth_data: Dict[str, str], metadata: Dict[str, str], message: JsonType, config: common.UrlMethod) -> None:
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
        self, properties: common.MethodProperties, message: Dict[str, Optional[Any]], request_headers: Mapping[str, str]
    ) -> None:
        """
            :param method_config: The method configuration that contains the metadata and functions to call
            :param message: The message recieved by the RPC call
            :param request_headers: The headers received by the RPC call
        """
        self._properties = properties
        self._message = message
        self._request_headers = request_headers
        self._argspec = inspect.getfullargspec(self._properties.function)

        self._call_args: JsonType = {}
        self._headers: Dict[str, str] = {}
        self._metadata: Dict[str, Any] = {}

        self._processed: bool = False

    @property
    def call_args(self) -> Dict[str, Any]:
        if not self._processed:
            raise Exception("Process call first before accessing property")

        return self._call_args

    @property
    def headers(self) -> Dict[str, str]:
        if not self._processed:
            raise Exception("Process call first before accessing property")

        return self._headers

    @property
    def metadata(self) -> Dict[str, Any]:
        if not self._processed:
            raise Exception("Process call first before accessing property")

        return self._metadata

    def _map_headers(self, arg: str) -> Optional[Any]:
        if arg not in self._properties.arg_options:
            return None

        opts = self._properties.arg_options[arg]

        if opts.header is None:
            return None

        value = self._request_headers[opts.header]
        if opts.reply_header:
            self._headers[opts.header] = value

        return value

    def _process_union(self, arg_type: Type, arg_name: str, value: Any) -> Any:
        """ Process a union type
        """
        matching_type = None
        for t in typing_inspect.get_args(arg_type):
            instanceof_type = t
            if typing_inspect.is_generic_type(t):
                instanceof_type = typing_inspect.get_origin(t)

            if isinstance(value, instanceof_type):
                if matching_type is not None:
                    raise exceptions.ServerError(
                        f"Argument {arg_name} is defined as a union {arg_type} for which multiple "
                        f"types match the provided value {value}"
                    )
                matching_type = t

        if matching_type is None:
            raise exceptions.BadRequest(
                f"Invalid argument {arg_name}, no matching type found in union {arg_type} for value type {type(value)}"
            )

        if typing_inspect.is_generic_type(matching_type):
            return self._process_generic(matching_type, arg_name, value)

        return matching_type(value)

    def _process_generic(self, arg_type: Type, arg_name: str, value: Any) -> Any:
        """ Process List or Dict types.

            :note: we return any here because the calling function also returns any.
        """
        if issubclass(typing_inspect.get_origin(arg_type), list):
            if not isinstance(value, list):
                raise exceptions.BadRequest(
                    f"Invalid argument {arg_name}, type needs to be a list. Argument type should be {arg_type}"
                )

            el_type = typing_inspect.get_args(arg_type)[0]
            if typing_inspect.is_union_type(el_type):
                return [self._process_union(el_type, arg_name, el) for el in value]

            elif issubclass(el_type, BaseModel):
                return [el_type(**el) for el in value]

            return [el_type(el) for el in value]

        elif issubclass(typing_inspect.get_origin(arg_type), dict):
            if not isinstance(value, dict):
                raise exceptions.BadRequest(
                    f"Invalid argument {arg_name}, type needs to be a dict. Argument type should be {arg_type}"
                )

            el_type = typing_inspect.get_args(arg_type)[1]
            result = {}
            for k, v in value.items():
                if not isinstance(k, str):
                    raise exceptions.BadRequest(f"Keys of dict argument {arg_name} need to be strings.")

                if typing_inspect.is_union_type(el_type):
                    result[k] = self._process_union(el_type, arg_name, v)
                elif issubclass(el_type, BaseModel):
                    result[k] = el_type(**v)
                else:
                    result[k] = el_type(v)

            return result

        else:
            # This should not happen because of MethodProperties validation
            raise exceptions.BadRequest(
                f"Failed to validate generic type {arg_type} of {arg_name}, only List and Dict are supported"
            )

    def _validate_union_return(self, arg_type: Type, value: Any) -> Any:
        """ Validate a return with a union type
        """
        matching_type = None
        for t in typing_inspect.get_args(arg_type):
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

    def _validate_generic_return(self, arg_type: Type, value: Any) -> Any:
        """ Validate List or Dict types.

            :note: we return any here because the calling function also returns any.
        """
        if issubclass(typing_inspect.get_origin(arg_type), list):
            if not isinstance(value, list):
                raise exceptions.ServerError(
                    f"Invalid return value, type needs to be a list. Argument type should be {arg_type}"
                )

            el_type = typing_inspect.get_args(arg_type)[0]
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

            el_type = typing_inspect.get_args(arg_type)[1]
            for k, v in value.items():
                if not isinstance(k, str):
                    raise exceptions.ServerError(f"Keys of return dict need to be strings.")

                if typing_inspect.is_union_type(el_type):
                    self._validate_union_return(el_type, v)
                elif not isinstance(v, el_type):
                    raise exceptions.ServerError(f"Element {v } of returned list is not of type {el_type}.")

        else:
            # This should not happen because of MethodProperties validation
            raise exceptions.BadRequest(
                f"Failed to validate generic type {arg_type} of return value, only List and Dict are supported"
            )

    def _process_typing(self, arg: str, value: Optional[Any]) -> Optional[Any]:
        """
            Validate and coerce if required
            :param arg: The name of the argument
            :param value: The current value of the argument
            :return: The processed value of the argument
        """
        if arg not in self._argspec.annotations:
            return value

        if value is None:
            return value

        arg_type: Type = self._argspec.annotations[arg]

        try:
            if typing_inspect.is_union_type(arg_type):
                return self._process_union(arg_type, arg, value)

            # This check needs to be first because isinstance fails on generic types.
            if typing_inspect.is_generic_type(arg_type):
                return self._process_generic(arg_type, arg, value)

            if isinstance(value, arg_type):
                return value

            if issubclass(arg_type, BaseModel):
                return arg_type(**value)

            if arg_type == datetime:
                return datetime.strptime(value, const.TIME_ISOFMT)

            elif issubclass(arg_type, enum.Enum):
                return arg_type[value]

            elif arg_type == bool:
                return inmanta_config.is_bool(value)

            else:
                return arg_type(value)

        except pydantic.ValidationError as e:
            error_msg = f"Failed to validate argument {arg} of expected type {arg_type}\n{str(e)}"
            LOGGER.exception(error_msg)
            raise exceptions.BadRequest(error_msg)

        except (ValueError, TypeError):
            error_msg = f"Invalid type for argument {arg}. Expected {arg_type} but received {value.__class__.__name__}, {value}"
            LOGGER.exception(error_msg)
            raise exceptions.BadRequest(error_msg)

    def get_default_value(self, arg_name: str, arg_position: int, default_start: int) -> Optional[Any]:
        """
            Get a default value for an argument
        """
        if default_start >= 0 and (arg_position - default_start) < len(self._argspec.defaults):
            return self._argspec.defaults[arg_position - default_start]
        else:
            raise exceptions.BadRequest("Invalid request. Field '%s' is required." % arg_name)

    async def _run_getters(self, arg: str, value: Optional[Any]) -> Optional[Any]:
        """
            Run ant available getters on value
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

        for i, arg in enumerate(args):
            # get value from headers, defaults or message
            value = self._map_headers(arg)
            if value is None:
                if arg in self._message:
                    value = self._message[arg]
                    all_fields.remove(arg)

                else:  # get default value
                    value = self.get_default_value(arg, i, defaults_start)

            # validate type
            value = self._process_typing(arg, value)

            # run getters
            value = await self._run_getters(arg, value)

            self._call_args[arg] = value

        # discard session handling data
        if self._properties.agent_server and "sid" in all_fields:
            all_fields.remove("sid")

        if len(all_fields) > 0 and self._argspec.varkw is None:
            raise exceptions.BadRequest(
                "request contains fields %s that are not declared in method and no kwargs argument is provided." % all_fields
            )

        self._processed = True

    async def process_return(self, config: common.UrlMethod, headers: Dict[str, str], result: Apireturn) -> common.Response:
        """ A handler can return ApiReturn, so lets handle all possible return types and convert it to a Response

            Apireturn = Union[int, Tuple[int, Optional[JsonType]], "ReturnValue", "BaseModel"]
        """
        if "return" in self._argspec.annotations:  # new style with return type
            return_type = self._argspec.annotations["return"]

            if return_type is None:
                if result is not None:
                    raise exceptions.ServerError(f"Method {config.method_name} returned a result but is defined as -> None")

                return common.Response(headers=headers, status_code=200)

            # There is no obvious method to check if the return_type is a specific version of the generic ReturnValue
            # The way this is implemented in typing is different for python 3.6 and 3.7. In this code we "trust" that the
            # signature of the handler and the method definition matches and the returned value matches this return value
            # Both isubclass and isinstance fail on this type
            # This check needs to be first because isinstance fails on generic types.
            # TODO: also validate the value inside a ReturnValue
            if typing_inspect.is_union_type(return_type):
                self._validate_union_return(return_type, result)
                return common.Response.create(ReturnValue(response=result), headers, config.properties.wrap_data)

            if typing_inspect.is_generic_type(return_type):
                if isinstance(result, ReturnValue):
                    return common.Response.create(result, headers, config.properties.wrap_data)
                else:
                    self._validate_generic_return(return_type, result)
                    return common.Response.create(ReturnValue(response=result), headers, config.properties.wrap_data)

            elif isinstance(result, BaseModel):
                return common.Response.create(ReturnValue(response=result), headers, config.properties.wrap_data)

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
                    return common.Response(body=body, headers=headers, status_code=code)

                else:
                    LOGGER.warning("Method %s returned a result although it has no reply!")

            return common.Response(headers=headers, status_code=code)


# Shared
class RESTBase(util.TaskHandler):
    """
        Base class for REST based client and servers
    """

    _id: str

    @property
    def id(self) -> str:
        return self._id

    def _decode(self, body: str) -> Optional[JsonType]:
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
        message: Dict[str, Any],
        request_headers: Mapping[str, str],
        auth=None,
    ) -> common.Response:

        headers: Dict[str, str] = {}
        try:
            if kwargs is None or config is None:
                raise Exception("This method is unknown! This should not occur!")

            # # create message that contains all arguments
            message.update(kwargs)

            if config.properties.validate_sid:
                if "sid" not in message:
                    raise exceptions.BadRequest("this is an agent to server call, it should contain an agent session id")

                elif not self.validate_sid(uuid.UUID(message["sid"])):
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
            return await arguments.process_return(config, headers, result)
        except exceptions.BaseHttpException:
            LOGGER.exception("")
            raise

        except Exception as e:
            LOGGER.exception("An exception occured during the request.")
            raise exceptions.ServerError(str(e.args))
