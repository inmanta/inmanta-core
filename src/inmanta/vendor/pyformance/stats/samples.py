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

import heapq
import math
import random
import time

from .. import Clock
from .snapshot import Snapshot

DEFAULT_SIZE = 1028
DEFAULT_ALPHA = 0.015


# TODO: do I ABC this, may cpst us a few % performance??
class Sample:
    def clear(self) -> None:
        raise NotImplementedError()

    def update(self, value: float) -> None:
        raise NotImplementedError()

    def get_snapshot(self) -> Snapshot:
        raise NotImplementedError()


class ExpDecayingSample(Sample):
    """
    An exponentially-decaying random sample of longs. Uses Cormode et al's
    forward-decaying priority reservoir sampling method to produce a
    statistically representative sample, exponentially biased towards newer
    entries.

    @see: <a href="http://www.research.att.com/people/Cormode_Graham/library/publications/CormodeShkapenyukSrivastavaXu09.pdf">
          Cormode et al. Forward Decay: A Practical Time Decay Model for
          Streaming Systems. ICDE '09: Proceedings of the 2009 IEEE
          International Conference on Data Engineering (2009)</a>
    """

    RESCALE_THREASHOLD = 3600.0  # 1 hour

    def __init__(self, size: int = DEFAULT_SIZE, alpha: float = DEFAULT_ALPHA, clock: Clock = time) -> None:
        """
        Creates a new L{ExponentiallyDecayingSample}.

        :type size: C{int}
        :param size: the number of samples to keep in the sampling reservoir
        :type alpha: C{float}
        :param alpha: the exponential decay factor; the higher this is, the more
                      biased the sample will be towards newer values
        :type clock: C{function}
        :param clock: the function used to return the current time, default to
                      seconds since the epoch; to be used with other time
                      units, or with the twisted clock for our testing purposes
        """
        super(ExpDecayingSample, self).__init__()
        self.clock = clock
        self.size = size
        self.alpha = alpha
        self.clear()

    def clear(self) -> None:
        self.values: dict[float, float] = {}
        self.priorities: list[float] = []
        self.counter = 0
        self.start_time = self.clock.time()
        self.next_time = self.clock.time() + ExpDecayingSample.RESCALE_THREASHOLD

    def get_size(self) -> int:
        return self.counter if self.counter < self.size else self.size

    def update(self, value: float) -> None:
        """
        Adds a value to the sample.

        :type value: C{int} or C{float}
        :param value: the value to be added
        """
        if self.size == 0:
            return
        self._rescale_if_necessary()
        priority = self._weight(self.clock.time() - self.start_time) / random.random()
        new_counter = self.counter + 1
        self.counter = new_counter

        if new_counter <= self.size:
            self.values[priority] = value
            heapq.heappush(self.priorities, priority)
        else:
            first = heapq.heappop(self.priorities)
            if first < priority:
                if priority not in self.values:
                    self.values[priority] = value
                    heapq.heappush(self.priorities, priority)
                    while first not in self.values:
                        first = heapq.heappop(self.priorities)
                    del self.values[first]
            else:
                heapq.heappush(self.priorities, first)

    def _rescale_if_necessary(self) -> None:
        if self.clock.time() >= self.next_time:
            self._rescale()

    def _rescale(self) -> None:
        self.next_time = self.clock.time() + ExpDecayingSample.RESCALE_THREASHOLD
        old_start_time = self.start_time
        self.start_time = self.clock.time()
        new_values = {}
        new_priorities: list[float] = []
        for key, val in self.values.items():
            priority = key * math.exp(-self.alpha * (self.start_time - old_start_time))
            new_values[priority] = val
            heapq.heappush(new_priorities, priority)
        self.values = new_values
        self.priorities = new_priorities
        self.counter = len(self.values)

    def _weight(self, value: float) -> float:
        return math.exp(self.alpha * value)

    def get_snapshot(self) -> Snapshot:
        return Snapshot(self.values.values())


class SlidingTimeWindowSample(Sample):
    """
    A sample of measurements made in a sliding time window.
    """

    DEFAULT_WINDOW = 300

    def __init__(self, window: int = DEFAULT_WINDOW, clock: Clock = time) -> None:
        """Creates a SlidingTimeWindowSample.

        :param window: the length of the time window in seconds
        :param clock: clock.time() is called to get the current time as seconds
                      since the epoch.
        """
        self.window = window
        self.clock = clock
        self.clear()

    def clear(self) -> None:
        self.values: list[tuple[float, float]] = []

    def _trim(self) -> None:
        deadline = self.clock.time() - self.window
        while self.values and self.values[0][0] < deadline:
            heapq.heappop(self.values)

    def update(self, value: float) -> None:
        heapq.heappush(self.values, (self.clock.time(), value))

    def get_snapshot(self) -> Snapshot:
        self._trim()
        return Snapshot(x[1] for x in self.values)
