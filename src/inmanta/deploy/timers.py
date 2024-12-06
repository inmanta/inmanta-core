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
import logging
from collections.abc import Collection
from typing import TYPE_CHECKING

from inmanta import util
from inmanta.agent import config as agent_config
from inmanta.data.model import ResourceIdStr
from inmanta.deploy.work import TaskPriority

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

        self._resource_scheduler = scheduler

    def set_timer(
        self,
        countdown: int,
        reason: str,
        priority: TaskPriority,
    ) -> None:
        """
        Main interface expected to be called by the TimerManager instance sitting on
        top of this class.

        Schedule the underlying resource for execution in <countdown> seconds with
        the given reason and priority.

        Should not be called if the timer is already active.

        :param countdown: In this many seconds in the future, this method will ensure the underlying
            resource is scheduled for deploy.
        :param reason: The reason argument that will be given for the deploy request.
        :param priority: The priority argument that will be given for the deploy request.
        """

        def _create_repair_task() -> None:
            self.trigger_deploy = asyncio.create_task(
                self._resource_scheduler.deploy_resource(self.resource, reason, priority)
            )

        if self.next_schedule_handle is not None:
            raise Exception(f"Per-resource timer set twice for resource {self.resource}, this should not happen")

        self.next_schedule_handle = asyncio.get_running_loop().call_later(countdown, _create_repair_task)

    def cancel(self) -> None:
        """
        Cancel the callback that schedules the next repair task
        """
        if self.next_schedule_handle is not None:
            self.next_schedule_handle.cancel()
        self.next_schedule_handle = None

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
        """
        self.resource_timers: dict[ResourceIdStr, ResourceTimer] = {}

        self.global_periodic_repair_task: util.ScheduledTask | None = None
        self.global_periodic_deploy_task: util.ScheduledTask | None = None

        self.periodic_repair_interval: int | None = None
        self.periodic_deploy_interval: int | None = None

        self._resource_scheduler = resource_scheduler

        self._cron_scheduler = util.Scheduler("Resource scheduler")

    def reset(self) -> None:
        self.stop()

        self.global_periodic_repair_task = None
        self.global_periodic_deploy_task = None
        self.periodic_repair_interval = None
        self.periodic_deploy_interval = None

    def stop(self) -> None:
        for timer in self.resource_timers.values():
            timer.cancel()

        self._cron_scheduler.stop()

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

    def update_timer(self, resource: ResourceIdStr, *, is_compliant: bool) -> None:
        """
        Make sure the given resource is marked for eventual re-deployment in the future.

        This method will inspect self.periodic_repair_interval and self.periodic_deploy_interval
        to decide when re-deployment will happen and whether this timer is global (i.e. pertains
        to all resources) or specific to this resource.

        The is_compliant parameter lets the caller (i.e. the resource scheduler sitting on top
        of this TimerManager) give information regarding the last known state of the resource
        so that this method can decide whether a repair or a deploy should be scheduled.

        The scheduler is considered the authority. If a previous timer is already in place
        for the given resource, (which should not happen) it will be canceled first and a
        new one will be re-scheduled.

        :param resource: the resource to re-deploy.
        :param is_compliant: If the resource is in an assumed bad state, we should re-deploy it
            at the soonest i.e. whichever interval is the smallest between per-resource deploy
            and per-resource repair. If it is in an assumed good state, mark the resource for
            repair (using the per-resource repair interval).
        """

        # Create if it is not known yet
        if resource not in self.resource_timers:
            self.resource_timers[resource] = ResourceTimer(resource, self._resource_scheduler)

        def _setup_repair(repair_interval: int) -> tuple[int, str, TaskPriority]:
            countdown = repair_interval
            reason = (
                f"Individual repair triggered for resource {resource} because last "
                f"repair happened more than {countdown}s ago."
            )
            priority = TaskPriority.INTERVAL_REPAIR

            return (countdown, reason, priority)

        def _setup_deploy(deploy_interval: int) -> tuple[int, str, TaskPriority]:
            countdown = deploy_interval
            reason = (
                f"Individual deploy triggered for resource {resource} because last "
                f"deploy happened more than {countdown}s ago."
            )
            priority = TaskPriority.INTERVAL_DEPLOY

            return (countdown, reason, priority)

        # Both periodic repairs and deploys are disabled on a per-resource basis.
        if self.periodic_repair_interval is None and self.periodic_deploy_interval is None:
            return

        if is_compliant:
            # At the time of the call, the resource is in an assumed good state:
            # schedule a periodic repair for it if the repair setting is set on a per-resource basis
            if self.periodic_repair_interval:
                countdown, reason, priority = _setup_repair(self.periodic_repair_interval)
            else:
                return

        else:
            # At the time of the call, the resource is in an assumed bad state:
            # schedule a repair or a deploy, whichever has the shortest interval set
            # on a per-resource basis.

            if self.periodic_repair_interval and self.periodic_deploy_interval:
                if self.periodic_repair_interval < self.periodic_deploy_interval:
                    countdown, reason, priority = _setup_repair(self.periodic_repair_interval)
                else:
                    countdown, reason, priority = _setup_deploy(self.periodic_deploy_interval)
            elif self.periodic_repair_interval:
                countdown, reason, priority = _setup_repair(self.periodic_repair_interval)
            else:
                assert self.periodic_deploy_interval is not None  # mypy
                countdown, reason, priority = _setup_deploy(self.periodic_deploy_interval)

        self.resource_timers[resource].cancel()
        self.resource_timers[resource].set_timer(
            countdown=countdown,
            reason=reason,
            priority=priority,
        )

    def update_timers(self, resources: Collection[ResourceIdStr], *, are_compliant: bool) -> None:
        """
        Make sure the given resources are marked for eventual re-deployment in the future.
        """
        for resource in resources:
            self.update_timer(resource, is_compliant)

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
            del self.resource_timers[resource]
