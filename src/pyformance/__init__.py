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
[Java Metrics library by Coda Hale](http://metrics.dropwizard.io/), w
ith inspiration by [YUNOMI - Y U NO MEASURE IT?](https://github.com/richzeng/yunomi)

It was vendored into the inmanta source tree as the original was no longer maintained.
"""

from typing import Protocol


class Clock(Protocol):

    def time(self) -> float: ...


from .registry import MetricsRegistry as MetricsRegistry
from .registry import clear as clear
from .registry import count_calls as count_calls
from .registry import counter as counter
from .registry import dump_metrics as dump_metrics
from .registry import gauge as gauge
from .registry import global_registry as global_registry
from .registry import hist_calls as hist_calls
from .registry import histogram as histogram
from .registry import meter as meter
from .registry import meter_calls as meter_calls
from .registry import set_global_registry as set_global_registry
from .registry import time_calls as time_calls
from .registry import timer as timer
