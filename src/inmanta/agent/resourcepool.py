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
"""
import abc
import datetime
import logging

import inmanta.util
import asyncio

from typing import Optional, Sequence, TypeVar, Generic, Callable, Coroutine

LOGGER = logging.getLogger(__name__)

TPoolID = TypeVar("TPoolID")


class PoolMember(abc.ABC, Generic[TPoolID]):

    def __init__(self, my_id: TPoolID):
        self.id = my_id
        self.last_used: datetime.datetime = datetime.datetime.now().astimezone()
        self.is_stopping = False
        self.is_stopped = False
        self.termination_listeners: list[Callable[[Type[self]], Awaitable[None]]] = []

    def touch(self):
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

        # We keep a reference to the periodic cleanup task to prevent it
        # from disappearing mid-execution https://docs.python.org/3.11/library/asyncio-task.html#creating-tasks
        # self.cleanup_job: Optional[asyncio.Task[None]] = None

        # self.retention_time: int = retention_time
        #
        self.closing_childern: set[TPoolMember] = set()

    async def start(self) -> None:
        """
        Start the cleaning job of the Pool Manager
        """
        pass
        # self.cleanup_job = asyncio.create_task(self.cleanup_inactive_pool_members_task())

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
        # if self.cleanup_job is not None:
        #     await self.cleanup_job
        pass

    async def request_close(self, pool_member: TPoolMember) -> None:
        """
        Additional cleanup operation(s) that need to be performed by the Manager regarding the pool member being cleaned.

        This method assumes to be in a lock to prevent other operations to overlap with the cleanup.
        """
        if pool_member.is_stopped:
            return
        self.closing_childern.add(pool_member)
        await pool_member.close()

    async def child_closed(self, pool_member: TPoolMember) -> bool:
        """
        a child has notified us that it is completely closed

        We take no lock, as we are either
        - in a crash situation and lock would not help
        - have gone through closing state so we are properly handled

        :return: if we effectively removed it from the pool
        """
        self.closing_childern.discard(pool_member)

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

    async def get(
        self,
        member_id: TPoolID
    ) -> TPoolMember:
        """
        Returns a new pool member
        """
        # Acquire a lock based on the executor's pool id
        async with self._locks.get(member_id):
            if member_id in self.pool:
                it = self.pool[member_id]
                if not it.is_stopping:
                    # TODO logging
#                    LOGGER.debug("Found existing executor for agent %s with id %s", agent_name, executor_id.identity())
                    it.touch()
                    return it
                # TODO: do we need the ability to join?
                # else:
                #     LOGGER.debug(
                #         "Found stale executor for agent %s with id %s, waiting for close", agent_name, executor_id.identity()
                #     )
                #     await it.join(inmanta.const.EXECUTOR_GRACE_HARD)
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

    async def pre_create_capacity_check(self, member_id: TPoolID) -> None:
        """
        Check if any members should be closed for the given id

        Will be called onder lock, is expected to call request_close
        """
        pass


    @abc.abstractmethod
    async def create_member(self, executor_id: TPoolID) -> TPoolMember:
        pass

    # async def cleanup_inactive_pool_members(self) -> float:
    #     """
    #     Cleans up idle pool member
    #
    #     :return: When to run the cleaning next time: default retention time or lowest expiration time of one of the pool members
    #     """
    #     cleanup_start = datetime.datetime.now().astimezone()
    #     # Number of seconds relative to cleanup_start
    #     run_next_cleanup_job_at: float = float(self.retention_time)
    #     pool_members = await self.get_pool_members()
    #     for pool_member in pool_members:
    #         LOGGER.debug(f"Will clean pool member {pool_member.get_id()}")
    #         try:
    #             if pool_member.can_be_cleaned_up(self.retention_time):
    #                 async with self._locks.get(pool_member.get_id()):
    #                     LOGGER.debug(f"Have the lock for pool member {pool_member.get_id()}")
    #                     # Check that the executor can still be cleaned up by the time we have acquired the lock
    #                     if pool_member.can_be_cleaned_up(self.retention_time):
    #                         await pool_member.clean()
    #                         LOGGER.debug(f"pool member {pool_member.get_id()} has been cleaned")
    #                         self.clean_pool_member_from_manager(pool_member)
    #             else:
    #                 # If this pool member expires sooner than the cleanup interval, schedule the next cleanup on that
    #                 # timestamp.
    #                 run_next_cleanup_job_at = min(
    #                     run_next_cleanup_job_at,
    #                     (
    #                         datetime.timedelta(seconds=self.retention_time) - (cleanup_start - pool_member.last_used())
    #                     ).total_seconds(),
    #                 )
    #         except Exception:
    #             LOGGER.exception(
    #                 "An error occurred while cleaning the %s pool member `%s`",
    #                 self.__class__.__name__,
    #                 pool_member.get_id(),
    #             )
    #
    #     cleanup_end = datetime.datetime.now().astimezone()
    #
    #     return max(0.0, run_next_cleanup_job_at - (cleanup_end - cleanup_start).total_seconds())
    #
    # async def cleanup_inactive_pool_members_task(self) -> None:
    #     """
    #     This task periodically cleans up idle pool member
    #
    #     We split up `cleanup_inactive_pool_members` and `cleanup_inactive_pool_members_task` in order to be able to call the
    #     cleanup method in the test without being blocked in a loop.
    #     """
    #     while self.running:
    #         sleep_interval = await self.cleanup_inactive_pool_members()
    #         if self.running:
    #             LOGGER.debug(f"Manager will clean for {sleep_interval} seconds")
    #             await asyncio.sleep(sleep_interval)
