from pyformance.meters import CallbackGauge


def test_gauge():
    value = 123

    def test_callback() -> int:
        return value

    gauge = CallbackGauge(test_callback)
    assert gauge.get_value() == 123
