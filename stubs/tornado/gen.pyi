from typing import Callable, Generator, TypeVar, Any
from asyncio import Future

_T = TypeVar("_T")

def coroutine(func: Callable[..., "Generator[Any, Any, _T]"]) -> Callable[..., "Future[_T]"]: ...
def sleep(duration: float) -> "Future[None]": ...
