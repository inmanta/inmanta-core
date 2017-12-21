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
import unittest
from time import sleep

from inmanta.agent.handler import cache
from inmanta.agent.cache import AgentCache
from inmanta.resources import resource, Resource, Id
import pytest
from _pytest.fixtures import fixture
from threading import Lock, Thread


@fixture(autouse=True)
def my_resource():
    @resource("test::Resource", agent="agent", id_attribute="key")
    class MyResource(Resource):
        """
            A file on a filesystem
        """
        fields = ("key", "value", "purged", "state_id", "allow_snapshot", "allow_restore")


class CacheTests(unittest.TestCase):

    def test_base(self):
        cache = AgentCache()
        value = "test too"
        cache.cache_value("test", value)
        assert value == cache.find("test")

    def test_timout(self):
        cache = AgentCache()
        value = "test too"
        cache.cache_value("test", value, timeout=0.1)
        cache.cache_value("test2", value)

        assert value == cache.find("test")
        sleep(1)
        try:
            assert value == cache.find("test")
            raise AssertionError("Should get exception")
        except KeyError:
            pass

        assert value == cache.find("test2")

    def test_base_fail(self):
        cache = AgentCache()
        value = "test too"
        with pytest.raises(KeyError):
            assert value == cache.find("test")

    def test_resource(self):
        cache = AgentCache()
        value = "test too"
        resource = Id("test::Resource", "test", "key", "test", 100).get_instance()
        cache.cache_value("test", value, resource=resource)
        assert value == cache.find("test", resource=resource)

    def test_resource_fail(self):
        cache = AgentCache()
        value = "test too"
        resource = Id("test::Resource", "test", "key", "test", 100).get_instance()
        cache.cache_value("test", value, resource=resource)

        with pytest.raises(KeyError):
            assert value == cache.find("test")

    def test_version_closed(self):
        cache = AgentCache()
        value = "test too"
        version = 200
        with pytest.raises(Exception):
            cache.cache_value("test", value, version=version)
            assert value == cache.find("test", version=version)

    def test_version(self):
        cache = AgentCache()
        value = "test too"
        version = 200
        cache.open_version(version)
        cache.cache_value("test", value, version=version)
        assert value == cache.find("test", version=version)

    def test_version_close(self):
        cache = AgentCache()
        value = "test too"
        version = 200
        cache.open_version(version)
        cache.cache_value("test", value, version=version)
        cache.cache_value("test0", value, version=version)
        cache.cache_value("test4", value, version=version)
        resource = Id("test::Resource", "test", "key", "test", 100).get_instance()
        cache.cache_value("testx", value, resource=resource)
        assert value == cache.find("test", version=version)
        assert value == cache.find("testx", resource=resource)
        cache.close_version(version)
        assert value, cache.find("testx", resource=resource)
        try:
            assert value == cache.find("test", version=version)
            raise AssertionError("Should get exception")
        except KeyError:
            pass

    def test_multi_threaded(self):
        class Spy(object):

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

        cache = AgentCache()
        version = 200

        cache.open_version(version)

        alpha = Spy()
        beta = Spy()
        alpha.lock.acquire()

        t1 = Thread(target=lambda: cache.get_or_else(
            "test", lambda version: alpha.create(), version=version, call_on_delete=lambda x: x.delete()))
        t2 = Thread(target=lambda: cache.get_or_else(
            "test", lambda version: beta.create(), version=version, call_on_delete=lambda x: x.delete()))

        t1.start()
        t2.start()

        alpha.lock.release()

        t1.join()
        t2.join()

        assert alpha.created + beta.created == 1
        assert alpha.deleted == 0
        assert beta.deleted == 0

        cache.close_version(version)

        assert alpha.created + beta.created == 1
        assert alpha.deleted == alpha.created
        assert beta.deleted == beta.created

    def test_timout_and_version(self):
        cache = AgentCache()
        version = 200

        cache.open_version(version)
        value = "test too"
        cache.cache_value("test", value, version=version, timeout=0.3)
        cache.cache_value("testx", value)

        assert value == cache.find("test", version=version)
        assert value == cache.find("testx")

        sleep(1)
        assert value == cache.find("testx")

        cache.close_version(version)
        assert value == cache.find("testx")

        with pytest.raises(KeyError):
            cache.find("test", version=version)
        assert value == cache.find("testx")

    def test_version_and_timout(self):
        cache = AgentCache()
        version = 200

        cache.open_version(version)
        value = "test too"
        cache.cache_value("test", value, version=version, timeout=0.3)
        cache.cache_value("testx", value)

        assert value == cache.find("test", version=version)
        assert value == cache.find("testx")

        cache.close_version(version)
        assert value == cache.find("testx")

        sleep(1)
        assert value == cache.find("testx")

        with pytest.raises(KeyError):
            cache.find("test", version=version)

    def test_version_fail(self):
        cache = AgentCache()
        value = "test too"
        version = 200
        cache.open_version(version)
        cache.cache_value("test", value, version=version)

        with pytest.raises(KeyError):
            assert value == cache.find("test")

    def test_resource_and_version(self):
        cache = AgentCache()
        value = "test too"
        resource = Id("test::Resource", "test", "key", "test", 100).get_instance()
        version = 200
        cache.open_version(version)
        cache.cache_value("test", value, resource=resource, version=version)
        assert value == cache.find("test", resource=resource, version=version)

    def test_get_or_else(self):
        called = []

        def creator(param, resource, version):

            called.append("x")
            return param

        cache = AgentCache()
        value = "test too"
        value2 = "test too x"
        resource = Id("test::Resource", "test", "key", "test", 100).get_instance()
        resourcev2 = Id("test::Resource", "test", "key", "test", 200).get_instance()
        assert 200 == resourcev2.id.version
        version = 200
        cache.open_version(version)
        assert value == cache.get_or_else("test", creator, resource=resource, version=version, param=value)
        assert value == cache.get_or_else("test", creator, resource=resource, version=version, param=value)
        assert len(called) == 1
        assert value == cache.get_or_else("test", creator, resource=resourcev2, version=version, param=value)
        assert len(called) == 1
        assert value2 == cache.get_or_else("test", creator, resource=resource, version=version, param=value2)

    def test_get_or_else_none(self):
        called = []

        def creator(param, resource, version):
            called.append("x")
            return param

        class Sequencer(object):

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
        version = 100
        cache.open_version(version)
        assert None is cache.get_or_else("test", creator, resource=resource, version=version, cache_none=False, param=None)
        assert len(called) == 1
        assert None is cache.get_or_else("test", creator, resource=resource, version=version, cache_none=False, param=None)
        assert len(called) == 2
        assert value == cache.get_or_else("test", creator, resource=resource, version=version, cache_none=False, param=value)
        assert value == cache.get_or_else("test", creator, resource=resource, version=version, cache_none=False, param=value)
        assert len(called) == 3

        seq = Sequencer([None, None, "A"])
        assert None is cache.get_or_else("testx", seq, resource=resource, version=version, cache_none=False)
        assert seq.count == 1
        assert None is cache.get_or_else("testx", seq, resource=resource, version=version, cache_none=False)
        assert seq.count == 2
        assert "A" is cache.get_or_else("testx", seq, resource=resource, version=version, cache_none=False)
        assert seq.count == 3
        assert "A" is cache.get_or_else("testx", seq, resource=resource, version=version, cache_none=False)
        assert seq.count == 3
        assert "A" is cache.get_or_else("testx", seq, resource=resource, version=version, cache_none=False)
        assert seq.count == 3

    def test_decorator(self):

        xcache = AgentCache()

        class DT(object):

            def __init__(self, cache):
                self.cache = cache
                self.count = 0
                self.c2 = 0

            @cache
            def test_method(self):
                self.count += 1
                return "x"

            @cache
            def test_method_2(self, version):
                self.count += 1
                return "x2"

            @cache(cacheNone=False)
            def test_method_3(self):
                self.c2 += 1
                if self.c2 < 2:
                    return None
                else:
                    return "X"

        test = DT(xcache)
        assert "x" == test.test_method()
        assert "x" == test.test_method()
        assert "x" == test.test_method()
        assert 1 == test.count

        xcache.open_version(1)
        xcache.open_version(2)
        assert "x2" == test.test_method_2(version=1)
        assert "x2" == test.test_method_2(version=1)
        assert 2 == test.count
        assert "x2" == test.test_method_2(version=2)
        assert 3 == test.count
        xcache.close_version(1)
        xcache.open_version(1)
        assert "x2" == test.test_method_2(version=1)
        assert "x2" == test.test_method_2(version=1)
        assert 4 == test.count

        assert None is test.test_method_3()
        assert 1 == test.c2
        assert "X" == test.test_method_3()
        assert 2 == test.c2
        assert "X" == test.test_method_3()
        assert 2 == test.c2
