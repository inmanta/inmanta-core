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
import datetime
import sys
from threading import Lock, Thread
from time import sleep

import pytest
from pytest import fixture

from inmanta.agent import Agent
from inmanta.agent import config as agent_config
from inmanta.agent import executor
from inmanta.agent.cache import AgentCache
from inmanta.agent.handler import cache
from inmanta.config import is_float
from inmanta.data import PipConfig
from inmanta.resources import Id, Resource, resource


@fixture()
def my_resource():
    @resource("test::Resource", agent="agent", id_attribute="key")
    class MyResource(Resource):
        """
        A file on a filesystem
        """

        fields = ("key", "value", "purged")


def test_base():
    """
    Basic test:
        - cache write
        - cache read
    """
    cache = AgentCache()
    value = "test too"
    cache.cache_value("test", value)
    assert value == cache.find("test")


@pytest.fixture
def set_custom_cache_cleanup_policy(monkeypatch, server_config):
    """
    Fixture to temporarily set the policy for cache cleanup.
    """
    old_value = agent_config.agent_cache_cleanup_tick_rate.get()

    monkeypatch.setattr(agent_config.agent_cache_cleanup_tick_rate, "validator", is_float)
    agent_config.agent_cache_cleanup_tick_rate.set("0.1")

    yield

    agent_config.agent_cache_cleanup_tick_rate.set(str(old_value))


@pytest.fixture(scope="function")
async def agent_cache(agent: Agent):
    pip_config = PipConfig()

    blueprint1 = executor.ExecutorBlueprint(
        pip_config=pip_config, requirements=(), sources=[], python_version=sys.version_info[:2]
    )

    myagent_instance = await agent.executor_manager.get_executor(
        "agent1", "local:", [executor.ResourceInstallSpec("test::Test", 5, blueprint1)]
    )
    yield myagent_instance._cache


async def test_timeout_automatic_cleanup(set_custom_cache_cleanup_policy, agent_cache: AgentCache):
    """
    Test timeout parameter: test that expired entry is removed from the cache
    """
    cache = agent_cache
    value = "test too"
    cache.cache_value("test", value, timeout=0.1, for_version=False)
    cache.cache_value("test2", value)

    assert value == cache.find("test")
    # Cache cleanup job is periodically triggered with a 0.1s delay
    await asyncio.sleep(0.3)
    with pytest.raises(KeyError):
        cache.find("test")

    assert value == cache.find("test2")


def test_timeout_manual_cleanup():
    cache = AgentCache()
    value = "test too"
    cache.cache_value("test", value, timeout=0.1, for_version=False)
    cache.cache_value("test2", value)

    assert value == cache.find("test")
    sleep(0.2)
    cache.clean_stale_entries()
    with pytest.raises(KeyError):
        assert value == cache.find("test")

    assert value == cache.find("test2")


def test_base_fail():
    """
    Test cache read on non-existing entry
    """
    cache = AgentCache()
    value = "test too"
    with pytest.raises(KeyError):
        assert value == cache.find("test")


def test_resource(my_resource):
    """
    Test writing and reading a resource from the agent cache
    """
    cache = AgentCache()
    value = "test too"
    resource = Id("test::Resource", "test", "key", "test", 100).get_instance()
    cache.cache_value("test", value, resource=resource)
    assert value == cache.find("test", resource=resource)


def test_resource_fail(my_resource):
    """
    Test that caching a resource correctly creates a single entry in the cache for the full key (args+resource_id)
    """
    cache = AgentCache()
    value = "test too"
    resource = Id("test::Resource", "test", "key", "test", 100).get_instance()
    cache.cache_value("test", value, resource=resource)

    with pytest.raises(KeyError):
        cache.find("test")


def test_default_timeout(my_resource, time_machine):
    """
    Test default timeout of cache entries for a regular entry (key='test') and
    for an entry associated with a resource (key=('testx', resource))
    """
    cache = AgentCache()
    value = "test too"

    cache.cache_value("test", value)
    assert value == cache.find("test")

    resource = Id("test::Resource", "test", "key", "test", 100).get_instance()
    cache.cache_value("testx", value, resource=resource)
    assert value == cache.find("testx", resource=resource)
    assert value, cache.find("testx", resource=resource)

    with pytest.raises(KeyError):
        cache.find("testx")

    # default timeout is 5000s
    time_machine.move_to(datetime.datetime.now() + datetime.timedelta(seconds=5001))

    # Check that values are still in the cache before running the cleanup job:
    assert value == cache.find("test")
    assert value == cache.find("testx", resource=resource)

    # Run the cleanup job and check removal
    cache.clean_stale_entries()
    with pytest.raises(KeyError):
        cache.find("test")

    with pytest.raises(KeyError):
        cache.find("testx")


