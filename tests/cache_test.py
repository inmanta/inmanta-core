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

from nose.tools import assert_equal
from nose.tools.nontrivial import raises
from inmanta.agent.handler import cache
from inmanta.agent.cache import AgentCache
from inmanta.resources import resource, Resource, Id


@resource("test::Resource", agent="agent", id_attribute="key")
class Resource(Resource):
    """
        A file on a filesystem
    """
    fields = ("key", "value", "purged", "state_id", "allow_snapshot", "allow_restore")


class CacheTests(unittest.TestCase):

    def testBase(self):
        cache = AgentCache()
        value = "test too"
        cache.cache_value("test", value)
        assert_equal(value, cache.find("test"))

    def testTimout(self):
        cache = AgentCache()
        value = "test too"
        cache.cache_value("test", value, timeout=0.1)
        cache.cache_value("test2", value)

        assert_equal(value, cache.find("test"))
        sleep(1)
        try:
            assert_equal(value, cache.find("test"))
            raise AssertionError("Should get exception")
        except KeyError:
            pass
        assert_equal(value, cache.find("test2"))

    @raises(KeyError)
    def testBaseFail(self):
        cache = AgentCache()
        value = "test too"
        assert_equal(value, cache.find("test"))

    def testResource(self):
        cache = AgentCache()
        value = "test too"
        resource = Id("test::Resource", "test", "key", "test", 100).get_instance()
        cache.cache_value("test", value, resource=resource)
        assert_equal(value, cache.find("test", resource=resource))

    @raises(KeyError)
    def testResourceFail(self):
        cache = AgentCache()
        value = "test too"
        resource = Id("test::Resource", "test", "key", "test", 100).get_instance()
        cache.cache_value("test", value, resource=resource)
        assert_equal(value, cache.find("test"))

    @raises(Exception)
    def testVersionClosed(self):
        cache = AgentCache()
        value = "test too"
        version = 200
        cache.cache_value("test", value, version=version)
        assert_equal(value, cache.find("test", version=version))

    def testVersion(self):
        cache = AgentCache()
        value = "test too"
        version = 200
        cache.open_version(version)
        cache.cache_value("test", value, version=version)
        assert_equal(value, cache.find("test", version=version))

    def testVersionClose(self):
        cache = AgentCache()
        value = "test too"
        version = 200
        cache.open_version(version)
        cache.cache_value("test", value, version=version)
        cache.cache_value("test0", value, version=version)
        cache.cache_value("test4", value, version=version)
        resource = Id("test::Resource", "test", "key", "test", 100).get_instance()
        cache.cache_value("testx", value, resource=resource)
        assert_equal(value, cache.find("test", version=version))
        assert_equal(value, cache.find("testx", resource=resource))
        cache.close_version(version)
        assert_equal(value, cache.find("testx", resource=resource))
        try:
            assert_equal(value, cache.find("test", version=version))
            raise AssertionError("Should get exception")
        except KeyError:
            pass

    @raises(KeyError)
    def testVersionFail(self):
        cache = AgentCache()
        value = "test too"
        version = 200
        cache.open_version(version)
        cache.cache_value("test", value, version=version)
        assert_equal(value, cache.find("test"))

    def testResourceAndVersion(self):
        cache = AgentCache()
        value = "test too"
        resource = Id("test::Resource", "test", "key", "test", 100).get_instance()
        version = 200
        cache.open_version(version)
        cache.cache_value("test", value, resource=resource, version=version)
        assert_equal(value, cache.find("test", resource=resource, version=version))

    def testGetOrElse(self):
        called = []

        def creator(param, resource, version):

            called.append("x")
            return param

        cache = AgentCache()
        value = "test too"
        value2 = "test too x"
        resource = Id("test::Resource", "test", "key", "test", 100).get_instance()
        resourcev2 = Id("test::Resource", "test", "key", "test", 200).get_instance()
        assert_equal(200, resourcev2.id.version)
        version = 200
        cache.open_version(version)
        assert_equal(value, cache.get_or_else("test", creator, resource=resource, version=version, param=value))
        assert_equal(value, cache.get_or_else("test", creator, resource=resource, version=version, param=value))
        assert_equal(len(called), 1)
        assert_equal(value, cache.get_or_else("test", creator, resource=resourcev2, version=version, param=value))
        assert_equal(len(called), 1)
        assert_equal(value2, cache.get_or_else("test", creator, resource=resource, version=version, param=value2))

    def testDecorator(self):

        xcache = AgentCache()

        class DT(object):

            def __init__(self, cache):
                self.cache = cache
                self.count = 0

            @cache
            def testMethod(self):
                self.count += 1
                return "x"

            @cache
            def testMethod2(self, version):
                self.count += 1
                return "x2"

        test = DT(xcache)
        assert_equal("x", test.testMethod())
        assert_equal("x", test.testMethod())
        assert_equal("x", test.testMethod())
        assert_equal(1, test.count)

        xcache.open_version(1)
        xcache.open_version(2)
        assert_equal("x2", test.testMethod2(version=1))
        assert_equal("x2", test.testMethod2(version=1))
        assert_equal(2, test.count)
        assert_equal("x2", test.testMethod2(version=2))
        assert_equal(3, test.count)
        xcache.close_version(1)
        xcache.open_version(1)
        assert_equal("x2", test.testMethod2(version=1))
        assert_equal("x2", test.testMethod2(version=1))
        assert_equal(4, test.count)
