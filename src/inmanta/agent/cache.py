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
from types import TracebackType
from typing import TYPE_CHECKING, Any, Callable, Optional, Type

from inmanta.resources import Resource
from inmanta.stable_api import stable_api

if TYPE_CHECKING:
    from inmanta.agent.executor import AgentInstance

LOGGER = logging.getLogger(__name__)


class Scope:
    """
    Scope of the lifetime of CacheItem.
    """

    def __init__(self, timeout: float = 24 * 3600) -> None:
        """
        :param timeout: How long (in seconds) before the associated cache item is considered expired.
        :param version: The version to which this cache item belongs.
        """
        self.timeout = timeout


class CacheItem:
    def __init__(
        self,
        key: str,
        timeout: float,
        value: Any,
        call_on_delete: Optional[Callable[[Any], None]],
        lingering: bool = True,
    ) -> None:
        """
        :param key: The full key identifying this item in the cache.
        :param timeout: Hard timeout for non-lingering cache item.
        :param value: The value being cached associated to the key.
        :param call_on_delete: Optional finalizer to call when the cache item is deleted. This is
            a callable expecting the cached value as an argument.
        :param lingering: When True, this cache item will linger in the cache for 60s after its last use.
            When False, this cache item will be evicted from the cache <timeout> seconds after
            entering the cache.
        """
        self.key = key
        self.value = value
        self.call_on_delete = call_on_delete
        self.lingering = lingering

        now = time.time()
        self.expiry_time = (now + 60) if lingering else (now + timeout)

        # Make sure finalizers are only called once
        self.finalizer_lock = Lock()
        self.called_finalizer = False

    def __lt__(self, other: "CacheItem") -> bool:
        return self.expiry_time < other.expiry_time

    def delete(self) -> None:
        with self.finalizer_lock:
            if callable(self.call_on_delete) and not self.called_finalizer:
                self.called_finalizer = True
                self.call_on_delete(self.value)

    def __del__(self) -> None:
        self.delete()


@stable_api
class AgentCache:
    """
    Caching system for the agent.

    Cached items are of two types:

    1. Lingering items

        These items are expected to be reused across multiple
        model versions. Their expiry time is reset to 60s any
        time they're accessed.

    2. Non-lingering items

        These items have a fixed lifetime. Their expiry time
        is set by the timeout parameter of the @cache decorator.

    To enforce consistency, this cache should be used as a context manager
    by the agent when performing a resource action (deploy / repair / fact retrieval / dry run).

    This ensures that:
        - before using the cache: we clean up stale entries.
        - when done using the cache: we reset the expiry time of lingering items
    """

    def __init__(self, agent_instance: Optional["AgentInstance"] = None) -> None:
        """
        :param agent_instance: The AgentInstance that is using the cache. The value is None when the cache
                               is used from pytest-inmanta.
        """
        # The cache itself
        self.cache: dict[str, CacheItem] = {}

        # Lingering items will remain in the cache for this
        # many seconds after they were last used.
        self.item_lingering_time: float = 60

        # Time-based eviction mechanism
        # Keep track of when is the next earliest cache item expiry time.
        self.next_action: float = sys.maxsize
        # Heap queue of cache items, used for efficient retrieval of the cache
        # item that expires the soonest. should only be mutated via the heapq API.
        self.timer_queue: list[CacheItem] = []

        self.addLock = Lock()
        self.addLocks: dict[str, Lock] = {}
        self._agent_instance = agent_instance

        # Set of lingering cache items used during a resource action.
        self.lingering_set: set[CacheItem] = set()

    def touch_used_cache_items(self) -> None:
        """
        Extend the expiry time of items in the lingering_set by 60s
        """
        now = time.time()
        for item in self.lingering_set:
            item.expiry_time = now + 60

        self.lingering_set = set()
        if self.timer_queue:
            # Bad O(N) but unavoidable (?) Since we modify elements above
            # we have to make sure the heap is still a heap.
            heapq.heapify(self.timer_queue)
            self.next_action = self.timer_queue[0].expiry_time

    def close(self) -> None:
        """
        Cleanly terminate the cache
        """
        self.next_action = sys.maxsize
        for key in list(self.cache.keys()):
            self._evict_item(key)
        self.timer_queue.clear()

    def _evict_item(self, key: str) -> None:
        """
        Evict an item from the cache by key.
        """
        try:
            item = self.cache[key]
            item.delete()
            del self.cache[key]
        except KeyError:
            # already gone
            pass

    def clean_stale_entries(self) -> None:
        """
        Remove stale entries from the cache.
        """
        now = time.time()
        while now > self.next_action and len(self.timer_queue) > 0:
            item = heapq.heappop(self.timer_queue)
            self._evict_item(item.key)
            if len(self.timer_queue) > 0:
                self.next_action = self.timer_queue[0].expiry_time
            else:
                self.next_action = sys.maxsize

    def _get(self, key: str) -> CacheItem:
        """
        Retrieve cache item with the given key

        :param key: Key of the item being retrieved from the cache
        :return: The cached item

        :raises KeyError: If the key is not present in the cache
        """
        item = self.cache[key]

        if item.lingering:
            self.lingering_set.add(item)

        return item

    def _cache(self, item: CacheItem) -> None:
        if item.key in self.cache:
            raise Exception("Added same item twice")

        self.cache[item.key] = item

        heapq.heappush(self.timer_queue, item)

        if item.lingering:
            self.lingering_set.add(item)

        if item.expiry_time < self.next_action:
            self.next_action = item.expiry_time

    def _get_key(self, key: str, resource: Optional[Resource]) -> str:
        key_parts = [key]
        if resource is not None:
            key_parts.append(str(resource.id.resource_str()))
        return "__".join(key_parts)

    def cache_value(
        self,
        key: str,
        value: Any,
        resource: Optional[Resource] = None,
        timeout: int = 5000,
        call_on_delete: Optional[Callable[[Any], None]] = None,
        for_version: bool = True,
    ) -> None:
        """
        add a value to the cache with the given key

        if a resource is given, it is appended to the key

        :param timeout: nr of second before this value is expired
        :param call_on_delete: A callback function that is called when the value is removed from the cache.
        """
        self._cache(
            CacheItem(
                self._get_key(key, resource),
                timeout,
                value,
                call_on_delete,
                lingering=for_version,
            )
        )

    def find(self, key: str, resource: Optional[Resource] = None) -> Any:
        """
        find a value in the cache with the given key

        if a resource is given, it is appended to the key

        :raise KeyError: if the value is not found
        """
        item = self._get(self._get_key(key, resource)).value

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

        :param timeout: Use in combination with for_version=False to set a "hard" expiry timeout (in seconds).
          The cached entry will be evicted from the cache after this period of time.
          Ignored when for_version=True.
        :param for_version: This parameter controls when the cached value is considered expired.
            - for_version=False: the cached value is not tied to any model version. It is
              considered stale after <timeout> seconds have elapsed since it entered the cache.
            - for_version=True: the cached value is expected to be reused across multiple versions.
              It is considered stale if no agent used this entry in the last 60s.

        """
        acceptable = {"resource"}
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
                        self.cache_value(
                            key, value, timeout=timeout, call_on_delete=call_on_delete, for_version=for_version, **args
                        )
            with self.addLock:
                del self.addLocks[key]
            return value

    def __enter__(self) -> None:
        """
        Assumed to be called under activity_lock.
        Clean stale entries before using the cache.
        """
        self.clean_stale_entries()

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """
        When done using the cache, update expiry time
        of all lingering items.
        """
        self.touch_used_cache_items()
