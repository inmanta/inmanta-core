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

    Logfire stub
"""

import contextlib
from typing import Any, Callable, ContextManager, LiteralString, ParamSpec, Sequence, TypeVar, Mapping

import logfire
from logfire import LevelName, LogfireSpan

# TODO: internal import
from logfire._internal.main import NoopSpan
from logfire.propagate import ContextCarrier
from opentelemetry.trace import Span

# look into fast span and why spans use atexit
# investigate why @instrument rewrites code

no_span = NoopSpan()
no_context = contextlib.nullcontext(None)


def span(
    msg_template: str,
    /,
    *,
    _tags: Sequence[str] | None = None,
    _span_name: str | None = None,
    _level: LevelName | None = None,
    **attributes: Any,
) -> LogfireSpan:
    return no_span


def attach_context(carrier: ContextCarrier) -> ContextManager[None]:
    return no_context


def get_context() -> Mapping[str, Any]:
    return {}


P = ParamSpec("P")
R = TypeVar("R")


def no_method(it: Callable[P, R]) -> Callable[P, R]:
    return it


def instrument(
    msg_template: LiteralString | None = None,
    *,
    span_name: str | None = None,
    extract_args: bool = True,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    return no_method


def enable() -> None:
    """ Replace dummy instrumentation with the real deal"""
    global span
    global attach_context
    global get_context
    global instrument
    span = logfire.span
    attach_context = logfire.propagate.attach_context
    get_context = logfire.propagate.get_context
    instrument = logfire.instrument
