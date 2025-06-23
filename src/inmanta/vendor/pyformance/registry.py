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

import functools
import re
import time
from typing import Callable, Mapping, Optional, Union

from . import Clock
from .meters import CallbackGauge, Counter, Gauge, Histogram, Meter, SimpleGauge, Timer, any_meter
from .meters.gauge import AnyGauge
from .meters.timer import TimerSink

type serialized_meter = Mapping[str, str | int | float]


class MetricsRegistry:
    """
    A single interface used to gather metrics on a service. It keeps track of
    all the relevant Counters, Meters, Histograms, and Timers. It does not have
    a reference back to its service. The service would create a
    L{MetricsRegistry} to manage all of its metrics tools.
    """

    def __init__(self, clock: Clock = time) -> None:
        """
        Creates a new L{MetricsRegistry} instance.
        """
        self._timers: dict[str, Timer] = {}
        self._meters: dict[str, Meter] = {}
        self._counters: dict[str, Counter] = {}
        self._histograms: dict[str, Histogram] = {}
        self._gauges: dict[str, Gauge[Union[int, float]]] = {}
        self._clock = clock

    def add(self, key: str, metric: any_meter) -> None:
        """
        Use this method to manually add custom metric instances to the registry
        which are not created with their constructor's default arguments,
        e.g. Histograms with a different size.

        :param key: name of the metric
        :type key: C{str}
        :param metric: instance of Histogram, Meter, Gauge, Timer or Counter
        """
        class_map = (
            (Histogram, self._histograms),
            (Meter, self._meters),
            (Gauge, self._gauges),
            (Timer, self._timers),
            (Counter, self._counters),
        )
        for cls, registry in class_map:
            if isinstance(metric, cls):
                if key in registry:
                    raise LookupError("Metric %r already registered" % key)
                registry[key] = metric
                return
        raise TypeError("Invalid class. Could not register metric %r" % key)

    def counter(self, key: str) -> Counter:
        """
        Gets a counter based on a key, creates a new one if it does not exist.

        :param key: name of the metric
        :type key: C{str}

        :return: L{Counter}
        """
        if key not in self._counters:
            self._counters[key] = Counter()
        return self._counters[key]

    def histogram(self, key: str) -> Histogram:
        """
        Gets a histogram based on a key, creates a new one if it does not exist.

        :param key: name of the metric
        :type key: C{str}

        :return: L{Histogram}
        """
        if key not in self._histograms:
            self._histograms[key] = Histogram(clock=self._clock)
        return self._histograms[key]

    def gauge[T: float | int](
        self, key: str, gauge: Gauge[T] | Callable[[], T] | None = None, default: float = float("nan")
    ) -> AnyGauge:
        out: AnyGauge
        if key not in self._gauges:
            if gauge is None:
                out = SimpleGauge(default)  # raise TypeError("gauge required for registering")
            elif not isinstance(gauge, Gauge):
                if not callable(gauge):
                    raise TypeError("gauge getter not callable")
                out = CallbackGauge(gauge)
            else:
                out = gauge
            self._gauges[key] = out
        return self._gauges[key]

    def meter(self, key: str) -> Meter:
        """
        Gets a meter based on a key, creates a new one if it does not exist.

        :param key: name of the metric
        :type key: C{str}

        :return: L{Meter}
        """
        if key not in self._meters:
            self._meters[key] = Meter(clock=self._clock)
        return self._meters[key]

    def create_sink(self) -> TimerSink | None:
        return None

    def timer(self, key: str) -> Timer:
        """
        Gets a timer based on a key, creates a new one if it does not exist.

        :param key: name of the metric
        :type key: C{str}

        :return: L{Timer}
        """
        if key not in self._timers:
            self._timers[key] = Timer(clock=self._clock, sink=self.create_sink())
        return self._timers[key]

    def clear(self) -> None:
        self._meters.clear()
        self._counters.clear()
        self._gauges.clear()
        self._timers.clear()
        self._histograms.clear()

    def _get_counter_metrics(self, key: str) -> serialized_meter:
        if key in self._counters:
            counter = self._counters[key]
            return {"count": counter.get_count()}
        return {}

    def _get_gauge_metrics(self, key: str) -> serialized_meter:
        if key in self._gauges:
            gauge = self._gauges[key]
            return {"value": gauge.get_value()}
        return {}

    def _get_histogram_metrics(self, key: str) -> serialized_meter:
        if key in self._histograms:
            histogram = self._histograms[key]
            snapshot = histogram.get_snapshot()
            res = {
                "avg": snapshot.get_mean(),
                "count": histogram.get_count(),
                "max": snapshot.get_max(),
                "min": snapshot.get_min(),
                "std_dev": snapshot.get_stddev(),
                "75_percentile": snapshot.get_75th_percentile(),
                "95_percentile": snapshot.get_95th_percentile(),
                "99_percentile": snapshot.get_99th_percentile(),
                "999_percentile": snapshot.get_999th_percentile(),
            }
            return res
        return {}

    def _get_meter_metrics(self, key: str) -> serialized_meter:
        if key in self._meters:
            meter = self._meters[key]
            res = {
                "count": meter.get_count(),
                "15m_rate": meter.get_fifteen_minute_rate(),
                "5m_rate": meter.get_five_minute_rate(),
                "1m_rate": meter.get_one_minute_rate(),
                "mean_rate": meter.get_mean_rate(),
            }
            return res
        return {}

    def _get_timer_metrics(self, key: str) -> serialized_meter:
        if key in self._timers:
            timer = self._timers[key]
            snapshot = timer.get_snapshot()
            res = {
                "avg": timer.get_mean(),
                "sum": timer.get_sum(),
                "count": timer.get_count(),
                "max": timer.get_max(),
                "min": timer.get_min(),
                "std_dev": timer.get_stddev(),
                "15m_rate": timer.get_fifteen_minute_rate(),
                "5m_rate": timer.get_five_minute_rate(),
                "1m_rate": timer.get_one_minute_rate(),
                "mean_rate": timer.get_mean_rate(),
                "50_percentile": snapshot.get_median(),
                "75_percentile": snapshot.get_75th_percentile(),
                "95_percentile": snapshot.get_95th_percentile(),
                "99_percentile": snapshot.get_99th_percentile(),
                "999_percentile": snapshot.get_999th_percentile(),
            }
            return res
        return {}

    def get_metrics(self, key: str) -> serialized_meter:
        """
        Gets all the metrics for a specified key.

        :param key: name of the metric
        :type key: C{str}

        :return: C{dict}
        """
        metrics: dict[str, str | int | float] = {}
        getter: Callable[[str], serialized_meter]
        for getter in (
            self._get_counter_metrics,
            self._get_histogram_metrics,
            self._get_meter_metrics,
            self._get_timer_metrics,
            self._get_gauge_metrics,
        ):
            metrics.update(getter(key))
        return metrics

    def dump_metrics(self) -> Mapping[str, serialized_meter]:
        """
        Formats all of the metrics and returns them as a dict.

        :return: C{list} of C{dict} of metrics
        """
        metrics: dict[str, serialized_meter] = {}
        for metric_type in (
            self._counters,
            self._histograms,
            self._meters,
            self._timers,
            self._gauges,
        ):
            for key in metric_type.keys():
                metrics[key] = self.get_metrics(key)

        return metrics


