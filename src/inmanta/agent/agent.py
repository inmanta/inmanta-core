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

import abc
import asyncio
import dataclasses
import datetime
import enum
import logging
import os
import random
import time
import traceback
import uuid
from collections.abc import Callable, Coroutine, Iterable, Mapping, Sequence
from concurrent.futures.thread import ThreadPoolExecutor
from logging import Logger
from typing import Any, Collection, Dict, Optional, Union, cast

from inmanta import config, const, data, protocol
from inmanta.agent import config as cfg
from inmanta.agent import executor, forking_executor, in_process_executor
from inmanta.agent.code_manager import CodeManager
from inmanta.agent.executor import ResourceDetails, ResourceInstallSpec
from inmanta.agent.reporting import collect_report
from inmanta.data.model import AttributeStateChange, ResourceIdStr, ResourceType, ResourceVersionIdStr
from inmanta.protocol import SessionEndpoint, methods, methods_v2
from inmanta.resources import Id
from inmanta.types import Apireturn, JsonType
from inmanta.util import CronSchedule, IntervalSchedule, ScheduledTask, TaskMethod, TaskSchedule, add_future, join_threadpools

LOGGER = logging.getLogger(__name__)


class ResourceActionResult:
    def __init__(self, cancel: bool) -> None:
        self.cancel = cancel

    def __add__(self, other: "ResourceActionResult") -> "ResourceActionResult":
        return ResourceActionResult(self.cancel or other.cancel)

    def __str__(self) -> str:
        return "%r" % self.cancel


ResourceActionResultFuture = asyncio.Future[ResourceActionResult]


class ResourceActionBase(abc.ABC):
    """
    Base class for Local and Remote resource actions. Model dependencies between resources
    and inform each other when they're done deploying.
    """

    resource_id: Id
    future: ResourceActionResultFuture
    dependencies: list["ResourceActionBase"]

    def __init__(self, scheduler: "ResourceScheduler", resource_id: Id, gid: uuid.UUID, reason: str) -> None:
        """
        :param gid: A unique identifier to identify a deploy. This is local to this agent.
        """
        self.scheduler: "ResourceScheduler" = scheduler
        self.resource_id: Id = resource_id
        self.future: ResourceActionResultFuture = asyncio.Future()
        # This variable is used to indicate that the future of a ResourceAction will get a value, because of a deploy
        # operation. This variable makes sure that the result cannot be set twice when the ResourceAction is cancelled.
        self.running: bool = False
        self.gid: uuid.UUID = gid
        self.undeployable: Optional[const.ResourceState] = None
        self.reason: str = reason
        self.logger: Logger = self.scheduler.logger

    async def execute(self, dummy: "ResourceActionBase", generation: "dict[ResourceIdStr, ResourceActionBase]") -> None:
        return

    def is_running(self) -> bool:
        return self.running

    def is_done(self) -> bool:
        return self.future.done()

    def cancel(self) -> None:
        if not self.is_running() and not self.is_done():
            self.logger.info("Cancelled deploy of %s %s %s", self.__class__.__name__, self.gid, self.resource_id)
            self.future.set_result(ResourceActionResult(cancel=True))

    def long_string(self) -> str:
        return "{} awaits {}".format(self.resource_id.resource_str(), " ".join([str(aw) for aw in self.dependencies]))

    def __str__(self) -> str:
        status = ""
        if self.is_done():
            status = " Done"
        elif self.is_running():
            status = " Running"

        return self.resource_id.resource_str() + status


class DummyResourceAction(ResourceActionBase):
    def __init__(self, scheduler: "ResourceScheduler", gid: uuid.UUID, reason: str) -> None:
        dummy_id = Id("agent::Dummy", scheduler.name, "type", "dummy")
        super().__init__(scheduler, dummy_id, gid, reason)


class ResourceAction(ResourceActionBase):
    def __init__(
        self,
        scheduler: "ResourceScheduler",
        my_executor: executor.Executor,
        env_id: uuid.UUID,
        resource: ResourceDetails,
        gid: uuid.UUID,
        reason: str,
    ) -> None:
        """
        :param gid: A unique identifier to identify a deploy. This is local to this agent.
        """
        super().__init__(scheduler, resource.id, gid, reason)
        self.resource: ResourceDetails = resource
        self.executor: executor.Executor = my_executor
        self.env_id: uuid.UUID = env_id

    async def execute(self, dummy: "ResourceActionBase", generation: Mapping[ResourceIdStr, ResourceActionBase]) -> None:
        self.logger.log(const.LogLevel.TRACE.to_int, "Entering %s %s", self.gid, self.resource)
        self.dependencies = [generation[resource_id.resource_str()] for resource_id in self.resource.requires]
        waiters = [x.future for x in self.dependencies]
        waiters.append(dummy.future)
        # Explicit cast is required because mypy has issues with * and generics
        results: list[ResourceActionResult] = cast(list[ResourceActionResult], await asyncio.gather(*waiters))

        if self.undeployable:
            self.running = True
            try:
                if self.is_done():
                    # Action is cancelled
                    self.logger.log(const.LogLevel.TRACE.to_int, "%s %s is no longer active", self.gid, self.resource)
                    return
                result = sum(results, ResourceActionResult(cancel=False))
                if result.cancel:
                    # self.running will be set to false when self.cancel is called
                    # Only happens when global cancel has not cancelled us but our predecessors have already been cancelled
                    return
                self.future.set_result(ResourceActionResult(cancel=False))
                return
            finally:
                self.running = False

        async with self.scheduler.ratelimiter:
            self.running = True

            try:
                if self.is_done():
                    # Action is cancelled
                    self.logger.log(const.LogLevel.TRACE.to_int, "%s %s is no longer active", self.gid, self.resource)
                    return

                result = sum(results, ResourceActionResult(cancel=False))

                if result.cancel:
                    # self.running will be set to false when self.cancel is called
                    # Only happens when global cancel has not cancelled us but our predecessors have already been cancelled
                    return

                await self.executor.execute(
                    gid=self.gid,
                    resource_details=self.resource,
                    reason=self.reason,
                )

                self.future.set_result(ResourceActionResult(cancel=False))
            finally:
                self.running = False


