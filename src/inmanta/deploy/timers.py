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
from collections.abc import Coroutine, Sequence
from typing import Any, Callable

import inmanta.deploy.scheduler
from inmanta.agent import config as agent_config
from inmanta.data.model import ResourceIdStr
from inmanta.deploy.work import TaskPriority
from inmanta.util import CronSchedule, ScheduledTask, Scheduler

LOGGER = logging.getLogger(__name__)


class ResourceTimer:
    resource: ResourceIdStr

    repair_handle: asyncio.Task[None] | None

    def __init__(self, resource: ResourceIdStr):
        self.resource = resource
        self.repair_handle = None

    async def install_timer(
        self,
        periodic_deploy_interval: int | None,
        periodic_repair_interval: int | None,
        is_dirty: bool,
        action_function: Callable[[ResourceIdStr, int], Coroutine[Any, Any, None]],
    ) -> None:

        next_execute_time: int

        if periodic_repair_interval is not None and periodic_deploy_interval is not None:
            if is_dirty:
                next_execute_time = min(periodic_deploy_interval, periodic_repair_interval)
            else:
                next_execute_time = periodic_repair_interval
        elif periodic_deploy_interval is not None:
            next_execute_time = periodic_deploy_interval
        elif periodic_repair_interval is not None:
            next_execute_time = periodic_repair_interval
        else:
            return

        await asyncio.sleep(next_execute_time)
        self.repair_handle = asyncio.create_task(action_function(self.resource, next_execute_time))

    def uninstall_timer(self) -> None:
        if self.repair_handle is not None:
            self.repair_handle.cancel()

    def cancel(self) -> None:
        if self.repair_handle:
            self.repair_handle.cancel()


class TimerManager:
    resource_timers: dict[ResourceIdStr, ResourceTimer]

    def __init__(self, resource_scheduler: "inmanta.deploy.scheduler.ResourceScheduler"):
        self.resource_timers = {}

        self.global_periodic_repair_task: ScheduledTask | None = None
        self.global_periodic_deploy_task: ScheduledTask | None = None

        # Typing for repair/deploy timers :
        #   - int: max number of seconds between consecutive repairs/deploys
        #     on a per-resource basis.
        #   - str: cron-like expression to schedule a periodic global repair/deploy
        #     i.e. for all known resources.
        self._deploy_timer: int | str | None = None
        self._repair_timer: int | str | None = None

        self._resource_scheduler = resource_scheduler

        self.periodic_repair_interval: int | None = None
        self.periodic_deploy_interval: int | None = None

        self._sched = Scheduler("Resource scheduler")

    def register_resource(self, resource: ResourceIdStr) -> None:
        self.resource_timers[resource] = ResourceTimer(resource)

    def unregister_resource(self, resource: ResourceIdStr) -> None:
        if resource in self.resource_timers:
            self.resource_timers[resource].cancel()
            del self.resource_timers[resource]

    def reset(self) -> None:
        pass

    def uninstall_timer(self, resource: ResourceIdStr) -> None:
        try:
            self.resource_timers[resource].uninstall_timer()
        except KeyError:
            pass

    async def install_timer(self, resource: ResourceIdStr) -> None:
        if resource not in self.resource_timers:
            self.register_resource(resource)
        await self.resource_timers[resource].install_timer(
            periodic_deploy_interval=self.periodic_deploy_interval,
            periodic_repair_interval=self.periodic_repair_interval,
            is_dirty=True,
            action_function=self._resource_scheduler.repair_resource,
        )

    def stop(self) -> None:
        for task in self.resource_timers.values():
            task.uninstall_timer()

    def initialize(self, resources: Sequence[ResourceIdStr]) -> None:
        self._deploy_timer = agent_config.agent_deploy_interval.get()
        self._repair_timer = agent_config.agent_repair_interval.get()
        if isinstance(self._deploy_timer, str):
            self.global_periodic_deploy_task = self.trigger_global_deploy(self._deploy_timer)
        else:
            self.periodic_deploy_interval = self._deploy_timer if self._deploy_timer > 0 else None

        if isinstance(self._repair_timer, str):
            self.global_periodic_repair_task = self.trigger_global_repair(self._repair_timer)
        else:
            self.periodic_repair_interval = self._repair_timer if self._repair_timer > 0 else None

        LOGGER.debug(
            "Initializing timer manager with gpd %s gpr %s pd %s pr %s",
            self.global_periodic_deploy_task,
            self.global_periodic_repair_task,
            self.periodic_deploy_interval,
            self.periodic_repair_interval,
        )

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
