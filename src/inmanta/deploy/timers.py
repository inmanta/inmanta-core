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
from collections.abc import Coroutine
from typing import Any, Callable, Optional

import inmanta.deploy.scheduler
from inmanta.agent import config as agent_config
from inmanta.data.model import ResourceIdStr
from inmanta.deploy.work import TaskPriority
from inmanta.util import CronSchedule, ScheduledTask, Scheduler

LOGGER = logging.getLogger(__name__)


class ResourceTimer:
    def __init__(self, resource: ResourceIdStr):
        self.resource: ResourceIdStr = resource
        self.repair_handle: asyncio.TimerHandle | None = None
        self.is_installed: bool = False

    def install_timer(
        self,
        periodic_deploy_interval: int | None,
        periodic_repair_interval: int | None,
        is_dirty: bool,
        action_function: Callable[..., Coroutine[Any, Any, None]],
    ) -> None:
        """
        Make sure the underlying resource is marked for execution

        :param periodic_deploy_interval: Per-resource deploy interval, assumed to be a positive int or None
        :param periodic_repair_interval: Per-resource repair interval, assumed to be a positive int or None
        :param is_dirty: Last known state of the resource at the timer install request time.
        :param action_function: The function to execute
        """
        if self.is_installed:
            return

        next_execute_time: int

        if periodic_repair_interval is not None and periodic_deploy_interval is not None:
            if is_dirty:
                next_execute_time = min(periodic_deploy_interval, periodic_repair_interval)
            else:
                next_execute_time = periodic_repair_interval
        elif periodic_deploy_interval is not None:
            if not is_dirty:
                return
            next_execute_time = periodic_deploy_interval
        elif periodic_repair_interval is not None:
            next_execute_time = periodic_repair_interval
        else:
            return

        self.is_installed = True

        def action() -> None:
            asyncio.ensure_future(action_function(self.resource, next_execute_time))
            self.uninstall_timer()

        self.repair_handle = asyncio.get_running_loop().call_later(next_execute_time, action)

    def uninstall_timer(self) -> None:
        self.is_installed = False

    def cancel(self) -> None:
        if self.repair_handle is not None:
            self.repair_handle.cancel()


class TimerManager:
    def __init__(self, resource_scheduler: Optional["inmanta.deploy.scheduler.ResourceScheduler"] = None):
        self.resource_timers: dict[ResourceIdStr, ResourceTimer] = {}

        self.global_periodic_repair_task: ScheduledTask | None = None
        self.global_periodic_deploy_task: ScheduledTask | None = None

        self.periodic_repair_interval: int | None = None
        self.periodic_deploy_interval: int | None = None

        # Back reference to the ResourceScheduler that was responsible for spawning this TimerManager
        # Used to schedule global repair/deploys. TODO: This feels hackish ??
        if resource_scheduler:
            self._resource_scheduler = resource_scheduler

        self._sched = Scheduler("Resource scheduler")

    def _initialize(self) -> None:
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

    def register_resource(self, resource: ResourceIdStr) -> None:
        self.resource_timers[resource] = ResourceTimer(resource)

    def unregister_resource(self, resource: ResourceIdStr) -> None:
        if resource in self.resource_timers:
            self.resource_timers[resource].uninstall_timer()
            del self.resource_timers[resource]

    def reset(self) -> None:
        self.stop()

        self.global_periodic_repair_task = None
        self.global_periodic_deploy_task = None
        self.periodic_repair_interval = None
        self.periodic_deploy_interval = None

        self._initialize()

    def uninstall_timer(self, resource: ResourceIdStr) -> None:
        """
        Remove the timer for a given resource (if it exists) and cancel
        the associated deployment task (if any).
        """
        try:
            self.resource_timers[resource].uninstall_timer()
            self.resource_timers[resource].cancel()
        except KeyError:
            pass

    def install_timer(self, resource: ResourceIdStr, is_dirty: bool, action: Callable[..., Coroutine[Any, Any, None]]) -> None:
        if resource not in self.resource_timers:
            self.register_resource(resource)
        self.resource_timers[resource].install_timer(
            periodic_deploy_interval=self.periodic_deploy_interval,
            periodic_repair_interval=self.periodic_repair_interval,
            is_dirty=is_dirty,
            action_function=action,
        )

    def stop(self) -> None:
        for timer in self.resource_timers.values():
            timer.uninstall_timer()

        for task in [self.global_periodic_repair_task, self.global_periodic_deploy_task]:
            if task:
                self._sched.remove(task)

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

    def __repr__(self) -> str:
        return str(self.resource_timers)
