"""
    Copyright 2016 Inmanta

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
"""
import logging
import time
import asyncio
import inspect


async def retry_limited(fun, timeout):
    async def fun_wrapper():
        if inspect.iscoroutinefunction(fun):
            return (await fun())
        else:
            return fun()

    start = time.time()
    while time.time() - start < timeout and not (await fun_wrapper()):
        await asyncio.sleep(0.1)
    if not (await fun_wrapper()):
        raise AssertionError("Bounded wait failed")


UNKWN = object()


def assert_equal_ish(minimal, actual, sortby=[]):
    if isinstance(minimal, dict):
        for k in minimal.keys():
            assert_equal_ish(minimal[k], actual[k], sortby)
    elif isinstance(minimal, list):
        assert len(minimal) == len(actual), "list not equal %s != %s" % (minimal, actual)
        if len(sortby) > 0:
            def keyfunc(val):
                if not isinstance(val, dict):
                    return val
                key = [str(val[x]) for x in sortby if x in val]
                return '_'.join(key)
            actual = sorted(actual, key=keyfunc)
        for (m, a) in zip(minimal, actual):
            assert_equal_ish(m, a, sortby)
    elif minimal is UNKWN:
        return
    else:
        assert minimal == actual


def assert_graph(graph, expected):
    lines = ["%s: %s" % (f.id.get_attribute_value(), t.id.get_attribute_value()) for f in graph.values() for t in f.requires]
    lines = sorted(lines)

    elines = [x.strip() for x in expected.split("\n")]
    elines = sorted(elines)

    assert elines == lines, (lines, elines)


class AsyncClosing(object):

    def __init__(self, awaitable):
        self.awaitable = awaitable

    async def __aenter__(self):
        self.closable = await self.awaitable
        return object

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.closable.stop()


def no_error_in_logs(caplog, levels=[logging.ERROR]):
    for logger_name, log_level, message in caplog.record_tuples:
        assert log_level not in levels, message


def log_contains(caplog, loggerpart, level, msg):
    close = []
    for logger_name, log_level, message in caplog.record_tuples:
        if msg in message:
            if loggerpart in logger_name and level == log_level:
                return
            else:
                close.append((logger_name, log_level, message))
    if close:
        print("found nearly matching log entry")
        for logger_name, log_level, message in close:
            print(logger_name, log_level, message)
        print("------------")

    assert False


def log_doesnt_contain(caplog, loggerpart, level, msg):
    for logger_name, log_level, message in caplog.record_tuples:
        if loggerpart in logger_name and level == log_level and msg in message:
            assert False


def log_index(caplog, loggerpart, level, msg, after=0):
    """Find a log in line in the captured log, return the index of the first occurrence

       :param after: only consider records after the given index"""
    close = []
    for i, (logger_name, log_level, message) in enumerate(caplog.record_tuples[after:]):
        if msg in message:
            if loggerpart in logger_name and level == log_level:
                return i + after
            else:
                close.append((logger_name, log_level, message))

    if close:
        print("found nearly matching")
        for logger_name, log_level, message in close:
            print(logger_name, log_level, message)
        print("------------")

    assert False


class LogSequence(object):

    def __init__(self, caplog, index=0):
        self.caplog = caplog
        self.index = index

    def log_contains(self, loggerpart, level, msg):
        index = log_index(self.caplog, loggerpart, level, msg, self.index)
        return LogSequence(self.caplog, index)
