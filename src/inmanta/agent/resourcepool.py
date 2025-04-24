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
2. has fairly accurate membership tracking (for requirements 4  and 5) through events/listeners
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
from asyncio import CancelledError, Task
from typing import Any, Callable, Coroutine, Generic, Optional, TypeVar

import inmanta.util
from inmanta.const import LOG_LEVEL_TRACE

LOGGER = logging.getLogger(__name__)

TPoolID = TypeVar("TPoolID")
TIntPoolID = TypeVar("TIntPoolID")


class PoolMember(abc.ABC, Generic[TIntPoolID]):
    """
    Item that can live in a pool

    The lifecycle if this item is:
    - running (after construction)
    - shutting down (after call to request_shutdown)
    - shutdown (after call to set_shutdown)

    Implementors of sub-classes are expected to
    - override request_shutdown to start the shutdown of the underlying resource
    - at the end of request_shutdown, call set_shutdown to indicate we are down

    After request_shutdown is called, this member will be considered invalid.
        When checked out of any pool a replacement will be produced.
    When set_shutdown is called, the shutdown event will be sent to all pools containing this member.
        This will cause it to be evicted
    """

    def __init__(self, my_id: TIntPoolID):
        self.id = my_id

        # Time based expiry
        self._last_used: datetime.datetime = datetime.datetime.now().astimezone()

        # state tracking
        self.shutting_down = False
        self.shut_down = False

        # event propagation
        self.termination_listeners: list[Callable[[PoolMember[TPoolID]], Coroutine[Any, Any, Any]]] = []

    @property
    def running(self) -> bool:
        return not self.shutting_down and not self.shut_down

    @property
    def last_used(self) -> datetime.datetime:
        return self._last_used

    def touch(self) -> None:
        """Update time last used"""
        self._last_used = datetime.datetime.now().astimezone()

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

    def get_id(self) -> TIntPoolID:
        """
        Returns the ID of the pool member that will be used to lock the pool member. This ensures that no operations will
        overlap while this pool member is being created, modified, or cleaned.
        """
        return self.id

    async def request_shutdown(self) -> None:
        """
        Close the pool member.

        This should eventually cause a call to closed
        """
        self.shutting_down = True

    async def set_shutdown(self) -> None:
        """
        This pool member is now closed
        """
        self.shut_down = True
        self.shutting_down = True
        for listener in self.termination_listeners:
            await listener(self)


TPoolMember = TypeVar("TPoolMember", bound=PoolMember)


class PoolManager(abc.ABC, Generic[TPoolID, TIntPoolID, TPoolMember]):
    """
    A pool of slow objects

    Items are stored by id.

    We have internal id, that is used internally (storage, cleanup)
    We have pool id, that is used to request new instances
    Most often these are the same

    When a pool member is shutting down, it is considered to be invalid and we allow it to be replaced in the pool
    As such, the pool id does not necessarily uniquely identify an object.

    When the member signals it is down, we drop it from the pool.

    The natural ID  (member.get_id()) of a member is assumed to be the internal id of the member
    """

    def __init__(self) -> None:
        self.shut_down = False
        self.shutting_down = False

        self._locks: inmanta.util.NamedLock = inmanta.util.NamedLock()
        self.pool: dict[TIntPoolID, TPoolMember] = {}

    @property
    def running(self) -> bool:
        return not self.shutting_down and not self.shut_down

    @abc.abstractmethod
    def _id_to_internal(self, ext_id: TPoolID) -> TIntPoolID:
        """Convert an external id to an internal id"""
        pass

    def my_name(self) -> str:
        """Method to improve logging output by naming this executor"""
        return "PoolManager"

    def render_id(self, member: TPoolID) -> str:
        """Method to improve logging output by naming external ids"""
        # This method is not abstract to allow this class to be integrated with minimal effort
        # The default is not very informative, to force implementors to eventually override it
        return "PoolMember"

    def member_name(self, member: TPoolMember) -> str:
        """Method to improve logging output by naming the members, best kept consistent with render_id"""
        return self.render_id(member.get_id())

    def get_lock_name_for(self, member_id: TIntPoolID) -> str:
        """Convert the id into a string to obtain a lock"""
        return str(member_id)

    async def start(self) -> None:
        """
        Start the Pool Manager
        """
        pass

    async def request_shutdown(self) -> None:
        """
        Stop the Pool Manager.

        This implies nothing about the children
        """
        self.shut_down = True
        self.shutting_down = True

    async def join(self) -> None:
        """
        Wait for shutdown to be completed
        """
        pass

    async def notify_member_shutdown(self, pool_member: TPoolMember) -> bool:
        """
        a child has notified us that it is completely closed

        We take no lock, as we are either
        - in a crash situation and lock would not help
        - have gone through closing state so we are properly handled

        :return: if we effectively removed it from the pool
        """
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

    async def get(self, member_id: TPoolID) -> TPoolMember:
        """
        Returns a valid pool member for the given id
        """
        LOGGER.log(LOG_LEVEL_TRACE, "%s: requesting %s", self.my_name(), self.render_id(member_id))
        internal_id = self._id_to_internal(member_id)
        # Acquire a lock based on the executor's pool id
        async with self._locks.get(self.get_lock_name_for(internal_id)):
            it = self.pool.get(internal_id, None)
            if it is not None:
                if not it.shutting_down:
                    LOGGER.debug("%s: found existing %s", self.my_name(), self.render_id(member_id))
                    it.touch()
                    return it
                else:
                    await self.pre_replace(it)
            LOGGER.debug("%s: creating %s", self.my_name(), self.render_id(member_id))
            out = await self._create_or_replace(member_id, internal_id)
            LOGGER.debug("%s: created %s", self.my_name(), self.render_id(member_id))
            return out

    async def _create_or_replace(self, member_id: TPoolID, internal_id: TIntPoolID) -> TPoolMember:
        """
        MUST BE CALLED UNDER LOCK!
        """
        await self.pre_create_capacity_check(member_id)

        my_executor = await self.create_member(member_id)
        assert my_executor.id == internal_id

        self.pool[internal_id] = my_executor
        my_executor.termination_listeners.append(self.notify_member_shutdown)

        return my_executor

    async def pre_replace(self, member: PoolMember) -> None:
        """Hook method to join/handle items being replaced, called under lock"""
        pass

    async def pre_create_capacity_check(self, member_id: TPoolID) -> None:
        """
        Check if any members should be closed for the given id

        Will be called onder lock, is expected to call request_close
        """
        pass

    @abc.abstractmethod
    async def create_member(self, executor_id: TPoolID) -> TPoolMember:
        """Produce a fresh member for the given id"""
        pass


