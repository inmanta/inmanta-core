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
from typing import Any, Dict, Optional

from tornado import web

from inmanta.types import JsonType


class BaseHttpException(web.HTTPError):
    """
    A base exception for errors in the server.

    Classes which extend from the BaseHttpException class cannot have mandatory arguments
    in their constructor. This is required to determine the status_code of the exception in
    :meth:`inmanta.protocol.common.MethodProperties._get_http_status_code_for_exception`
    """

    def __init__(self, status_code: int = 500, message: Optional[str] = None, details: Optional[JsonType] = None) -> None:
        super().__init__(status_code, message)
        self.details = details

    def to_body(self) -> Dict[str, Any]:
        """
        Return a response body
        """
        body: JsonType = {"message": self.log_message}
        if self.details is not None:
            body["error_details"] = self.details

        return body

    def to_status(self) -> int:
        """
        Return the status code
        """
        return self.status_code


class Forbidden(BaseHttpException):
    """
    An exception raised when access is denied (403)
    """

    def __init__(self, message: Optional[str] = None, details: Optional[JsonType] = None) -> None:
        msg = "Access denied"
        if message is not None:
            msg += ": " + message

        super().__init__(403, msg, details)


class UnauthorizedException(BaseHttpException):
    """
    An exception raised when access to this resource is unauthorized
    """

    def __init__(self, message: Optional[str] = None, details: Optional[JsonType] = None) -> None:
        msg = "Access to this resource is unauthorized"
        if message is not None:
            msg += ": " + message

        super().__init__(401, msg, details)


class BadRequest(BaseHttpException):
    """
    This exception is raised for a malformed request
    """

    def __init__(self, message: Optional[str] = None, details: Optional[JsonType] = None) -> None:
        msg = "Invalid request"
        if message is not None:
            msg += ": " + message

        super().__init__(400, msg, details)


class NotFound(BaseHttpException):
    """
    This exception is used to indicate that a request or reference resource was not found.
    """

    def __init__(self, message: Optional[str] = None, details: Optional[JsonType] = None) -> None:
        msg = "Request or referenced resource does not exist"
        if message is not None:
            msg += ": " + message

        super().__init__(404, msg, details)


class Conflict(BaseHttpException):
    """
    This exception is used to indicate that a request conflicts with the current state of the resource.
    """

    def __init__(self, message: Optional[str] = None, details: Optional[JsonType] = None) -> None:
        msg = "Request conflicts with the current state of the resource"
        if message is not None:
            msg += ": " + message

        super().__init__(409, msg, details)


class ServerError(BaseHttpException):
    """
    An unexpected error occurred in the server
    """

    def __init__(self, message: Optional[str] = None, details: Optional[JsonType] = None) -> None:
        msg = "An unexpected error occurred in the server while processing the request"
        if message is not None:
            msg += ": " + message

        super().__init__(500, msg, details)


class ShutdownInProgress(BaseHttpException):
    """This request can not be fulfilled because the server is going down"""

    def __init__(self, message: Optional[str] = None, details: Optional[JsonType] = None) -> None:
        msg = "Can not complete this request as a shutdown is on progress"
        if message is not None:
            msg += ": " + message

        super().__init__(503, msg, details)
