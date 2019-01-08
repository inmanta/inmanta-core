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
        return {"message": self._log_message}

    def to_status(self) -> int:
        """
            Return the status code
        """
        return self._status_code


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
