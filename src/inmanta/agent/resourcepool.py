"""
    Copyright 2024 Inmanta

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

    This file contains the caching mechanism for the forking executor

    The complexity is that:
    1. we need to cache processes on blueprint id
    2. we need to cache executors (running on processes) on executor id
    3. invalidate both caches if a process dies
    4. invalidate executors based on idle time
    5. invalidate executors based on nr per agent
    6. closed processes if they are no longer in use
    7. never invalidate executors that have work in flight

    The solution is a combination of pool manager/pool members that can:
    1. can perform invalidation according to various stategies
    2. has fairly accurate membership tracking (for requirements 4  and 5) through events/listeners \
        (cache responds correctly to crashes)
    3. members can be contained in multiple cache

    To make this work, we propagate the 'closed' event, that indicates when a pool member has terminated.
    We use it for cache eviction and failure propagation.

    The `closing` status is tracked on each member and checked when taking an item out of the cache.
    As such, the cache can contain closing items. These are replaced when being checked out.
    We don't propagate this as an event, as they will eventually get a closed event.

    The intended usage is that:
    1. A single Pool Manager manages a pool of processes (no eviction policy)
    2. each process is a pool manager for a set of executors (evict self when pool is empty, on receival of closed event)
    3. an overarching pool manager also caches executors on top of the other two (i.e. it never creates new things),
        it evicts based on time and executors per agent
"""

import abc
import asyncio
import datetime
import logging
from typing import Any, Awaitable, Callable, Coroutine, Generic, Optional, Self, Sequence, TypeVar

import inmanta.util
from inmanta.const import LOG_LEVEL_TRACE

LOGGER = logging.getLogger(__name__)

TPoolID = TypeVar("TPoolID")


class PoolMember(abc.ABC, Generic[TPoolID]):

    def __init__(self, my_id: TPoolID):
        self.id = my_id

        # Time based expiry
        self.last_used: datetime.datetime = datetime.datetime.now().astimezone()

        # state tracking
        self.is_stopping = False
        self.is_stopped = False

        # event propagation
        self.termination_listeners: list[Callable[[PoolMember[TPoolID]], Coroutine[Any, Any, Any]]] = []

    @property
    def running(self) -> bool:
        return not self.is_stopping and not self.is_stopped

    def touch(self) -> None:
        """Update time last used"""
        self.last_used = datetime.datetime.now().astimezone()

    def can_be_cleaned_up(self) -> bool:
        """
        Return true if this member is not inhibited from cleanup
        """
        return True

    def get_idle_time(self) -> datetime.timedelta:
        """
        Retrieve the idle time of this pool member
        """
        return datetime.datetime.now().astimezone() - self.last_used

    def get_id(self) -> TPoolID:
        """
        Returns the ID of the pool member that will be used to lock the pool member. This ensures that no operations will
        overlap while this pool member is being created, modified, or cleaned.
        """
        return self.id

    async def close(self) -> None:
        """
        Close the pool member.

        This should eventually cause a call to closed
        """
        self.is_stopping = True

    async def closed(self) -> None:
        """
        This pool member is now closed
        """
        self.is_stopped = True
        self.is_stopping = True
        for listener in self.termination_listeners:
            await listener(self)


TPoolMember = TypeVar("TPoolMember", bound=PoolMember)


