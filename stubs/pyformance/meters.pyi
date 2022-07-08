from typing import Union, Callable


class Gauge(object):

    def get_value(self) -> Union[float, int, str, bool]: ...

class CallbackGauge(Gauge):

    def __init__(self, callback: Callable[[],Union[float, int, str, bool]]) -> None: ...

