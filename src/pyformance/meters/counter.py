from threading import Lock


class Counter(object):
    """
    An incrementing and decrementing metric
    """

    def __init__(self) -> None:
        super(Counter, self).__init__()
        self.lock = Lock()
        self.counter = 0

    def inc(self, val: int = 1) -> None:
        "increment counter by val (default is 1)"
        with self.lock:
            self.counter = self.counter + val

    def dec(self, val: int = 1) -> None:
        "decrement counter by val (default is 1)"
        self.inc(-val)

    def get_count(self) -> int:
        "return current value of counter"
        return self.counter

    def clear(self) -> None:
        "reset counter to 0"
        with self.lock:
            self.counter = 0
