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
from typing import Any, Callable, ContextManager, Literal, LiteralString, Mapping, ParamSpec, Sequence, TypeVar

LOGGER = logging.getLogger("inmanta")

# We need this early to make @instrument work
enabled = os.getenv("LOGFIRE_TOKEN", None) is not None
try:
    import logfire._internal.config
    import logfire.integrations
    import logfire.integrations.pydantic
    import logfire.propagate
    from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor

    # Make sure we don't get warnings when it is off
    logfire._internal.config.GLOBAL_CONFIG.ignore_no_config = True
    enabled = os.getenv("LOGFIRE_TOKEN", None) is not None


except (ModuleNotFoundError, Exception):
    enabled = False

# Retaken from Logfire 1.0.1 to make sure tests pass even if logfire is not installed
LevelName = Literal["trace", "debug", "info", "notice", "warn", "warning", "error", "fatal"]
"""Level names for records."""


class NoopSpan:
    """Implements the same methods as `LogfireSpan` but does nothing.

    Used in place of `LogfireSpan` and `FastLogfireSpan` when an exception occurs during span creation.
    This way code like:

        with logfire.span(...) as span:
            span.set_attribute(...)

    doesn't raise an error even if `logfire.span` fails internally.
    If `logfire.span` just returned `None` then the `with` block and the `span.set_attribute` call would raise an error.
    """

    def __init__(self, *_args: Any, **__kwargs: Any) -> None:
        pass

    def __getattr__(self, _name: str) -> Any:
        # Handle methods of LogfireSpan which return nothing
        return lambda *_args, **__kwargs: None

    def __enter__(self) -> "NoopSpan":
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: Any) -> None:
        pass

    # Implement methods/properties that return something to get the type right.
    @property
    def message_template(self) -> str:  # pragma: no cover
        return ""

    @property
    def tags(self) -> Sequence[str]:  # pragma: no cover
        return []

    @property
    def message(self) -> str:  # pragma: no cover
        return ""

    # This is required to make `span.message = ` not raise an error.
    @message.setter
    def message(self, message: str) -> None:
        pass

    def is_recording(self) -> bool:
        return False


ContextCarrier = Mapping[str, Any]


def configure_logfire(service: str) -> None:
    """Configure logfire to collect telemetry from the spans and instrument libraries such as asyncpg. By default, no traces
    will be processed and sent, this requires configuration in environment variables:

    - LOGFIRE_TOKEN: This variable needs to be set to enable the exporter. When set to a https://logfire.pydantic.dev token
      the traces will be sent to logfire. Be aware that by enabling capture parameters for asyncpg and pydantic, quite some
      data will be sent to logfire. See the other options for using another trace endpoint.
    - OTEL_RESOURCE_ATTRIBUTES: A comma separated list of attributes that are added to each trace. These can be used to
      distinguish traces from different instances, developers, ci runs, ...
    - OTEL_EXPORTER_OTLP_PROTOCOL and OTEL_EXPORTER_OTLP_ENDPOINT: These variables can be used to send the traces to different
      collectors. Either to aggregate before shipping them to logfire or to send them to entirely different systems.
    - OTEL_DETAILED_REPORTING: When set detailed parameters are logged such as asyncpg parameters and pydantic objects
    """

    if enabled:
        LOGGER.info("Setting up telemetry")
        enable()

        detailed_reporting = bool(os.environ.get("OTEL_DETAILED_REPORTING"))

        AsyncPGInstrumentor(capture_parameters=detailed_reporting).instrument()

        logfire.instrument_pydantic("all" if detailed_reporting else "off")
        logfire.configure(
            service_name=service,
            send_to_logfire="if-token-present",
            console=False,
        )
    else:
        LOGGER.info("Not setting up telemetry")


no_span = NoopSpan()
no_context = contextlib.nullcontext(None)


def span(
    msg_template: str,
    /,
    *,
    _tags: Sequence[str] | None = None,
    _span_name: str | None = None,
    _level: "LevelName | None | logfire.LevelName" = None,
    **attributes: Any,
) -> "NoopSpan | logfire.LogfireSpan":
    if enabled:
        return logfire.span(msg_template, _tags=_tags, _span_name=_span_name, _level=_level, **attributes)
    else:
        return no_span


def attach_context(carrier: "ContextCarrier | logfire.propagate.ContextCarrier") -> ContextManager[None]:
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
