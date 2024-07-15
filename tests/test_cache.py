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
import time
from threading import Lock, Thread
from time import sleep

import pytest
from pytest import fixture

import time_machine
from inmanta.agent import executor
from inmanta.agent.cache import AgentCache
from inmanta.agent.handler import cache
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


def code_for(bp: executor.ExecutorBlueprint) -> list[executor.ResourceInstallSpec]:
    return [executor.ResourceInstallSpec("test::Test", 5, bp)]

@pytest.fixture(scope="function")
async def agent_cache(agent):
    pip_config = PipConfig()

    blueprint1 = executor.ExecutorBlueprint(pip_config=pip_config, requirements=(), sources=[])

    myagent_instance = await agent.executor_manager.get_executor("agent1", "local:", code_for(blueprint1))
    yield myagent_instance._cache

async def test_timeout_automatic_cleanup(agent_cache):
    """
    Test timeout parameter: test that expired entry is removed from the cache
    """
    cache = agent_cache
    value = "test too"
    cache.cache_value("test", value, timeout=0.1)
    cache.cache_value("test2", value)

    assert value == cache.find("test")
    # Cache cleanup job is periodically triggered with a 1s delay
    print(cache)

    await asyncio.sleep(2)
    print(cache)
    with pytest.raises(KeyError):
        assert value == cache.find("test")

    assert value == cache.find("test2")


def test_timout_manual_cleanup():
    cache = AgentCache()
    value = "test too"
    cache.cache_value("test", value, timeout=0.1)
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
        assert value == cache.find("test")


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
        assert value == cache.find("testx")

    # default timeout is 5000s
    traveller = time_machine.travel(datetime.datetime.now() + datetime.timedelta(seconds=5001))
    traveller.start()

    # Check that values are still in the cache before running the cleanup job:
    assert value == cache.find("test")
    assert value == cache.find("testx", resource=resource)

    # Run the cleanup job and check removal
    cache.clean_stale_entries()
    with pytest.raises(KeyError):
        assert value == cache.find("test")

    with pytest.raises(KeyError):
        assert value == cache.find("testx")


def test_multi_threaded():

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
            with self.lock:
                self.deleted += 1

    cache = AgentCache()

    # Cache entry will be considered stale after 10s
    cache_entry_expiry = 10

    alpha = Spy()
    beta = Spy()
    alpha.lock.acquire()

    t1 = Thread(
        target=lambda: cache.get_or_else(
            "test", lambda: alpha.create(), timeout=cache_entry_expiry, call_on_delete=lambda x: x.delete()
        )
    )
    t2 = Thread(
        target=lambda: cache.get_or_else(
            "test", lambda: beta.create(), timeout=cache_entry_expiry, call_on_delete=lambda x: x.delete()
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


async def test_decorator(agent_cache):
    class Closeable:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    my_closable = Closeable()
    my_closable_2 = Closeable()

    xcache = agent_cache


    class DT:
        def __init__(self, cache: AgentCache):
            self.cache = cache
            self.count = 0
            self.c2 = 0
            self.c3 = 0

        @cache()
        def test_method(self):
            self.count += 1
            return "x"

        @cache
        def test_method_2(self, version, timeout=1):
            self.count += 1
            return "x2"

        @cache(cacheNone=False)
        def test_method_3(self):
            self.c2 += 1
            if self.c2 < 2:
                return None
            else:
                return "X"

        @cache(cache_none=False)
        def test_method_4(self):
            self.c3 += 1
            if self.c3 < 2:
                return None
            else:
                return "X"

        @cache(call_on_delete=lambda x: x.close())
        def test_close(self, version):
            self.count += 1
            return my_closable

        @cache(call_on_delete=lambda x: x.close())
        def test_close_2(self):
            self.count += 1
            return my_closable_2

    test = DT(xcache)

    test.test_close(version=3)
    test.test_close_2()
    xcache.close()
    assert my_closable.closed
    assert my_closable_2.closed

    test.count = 0
    my_closable.closed = False

    assert "x" == test.test_method()
    assert "x" == test.test_method()
    assert "x" == test.test_method()
    assert 1 == test.count

    assert "x2" == test.test_method_2(version=1)
    assert "x2" == test.test_method_2(version=1)
    assert 2 == test.count
    assert "x2" == test.test_method_2(version=2)
    assert 3 == test.count
    print(xcache)
    print(time.time())
    await asyncio.sleep(2)
    print(xcache)
    print(time.time())

    assert "x2" == test.test_method_2(version=1)
    assert "x2" == test.test_method_2(version=1)
    assert 4 == test.count

    assert None is test.test_method_3()
    assert 1 == test.c2
    assert "X" == test.test_method_3()
    assert 2 == test.c2
    assert "X" == test.test_method_3()
    assert 2 == test.c2

    assert None is test.test_method_4()
    assert 1 == test.c3
    assert "X" == test.test_method_4()
    assert 2 == test.c3
    assert "X" == test.test_method_4()
    assert 2 == test.c3

    test.count = 0
    test.test_close(version=3)
    assert test.count == 1
    test.test_close(version=3)
    assert test.count == 1
    assert not my_closable.closed
    assert my_closable.closed
