from typing import Protocol


class Clock(Protocol):

    def time(self) -> float: ...


from .registry import MetricsRegistry as MetricsRegistry
from .registry import clear as clear
from .registry import count_calls as count_calls
from .registry import counter as counter
from .registry import dump_metrics as dump_metrics
from .registry import gauge as gauge
from .registry import global_registry as global_registry
from .registry import hist_calls as hist_calls
from .registry import histogram as histogram
from .registry import meter as meter
from .registry import meter_calls as meter_calls
from .registry import set_global_registry as set_global_registry
from .registry import time_calls as time_calls
from .registry import timer as timer
