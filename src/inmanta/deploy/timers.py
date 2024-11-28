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
import sys
from collections.abc import Coroutine
from typing import Any, Callable

import inmanta.deploy.scheduler
from inmanta.agent import config as agent_config
from inmanta.data.model import ResourceIdStr
from inmanta.deploy.state import BlockedStatus
from inmanta.deploy.work import TaskPriority
from inmanta.util import CronSchedule, ScheduledTask, Scheduler

LOGGER = logging.getLogger(__name__)


class ResourceTimer:
    def __init__(self, resource: ResourceIdStr, scheduler: "inmanta.deploy.scheduler.ResourceScheduler"):
        """
        :param resource: The resource for which to ensure periodic repairs.
        """
        self.resource: ResourceIdStr = resource
        self.time_to_next_deploy = sys.maxsize

        # "Inner" asyncio task responsible for queuing a Deploy task
        self.trigger_deploy: asyncio.Task[None] | None = None
        # "Outer" handle to the soon-to-be-called trigger_deploy
        self.next_schedule_handle: asyncio.TimerHandle | None = None

        self._resource_scheduler = scheduler

    def ensure_timer(
        self,
        periodic_deploy_interval: int | None,
        periodic_repair_interval: int | None,
        is_dirty: bool,
    ) -> None:
        """
        Make sure the underlying resource is marked for execution

        :param periodic_deploy_interval: Per-resource deploy interval, assumed to be a positive int or None
        :param periodic_repair_interval: Per-resource repair interval, assumed to be a positive int or None
        :param is_dirty: Last known state of the resource at the timer install request time.
        """

        next_execute_time: int

        if periodic_repair_interval is None:
            periodic_repair_interval = sys.maxsize
        if periodic_deploy_interval is None:
            periodic_deploy_interval = sys.maxsize

        action_function: Callable[[ResourceIdStr, int], Coroutine[Any, Any, None]]
        if is_dirty:
            next_execute_time, action_function = min(
                (periodic_deploy_interval, self._trigger_deploy_for_resource),
                (periodic_repair_interval, self._trigger_repair_for_resource),
                key=lambda x: x[0],
            )
        else:
            next_execute_time = periodic_repair_interval
            action_function = self._trigger_repair_for_resource

        if next_execute_time == sys.maxsize:
            # Per-resource timers are disabled
            return

        if next_execute_time == self.time_to_next_deploy:
            # This timer is already in place
            return

        # Cancel previous schedule and re-schedule
        self.cancel_next_schedule()

        def _create_repair_task() -> None:
            self.trigger_deploy = asyncio.create_task(action_function(self.resource, next_execute_time))

        self.time_to_next_deploy = next_execute_time
        self.next_schedule_handle = asyncio.get_running_loop().call_later(next_execute_time, _create_repair_task)

    def cancel_next_schedule(self) -> None:
        """
        Cancel the callback that schedules the next repair task
        """
        if self.next_schedule_handle is not None:
            self.next_schedule_handle.cancel()

    async def join(self) -> None:
        """
        Wait for the deploy trigger task to finish
        """
        if self.trigger_deploy is not None:
            await self.trigger_deploy

    async def _trigger_repair_for_resource(self, resource: ResourceIdStr, timer: int) -> None:
        async with self._resource_scheduler._scheduler_lock:

            if self._resource_scheduler._state.resource_state[resource].blocked is BlockedStatus.YES:  # Can't deploy
                return
            to_deploy: set[ResourceIdStr] = {resource}

            self._resource_scheduler._work.deploy_with_context(
                to_deploy,
                reason=f"Individual repair triggered for resource {resource} because last "
                f"repair happened more than {timer}s ago.",
                priority=TaskPriority.INTERVAL_REPAIR,
                deploying=self._resource_scheduler._deploying_latest,
            )

    async def _trigger_deploy_for_resource(self, resource: ResourceIdStr, timer: int) -> None:
        async with self._resource_scheduler._scheduler_lock:

            if self._resource_scheduler._state.resource_state[resource].blocked is BlockedStatus.YES:  # Can't deploy
                return
            to_deploy: set[ResourceIdStr] = {resource}

            self._resource_scheduler._work.deploy_with_context(
                to_deploy,
                reason=f"Individual deploy triggered for resource {resource} because last "
                f"deploy happened more than {timer}s ago.",
                priority=TaskPriority.INTERVAL_DEPLOY,
                deploying=self._resource_scheduler._deploying_latest,
            )


