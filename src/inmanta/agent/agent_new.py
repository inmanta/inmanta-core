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
import uuid
from concurrent.futures.thread import ThreadPoolExecutor
from typing import Any, Optional

import inmanta.server.config as opt
from inmanta import config, const, data, protocol
from inmanta.agent import config as cfg
from inmanta.agent import executor, forking_executor
from inmanta.agent.reporting import collect_report
from inmanta.const import AGENT_SCHEDULER_ID
from inmanta.data.model import DataBaseReport, SchedulerStatusReport
from inmanta.deploy import scheduler
from inmanta.protocol import SessionEndpoint, methods, methods_v2
from inmanta.server.services.databaseservice import DatabaseMonitor
from inmanta.types import Apireturn
from inmanta.util import ensure_directory_exist, join_threadpools

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

    async def start(self) -> None:
        # Make mypy happy
        assert data.Resource._connection_pool is not None
        self._db_monitor = DatabaseMonitor(
            data.Resource._connection_pool,
            opt.db_name.get(),
            opt.db_host.get(),
        )
        self._db_monitor.start()

        await super().start()

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
        if self._db_monitor:
            await self._db_monitor.stop()
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
        LOGGER.info("Scheduler started for environment %s", self.environment)

    async def stop_working(self, timeout: float = 0.0) -> None:
        """Stop working, connection lost"""
        if not self.working:
            return
        self.working = False
        await self.scheduler.stop()
        await self.executor_manager.stop()
        await self.executor_manager.join([], timeout=timeout)
        await self.scheduler.join()
        LOGGER.info("Scheduler stopped for environment %s", self.environment)

    @protocol.handle(methods_v2.remove_executor_venvs)
    async def remove_executor_venvs(self) -> None:
        """
        Remove all the venvs used by the executors of this agent.
        """
        try:
            await data.Notification(
                environment=self._env_id,
                created=datetime.datetime.now().astimezone(),
                title="Agent operations suspended",
                message="Agent operations are temporarily suspended because the user requested to remove the agent venvs.",
                severity=const.NotificationSeverity.info,
            ).insert()
            # Stop all deployments and stop all executors
            await self.scheduler.suspend_deployments(reason="removing all agent venvs")
            await self.executor_manager.stop_all_executors()
            # Remove venvs
            await self._remove_executor_venvs()
        except Exception as e:
            await data.Notification(
                environment=self._env_id,
                created=datetime.datetime.now().astimezone(),
                title="Agent venv removal failed",
                message=f"Failed to remove agent venvs: {e}",
                severity=const.NotificationSeverity.error,
            ).insert()
        else:
            await data.Notification(
                environment=self._env_id,
                created=datetime.datetime.now().astimezone(),
                title="Agent venv removal finished",
                message="The agent venvs were successfully removed. Resuming agent operations.",
                severity=const.NotificationSeverity.info,
            ).insert()
        finally:
            # Resume deployments again
            await self.scheduler.resume_deployments()

    async def _remove_executor_venvs(self) -> None:
        """
        This method was created to be able to monkeypatch it in testing.
        """
        environment_manager: executor.VirtualEnvironmentManager | None = self.executor_manager.get_environment_manager()
        if not environment_manager:
            raise Exception(
                "Calling the remove_executor_venvs endpoint while running against an ExecutorManager that doesn't have"
                " a VirtualEnvironmentManager. This can happen while running the test suite using"
                " the agent fixture. In that case all executors run in the same process as the server."
                " So there are no venvs to cleanup."
            )
        await environment_manager.remove_all_venvs()

    @protocol.handle(methods.set_state)
    async def set_state(self, agent: Optional[str], enabled: bool) -> Apireturn:
        if agent == AGENT_SCHEDULER_ID:
            if enabled:
                if self.working != enabled:
                    await self.start_working()
                else:
                    # Special case that the server considers us disconnected, but the Scheduler thinks we are still connected.
                    # In that case, the Scheduler may have missed some event, therefore, we need to refresh everything
                    # (Scheduler side) to make sure we are up to date when the server considers that the Scheduler
                    # is back online
                    await self.scheduler.read_version()
                    await self.scheduler.refresh_all_agent_states_from_db()
            else:
                # We want the request to not end in a 500 error:
                # if the scheduler is being shut down, it cannot respond to the request
                await self.stop_working(timeout=const.EXECUTOR_GRACE_HARD)

            return 200, "Scheduler has been notified!"
        else:
            if agent is None:
                await self.scheduler.refresh_all_agent_states_from_db()
                return 200, "All agents have been notified!"
            else:
                await self.scheduler.refresh_agent_state_from_db(name=agent)
                return 200, f"Agent `{agent}` has been notified!"

    async def on_reconnect(self) -> None:
        result = await self._client.get_state(tid=self._env_id, sid=self.sessionid, agent=AGENT_SCHEDULER_ID)
        if result.code == 200 and result.result is not None:
            state = result.result
            if "enabled" in state and isinstance(state["enabled"], bool):
                if state["enabled"]:
                    await self.start_working()
                else:
                    assert not self.working
            else:
                LOGGER.warning("Server reported invalid state %s" % (repr(state)))
        else:
            LOGGER.warning("could not get state from the server")

    async def on_disconnect(self) -> None:
        LOGGER.warning("Connection to server lost, stopping scheduler in environment %s", self.environment)
        await self.stop_working()

    @protocol.handle(methods.trigger, env="tid", agent="id")
    async def trigger_update(self, env: uuid.UUID, agent: None | str, incremental_deploy: bool) -> Apireturn:
        """
        Trigger an update for a specific agent, or for ALL agents in the environment when <agent> param is None.
        """
        if agent == const.AGENT_SCHEDULER_ID:
            agent = None

        if agent is None:
            agent_id = "All agents"
        else:
            agent_id = f"Agent {agent}"

        if incremental_deploy:
            LOGGER.info("%s got a trigger to run deploy in environment %s", agent_id, env)
            await self.scheduler.deploy(reason="user requested a deploy", agent=agent)
        else:
            LOGGER.info("%s got a trigger to run repair in environment %s", agent_id, env)
            await self.scheduler.repair(reason="user requested a repair", agent=agent)
        return 200

    @protocol.handle(methods.trigger_read_version, env="tid", agent="id")
    async def read_version(self, env: uuid.UUID) -> Apireturn:
        """
        Send a notification to the scheduler that a new version has been released
        """
        assert env == self.environment
        await self.scheduler.read_version()
        return 200

    @protocol.handle(methods.do_dryrun, env="tid", dry_run_id="id")
    async def run_dryrun(self, env: uuid.UUID, dry_run_id: uuid.UUID, agent: str, version: int) -> Apireturn:
        """
        Run a dryrun of the given version

        Paused agents are silently ignored
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

    @protocol.handle(methods_v2.trigger_get_status, env="tid")
    async def get_scheduler_resource_state(self, env: data.Environment) -> SchedulerStatusReport:
        assert env.id == self.environment
        report = await self.scheduler.get_resource_state()
        return report

    @protocol.handle(methods_v2.notify_timer_update, env="tid")
    async def notify_timer_update(self, env: data.Environment) -> None:
        assert env == self.environment
        await self.scheduler.load_timer_settings()

    @protocol.handle(methods_v2.get_db_status)
    async def get_db_status(self) -> DataBaseReport:
        if self._db_monitor is None:
            return DataBaseReport(
                connected=False,
                database="",
                host="",
                max_pool=0,
                open_connections=0,
                free_connections=0,
                pool_exhaustion_count=0,
            )
        return await self._db_monitor.get_status()

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
