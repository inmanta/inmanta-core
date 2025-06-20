from typing import Callable, Union


class Gauge[T: Union[int, float]]:
    """
    A base class for reading of a particular.

    For example, to instrument a queue depth:

    class QueueLengthGaguge(Gauge):
        def __init__(self, queue):
            super(QueueGaguge, self).__init__()
            self.queue = queue

        def get_value(self):
            return len(self.queue)

    """

    def get_value(self) -> T:
        "A subclass of Gauge should implement this method"
        raise NotImplementedError()


class CallbackGauge[T: Union[int, float]](Gauge[T]):
    """
    A Gauge reading for a given callback
    """

    def __init__(self, callback: Callable[[], T]) -> None:
        "constructor expects a callable"
        super(CallbackGauge, self).__init__()
        self.callback = callback

    def get_value(self) -> T:
        "returns the result of callback which is executed each time"
        return self.callback()


class SimpleGauge[T: Union[int, float]](Gauge[T]):
    """
    A gauge which holds values with simple getter- and setter-interface
    """

    def __init__(self, value: T) -> None:
        "constructor accepts initial value"
        super(SimpleGauge, self).__init__()
        self._value = value

    def get_value(self) -> T:
        "getter returns current value"
        return self._value

    def set_value(self, value: T) -> None:
        "setter changes current value"
        # XXX: add locking?
        self._value = value


type AnyGauge = Gauge[float | int]