class RemoteResourceAction(ResourceActionBase):
    def __init__(self, scheduler: "ResourceScheduler", resource_id: Id, gid: uuid.UUID, reason: str) -> None:
        super().__init__(scheduler, resource_id, gid, reason)

    async def execute(self, dummy: "ResourceActionBase", generation: "Dict[ResourceIdStr, ResourceActionBase]") -> None:
        pass

    def notify(
        self,
        status: const.ResourceState,
    ) -> None:
        if not self.future.done():
            self.status = status
            self.future.set_result(ResourceActionResult(cancel=False))


@dataclasses.dataclass
class DeployRequest:
    """
    A request to perform a deploy

    :param is_full_deploy: is this a full deploy or incremental deploy?
    :param is_periodic: is this deploy triggered by a timer?
    :param reason: textual description of the deployment
    """

    is_full_deploy: bool
    is_periodic: bool
    reason: str

    def interrupt(self, other: "DeployRequest") -> "DeployRequest":
        """Interrupt this deploy for the other and produce a new request for future rescheduling of this deploy"""
        return DeployRequest(
            self.is_full_deploy, self.is_periodic, f"Restarting run '{self.reason}', interrupted for '{other.reason}'"
        )


class DeployRequestAction(str, enum.Enum):
    """
    When a deploy is running and a new request arrives, we can take the following actions
    """

    ignore = "ignore"
    """ ignore the new request, continue with the exiting deploy """
    terminate = "terminate"
    """ terminate the current deploy, start the new one """
    defer = "defer"
    """ defer the new request,  continue with the exiting deploy, start the new one when the current deploy is done"""
    interrupt = "interrupt"
    """ interrupt the current deploy: cancel it, start the new one and restart the current deploy when the new one is done"""


# Two letter abbreviations to make table line up
# N normal
# P periodic
# F full
# I incremental
NF = (True, False)
NI = (False, False)
PF = (True, True)
PI = (False, True)
# shorten table
ignore = DeployRequestAction.ignore
terminate = DeployRequestAction.terminate
defer = DeployRequestAction.defer
interrupt = DeployRequestAction.interrupt

# This matrix describes what do when a new DeployRequest enters before the old one is done
# Format is (old_is_repair, old_is_periodic), (new_is_repair, new_is_periodic)
# The underlying idea is that
# 1. periodic deploys have no time pressure, they can be delayed
# 2. non-periodic deploy should run as soon as possible
# 3. non-periodic incremental deploys take precedence over repairs (as they are smaller)
# 4. Periodic repairs should not interrupt each other to prevent restart loops
# 5. Periodic repairs take precedence over periodic incremental deploys.
# These rules do not full specify the matrix! They are the rules we have to follow.
# A subtle detail is that when we do defer or interrupt, we only over keep one.
# So if a previous deferred run exists, it will be silently dropped
# But, we only defer or interrupt full deploys
# As such, we will always execute a full deploy
# (it may oscillate between periodic and not, but it will execute)

deploy_response_matrix = {
    # ((old_is_repair, old_is_periodic), (new_is_repair, new_is_periodic))
    # Periodic restart loops: Full periodic is never interrupted by periodic
    (PF, PF): ignore,  # Full periodic ignores full periodic to prevent restart loops
    (NF, PF): ignore,  # Full ignores full periodic to avoid restart loops
    (PF, PI): ignore,  # Full periodic ignores periodic increment to prevent restart loops
    (PI, PF): terminate,  # Incremental periodic terminated by full periodic: upgrade to full
    (PI, NF): terminate,  # Incremental periodic terminated by full: upgrade to full
    # Same terminates same: focus on the new one
    (PF, NF): terminate,  # Full periodic terminated by Full
    (NF, NF): terminate,  # Full terminated by Full
    # Increment * terminates Increment *
    (PI, PI): terminate,
    (PI, NI): terminate,
    (NI, PI): terminate,
    (NI, NI): terminate,
    (NI, PF): defer,  # Incremental defers full periodic
    (NI, NF): defer,  # Incremental defers full
    # Non-periodic is always executed asap
    (PF, NI): interrupt,  # periodic full interrupted by increment
    (NF, NI): interrupt,  # full interrupted by increment
    # Prefer the normal full over PI
    (NF, PI): ignore,  # full ignores periodic increment
}


