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
import math
import sys
from threading import Lock, Thread
from time import sleep, time, localtime

import pytest
from pytest import fixture

import time_machine
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
async def agent_cache(agent):
    pip_config = PipConfig()

    blueprint1 = executor.ExecutorBlueprint(
        pip_config=pip_config, requirements=(), sources=[], python_version=sys.version_info[:2]
    )

    myagent_instance = await agent.executor_manager.get_executor(
        "agent1", "local:", [executor.ResourceInstallSpec("test::Test", 5, blueprint1)]
    )
    yield myagent_instance._cache


async def test_timeout_automatic_cleanup(set_custom_cache_cleanup_policy, agent_cache):
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


def test_default_timeout(my_resource):
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
    traveller = time_machine.travel(datetime.datetime.now() + datetime.timedelta(seconds=5001))
    traveller.start()

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


async def test_decorator():
    def advance_time_and_cleanup(n_seconds: int):
        traveller = time_machine.travel(datetime.datetime.now() + datetime.timedelta(seconds=61))
        traveller.start()
        xcache.clean_stale_entries()

    class Closeable:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    my_closable = Closeable()

    xcache = AgentCache()

    class DT:
        def __init__(self, cache: AgentCache):
            self.cache = cache
            self.cache_miss_counters: dict[str, int] = {
                "basic_test": 0,
                "test_cacheNone": 0,
                "test_cache_none": 0
            }

        @cache()
        def test_method(self):
            self.cache_miss_counters["basic_test"] += 1
            return "x"

        @cache
        def test_method_2(self, dummy_arg, timeout=100, for_version=True):
            self.cache_miss_counters["basic_test"] += 1
            return "x2"

        @cache(cacheNone=False)
        def test_cacheNone(self):
            self.cache_miss_counters["test_cacheNone"] += 1
            if self.cache_miss_counters["test_cacheNone"] < 2:
                return None
            else:
                return "X"

        @cache(cache_none=False)
        def test_cache_none(self):
            self.cache_miss_counters["test_cache_none"] += 1
            if self.cache_miss_counters["test_cache_none"] < 2:
                return None
            else:
                return "X"

        @cache(call_on_delete=lambda x: x.close())
        def test_close(self):
            self.cache_miss_counters["basic_test"] += 1
            return my_closable

    test = DT(xcache)

    # Test basic caching / retrieval

    # 1 cache miss and 2 hits:
    assert "x" == test.test_method()
    assert "x" == test.test_method()
    assert "x" == test.test_method()
    assert 1 == test.cache_miss_counters["basic_test"]

    # 1 cache miss and 1 hit:
    assert "x2" == test.test_method_2(dummy_arg="AAA")
    assert "x2" == test.test_method_2(dummy_arg="AAA")
    assert 2 == test.cache_miss_counters["basic_test"]
    # 1 cache miss :
    assert "x2" == test.test_method_2(dummy_arg="BBB")
    assert 3 == test.cache_miss_counters["basic_test"]

    # Wait out lingering time of 60s after last read
    advance_time_and_cleanup(61)

    # 1 cache miss and 1 hit:
    assert "x2" == test.test_method_2(dummy_arg="AAA")
    assert "x2" == test.test_method_2(dummy_arg="AAA")
    assert 4 == test.cache_miss_counters["basic_test"]

    advance_time_and_cleanup(31)

    # 1 hit:
    assert "x2" == test.test_method_2(dummy_arg="AAA")
    assert 4 == test.cache_miss_counters["basic_test"]

    advance_time_and_cleanup(31)

    # 1 hit:
    assert "x2" == test.test_method_2(dummy_arg="AAA")
    assert 4 == test.cache_miss_counters["basic_test"]

    # Wait out lingering time of 60s after last read
    advance_time_and_cleanup(61)

    # 1 cache miss and 1 hit:
    assert "x2" == test.test_method_2(dummy_arg="AAA")
    assert "x2" == test.test_method_2(dummy_arg="AAA")
    assert 5 == test.cache_miss_counters["basic_test"]

    # Test cache_none and cacheNone arguments
    assert None is test.test_cacheNone()
    assert 1 == test.cache_miss_counters["test_cacheNone"]
    assert "X" == test.test_cacheNone()
    assert 2 == test.cache_miss_counters["test_cacheNone"]
    assert "X" == test.test_cacheNone()
    assert 2 == test.cache_miss_counters["test_cacheNone"]

    assert None is test.test_cache_none()
    assert 1 == test.cache_miss_counters["test_cache_none"]
    assert "X" == test.test_cache_none()
    assert 2 == test.cache_miss_counters["test_cache_none"]
    assert "X" == test.test_cache_none()
    assert 2 == test.cache_miss_counters["test_cache_none"]

    # Test call_on_delete
    test.test_close()
    assert not my_closable.closed
    xcache.close()
    assert my_closable.closed

    test.cache_miss_counters["basic_test"] = 0
    my_closable.closed = False

    test.cache_miss_counters["basic_test"] = 0
    test.test_close()
    assert test.cache_miss_counters["basic_test"] == 1
    test.test_close()
    assert test.cache_miss_counters["basic_test"] == 1
    assert not my_closable.closed

    advance_time_and_cleanup(5001)


    assert my_closable.closed

