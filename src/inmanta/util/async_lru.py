"""
 Copyright 2024 Inmanta

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

Async support for @functools.lrucache
From https://github.com/python/cpython/issues/90780
"""

import asyncio
from asyncio import Future
from functools import _lru_cache_wrapper, lru_cache, wraps
from typing import Any, Awaitable, Callable, Generator, ParamSpec, TypeVar, overload

T = TypeVar("T")
_PWrapped = ParamSpec("_PWrapped")


class CachedAwaitable(Awaitable[T]):
    def __init__(self, awaitable: Awaitable[T]) -> None:
        self.awaitable = awaitable
        self.result: Future[T] | None = None

    def __await__(self) -> Generator[Any, None, T]:
        if self.result is None:
            fut = asyncio.get_event_loop().create_future()
            self.result = fut
            try:
                result = yield from self.awaitable.__await__()
                fut.set_result(result)
            except Exception as e:
                fut.set_exception(e)
        if not self.result.done():
            yield from self.result
        return self.result.result()


def reawaitable(func: Callable[_PWrapped, Awaitable[T]]) -> Callable[_PWrapped, CachedAwaitable[T]]:
    @wraps(func)
    def wrapper(*args, **kwargs):
        return CachedAwaitable(func(*args, **kwargs))

    return wrapper


@overload
def async_lru_cache(
    maxsize: int | None = 128, typed: bool = False
) -> "Callable[[Callable[..., Awaitable[T]]], _lru_cache_wrapper[CachedAwaitable[T]]]": ...
@overload
def async_lru_cache(maxsize: Callable[..., Awaitable[T]], typed: bool = False) -> "_lru_cache_wrapper[CachedAwaitable[T]]": ...


def async_lru_cache(
    maxsize: int | None | Callable[..., Awaitable[T]] = 128, typed=False
) -> "Callable[[Callable[..., Awaitable[T]]], _lru_cache_wrapper[CachedAwaitable[T]]] | _lru_cache_wrapper[CachedAwaitable[T]]":
    if callable(maxsize) and isinstance(typed, bool):
        user_function, maxsize = maxsize, 128
        return lru_cache(maxsize, typed)(reawaitable(user_function))

    def decorating_function(user_function):
        return lru_cache(maxsize, typed)(reawaitable(user_function))

    return decorating_function
