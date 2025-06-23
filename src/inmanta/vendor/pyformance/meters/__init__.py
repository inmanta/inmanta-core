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

from .counter import Counter
from .gauge import CallbackGauge, Gauge, SimpleGauge
from .histogram import Histogram
from .meter import Meter
from .timer import Timer

__all__ = ["Counter", "CallbackGauge", "Gauge", "SimpleGauge", "Histogram", "Meter", "Timer"]

type any_meter = Histogram | Meter | Gauge[int | float] | Timer | Counter
