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

from pyformance.meters import Histogram
from pytest import approx


def test__a_sample_of_100_from_1000():
    hist = Histogram(100, 0.99)
    for i in range(1000):
        hist.add(i)

    assert 1000 == hist.get_count()
    assert 100 == hist.sample.get_size()
    snapshot = hist.get_snapshot()
    assert 100 == snapshot.get_size()

    for i in snapshot.values:
        assert 0 <= i and i <= 1000

    assert 999 == hist.get_max()
    assert 0 == hist.get_min()
    assert 499.5 == hist.get_mean()
    assert 83416.6666 == approx(hist.get_var(), 0.0001)


def test__a_sample_of_100_from_10():
    hist = Histogram(100, 0.99)
    for i in range(10):
        hist.add(i)

    assert 10 == hist.get_count()
    assert 10 == hist.sample.get_size()
    snapshot = hist.get_snapshot()
    assert 10 == snapshot.get_size()

    for i in snapshot.values:
        assert 0 <= i and i <= 10

    assert 9 == hist.get_max()
    assert 0 == hist.get_min()
    assert 4.5 == hist.get_mean()
    assert 9.1666 == approx(hist.get_var(), 0.0001)


def test__a_long_wait_should_not_corrupt_sample(clock):
    hist = Histogram(10, 0.015, clock=clock)

    for i in range(1000):
        hist.add(1000 + i)
        clock.add(0.1)

    assert hist.get_snapshot().get_size() == 10
    for i in hist.sample.get_snapshot().values:
        assert 1000 <= i and i <= 2000

    clock.add(15 * 3600)  # 15 hours, should trigger rescale
    hist.add(2000)
    assert hist.get_snapshot().get_size() == 2
    for i in hist.sample.get_snapshot().values:
        assert 1000 <= i and i <= 3000

    for i in range(1000):
        hist.add(3000 + i)
        clock.add(0.1)
    assert hist.get_snapshot().get_size() == 10
    for i in hist.sample.get_snapshot().values:
        assert 3000 <= i and i <= 4000
