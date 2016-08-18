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

import time
import sys
import bisect


class Scope(object):

    def __init__(self, timeout: int=24 * 3600, version: int=0):
        self.timeout = timeout
        self.version = version


class CacheItem(object):

    def __init__(self, key, scope: Scope, value):
        self.key = key
        self.scope = scope
        self.value = value
        self.time = time.time() + scope.timeout

    def __lt__(self, other):
        return self.time < other.time


class AgentCache():
    """
        Caching system for the agent:

        cache items can expire based on:
        1. time
        2. version

        versions are opened and closed
        when a version is closed as many times as it was opened, all cache items linked to this version are dropped
    """

    def __init__(self):
        self.cache = {}
        self.counterforVersion = {}
        self.keysforVersion = {}
        self.timerqueue = []
        self.nextAction = sys.maxsize

    def open_version(self, version: int):
        """
            Open the cache for the specific version

            :param verion the version id to open the cache for
        """
        if version in self.counterforVersion:
            self.counterforVersion[version] += 1
        else:
            self.counterforVersion[version] = 1
            self.keysforVersion[version] = set()

    def close_version(self, version: int):
        """
            Close the cache for the specific version

            when a version is closed as many times as it was opened, all cache items linked to this version are dropped

            :param verion the version id to close the cache for
        """
        if version not in self.counterforVersion:
            raise Exception("Closed version that does not exist")

        self.counterforVersion[version] -= 1

        if self.counterforVersion[version] != 0:
            return

        for x in self.keysforVersion[version]:
            del self.cache[x]
        del self.counterforVersion[version]
        del self.keysforVersion[version]

    def _advance_time(self):
        now = time.time()
        while now > self.nextAction and len(self.timerqueue) > 0:
            item = self.timerqueue.pop(0)
            del self.cache[item.key]
            if len(self.timerqueue) > 0:
                self.nextAction = self.timerqueue[0].time
            else:
                self.nextAction = sys.maxsize

    def _get(self, key):
        self._advance_time()
        return self.cache[key]

    def _cache(self, item: CacheItem):
        scope = item.scope

        if item.key in self.cache:
            raise Exception("Added same item twice")

        self.cache[item.key] = item

        if scope.version != 0:
            try:
                self.keysforVersion[scope.version].add(item.key)
            except KeyError:
                raise Exception("Added data to version that is not open")

        bisect.insort_right(self.timerqueue, item)
        if item.time < self.nextAction:
            self.nextAction = item.time
        self._advance_time()

    def cache_value(self, key, value, resource=None, version=0, timeout=5000):
        """
            add a value to the cache with the given key

            if a resource or version is given, these are prepended to the key and expiry is adapted accordingly

            @param timeoute: nr of second before this value is expired
        """
        key = [key]
        if resource is not None:
            key.append(str(resource.id.resource_str()))
        if version != 0:
            key.append(str(version))
        key = '__'.join(key)
        self._cache(CacheItem(key, Scope(timeout, version), value))

    def find(self, key, resource=None, version=0):
        """
            find a value in the cache with the given key

            if a resource or version is given, these are prepended to the key

            :raise KeyError: if the value is not found
        """
        key = [key]
        if resource is not None:
            key.append(resource.id.resource_str())
        if version != 0:
            key.append(str(version))
        key = '__'.join(key)
        return self._get(key).value

    def get_or_else(self, key, function, forVerion=True, timeout=5000, ignore=set(), **kwargs):
        """
            Attempt to find a value in the cache.

            If it is not found, the function is called with kwargs as arguments, to produce the value.
            The value is cached.

            all kwargs are prepended to the key

            if a kwarg named version is found and forVersion is true, the value is cached only for that particular version


            :param forVersion: wheter to use the version attribute to attach this value to the resource

        """
        acceptable = set(["resource"])
        if forVerion:
            acceptable.add("version")
        args = {k: v for k, v in kwargs.items() if k in acceptable and k not in ignore}
        others = sorted([k for k in kwargs.keys() if k not in acceptable and k not in ignore])
        for k in others:
            key = "%s,%s" % (k, repr(kwargs[k])) + key
        try:
            return self.find(key, **args)
        except KeyError:
            value = function(**kwargs)
            self.cache_value(key, value, timeout=timeout, **args)
            return value
