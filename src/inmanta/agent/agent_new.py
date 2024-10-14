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

import datetime
import logging
import os
import random
import uuid
from concurrent.futures.thread import ThreadPoolExecutor
from typing import Any, Callable, Coroutine, Optional, Union

from inmanta import config, const, protocol
from inmanta.agent import config as cfg
from inmanta.agent import executor, forking_executor
from inmanta.agent.reporting import collect_report
from inmanta.const import AGENT_SCHEDULER_ID
from inmanta.data.model import AttributeStateChange, ResourceVersionIdStr
from inmanta.deploy.scheduler import ResourceScheduler
from inmanta.protocol import SessionEndpoint, methods, methods_v2
from inmanta.types import Apireturn
from inmanta.util import CronSchedule, IntervalSchedule, ScheduledTask, Scheduler, TaskMethod, TaskSchedule, join_threadpools

LOGGER = logging.getLogger(__name__)


class Agent(SessionEndpoint):
    """
    This is the new scheduler, adapted to the agent protocol

    It serves a single endpoint that allows communications with the scheduler
    """

    def __init__(
        self,
        environment: Optional[uuid.UUID] = None,
    ):
        """
        :param environment: environment id
        """
        super().__init__(name="agent", timeout=cfg.server_timeout.get(), reconnect_delay=cfg.agent_reconnect_delay.get())

        self.thread_pool = ThreadPoolExecutor(1, thread_name_prefix="mainpool")
        self._storage = self.check_storage()

        if environment is None:
            environment = cfg.environment.get()
            if environment is None:
                raise Exception("The agent requires an environment to be set.")
        self.set_environment(environment)

        assert self._env_id is not None

        self.executor_manager: executor.ExecutorManager[executor.Executor] = self.create_executor_manager()
        self.scheduler = ResourceScheduler(self._env_id, self.executor_manager, self._client)
        self.working = False

        self._sched = Scheduler("new agent endpoint")
        self._time_triggered_actions: set[ScheduledTask] = set()

        self._set_deploy_and_repair_intervals()

    def _set_deploy_and_repair_intervals(self) -> None:
        """
        Fetch the settings related to automatic deploys and repairs from the config
        FIXME: These settings are not currently updated (unlike the old agent)
            We should fix or remove this timer in the future.
        """
        # do regular deploys
        self._deploy_interval = cfg.agent_deploy_interval.get()
        deploy_splay_time = cfg.agent_deploy_splay_time.get()

        self._deploy_splay_value = random.randint(0, deploy_splay_time)

        # do regular repair runs
        self._repair_interval: Union[int, str] = cfg.agent_repair_interval.get()
        repair_splay_time = cfg.agent_repair_splay_time.get()
        self._repair_splay_value = random.randint(0, repair_splay_time)

    def _enable_time_triggers(self) -> None:

        def periodic_schedule(
            kind: str,
            action: Callable[[], Coroutine[object, None, object]],
            interval: Union[int, str],
            splay_value: int,
        ) -> bool:
            """
            Schedule a periodic task

            :param kind: Name of the task (value to display in logs)
            :param action: The action to schedule periodically
            :param interval: The interval at which to schedule the task. Can be specified as either a number of
                seconds, or a cron string.
            :param splay_value: When specifying the interval as a number of seconds, this parameter specifies
                the number of seconds by which to delay the initial execution of this action.
            """
            now = datetime.datetime.now().astimezone()

            if isinstance(interval, int) and interval > 0:
                LOGGER.info(
                    "Scheduling periodic %s with interval %d and splay %d (first run at %s)",
                    kind,
                    interval,
                    splay_value,
                    (now + datetime.timedelta(seconds=splay_value)).strftime(const.TIME_LOGFMT),
                )
                interval_schedule: IntervalSchedule = IntervalSchedule(
                    interval=float(interval), initial_delay=float(splay_value)
                )
                self._enable_time_trigger(action, interval_schedule)
                return True

            if isinstance(interval, str):
                LOGGER.info("Scheduling periodic %s with cron expression '%s'", kind, interval)
                cron_schedule = CronSchedule(cron=interval)
                self._enable_time_trigger(action, cron_schedule)
                return True
            return False

        periodic_schedule("deploy", self.scheduler.deploy, self._deploy_interval, self._deploy_splay_value)
        periodic_schedule("repair", self.scheduler.repair, self._repair_interval, self._repair_splay_value)

    def _enable_time_trigger(self, action: TaskMethod, schedule: TaskSchedule) -> None:
        self._sched.add_action(action, schedule)
        self._time_triggered_actions.add(ScheduledTask(action=action, schedule=schedule))

    def _disable_time_triggers(self) -> None:
        for task in self._time_triggered_actions:
            self._sched.remove(task)
        self._time_triggered_actions.clear()

    def create_executor_manager(self) -> executor.ExecutorManager[executor.Executor]:
        assert self._env_id is not None
        return forking_executor.MPManager(
            self.thread_pool,
            self.sessionid,
            self._env_id,
            config.log_dir.get(),
            self._storage["executor"],
            LOGGER.level,
            cli_log=False,
        )

    async def stop(self) -> None:
        if self.working:
            await self.stop_working()
        threadpools_to_join = [self.thread_pool]
        await self.executor_manager.join(threadpools_to_join, const.SHUTDOWN_GRACE_IOLOOP * 0.9)
        self.thread_pool.shutdown(wait=False)

        await join_threadpools(threadpools_to_join)
        await super().stop()

    async def start_connected(self) -> None:
        """
        Setup our single endpoint
        """
        await self.add_end_point_name(AGENT_SCHEDULER_ID)

    async def start_working(self) -> None:
        """Start working, once we have a session"""
        if self.working:
            return
        self.working = True
        await self.executor_manager.start()
        await self.scheduler.start()
        self._enable_time_triggers()

    async def stop_working(self, timeout: Optional[int] = None) -> None:
        """Stop working, connection lost"""
        if not self.working:
            return
        self.working = False
        self._disable_time_triggers()
        await self.executor_manager.stop()
        if timeout is not None:
            await self.executor_manager.join([], timeout=timeout)
        await self.scheduler.stop()

    @protocol.handle(methods_v2.update_agent_map)
    async def update_agent_map(self, agent_map: dict[str, str]) -> None:
        # Not used here
        pass

    @protocol.handle(methods.set_state)
    async def set_state(self, agent: str, enabled: bool) -> Apireturn:
        if agent == AGENT_SCHEDULER_ID:
            should_be_stopped = await self.scheduler.refresh_state()
            enabled = not should_be_stopped  # TODO h remove

            if enabled:
                await self.start_working()
            else:
                await self.stop_working(timeout=const.EXECUTOR_GRACE_HARD)
        else:
            try:
                await self.scheduler.refresh_agent_state_from_db(name=agent)
            except LookupError:
                return 404, "No such agent"

        return 200, f"{agent} has been {'started' if enabled else 'stopped'} - {should_be_stopped}"

    async def on_reconnect(self) -> None:
        name = AGENT_SCHEDULER_ID
        result = await self._client.get_state(tid=self._env_id, sid=self.sessionid, agent=name)
        if result.code == 200 and result.result is not None:
            state = result.result
            if "enabled" in state and isinstance(state["enabled"], bool):
                await self.set_state(name, state["enabled"])
            else:
                LOGGER.warning("Server reported invalid state %s" % (repr(state)))
        else:
            LOGGER.warning("could not get state from the server")

    async def on_disconnect(self) -> None:
        await self.stop_working()

    @protocol.handle(methods.trigger, env="tid", agent="id")
    async def trigger_update(self, env: uuid.UUID, agent: str, incremental_deploy: bool) -> Apireturn:
        """
        Trigger an update
        """
        assert env == self.environment
        assert agent == AGENT_SCHEDULER_ID
        if incremental_deploy:
            LOGGER.info("Agent %s got a trigger to run deploy in environment %s", agent, env)
            await self.scheduler.deploy()
        else:
            LOGGER.info("Agent %s got a trigger to run repair in environment %s", agent, env)
            await self.scheduler.repair()
        return 200

    @protocol.handle(methods.trigger_read_version, env="tid", agent="id")
    async def read_version(self, env: uuid.UUID) -> Apireturn:
        """
        Send a notification to the scheduler that a new version has been released
        """
        assert env == self.environment
        await self.scheduler.read_version()
        return 200

    @protocol.handle(methods.resource_event, env="tid", agent="id")
    async def resource_event(
        self,
        env: uuid.UUID,
        agent: str,
        resource: ResourceVersionIdStr,
        send_events: bool,
        state: const.ResourceState,
        change: const.Change,
        changes: dict[ResourceVersionIdStr, dict[str, AttributeStateChange]],
    ) -> Apireturn:
        # Doesn't do anything
        pass

    @protocol.handle(methods.do_dryrun, env="tid", dry_run_id="id")
    async def run_dryrun(self, env: uuid.UUID, dry_run_id: uuid.UUID, agent: str, version: int) -> Apireturn:
        """
        Run a dryrun of the given version
        """
        assert env == self.environment
        assert agent == AGENT_SCHEDULER_ID
        LOGGER.info("Agent %s got a trigger to run dryrun %s for version %s in environment %s", agent, dry_run_id, version, env)

        await self.scheduler.dryrun(dry_run_id, version)
        return 200

    @protocol.handle(methods.get_parameter, env="tid")
    async def get_facts(self, env: uuid.UUID, agent: str, resource: dict[str, Any]) -> Apireturn:
        # FIXME: this api is very inefficient: it sends the entire resource, we only need the id now
        assert env == self.environment
        assert agent == AGENT_SCHEDULER_ID
        LOGGER.info("Agent %s got a trigger to run get_facts for resource %s in environment %s", agent, resource.get("id"), env)
        await self.scheduler.get_facts(resource)
        return 200

    @protocol.handle(methods.get_status)
    async def get_status(self) -> Apireturn:
        return 200, collect_report(self)

    def check_storage(self) -> dict[str, str]:
        """
        Check if the server storage is configured and ready to use.
        """

        # FIXME: review on disk layout: https://github.com/inmanta/inmanta-core/issues/7590

        state_dir = cfg.state_dir.get()

        if not os.path.exists(state_dir):
            os.mkdir(state_dir)

        agent_state_dir = os.path.join(state_dir, "agent")

        if not os.path.exists(agent_state_dir):
            os.mkdir(agent_state_dir)

        dir_map = {"agent": agent_state_dir}

        code_dir = os.path.join(agent_state_dir, "code")
        dir_map["code"] = code_dir
        if not os.path.exists(code_dir):
            os.mkdir(code_dir)

        env_dir = os.path.join(agent_state_dir, "env")
        dir_map["env"] = env_dir
        if not os.path.exists(env_dir):
            os.mkdir(env_dir)

        executor_dir = os.path.join(agent_state_dir, "executor")
        dir_map["executor"] = executor_dir
        if not os.path.exists(executor_dir):
            os.mkdir(executor_dir)

        return dir_map

    # TODO h missing change if agent is paused and then resumed
    """
    Resume the scheduler / a particular agent. Depending on the provided name, one or the other will be impacted by this
    action. If the scheduler is resumed, the executor manager will be resumed. Otherwise, only the agent will be resumed
    (if it exists)

    :param name: The name of the agent to resume
    """
    """
    Stop the scheduler / a particular agent. Depending on the provided name, one or the other will be impacted by this
    action. If the scheduler is stopped, the executor manager will also be stopped to kill any remaining processes.
    Otherwise, only the agent will be stopped (if it exists)

    :param name: The name of the agent to stop
    """
