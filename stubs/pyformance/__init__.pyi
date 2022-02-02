from typing import Callable, Dict, Optional

from pyformance.meters import Gauge


class MetricsRegistry:
    def __init__(self, clock): ...
    def dump_metrics(self)-> Dict[str, Dict[str, float]]: ...

global_registry: Callable[[], MetricsRegistry]

def gauge(key: str, gauge: Optional[Gauge]=None) -> Gauge: ...
