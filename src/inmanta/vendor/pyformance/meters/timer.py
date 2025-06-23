"""
Copyright 2014 Omer Gertel
Copyright 2025 Inmanta

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

This code was originally developed by Omer Gertel, as a python port of the core portion of a
[Java Metrics library by Coda Hale](http://metrics.dropwizard.io/)

It was vendored into the inmanta source tree as the original was no longer maintained.
"""

import abc
import time
from types import TracebackType
from typing import Optional, Type

from .. import Clock
from ..stats.samples import DEFAULT_ALPHA, DEFAULT_SIZE, Sample
from ..stats.snapshot import Snapshot
from .histogram import Histogram
from .meter import Meter


class TimerSink(abc.ABC):

    @abc.abstractmethod
    def add(self, value: float) -> None:
        pass


class Timer(object):
    """
    A timer metric which aggregates timing durations and provides duration statistics, plus
    throughput statistics via Meter and Histogram.

    """

    def __init__(
        self,
        size: int = DEFAULT_SIZE,
        alpha: float = DEFAULT_ALPHA,
        clock: Clock = time,
        sink: TimerSink | None = None,
        sample: Sample | None = None,
    ) -> None:
        super(Timer, self).__init__()
        self.meter = Meter(clock=clock)
        self.hist = Histogram(size=size, alpha=alpha, clock=clock, sample=sample)
        self.sink = sink

    def get_count(self) -> float:
        "get count from internal histogram"
        return self.hist.get_count()

    def get_sum(self) -> float:
        "get sum from snapshot of internal histogram"
        return self.get_snapshot().get_sum()

    def get_max(self) -> float:
        "get max from snapshot of internal histogram"
        return self.get_snapshot().get_max()

    def get_min(self) -> float:
        "get min from snapshot of internal histogram"
        return self.get_snapshot().get_min()

    def get_mean(self) -> float:
        "get mean from snapshot of internal histogram"
        return self.get_snapshot().get_mean()

    def get_stddev(self) -> float:
        "get stddev from snapshot of internal histogram"
        return self.get_snapshot().get_stddev()

    def get_var(self) -> float:
        "get var from snapshot of internal histogram"
        return self.get_snapshot().get_var()

    def get_snapshot(self) -> Snapshot:
        "get snapshot from internal histogram"
        return self.hist.get_snapshot()

    def get_mean_rate(self) -> float:
        "get mean rate from internal meter"
        return self.meter.get_mean_rate()

    def get_one_minute_rate(self) -> float:
        "get 1 minut rate from internal meter"
        return self.meter.get_one_minute_rate()

    def get_five_minute_rate(self) -> float:
        "get 5 minute rate from internal meter"
        return self.meter.get_five_minute_rate()

    def get_fifteen_minute_rate(self) -> float:
        "get 15 rate from internal meter"
        return self.meter.get_fifteen_minute_rate()

    def _update(self, seconds: float) -> None:
        if seconds >= 0:
            self.hist.add(seconds)
            self.meter.mark()
            if self.sink:
                self.sink.add(seconds)

    def time(self, *args: object, **kwargs: object) -> "TimerContext":
        """
        Parameters will be sent to signal, if fired.
        Returns a timer context instance which can be used from a with-statement.
        Without with-statement you have to call the stop method on the context
        """
        return TimerContext(self, self.meter.clock, *args, **kwargs)

    def clear(self) -> None:
        "clear internal histogram and meter"
        self.hist.clear()
        self.meter.clear()


class TimerContext(object):
    def __init__(self, timer: Timer, clock: Clock, *args: object, **kwargs: object) -> None:
        super(TimerContext, self).__init__()
        self.clock = clock
        self.timer = timer
        self.start_time = self.clock.time()
        self.kwargs = kwargs
        self.args = args

    def stop(self) -> float:
        elapsed: float = self.clock.time() - self.start_time
        self.timer._update(elapsed)
        return elapsed

    def __enter__(self) -> None:
        pass

    def __exit__(self, t: Optional[Type[BaseException]], v: Optional[BaseException], tb: Optional[TracebackType]) -> None:
        self.stop()
