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

import math
from collections.abc import Iterable


class Snapshot(object):
    """
    This class is used by the histogram meter
    """

    MEDIAN = 0.5
    P75_Q = 0.75
    P95_Q = 0.95
    P99_Q = 0.99
    P999_Q = 0.999

    def __init__(self, values: Iterable[float]) -> None:
        super(Snapshot, self).__init__()
        self.values = sorted(values)

    def get_size(self) -> int:
        "get current size"
        return len(self.values)

    def get_sum(self) -> float:
        "get current sum"
        return float(sum(self.values))

    def get_max(self) -> float:
        "get current maximum value"
        if not self.values:
            return 0
        return self.values[-1]

    def get_min(self) -> float:
        "get current minimum value"
        if not self.values:
            return 0
        return self.values[0]

    def get_mean(self) -> float:
        "get current mean value"
        if not self.values:
            return 0
        return float(sum(self.values)) / self.get_size()

    def get_stddev(self) -> float:
        "get current standard deviation"
        if not self.values:
            return 0
        return math.sqrt(self.get_var())

    def get_var(self) -> float:
        "get current variance"
        if not self.values or self.get_size() == 1:
            return 0
        mean = self.get_mean()
        square_differences = [(mean - value) ** 2 for value in self.values]
        return sum(square_differences) / (self.get_size() - 1)

    def get_median(self) -> float:
        "get current median"
        return self.get_percentile(Snapshot.MEDIAN)

    def get_75th_percentile(self) -> float:
        "get current 75th percentile"
        return self.get_percentile(Snapshot.P75_Q)

    def get_95th_percentile(self) -> float:
        "get current 95th percentile"
        return self.get_percentile(Snapshot.P95_Q)

    def get_99th_percentile(self) -> float:
        "get current 99th percentile"
        return self.get_percentile(Snapshot.P99_Q)

    def get_999th_percentile(self) -> float:
        "get current 999th percentile"
        return self.get_percentile(Snapshot.P999_Q)

    def get_percentile(self, percentile: float) -> float:
        """
        get custom percentile

        :param percentile: float value between 0 and 1
        """
        if percentile < 0 or percentile > 1:
            raise ValueError("{0} is not in [0..1]".format(percentile))
        length = len(self.values)
        if length == 0:
            return 0
        pos = percentile * (length + 1)
        if pos < 1:
            return self.values[0]
        if pos >= length:
            return self.values[-1]
        lower = self.values[int(pos) - 1]
        upper = self.values[int(pos)]
        return lower + (pos - int(pos)) * (upper - lower)
