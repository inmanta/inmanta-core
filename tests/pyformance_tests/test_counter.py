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

import pytest

from inmanta.vendor.pyformance.meters.counter import Counter


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
