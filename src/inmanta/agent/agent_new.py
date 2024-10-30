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
from inmanta.deploy import scheduler
from inmanta.deploy.work import TaskPriority
from inmanta.protocol import SessionEndpoint, methods, methods_v2
from inmanta.types import Apireturn
from inmanta.util import (
    CronSchedule,
    IntervalSchedule,
    ScheduledTask,
    Scheduler,
    TaskMethod,
    TaskSchedule,
    ensure_directory_exist,
    join_threadpools,
)

LOGGER = logging.getLogger("inmanta.scheduler")


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
        self.scheduler = scheduler.ResourceScheduler(self._env_id, self.executor_manager, self._client)
        self.working = False

    def _set_deploy_and_repair_intervals(self) -> None:
        """
        Fetch the settings related to automatic deploys and repairs from the config
        FIXME: These settings are not currently updated (unlike the old agent)
            We should fix or remove this timer in the future.
        """
        # quick and dirty, fix later:
        self.scheduler._compliance_check_window = cfg.scheduler_resource_compliance_check_window.get()



    def create_executor_manager(self) -> executor.ExecutorManager[executor.Executor]:
        assert self._env_id is not None
        return forking_executor.MPManager(
            self.thread_pool,
            self.sessionid,
            self._env_id,
            config.log_dir.get(),
            self._storage["executors"],
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

    async def stop_working(self) -> None:
        """Stop working, connection lost"""
        if not self.working:
            return
        self.working = False
        await self.executor_manager.stop()
        await self.scheduler.stop()

    @protocol.handle(methods_v2.update_agent_map)
    async def update_agent_map(self, agent_map: dict[str, str]) -> None:
        # Not used here
        pass

    async def unpause(self, name: str) -> Apireturn:
        if name != AGENT_SCHEDULER_ID:
            return 404, "No such agent"

        LOGGER.info("Scheduler started for environment %s", self.environment)
        await self.start_working()
        return 200

    async def pause(self, name: str) -> Apireturn:
        if name != AGENT_SCHEDULER_ID:
            return 404, "No such agent"

        LOGGER.info("Scheduler stopped for environment %s", self.environment)
        await self.stop_working()
        return 200

    @protocol.handle(methods.set_state)
    async def set_state(self, agent: str, enabled: bool) -> Apireturn:
        if enabled:
            return await self.unpause(agent)
        else:
            return await self.pause(agent)

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
        LOGGER.warning("Connection to server lost, stopping scheduler in environment %s", self.environment)
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
        Check if the server storage is configured and ready to use. Ultimately, this is
        what the layout on disk will look like:

            /var/lib/inmanta/
                ├─ server
                    ├─ env_uuid
                        ├─ executors/
                        │   ├─ venvs/
                        │   │   ├─ venv_blueprint_hash_1/
                        │   │   ├─ venv_blueprint_hash_2/
                        │   │   ├─ ...
                        │   │
                        │   ├─ code/
                        │       ├─ executor_blueprint_hash_1/
                        │       ├─ executor_blueprint_hash_2/
                        │       ├─ ...
                        │
                        ├─ compiler/
                        │
                        ├─ scheduler.cfg

        """

        state_dir = cfg.state_dir.get()
        if not os.path.exists(state_dir):
            os.mkdir(state_dir)

        dir_map = {
            "executors": ensure_directory_exist(state_dir, "executors"),
        }
        return dir_map
