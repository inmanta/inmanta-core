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

from pytest import approx

from inmanta.vendor.pyformance.stats.moving_average import ExpWeightedMovingAvg


def test_one_minute_EWMA_five_sec_tick(clock):
    ewma = ExpWeightedMovingAvg(1, clock=clock)

    ewma.add(3)
    clock.add(5)
    ewma.tick()

    for expected_rate in [
        0.6,
        0.22072766,
        0.08120117,
        0.02987224,
        0.01098938,
        0.00404277,
        0.00148725,
        0.00054713,
        0.00020128,
        0.00007405,
    ]:
        assert ewma.get_rate() == approx(expected_rate, 0.0001)
        clock.add(60)


def test_five_minute_EWMA_five_sec_tick(clock):
    ewma = ExpWeightedMovingAvg(5, clock=clock)

    ewma.add(3)
    clock.add(5)
    ewma.tick()

    for expected_rate in [
        0.6,
        0.49123845,
        0.40219203,
        0.32928698,
        0.26959738,
        0.22072766,
        0.18071653,
        0.14795818,
        0.12113791,
        0.09917933,
    ]:
        assert ewma.get_rate() == approx(expected_rate)
        clock.add(60)


def test_fifteen_minute_EWMA_five_sec_tick(clock):
    ewma = ExpWeightedMovingAvg(15, clock=clock)

    ewma.add(3)
    clock.add(5)
    ewma.tick()

    for expected_rate in [
        0.6,
        0.56130419,
        0.52510399,
        0.49123845,
        0.45955700,
        0.42991879,
        0.40219203,
        0.37625345,
        0.35198773,
        0.32928698,
    ]:
        assert ewma.get_rate() == approx(expected_rate)
        clock.add(60)


def test_one_minute_EWMA_one_minute_tick(clock):
    ewma = ExpWeightedMovingAvg(1, 60, clock=clock)
    ewma.add(3)
    clock.add(5)
    ewma.tick()

    for expected_rate in [
        0.6,
        0.22072766,
        0.08120117,
        0.02987224,
        0.01098938,
        0.00404277,
        0.00148725,
        0.00054713,
        0.00020128,
        0.00007405,
    ]:
        assert ewma.get_rate() == approx(expected_rate, 0.0001)
        clock.add(60)


def test_five_minute_EWMA_one_minute_tick(clock):
    ewma = ExpWeightedMovingAvg(5, 60, clock=clock)

    ewma.add(3)
    clock.add(5)
    ewma.tick()

    for expected_rate in [
        0.6,
        0.49123845,
        0.40219203,
        0.32928698,
        0.26959738,
        0.22072766,
        0.18071653,
        0.14795818,
        0.12113791,
        0.09917933,
    ]:
        assert ewma.get_rate() == approx(expected_rate)
        clock.add(60)


def test_fifteen_minute_EWMA_one_minute_tick(clock):
    ewma = ExpWeightedMovingAvg(15, 60, clock=clock)

    ewma.add(3)
    clock.add(5)
    ewma.tick()

    for expected_rate in [
        0.6,
        0.56130419,
        0.52510399,
        0.49123845,
        0.45955700,
        0.42991879,
        0.40219203,
        0.37625345,
        0.35198773,
        0.32928698,
    ]:
        assert ewma.get_rate() == approx(expected_rate)
        clock.add(60)
