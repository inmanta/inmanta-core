from typing import Callable, Dict


class MetricsRegistry:
    def __init__(self, clock): ...
    def dump_metrics(self)-> Dict[str, Dict[str, float]]: ...

global_registry: Callable[[], MetricsRegistry]
