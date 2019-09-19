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
from typing import Optional

from inmanta.reporter import InfluxReporter
from inmanta.server import SLICE_METRICS
from inmanta.server import config as opt
from inmanta.server import protocol

LOGGER = logging.getLogger(__name__)


class MetricsService(protocol.ServerSlice):
    """Slice managing metrics collector"""

    def __init__(self) -> None:
        super(MetricsService, self).__init__(SLICE_METRICS)
        self._influx_db_reporter: Optional[InfluxReporter] = None

    async def start(self) -> None:
        self.start_metric_reporters()
        await super().start()

    async def stop(self) -> None:
        await super().stop()
        self.stop_metric_reporters()

    def stop_metric_reporters(self) -> None:
        if self._influx_db_reporter:
            self._influx_db_reporter.stop()
            self._influx_db_reporter = None

    def start_metric_reporters(self) -> None:
        if opt.influxdb_host.get():
            self._influx_db_reporter = InfluxReporter(
                server=opt.influxdb_host.get(),
                port=opt.influxdb_port.get(),
                database=opt.influxdb_name.get(),
                username=opt.influxdb_username.get(),
                password=opt.influxdb_password.get(),
                reporting_interval=opt.influxdb_interval.get(),
                autocreate_database=True,
                tags=opt.influxdb_tags.get(),
            )
            self._influx_db_reporter.start()
