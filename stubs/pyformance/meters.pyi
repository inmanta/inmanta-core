from types import TracebackType
from typing import Union, Callable


class Gauge(object):

    # The code can handle string and bool as well
    # but influxdb can not
    def get_value(self) -> Union[float, int]: ...

class CallbackGauge(Gauge):

    def __init__(self, callback: Callable[[],Union[float, int]]) -> None: ...



class TimerContext(object):
    def __enter__(self) -> None: ...

    def __exit__(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None, /) -> None: ...

class Timer(object):

    def time(self) -> TimerContext: ...
