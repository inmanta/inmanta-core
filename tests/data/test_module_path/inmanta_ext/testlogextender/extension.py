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
from typing import TextIO, Mapping

from inmanta.logging import LoggingConfigBuilderExtension, Options, FullLoggingConfig
from inmanta.server import SLICE_AGENT_MANAGER, SLICE_SERVER
from inmanta.server.extensions import ApplicationContext
from inmanta.server.protocol import ServerSlice


class Extender(LoggingConfigBuilderExtension):

    def get_logging_config_from_options(
        self,
        stream: TextIO,
        options: Options,
        component: str | None,
        context: Mapping[str, str],
        master_config: FullLoggingConfig
    ) -> FullLoggingConfig:
        master_config.formatters["test_formatter"] = {
            "format": 'TEST TEST TEST %(asctime)s %(levelname)-8s %(name)-10s %(message)s'
        }
        master_config.handlers["test_handler"] = {
            "class": "logging.StreamHandler",
            "formatter": "core_console_formatter",
            "level": "DEBUG",
            "stream": stream,
        }
        master_config.root_handlers.append("test_handler")

        return master_config




def setup(application: ApplicationContext) -> None:
    application.register_default_logging_config()
