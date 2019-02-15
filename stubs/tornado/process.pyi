import typing
import subprocess

from typing import Tuple, Optional, Any, Callable,List
from tornado.concurrent import (
    Future,
    future_set_result_unless_cancelled,
    future_set_exception_unless_cancelled,
)

class Subprocess(object):
	proc: subprocess.Popen
	def __init__(self, *args: Any, **kwargs: Any) -> None: ...
	def wait_for_exit(self, raise_error: bool = ...) -> Future[int]: ...