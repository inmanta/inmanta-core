from typing import Protocol

class Clock(Protocol):

    def time(self) -> float:
        ...

from .registry import (
    MetricsRegistry,
    clear,
    count_calls,
    counter,
    dump_metrics,
    gauge,
    global_registry,
    hist_calls,
    histogram,
    meter,
    meter_calls,
    set_global_registry,
    time_calls,
    timer,
)



