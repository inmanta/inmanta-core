"""
Copyright 2014 Omer Gertel
Copyright 2025 Inmanta

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Contact: code@inmanta.com

This code was originally developed by Omer Gertel, as a python port of the core portion of a
[Java Metrics library by Coda Hale](http://metrics.dropwizard.io/)

It was vendored into the inmanta source tree as the original was no longer maintained.
"""

from pyformance.meters import Meter
from pytest import approx


def test__one_minute_rate(clock):
    meter = Meter(clock)
    meter.mark(3)
    clock.add(5)
    meter.tick()

    # the EWMA has a rate of 0.6 events/sec after the first tick
    assert 0.6 == approx(meter.get_one_minute_rate(), 0.000001)

    clock.add(60)
    # the EWMA has a rate of 0.22072766 events/sec after 1 minute
    assert 0.22072766 == approx(meter.get_one_minute_rate(), 0.000001)

    clock.add(60)
    # the EWMA has a rate of 0.08120117 events/sec after 2 minute
    assert 0.08120117 == approx(meter.get_one_minute_rate(), 0.000001)


def test__five_minute_rate(clock):
    meter = Meter(clock)

    meter.mark(3)
    clock.add(5)
    meter.tick()

    # the EWMA has a rate of 0.6 events/sec after the first tick
    assert 0.6 == approx(meter.get_five_minute_rate(), 0.000001)

    clock.add(60)
    # the EWMA has a rate of 0.49123845 events/sec after 1 minute
    assert 0.49123845 == approx(meter.get_five_minute_rate(), 0.000001)

    clock.add(60)
    # the EWMA has a rate of 0.40219203 events/sec after 2 minute
    assert 0.40219203 == approx(meter.get_five_minute_rate(), 0.000001)


def test__fifteen_minute_rate(clock):
    meter = Meter(clock)

    meter.mark(3)
    clock.add(5)
    meter.tick()

    # the EWMA has a rate of 0.6 events/sec after the first tick
    assert 0.6 == approx(meter.get_fifteen_minute_rate(), 0.000001)

    clock.add(60)
    # the EWMA has a rate of 0.56130419 events/sec after 1 minute
    assert 0.56130419 == approx(meter.get_fifteen_minute_rate(), 0.000001)

    clock.add(60)
    # the EWMA has a rate of 0.52510399 events/sec after 2 minute
    assert 0.52510399 == approx(meter.get_fifteen_minute_rate(), 0.000001)


def test__mean_rate(clock):
    meter = Meter(clock)

    meter.mark(60)
    clock.add(60)
    meter.tick()
    val = meter.get_mean_rate()
    assert 1 == val
