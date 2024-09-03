"""
    Copyright 2017 Inmanta

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
import os
import uuid
from concurrent.futures.thread import ThreadPoolExecutor
from typing import Any, Optional

from inmanta import config, const, protocol
from inmanta.agent import config as cfg
from inmanta.agent import executor, forking_executor
from inmanta.agent.reporting import collect_report
from inmanta.const import AGENT_SCHEDULER_ID
from inmanta.data.model import AttributeStateChange, ResourceVersionIdStr
from inmanta.deploy.scheduler import ResourceScheduler
from inmanta.protocol import SessionEndpoint, methods, methods_v2
from inmanta.types import Apireturn
from inmanta.util import join_threadpools

LOGGER = logging.getLogger(__name__)


class CouldNotConnectToServer(Exception):
    pass


class Agent(SessionEndpoint):
    """
    An agent to enact changes upon resources. This agent listens to the
    message bus for changes.
    """

    # cache reference to THIS ioloop for handlers to push requests on it
    # defer to start, just to be sure
    _io_loop: asyncio.AbstractEventLoop

    def __init__(
        self,
        environment: Optional[uuid.UUID] = None,
    ):
        """
        :param hostname: this used to indicate the hostname of the agent,
        but it is now mostly used by testcases to prevent endpoint to be loaded from the config singleton
           see _init_endpoint_names
        :param agent_map: the agent map for this agent to use
        :param code_loader: do we enable the code loader (used for testing)
        :param environment: environment id
        """
        super().__init__("agent", timeout=cfg.server_timeout.get(), reconnect_delay=cfg.agent_reconnect_delay.get())

        self.thread_pool = ThreadPoolExecutor(1, thread_name_prefix="mainpool")
        self._storage = self.check_storage()

        if environment is None:
            environment = cfg.environment.get()
            if environment is None:
                raise Exception("The agent requires an environment to be set.")
        self.set_environment(environment)

        self.executor_manager: executor.ExecutorManager[executor.Executor] = self.create_executor_manager()
        self.scheduler = ResourceScheduler(self.executor_manager)
        self.working = False

    def create_executor_manager(self) -> executor.ExecutorManager[executor.Executor]:
        # To override in testing
        return forking_executor.MPManager(
            self.thread_pool,
            self.sessionid,
            self.environment,
            config.log_dir.get(),
            self._storage["executor"],
            LOGGER.level,
            False,
        )

    async def stop(self) -> None:
        await super().stop()

        if self.working:
            await self.stop_working()

        threadpools_to_join = [self.thread_pool]

        await self.executor_manager.join(threadpools_to_join, const.SHUTDOWN_GRACE_IOLOOP * 0.9)

        self.thread_pool.shutdown(wait=False)

        await join_threadpools(threadpools_to_join)

    async def start_connected(self) -> None:
        """
        This method is required because:
            1) The client transport is required to retrieve the autostart_agent_map from the server.
            2) _init_endpoint_names() needs to be an async method and async calls are not possible in a constructor.
        """
        await self.add_end_point_name(AGENT_SCHEDULER_ID)

    async def start(self) -> None:
        # cache reference to THIS ioloop for handlers to push requests on it
        self._io_loop = asyncio.get_running_loop()
        await super().start()

    async def start_working(self) -> None:
        """Start working, once we have a session"""
        # Todo: recycle them when we restart
        if self.working:
            return
        self.working = True
        await self.executor_manager.start()
        await self.scheduler.start()

    async def stop_working(self) -> None:
        """Start working, once we have a session"""
        if not self.working:
            return
        # Todo: recycle them when we restart
        self.working = False
        await self.executor_manager.stop()
        await self.scheduler.stop()

    @protocol.handle(methods_v2.update_agent_map)
    async def update_agent_map(self, agent_map: dict[str, str]) -> None:
        # Not used here
        pass

    async def unpause(self, name: str) -> Apireturn:
        if not name == AGENT_SCHEDULER_ID:
            return 404, "No such agent"

        await self.start_working()
        return 200

    async def pause(self, name: str) -> Apireturn:
        if not name == AGENT_SCHEDULER_ID:
            return 404, "No such agent"

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
        await self.stop_working()

    @protocol.handle(methods.trigger, env="tid", agent="id")
    async def trigger_update(self, env: uuid.UUID, agent: str, incremental_deploy: bool) -> Apireturn:
        """
        Trigger an update
        """
        assert env == self.environment
        assert agent == AGENT_SCHEDULER_ID
        if incremental_deploy:
            await self.scheduler.deploy()
        else:
            await self.scheduler.repair()
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
        assert env == self.environment
        assert agent == AGENT_SCHEDULER_ID
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
