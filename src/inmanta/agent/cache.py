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
import pprint
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
    """
    Scope of the lifetime of CacheItem.
    """
    def __init__(self, timeout: float = 24 * 3600, version: int = 0) -> None:
        """
        :param timeout: How long (in seconds) before the associated cache item is considered expired.
        :param version: The version to which this cache item belongs.
        """
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
        :param key: The full key identifying this item in the cache.
        :param scope: Information about the lifetime of the item.
        :param value: The value being cached associated to the key.
        :param call_on_delete: Optional finalizer to call when the cache item is deleted.
        """
        self.key = key
        self.scope: Scope = scope
        self.value = value
        self.call_on_delete = call_on_delete
        self.expiry_time = time.time() + scope.timeout
        self.called_finalizer = False

    def __lt__(self, other: "CacheItem") -> bool:
        return self.expiry_time < other.expiry_time

    def delete(self) -> None:
        if callable(self.call_on_delete) and not self.called_finalizer:
            self.called_finalizer = True
            self.call_on_delete(self.value)

    def __del__(self) -> None:
        self.delete()


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

        # Version-based caching:
        # How long we keep each version after it was last used
        self.version_expiry_time: float = 60
        # Keep track of when each version can be deleted
        self.timer_for_version: dict[int, float] = {}
        # Keep track of which cache keys belong to which version
        self.keys_for_version: dict[int, set[str]] = {}

        # Time-based eviction mechanism
        self.next_action: float = sys.maxsize
        self.timer_queue: list[CacheItem] = []

        self.addLock = Lock()
        self.addLocks: dict[str, Lock] = {}
        self._agent_instance = agent_instance

    def close(self) -> None:
        """
        Cleanly terminate the cache
        """
        self.next_action = sys.maxsize
        for key in list(self.cache.keys()):
            self._evict_item(key)
        self.timer_queue.clear()

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
        while now > self.next_action and len(self.timer_queue) > 0:
            item = heapq.heappop(self.timer_queue)
            self._evict_item(item.key)
            if len(self.timer_queue) > 0:
                self.next_action = self.timer_queue[0].expiry_time
            else:
                self.next_action = sys.maxsize

        expired_versions = [version for version, timer in self.timer_for_version.items() if now > timer]
        for version in expired_versions:
            for key in self.keys_for_version[version]:
                self._evict_item(key)

            del self.timer_for_version[version]
            del self.keys_for_version[version]

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
        self.timer_for_version[version] = time.time() + self.version_expiry_time

    def _cache(self, item: CacheItem) -> None:
        scope = item.scope
        if item.key in self.cache:
            raise Exception("Added same item twice")

        self.cache[item.key] = item

        heapq.heappush(self.timer_queue, item)

        if scope.version != 0:
            try:
                self.keys_for_version[scope.version].add(item.key)
            except KeyError:
                self.keys_for_version[scope.version] = set([item.key])

            self._set_version_expiry(scope.version)

        if item.expiry_time < self.next_action:
            self.next_action = item.expiry_time

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

    def __repr__(self):
        return pprint.saferepr({"CACHE": self.cache, "QUEUE": self.timer_queue})
