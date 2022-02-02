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
from time import perf_counter, time
from typing import Optional

from pyformance import gauge
from pyformance.meters import Gauge

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
        self.start_auto_benchmark()
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

    def start_auto_benchmark(self) -> None:
        """Add all auto benchmarking to pyformance"""
        gauge("self.spec.cpu", CPUMicroBenchMark())


class CachingCallbackGuage(Gauge):
    """
    A gauge that calculates a value on the fly and holds it for a specific time interval.

    Intended to keep load under control.

    Be aware that the callback has to be short, as it is called from the IOLoop main thread.
    """

    def __init__(self, interval: float = 1):
        """
        :param interval: time a cache entry is valid, in seconds
        """
        super().__init__()
        self.next_time: float = 0
        self.last_value: int = 0
        self.interval: float = interval

    def get_value(self) -> int:
        now = time()
        if now < self.next_time:
            return self.last_value
        self.last_value = self.callback()
        self.next_time = now + self.interval
        return self.last_value

    def callback(self) -> int:
        """
        Be aware that the callback has to be short, as it is called from the IOLoop main thread.
        :return: the value of the gauge
        """
        raise NotImplementedError()


class CPUMicroBenchMark(CachingCallbackGuage):
    def callback(self) -> int:
        """
        Determine baseline performance of the machine by running a short cpu benchmark

        :return: time required to perform a specific calculation, in ns, 100% cpu bound
        """
        start = perf_counter()
        # this value was chosen to be around 0.1ms on a reference machine
        # which is long enough to be meaningful, short enough to not be disturbing.
        # the value is cached for 1s, making this at most 0.1% of additional overhead
        self.factor(1100)
        end = perf_counter()
        result = int((end - start) * 1000000000)
        return result

    @staticmethod
    def factor(number: int) -> int:
        """A CPU intensive algorithm"""
        out = 0
        # for each potential factor i
        for i in range(2, number + 1):
            # if i is a factor of N, repeatedly divide it out
            while number % i == 0:
                out += i
                number = number / i

        # if biggest factor occurs only once, n > 1
        if number > 1:
            out += number

        return out
