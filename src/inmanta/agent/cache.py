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

import heapq
import logging
import sys
import time
from threading import Lock
from typing import TYPE_CHECKING, Any, Callable, Optional

from inmanta.resources import Resource
from inmanta.stable_api import stable_api

if TYPE_CHECKING:
    from inmanta.agent.executor import AgentInstance

LOGGER = logging.getLogger()


class Scope:
    def __init__(self, timeout: float = 24 * 3600, version: int = 0) -> None:
        self.timeout = timeout
        self.version = version


class CacheItem:
    def __init__(
        self,
        key: str,
        scope: Scope,
        value: Any,
        call_on_delete: Optional[Callable[[Any], None]],
    ) -> None:
        """
        TODO docstring
        """
        self.key = key
        self.scope: Scope = scope
        self.value = value
        self.call_on_delete = call_on_delete
        self.expiry_time = time.time() + scope.timeout

    def __lt__(self, other: "CacheItem") -> bool:
        return self.expiry_time < other.expiry_time

    def delete(self) -> None:
        if callable(self.call_on_delete):
            self.call_on_delete(self.value)

    def __del__(self) -> None:
        self.delete()

    def __repr__(self) -> str:
        return f"{self.key=} {self.value=}"


@stable_api
class AgentCache:
    """
    Caching system for the agent:

    cache items are removed from the cache either:
    1. individually when their expiry_time is up
    2. as a group when their version is not being used for a while (default 1 min)

    """

    def __init__(self, agent_instance: Optional["AgentInstance"] = None) -> None:
        """
        :param agent_instance: The AgentInstance that is using the cache. The value is None when the cache
                               is used from pytest-inmanta.
        """
        # The cache itself
        self.cache: dict[str, CacheItem] = {}

        # Version-based caching
        self.timerforVersion: dict[int, float] = {}
        self.keysforVersion: dict[int, set[str]] = {}

        # Time-based eviction mechanism
        self.nextAction: float = sys.maxsize
        self.timerqueue: list[CacheItem] = []

        self.addLock = Lock()
        self.addLocks: dict[str, Lock] = {}
        self._agent_instance = agent_instance

    def close(self) -> None:
        """
        Cleanly terminate the cache
        """
        self.nextAction = sys.maxsize
        for key in list(self.cache.keys()):
            self._evict_item(key)
        self.timerqueue.clear()

    def _evict_item(self, key: str) -> None:
        try:
            item = self.cache[key]
            LOGGER.info(f"ITEM....{item}")
            item.delete()
            del self.cache[key]
        except KeyError:
            # already gone
            pass

    def clean_stale_entries(self) -> None:
        now = time.time()
        while now > self.nextAction and len(self.timerqueue) > 0:
            item = heapq.heappop(self.timerqueue)
            self._evict_item(item.key)
            if len(self.timerqueue) > 0:
                self.nextAction = self.timerqueue[0].expiry_time
            else:
                self.nextAction = sys.maxsize

        for version, timer in self.timerforVersion.items():
            if now > timer:
                for key in self.keysforVersion[version]:
                    self._evict_item(key)

                del self.timerforVersion[version]
                del self.keysforVersion[version]

    def _get(self, key: str) -> CacheItem:
        """
        Retrieve cache item with the given key

        :param key: Key of the item being retrieved from the cache
        :return: The cached item

        :raises KeyError: If the key is not present in the cache
        """
        item = self.cache[key]
        return item

    def _set_version_expiry(self, version: int) -> None:
        """
        Update the expiry time for the given version
        """
        self.timerforVersion[version] = time.time() + 60

    def _cache(self, item: CacheItem) -> None:
        scope = item.scope
        if item.key in self.cache:
            raise Exception("Added same item twice")

        self.cache[item.key] = item

        heapq.heappush(self.timerqueue, item)

        if scope.version != 0:
            try:
                self.keysforVersion[scope.version].add(item.key)
            except KeyError:
                self.keysforVersion[scope.version] = set(item.key)

            self._set_version_expiry(scope.version)

        if item.expiry_time < self.nextAction:
            self.nextAction = item.expiry_time

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

        if a resource or version is given, these are appended to the key and expiry is adapted accordingly

        :param timeout: nr of second before this value is expired
        :param version: The model version this cache entry belongs to
        :param call_on_delete: A callback function that is called when the value is removed from the cache.
        """
        self._cache(
            CacheItem(
                self._get_key(key, resource, version),
                Scope(timeout, version),
                value,
                call_on_delete,
            )
        )

    def find(self, key: str, resource: Optional[Resource] = None, version: int = 0) -> Any:
        """
        find a value in the cache with the given key

        if a resource or version is given, these are appended to the key

        :raise KeyError: if the value is not found
        """
        item = self._get(self._get_key(key, resource, version)).value

        if version != 0:
            self._set_version_expiry(version)

        return item

    def get_or_else(
        self,
        key: str,
        function: Callable[..., Any],
        for_version: bool = True,
        timeout: int = 5000,
        ignore: set[str] = set(),
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
            key = f"{k},{repr(kwargs[k])}" + key
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
