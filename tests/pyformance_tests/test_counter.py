import pytest
from pyformance.meters import Counter


@pytest.fixture
def counter():
    return Counter()


def test__inc(counter):
    before = counter.get_count()
    counter.inc()
    after = counter.get_count()
    assert before + 1 == after


def test__dec(counter):
    before = counter.get_count()
    counter.dec()
    after = counter.get_count()
    assert before - 1 == after
