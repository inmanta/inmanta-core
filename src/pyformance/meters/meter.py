import time
from threading import Lock

from ..stats.moving_average import ExpWeightedMovingAvg


class Meter(object):
    """
    A meter metric which measures mean throughput and one-, five-, and fifteen-minute
    exponentially-weighted moving average throughputs.
    """

    def __init__(self, clock=time) -> None:
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
        elapsed = self.clock.time() - self.start_time
        return self.counter / elapsed