async def test_multi_threaded(agent_cache: AgentCache):

    class Spy:
        def __init__(self):
            self.created = 0
            self.deleted = 0
            self.lock = Lock()

        def create(self):
            with self.lock:
                self.created += 1
            return self

        def delete(self):
            self.deleted += 1

    cache = agent_cache

    # Cache entry will be considered stale after 0.1s
    cache_entry_expiry = 0.1

    alpha = Spy()
    beta = Spy()
    alpha.lock.acquire()

    def target_1():
        cache.get_or_else(
            "test", lambda: alpha.create(), timeout=cache_entry_expiry, call_on_delete=lambda x: x.delete(), for_version=False
        )

    t1 = Thread(target=target_1)
    t2 = Thread(
        target=lambda: cache.get_or_else(
            "test", lambda: beta.create(), timeout=cache_entry_expiry, call_on_delete=lambda x: x.delete(), for_version=False
        )
    )

    t1.start()
    t2.start()

    alpha.lock.release()

    t1.join()
    t2.join()

    assert alpha.created + beta.created == 1
    assert alpha.deleted == 0
    assert beta.deleted == 0

    await asyncio.sleep(0.3)
    cache.clean_stale_entries()

    assert alpha.created + beta.created == 1
    assert beta.deleted == beta.created
    assert alpha.deleted == alpha.created


def test_get_or_else(my_resource):
    called = []

    def creator(param, resource):
        called.append("x")
        return param

    cache = AgentCache()
    value = "test too"
    value2 = "test too x"
    resource = Id("test::Resource", "test", "key", "test", 100).get_instance()
    resourcev2 = Id("test::Resource", "test", "key", "test", 200).get_instance()
    assert 200 == resourcev2.id.version
    assert value == cache.get_or_else("test", creator, resource=resource, param=value)
    assert value == cache.get_or_else("test", creator, resource=resource, param=value)
    assert len(called) == 1
    assert value == cache.get_or_else("test", creator, resource=resourcev2, param=value)
    assert len(called) == 1
    assert value2 == cache.get_or_else("test", creator, resource=resource, param=value2)


def test_get_or_else_none(my_resource):
    """
    Test the get_or_else cache_none parameter. This parameter controls
    whether None values are valid cache entries.
    """

    # This list is extended for each cache miss on the "creator" function
    called = []

    def creator(param, resource):
        called.append("x")
        return param

    class Sequencer:
        def __init__(self, sequence):
            self.seq = sequence
            self.count = 0

        def __call__(self, **kwargs):
            out = self.seq[self.count]
            self.count += 1
            return out

    cache = AgentCache()
    value = "test too"
    resource = Id("test::Resource", "test", "key", "test", 100).get_instance()

    # Check for 2 successive cache miss since caching None is disabled
    assert None is cache.get_or_else("test", creator, resource=resource, cache_none=False, param=None)
    assert len(called) == 1
    assert None is cache.get_or_else("test", creator, resource=resource, cache_none=False, param=None)
    assert len(called) == 2

    # Check for 1 cache miss and then a hit.
    assert value == cache.get_or_else("test", creator, resource=resource, cache_none=False, param=value)
    assert value == cache.get_or_else("test", creator, resource=resource, cache_none=False, param=value)
    assert len(called) == 3

    # The Sequencer will return the next item in the sequence on each cache miss
    seq = Sequencer([None, None, "A"])

    # Check that we have cache misses until the sequencer returns a non-None value.
    assert None is cache.get_or_else("testx", seq, resource=resource, cache_none=False)
    assert seq.count == 1
    assert None is cache.get_or_else("testx", seq, resource=resource, cache_none=False)
    assert seq.count == 2
    assert "A" == cache.get_or_else("testx", seq, resource=resource, cache_none=False)
    assert seq.count == 3
    assert "A" == cache.get_or_else("testx", seq, resource=resource, cache_none=False)
    assert seq.count == 3
    assert "A" == cache.get_or_else("testx", seq, resource=resource, cache_none=False)
    assert seq.count == 3


class CacheMissCounter:
    """
    Utility class wrapper around AgentCache providing
    functionality to count cache misses.
    """

    def __init__(self, cache: AgentCache):
        self.cache = cache
        self._counter = 0

    @property
    def cache_miss_counter(self):
        return self._counter

    def increment_miss_counter(self):
        self._counter += 1

    def reset_miss_counter(self):
        self._counter = 0

    def check_n_cache_misses(self, n: int):
        assert self._counter == n, f"Expected {n} cache misses, but counted {self._counter}."


