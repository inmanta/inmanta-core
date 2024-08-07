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

import logging
import os

import logfire
import logfire.integrations
import logfire.integrations.pydantic
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
    LOGGER.info("Setting up telemetry")

    detailed_reporting = bool(os.environ.get("OTEL_DETAILED_REPORTING"))

    AsyncPGInstrumentor(capture_parameters=detailed_reporting).instrument()

    logfire.configure(
        service_name=service,
        send_to_logfire="if-token-present",
        console=False,
        pydantic_plugin=logfire.integrations.pydantic.PydanticPlugin(record="all") if detailed_reporting else None,
    )