async def test_decorator_2():
    class FrozenCache(object):
        def __init__(self, cache: AgentCache):
            self.cache = cache

        def __enter__(self):
            self.cache.freeze()

        def __exit__(self, type, value, traceback):
            self.cache.unfreeze()

    def advance_time_and_cleanup(n_seconds: int):
        traveller = time_machine.travel(datetime.datetime.now() + datetime.timedelta(seconds=n_seconds))
        traveller.start()
        xcache.clean_stale_entries()

    xcache = AgentCache()
    class DT:
        def __init__(self, cache: AgentCache):
            self.cache = cache
            self.cache_miss_counters: dict[str, int] = {
                "basic_test": 0,
            }

        @cache
        def test_method_2(self, dummy_arg, timeout=100, for_version=True):
            self.cache_miss_counters["basic_test"] += 1
            return "x2"



    test = DT(xcache)

    with FrozenCache(xcache):
        # 1 cache miss and 1 hit:
        assert "x2" == test.test_method_2(dummy_arg="AAA")
        assert "x2" == test.test_method_2(dummy_arg="AAA")
        assert 1 == test.cache_miss_counters["basic_test"]
        # 1 cache miss :
        assert "x2" == test.test_method_2(dummy_arg="BBB")
        assert 2 == test.cache_miss_counters["basic_test"]

    # Wait out lingering time of 60s after last read
    advance_time_and_cleanup(61)

    with FrozenCache(xcache):
        # 1 cache miss and 1 hit:
        assert "x2" == test.test_method_2(dummy_arg="AAA")
        assert "x2" == test.test_method_2(dummy_arg="AAA")
        assert 3 == test.cache_miss_counters["basic_test"]

    advance_time_and_cleanup(31)

    with FrozenCache(xcache):
        # 1 hit:
        assert "x2" == test.test_method_2(dummy_arg="AAA")
        assert 3 == test.cache_miss_counters["basic_test"]

    advance_time_and_cleanup(31)

    with FrozenCache(xcache):
        # 1 hit:
        assert "x2" == test.test_method_2(dummy_arg="AAA")
        assert 3 == test.cache_miss_counters["basic_test"]

    # Wait out lingering time of 60s after last read
    advance_time_and_cleanup(61)

    with FrozenCache(xcache):
        # 1 cache miss and 1 hit:
        assert "x2" == test.test_method_2(dummy_arg="AAA")
        assert "x2" == test.test_method_2(dummy_arg="AAA")
        assert 4 == test.cache_miss_counters["basic_test"]


async def test_decorator_3():
    class FrozenCache(object):
        def __init__(self, cache: AgentCache):
            self.cache = cache

        def __enter__(self):
            self.cache.freeze()

        def __exit__(self, type, value, traceback):
            self.cache.unfreeze()

    def advance_time_and_cleanup(traveller, n_seconds: int):
        traveller.shift(datetime.timedelta(seconds=n_seconds))
        xcache.clean_stale_entries()

    xcache = AgentCache()
    class DT:
        def __init__(self, cache: AgentCache):
            self.cache = cache
            self.cache_miss_counters: dict[str, int] = {
                "basic_test": 0,
            }

        @cache
        def test_method_2(self, dummy_arg, timeout=100, for_version=True):
            self.cache_miss_counters["basic_test"] += 1
            return "x2"



    test = DT(xcache)

    with time_machine.travel(datetime.datetime.now().astimezone(), tick=False) as traveller:

        # cache : []  T=0
        with FrozenCache(xcache):
            # 1 cache miss
            assert "x2" == test.test_method_2(dummy_arg="AAA")
            # cache : [dummy_arg,'AAA'test_method_2 | x2]  expiry: +60
            # 1 hit
            assert "x2" == test.test_method_2(dummy_arg="AAA")
            # cache : [dummy_arg,'AAA'test_method_2 | x2]  expiry: +60

        assert 1 == test.cache_miss_counters["basic_test"]

        advance_time_and_cleanup(traveller, 31)

        # cache : [dummy_arg,'AAA'test_method_2 | x2]  expiry: +29

        with FrozenCache(xcache):
            # 1 hit:
            assert "x2" == test.test_method_2(dummy_arg="AAA")
            # cache : [dummy_arg,'AAA'test_method_2 | x2]  expiry: +60

        assert 1 == test.cache_miss_counters["basic_test"]

        advance_time_and_cleanup(traveller, 31)

        # cache : [dummy_arg,'AAA'test_method_2 | x2]  expiry: +29

        with FrozenCache(xcache):
            # 1 hit:
            assert "x2" == test.test_method_2(dummy_arg="AAA")
            # cache : [dummy_arg,'AAA'test_method_2 | x2]  expiry: +60

        assert 1 == test.cache_miss_counters["basic_test"]

        # Wait out lingering time of 60s after last read
        advance_time_and_cleanup(traveller, 61)
        # cache : []

        with FrozenCache(xcache):
            # 1 cache miss and 1 hit:
            assert "x2" == test.test_method_2(dummy_arg="AAA")
            assert "x2" == test.test_method_2(dummy_arg="AAA")

        assert 2 == test.cache_miss_counters["basic_test"]


def test_time_machine():
    def advance_time_and_cleanup(traveller, n_seconds: int):
        print("1")
        print(datetime.datetime.now().astimezone())
        traveller.shift(datetime.timedelta(seconds=n_seconds))
        print("22")
        print(datetime.datetime.now().astimezone())
        print("333")
        print(datetime.datetime.now().astimezone())

    with time_machine.travel(datetime.datetime.now().astimezone(), tick=False) as traveller:
        now = localtime(time())
        print(now)
        advance_time_and_cleanup(traveller, 60)
        now = localtime(time())
        print(now)
    #
    #
    # now = datetime.datetime.now().astimezone()
    # print(now)
    # advance_time_and_cleanup(60)
    # now = datetime.datetime.now().astimezone()
    # print(now)