async def test_cache_decorator_basics(time_machine):
    """
    Test basic caching / retrieval functionalities of the @cache decorator
    """

    class BasicTest(CacheMissCounter):
        @cache
        def test_method(self):
            self.increment_miss_counter()
            return "x"

        @cache
        def test_method_2(self, dummy_arg):
            self.increment_miss_counter()
            return "x2"

    agent_cache = AgentCache()
    test = BasicTest(agent_cache)

    time_machine.move_to(datetime.datetime.now().astimezone(), tick=False)
    with agent_cache:
        # 1 cache miss and 2 hits:
        assert "x" == test.test_method()  # +1 miss
        assert "x" == test.test_method()
        assert "x" == test.test_method()
        test.check_n_cache_misses(1)

        # 1 cache miss and 1 hit:
        assert "x2" == test.test_method_2(dummy_arg="AAA")  # +1 miss
        assert "x2" == test.test_method_2(dummy_arg="AAA")
        test.check_n_cache_misses(2)

        # 1 cache miss :
        assert "x2" == test.test_method_2(dummy_arg="BBB")  # +1 miss
        test.check_n_cache_misses(3)

    # Wait out lingering time of 60s after last read
    time_machine.shift(datetime.timedelta(seconds=61))

    # The cache cleanup method is called upon entering the AgentCache context manager
    with agent_cache:
        # 1 cache miss and 1 hit:
        assert "x2" == test.test_method_2(dummy_arg="AAA")  # +1 miss
        assert "x2" == test.test_method_2(dummy_arg="AAA")
        test.check_n_cache_misses(4)

    time_machine.shift(datetime.timedelta(seconds=31))

    with agent_cache:
        # 1 hit:
        assert "x2" == test.test_method_2(dummy_arg="AAA")
        test.check_n_cache_misses(4)

    time_machine.shift(datetime.timedelta(seconds=31))

    with agent_cache:
        # 1 hit:
        assert "x2" == test.test_method_2(dummy_arg="AAA")
        test.check_n_cache_misses(4)

    # Wait out lingering time of 60s after last read
    time_machine.shift(datetime.timedelta(seconds=61))

    with agent_cache:
        # 1 cache miss and 1 hit:
        assert "x2" == test.test_method_2(dummy_arg="AAA")  # +1 miss
        assert "x2" == test.test_method_2(dummy_arg="AAA")
        test.check_n_cache_misses(5)


