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
import datetime
import logging
import traceback
import uuid
from collections.abc import Mapping, Set
from typing import Any, Optional

from inmanta import const, data
from inmanta.agent import executor
from inmanta.agent.code_manager import CodeManager
from inmanta.const import ResourceAction
from inmanta.data.model import ResourceIdStr
from inmanta.deploy import work
from inmanta.deploy.state import ModelState, ResourceDetails, ResourceStatus
from inmanta.deploy.work import PoisonPill
from inmanta.protocol import Client

# FIXME[#8008] review code structure + functionality + add docstrings
# FIXME[#8008] add import entry point test case


class ResourceScheduler:
    """
    Scheduler for resource actions. Reads resource state from the database and accepts deploy, dry-run, ... requests from the
    server. Schedules these requests as tasks according to priorities and, in case of deploy tasks, requires-provides edges.

    The scheduler expects to be notified by the server whenever a new version is released.
    """

    def __init__(
        self, environment: uuid.UUID, executor_manager: executor.ExecutorManager[executor.Executor], client: Client
    ) -> None:
        """
        :param environment: the environment we work for
        :param executor_manager: the executor manager that will provide us with executors
        :param client: connection to the server
        """
        self._state: ModelState = ModelState(version=0)
        self._work: work.ScheduledWork = work.ScheduledWork(
            requires=self._state.requires.requires_view(),
            provides=self._state.requires.provides_view(),
            consumer_factory=self.start_for_agent,
        )

        self._executor_manager = executor_manager

        # We uphold two locks to prevent concurrency conflicts between external events (e.g. new version or deploy request)
        # and the task executor background tasks.
        #
        # - lock to block scheduler state access (both model state and scheduled work) during scheduler-wide state updates
        #   (e.g. trigger deploy). A single lock suffices since all state accesses (both read and write) by the task runners are
        #   short, synchronous operations (and therefore we wouldn't gain anything by allowing multiple readers).
        self._scheduler_lock: asyncio.Lock = asyncio.Lock()
        # - lock to serialize scheduler state updates (i.e. process new version)
        self._update_lock: asyncio.Lock = asyncio.Lock()

        self._running = False
        # Agent name to worker task
        # here to prevent it from being GC-ed
        self._workers: dict[str, asyncio.Task[None]] = {}

        self._code_manager = CodeManager(client)
        self._environment = environment
        self._client = client

    def reset(self):
        """
        Clear out all state and start empty

        only allowed when ResourceScheduler is not running
        """
        assert not self._running
        self._state.reset()
        self._work.reset()

    async def start(self) -> None:
        self.reset()
        self._running = True
        # FIXME[#8009]: read from DB instead
        pass

    async def stop(self) -> None:
        self._running = False
        self._work.agent_queues.send_shutdown()
        await asyncio.gather(*self._workers.values())

    async def deploy(self) -> None:
        """
        Trigger a deploy
        """
        async with self._scheduler_lock:
            # FIXME[#8008]: more efficient access to dirty set by caching it on the ModelState
            dirty: Set[ResourceIdStr] = {
                r for r, details in self._state.resource_state.items() if details.status == ResourceStatus.HAS_UPDATE
            }
            # FIXME[#8008]: pass in running deploys
            self._work.update_state(ensure_scheduled=dirty, running_deploys=set())

    async def repair(self) -> None:
        # FIXME[#8008]: implement repair
        pass

    async def dryrun(self, dry_run_id: uuid.UUID, version: int) -> None:
        # FIXME
        pass

    async def get_facts(self, resource: dict[str, Any]) -> None:
        # FIXME, also clean up typing of arguments
        pass

    # FIXME[#8009]: design step 2: read new state from DB instead of accepting as parameter
    #               (method should be notification only, i.e. 0 parameters)
    async def new_version(
        self,
        version: int,
        resources: Mapping[ResourceIdStr, ResourceDetails],
        requires: Mapping[ResourceIdStr, Set[ResourceIdStr]],
    ) -> None:
        """A new version was received, update state and start deploying"""
        async with self._update_lock:
            # Inspect new state and mark resources as "update pending" where appropriate. Since this method is the only writer
            # for "update pending", and a stale read is acceptable, we can do this part before acquiring the exclusive scheduler
            # lock.
            deleted_resources: Set[ResourceIdStr] = self._state.resources.keys() - resources.keys()
            for resource in deleted_resources:
                self._work.delete_resource(resource)

            new_desired_state: list[ResourceIdStr] = []
            added_requires: dict[ResourceIdStr, Set[ResourceIdStr]] = {}
            dropped_requires: dict[ResourceIdStr, Set[ResourceIdStr]] = {}
            for resource, details in resources.items():
                if (
                    resource not in self._state.resources
                    or details.attribute_hash != self._state.resources[resource].attribute_hash
                ):
                    self._state.update_pending.add(resource)
                    new_desired_state.append(resource)
                new_requires: Set[ResourceIdStr] = requires.get(resource, set())
                old_requires: Set[ResourceIdStr] = self._state.requires.get(resource, set())
                added: Set[ResourceIdStr] = new_requires - old_requires
                dropped: Set[ResourceIdStr] = old_requires - new_requires
                if added:
                    self._state.update_pending.add(resource)
                    added_requires[resource] = added
                if dropped:
                    self._state.update_pending.add(resource)
                    dropped_requires[resource] = dropped
                # this loop is race-free, potentially slow, and completely synchronous
                # => regularly pass control to the event loop to not block scheduler operation during update prep
                await asyncio.sleep(0)

            # in the current implementation everything below the lock is synchronous, so it's not technically required. It is
            # however kept for two reasons:
            # 1. pass context once more to event loop before starting on the sync path
            #   (could be achieved with a simple sleep(0) if desired)
            # 2. clarity: it clearly signifies that this is the atomic and performance-sensitive part
            async with self._scheduler_lock:
                self._state.version = version
                for resource in new_desired_state:
                    self._state.update_desired_state(resources[resource])
                for resource in added_requires.keys() | dropped_requires.keys():
                    self._state.update_requires(resource, requires[resource])
                # ensure deploy for ALL dirty resources, not just the new ones
                # FIXME[#8008]: this is copy-pasted, make into a method?
                # FIXME: WDB TO SANDER: We should track dirty resources in a collection to not force a scan of the full state
                dirty: Set[ResourceIdStr] = {
                    r for r, details in self._state.resource_state.items() if details.status == ResourceStatus.HAS_UPDATE
                }
                self._work.update_state(
                    ensure_scheduled=dirty,
                    # FIXME[#8008]: pass in running deploys
                    running_deploys=set(),
                    added_requires=added_requires,
                    dropped_requires=dropped_requires,
                )
                for resource in deleted_resources:
                    self._state.drop(resource)
                # FIXME[#8008]: design step 7: drop update_pending
            # FIXME[#8008]: design step 10: Once more, drop all resources that do not exist in this version from the scheduled
            #               work, in case they got added again by a deploy trigger

    # FIXME[#8008]: set up background workers for each agent, calling _run_for_agent(). Make sure to somehow respond to new
    #           agents or removed ones

    def start_for_agent(self, agent: str) -> None:
        """Start processing for the given agent"""
        self._workers[agent] = asyncio.create_task(self._run_for_agent(agent))

    async def _run_task(self, agent: str, task: work.Task, resource_details: ResourceDetails) -> None:
        """Run a task"""
        match task:
            case work.Deploy():
                await self.perform_deploy(agent, resource_details)
            case _:
                print("Nothing here!")

    async def perform_deploy(self, agent: str, resource_details: ResourceDetails) -> None:
        """
        Perform an actual deploy on an agent.

        :param agent:
        :param resource_details:
        """
        # FIXME: WDB to Sander: is the version of the state the correct version?
        #   It may happen that the set of types no longer matches the version?
        # FIXME: code loading interface is not nice like this,
        #   - we may want to track modules per agent, instead of types
        #   - we may also want to track the module version vs the model version
        #       as it avoid the problem of fast chanfing model versions

        async def report_deploy_failure(excn: Exception) -> None:
            res_type = resource_details.id.entity_type
            log_line = data.LogLine.log(
                logging.ERROR,
                "All resources of type `%(res_type)s` failed to load handler code or install handler code "
                "dependencies: `%(error)s`\n%(traceback)s",
                res_type=res_type,
                error=str(excn),
                traceback="".join(traceback.format_tb(excn.__traceback__)),
            )
            await self._client.resource_action_update(
                tid=self._environment,
                resource_ids=[resource_details.rvid],
                action_id=uuid.uuid4(),
                action=ResourceAction.deploy,
                started=datetime.datetime.now().astimezone(),
                finished=datetime.datetime.now().astimezone(),
                messages=[log_line],
                status=const.ResourceState.unavailable,
            )

        # Find code
        code, invalid_resources = await self._code_manager.get_code(
            environment=self._environment, version=self._state.version, resource_types=self._state.get_types_for_agent(agent)
        )

        # Bail out if this failed
        if resource_details.id.entity_type in invalid_resources:
            await report_deploy_failure(invalid_resources[resource_details.id.entity_type])
            return

        # Get executor
        my_executor: executor.Executor = await self._executor_manager.get_executor(agent_name=agent, agent_uri="NO_URI", code=code)
        failed_resources = my_executor.failed_resources

        # Bail out if this failed
        if resource_details.id.entity_type in failed_resources:
            await report_deploy_failure(failed_resources[resource_details.id.entity_type])
            return

        # DEPLOY!!!
        gid = uuid.uuid4()
        # FIXME: reason argument is not used
        await my_executor.execute(gid, resource_details, "New Scheduler initiated action")

    async def _work_once(self, agent: str) -> None:
        task: work.Task = await self._work.agent_queues.queue_get(agent)
        # FIXME[#8008]: skip and reschedule deploy / refresh-fact task if resource marked as update pending?
        if isinstance(task, PoisonPill):
            # wake up and return, queue will be shut down
            return
        resource_details: ResourceDetails
        async with self._scheduler_lock:
            # fetch resource details atomically under lock
            try:
                resource_details = self._state.resources[task.resource]
            except KeyError:
                # Stale resource, can simply be dropped.
                # May occur in rare races between new_version and acquiring the lock we're under here. This race is safe
                # because of this check, and an intrinsic part of the locking design because it's preferred over wider
                # locking for performance reasons.
                return

        await self._run_task(agent, task, resource_details)

        # post-processing
        match task:
            case work.Deploy():
                async with self._scheduler_lock:
                    # refresh resource details for latest model state
                    new_details: Optional[ResourceDetails] = self._state.resources.get(task.resource, None)
                    if new_details is not None and new_details.attribute_hash == resource_details.attribute_hash:
                        # FIXME[#8010]: pass success/failure to notify_provides()
                        # FIXME[#8008]: iff deploy was successful set resource status and deployment result
                        #               in self.state.resources
                        self._work.notify_provides(task)
                    # The deploy that finished has become stale (state has changed since the deploy started).
                    # Nothing to report on a stale deploy.
                    # A new deploy for the current model state will have been queued already.
            case _:
                # nothing to do
                pass
        self._work.agent_queues.task_done(agent)

    async def _run_for_agent(self, agent: str) -> None:
        """Main loop for one agent"""
        while self._running:
            await self._work_once(agent)
