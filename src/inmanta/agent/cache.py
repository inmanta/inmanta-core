"""
    Copyright 2017 Inmanta

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
import logging
from threading import Lock


LOGGER = logging.getLogger()


class Scope(object):

    def __init__(self, timeout: int=24 * 3600, version: int=0):
        self.timeout = timeout
        self.version = version


class CacheItem(object):

    def __init__(self, key, scope: Scope, value, call_on_delete):
        self.key = key
        self.scope = scope
        self.value = value
        self.time = time.time() + scope.timeout
        self.call_on_delete = call_on_delete

    def __lt__(self, other):
        return self.time < other.time

    def delete(self):
        if callable(self.call_on_delete):
            self.call_on_delete(self.value)

    def __del__(self):
        self.delete()


class AgentCache(object):
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
        self.addLock = Lock()
        self.addLocks = {}

    def is_open(self, version: int) -> bool:
        """
            Is the given version open in the cache?
        """
        return version in self.counterforVersion

    def open_version(self, version: int):
        """
            Open the cache for the specific version

            :param verion the version id to open the cache for
        """
        if version in self.counterforVersion:
            self.counterforVersion[version] += 1
        else:
            LOGGER.debug("Cache open version %d", version)
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

        LOGGER.debug("Cache close version %d", version)
        for x in self.keysforVersion[version]:
            try:
                item = self.cache[x]
                item.delete()
                del self.cache[x]
            except KeyError:
                # already gone
                pass

        del self.counterforVersion[version]
        del self.keysforVersion[version]

    def _advance_time(self):
        now = time.time()
        while now > self.nextAction and len(self.timerqueue) > 0:
            item = self.timerqueue.pop(0)
            try:
                del self.cache[item.key]
            except KeyError:
                # already gone
                pass
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

    def cache_value(self, key, value, resource=None, version=0, timeout=5000, call_on_delete=None):
        """
            add a value to the cache with the given key

            if a resource or version is given, these are prepended to the key and expiry is adapted accordingly

            :param timeout: nr of second before this value is expired
            :param call_on_delete: A callback function that is called when the value is removed from the cache.
        """
        key = [key]
        if resource is not None:
            key.append(str(resource.id.resource_str()))
        if version != 0:
            key.append(str(version))
        key = '__'.join(key)
        self._cache(CacheItem(key, Scope(timeout, version), value, call_on_delete))

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

    def get_or_else(self, key, function, for_version=True, timeout=5000, ignore=set(),
                    cache_none=True, call_on_delete=None, **kwargs):
        """
            Attempt to find a value in the cache.

            If it is not found, the function is called with kwargs as arguments, to produce the value.
            The value is cached.

            all kwargs are prepended to the key

            if a kwarg named version is found and forVersion is true, the value is cached only for that particular version


            :param forVersion: whether to use the version attribute to attach this value to the resource

        """
        acceptable = set(["resource"])
        if for_version:
            acceptable.add("version")
        args = {k: v for k, v in kwargs.items() if k in acceptable and k not in ignore}
        others = sorted([k for k in kwargs.keys() if k not in acceptable and k not in ignore])
        for k in others:
            key = "%s,%s" % (k, repr(kwargs[k])) + key
        try:
            return self.find(key, **args)
        except KeyError:
            with self.addLock:
                if key in self.addLocks:
                    lock = self.addLocks[key]
                else:
                    lock = Lock()
                    self.addLocks[key] = lock
            with lock:
                try:
                    value = self.find(key, **args)
                except KeyError:
                    value = function(**kwargs)
                    if cache_none or value is not None:
                        self.cache_value(key, value, timeout=timeout, call_on_delete=call_on_delete, **args)
            with self.addLock:
                del self.addLocks[key]
            return value

    def report(self):
        return "\n".join([str(k) + " " + str(v) for k, v in self.counterforVersion.items()])