class ResourceScheduler:
    """Class responsible for managing sequencing of actions performed by the agent.

    State of the last run is not removed after the run but remains.

    By not removing e.g. the generation,
    1 - the class is always in a valid state
    2 - we don't need to figure out exactly when a run is done
    """

    def __init__(self, agent: "AgentInstance", env_id: uuid.UUID, name: str) -> None:
        self.generation: dict[ResourceIdStr, ResourceActionBase] = {}
        self.cad: dict[str, RemoteResourceAction] = {}
        self._env_id = env_id
        self.agent = agent
        self.name = name
        self.ratelimiter = agent.ratelimiter
        self.version: int = 0

        self.running: Optional[DeployRequest] = None
        self.deferred: Optional[DeployRequest] = None
        self.cad_resolver: Optional[asyncio.Task[None]] = None

        self.logger: Logger = agent.logger

    def get_scheduled_resource_actions(self) -> list[ResourceActionBase]:
        return list(self.generation.values())

    def finished(self) -> bool:
        for resource_action in self.generation.values():
            if not resource_action.is_done():
                return False
        return True

    def cancel(self) -> None:
        """
        Cancel all scheduled deployments.
        """
        for ra in self.generation.values():
            ra.cancel()
        if self.cad_resolver is not None:
            self.cad_resolver.cancel()
            self.cad_resolver = None
        self.generation = {}
        self.cad = {}

    def reload(
        self,
        resources: Sequence[ResourceDetails],
        undeployable: dict[ResourceVersionIdStr, const.ResourceState],
        new_request: DeployRequest,
        executor: executor.Executor,
    ) -> None:
        """
        Schedule a new set of resources for execution.

        :param resources: The set of resource should be closed, the scheduler assumes that all resource referenced are in the
                          set or on another agent.

        **This method should only be called under critical_ratelimiter lock!**
        """
        # First determined if we should start and if the current run should be resumed
        if not self.finished():
            # we are still running
            assert self.running is not None
            # Get correct action
            response = deploy_response_matrix[
                ((self.running.is_full_deploy, self.running.is_periodic), (new_request.is_full_deploy, new_request.is_periodic))
            ]
            # Execute action
            if response == DeployRequestAction.terminate:
                self.logger.info("Terminating run '%s' for '%s'", self.running.reason, new_request.reason)
            elif response == DeployRequestAction.defer:
                self.logger.info("Deferring run '%s' for '%s'", new_request.reason, self.running.reason)
                self.deferred = new_request
                return
            elif response == DeployRequestAction.ignore:
                self.logger.info("Ignoring new run '%s' in favor of current '%s'", new_request.reason, self.running.reason)
                return
            elif response == DeployRequestAction.interrupt:
                self.logger.info("Interrupting run '%s' for '%s'", self.running.reason, new_request.reason)
                # Can overwrite, acceptable
                self.deferred = self.running.interrupt(new_request)
            else:
                assert False, f"Unexpected DeployRequestAction {response}"

            # cancel old run
            self.cancel()

        # start new run
        self.running = new_request
        self.version = resources[0].model_version
        gid = uuid.uuid4()
        self.logger.info("Running %s for reason: %s", gid, self.running.reason)

        # re-generate generation
        self.generation = {}

        for resource in resources:
            local_resource_action = ResourceAction(self, executor, self._env_id, resource, gid, self.running.reason)
            # mark undeployable
            if resource.rvid in undeployable:
                local_resource_action.undeployable = undeployable[resource.rvid]
            self.generation[resource.rid] = local_resource_action

        # hook up Cross Agent Dependencies
        cross_agent_dependencies: set[Id] = {q for r in resources for q in r.requires if q.get_agent_name() != self.name}
        cads_by_rid: dict[ResourceIdStr, RemoteResourceAction] = {}
        for cad in cross_agent_dependencies:
            ra = RemoteResourceAction(self, cad, gid, self.running.reason)
            self.cad[str(cad)] = ra
            rid = cad.resource_str()
            cads_by_rid[rid] = ra
            self.generation[rid] = ra

        if cads_by_rid:
            self.cad_resolver = self.agent.process.add_background_task(self.resolve_cads(self.version, cads_by_rid))

        # Create dummy to give start signal
        dummy = DummyResourceAction(self, gid, self.running.reason)
        # Dispatch all actions
        # Will block on dependencies and dummy
        for resource_action in self.generation.values():
            add_future(resource_action.execute(dummy, self.generation))

        # Listen for completion
        self.agent.process.add_background_task(self.mark_deployment_as_finished(self.generation.values()))

        # Start running
        dummy.future.set_result(ResourceActionResult(cancel=False))

    async def mark_deployment_as_finished(self, resource_actions: Iterable[ResourceActionBase]) -> None:
        # This method is executing as a background task. As such, it will get cancelled when the agent is stopped.
        # Because the asyncio.gather() call propagates cancellation, we shield the ResourceActionBase.future.
        # Cancellation of these futures is handled by the ResourceActionBase.cancel() method. Not shielding them
        # would cause the result of the future to be set twice, which results in an undesired InvalidStateError.
        await asyncio.gather(*[asyncio.shield(resource_action.future) for resource_action in resource_actions])
        async with self.agent.critical_ratelimiter:
            if not self.finished():
                return
            if self.deferred is not None:
                self.logger.info("Resuming run '%s'", self.deferred.reason)
                self.agent.process.add_background_task(self.agent.get_latest_version_for_agent(self.deferred))
                self.deferred = None

    async def resolve_cads(self, version: int, cads: dict[ResourceIdStr, RemoteResourceAction]) -> None:
        """Batch resolve all CAD's"""
        async with self.agent.process.cad_ratelimiter:
            result = await self.get_client().resources_status(
                tid=self.agent._env_id,
                version=version,
                rids=list(cads.keys()),
            )
            if result.code != 200 or result.result is None:
                LOGGER.error("Failed to get the status for remote resources %s (%s)", list(cads.keys()), result.result)
                return

            for rid_raw, status_raw in result.result["data"].items():
                status = const.ResourceState[status_raw]
                rra = cads[rid_raw]
                if status not in const.TRANSIENT_STATES:
                    rra.notify(status)

    def notify_ready(
        self,
        resourceid: ResourceVersionIdStr,
        state: const.ResourceState,
        change: const.Change,
        changes: dict[ResourceVersionIdStr, dict[str, AttributeStateChange]],
    ) -> None:
        if resourceid not in self.cad:
            # received CAD notification for which no resource are waiting, so return
            return
        self.cad[resourceid].notify(state)

    def dump(self) -> None:
        print("Waiting:")
        for r in self.generation.values():
            print(r.long_string())

    def get_client(self) -> protocol.Client:
        return self.agent.get_client()