async def test_cache_decorator_lingering_entries(time_machine):
    """
    Test the behaviour of lingering cache entries.

    Cache entries are considered lingering as long as for_version=True (default).
    The timeout argument is ignored for lingering entries.
    Lingering entries are considered stale 60s after their last use.
    Stale entries are cleaned up on the next call to `clean_stale_entries`.

    This test checks that this behaviour is consistent for the 4 combinations
    of (timeout, for_version) via `linger_test_method_1` to `linger_test_method_4`.

    `linger_test_method_5` is used to test that
        - a lingering entry is properly cleaned up if it is not being used ("initial_read" entry).
        - the expiry time of a lingering entry is properly reset to 60s when
          it is read ("recurring_read" entry).

    """

    class LingeringTest(CacheMissCounter):
        @cache
        def linger_test_method_1(self):
            self.increment_miss_counter()
            return "x1"

        @cache(for_version=True)
        def linger_test_method_2(self):
            self.increment_miss_counter()
            return "x2"

        @cache(timeout=1)
        def linger_test_method_3(self):
            self.increment_miss_counter()
            return "x3"

        @cache(timeout=1, for_version=True)
        def linger_test_method_4(self):
            self.increment_miss_counter()
            return "x4"

        @cache
        def linger_test_method_5(self, dummy_arg: str):
            self.increment_miss_counter()
            return dummy_arg

    agent_cache = AgentCache()
    test = LingeringTest(agent_cache)

    time_machine.move_to(datetime.datetime.now().astimezone(), tick=False)

    with agent_cache:
        assert "initial_read" == test.linger_test_method_5(dummy_arg="initial_read")  # +1 miss
        test.check_n_cache_misses(1)

    test.reset_miss_counter()

    with agent_cache:
        # Populate the cache
        assert "x1" == test.linger_test_method_1()  # +1 miss
        assert "x2" == test.linger_test_method_2()  # +1 miss
        assert "x3" == test.linger_test_method_3()  # +1 miss
        assert "x4" == test.linger_test_method_4()  # +1 miss
        test.check_n_cache_misses(4)

        assert "recurring_read" == test.linger_test_method_5(dummy_arg="recurring_read")  # +1 miss
        test.check_n_cache_misses(5)

    test.reset_miss_counter()

    # Check that the timeout parameter is correctly ignored
    time_machine.shift(datetime.timedelta(seconds=50))

    # The cache cleanup method is called upon entering the AgentCache context manager
    # All entries are lingering, check that we have 0 miss
    with agent_cache:
        assert "x1" == test.linger_test_method_1()  # cache hit
        assert "x2" == test.linger_test_method_2()  # cache hit
        assert "x3" == test.linger_test_method_3()  # cache hit
        assert "x4" == test.linger_test_method_4()  # cache hit
        assert "recurring_read" == test.linger_test_method_5(dummy_arg="recurring_read")  # cache hit
        test.check_n_cache_misses(0)

    # Check that the "initial_read" entry was properly cleaned up but all other
    # entries lingered on.
    time_machine.shift(datetime.timedelta(seconds=50))

    with agent_cache:
        assert "x1" == test.linger_test_method_1()  # cache hit
        assert "x2" == test.linger_test_method_2()  # cache hit
        assert "x3" == test.linger_test_method_3()  # cache hit
        assert "x4" == test.linger_test_method_4()  # cache hit
        assert "recurring_read" == test.linger_test_method_5(dummy_arg="recurring_read")  # cache hit
        test.check_n_cache_misses(0)

        assert "initial_read" == test.linger_test_method_5(dummy_arg="initial_read")  # +1 miss
        test.check_n_cache_misses(1)

    test.reset_miss_counter()

    # Wait out lingering time of 60s after last read, all entries should miss
    time_machine.shift(datetime.timedelta(seconds=61))

    with agent_cache:
        assert "x1" == test.linger_test_method_1()  # +1 miss
        assert "x2" == test.linger_test_method_2()  # +1 miss
        assert "x3" == test.linger_test_method_3()  # +1 miss
        assert "x4" == test.linger_test_method_4()  # +1 miss
        assert "recurring_read" == test.linger_test_method_5(dummy_arg="recurring_read")  # +1 miss
        assert "initial_read" == test.linger_test_method_5(dummy_arg="initial_read")  # +1 miss
        test.check_n_cache_misses(6)


async def test_cache_decorator_hard_expiry_entries(time_machine):
    """
    Test the behaviour of non-lingering cache entries.

    Cache entries are considered non-lingering when for_version=False.
    The timeout argument controls the lifetime of the entry since it entered the cache.
    Stale entries are cleaned up on the next call to `clean_stale_entries`.

    This test checks that this behaviour is consistent for the 4 combinations
    of (timeout, for_version) via `linger_test_method_1` to `linger_test_method_4`.

    `linger_test_method_5` is used to test that
        - a lingering entry is properly cleaned up if it is not being used ("initial_read" entry).
        - the expiry time of a lingering entry is properly reset to 60s when
          it is read ("recurring_read" entry).

    """

    class NonLingeringTest(CacheMissCounter):
        @cache(for_version=False)
        def non_linger_test_method_1(self):
            self.increment_miss_counter()
            return "x1"

        @cache(timeout=80, for_version=False)
        def non_linger_test_method_2(self):
            self.increment_miss_counter()
            return "x2"

        @cache(timeout=80, for_version=False)
        def non_linger_test_method_3(self, dummy_arg: str):
            self.increment_miss_counter()
            return dummy_arg

        @cache
        def linger_test_method(self):
            self.increment_miss_counter()
            return "x3"

        @cache(timeout=20, for_version=False)
        def short_lived_non_linger(self):
            self.increment_miss_counter()
            return "x4"

    agent_cache = AgentCache()
    test = NonLingeringTest(agent_cache)

    time_machine.move_to(datetime.datetime.now().astimezone(), tick=False)

    with agent_cache:
        assert "initial_read" == test.non_linger_test_method_3(dummy_arg="initial_read")  # +1 miss
        test.check_n_cache_misses(1)

    test.reset_miss_counter()

    with agent_cache:
        # Populate the cache
        assert "x1" == test.non_linger_test_method_1()  # +1 miss
        assert "x2" == test.non_linger_test_method_2()  # +1 miss
        assert "x3" == test.linger_test_method()  # +1 miss
        assert "x4" == test.short_lived_non_linger()  # +1 miss
        test.check_n_cache_misses(4)

        assert "recurring_read" == test.non_linger_test_method_3(dummy_arg="recurring_read")  # +1 miss
        test.check_n_cache_misses(5)

    test.reset_miss_counter()

    # Check that entries are not cleaned up
    time_machine.shift(datetime.timedelta(seconds=61))

    # The cache cleanup method is called upon entering the AgentCache context manager
    with agent_cache:
        assert "x1" == test.non_linger_test_method_1()  # cache hit
        assert "x2" == test.non_linger_test_method_2()  # cache hit
        assert "recurring_read" == test.non_linger_test_method_3(dummy_arg="recurring_read")  # cache hit
        assert "x3" == test.linger_test_method()  # +1 miss
        assert "x4" == test.short_lived_non_linger()  # +1 miss
        test.check_n_cache_misses(2)

    test.reset_miss_counter()

    time_machine.shift(datetime.timedelta(seconds=20))

    with agent_cache:
        # Check that non-lingering entries with an 80s timeout got cleaned up:
        assert "x2" == test.non_linger_test_method_2()  # +1 miss
        assert "recurring_read" == test.non_linger_test_method_3(dummy_arg="recurring_read")  # +1 miss
        assert "initial_read" == test.non_linger_test_method_3(dummy_arg="initial_read")  # +1 miss
        test.check_n_cache_misses(3)
        # Check that entry with default timeout of 5000s wasn't cleaned up:
        assert "x1" == test.non_linger_test_method_1()  # cache hit
        test.check_n_cache_misses(3)

    test.reset_miss_counter()

    # Wait out longer than the default timeout and check that the cache entry was cleaned up:
    time_machine.shift(datetime.timedelta(seconds=5000))

    with agent_cache:
        assert "x1" == test.non_linger_test_method_1()  # +1 miss
        test.check_n_cache_misses(1)


