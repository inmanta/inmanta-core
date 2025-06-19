import pytest


class ManualClock(object):
    def __init__(self):
        super(ManualClock, self).__init__()
        self.now = 0

    def add(self, value):
        self.now = self.now + value

    def time(self):
        return self.now


@pytest.fixture
def clock():
    return ManualClock()