class AgentInstance:
    _get_resource_timeout: float
    _get_resource_duration: float

    def __init__(self, process: "Agent", name: str, uri: str, *, ensure_deploy_on_start: bool = False) -> None:
        self.process = process
        self.name = name
        self._uri = uri

        self.logger: Logger = LOGGER.getChild(self.name)

        # the lock for changing the current ongoing deployment
        self.critical_ratelimiter = asyncio.Semaphore(1)
        # lock for dryrun tasks
        self.dryrunlock = asyncio.Semaphore(1)

        # multi threading control
        self.ratelimiter = asyncio.Semaphore(1)

        if process.environment is None:
            raise Exception("Agent instance started without a valid environment id set.")

        self._env_id: uuid.UUID = process.environment
        self.sessionid: uuid.UUID = process.sessionid

        # init
        self._nq = ResourceScheduler(self, self._env_id, name)
        self._time_triggered_actions: set[ScheduledTask] = set()
        self._enabled = False
        self._stopped = False

        # do regular deploys
        self._deploy_interval = cfg.agent_deploy_interval.get()
        deploy_splay_time = cfg.agent_deploy_splay_time.get()
        self._deploy_splay_value = random.randint(0, deploy_splay_time)

        # do regular repair runs
        self._repair_interval: Union[int, str] = cfg.agent_repair_interval.get()
        repair_splay_time = cfg.agent_repair_splay_time.get()
        self._repair_splay_value = random.randint(0, repair_splay_time)

        self._getting_resources = False
        self._get_resource_timeout = 0

        # If this instance has no deploy timer set, deploy anyway
        # This is used for agents that are started via the agentmap
        # To give smooth deploy experience, we want these agents to start immediately.
        self.ensure_deploy_on_start = ensure_deploy_on_start

        self.executor_manager: executor.ExecutorManager[executor.Executor] = process.executor_manager
        self._executors_to_join: list[executor.Executor] = []

    async def stop(self) -> None:
        self._stopped = True
        self._enabled = False
        self._disable_time_triggers()
        self._nq.cancel()
        self._executors_to_join = await self.executor_manager.stop_for_agent(self.name)

    async def join(self, thread_pool_finalizer: list[ThreadPoolExecutor]) -> None:
        """
        Called after stop to ensure complete shutdown

        :param thread_pool_finalizer: all threadpools that should be joined should be added here.
        """
        assert self._stopped
        await self.executor_manager.join(thread_pool_finalizer, const.SHUTDOWN_GRACE_IOLOOP * 0.9)
        await asyncio.gather(*(executor.join() for executor in self._executors_to_join))

    @property
    def environment(self) -> uuid.UUID:
        return self._env_id

    def get_client(self) -> protocol.SessionClient:
        return self.process._client

    @property
    def uri(self) -> str:
        return self._uri

    def is_enabled(self) -> bool:
        return self._enabled

    def is_stopped(self) -> bool:
        return self._stopped

    def unpause(self) -> Apireturn:
        if self._stopped:
            return 403, "Cannot unpause stopped agent instance"

        if self.is_enabled():
            return 200, "already running"

        self.logger.info("Agent assuming primary role for %s", self.name)

        self._enable_time_triggers()
        self._enabled = True
        return 200, "unpaused"

    def pause(self, reason: str = "agent lost primary role") -> Apireturn:
        if not self.is_enabled():
            return 200, "already paused"

        self.logger.info("Agent %s stopped because %s", self.name, reason)

        self._disable_time_triggers()
        self._enabled = False

        # Cancel the ongoing deployment if exists
        self._nq.cancel()

        return 200, "paused"

    def _enable_time_triggers(self) -> None:
        async def deploy_action() -> None:
            now = datetime.datetime.now().astimezone()
            await self.get_latest_version_for_agent(
                DeployRequest(
                    reason="Periodic deploy started at %s" % (now.strftime(const.TIME_LOGFMT)),
                    is_full_deploy=False,
                    is_periodic=True,
                )
            )

        async def repair_action() -> None:
            now = datetime.datetime.now().astimezone()
            await self.get_latest_version_for_agent(
                DeployRequest(
                    reason="Repair run started at %s" % (now.strftime(const.TIME_LOGFMT)),
                    is_full_deploy=True,
                    is_periodic=True,
                )
            )

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
                self.logger.info(
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
                self.logger.info("Scheduling periodic %s with cron expression '%s'", kind, interval)
                cron_schedule = CronSchedule(cron=interval)
                self._enable_time_trigger(action, cron_schedule)
                return True
            return False

        now = datetime.datetime.now().astimezone()
        if self.ensure_deploy_on_start:
            self.process.add_background_task(
                self.get_latest_version_for_agent(
                    DeployRequest(
                        reason="Initial deploy started at %s" % (now.strftime(const.TIME_LOGFMT)),
                        is_full_deploy=False,
                        is_periodic=False,
                    )
                )
            )
            self.ensure_deploy_on_start = False

        periodic_schedule("deploy", deploy_action, self._deploy_interval, self._deploy_splay_value)
        periodic_schedule("repair", repair_action, self._repair_interval, self._repair_splay_value)

    def _enable_time_trigger(self, action: TaskMethod, schedule: TaskSchedule) -> None:
        self.process._sched.add_action(action, schedule)
        self._time_triggered_actions.add(ScheduledTask(action=action, schedule=schedule))

    def _disable_time_triggers(self) -> None:
        for task in self._time_triggered_actions:
            self.process._sched.remove(task)
        self._time_triggered_actions.clear()

    def notify_ready(
        self,
        resourceid: ResourceVersionIdStr,
        state: const.ResourceState,
        change: const.Change,
        changes: dict[ResourceVersionIdStr, dict[str, AttributeStateChange]],
    ) -> None:
        self._nq.notify_ready(resourceid, state, change, changes)

    def _can_get_resources(self) -> bool:
        if self._getting_resources:
            self.logger.info("Attempting to get resource while get is in progress")
            return False
        if time.time() < self._get_resource_timeout:
            self.logger.info(
                "Attempting to get resources during backoff %g seconds left, last download took %f seconds",
                self._get_resource_timeout - time.time(),
                self._get_resource_duration,
            )
            return False
        return True

    async def get_latest_version_for_agent(
        self,
        deploy_request: DeployRequest,
    ) -> None:
        """
        Get the latest version for the given agent (this is also how we are notified)

        :param reason: the reason this deploy was started
        """
        if not self._can_get_resources():
            self.logger.warning("%s aborted by rate limiter", deploy_request.reason)
            return

        async with self.critical_ratelimiter:
            if not self._can_get_resources():
                self.logger.warning("%s aborted by rate limiter", deploy_request.reason)
                return

            self.logger.debug("Getting latest resources for %s", deploy_request.reason)
            self._getting_resources = True
            start = time.time()
            try:
                result = await self.get_client().get_resources_for_agent(
                    tid=self._env_id, agent=self.name, incremental_deploy=not deploy_request.is_full_deploy
                )
            finally:
                self._getting_resources = False
            end = time.time()
            self._get_resource_duration = end - start
            self._get_resource_timeout = cfg.agent_get_resource_backoff.get() * self._get_resource_duration + end
            if result.code == 404:
                self.logger.info("No released configuration model version available for %s", deploy_request.reason)
            elif result.code == 409:
                self.logger.warning("We are not currently primary during %s: %s", deploy_request.reason, result.result)
            elif result.code != 200 or result.result is None:
                self.logger.warning("Got an error while pulling resources for %s. %s", deploy_request.reason, result.result)

            else:
                self.logger.debug("Pulled %d resources because %s", len(result.result["resources"]), deploy_request.reason)
                if len(result.result["resources"]) > 0:
                    undeployable, resources, executor = await self.prepare_resources(
                        model_version=result.result["version"],
                        action=const.ResourceAction.deploy,
                        resource_batch=result.result["resources"],
                        resource_types=set(result.result["resource_types"]),
                    )
                    if len(resources) > 0 and executor is not None:
                        self._nq.reload(resources, undeployable, deploy_request, executor)

    async def dryrun(self, dry_run_id: uuid.UUID, version: int) -> Apireturn:
        self.process.add_background_task(self.do_run_dryrun(version, dry_run_id))
        return 200

    async def do_run_dryrun(self, version: int, dry_run_id: uuid.UUID) -> None:
        async with self.dryrunlock:
            async with self.ratelimiter:
                response = await self.get_client().get_resources_for_agent(tid=self._env_id, agent=self.name, version=version)
                if response.code == 404:
                    self.logger.warning("Version %s does not exist, can not run dryrun", version)
                    return

                elif response.code != 200 or response.result is None:
                    self.logger.warning("Got an error while pulling resources and version %s", version)
                    return

                undeployable, resource_refs, executor = await self.prepare_resources(
                    model_version=version,
                    action=const.ResourceAction.dryrun,
                    resource_batch=response.result["resources"],
                    resource_types=set(response.result["resource_types"]),
                )
                deployable_resources: list[ResourceDetails] = []
                for resource in resource_refs:
                    if resource.rvid in undeployable:
                        self.logger.error(
                            "Skipping dryrun for resource %s because it is in undeployable state %s",
                            resource.rvid,
                            undeployable[resource.rvid],
                        )
                        await self.get_client().dryrun_update(
                            tid=self.environment,
                            id=dry_run_id,
                            resource=resource.rvid,
                            changes={"handler": {"current": "FAILED", "desired": "Resource is in an undeployable state"}},
                        )
                    else:
                        deployable_resources.append(resource)
                if deployable_resources:
                    assert executor is not None
                    await executor.dry_run(deployable_resources, dry_run_id)

    async def get_facts(self, resource: JsonType) -> Apireturn:
        async with self.ratelimiter:
            undeployable, resource_refs, executor = await self.prepare_resources(
                model_version=resource["model"],
                action=const.ResourceAction.getfact,
                resource_batch=[resource],
                resource_types={resource["resource_type"]},
            )

            if undeployable or not resource_refs:
                self.logger.warning(
                    "Cannot retrieve fact for %s because resource is undeployable or code could not be loaded", resource["id"]
                )
                return 500

            assert executor is not None
            return await executor.get_facts(resource_refs[0])

    async def setup_executor(
        self, model_version: int, resource_types: set[ResourceType]
    ) -> tuple[Optional[executor.Executor], executor.FailedResources]:
        """
        Set up an executor for a given version of a model. This executor is the interface
        to interact with the resources.

        :param model_version: model version being loaded
        :param resource_types: set of all resource types we want to be able to interact with via this executor
        :return: A tuple of:
            - The executor (if creation/retrieval was successful)
            - invalid_resource_types: resource types for which we're missing a handler or pip config
                or for which handler code installation failed
        """
        code: Collection[ResourceInstallSpec]

        # Resource types for which no handler code exist for the given model_version
        # or for which the pip config couldn't be retrieved
        code, invalid_resources = await self.process.get_code(self._env_id, model_version, resource_types)

        try:
            current_executor = await self.executor_manager.get_executor(self.name, self.uri, code)
            # Resource types for which an error occurred during handler code installation
            failed_resources = current_executor.failed_resources
        except Exception as e:
            logging.warning("Could not set up executor for %s", self.name, exc_info=True)
            current_executor = None
            # If the failed resource type is not present in `failed_resources`, then we add it with the current exception
            # If it was already present, we only keep the old error
            failed_resources = {
                resource_type: Exception(f"Could not set up executor for {self.name}: {e}").with_traceback(e.__traceback__)
                for resource_type in resource_types.difference(set(invalid_resources.keys()))
            }

        invalid_resources.update(failed_resources)

        return current_executor, invalid_resources

    async def prepare_resources(
        self,
        model_version: int,
        action: const.ResourceAction,
        resource_batch: list[JsonType],
        resource_types: set[ResourceType],
    ) -> tuple[dict[ResourceVersionIdStr, const.ResourceState], list[ResourceDetails], Optional[executor.Executor]]:
        """
        This method is expected to be called as an initialization step when interacting with resources.
        It prepares resources by parsing them into ResourceDetails and setting up an executor that will
        be the interface to perform further work on them.

        :param model_version: prepare resources belonging to this model version
        :param action: the action these resources are being prepared for
        :param resource_batch: list of resources in serialized form: a dict with information about
            this resource and its desired state
        :param resource_types: set of ALL resource types composing this version of the model
        :return: Tuple of:

            - undeployable: resources for which code loading failed
            - loaded_resources: ALL resources from this batch
            - the executor: with relevant handler code loaded, can be None if all are undeployable

        """
        started = datetime.datetime.now().astimezone()

        executor, invalid_resources = await self.setup_executor(model_version, resource_types)

        loaded_resources: list[ResourceDetails] = []
        undeployable: dict[ResourceVersionIdStr, const.ResourceState] = {}

        # {resource_type -> (set{resource_ids}, LogLine)}
        failed_resources: dict[str, tuple[set[str], data.LogLine]] = dict()
        for res in resource_batch:
            res_id = res["id"]
            res_type = res["resource_type"]

            if res_type not in invalid_resources:
                loaded_resources.append(ResourceDetails.from_json(res))

                state = const.ResourceState[res["status"]]
                if state in const.UNDEPLOYABLE_STATES:
                    undeployable[res_id] = state
            else:
                if res_type not in failed_resources:
                    failed_resources[res_type] = (
                        {res_id},
                        data.LogLine.log(
                            logging.ERROR,
                            "All resources of type `%(res_type)s` failed to load handler code or install handler code "
                            "dependencies: `%(error)s`\n%(traceback)s",
                            res_type=res_type,
                            error=str(invalid_resources[res_type]),
                            traceback="".join(traceback.format_tb(invalid_resources[res_type].__traceback__)),
                        ),
                    )
                else:
                    failed_resources[res_type][0].add(res_id)
                undeployable[res_id] = const.ResourceState.unavailable
                loaded_resources.append(ResourceDetails.from_json(res))

        if len(failed_resources) > 0:
            for resource_type, (failed_resource_ids, log_line) in failed_resources.items():
                await self.get_client().resource_action_update(
                    tid=self._env_id,
                    resource_ids=list(failed_resource_ids),
                    action_id=uuid.uuid4(),
                    action=action,
                    started=started,
                    finished=datetime.datetime.now().astimezone(),
                    messages=[log_line],
                    status=const.ResourceState.unavailable,
                )
        return undeployable, loaded_resources, executor


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
        hostname: Optional[str] = None,
        agent_map: Optional[dict[str, str]] = None,
        code_loader: bool = True,
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

        self.hostname = hostname
        self.ratelimiter = asyncio.Semaphore(1)
        # Number of in flight requests for resolving CAD's
        self.cad_ratelimiter = asyncio.Semaphore(3)
        self.thread_pool = ThreadPoolExecutor(1, thread_name_prefix="mainpool")

        self._storage = self.check_storage()

        if environment is None:
            environment = cfg.environment.get()
            if environment is None:
                raise Exception("The agent requires an environment to be set.")
        self.set_environment(environment)

        self._instances: dict[str, AgentInstance] = {}
        self._instances_lock = asyncio.Lock()

        # Cache to prevent re-fetching the same resource-version
        self._code_cache: dict[tuple[str, int], ResourceInstallSpec] = {}

        self.agent_map: Optional[dict[str, str]] = agent_map

        self.code_manager = CodeManager(self._client)

        remote_executor = cfg.agent_executor_mode.get() == cfg.AgentExecutorMode.forking
        can_have_remote_executor = code_loader

        # Mechanism to speed up tests using the old (<= iso7) agent mechanism
        # by avoiding spawning a virtual environment.
        self._code_loader = code_loader

        self.executor_manager: executor.ExecutorManager[executor.Executor]
        if remote_executor and can_have_remote_executor:
            LOGGER.info("Selected forking agent executor mode")
            assert self.environment is not None  # Mypy
            self.executor_manager = forking_executor.MPManager(
                self.thread_pool,
                self.sessionid,
                self.environment,
                config.log_dir.get(),
                self._storage["executor"],
                LOGGER.level,
                False,
            )
        else:
            LOGGER.info("Selected threaded agent executor mode")
            self.executor_manager = in_process_executor.InProcessExecutorManager(
                environment,
                self._client,
                asyncio.get_event_loop(),
                LOGGER,
                self.thread_pool,
                self._storage["code"],
                self._storage["env"],
                code_loader,
            )

    async def _init_agent_map(self) -> None:
        if cfg.use_autostart_agent_map.get():
            LOGGER.info("Using the autostart_agent_map configured on the server")
            env_id = self.get_environment()
            assert env_id is not None
            result = await self._client.environment_setting_get(env_id, data.AUTOSTART_AGENT_MAP)
            if result.code != 200 or result.result is None:
                error_msg = result.result["message"] if result.result else ""
                LOGGER.error("Failed to retrieve the autostart_agent_map setting from the server. %s", error_msg)
                raise CouldNotConnectToServer()
            self.agent_map = result.result["data"]["settings"][data.AUTOSTART_AGENT_MAP]
        elif self.agent_map is None:
            self.agent_map = dict(cfg.agent_map.get())

    async def _init_endpoint_names(self) -> None:
        assert self.agent_map is not None
        endpoints: Iterable[str] = (
            [self.hostname]
            if self.hostname is not None
            else (
                self.agent_map.keys()
                if cfg.use_autostart_agent_map.get()
                else (name if "$" not in name else name.replace("$node-name", self.node_name) for name in cfg.agent_names.get())
            )
        )
        for endpoint in endpoints:
            await self.add_end_point_name(endpoint)

    async def stop(self) -> None:
        await super().stop()
        await self.executor_manager.stop()

        threadpools_to_join = [self.thread_pool]

        await self.executor_manager.join(threadpools_to_join, const.SHUTDOWN_GRACE_IOLOOP * 0.9)

        self.thread_pool.shutdown(wait=False)
        for instance in self._instances.values():
            await instance.stop()
            await instance.join(threadpools_to_join)

        await join_threadpools(threadpools_to_join)

    async def start_connected(self) -> None:
        """
        This method is required because:
            1) The client transport is required to retrieve the autostart_agent_map from the server.
            2) _init_endpoint_names() needs to be an async method and async calls are not possible in a constructor.
        """
        init_agentmap_succeeded = False
        while not init_agentmap_succeeded:
            try:
                await self._init_agent_map()
                init_agentmap_succeeded = True
            except CouldNotConnectToServer:
                await asyncio.sleep(1)
        await self._init_endpoint_names()

    async def start(self) -> None:
        # cache reference to THIS ioloop for handlers to push requests on it
        self._io_loop = asyncio.get_running_loop()
        await super().start()
        await self.executor_manager.start()

    async def add_end_point_name(self, name: str) -> None:
        async with self._instances_lock:
            await self._add_end_point_name(name)

    async def _add_end_point_name(self, name: str, *, ensure_deploy_on_start: bool = False) -> None:
        """
        Note: always call under _instances_lock
        """
        LOGGER.info("Adding endpoint %s", name)
        await super().add_end_point_name(name)

        # Make mypy happy
        assert self.agent_map is not None

        hostname = "local:"
        if name in self.agent_map:
            hostname = self.agent_map[name]

        self._instances[name] = AgentInstance(self, name, hostname, ensure_deploy_on_start=ensure_deploy_on_start)

    async def remove_end_point_name(self, name: str) -> None:
        async with self._instances_lock:
            await self._remove_end_point_name(name)

    async def _remove_end_point_name(self, name: str) -> None:
        """
        Note: always call under _instances_lock
        """
        LOGGER.info("Removing endpoint %s", name)
        await super().remove_end_point_name(name)

        agent_instance = self._instances[name]
        del self._instances[name]
        await agent_instance.stop()

    @protocol.handle(methods_v2.update_agent_map)
    async def update_agent_map(self, agent_map: dict[str, str]) -> None:
        if not cfg.use_autostart_agent_map.get():
            LOGGER.warning(
                "Agent received an update_agent_map() trigger, but agent is not running with "
                "the use_autostart_agent_map option."
            )
        else:
            LOGGER.debug("Received update_agent_map() trigger with agent_map %s", agent_map)
            await self._update_agent_map(agent_map)

    async def _update_agent_map(self, agent_map: dict[str, str]) -> None:
        if "internal" not in agent_map:
            LOGGER.warning(
                "Agent received an update_agent_map() trigger without internal agent in the agent_map %s",
                agent_map,
            )
            agent_map = {"internal": "local:", **agent_map}

        async with self._instances_lock:
            self.agent_map = agent_map
            # Add missing agents
            agents_to_add = [agent_name for agent_name in self.agent_map.keys() if agent_name not in self._instances]
            # Remove agents which are not present in agent-map anymore
            agents_to_remove = [agent_name for agent_name in self._instances.keys() if agent_name not in self.agent_map]
            # URI was updated
            update_uri_agents = []
            for agent_name, uri in self.agent_map.items():
                if agent_name not in self._instances:
                    continue
                current_uri = self._instances[agent_name].uri
                if current_uri != uri:
                    LOGGER.info("Updating the URI of the endpoint %s from %s to %s", agent_name, current_uri, uri)
                    update_uri_agents.append(agent_name)

            updated_uri_agents_to_enable = [
                agent_name for agent_name in update_uri_agents if self._instances[agent_name].is_enabled()
            ]

            to_be_gathered = [self._add_end_point_name(agent_name, ensure_deploy_on_start=True) for agent_name in agents_to_add]
            to_be_gathered += [self._remove_end_point_name(agent_name) for agent_name in agents_to_remove + update_uri_agents]
            await asyncio.gather(*to_be_gathered)
            # Re-add agents with updated URI
            await asyncio.gather(
                *[self._add_end_point_name(agent_name, ensure_deploy_on_start=True) for agent_name in update_uri_agents]
            )
            # Enable agents with updated URI that were enabled before
            for agent_to_enable in updated_uri_agents_to_enable:
                self.unpause(agent_to_enable)

    def unpause(self, name: str) -> Apireturn:
        instance = self._instances.get(name)
        if not instance:
            return 404, "No such agent"

        return instance.unpause()

    def pause(self, name: str) -> Apireturn:
        instance = self._instances.get(name)
        if not instance:
            return 404, "No such agent"

        return instance.pause()

    @protocol.handle(methods.set_state)
    async def set_state(self, agent: str, enabled: bool) -> Apireturn:
        if enabled:
            return self.unpause(agent)
        else:
            return self.pause(agent)

    async def on_reconnect(self) -> None:
        if cfg.use_autostart_agent_map.get():
            # When the internal agent doesn't have a session with the server, it doesn't receive notifications
            # about updates to the autostart_agent_map environment setting. On reconnect the autostart_agent_map
            # is fetched from the server to resolve this inconsistency.
            result = await self._client.environment_setting_get(tid=self.get_environment(), id=data.AUTOSTART_AGENT_MAP)
            if result.code == 200 and result.result is not None:
                agent_map = result.result["data"]["settings"][data.AUTOSTART_AGENT_MAP]
                await self._update_agent_map(agent_map=agent_map)
            else:
                LOGGER.warning("Could not get environment setting %s from server", data.AUTOSTART_AGENT_MAP)
        for name in self._instances.keys():
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
        LOGGER.warning("Connection to server lost, taking agents offline")
        for agent_instance in self._instances.values():
            agent_instance.pause("Connection to server lost")

    async def get_code(
        self, environment: uuid.UUID, version: int, resource_types: Collection[ResourceType]
    ) -> tuple[Collection[ResourceInstallSpec], executor.FailedResources]:
        """
        Get the collection of installation specifications (i.e. pip config, python package dependencies,
        Inmanta modules sources) required to deploy a given version for the provided resource types.

        :return: Tuple of:
            - collection of ResourceInstallSpec for resource_types with valid handler code and pip config
            - set of invalid resource_types (no handler code and/or invalid pip config)
        """
        if not self._code_loader:
            return [], {}

        return await self.code_manager.get_code(environment, version, resource_types)

    @protocol.handle(methods.trigger, env="tid", agent="id")
    async def trigger_update(self, env: uuid.UUID, agent: str, incremental_deploy: bool) -> Apireturn:
        """
        Trigger an update
        """
        instance = self._instances.get(agent)

        if not instance:
            return 200

        if not instance.is_enabled():
            return 500, "Agent is not _enabled"

        LOGGER.info("Agent %s got a trigger to update in environment %s", agent, env)
        self.add_background_task(
            instance.get_latest_version_for_agent(
                DeployRequest(
                    is_full_deploy=not incremental_deploy,
                    is_periodic=False,
                    reason="call to trigger_update",
                )
            )
        )
        return 200

    @protocol.handle(methods.trigger_read_version, env="tid")
    async def read_version(self, env: uuid.UUID) -> Apireturn:
        """
        Send a notification to the agent that a new version has been released
        """
        pass

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
        if env != self._env_id:
            LOGGER.error(
                "The agent process for the environment %s has received a cross agent dependency event that was intended for "
                "another environment %s. It originated from the resource: %s, that is in state: %s",
                self._env_id,
                env,
                resource,
                state,
            )
            return 200

        instance = self._instances.get(agent)
        if not instance:
            LOGGER.warning(
                "The agent process for the environment %s has received a cross agent dependency event that was intended for "
                "an agent that is not present here %s. It originated from the resource: %s, that is in state: %s",
                self._env_id,
                agent,
                resource,
                state,
            )
            return 200

        LOGGER.debug(
            "Agent %s got a resource event: tid: %s, agent: %s, resource: %s, state: %s", agent, env, agent, resource, state
        )
        instance.notify_ready(resource, state, change, changes)

        return 200

    @protocol.handle(methods.do_dryrun, env="tid", dry_run_id="id")
    async def run_dryrun(self, env: uuid.UUID, dry_run_id: uuid.UUID, agent: str, version: int) -> Apireturn:
        """
        Run a dryrun of the given version
        """
        assert env == self._env_id

        instance = self._instances.get(agent)
        if not instance:
            return 200

        LOGGER.info("Agent %s got a trigger to run dryrun %s for version %s in environment %s", agent, dry_run_id, version, env)

        return await instance.dryrun(dry_run_id, version)

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

    @protocol.handle(methods.get_parameter, env="tid")
    async def get_facts(self, env: uuid.UUID, agent: str, resource: dict[str, Any]) -> Apireturn:
        instance = self._instances.get(agent)
        if not instance:
            return 200

        return await instance.get_facts(resource)

    @protocol.handle(methods.get_status)
    async def get_status(self) -> Apireturn:
        return 200, collect_report(self)
