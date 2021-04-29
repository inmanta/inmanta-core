from typing import Union


class Gauge(object):

    def get_value(self) -> Union[float, int, str]: ...