class PoolManager(abc.ABC, Generic[TPoolID, TPoolMember]):
    """
    A pool of slow objects

    We pool by key, however, when a pool member is shutting down, we allow it to be replaced in the pool
    As such, the pool id does not necessarily identify the correct object

    """

    def __init__(self) -> None:
        self.is_stopped = False
        self.is_stopping = False

        self._locks: inmanta.util.NamedLock = inmanta.util.NamedLock()
        self.pool: dict[TPoolID, TPoolMember] = {}

        self.closing_children: set[TPoolMember] = set()

    @property
    def running(self) -> bool:
        return not self.is_stopping and not self.is_stopped

    async def start(self) -> None:
        """
        Start the cleaning job of the Pool Manager
        """
        pass

    async def stop(self) -> None:
        """
        Stop the cleaning job of the Pool Manager.
        """
        # We don't want to cancel the task because it could lead to an inconsistent state (e.g. Venv half removed). Therefore,
        # we need to wait for the completion of the task
        self.is_stopped = True
        self.is_stopping = True

    async def join(self) -> None:
        """
        Wait for the cleaning job to terminate.
        """
        pass

    def my_name(self) -> str:
        """Method to improve logging output by naming this executor"""
        return "PoolManager"

    def member_name(self, member: TPoolMember) -> str:
        return "PoolMember"

    async def request_close(self, pool_member: TPoolMember) -> None:
        """
        Additional cleanup operation(s) that need to be performed by the Manager regarding the pool member being cleaned.

        This method assumes to be in a lock to prevent other operations to overlap with the cleanup.
        """
        if pool_member.is_stopped:
            return
        self.closing_children.add(pool_member)
        await pool_member.close()

    async def child_closed(self, pool_member: TPoolMember) -> bool:
        """
        a child has notified us that it is completely closed

        We take no lock, as we are either
        - in a crash situation and lock would not help
        - have gone through closing state so we are properly handled

        :return: if we effectively removed it from the pool
        """
        self.closing_children.discard(pool_member)

        theid = pool_member.get_id()
        registered_for_id = self.pool.get(theid)
        if registered_for_id is None:
            # already dropped from cache
            return False
        elif registered_for_id != pool_member:
            # We have a stale instance that refused to close before
            # it was replaced and has now gone down
            return False
        else:
            self.pool.pop(theid)
            return True

    def get_lock_name_for(self, member_id: TPoolID) -> str:
        return str(member_id)

    async def get(self, member_id: TPoolID) -> TPoolMember:
        """
        Returns a new pool member
        """
        # Acquire a lock based on the executor's pool id
        async with self._locks.get(self.get_lock_name_for(member_id)):
            if member_id in self.pool:
                it = self.pool[member_id]
                if not it.is_stopping:
                    LOGGER.debug("Found existing %s for %s with id %s", self.my_name(), self.member_name(it), member_id)
                    it.touch()
                    return it
                else:
                    self.pre_replace(it)
            return await self._create_or_replace(member_id)

    async def _create_or_replace(self, member_id: TPoolID) -> TPoolMember:
        """
        MUST BE CALLED UNDER LOCK!
        """
        await self.pre_create_capacity_check(member_id)

        my_executor = await self.create_member(member_id)
        self.pool[member_id] = my_executor
        my_executor.termination_listeners.append(self.child_closed)

        return my_executor

    async def pre_replace(self, member: PoolMember) -> None:
        """Hook method to join items being replaced, called under lock"""
        pass

    async def pre_create_capacity_check(self, member_id: TPoolID) -> None:
        """
        Check if any members should be closed for the given id

        Will be called onder lock, is expected to call request_close
        """
        pass

    @abc.abstractmethod
    async def create_member(self, executor_id: TPoolID) -> TPoolMember:
        pass


class TimeBasedPoolManager(PoolManager[TPoolID, TPoolMember]):

    def __init__(self, retention_time: int) -> None:
        super().__init__()

        # We keep a reference to the periodic cleanup task to prevent it
        # from disappearing mid-execution https://docs.python.org/3.11/library/asyncio-task.html#creating-tasks
        self.cleanup_job: Optional[asyncio.Task[None]] = None
        self.retention_time: int = retention_time

    async def start(self) -> None:
        """
        Start the cleaning job of the Pool Manager
        """
        await super().start()
        self.cleanup_job = asyncio.create_task(self.cleanup_inactive_pool_members_task())

    async def join(self) -> None:
        """
        Wait for the cleaning job to terminate.
        """
        if self.cleanup_job is not None:
            await self.cleanup_job
        await super().join()

    async def cleanup_inactive_pool_members_task(self) -> None:
        """
        This task periodically cleans up idle pool member

        We split up `cleanup_inactive_pool_members` and `cleanup_inactive_pool_members_task` in order to be able to call the
        cleanup method in the test without being blocked in a loop.
        """
        while self.running:
            sleep_interval = await self.cleanup_inactive_pool_members()
            if self.running:
                LOGGER.log(LOG_LEVEL_TRACE, f"Manager will clean in %.2f seconds", sleep_interval)
                await asyncio.sleep(sleep_interval)

    async def cleanup_inactive_pool_members(self) -> float:
        """
        Cleans up idle pool member

        :return: When to run the cleaning next time: default retention time or lowest expiration time of one of the pool members
        """
        cleanup_start = datetime.datetime.now().astimezone()
        # Clean up anything older than this
        expiry = datetime.timedelta(seconds=self.retention_time)
        oldest_time = cleanup_start - expiry
        # Number of seconds relative to cleanup_start
        run_next_cleanup_job_in: float = float(self.retention_time)
        pool_members = list(self.pool.values())
        for pool_member in pool_members:
            try:
                if pool_member.can_be_cleaned_up() and pool_member.last_used < oldest_time and pool_member.running:
                    async with self._locks.get(self.get_lock_name_for(pool_member.get_id())):
                        # Check that the executor can still be cleaned up by the time we have acquired the lock
                        if pool_member.can_be_cleaned_up() and pool_member.last_used < oldest_time and pool_member.running:
                            LOGGER.debug(
                                f"Pool member %s with %.2f >= %d is about to expire",
                                pool_member.get_id(),
                                (cleanup_start - pool_member.last_used).total_seconds(),
                                self.retention_time,
                            )
                            await self.request_close(pool_member)
                else:
                    # If this pool member expires sooner than the cleanup interval, schedule the next cleanup on that
                    # timestamp.
                    run_next_cleanup_job_in = min(
                        run_next_cleanup_job_in,
                        (pool_member.last_used - oldest_time).total_seconds(),
                    )
            except Exception:
                LOGGER.exception(
                    "An error occurred while cleaning the pool member `%s`",
                    pool_member.get_id(),
                )

        cleanup_end = datetime.datetime.now().astimezone()

        return max(0.0, run_next_cleanup_job_in - (cleanup_end - cleanup_start).total_seconds())
