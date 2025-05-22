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
import logging
import sys
import uuid
from threading import Lock, Thread
from time import sleep

import pytest
from pytest import fixture

from inmanta.agent import config as agent_config
from inmanta.agent import executor
from inmanta.agent.cache import AgentCache
from inmanta.agent.handler import cache
from inmanta.config import is_float
from inmanta.data import PipConfig
from inmanta.resources import Id, Resource, resource
from utils import log_contains


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
async def agent_cache(agent, environment):
    pip_config = PipConfig()

    blueprint1 = executor.ExecutorBlueprint(
        environment_id=uuid.UUID(environment),
        pip_config=pip_config,
        requirements=(),
        sources=[],
        python_version=sys.version_info[:2],
    )

    myagent_instance = await agent.executor_manager.delegate.get_executor(
        "agent1", "local:", [executor.ModuleInstallSpec("test", "abcdef", blueprint1)]
    )
    yield myagent_instance._cache


async def test_timeout_automatic_cleanup(set_custom_cache_cleanup_policy, agent_cache: AgentCache):
    """
    Test timeout parameter: test that expired entry is removed from the cache
    """
    cache = agent_cache
    value = "test too"
    cache.cache_value("test", value, evict_after_creation=0.1)
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
    cache.cache_value("test", value, evict_after_creation=0.1)
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

    cache.cache_value("test", value, evict_after_creation=5000)
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
            "test",
            lambda: alpha.create(),
            call_on_delete=lambda x: x.delete(),
            evict_after_creation=cache_entry_expiry,
        )

    t1 = Thread(target=target_1)
    t2 = Thread(
        target=lambda: cache.get_or_else(
            "test",
            lambda: beta.create(),
            call_on_delete=lambda x: x.delete(),
            evict_after_creation=cache_entry_expiry,
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


def test_get_or_else_backwards_compatibility(my_resource, time_machine):
    """
    Test backwards compatibility for the `get_or_else` method of the agent cache
    with the legacy parameters `for_version` and `timeout`.
    """
    called = []

    def creator(param, resource):
        called.append("x")
        return param

    cache = AgentCache()
    value = "test"
    resource = Id("test::Resource", "test", "key", "test", 100).get_instance()

    time_machine.move_to(datetime.datetime.now().astimezone(), tick=False)

    with cache:
        # Populate cache

        assert value == cache.get_or_else(
            "test_evict_after_last_access", creator, resource=resource, param=value, evict_after_last_access=60
        )  # cache miss
        assert len(called) == 1
        assert value == cache.get_or_else("test_evict_after_last_access", creator, resource=resource, param=value)  # cache hit
        assert len(called) == 1
        assert value == cache.get_or_else(
            "test_evict_after_creation", creator, resource=resource, param=value, for_version=False, timeout=100
        )  # cache miss
        assert len(called) == 2
        called = []

        # Populate cache with legacy variants

        assert value == cache.get_or_else(
            "legacy_test_evict_after_last_access", creator, resource=resource, param=value, for_version=True
        )  # cache miss
        assert len(called) == 1
        assert value == cache.get_or_else(
            "legacy_test_evict_after_last_access", creator, resource=resource, param=value
        )  # cache hit
        assert len(called) == 1
        assert value == cache.get_or_else(
            "legacy_test_evict_after_creation", creator, resource=resource, param=value, for_version=False, timeout=100
        )  # cache miss
        assert len(called) == 2

    time_machine.shift(datetime.timedelta(seconds=61))

    with cache:
        # Assert that the entries with evict_after_last_access semantics were removed:

        called = []
        assert value == cache.get_or_else("test_evict_after_last_access", creator, resource=resource, param=value)  # cache miss
        assert len(called) == 1
        assert value == cache.get_or_else("test_evict_after_creation", creator, resource=resource, param=value)  # cache hit
        assert len(called) == 1

        # Same for the legacy variant:

        called = []
        assert value == cache.get_or_else(
            "legacy_test_evict_after_last_access", creator, resource=resource, param=value
        )  # cache miss
        assert len(called) == 1
        assert value == cache.get_or_else(
            "legacy_test_evict_after_creation", creator, resource=resource, param=value
        )  # cache hit
        assert len(called) == 1

    time_machine.shift(datetime.timedelta(seconds=40))

    with cache:
        # Assert:
        #   - that the entries with evict_after_creation semantics were removed:
        #   - that the entries with evict_after_last_access semantics were refreshed by the last access:

        called = []
        assert value == cache.get_or_else("test_evict_after_last_access", creator, resource=resource, param=value)  # cache hit
        assert len(called) == 0
        assert value == cache.get_or_else("test_evict_after_creation", creator, resource=resource, param=value)  # cache miss
        assert len(called) == 1

        called = []
        assert value == cache.get_or_else(
            "legacy_test_evict_after_last_access", creator, resource=resource, param=value
        )  # cache hit
        assert len(called) == 0
        assert value == cache.get_or_else(
            "legacy_test_evict_after_creation", creator, resource=resource, param=value
        )  # cache miss
        assert len(called) == 1


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
    Test basic caching / retrieval functionalities of the @cache decorator.
    Test the default behaviour (evict 60s after last access) with and
    without an argument.
    """

    class BasicTest(CacheMissCounter):
        @cache
        def test_default_last_access_60_s_timeout(self):
            self.increment_miss_counter()
            return "x"

        @cache
        def test_defaults_with_argument(self, dummy_arg):
            self.increment_miss_counter()
            return "x2"

    agent_cache = AgentCache()
    test = BasicTest(agent_cache)

    time_machine.move_to(datetime.datetime.now().astimezone(), tick=False)
    with agent_cache:
        # 1 cache miss and 2 hits:
        assert "x" == test.test_default_last_access_60_s_timeout()  # +1 miss
        assert "x" == test.test_default_last_access_60_s_timeout()
        assert "x" == test.test_default_last_access_60_s_timeout()
        test.check_n_cache_misses(1)

        # 1 cache miss and 1 hit:
        assert "x2" == test.test_defaults_with_argument(dummy_arg="AAA")  # +1 miss
        assert "x2" == test.test_defaults_with_argument(dummy_arg="AAA")
        test.check_n_cache_misses(2)

        # 1 cache miss :
        assert "x2" == test.test_defaults_with_argument(dummy_arg="BBB")  # +1 miss
        test.check_n_cache_misses(3)

    # Wait out expiry time of 60s after last read
    time_machine.shift(datetime.timedelta(seconds=61))

    # The cache cleanup method is called upon entering the AgentCache context manager
    with agent_cache:
        # 1 cache miss and 1 hit:
        assert "x2" == test.test_defaults_with_argument(dummy_arg="AAA")  # +1 miss
        assert "x2" == test.test_defaults_with_argument(dummy_arg="AAA")
        test.check_n_cache_misses(4)

    time_machine.shift(datetime.timedelta(seconds=31))

    with agent_cache:
        # 1 hit:
        assert "x2" == test.test_defaults_with_argument(dummy_arg="AAA")
        test.check_n_cache_misses(4)

    time_machine.shift(datetime.timedelta(seconds=31))

    with agent_cache:
        # 1 hit:
        assert "x2" == test.test_defaults_with_argument(dummy_arg="AAA")
        test.check_n_cache_misses(4)

    # Wait out expiry time of 60s after last read
    time_machine.shift(datetime.timedelta(seconds=61))

    with agent_cache:
        # 1 cache miss and 1 hit:
        assert "x2" == test.test_defaults_with_argument(dummy_arg="AAA")  # +1 miss
        assert "x2" == test.test_defaults_with_argument(dummy_arg="AAA")
        test.check_n_cache_misses(5)


async def test_cache_decorator_last_access_expiry(time_machine):
    """
    Test the behaviour of cache entries expiring after last access.

    Cache entries will expire after their last access if:
      - for_version=True (legacy parameter), timeout controlled by the `timeout` legacy parameter.
      - a timeout is set via the `evict_after_last_access` parameter.

    """

    class EvictAfterLastAccessTest(CacheMissCounter):

        @cache(for_version=True)
        def _60s_legacy_for_version_true(self):
            self.increment_miss_counter()
            return "x2"

        @cache(timeout=1, for_version=True)
        def _60s_legacy_for_version_true_timeout_1s(self):
            """
            timeout param is ignored since it is an alias for evict_after_creation
            """
            self.increment_miss_counter()
            return "x4"

        @cache(timeout=1, evict_after_last_access=10)
        def _10s_legacy_test_new_param_override(self):
            self.increment_miss_counter()
            return "x4"

        @cache(timeout=1, evict_after_last_access=10, for_version=True)
        def _10s_legacy_test_new_param_override_for_version_true(self):
            self.increment_miss_counter()
            return "x4"

        @cache
        def evict_60s_after_last_access_default(self):
            self.increment_miss_counter()
            return "x1"

        @cache
        def evict_60s_after_last_access_default_with_arg(self, dummy_arg: str):
            self.increment_miss_counter()
            return dummy_arg

        @cache(evict_after_last_access=60)
        def evict_60s_after_last_access(self):
            self.increment_miss_counter()
            return "x2"

        @cache(evict_after_last_access=60)
        def evict_after_last_access_60s_with_arg(self, dummy_arg: str):
            self.increment_miss_counter()
            return dummy_arg

    agent_cache = AgentCache()
    test = EvictAfterLastAccessTest(agent_cache)

    time_machine.move_to(datetime.datetime.now().astimezone(), tick=False)

    with agent_cache:
        assert "initial_read" == test.evict_60s_after_last_access_default_with_arg(dummy_arg="initial_read")  # +1 miss
        assert "initial_read" == test.evict_after_last_access_60s_with_arg(dummy_arg="initial_read")  # +1 miss
        test.check_n_cache_misses(2)

    test.reset_miss_counter()

    with agent_cache:
        # Populate the cache
        assert "x1" == test.evict_60s_after_last_access_default()  # +1 miss
        assert "x2" == test.evict_60s_after_last_access()  # +1 miss

        test.check_n_cache_misses(2)
        test.reset_miss_counter()

        assert "recurring_read" == test.evict_60s_after_last_access_default_with_arg(dummy_arg="recurring_read")  # +1 miss
        assert "recurring_read" == test.evict_after_last_access_60s_with_arg(dummy_arg="recurring_read")  # +1 miss
        test.check_n_cache_misses(2)

    test.reset_miss_counter()

    # Check that the timeout parameter is correctly ignored
    time_machine.shift(datetime.timedelta(seconds=50))

    # The cache cleanup method is called upon entering the AgentCache context manager
    # All entries expiry times were refreshed after last access, check that we have 0 miss
    with agent_cache:
        assert "x1" == test.evict_60s_after_last_access_default()  # cache hit
        assert "x2" == test.evict_60s_after_last_access()  # cache hit
        assert "recurring_read" == test.evict_60s_after_last_access_default_with_arg(dummy_arg="recurring_read")  # cache hit
        assert "recurring_read" == test.evict_after_last_access_60s_with_arg(dummy_arg="recurring_read")  # cache hit
        test.check_n_cache_misses(0)

    test.reset_miss_counter()
    # Check that the "initial_read" entry was properly cleaned up but all other
    # entries remained in the cache.
    time_machine.shift(datetime.timedelta(seconds=50))

    with agent_cache:
        assert "x1" == test.evict_60s_after_last_access_default()  # cache hit
        assert "x2" == test.evict_60s_after_last_access()  # cache hit
        assert "recurring_read" == test.evict_60s_after_last_access_default_with_arg(dummy_arg="recurring_read")  # cache hit
        assert "recurring_read" == test.evict_after_last_access_60s_with_arg(dummy_arg="recurring_read")  # cache hit
        test.check_n_cache_misses(0)

        assert "initial_read" == test.evict_60s_after_last_access_default_with_arg(dummy_arg="initial_read")  # +1 miss
        assert "initial_read" == test.evict_after_last_access_60s_with_arg(dummy_arg="initial_read")  # +1 miss

        test.check_n_cache_misses(2)

    test.reset_miss_counter()

    # Expiry time was reset to 60s after last read.
    # Wait it out and check that all entries miss.
    time_machine.shift(datetime.timedelta(seconds=61))

    with agent_cache:
        assert "x1" == test.evict_60s_after_last_access_default()  # +1 miss
        assert "x2" == test.evict_60s_after_last_access()  # +1 miss
        assert "recurring_read" == test.evict_60s_after_last_access_default_with_arg(dummy_arg="recurring_read")  # +1 miss
        assert "recurring_read" == test.evict_after_last_access_60s_with_arg(dummy_arg="recurring_read")  # +1 miss
        assert "initial_read" == test.evict_60s_after_last_access_default_with_arg(dummy_arg="initial_read")  # +1 miss
        assert "initial_read" == test.evict_after_last_access_60s_with_arg(dummy_arg="initial_read")  # +1 miss
        test.check_n_cache_misses(6)

    test.reset_miss_counter()

    # test legacy parameters
    with agent_cache:
        assert "x2" == test._60s_legacy_for_version_true()  # +1 miss
        assert "x4" == test._60s_legacy_for_version_true_timeout_1s()  # +1 miss

        test.check_n_cache_misses(2)

    test.reset_miss_counter()
    time_machine.shift(datetime.timedelta(seconds=59))

    with agent_cache:
        assert "x2" == test._60s_legacy_for_version_true()  # +1 hit
        assert "x4" == test._60s_legacy_for_version_true_timeout_1s()  # +1 hit

        test.check_n_cache_misses(0)

    test.reset_miss_counter()
    time_machine.shift(datetime.timedelta(seconds=61))

    with agent_cache:
        assert "x2" == test._60s_legacy_for_version_true()  # +1 miss
        assert "x4" == test._60s_legacy_for_version_true_timeout_1s()  # +1 miss

        test.check_n_cache_misses(2)

    test.reset_miss_counter()

    with agent_cache:
        assert "x4" == test._10s_legacy_test_new_param_override()  # +1 miss
        test.check_n_cache_misses(1)

    test.reset_miss_counter()
    time_machine.shift(datetime.timedelta(seconds=9))

    with agent_cache:
        assert "x4" == test._10s_legacy_test_new_param_override()  # +1 hit
        test.check_n_cache_misses(0)

    test.reset_miss_counter()
    time_machine.shift(datetime.timedelta(seconds=11))

    with agent_cache:
        assert "x4" == test._10s_legacy_test_new_param_override()  # +1 miss
        test.check_n_cache_misses(1)


async def test_cache_decorator_since_creation_expiry(time_machine):
    """
    Test the behaviour of cache entries expiring after creation.

    Test legacy parameters:
        - for_version=False
        - timeout (default 5000s)

    Test new parameter:
        - evict_after_creation>0

    The legacy `timeout` parameter is now an alias for the `evict_after_creation` parameter.
    """

    class ExpireAfterCreationTest(CacheMissCounter):
        @cache(for_version=False)
        def test_default_5000s_timeout_legacy(self):
            self.increment_miss_counter()
            return "x1"

        @cache(timeout=80, for_version=False)
        def test_80s_timeout_legacy(self):
            self.increment_miss_counter()
            return "x2"

        @cache(timeout=80, for_version=False)
        def test_80s_timeout_with_arg_legacy(self, dummy_arg: str):
            self.increment_miss_counter()
            return dummy_arg

        @cache(timeout=20, for_version=False)
        def test_20s_timeout_legacy(self):
            self.increment_miss_counter()
            return "x4"

        @cache
        def baseline_evict_after_last_access(self):
            self.increment_miss_counter()
            return "x3"

        @cache(evict_after_creation=5000)
        def test_5000s_timeout(self):
            self.increment_miss_counter()
            return "x1"

        @cache(evict_after_creation=80)
        def test_80s_timeout(self):
            self.increment_miss_counter()
            return "x2"

        @cache(evict_after_creation=80)
        def test_80s_timeout_with_arg(self, dummy_arg: str):
            self.increment_miss_counter()
            return dummy_arg

        @cache(evict_after_creation=20)
        def test_20s_timeout(self):
            self.increment_miss_counter()
            return "x4"

        @cache(timeout=5000)
        def test_5000s_timeout_aliasing(self):
            self.increment_miss_counter()
            return "x1"

        @cache(timeout=80)
        def test_80s_timeout_aliasing(self):
            self.increment_miss_counter()
            return "x2"

        @cache(timeout=80)
        def test_80s_timeout_aliasing_with_arg(self, dummy_arg: str):
            self.increment_miss_counter()
            return dummy_arg

        @cache(timeout=20)
        def test_20s_timeout_aliasing(self):
            self.increment_miss_counter()
            return "x4"

    agent_cache = AgentCache()
    test = ExpireAfterCreationTest(agent_cache)

    time_machine.move_to(datetime.datetime.now().astimezone(), tick=False)

    with agent_cache:
        assert "initial_read" == test.test_80s_timeout_with_arg_legacy(dummy_arg="initial_read")  # +1 miss
        assert "initial_read" == test.test_80s_timeout_with_arg(dummy_arg="initial_read")  # +1 miss
        test.check_n_cache_misses(2)

    test.reset_miss_counter()

    with agent_cache:
        # Populate the cache
        assert "x1" == test.test_default_5000s_timeout_legacy()  # +1 miss
        assert "x1" == test.test_5000s_timeout()  # +1 miss
        assert "x2" == test.test_80s_timeout_legacy()  # +1 miss
        assert "x2" == test.test_80s_timeout()  # +1 miss
        assert "x3" == test.baseline_evict_after_last_access()  # +1 miss
        assert "x4" == test.test_20s_timeout_legacy()  # +1 miss
        assert "x4" == test.test_20s_timeout()  # +1 miss
        test.check_n_cache_misses(7)

        test.reset_miss_counter()

        assert "recurring_read" == test.test_80s_timeout_with_arg_legacy(dummy_arg="recurring_read")  # +1 miss
        assert "recurring_read" == test.test_80s_timeout_with_arg(dummy_arg="recurring_read")  # +1 miss
        test.check_n_cache_misses(2)
        test.reset_miss_counter()

        assert "x1" == test.test_5000s_timeout_aliasing()  # +1 miss
        assert "x2" == test.test_80s_timeout_aliasing()  # +1 miss
        assert "recurring_read" == test.test_80s_timeout_aliasing_with_arg(dummy_arg="recurring_read")  # +1 miss
        assert "x4" == test.test_20s_timeout_aliasing()  # +1 miss

        test.check_n_cache_misses(4)

    test.reset_miss_counter()

    # Check that entries are not cleaned up
    time_machine.shift(datetime.timedelta(seconds=61))

    # The cache cleanup method is called upon entering the AgentCache context manager
    with agent_cache:
        assert "x1" == test.test_default_5000s_timeout_legacy()  # cache hit
        assert "x1" == test.test_5000s_timeout()  # cache hit
        assert "x2" == test.test_80s_timeout_legacy()  # cache hit
        assert "x2" == test.test_80s_timeout()  # cache hit
        assert "recurring_read" == test.test_80s_timeout_with_arg_legacy(dummy_arg="recurring_read")  # cache hit
        assert "recurring_read" == test.test_80s_timeout_with_arg(dummy_arg="recurring_read")  # cache hit

        test.check_n_cache_misses(0)

        assert "x3" == test.baseline_evict_after_last_access()  # +1 miss
        assert "x4" == test.test_20s_timeout_legacy()  # +1 miss
        assert "x4" == test.test_20s_timeout()  # +1 miss

        test.check_n_cache_misses(3)
        test.reset_miss_counter()

        assert "x1" == test.test_5000s_timeout_aliasing()  # +1 hit
        assert "x2" == test.test_80s_timeout_aliasing()  # +1 hit
        assert "recurring_read" == test.test_80s_timeout_aliasing_with_arg(dummy_arg="recurring_read")  # +1 hit
        assert "x4" == test.test_20s_timeout_aliasing()  # +1 miss

        test.check_n_cache_misses(1)

    test.reset_miss_counter()

    time_machine.shift(datetime.timedelta(seconds=20))

    with agent_cache:
        # Check that entries with a lifetime of 80s after entering the cache got cleaned up:
        assert "x2" == test.test_80s_timeout_legacy()  # +1 miss
        assert "x2" == test.test_80s_timeout()  # +1 miss
        assert "recurring_read" == test.test_80s_timeout_with_arg_legacy(dummy_arg="recurring_read")  # +1 miss
        assert "recurring_read" == test.test_80s_timeout_with_arg(dummy_arg="recurring_read")  # +1 miss
        assert "initial_read" == test.test_80s_timeout_with_arg_legacy(dummy_arg="initial_read")  # +1 miss
        assert "initial_read" == test.test_80s_timeout_with_arg(dummy_arg="initial_read")  # +1 miss
        test.check_n_cache_misses(6)
        test.reset_miss_counter()

        # Check that entry with default timeout of 5000s wasn't cleaned up:
        assert "x1" == test.test_default_5000s_timeout_legacy()  # cache hit
        assert "x1" == test.test_5000s_timeout()  # cache hit
        test.check_n_cache_misses(0)
        test.reset_miss_counter()

        assert "x1" == test.test_5000s_timeout_aliasing()  # +1 hit
        assert "x2" == test.test_80s_timeout_aliasing()  # +1 miss
        assert "recurring_read" == test.test_80s_timeout_aliasing_with_arg(dummy_arg="recurring_read")  # +1 miss

        test.check_n_cache_misses(2)

    test.reset_miss_counter()

    # Wait out longer than the default timeout and check that the cache entry was cleaned up:
    time_machine.shift(datetime.timedelta(seconds=5001))

    with agent_cache:
        assert "x1" == test.test_default_5000s_timeout_legacy()  # +1 miss
        assert "x1" == test.test_5000s_timeout()  # +1 miss
        test.check_n_cache_misses(2)
        test.reset_miss_counter()

        assert "x1" == test.test_5000s_timeout_aliasing()  # +1 miss
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


async def test_cache_decorator_parameters(time_machine):
    """
    Test specific cache parameter combinations:
        - test that the legacy `for_version` parameter correctly overrides the 'new' parameters.

    """

    class CacheParametersTest(CacheMissCounter):
        @cache(for_version=False, evict_after_last_access=60)
        def test_legacy_override_ela(self):
            """
            for_version=False overrides evict_after_last_access behaviour:
            Use default for evict_after_creation = 5000s
            """
            self.increment_miss_counter()
            return "x1"

        @cache(for_version=True, evict_after_creation=5000)
        def test_legacy_override_eac(self):
            """
            for_version=True overrides evict_after_creation behaviour:
            Use default for evict_after_last_access = 60
            """
            self.increment_miss_counter()
            return "x2"

    agent_cache = AgentCache()
    test = CacheParametersTest(agent_cache)

    time_machine.move_to(datetime.datetime.now().astimezone(), tick=False)

    test.reset_miss_counter()

    with agent_cache:
        # Populate the cache
        assert "x1" == test.test_legacy_override_ela()  # +1 miss
        assert "x2" == test.test_legacy_override_eac()  # +1 miss
        test.check_n_cache_misses(2)

    test.reset_miss_counter()
    # Check that entries are not cleaned up
    time_machine.shift(datetime.timedelta(seconds=61))

    # The cache cleanup method is called upon entering the AgentCache context manager
    with agent_cache:
        assert "x1" == test.test_legacy_override_ela()  # cache hit
        test.check_n_cache_misses(0)
        assert "x2" == test.test_legacy_override_eac()  # cache miss
        test.check_n_cache_misses(1)

    test.reset_miss_counter()
    # Check that default timeout of 5000s is used
    time_machine.shift(datetime.timedelta(seconds=5001))

    # The cache cleanup method is called upon entering the AgentCache context manager
    with agent_cache:
        assert "x1" == test.test_legacy_override_ela()  # cache miss
        test.check_n_cache_misses(1)


async def test_cache_warning(time_machine, caplog):
    """
    Test that a warning is raised when both the `timeout` and the `evict_after_creation` are set
    """

    class CacheWarningTest(CacheMissCounter):
        @cache(for_version=False, timeout=60, evict_after_creation=20)
        def test_warning_and_override(self, dummy_arg: int):
            self.increment_miss_counter()
            return "x1"

    log_contains(
        caplog,
        "inmanta.agent.handler",
        logging.WARNING,
        "Both the `evict_after_creation` and the deprecated `timeout` parameter are set "
        "for cached method test_cache.test_warning_and_override. The `timeout` parameter will be ignored and cached entries "
        "will be kept in the cache for 20.00s after entering it. The `timeout` parameter should no"
        "longer be used. Please refer to the handler documentation "
        "for more information about setting a retention policy.",
    )

    agent_cache = AgentCache()
    test = CacheWarningTest(agent_cache)

    time_machine.move_to(datetime.datetime.now().astimezone(), tick=False)

    test.reset_miss_counter()

    # The cache cleanup method is called upon entering the AgentCache context manager
    with agent_cache:
        assert "x1" == test.test_warning_and_override(dummy_arg=1)  # cache miss
        test.check_n_cache_misses(1)

    time_machine.shift(datetime.timedelta(seconds=21))
    test.reset_miss_counter()

    with agent_cache:
        assert "x1" == test.test_warning_and_override(dummy_arg=1)  # cache miss
        test.check_n_cache_misses(1)