class SingleIdPoolManager(PoolManager[TPoolID, TPoolID, TPoolMember]):
    """Pool where internal and external id are the same"""

    def _id_to_internal(self, ext_id: TPoolID) -> TPoolID:
        return ext_id


class TimeBasedPoolManager(PoolManager[TPoolID, TIntPoolID, TPoolMember]):
    """
    Pool that will discard items after a specific period of not being used.

    Getting a member from the pool is considered use
    """

    def __init__(self, retention_time: int) -> None:
        super().__init__()

        # We keep a reference to the periodic cleanup task to prevent it
        # from disappearing mid-execution https://docs.python.org/3.11/library/asyncio-task.html#creating-tasks
        self.cleanup_job: Optional[asyncio.Task[None]] = None
        self.retention_time: int = retention_time
        # We keep track of the sleep function to be able to cancel it on shutdown
        # Without risking interrupting the cleanup itself
        self.shutdown_sleep: Optional[Task[None]] = None

    async def start(self) -> None:
        """
        Start the cleaning job of the Pool Manager
        """
        await super().start()
        self.cleanup_job = asyncio.create_task(self.cleanup_inactive_pool_members_task())

    async def request_shutdown(self) -> None:
        await super().request_shutdown()
        if self.shutdown_sleep is not None and not self.shutdown_sleep.done():
            self.shutdown_sleep.cancel("Shutting down cleanup task")

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
        try:
            while self.running:
                try:
                    sleep_interval = await self.cleanup_inactive_pool_members()
                except Exception:
                    # This should not happen, as the cleanup_inactive_pool_members should handle all exceptions
                    logging.exception("Unexpected error while cleaning up pool members")
                if self.running:
                    LOGGER.log(LOG_LEVEL_TRACE, "Manager will clean in %.2f seconds", sleep_interval)
                    # Allow wait to be cancelled on shutdown
                    self.shutdown_sleep = asyncio.create_task(asyncio.sleep(sleep_interval))
                    await self.shutdown_sleep
        except CancelledError:
            # We are woken up by shutdown
            pass

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
                                "%s will be shutdown because it was inactive for %.2f, which is more than %d",
                                self.member_name(pool_member),
                                (cleanup_start - pool_member.last_used).total_seconds(),
                                self.retention_time,
                            )
                            await pool_member.request_shutdown()
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

        minimal_waiting_time: float = 0.5  # enforce minimal wait time to prevent bussy polling when can_be_cleaned_up == False
        return max(minimal_waiting_time, run_next_cleanup_job_in - (cleanup_end - cleanup_start).total_seconds())