class TimerManager:
    def __init__(self, resource_scheduler: "inmanta.deploy.scheduler.ResourceScheduler"):
        """
        :param resource_scheduler: Back reference to the ResourceScheduler that was responsible for
            spawning this TimerManager.
        """
        self.resource_timers: dict[ResourceIdStr, ResourceTimer] = {}

        self.global_periodic_repair_task: ScheduledTask | None = None
        self.global_periodic_deploy_task: ScheduledTask | None = None

        self.periodic_repair_interval: int | None = None
        self.periodic_deploy_interval: int | None = None

        self._resource_scheduler = resource_scheduler

        self._sched = Scheduler("Resource scheduler")

    def reset(self) -> None:
        self.stop()

        self.global_periodic_repair_task = None
        self.global_periodic_deploy_task = None
        self.periodic_repair_interval = None
        self.periodic_deploy_interval = None

    def stop(self) -> None:
        for timer in self.resource_timers.values():
            timer.cancel_next_schedule()

        for task in [self.global_periodic_repair_task, self.global_periodic_deploy_task]:
            if task:
                self._sched.remove(task)

    async def join(self) -> None:
        await asyncio.gather(*[timer.join() for timer in self.resource_timers.values()])

    def initialize(self) -> None:
        """
        Set the periodic timers for repairs and deploys. Either per-resource if the
        associated config option is passed as a positive integer, or globally if it
        is passed as a cron expression string.
        """
        deploy_timer: int | str = agent_config.agent_deploy_interval.get()
        repair_timer: int | str = agent_config.agent_repair_interval.get()

        if isinstance(deploy_timer, str):
            self.global_periodic_deploy_task = self.trigger_global_deploy(deploy_timer)
        else:
            self.periodic_deploy_interval = deploy_timer if deploy_timer > 0 else None

        if isinstance(repair_timer, str):
            self.global_periodic_repair_task = self.trigger_global_repair(repair_timer)
        else:
            self.periodic_repair_interval = repair_timer if repair_timer > 0 else None

    def trigger_global_deploy(self, cron_expression: str) -> ScheduledTask:
        """
        Trigger a global deploy following a cron expression schedule.

        :returns: the associated scheduled task.
        """

        cron_schedule = CronSchedule(cron=cron_expression)

        async def _action() -> None:
            await self._resource_scheduler.deploy(
                reason=f"Global deploy triggered because of set cron {cron_expression}",
                priority=TaskPriority.INTERVAL_DEPLOY,
            )

        task = self._sched.add_action(_action, cron_schedule)
        assert isinstance(task, ScheduledTask)
        return task

    def trigger_global_repair(self, cron_expression: str) -> ScheduledTask:
        """
        Trigger a global repair following a cron expression schedule.

        :returns: the associated scheduled task.
        """
        cron_schedule = CronSchedule(cron=cron_expression)

        async def _action() -> None:
            await self._resource_scheduler.repair(
                reason=f"Global repair triggered because of set cron {cron_expression}",
                priority=TaskPriority.INTERVAL_REPAIR,
            )

        task = self._sched.add_action(_action, cron_schedule)
        assert isinstance(task, ScheduledTask)
        return task

    def update_resource(self, resource: ResourceIdStr, dirty: bool) -> None:
        # Create if it is not known yet
        if resource not in self.resource_timers:
            self.resource_timers[resource] = ResourceTimer(resource, self._resource_scheduler)

        # Check if timer needs updating
        self.resource_timers[resource].ensure_timer(
            periodic_deploy_interval=self.periodic_deploy_interval,
            periodic_repair_interval=self.periodic_repair_interval,
            is_dirty=dirty,
        )

    def remove_resource(self, resource: ResourceIdStr) -> None:
        if resource in self.resource_timers:
            self.resource_timers[resource].cancel_next_schedule()
            del self.resource_timers[resource]

    def __repr__(self) -> str:
        return str(self.resource_timers)
