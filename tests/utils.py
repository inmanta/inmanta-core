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
import asyncio
import inspect
import json
import logging
import time

from inmanta import data


async def retry_limited(fun, timeout):
    async def fun_wrapper():
        if inspect.iscoroutinefunction(fun):
            return await fun()
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
                return "_".join(key)

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


def no_error_in_logs(caplog, levels=[logging.ERROR], ignore_namespaces=["tornado.access"]):
    for logger_name, log_level, message in caplog.record_tuples:
        if logger_name in ignore_namespaces:
            continue
        assert log_level not in levels, f"{logger_name} {log_level} {message}"


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
    def __init__(self, caplog, index=0, allow_errors=True, ignore=[]):
        """

        :param caplog: caplog fixture
        :param index: start index in the log
        :param allow_errors: allow errors between log entries that are requested by log_contains
        :param ignore: ignore following namespaces
        """
        self.caplog = caplog
        self.index = index
        self.allow_errors = allow_errors
        self.ignore = ignore

    def _find(self, loggerpart, level, msg, after=0):
        for i, (logger_name, log_level, message) in enumerate(self.caplog.record_tuples[after:]):
            if msg in message:
                if loggerpart in logger_name and level == log_level:
                    if any(i in logger_name for i in self.ignore):
                        continue
                    return i + after
        return -1

    def contains(self, loggerpart, level, msg):
        index = self._find(loggerpart, level, msg, self.index)
        if not self.allow_errors:
            # first error is later
            idxe = self._find("", logging.ERROR, "", self.index)
            assert idxe == -1 or idxe >= index
        assert index >= 0
        return LogSequence(self.caplog, index + 1, self.allow_errors, self.ignore)

    def assert_not(self, loggerpart, level, msg):
        idx = self._find(loggerpart, level, msg, self.index)
        assert idx == -1, f"{idx}, {self.caplog.record_tuples[idx]}"

    def no_more_errors(self):
        self.assert_not("", logging.ERROR, "")


def configure(unused_tcp_port, database_name, database_port):
    from inmanta.config import Config

    import inmanta.agent.config  # noqa: F401
    import inmanta.server.config  # noqa: F401

    free_port = str(unused_tcp_port)
    Config.load_config()
    Config.set("server_rest_transport", "port", free_port)
    Config.set("agent_rest_transport", "port", free_port)
    Config.set("compiler_rest_transport", "port", free_port)
    Config.set("client_rest_transport", "port", free_port)
    Config.set("cmdline_rest_transport", "port", free_port)
    Config.set("database", "name", database_name)
    Config.set("database", "host", "localhost")
    Config.set("database", "port", str(database_port))


async def report_db_index_usage(min_precent=100):
    q = (
        "select relname ,idx_scan ,seq_scan , 100*idx_scan / (seq_scan + idx_scan) percent_of_times_index_used,"
        " n_live_tup rows_in_table, seq_scan * n_live_tup badness  FROM pg_stat_user_tables "
        "WHERE seq_scan + idx_scan > 0 order by badness desc"
    )
    async with data.Compile._connection_pool.acquire() as con:
        result = await con.fetch(q)

    for row in result:
        print(row)


async def wait_for_version(client, environment, cnt):
    start = time.time()

    # Wait until the server is no longer compiling
    # wait for it to finish
    async def compile_done():
        compiling = await client.is_compiling(environment)
        code = compiling.code
        return code == 204

    await retry_limited(compile_done, 10)

    reports = await client.get_reports(environment)
    for report in reports.result["reports"]:
        data = await client.get_report(report["id"])
        print(json.dumps(data.result, indent=4))
        assert report["success"]

    # wait for it to appear
    async def sufficient_versions():
        versions = await client.list_versions(environment)
        return versions.result["count"] >= cnt

    await retry_limited(sufficient_versions, 10)

    # Added until #1011 is implemented
    nextsecond = int(start) + 1
    await asyncio.sleep(nextsecond - time.time())
    versions = await client.list_versions(environment)
    return versions.result