async def test_cache_decorator_cache_none():
    """
    Test the cache_none argument of the @cache decorator and the cacheNone legacy variant
    """

    class CacheNoneTest(CacheMissCounter):
        @cache(cache_none=False)
        def test_cache_none(self):
            self.increment_miss_counter()
            if self.cache_miss_counter < 2:
                return None
            else:
                return "X"

    agent_cache = AgentCache()
    test = CacheNoneTest(agent_cache)

    with agent_cache:
        assert None is test.test_cache_none()
        test.check_n_cache_misses(1)
        assert "X" == test.test_cache_none()
        test.check_n_cache_misses(2)
        assert "X" == test.test_cache_none()
        test.check_n_cache_misses(2)

    class CacheNoneTestLegacy(CacheMissCounter):
        @cache(cacheNone=False)
        def test_cacheNone(self):
            self.increment_miss_counter()
            if self.cache_miss_counter < 2:
                return None
            else:
                return "X"

    agent_cache = AgentCache()
    test = CacheNoneTestLegacy(agent_cache)

    with agent_cache:
        assert None is test.test_cacheNone()
        test.check_n_cache_misses(1)
        assert "X" == test.test_cacheNone()
        test.check_n_cache_misses(2)
        assert "X" == test.test_cacheNone()
        test.check_n_cache_misses(2)


async def test_cache_decorator_call_on_delete(time_machine):
    """
    Test the call_on_delete argument of the cache decorator
    """

    class Closeable:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    my_closable = Closeable()

    agent_cache = AgentCache()

    class CallOnDeleteTest(CacheMissCounter):
        @cache(call_on_delete=lambda x: x.close())
        def test_close(self):
            self.increment_miss_counter()
            return my_closable

    test = CallOnDeleteTest(agent_cache)

    time_machine.move_to(datetime.datetime.now().astimezone(), tick=False)
    # Test call_on_delete
    with agent_cache:
        test.test_close()

    assert not my_closable.closed
    agent_cache.close()
    assert my_closable.closed

    test.reset_miss_counter()
    my_closable.closed = False

    with agent_cache:
        test.test_close()
        test.check_n_cache_misses(1)
        test.test_close()
        test.check_n_cache_misses(1)
        assert not my_closable.closed

    time_machine.shift(datetime.timedelta(seconds=61))
    agent_cache.clean_stale_entries()

    assert my_closable.closed

    test.reset_miss_counter()
    my_closable.closed = False

    with agent_cache:
        test.test_close()
        test.check_n_cache_misses(1)
        assert not my_closable.closed

    time_machine.shift(datetime.timedelta(seconds=61))
    # The cache entry is stale but still in the cache since
    # clean_stale_entries wasn't called yet.
    assert not my_closable.closed

    # Upon entering the cache we call clean_stale_entries:
    with agent_cache:
        assert my_closable.closed
