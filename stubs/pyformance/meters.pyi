from typing import Union, Callable


class Gauge(object):

    # The code can handle string and bool as well
    # but influxdb can not
    def get_value(self) -> Union[float, int]: ...

class CallbackGauge(Gauge):

    def __init__(self, callback: Callable[[],Union[float, int]]) -> None: ...

