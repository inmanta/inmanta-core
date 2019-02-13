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
from tornado import web
from typing import Optional, Dict, Any


class BaseException(web.HTTPError):
    """
        A base exception for errors in the server
    """

    def __init__(self, status_code: int = 500, message: Optional[str] = None) -> None:
        super().__init__(status_code, message)

    def to_body(self) -> Dict[str, Any]:
        """
            Return a response body
        """
        return {"message": self.log_message}

    def to_status(self) -> int:
        """
            Return the status code
        """
        return self.status_code


class AccessDeniedException(BaseException):
    """
        An exception raised when access is denied (403)
    """

    def __init__(self, message: Optional[str] = None) -> None:
        msg = "Access denied"
        if message is not None:
            msg += ": " + message

        super().__init__(403, msg)


class UnauthorizedException(BaseException):
    """
        An exception raised when access to this resource is unauthorized
    """

    def __init__(self, message: Optional[str] = None) -> None:
        msg = "Access to this resource is unauthorized"
        if message is not None:
            msg += ": " + message

        super().__init__(401, msg)


class BadRequest(BaseException):
    """
        This exception is raised for a mailformed request
    """

    def __init__(self, message: Optional[str] = None) -> None:
        msg = "Invalid request"
        if message is not None:
            msg += ": " + message

        super().__init__(400, msg)


class NotFound(BaseException):
    """
        This exception is used to indicate that a request or reference resource was not found.
    """

    def __init__(self, message: Optional[str] = None) -> None:
        msg = "Request or referenced resource does not exist"
        if message is not None:
            msg += ": " + message

        super().__init__(404, msg)


class ServerError(BaseException):
    """
        An unexpected error occurred in the server
    """

    def __init__(self, message: Optional[str] = None) -> None:
        msg = "An unexpected error occurred in the server while processing the request"
        if message is not None:
            msg += ": " + message

        super().__init__(500, msg)
