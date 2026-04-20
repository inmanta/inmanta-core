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

import asyncio
import contextlib
import logging
import time
import typing
from collections.abc import Collection
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from inmanta import data, util
from inmanta.deploy.state import Blocked, Compliance, ResourceState
from inmanta.deploy.work import TaskPriority
from inmanta.types import ResourceIdStr

if TYPE_CHECKING:
    from inmanta.deploy.scheduler import ResourceScheduler

LOGGER = logging.getLogger(__name__)


class ResourceTimer:
    """
    This class represents a single timer for a single resource.
    This class is not meant to be used directly. It is solely intended
    to be instantiated and manipulated by a TimerManager instance sitting on
    top of it. To create and delete resource timers, the TimerManager interface
    should be used.
    """

    def __init__(self, resource: ResourceIdStr, scheduler: "ResourceScheduler"):
        """
        Instances of this class are expected to be created by a TimerManager.

        :param resource: The resource for which to ensure periodic repairs.
        :param scheduler: Back reference to the resource scheduler sitting on top of this class.
        """
        self.resource: ResourceIdStr = resource

        # "Inner" asyncio task responsible for queuing a Deploy task
        self.trigger_deploy: asyncio.Task[None] | None = None
        # "Outer" handle to the soon-to-be-called trigger_deploy
        self.next_schedule_handle: asyncio.TimerHandle | None = None
        self.next_scheduled_time: datetime | None = None
        self.reason: str | None = None
        self.priority: TaskPriority | None = None

        self._resource_scheduler = scheduler

    def _activate(self) -> None:
        assert self.reason is not None
        assert self.priority is not None
        self.trigger_deploy = asyncio.create_task(
            self._resource_scheduler.deploy_resource(self.resource, self.reason, self.priority)
        )

    def set_timer(
        self,
        when: datetime,
        reason: str,
        priority: TaskPriority,
    ) -> None:
        """
        Main interface expected to be called by the TimerManager instance sitting on
        top of this class.

        Schedule the underlying resource for execution in <countdown> seconds with
        the given reason and priority.

        :param when: Schedule the next deploy for this resource at this datetime.
            If the given time is in the past, the deploy is scheduled immediately (on the IO loop).
        :param reason: The reason argument that will be given for the deploy request.
        :param priority: The priority argument that will be given for the deploy request.
        """
        self.reason = reason
        self.priority = priority

        if self.next_scheduled_time == when:
            # already good
            return

        # Ensure old one is stopped
        self.cancel()

        # Override all values
        self.next_scheduled_time = when

        # convert time to ioloop mono time
        time_delta = asyncio.get_running_loop().time() - time.time()
        self.next_schedule_handle = asyncio.get_running_loop().call_at(when.timestamp() + time_delta, self._activate)

    def cancel(self) -> None:
        """
        Cancel the callback that schedules the next repair task
        """
        if self.next_schedule_handle is not None:
            self.next_schedule_handle.cancel()
        self.next_schedule_handle = None
        self.next_scheduled_time = None

    async def join(self) -> None:
        """
        Wait for the deploy trigger task to finish
        """
        if self.trigger_deploy is not None:
            await self.trigger_deploy


