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

import bisect
import contextlib
import logging
import sys
import time
from threading import Lock
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set

from inmanta.resources import Resource
from inmanta.stable_api import stable_api

if TYPE_CHECKING:
    from inmanta.agent.agent import AgentInstance

LOGGER = logging.getLogger()


class Scope(object):
    def __init__(self, timeout: int = 24 * 3600, version: int = 0) -> None:
        self.timeout = timeout
        self.version = version


class CacheItem(object):
    def __init__(self, key: str, scope: Scope, value: Any, call_on_delete: Optional[Callable[[Any], None]]) -> None:
        self.key = key
        self.scope = scope
        self.value = value
        self.time: float = time.time() + scope.timeout
        self.call_on_delete = call_on_delete

    def __lt__(self, other: "CacheItem") -> bool:
        return self.time < other.time

    def delete(self) -> None:
        if callable(self.call_on_delete):
            self.call_on_delete(self.value)

    def __del__(self) -> None:
        self.delete()


class CacheVersionContext(contextlib.AbstractContextManager):
    """
    A context manager to ensure the cache version is properly closed
    """

    def __init__(self, cache: "AgentCache", version: int) -> None:
        self.version = version
        self.cache = cache

    def __enter__(self):
        self.cache.open_version(self.version)
        return self.cache

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cache.close_version(self.version)
        return None


@stable_api
class AgentCache(object):
    """
    Caching system for the agent:

    cache items can expire based on:
    1. time
    2. version

    versions are opened and closed
    when a version is closed as many times as it was opened, all cache items linked to this version are dropped
    """

    def __init__(self, agent_instance: Optional["AgentInstance"] = None) -> None:
        """
        :param agent_instance: The AgentInstance that is using the cache. The value is None when the cache
                               is used from pytest-inmanta.
        """
        self.cache: Dict[str, Any] = {}
        self.counterforVersion: Dict[int, int] = {}
        self.keysforVersion: Dict[int, Set[str]] = {}
        self.timerqueue: List[CacheItem] = []
        self.nextAction: float = sys.maxsize
        self.addLock = Lock()
        self.addLocks: Dict[str, Lock] = {}
        self._agent_instance = agent_instance

    def close(self) -> None:
        """
        Cleanly terminate the cache
        """
        for version in list(self.counterforVersion.keys()):
            while self.is_open(version):
                self.close_version(version)
        self.nextAction = sys.maxsize
        self.timerqueue.clear()
        for key in list(self.cache.keys()):
            self._evict_item(key)

    def is_open(self, version: int) -> bool:
        """
        Is the given version open in the cache?
        """
        return version in self.counterforVersion

    def manager(self, version: int) -> CacheVersionContext:
        return CacheVersionContext(self, version)

    def open_version(self, version: int) -> None:
        """
        Open the cache for the specific version

        :param version: the version id to open the cache for
        """
        if version in self.counterforVersion:
            self.counterforVersion[version] += 1
        else:
            LOGGER.debug("Cache open version %d", version)
            self.counterforVersion[version] = 1
            self.keysforVersion[version] = set()

    def close_version(self, version: int) -> None:
        """
        Close the cache for the specific version

        when a version is closed as many times as it was opened, all cache items linked to this version are dropped

        :param version: the version id to close the cache for
        """
        if version not in self.counterforVersion:
            if self._agent_instance and self._agent_instance.is_stopped():
                # When a AgentInstance is stopped, all cache entries are cleared and all ResourceActions are cancelled.
                # However, all ResourceActions that are in-flight keep executing. As such, close_version() might get called
                # on an already closed cache.
                return
            else:
                raise Exception("Closed version that does not exist")

        self.counterforVersion[version] -= 1

        if self.counterforVersion[version] != 0:
            return

        LOGGER.debug("Cache close version %d", version)
        for x in self.keysforVersion[version]:
            self._evict_item(x)

        del self.counterforVersion[version]
        del self.keysforVersion[version]

    def _evict_item(self, key: str) -> None:
        try:
            item = self.cache[key]
            item.delete()
            del self.cache[key]
        except KeyError:
            # already gone
            pass

    def _advance_time(self) -> None:
        now = time.time()
        while now > self.nextAction and len(self.timerqueue) > 0:
            item = self.timerqueue.pop(0)
            self._evict_item(item.key)
            if len(self.timerqueue) > 0:
                self.nextAction = self.timerqueue[0].time
            else:
                self.nextAction = sys.maxsize

    def _get(self, key: str) -> Any:
        self._advance_time()
        return self.cache[key]

    def _cache(self, item: CacheItem) -> None:
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

    def _get_key(self, key: str, resource: Optional[Resource], version: int) -> str:
        key_parts = [key]
        if resource is not None:
            key_parts.append(str(resource.id.resource_str()))
        if version != 0:
            key_parts.append(str(version))
        return "__".join(key_parts)

    def cache_value(
        self,
        key: str,
        value: Any,
        resource: Optional[Resource] = None,
        version: int = 0,
        timeout: int = 5000,
        call_on_delete: Optional[Callable[[Any], None]] = None,
    ) -> None:
        """
        add a value to the cache with the given key

        if a resource or version is given, these are prepended to the key and expiry is adapted accordingly

        :param timeout: nr of second before this value is expired
        :param call_on_delete: A callback function that is called when the value is removed from the cache.
        """
        self._cache(CacheItem(self._get_key(key, resource, version), Scope(timeout, version), value, call_on_delete))

    def find(self, key: str, resource: Optional[Resource] = None, version: int = 0) -> Any:
        """
        find a value in the cache with the given key

        if a resource or version is given, these are prepended to the key

        :raise KeyError: if the value is not found
        """
        return self._get(self._get_key(key, resource, version)).value

    def get_or_else(
        self,
        key: str,
        function: Callable[..., Any],
        for_version: bool = True,
        timeout: int = 5000,
        ignore: Set[str] = set(),
        cache_none: bool = True,
        call_on_delete: Optional[Callable[[Any], None]] = None,
        **kwargs,
    ) -> object:
        """
        Attempt to find a value in the cache.

        If it is not found, the function is called with kwargs as arguments, to produce the value.
        The value is cached.

        all kwargs are prepended to the key

        if a kwarg named version is found and forVersion is true, the value is cached only for that particular version


        :param forVersion: whether to use the version attribute to attach this value to the resource

        """
        acceptable = {"resource"}
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

    def report(self) -> str:
        return "\n".join([str(k) + " " + str(v) for k, v in self.counterforVersion.items()])
