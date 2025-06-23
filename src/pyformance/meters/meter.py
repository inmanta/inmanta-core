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

import time
from threading import Lock

from .. import Clock
from ..stats.moving_average import ExpWeightedMovingAvg


class Meter(object):
    """
    A meter metric which measures mean throughput and one-, five-, and fifteen-minute
    exponentially-weighted moving average throughputs.
    """

    def __init__(self, clock: Clock = time) -> None:
        super(Meter, self).__init__()
        self.lock = Lock()
        self.clock = clock
        self.clear()

    def clear(self) -> None:
        with self.lock:
            self.start_time = self.clock.time()
            self.counter = 0.0
            self.m1rate = ExpWeightedMovingAvg(period=1, clock=self.clock)
            self.m5rate = ExpWeightedMovingAvg(period=5, clock=self.clock)
            self.m15rate = ExpWeightedMovingAvg(period=15, clock=self.clock)

    def get_one_minute_rate(self) -> float:
        return self.m1rate.get_rate()

    def get_five_minute_rate(self) -> float:
        return self.m5rate.get_rate()

    def get_fifteen_minute_rate(self) -> float:
        return self.m15rate.get_rate()

    def tick(self) -> None:
        self.m1rate.tick()
        self.m5rate.tick()
        self.m15rate.tick()

    def mark(self, value: float = 1) -> None:
        with self.lock:
            self.counter += value
            self.m1rate.add(value)
            self.m5rate.add(value)
            self.m15rate.add(value)

    def get_count(self) -> float:
        return self.counter

    def get_mean_rate(self) -> float:
        if self.counter == 0:
            return 0
        elapsed: float = self.clock.time() - self.start_time
        return self.counter / elapsed
