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
import enum
import logging
import time
from collections.abc import Collection
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from inmanta import util
from inmanta.agent import config as agent_config
from inmanta.deploy.state import BlockedStatus, ComplianceStatus, ResourceState
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

        Should not be called if the timer is already active.

        :param when: Schedule the next deploy for this resource at this datetime.
        :param reason: The reason argument that will be given for the deploy request.
        :param priority: The priority argument that will be given for the deploy request.
        """
        if self.next_scheduled_time == when:
            # already good
            return

        # Ensure old one is stopped
        self.cancel()

        # Override all values
        self.next_scheduled_time = when
        self.reason = reason
        self.priority = priority

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

    def initialize(self) -> None:
        """
        Set the periodic timers for repairs and deploys. Either per-resource if the
        associated config option is passed as a positive integer, or globally if it
        is passed as a cron expression string.

        Should only be called once when initializing the resource scheduler.
        After each call to reset(), this method can be called again once.
        """
        deploy_timer: int | str = agent_config.agent_deploy_interval.get()
        repair_timer: int | str = agent_config.agent_repair_interval.get()

        if isinstance(deploy_timer, str):
            self.global_periodic_deploy_task = self._trigger_global_deploy(deploy_timer)
        else:
            self.periodic_deploy_interval = deploy_timer if deploy_timer > 0 else None

        if isinstance(repair_timer, str):
            self.global_periodic_repair_task = self._trigger_global_repair(repair_timer)
        else:
            self.periodic_repair_interval = repair_timer if repair_timer > 0 else None

    def _trigger_global_deploy(self, cron_expression: str) -> util.ScheduledTask:
        """
        Trigger a global deploy following a cron expression schedule.
        This does not affect previously started cron schedules.

        :returns: the associated scheduled task.
        """

        cron_schedule = util.CronSchedule(cron=cron_expression)

        async def _action() -> None:
            await self._resource_scheduler.deploy(
                reason=f"Global deploy triggered because of cron expression for deploy interval: '{cron_expression}'",
                priority=TaskPriority.INTERVAL_DEPLOY,
            )

        task = self._cron_scheduler.add_action(_action, cron_schedule)
        assert isinstance(task, util.ScheduledTask)
        return task

    def _trigger_global_repair(self, cron_expression: str) -> util.ScheduledTask:
        """
        Trigger a global repair following a cron expression schedule.
        This does not affect previously started cron schedules.

        :returns: the associated scheduled task.
        """
        cron_schedule = util.CronSchedule(cron=cron_expression)

        async def _action() -> None:
            await self._resource_scheduler.repair(
                reason=f"Global repair triggered because of cron expression for repair interval: '{cron_expression}'",
                priority=TaskPriority.INTERVAL_REPAIR,
            )

        task = self._cron_scheduler.add_action(_action, cron_schedule)
        assert isinstance(task, util.ScheduledTask)
        return task

    def update_timer(self, resource: ResourceIdStr, *, state: ResourceState) -> None:
        """
        Make sure the given resource is marked for eventual re-deployment in the future.

        This method will inspect self.periodic_repair_interval and self.periodic_deploy_interval
        to decide when re-deployment will happen and whether this timer is global (i.e. pertains
        to all resources) or specific to this resource.

        :param resource: the resource to re-deploy.
        :param state: The state of the resource. To have a consistent view, either under lock or a copy

        it is expected that the resource has a last_deployed time already set, otherwise it will be ignored
        """

        # Create if it is not known yet
        if resource not in self.resource_timers:
            self.resource_timers[resource] = ResourceTimer(resource, self._resource_scheduler)

        repair_only = False  # consider only repair or also deploy?

        match state.blocked:
            case BlockedStatus.YES:
                self.resource_timers[resource].cancel()
                return
            case BlockedStatus.NO:
                repair_only = state.status == ComplianceStatus.COMPLIANT
            case BlockedStatus.TRANSIENT:
                repair_only = True

        # Both periodic repairs and deploys are disabled on a per-resource basis.
        if self.periodic_repair_interval is None and self.periodic_deploy_interval is None:
            return

        last_deployed = state.last_deployed
        if last_deployed is None:
            # Should not happen
            return

        def _setup_repair(repair_interval: int) -> None:
            self.resource_timers[resource].set_timer(
                when=(last_deployed + timedelta(seconds=repair_interval)),
                reason=(
                    f"Individual repair triggered for resource {resource} because last "
                    f"repair happened more than {repair_interval}s ago."
                ),
                priority=(TaskPriority.INTERVAL_REPAIR),
            )

        def _setup_deploy(deploy_interval: int) -> None:
            self.resource_timers[resource].set_timer(
                when=(last_deployed + timedelta(seconds=deploy_interval)),
                reason=(
                    f"Individual deploy triggered for resource {resource} because last "
                    f"deploy happened more than {deploy_interval}s ago."
                ),
                priority=(TaskPriority.INTERVAL_DEPLOY),
            )

        if repair_only:
            # At the time of the call, the resource is in an assumed good state:
            # schedule a periodic repair for it if the repair setting is set on a per-resource basis
            if self.periodic_repair_interval:
                _setup_repair(self.periodic_repair_interval)

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
        Cancel and remove timers for resources that have been completely dropped from the model.
        """
        self.stop_timers(resources)
        for resource in resources:
            with contextlib.suppress(KeyError):
                del self.resource_timers[resource]