class RegexRegistry(MetricsRegistry):
    r"""
    A single interface used to gather metrics on a service. This class uses a regex to combine
    measures that match a pattern. For example, if you have a REST API, instead of defining
    a timer for each method, you can use a regex to capture all API calls and group them.
    A pattern like '^/api/(?P<model>)/\d+/(?P<verb>)?$' will group and measure the following:
        /api/users/1 -> users
        /api/users/1/edit -> users/edit
        /api/users/2/edit -> users/edit
    """

    def __init__(self, pattern: Optional[str] = None, clock: Clock = time) -> None:
        super(RegexRegistry, self).__init__(clock)
        if pattern is not None:
            self.pattern = re.compile(pattern)
        else:
            self.pattern = re.compile("^$")

    def _get_key(self, key: str) -> str:
        matches = self.pattern.finditer(key)
        key = "/".join((v for match in matches for v in match.groups() if v))
        return key

    def timer(self, key: str) -> Timer:
        return super(RegexRegistry, self).timer(self._get_key(key))

    def histogram(self, key: str) -> Histogram:
        return super(RegexRegistry, self).histogram(self._get_key(key))

    def counter(self, key: str) -> Counter:
        return super(RegexRegistry, self).counter(self._get_key(key))

    def gauge[T: float | int](
        self, key: str, gauge: Gauge[T] | Callable[[], T] | None = None, default: float = float("nan")
    ) -> AnyGauge:
        return super(RegexRegistry, self).gauge(self._get_key(key), gauge, default)

    def meter(self, key: str) -> Meter:
        return super(RegexRegistry, self).meter(self._get_key(key))


_global_registry = MetricsRegistry()


def global_registry() -> MetricsRegistry:
    return _global_registry


def set_global_registry(registry: MetricsRegistry) -> None:
    global _global_registry
    _global_registry = registry


def counter(key: str) -> Counter:
    return _global_registry.counter(key)


def histogram(key: str) -> Histogram:
    return _global_registry.histogram(key)


def meter(key: str) -> Meter:
    return _global_registry.meter(key)


def timer(key: str) -> Timer:
    return _global_registry.timer(key)


def gauge(key: str, gauge: AnyGauge | None = None) -> AnyGauge:
    return _global_registry.gauge(key, gauge)


def dump_metrics() -> Mapping[str, serialized_meter]:
    return _global_registry.dump_metrics()


def clear() -> None:
    return _global_registry.clear()


def get_qualname[**P, R](obj: Callable[P, R]) -> str:
    return obj.__qualname__


def count_calls[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
    """
    Decorator to track the number of times a function is called.

    :param fn: the function to be decorated
    :type fn: C{func}

    :return: the decorated function
    :rtype: C{func}
    """

    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        counter("%s_calls" % get_qualname(fn)).inc()
        return fn(*args, **kwargs)

    return wrapper


def meter_calls[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
    """
    Decorator to the rate at which a function is called.

    :param fn: the function to be decorated
    :type fn: C{func}

    :return: the decorated function
    :rtype: C{func}
    """

    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        meter("%s_calls" % get_qualname(fn)).mark()
        return fn(*args, **kwargs)

    return wrapper


def hist_calls[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
    """
    Decorator to check the distribution of return values of a function.

    :param fn: the function to be decorated
    :type fn: C{func}

    :return: the decorated function
    :rtype: C{func}
    """

    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        _histogram = histogram("%s_calls" % get_qualname(fn))
        rtn = fn(*args, **kwargs)
        if isinstance(rtn, (int, float)):
            _histogram.add(rtn)
        return rtn

    return wrapper


def time_calls[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
    """
    Decorator to time the execution of the function.

    :param fn: the function to be decorated
    :type fn: C{func}

    :return: the decorated function
    :rtype: C{func}
    """

    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        _timer = timer("%s_calls" % get_qualname(fn))
        with _timer.time(fn=get_qualname(fn)):
            return fn(*args, **kwargs)

    return wrapper