class TimerManager:
    def __init__(self, resource_scheduler: "ResourceScheduler"):
        """
        :param resource_scheduler: Back reference to the ResourceScheduler that was responsible for
            spawning this TimerManager.

        if the repair interval is shorter than the deploy interval, we will not correctly bump the priority!

        """
        self.resource_timers: dict[ResourceIdStr, ResourceTimer] = {}

        self.global_periodic_repair_task: util.ScheduledTask | None = None
        self.global_periodic_deploy_task: util.ScheduledTask | None = None

        self.periodic_repair_interval: int | None = None
        self.periodic_deploy_interval: int | None = None

        self._resource_scheduler = resource_scheduler

        self._cron_scheduler = util.Scheduler("Resource scheduler")

    async def reset(self) -> None:
        await self.stop()

        self._cron_scheduler = util.Scheduler("Resource scheduler")
        self.global_periodic_repair_task = None
        self.global_periodic_deploy_task = None
        self.periodic_repair_interval = None
        self.periodic_deploy_interval = None

    async def stop(self) -> None:
        for timer in self.resource_timers.values():
            timer.cancel()

        await self._cron_scheduler.stop()

    async def join(self) -> None:
        await asyncio.gather(*[timer.join() for timer in self.resource_timers.values()])

    async def initialize(self) -> None:
        """
        Set the periodic timers for repairs and deploys. Either per-resource if the
        associated config option is passed as a positive integer, or globally if it
        is passed as a cron expression string.
        """
        await self.reload_config()

    async def reload_config(self) -> None:

        async with data.Environment.get_connection() as connection:
            assert self._resource_scheduler.environment is not None
            environment = await data.Environment.get_by_id(self._resource_scheduler.environment, connection=connection)
            assert environment is not None
            deploy_timer = await environment.get(data.AUTOSTART_AGENT_DEPLOY_INTERVAL, connection=connection)
            assert isinstance(deploy_timer, str)  # make mypy happy
            repair_timer = await environment.get(data.AUTOSTART_AGENT_REPAIR_INTERVAL, connection=connection)
            assert isinstance(repair_timer, str)  # make mypy happy

        new_deploy_cron: str | None
        new_periodic_deploy_interval: int | None
        new_repair_cron: str | None
        new_periodic_repair_interval: int | None

        try:
            deploy_timer = int(deploy_timer)
            new_deploy_cron = None
            new_periodic_deploy_interval = deploy_timer if deploy_timer > 0 else None
        except ValueError:
            assert isinstance(deploy_timer, str)  # make mypy happy
            new_deploy_cron = deploy_timer
            new_periodic_deploy_interval = None

        try:
            repair_timer = int(repair_timer)
            new_repair_cron = None
            new_periodic_repair_interval = repair_timer if repair_timer > 0 else None
        except ValueError:
            assert isinstance(repair_timer, str)  # make mypy happy
            new_repair_cron = repair_timer
            new_periodic_repair_interval = None

        if not new_periodic_repair_interval and not new_periodic_deploy_interval:
            self.periodic_repair_interval = new_periodic_repair_interval
            self.periodic_deploy_interval = new_periodic_deploy_interval
            # shutdown all finegrained timers
            for timer in self.resource_timers.values():
                timer.cancel()

        # update globals
        self._update_global_repair(new_repair_cron)
        self._update_global_deploy(new_deploy_cron)

        # restart timers if needed
        if (
            new_periodic_repair_interval != self.periodic_repair_interval
            or new_periodic_deploy_interval != self.periodic_deploy_interval
        ):
            self.periodic_repair_interval = new_periodic_repair_interval
            self.periodic_deploy_interval = new_periodic_deploy_interval
            await self._resource_scheduler.reload_all_timers()

    def _update_global_timer(
        self, cron_expression: str | None, previous_value: util.ScheduledTask | None, action: util.TaskMethod
    ) -> util.ScheduledTask | None:
        """
        Configure the global deploy according to the given expression
        None for disabled

        :returns: the associated scheduled task.
        """
        if cron_expression is None:
            # disable
            if previous_value is not None:
                self._cron_scheduler.remove(previous_value)
            return None

        # enable
        cron_schedule = util.CronSchedule(cron=cron_expression)

        if previous_value is not None:
            # Already exists
            if previous_value.schedule == cron_schedule:
                # All good!
                return previous_value
            else:
                # Not good, remove
                self._cron_scheduler.remove(previous_value)

        return self._cron_scheduler.add_action(action, cron_schedule)

    def _update_global_deploy(self, cron_expression: str | None) -> None:
        """
        Configure the global deploy according to the given expression
        None for disabled

        """

        async def _action() -> None:
            await self._resource_scheduler.deploy(
                reason="a global deploy was triggered by a cron expression",
                priority=TaskPriority.INTERVAL_DEPLOY,
            )

        self.global_periodic_deploy_task = self._update_global_timer(
            cron_expression,
            previous_value=self.global_periodic_deploy_task,
            action=_action,
        )

    def _update_global_repair(self, cron_expression: str | None) -> None:
        """
        Configure the global repair according to the given expression
        None for disabled

        """

        async def _action() -> None:
            await self._resource_scheduler.repair(
                reason="a global repair was triggered by a cron expression",
                priority=TaskPriority.INTERVAL_REPAIR,
            )

        self.global_periodic_repair_task = self._update_global_timer(
            cron_expression,
            previous_value=self.global_periodic_repair_task,
            action=_action,
        )

    def update_timer(self, resource: ResourceIdStr, *, state: ResourceState) -> None:
        """
        Make sure the given resource is marked for eventual re-deployment in the future

        It will correctly handle all cases (for adding, moving or removing the timer), but should not be called when
        - the resource is already queued (it is OK to add it again, but it will do nothing)
        - the resource has no last_deployed time set (which implies the first condition), in which case we ignore it

        This method will inspect the resource state, self.periodic_repair_interval and self.periodic_deploy_interval
        to decide when re-deployment will happen and whether this timer is global (i.e. pertains
        to all resources) or specific to this resource.

        :param resource: the resource to re-deploy.
        :param state: The state of the resource. To have a consistent view, either under lock or a copy
        """

        # Create if it is not known yet
        if resource not in self.resource_timers:
            self.resource_timers[resource] = self._make_resource_timer(resource)

        repair_only: bool  # consider only repair or also deploy?

        match state.blocked:
            case Blocked.BLOCKED:
                self.resource_timers[resource].cancel()
                return
            case Blocked.NOT_BLOCKED:
                repair_only = state.compliance == Compliance.COMPLIANT
            case Blocked.TEMPORARILY_BLOCKED:
                repair_only = True
            case _ as _never:
                typing.assert_never(_never)

        # Both periodic repairs and deploys are disabled on a per-resource basis.
        if self.periodic_repair_interval is None and self.periodic_deploy_interval is None:
            self.resource_timers[resource].cancel()
            return

        last_deployed = state.last_deployed
        if last_deployed is None:
            # Should not happen
            return

        def _setup_repair(repair_interval: int) -> None:
            self.resource_timers[resource].set_timer(
                when=(last_deployed + timedelta(seconds=repair_interval)),
                reason=f"previous repair happened more than {repair_interval}s ago",
                priority=(TaskPriority.INTERVAL_REPAIR),
            )

        def _setup_deploy(deploy_interval: int) -> None:
            self.resource_timers[resource].set_timer(
                when=(last_deployed + timedelta(seconds=deploy_interval)),
                reason=f"previous deploy happened more than {deploy_interval}s ago",
                priority=(TaskPriority.INTERVAL_DEPLOY),
            )

        if repair_only:
            # At the time of the call, the resource is in an assumed good state:
            # schedule a periodic repair for it if the repair setting is set on a per-resource basis
            if self.periodic_repair_interval:
                _setup_repair(self.periodic_repair_interval)
            else:
                self.resource_timers[resource].cancel()

        else:
            # At the time of the call, the resource is in an assumed bad state:
            # schedule a repair or a deploy, whichever has the shortest interval set
            # on a per-resource basis.

            if self.periodic_repair_interval and self.periodic_deploy_interval:
                if self.periodic_repair_interval < self.periodic_deploy_interval:
                    _setup_repair(self.periodic_repair_interval)
                else:
                    _setup_deploy(self.periodic_deploy_interval)
            elif self.periodic_repair_interval:
                _setup_repair(self.periodic_repair_interval)
            else:
                assert self.periodic_deploy_interval is not None  # mypy
                _setup_deploy(self.periodic_deploy_interval)

    def _make_resource_timer(self, resource: ResourceIdStr) -> ResourceTimer:
        """Factory method for testing"""
        return ResourceTimer(resource, self._resource_scheduler)

    def update_timers(self, resources: Collection[ResourceIdStr]) -> None:
        """
        Make sure the given resources are marked for eventual re-deployment in the future.

        Must be called under scheduler lock
        Should not be called with resources that are already scheduled
         -> this implies that every resource is expected to have a last_deployed time already,
            otherwise it would be in the queue
        """
        for resource in resources:
            self.update_timer(resource, state=self._resource_scheduler._state.resource_state[resource])

    def stop_timer(self, resource: ResourceIdStr) -> None:
        """
        Cancel the associated timer (if any) for re-deployment for the given resource.
        """
        if resource in self.resource_timers:
            self.resource_timers[resource].cancel()

    def stop_timers(self, resources: Collection[ResourceIdStr]) -> None:
        """
        Stop a batch of resource timers.
        """
        for resource in resources:
            self.stop_timer(resource)

    def remove_timers(self, resources: Collection[ResourceIdStr]) -> None:
        """
        Cancel and remove timers (if they exist) for resources that have been completely dropped from the model.
        """
        self.stop_timers(resources)
        for resource in resources:
            with contextlib.suppress(KeyError):
                del self.resource_timers[resource]
