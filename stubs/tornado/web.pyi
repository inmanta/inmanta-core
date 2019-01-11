import numbers
import datetime

from typing import Optional, Union, Dict, Any, List
from tornado import web, httputil, routing

Chunk = Union[bytes, str, dict, Dict[str, Any]]
_HeaderTypes = Union[bytes, str, numbers.Integral, datetime.datetime]

class RequestHandler:
    request: httputil.HTTPServerRequest

    def set_status(self, status_code: int, reason: Optional[str]=None) -> None: ...
    def set_header(self, name: str, value: web._HeaderTypes) -> None: ...
    def write(self, chunk: Chunk) -> None: ...
    def finish(self, chunk: Optional[Chunk]) -> None: ...


class Application:
    def __init__(self, handlers: List[routing.Rule], **kwargs: Any) -> None: ...


class HTTPError(Exception):
    log_message: Optional[str]
    status_code: int

    def __init__(self, status_code: int, log_message: Optional[str]) -> None: ...
