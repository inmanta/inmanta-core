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
"""

import contextlib
import logging
import os
from typing import Any, Callable, ContextManager, LiteralString, Mapping, ParamSpec, Sequence, TypeVar

import logfire
import logfire.integrations
import logfire.integrations.pydantic
from logfire import LevelName, LogfireSpan
from logfire._internal.main import NoopSpan
from logfire.propagate import ContextCarrier
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor

LOGGER = logging.getLogger("inmanta")


def configure_logfire(service: str) -> None:
    """Configure logfire to collect telemetry from the spans and instrument libraries such as asyncpg. By default, no traces
    will be processed and sent, this requires configuration in environemnt variables:

    - LOGFIRE_TOKEN: This variable needs to be set to enable the exporter. When set to a https://logfire.pydantic.dev token
      the traces will be sent to logfire. Be aware that by enabling capture parameters for asyncpg and pydantic, quite some
      data will be sent to logfire. See the other options for using another trace endpoint.
    - OTEL_RESOURCE_ATTRIBUTES: A comma separated list of attributes that are added to each trace. These can used to disinguish
      traces from different instances, developers, ci runs, ...
    - OTEL_EXPORTER_OTLP_PROTOCOL and OTEL_EXPORTER_OTLP_ENDPOINT: These variables can be used to send the traces to different
      collectors. Either to aggregate before shipping them to logfire or to sent them to entirely different systems.
    - OTEL_DETAILED_REPORTING: When set detailed parameters are logged such as asyncpg parameters and pydantic objects
    """

    if os.getenv("LOGFIRE_TOKEN", None):
        LOGGER.info("Setting up telemetry")
        enable()

        detailed_reporting = bool(os.environ.get("OTEL_DETAILED_REPORTING"))

        AsyncPGInstrumentor(capture_parameters=detailed_reporting).instrument()

        logfire.configure(
            service_name=service,
            send_to_logfire="if-token-present",
            console=False,
            pydantic_plugin=logfire.integrations.pydantic.PydanticPlugin(record="all") if detailed_reporting else None,
        )
    else:
        LOGGER.info("Not setting up telemetry")


# We need this early to make @instrument work
enabled = os.getenv("LOGFIRE_TOKEN", None) is None


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
    if enabled:
        return logfire.span(msg_template, _tags=_tags, _span_name=_span_name, _level=_level, **attributes)
    else:
        return no_span


def attach_context(carrier: ContextCarrier) -> ContextManager[None]:
    if enabled:
        return logfire.propagate.attach_context(carrier)
    else:
        return no_context


def get_context() -> Mapping[str, Any]:
    if enabled:
        return logfire.propagate.get_context()
    else:
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
    if enabled:
        return logfire.instrument(msg_template, span_name=span_name, extract_args=extract_args)
    else:
        return no_method


def enable() -> None:
    """Replace dummy instrumentation with the real deal"""
    global enabled
    enabled = True
