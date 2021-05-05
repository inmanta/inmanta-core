from typing import Callable, Dict

from pyformance.meters import Gauge


class MetricsRegistry:
    def __init__(self, clock): ...
    def dump_metrics(self)-> Dict[str, Dict[str, float]]: ...

global_registry: Callable[[], MetricsRegistry]

def gauge(key: str, gauge: Gauge=None) -> Gauge: ...
