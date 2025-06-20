import math
import time
from threading import Lock
from typing import Callable

from .. import Clock
from ..stats.samples import DEFAULT_ALPHA, DEFAULT_SIZE, ExpDecayingSample, Sample
from ..stats.snapshot import Snapshot


class Histogram(object):
    """
    A metric which calculates the distribution of a value.
    """

    counter: float  # Would be expected to be int?
    max: float
    min: float
    sum: float
    var: tuple[float, float]
    sample: Sample

    def __init__(
        self, size: int = DEFAULT_SIZE, alpha: float = DEFAULT_ALPHA, clock: Clock = time, sample: Sample | None = None
    ) -> None:
        """
        Creates a new instance of a L{Histogram}.
        """
        super(Histogram, self).__init__()
        self.lock = Lock()
        self.clock = clock
        if sample is None:
            sample = ExpDecayingSample(size, alpha, clock)
        self.sample = sample
        self.clear()

    def add(self, value: float) -> None:
        """
        Add value to histogram

        :type value: float
        """
        with self.lock:
            self.sample.update(value)
            self.counter = self.counter + 1
            self.max = value if value > self.max else self.max
            self.min = value if value < self.min else self.min
            self.sum = self.sum + value
            self._update_var(value)

    def clear(self) -> None:
        "reset histogram to initial state"
        with self.lock:
            self.sample.clear()
            self.counter = 0.0
            self.max = -2147483647.0
            self.min = 2147483647.0
            self.sum = 0.0
            self.var = (-1.0, 0.0)

    def get_count(self) -> float:
        "get current value of counter"
        return self.counter

    def get_sum(self) -> float:
        "get current sum"
        return self.sum

    def get_max(self) -> float:
        "get current maximum"
        return self.max

    def get_min(self) -> float:
        "get current minimum"
        return self.min

    def get_mean(self) -> float:
        "get current mean"
        if self.counter > 0:
            return self.sum / self.counter
        return 0

    def get_stddev(self) -> float:
        "get current standard deviation"
        if self.counter > 0:
            return math.sqrt(self.get_var())
        return 0

    def get_var(self) -> float:
        "get current variance"
        if self.counter > 1:
            return self.var[1] / (self.counter - 1)
        return 0

    def get_snapshot(self) -> Snapshot:
        "get snapshot instance which holds the percentiles"
        return self.sample.get_snapshot()

    def _update_var(self, value: float) -> None:
        old_m, old_s = self.var
        new_m, new_s = (0.0, 0.0)
        if old_m == -1:
            new_m = value
        else:
            new_m = old_m + ((value - old_m) / self.counter)
            new_s = old_s + ((value - old_m) * (value - new_m))
        self.var = (new_m, new_s)
