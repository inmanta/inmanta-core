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
from typing import Sequence

import inmanta.deploy.scheduler
from inmanta.agent import config as agent_config
from inmanta.data.model import ResourceIdStr

from inmanta import data
from inmanta.deploy.work import TaskPriority
from inmanta.util import CronSchedule, ScheduledTask, Scheduler, IntervalSchedule

LOGGER = logging.getLogger(__name__)


class ResourceTimer:
    """
    This class represents a single timer for a single resource.
    This class is not meant to be used directly. It is solely intended
    to be instantiated and manipulated by a TimerManager instance sitting on
    top of it. To create and delete resource timers, the TimerManager interface
    should be used.
    """

    def __init__(self, resource: ResourceIdStr, scheduler: "inmanta.deploy.scheduler.ResourceScheduler"):
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
        Main interface expected to be called once per timer by the TimerManager instance sitting on
        top of this class.

        Schedule the underlying resource for execution in <countdown> seconds with
        the given reason and priority.

        :param countdown: In this many seconds in the future, this method will ensure the underlying
            resource is scheduled for deploy.
        :param reason: The reason argument that will be passed down
            to the resource scheduler's `deploy_with_context` method.
        :param priority: The priority argument that will be passed down
            to the resource scheduler's `deploy_with_context` method.
        """

        def _create_repair_task() -> None:
            self.trigger_deploy = asyncio.create_task(
                self._resource_scheduler.trigger_deploy_for_resource(self.resource, reason, priority)
            )

        assert (
            self.next_schedule_handle is None
        ), f"Per-resource timer set twice for resource {self.resource}, this should not happen"

        self.next_schedule_handle = asyncio.get_running_loop().call_later(countdown, _create_repair_task)

    def cancel(self) -> None:
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


class TimerManager:
    def __init__(self, resource_scheduler: "inmanta.deploy.scheduler.ResourceScheduler"):
        """
        :param resource_scheduler: Back reference to the ResourceScheduler that was responsible for
            spawning this TimerManager.
        """
        self.resource_timers: dict[ResourceIdStr, ResourceTimer] = {}


        self.periodic_per_resource_repair_interval: int | None = None
        self.periodic_per_resource_deploy_interval: int | None = None

        self.periodic_global_repair_cron: str | None = None
        self.periodic_global_deploy_cron: str | None = None

        self._resource_scheduler = resource_scheduler

        self._cron_scheduler = Scheduler("TimerManager")

        self.global_periodic_repair_task: ScheduledTask | None = None
        self.global_periodic_deploy_task: ScheduledTask | None = None

        self._env_settings_watcher_check_interval: float = 0.2
        self.env_settings_watcher_task: ScheduledTask | None = None

    def reset(self) -> None:
        self.stop()

        self.global_periodic_repair_task = None
        self.periodic_global_repair_cron = None
        self.global_periodic_deploy_task = None
        self.periodic_global_deploy_cron = None
        self.periodic_per_resource_repair_interval = None
        self.periodic_per_resource_deploy_interval = None
        self.env_settings_watcher_task = None

    def stop(self) -> None:
        for timer in self.resource_timers.values():
            timer.cancel()

        for task in [self.global_periodic_repair_task, self.global_periodic_deploy_task, self.env_settings_watcher_task]:
            if task:
                self._cron_scheduler.remove(task)

    async def join(self) -> None:
        await asyncio.gather(*[timer.join() for timer in self.resource_timers.values()])

    def _initialize(self) -> None:
        """
        Set the periodic timers for repairs and deploys. Either per-resource if the
        associated config option is passed as a positive integer, or globally if it
        is passed as a cron expression string.

        Set the watcher task that periodically checks whether the environment
        settings for periodic deploy and repairs have changed.
        """
        deploy_timer: int | str = agent_config.agent_deploy_interval.get()
        repair_timer: int | str = agent_config.agent_repair_interval.get()

        if isinstance(deploy_timer, str):
            self.global_periodic_deploy_task = self._trigger_global_deploy(deploy_timer)
            self.periodic_global_deploy_cron = deploy_timer
        else:
            self.periodic_per_resource_deploy_interval = deploy_timer if deploy_timer > 0 else None

        if isinstance(repair_timer, str):
            self.global_periodic_repair_task = self._trigger_global_repair(repair_timer)
            self.periodic_global_repair_cron = repair_timer
        else:
            self.periodic_per_resource_repair_interval = repair_timer if repair_timer > 0 else None

        self.env_settings_watcher_task = self._trigger_environment_settings_watcher()

    def _trigger_environment_settings_watcher(self) -> ScheduledTask:
        """
        Trigger a watcher task that periodically checks for changes in the
        environment settings for periodic deploys and repairs.

        :returns: the associated scheduled task.
        """

        task = self._cron_scheduler.add_action(
            self._check_environment_settings,
            IntervalSchedule(self._env_settings_watcher_check_interval),
            cancel_on_stop=True,
            quiet_mode=True,
        )

        assert isinstance(task, ScheduledTask)
        return task

    async def _check_environment_settings(self) -> None:
        """
        Check if the settings for periodic repair and deploy have changed.
        Take action accordingly, for each setting:
            - check for type change from int (per-resource) to str (global) and vice versa
            - check for value change
        """

        async with data.Environment.get_connection() as connection:
            env = await data.Environment.get_by_id(self._resource_scheduler.environment, connection=connection)
            assert env is not None, (
                f"TimerManager cannot fetch settings for environment {self._resource_scheduler.environment} "
                "because it does not exist. This shouldn't happen."
            )
            db_deploy_interval: str = await env.get(data.AUTOSTART_AGENT_DEPLOY_INTERVAL, connection)
            db_repair_interval: str = await env.get(data.AUTOSTART_AGENT_REPAIR_INTERVAL, connection)

        db_per_resource_periodic_deploy: int | None = None
        db_global_periodic_deploy: str | None = None
        db_per_resource_periodic_repair: int | None = None
        db_global_periodic_repair: str | None = None

        try:
            db_per_resource_periodic_deploy = int(db_deploy_interval)
        except ValueError:
            db_global_periodic_deploy = db_deploy_interval
        try:
            db_per_resource_periodic_repair = int(db_repair_interval)
        except ValueError:
            db_global_periodic_repair = db_repair_interval

        if self.periodic_global_deploy_cron != db_global_periodic_deploy:
            if self.periodic_global_deploy_cron is None:
                # Deploys are now set globally, and no longer on a per-resource basis

                self.periodic_per_resource_deploy_interval = None
                self.remove_resources([resource for resource in self.resource_timers.keys()])

            else:
                # Global deploy schedule changed
                self._cron_scheduler.remove(self.global_periodic_deploy_task)

            self.periodic_global_deploy_cron = db_global_periodic_deploy

            if self.periodic_global_deploy_cron:
                self.global_periodic_deploy_task = self._trigger_global_deploy(self.periodic_global_deploy_cron)

        elif self.periodic_per_resource_deploy_interval != db_per_resource_periodic_deploy:
            pass



        self.periodic_global_deploy_cron: str | None = None

        self.periodic_per_resource_repair_interval: int | None = None
        self.periodic_per_resource_deploy_interval: int | None = None


    def _trigger_global_deploy(self, cron_expression: str) -> ScheduledTask:
        """
        Trigger a global deploy following a cron expression schedule.
        This does not affect previously started cron schedules.

        :returns: the associated scheduled task.
        """

        cron_schedule = CronSchedule(cron=cron_expression)

        async def _action() -> None:
            await self._resource_scheduler.deploy(
                reason=f"Global deploy triggered because of cron expression for deploy interval: '{cron_expression}'",
                priority=TaskPriority.INTERVAL_DEPLOY,
            )

        task = self._cron_scheduler.add_action(_action, cron_schedule)
        assert isinstance(task, ScheduledTask)
        return task

    def _trigger_global_repair(self, cron_expression: str) -> ScheduledTask:
        """
        Trigger a global repair following a cron expression schedule.
        This does not affect previously started cron schedules.

        :returns: the associated scheduled task.
        """
        cron_schedule = CronSchedule(cron=cron_expression)

        async def _action() -> None:
            await self._resource_scheduler.repair(
                reason=f"Global repair triggered because of cron expression for repair interval: '{cron_expression}'",
                priority=TaskPriority.INTERVAL_REPAIR,
            )

        task = self._cron_scheduler.add_action(_action, cron_schedule)
        assert isinstance(task, ScheduledTask)
        return task

    def update_resource(self, resource: ResourceIdStr, is_dirty: bool) -> None:
        """
        Make sure the given resource is marked for eventual re-deployment in the future.

        This method will inspect self.periodic_repair_interval and self.periodic_deploy_interval
        to decide when re-deployment will happen and whether this timer is global (i.e. pertains
        to all resources) or specific to this resource.

        The is_dirty parameter lets the caller (i.e. the resource scheduler sitting on top
        of this TimerManager) give information regarding the last known state of the resource
        so that this method can decide whether a repair or a deploy should be scheduled.

        The scheduler is considered the authority. If a previous timer is already in place
        for the given resource, (which should not happen) it will be canceled first and a
        new one will be re-scheduled.

        :param resource: the resource to re-deploy.
        :param is_dirty: If the resource is in an assumed bad state, we should re-deploy it
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
        if self.periodic_per_resource_repair_interval is None and self.periodic_per_resource_deploy_interval is None:
            return

        if not is_dirty:
            # At the time of the call, the resource is in an assumed good state:
            # schedule a periodic repair for it if the repair setting is set on a per-resource basis
            if self.periodic_per_resource_repair_interval:
                countdown, reason, priority = _setup_repair(self.periodic_per_resource_repair_interval)
            else:
                return

        else:
            # At the time of the call, the resource is in an assumed bad state:
            # schedule a repair or a deploy, whichever has the shortest interval set
            # on a per-resource basis.

            if self.periodic_per_resource_repair_interval and self.periodic_per_resource_deploy_interval:
                if self.periodic_per_resource_repair_interval < self.periodic_per_resource_deploy_interval:
                    countdown, reason, priority = _setup_repair(self.periodic_per_resource_repair_interval)
                else:
                    countdown, reason, priority = _setup_deploy(self.periodic_per_resource_deploy_interval)
            elif self.periodic_per_resource_repair_interval:
                countdown, reason, priority = _setup_repair(self.periodic_per_resource_repair_interval)
            else:
                assert self.periodic_deploy_interval is not None  # mypy
                countdown, reason, priority = _setup_deploy(self.periodic_per_resource_deploy_interval)

        self.resource_timers[resource].cancel()
        self.resource_timers[resource].set_timer(
            countdown=countdown,
            reason=reason,
            priority=priority,
        )

    def remove_resource(self, resource: ResourceIdStr) -> None:
        """
        Stop managing the timer for the given resource and
        cancel the associated re-deployment, if any.
        """
        if resource in self.resource_timers:
            self.resource_timers[resource].cancel()
            del self.resource_timers[resource]

    def remove_resources(self, resources: Sequence[ResourceIdStr]) -> None:
        """
        Remove a batch of resources.
        """
        for resource in resources:
            self.remove_resource(resource)
