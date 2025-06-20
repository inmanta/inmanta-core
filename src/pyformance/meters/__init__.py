from .counter import Counter
from .gauge import CallbackGauge, Gauge, SimpleGauge
from .histogram import Histogram
from .meter import Meter
from .timer import Timer

__all__ = ["Counter", "CallbackGauge", "Gauge", "SimpleGauge", "Histogram", "Meter", "Timer"]

type any_meter = Histogram | Meter | Gauge[int | float] | Timer | Counter
