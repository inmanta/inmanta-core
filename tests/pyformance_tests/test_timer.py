from pyformance.meters import Timer

from tests import TimedTestCase


def test__start_stop_clear(clock):
    timer = Timer(clock=clock)

    context = timer.time()
    clock.add(1)
    context.stop()

    assert timer.get_count() == 1
    assert timer.get_max() == 1
    assert timer.get_min() == 1
    assert timer.get_mean() == 1
    assert timer.get_sum() == 1
    assert timer.get_mean_rate() == 1

    context = timer.time()
    clock.add(2)
    context.stop()

    assert timer.get_count() == 2
    assert timer.get_max() == 2
    assert timer.get_min() == 1
    assert timer.get_mean() == 1.5
    assert timer.get_snapshot().get_median() == 1.5
    assert timer.get_sum() == 3
    assert timer.get_mean_rate() == 2.0 / 3

    context = timer.time()
    clock.add(1)
    context.stop()

    assert timer.get_count() == 3
    assert timer.get_max() == 2
    assert timer.get_min() == 1
    assert timer.get_mean() == 4.0 / 3
    assert timer.get_snapshot().get_median() == 1
    assert timer.get_sum() == 4
    assert timer.get_mean_rate() == 0.75

    timer.clear()

    assert timer.get_count() == 0
