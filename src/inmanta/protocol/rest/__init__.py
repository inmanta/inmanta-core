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
import logging
import inspect
import json
import uuid
from datetime import datetime
import enum

from tornado import gen, escape
from inmanta import const
from inmanta.types import JsonType
from inmanta.protocol import common, exceptions
from inmanta import config as inmanta_config

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING, cast, Mapping, Generator  # noqa: F401

LOGGER: logging.Logger = logging.getLogger(__name__)
INMANTA_MT_HEADER = "X-Inmanta-tid"
CONTENT_TYPE = "Content-Type"
JSON_CONTENT = "application/json"

"""

RestServer  => manages tornado/handlers, marshalling, dispatching, and endpoints

ServerSlice => contributes handlers and methods

ServerSlice.server [1] -- RestServer.endpoints [1:]

"""


def authorize_request(
    auth_data: Dict[str, str], metadata: Dict[str, str], message: JsonType, config: common.UrlMethod
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

    def _process_typing(self, arg: str, value: Optional[Any]) -> Optional[Any]:
        """
            Validate and coerce if required
            :param arg: The name of the arugment
            :param value: The current value of the argument
            :return: The processed value of the argument
        """
        if arg not in self._argspec.annotations:
            return value

        if value is None:
            return value

        arg_type = self._argspec.annotations[arg]
        if isinstance(value, arg_type):
            return value

        try:
            if arg_type == datetime:
                return datetime.strptime(value, const.TIME_ISOFMT)

            elif issubclass(arg_type, enum.Enum):
                return arg_type[value]

            elif arg_type == bool:
                return inmanta_config.is_bool(value)

            else:
                return arg_type(value)

        except (ValueError, TypeError):
            error_msg = "Invalid type for argument %s. Expected %s but received %s, %s" % (
                arg,
                arg_type,
                value.__class__,
                value,
            )
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

    @gen.coroutine
    def _run_getters(self, arg: str, value: Optional[Any]) -> Optional[Any]:
        """
            Run ant available getters on value
        """
        if arg not in self._properties.arg_options or self._properties.arg_options[arg].getter is None:
            return value

        try:
            value = yield self._properties.arg_options[arg].getter(value, self._metadata)
            return value
        except Exception as e:
            LOGGER.exception("Failed to use getter for arg %s", arg)
            raise e

    @gen.coroutine
    def process(self) -> None:
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
            value = yield self._run_getters(arg, value)

            self._call_args[arg] = value

        # discard session handling data
        if self._properties.agent_server and "sid" in all_fields:
            all_fields.remove("sid")

        if len(all_fields) > 0 and self._argspec.varkw is None:
            raise exceptions.BadRequest(
                "request contains fields %s that are not declared in method and no kwargs argument is provided." % all_fields
            )

        self._processed = True


# Shared
class RESTBase(object):
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

    @gen.coroutine
    def _execute_call(
        self,
        kwargs: Dict[str, str],
        http_method: str,
        config: common.UrlMethod,
        message: Dict[str, Any],
        request_headers: Mapping[str, str],
        auth=None,
    ) -> Generator[Any, Any, common.Response]:

        headers: Dict[str, str] = {}
        try:
            if kwargs is None or config is None:
                raise Exception("This method is unknown! This should not occur!")

            # create message that contains all arguments (id, query args and body)
            if "id" in kwargs and (message is None or "id" not in message):
                message["id"] = kwargs["id"]

            # validate message against config
            if config.properties.id and "id" not in message:
                raise exceptions.BadRequest("the request should contain an id in the url.")

            if config.properties.validate_sid:
                if "sid" not in message:
                    raise exceptions.BadRequest("this is an agent to server call, it should contain an agent session id")

                elif not self.validate_sid(uuid.UUID(message["sid"])):
                    raise exceptions.BadRequest("the sid %s is not valid." % message["sid"])

            arguments = CallArguments(config.properties, message, request_headers)
            yield arguments.process()
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

            result = yield config.handler(**arguments.call_args)

            if result is None:
                raise exceptions.BadRequest(
                    "Handlers for method calls should at least return a status code. %s on %s"
                    % (config.method_name, config.endpoint)
                )

            reply = None
            if isinstance(result, tuple):
                if len(result) == 2:
                    code, reply = result
                else:
                    raise exceptions.BadRequest("Handlers for method call can only return a status code and a reply")

            else:
                code = result

            if reply is not None:
                if config.properties.reply:
                    LOGGER.debug("%s returned %d: %s", config.method_name, code, common.shorten(str(reply), 70))
                    return common.Response(body=reply, headers=headers, status_code=code)

                else:
                    LOGGER.warning("Method %s returned a result although it is has not reply!")

            return common.Response(headers=headers, status_code=code)

        except exceptions.BaseException:
            LOGGER.exception("")
            raise

        except Exception as e:
            LOGGER.exception("An exception occured during the request.")
            raise exceptions.ServerError(str(e.args))
