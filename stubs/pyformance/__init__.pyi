from collections import abc
from typing import Optional

from pyformance.meters import Gauge
from pyformance.meters import Timer



class MetricsRegistry:

    _gauges: dict[str, Gauge]

    def __init__(self, clock): ...
    def dump_metrics(self)-> abc.Mapping[str, abc.Mapping[str, int|float|str]]: ...

global_registry: abc.Callable[[], MetricsRegistry]

def gauge(key: str, gauge: Optional[Gauge]=None) -> Gauge: ...
def timer(key: str) -> Timer: ...
