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
import datetime
import logging
import os
import random
import time
import uuid
from asyncio import Lock
from collections import defaultdict
from concurrent.futures.thread import ThreadPoolExecutor
from logging import Logger
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple, cast

from tornado import ioloop
from tornado.concurrent import Future

from inmanta import const, data, env, protocol
from inmanta.agent import config as cfg
from inmanta.agent import handler
from inmanta.agent.cache import AgentCache
from inmanta.agent.handler import ResourceHandler, SkipResource
from inmanta.agent.io.remote import ChannelClosedException
from inmanta.agent.reporting import collect_report
from inmanta.const import ParameterSource, ResourceState
from inmanta.data.model import AttributeStateChange, ResourceIdStr, ResourceVersionIdStr
from inmanta.loader import CodeLoader, ModuleSource
from inmanta.protocol import SessionEndpoint, SyncClient, methods, methods_v2
from inmanta.resources import Id, Resource
from inmanta.types import Apireturn, JsonType
from inmanta.util import IntervalSchedule, NamedLock, ScheduledTask, TaskMethod, add_future

LOGGER = logging.getLogger(__name__)
GET_RESOURCE_BACKOFF = 5


class ResourceActionResult(object):
    def __init__(self, cancel: bool) -> None:
        self.cancel = cancel

    def __add__(self, other: "ResourceActionResult") -> "ResourceActionResult":
        return ResourceActionResult(self.cancel or other.cancel)

    def __str__(self) -> str:
        return "%r" % self.cancel


# https://mypy.readthedocs.io/en/latest/common_issues.html#using-classes-that-are-generic-in-stubs-but-not-at-runtime
if TYPE_CHECKING:
    ResourceActionResultFuture = asyncio.Future[ResourceActionResult]
else:
    ResourceActionResultFuture = asyncio.Future


class ResourceActionBase(abc.ABC):
    """Base class for Local and Remote resource actions"""

    resource_id: Id
    future: ResourceActionResultFuture
    dependencies: List["ResourceActionBase"]
    # resourceid -> attribute -> {current: , desired:}
    changes: Dict[ResourceVersionIdStr, Dict[str, AttributeStateChange]]

    def __init__(self, scheduler: "ResourceScheduler", resource_id: Id, gid: uuid.UUID, reason: str) -> None:
        """
        :param gid: A unique identifier to identify a deploy. This is local to this agent.
        """
        self.scheduler: "ResourceScheduler" = scheduler
        self.resource_id: Id = resource_id
        self.future: ResourceActionResultFuture = Future()
        # This variable is used to indicate that the future of a ResourceAction will get a value, because of a deploy
        # operation. This variable makes sure that the result cannot be set twice when the ResourceAction is cancelled.
        self.running: bool = False
        self.gid: uuid.UUID = gid
        self.status: Optional[const.ResourceState] = None
        self.change: Optional[const.Change] = const.Change.nochange
        self.undeployable: Optional[const.ResourceState] = None
        self.reason: str = reason
        self.logger: Logger = self.scheduler.logger

    async def execute(
        self, dummy: "ResourceActionBase", generation: "Dict[ResourceIdStr, ResourceActionBase]", cache: AgentCache
    ) -> None:
        return

    def is_running(self) -> bool:
        return self.running

    def is_done(self) -> bool:
        return self.future.done()

    def cancel(self) -> None:
        if not self.is_running() and not self.is_done():
            LOGGER.info("Cancelled deploy of %s %s", self.gid, self.resource_id)
            self.future.set_result(ResourceActionResult(cancel=True))

    def long_string(self) -> str:
        return "%s awaits %s" % (self.resource_id.resource_str(), " ".join([str(aw) for aw in self.dependencies]))

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
        super(DummyResourceAction, self).__init__(scheduler, dummy_id, gid, reason)


class ResourceAction(ResourceActionBase):
    def __init__(self, scheduler: "ResourceScheduler", resource: Resource, gid: uuid.UUID, reason: str) -> None:
        """
        :param gid: A unique identifier to identify a deploy. This is local to this agent.
        """
        super(ResourceAction, self).__init__(scheduler, resource.id, gid, reason)
        self.resource: Resource = resource

    async def send_in_progress(self, action_id: uuid.UUID) -> Dict[ResourceIdStr, const.ResourceState]:
        result = await self.scheduler.get_client().resource_deploy_start(
            tid=self.scheduler._env_id,
            rvid=self.resource.id.resource_version_str(),
            action_id=action_id,
        )
        if result.code != 200 or result.result is None:
            raise Exception("Failed to report the start of the deployment to the server")
        return {Id.parse_id(key).resource_str(): const.ResourceState[value] for key, value in result.result["data"].items()}

    async def _execute(self, ctx: handler.HandlerContext, requires: Dict[ResourceIdStr, const.ResourceState]) -> None:
        """
        :param ctx: The context to use during execution of this deploy
        :param requires: A dictionary that maps each dependency of the resource to be deployed, to its latest resource
                         state that was not `deploying'.
        """
        ctx.debug("Start deploy %(deploy_id)s of resource %(resource_id)s", deploy_id=self.gid, resource_id=self.resource_id)

        # setup provider
        provider: Optional[ResourceHandler] = None
        try:
            provider = await self.scheduler.agent.get_provider(self.resource)
        except ChannelClosedException as e:
            ctx.set_status(const.ResourceState.unavailable)
            ctx.exception(str(e))
            return
        except Exception:
            ctx.set_status(const.ResourceState.unavailable)
            ctx.exception("Unable to find a handler for %(resource_id)s", resource_id=self.resource.id.resource_version_str())
            return
        else:
            # main execution
            try:
                await asyncio.get_event_loop().run_in_executor(
                    self.scheduler.agent.thread_pool,
                    provider.deploy,
                    ctx,
                    self.resource,
                    requires,
                )
                if ctx.status is None:
                    ctx.set_status(const.ResourceState.deployed)
            except ChannelClosedException as e:
                ctx.set_status(const.ResourceState.failed)
                ctx.exception(str(e))
            except SkipResource as e:
                ctx.set_status(const.ResourceState.skipped)
                ctx.warning(msg="Resource %(resource_id)s was skipped: %(reason)s", resource_id=self.resource.id, reason=e.args)
            except Exception as e:
                ctx.set_status(const.ResourceState.failed)
                ctx.exception(
                    "An error occurred during deployment of %(resource_id)s (exception: %(exception)s",
                    resource_id=self.resource.id,
                    exception=repr(e),
                )
        finally:
            if provider is not None:
                provider.close()

    async def execute(
        self, dummy: "ResourceActionBase", generation: "Dict[ResourceIdStr, ResourceActionBase]", cache: AgentCache
    ) -> None:
        self.logger.log(const.LogLevel.TRACE.to_int, "Entering %s %s", self.gid, self.resource)
        with cache.manager(self.resource.id.get_version()):
            self.dependencies = [generation[x.resource_str()] for x in self.resource.requires]
            waiters = [x.future for x in self.dependencies]
            waiters.append(dummy.future)
            # Explicit cast is required because mypy has issues with * and generics
            results: List[ResourceActionResult] = cast(List[ResourceActionResult], await asyncio.gather(*waiters))

            async with self.scheduler.ratelimiter:
                ctx = handler.HandlerContext(self.resource, logger=self.logger)

                ctx.debug(
                    "Start run for resource %(resource)s because %(reason)s",
                    resource=str(self.resource.id),
                    deploy_id=self.gid,
                    agent=self.scheduler.agent.name,
                    reason=self.reason,
                )

                self.running = True
                try:
                    if self.is_done():
                        # Action is cancelled
                        self.logger.log(const.LogLevel.TRACE.to_int, "%s %s is no longer active" % (self.gid, self.resource))
                        return

                    result = sum(results, ResourceActionResult(cancel=False))

                    if result.cancel:
                        # self.running will be set to false when self.cancel is called
                        # Only happens when global cancel has not cancelled us but our predecessors have already been cancelled
                        return

                    try:
                        requires: Dict[ResourceIdStr, const.ResourceState] = await self.send_in_progress(ctx.action_id)
                    except Exception:
                        ctx.set_status(const.ResourceState.failed)
                        ctx.exception("Failed to report the start of the deployment to the server")
                    else:
                        if self.undeployable is not None:
                            ctx.set_status(self.undeployable)
                        else:
                            await self._execute(ctx=ctx, requires=requires)

                    ctx.debug(
                        "End run for resource %(resource)s in deploy %(deploy_id)s",
                        resource=str(self.resource.id),
                        deploy_id=self.gid,
                    )

                    changes: Dict[ResourceVersionIdStr, Dict[str, AttributeStateChange]] = {
                        self.resource.id.resource_version_str(): ctx.changes
                    }

                    if ctx.facts:
                        ctx.debug("Sending facts to the server")
                        set_fact_response = await self.scheduler.get_client().set_parameters(
                            tid=self.scheduler._env_id, parameters=ctx.facts
                        )
                        if set_fact_response.code != 200:
                            ctx.error("Failed to send facts to the server %s", set_fact_response.result)

                    response = await self.scheduler.get_client().resource_deploy_done(
                        tid=self.scheduler._env_id,
                        rvid=self.resource.id.resource_version_str(),
                        action_id=ctx.action_id,
                        status=ctx.status,
                        messages=ctx.logs,
                        changes=changes,
                        change=ctx.change,
                    )

                    if response.code != 200:
                        LOGGER.error("Resource status update failed %s", response.result)

                    self.status = ctx.status
                    self.change = ctx.change
                    self.changes = changes
                    self.future.set_result(ResourceActionResult(cancel=False))
                finally:
                    self.running = False


class RemoteResourceAction(ResourceActionBase):
    def __init__(self, scheduler: "ResourceScheduler", resource_id: Id, gid: uuid.UUID, reason: str) -> None:
        super(RemoteResourceAction, self).__init__(scheduler, resource_id, gid, reason)

    async def execute(
        self, dummy: "ResourceActionBase", generation: "Dict[ResourceIdStr, ResourceActionBase]", cache: AgentCache
    ) -> None:
        await dummy.future
        try:
            result = await self.scheduler.get_client().get_resource(
                self.scheduler.agent._env_id,
                self.resource_id.resource_version_str(),
                logs=True,
                log_action=const.ResourceAction.deploy,
                log_limit=1,
            )
            if result.code != 200 or result.result is None:
                LOGGER.error("Failed to get the status for remote resource %s (%s)", str(self.resource_id), result.result)
                return

            status = const.ResourceState[result.result["resource"]["status"]]
            self.running = True
            if status in const.TRANSIENT_STATES or self.future.done():
                # wait for event
                pass
            else:
                if "logs" in result.result and len(result.result["logs"]) > 0:
                    log = result.result["logs"][0]

                    if "change" in log and log["change"] is not None:
                        self.change = const.Change[log["change"]]
                    else:
                        self.change = const.Change.nochange

                    if "changes" in log and log["changes"] is not None and str(self.resource_id) in log["changes"]:
                        self.changes = log["changes"]
                    else:
                        self.changes = {}
                    self.status = status

                self.future.set_result(ResourceActionResult(cancel=False))
        except Exception:
            LOGGER.exception("could not get status for remote resource")
        finally:
            self.running = False

    def notify(
        self,
        status: const.ResourceState,
        change: const.Change,
        changes: Dict[ResourceVersionIdStr, Dict[str, AttributeStateChange]],
    ) -> None:
        if not self.future.done():
            self.status = status
            self.change = change
            self.changes = changes
            self.future.set_result(ResourceActionResult(cancel=False))


class ResourceScheduler(object):
    """Class responsible for managing sequencing of actions performed by the agent.

    State of the last run is not removed after the run but remains.

    By not removing e.g. the generation,
    1 - the class is always in a valid state
    2 - we don't need to figure out exactly when a run is done
    """

    def __init__(
        self, agent: "AgentInstance", env_id: uuid.UUID, name: str, cache: AgentCache, ratelimiter: asyncio.Semaphore
    ) -> None:
        self.generation: Dict[ResourceIdStr, ResourceActionBase] = {}
        self.cad: Dict[str, RemoteResourceAction] = {}
        self._env_id = env_id
        self.agent = agent
        self.cache = cache
        self.name = name
        self.ratelimiter = ratelimiter
        self.version: int = 0
        # the reason the last run was started
        self.reason: str = ""
        # was the last run a repair run?
        self.is_repair: bool = False
        # if this value is not None, a new repair run will be started after the current run is done
        # this field is both flag and value, to ensure consistency
        self._resume_reason: Optional[str] = None
        self.logger: Logger = agent.logger

    def get_scheduled_resource_actions(self) -> List[ResourceActionBase]:
        return list(self.generation.values())

    def finished(self) -> bool:
        for resource_action in self.generation.values():
            if not resource_action.is_done():
                return False
        return True

    def is_normal_deploy_running(self) -> bool:
        return not self.finished() and not self.is_repair

    def cancel(self) -> None:
        """
        Cancel all scheduled deployments.
        """
        for ra in self.generation.values():
            ra.cancel()
        self.generation = {}
        self.cad = {}

    def reload(
        self,
        resources: List[Resource],
        undeployable: Dict[ResourceVersionIdStr, ResourceState] = {},
        reason: str = "RELOAD",
        is_repair: bool = False,
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
            if self.is_repair:
                # now running repair
                if is_repair:
                    # repair restarts repair
                    self.logger.info("Terminating run '%s' for '%s'", self.reason, reason)
                else:
                    # increment interrupts repair
                    self.logger.info("Interrupting run '%s' for '%s'", self.reason, reason)
                    self._resume_reason = "Restarting run '%s', interrupted for '%s'" % (self.reason, reason)
            else:
                # now running increment
                if is_repair:
                    # repair is delayed
                    self.logger.info("Deferring run '%s' for '%s'", reason, self.reason)
                    self._resume_reason = reason
                    return
                else:
                    # increment overrules increment
                    self.logger.info("Terminating run '%s' for '%s'", self.reason, reason)
            # cancel old run
            self.cancel()

        # start new run
        self.reason = reason
        self.is_repair = is_repair
        self.version = resources[0].id.get_version()
        gid = uuid.uuid4()
        self.logger.info("Running %s for reason: %s" % (gid, reason))

        # re-generate generation
        self.generation = {r.id.resource_str(): ResourceAction(self, r, gid, reason) for r in resources}

        # mark undeployable
        for key, res in self.generation.items():
            vid = res.resource_id.resource_version_str()
            if vid in undeployable:
                self.generation[key].undeployable = undeployable[vid]

        # hook up Cross Agent Dependencies
        cross_agent_dependencies = [q for r in resources for q in r.requires if q.get_agent_name() != self.name]
        for cad in cross_agent_dependencies:
            ra = RemoteResourceAction(self, cad, gid, reason)
            self.cad[str(cad)] = ra
            self.generation[cad.resource_str()] = ra

        # Create dummy to give start signal
        dummy = DummyResourceAction(self, gid, reason)
        # Dispatch all actions
        # Will block on dependencies and dummy
        for r in self.generation.values():
            add_future(r.execute(dummy, self.generation, self.cache))

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
            if self._resume_reason is not None:
                self.logger.info("Resuming run '%s'", self._resume_reason)
                self.agent.process.add_background_task(
                    self.agent.get_latest_version_for_agent(
                        reason=self._resume_reason, incremental_deploy=False, is_repair_run=True
                    )
                )
                self._resume_reason = None

    def notify_ready(
        self,
        resourceid: ResourceVersionIdStr,
        state: const.ResourceState,
        change: const.Change,
        changes: Dict[ResourceVersionIdStr, Dict[str, AttributeStateChange]],
    ) -> None:
        if resourceid not in self.cad:
            # received CAD notification for which no resource are waiting, so return
            return
        self.cad[resourceid].notify(state, change, changes)

    def dump(self) -> None:
        print("Waiting:")
        for r in self.generation.values():
            print(r.long_string())

    def get_client(self) -> protocol.Client:
        return self.agent.get_client()


class AgentInstance(object):
    _get_resource_timeout: float
    _get_resource_duration: float

    def __init__(self, process: "Agent", name: str, uri: str) -> None:
        self.process = process
        self.name = name
        self._uri = uri

        self.logger: Logger = LOGGER.getChild(self.name)

        # the lock for changing the current ongoing deployment
        self.critical_ratelimiter = asyncio.Semaphore(1)
        # lock for dryrun tasks
        self.dryrunlock = asyncio.Semaphore(1)

        # multi threading control
        # threads to setup connections
        self.provider_thread_pool: ThreadPoolExecutor = ThreadPoolExecutor(1, thread_name_prefix="ProviderPool_%s" % name)
        # threads to work
        self.thread_pool: ThreadPoolExecutor = ThreadPoolExecutor(process.poolsize, thread_name_prefix="Pool_%s" % name)
        self.ratelimiter = asyncio.Semaphore(process.poolsize)

        if process.environment is None:
            raise Exception("Agent instance started without a valid environment id set.")

        self._env_id: uuid.UUID = process.environment
        self.sessionid: uuid.UUID = process.sessionid

        # init
        self._cache = AgentCache(self)
        self._nq = ResourceScheduler(self, self._env_id, name, self._cache, ratelimiter=self.ratelimiter)
        self._time_triggered_actions: Set[ScheduledTask] = set()
        self._enabled = False
        self._stopped = False

        # do regular deploys
        self._deploy_interval = cfg.agent_deploy_interval.get()
        deploy_splay_time = cfg.agent_deploy_splay_time.get()
        self._deploy_splay_value = random.randint(0, deploy_splay_time)

        # do regular repair runs
        self._repair_interval = cfg.agent_repair_interval.get()
        repair_splay_time = cfg.agent_repair_splay_time.get()
        self._repair_splay_value = random.randint(0, repair_splay_time)

        self._getting_resources = False
        self._get_resource_timeout = 0

    async def stop(self) -> None:
        self._stopped = True
        self._enabled = False
        self._disable_time_triggers()
        self._nq.cancel()
        self._cache.close()
        self.provider_thread_pool.shutdown(wait=False)
        self.thread_pool.shutdown(wait=False)

    @property
    def environment(self) -> uuid.UUID:
        return self._env_id

    def get_client(self) -> protocol.Client:
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
                reason="Periodic deploy started at %s" % (now.strftime(const.TIME_LOGFMT)),
                incremental_deploy=True,
                is_repair_run=False,
            )

        async def repair_action() -> None:
            now = datetime.datetime.now().astimezone()
            await self.get_latest_version_for_agent(
                reason="Repair run started at %s" % (now.strftime(const.TIME_LOGFMT)),
                incremental_deploy=False,
                is_repair_run=True,
            )

        now = datetime.datetime.now().astimezone()
        if self._deploy_interval > 0:
            self.logger.info(
                "Scheduling periodic deploy with interval %d and splay %d (first run at %s)",
                self._deploy_interval,
                self._deploy_splay_value,
                (now + datetime.timedelta(seconds=self._deploy_splay_value)).strftime(const.TIME_LOGFMT),
            )
            self._enable_time_trigger(deploy_action, self._deploy_interval, self._deploy_splay_value)
        if self._repair_interval > 0:
            self.logger.info(
                "Scheduling repair with interval %d and splay %d (first run at %s)",
                self._repair_interval,
                self._repair_splay_value,
                (now + datetime.timedelta(seconds=self._repair_splay_value)).strftime(const.TIME_LOGFMT),
            )
            self._enable_time_trigger(repair_action, self._repair_interval, self._repair_splay_value)

    def _enable_time_trigger(self, action: TaskMethod, interval: int, splay: int) -> None:
        schedule: IntervalSchedule = IntervalSchedule(interval=float(interval), initial_delay=float(splay))
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
        changes: Dict[ResourceVersionIdStr, Dict[str, AttributeStateChange]],
    ) -> None:
        self._nq.notify_ready(resourceid, state, change, changes)

    def _can_get_resources(self) -> bool:
        if self._getting_resources:
            self.logger.info("Attempting to get resource while get is in progress")
            return False
        if time.time() < self._get_resource_timeout:
            self.logger.info(
                "Attempting to get resources during backoff %g seconds left, last download took %d seconds",
                self._get_resource_timeout - time.time(),
                self._get_resource_duration,
            )
            return False
        return True

    async def get_provider(self, resource: Resource) -> ResourceHandler:
        provider = await asyncio.get_event_loop().run_in_executor(
            self.provider_thread_pool, handler.Commander.get_provider, self._cache, self, resource
        )
        provider.set_cache(self._cache)
        return provider

    async def get_latest_version_for_agent(
        self, reason: str = "Unknown", incremental_deploy: bool = False, is_repair_run: bool = False
    ) -> None:
        """
        Get the latest version for the given agent (this is also how we are notified)

        :param reason: the reason this deploy was started
        """
        if not self._can_get_resources():
            self.logger.warning("%s aborted by rate limiter", reason)
            return

        async with self.critical_ratelimiter:
            if not self._can_get_resources():
                self.logger.warning("%s aborted by rate limiter", reason)
                return

            self.logger.debug("Getting latest resources for %s", reason)
            self._getting_resources = True
            start = time.time()
            try:
                result = await self.get_client().get_resources_for_agent(
                    tid=self._env_id, agent=self.name, incremental_deploy=incremental_deploy
                )
            finally:
                self._getting_resources = False
            end = time.time()
            self._get_resource_duration = end - start
            self._get_resource_timeout = GET_RESOURCE_BACKOFF * self._get_resource_duration + end
            if result.code == 404:
                self.logger.info("No released configuration model version available for %s", reason)
            elif result.code == 409:
                self.logger.warning("We are not currently primary during %s: %s", reason, result.result)
            elif result.code != 200 or result.result is None:
                self.logger.warning("Got an error while pulling resources for %s. %s", reason, result.result)

            else:
                undeployable, resources = await self.load_resources(
                    result.result["version"], const.ResourceAction.deploy, result.result["resources"]
                )
                self.logger.debug("Pulled %d resources because %s", len(resources), reason)

                if len(resources) > 0:
                    self._nq.reload(resources, undeployable, reason=reason, is_repair=is_repair_run)

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

                undeployable, resources = await self.load_resources(
                    version, const.ResourceAction.dryrun, response.result["resources"]
                )

                self._cache.open_version(version)
                for resource in resources:
                    ctx = handler.HandlerContext(resource, True)
                    started = datetime.datetime.now().astimezone()
                    provider = None

                    resource_id = resource.id.resource_version_str()
                    if resource_id in undeployable:
                        ctx.error(
                            "Skipping dryrun %(resource_id)s because in undeployable state %(status)s",
                            resource_id=resource_id,
                            status=undeployable[resource_id],
                        )
                        await self.get_client().dryrun_update(tid=self._env_id, id=dry_run_id, resource=resource_id, changes={})
                        continue

                    try:
                        self.logger.debug("Running dryrun for %s", resource_id)

                        try:
                            provider = await self.get_provider(resource)
                        except Exception as e:
                            ctx.exception(
                                "Unable to find a handler for %(resource_id)s (exception: %(exception)s",
                                resource_id=resource_id,
                                exception=str(e),
                            )
                            await self.get_client().dryrun_update(
                                tid=self._env_id,
                                id=dry_run_id,
                                resource=resource_id,
                                changes={"handler": {"current": "FAILED", "desired": "Unable to find a handler"}},
                            )
                        else:
                            try:
                                await asyncio.get_event_loop().run_in_executor(
                                    self.thread_pool, provider.execute, ctx, resource, True
                                )

                                changes = ctx.changes
                                if changes is None:
                                    changes = {}
                                if ctx.status == const.ResourceState.failed:
                                    changes["handler"] = AttributeStateChange(current="FAILED", desired="Handler failed")
                                await self.get_client().dryrun_update(
                                    tid=self._env_id, id=dry_run_id, resource=resource_id, changes=changes
                                )
                            except Exception as e:
                                ctx.exception(
                                    "Exception during dryrun for %(resource_id)s (exception: %(exception)s",
                                    resource_id=str(resource.id),
                                    exception=str(e),
                                )
                                changes = ctx.changes
                                if changes is None:
                                    changes = {}
                                changes["handler"] = AttributeStateChange(current="FAILED", desired="Handler failed")
                                await self.get_client().dryrun_update(
                                    tid=self._env_id, id=dry_run_id, resource=resource_id, changes=changes
                                )

                    except Exception:
                        ctx.exception("Unable to process resource for dryrun.")
                        changes = {}
                        changes["handler"] = AttributeStateChange(current="FAILED", desired="Resource Deserialization Failed")
                        await self.get_client().dryrun_update(
                            tid=self._env_id, id=dry_run_id, resource=resource_id, changes=changes
                        )
                    finally:
                        if provider is not None:
                            provider.close()

                        finished = datetime.datetime.now().astimezone()
                        await self.get_client().resource_action_update(
                            tid=self._env_id,
                            resource_ids=[resource_id],
                            action_id=ctx.action_id,
                            action=const.ResourceAction.dryrun,
                            started=started,
                            finished=finished,
                            messages=ctx.logs,
                            status=const.ResourceState.dry,
                        )

                self._cache.close_version(version)

    async def get_facts(self, resource: JsonType) -> Apireturn:
        async with self.ratelimiter:
            undeployable, resources = await self.load_resources(resource["model"], const.ResourceAction.getfact, [resource])

            if undeployable or not resources:
                self.logger.warning(
                    "Cannot retrieve fact for %s because resource is undeployable or code could not be loaded", resource["id"]
                )
                return 500

            started = datetime.datetime.now().astimezone()
            provider = None
            try:
                resource_obj = resources[0]
                ctx = handler.HandlerContext(resource_obj)

                version = resource_obj.id.get_version()
                try:
                    self._cache.open_version(version)
                    provider = await self.get_provider(resource_obj)
                    result = await asyncio.get_event_loop().run_in_executor(
                        self.thread_pool, provider.check_facts, ctx, resource_obj
                    )

                    parameters = [
                        {
                            "id": name,
                            "value": value,
                            "resource_id": resource_obj.id.resource_str(),
                            "source": ParameterSource.fact.value,
                        }
                        for name, value in result.items()
                    ]
                    # Add facts set via the set_fact() method of the HandlerContext
                    parameters.extend(ctx.facts)

                    await self.get_client().set_parameters(tid=self._env_id, parameters=parameters)
                    finished = datetime.datetime.now().astimezone()
                    await self.get_client().resource_action_update(
                        tid=self._env_id,
                        resource_ids=[resource_obj.id.resource_version_str()],
                        action_id=ctx.action_id,
                        action=const.ResourceAction.getfact,
                        started=started,
                        finished=finished,
                        messages=ctx.logs,
                    )

                except Exception:
                    self.logger.exception("Unable to retrieve fact")
                finally:
                    self._cache.close_version(version)

            except Exception:
                self.logger.exception("Unable to find a handler for %s", resource["id"])
                return 500
            finally:
                if provider is not None:
                    provider.close()
            return 200

    async def load_resources(
        self, version: int, action: const.ResourceAction, resources: List[JsonType]
    ) -> Tuple[Dict[ResourceVersionIdStr, const.ResourceState], List[Resource]]:
        """Deserialize all resources and load all handler code. When the code for this type fails to load, the resource
        is marked as failed
        """
        started = datetime.datetime.now().astimezone()
        failed_resource_types = await self.process.ensure_code(
            self._env_id, version, [res["resource_type"] for res in resources]
        )
        loaded_resources: List[Resource] = []
        failed_resources: List[ResourceVersionIdStr] = []
        undeployable: Dict[ResourceVersionIdStr, const.ResourceState] = {}

        for res in resources:
            try:
                res["attributes"]["id"] = res["id"]
                if res["resource_type"] not in failed_resource_types:
                    resource = Resource.deserialize(res["attributes"])
                    loaded_resources.append(resource)

                    state = const.ResourceState[res["status"]]
                    if state in const.UNDEPLOYABLE_STATES:
                        undeployable[res["id"]] = state
                else:
                    failed_resources.append(res["id"])
                    undeployable[res["id"]] = const.ResourceState.unavailable
                    resource = Resource.deserialize(res["attributes"], use_generic=True)
                    loaded_resources.append(resource)

            except TypeError:
                failed_resources.append(res["id"])
                undeployable[res["id"]] = const.ResourceState.unavailable
                resource = Resource.deserialize(res["attributes"], use_generic=True)
                loaded_resources.append(resource)

        if len(failed_resources) > 0:
            log = data.LogLine.log(
                logging.ERROR,
                "Failed to load handler code or install handler code dependencies. Check the agent log for details.",
            )
            await self.get_client().resource_action_update(
                tid=self._env_id,
                resource_ids=failed_resources,
                action_id=uuid.uuid4(),
                action=action,
                started=started,
                finished=datetime.datetime.now().astimezone(),
                messages=[log],
                status=const.ResourceState.unavailable,
            )
        return undeployable, loaded_resources


class CouldNotConnectToServer(Exception):
    pass


class Agent(SessionEndpoint):
    """
    An agent to enact changes upon resources. This agent listens to the
    message bus for changes.
    """

    # cache reference to THIS ioloop for handlers to push requests on it
    # defer to start, just to be sure
    _io_loop: ioloop.IOLoop

    def __init__(
        self,
        hostname: Optional[str] = None,
        agent_map: Optional[Dict[str, str]] = None,
        code_loader: bool = True,
        environment: Optional[uuid.UUID] = None,
        poolsize: int = 1,
        cricital_pool_size: int = 5,
    ):
        super().__init__("agent", timeout=cfg.server_timeout.get(), reconnect_delay=cfg.agent_reconnect_delay.get())

        self.hostname = hostname
        self.poolsize = poolsize
        self.ratelimiter = asyncio.Semaphore(poolsize)
        self.critical_ratelimiter = asyncio.Semaphore(cricital_pool_size)
        self.thread_pool = ThreadPoolExecutor(poolsize, thread_name_prefix="mainpool")

        self._storage = self.check_storage()

        if environment is None:
            environment = cfg.environment.get()
            if environment is None:
                raise Exception("The agent requires an environment to be set.")
        self.set_environment(environment)

        self._instances: Dict[str, AgentInstance] = {}
        self._instances_lock = asyncio.Lock()

        self._loader: Optional[CodeLoader] = None
        self._env: Optional[env.VirtualEnv] = None
        if code_loader:
            self._env = env.VirtualEnv(self._storage["env"])
            self._env.use_virtual_env()
            self._loader = CodeLoader(self._storage["code"])
            # Lock to ensure only one actual install runs at a time
            self._loader_lock = Lock()
            # Cache to prevent re-loading the same resource-version
            self._last_loaded: Dict[str, int] = defaultdict(lambda: -1)
            # Per-resource lock to serialize all actions per resource
            self._resource_loader_lock = NamedLock()

        self.agent_map: Optional[Dict[str, str]] = agent_map

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
            self.agent_map = cfg.agent_map.get()

    async def _init_endpoint_names(self) -> None:
        if self.hostname is not None:
            await self.add_end_point_name(self.hostname)
        else:
            # load agent names from the config file
            agent_names = cfg.agent_names.get()
            if agent_names is not None:
                for name in agent_names:
                    if "$" in name:
                        name = name.replace("$node-name", self.node_name)
                    await self.add_end_point_name(name)

    async def stop(self) -> None:
        await super(Agent, self).stop()
        self.thread_pool.shutdown(wait=False)
        for instance in self._instances.values():
            await instance.stop()

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
        self._io_loop = ioloop.IOLoop.current()
        await super(Agent, self).start()

    async def add_end_point_name(self, name: str) -> None:
        async with self._instances_lock:
            await self._add_end_point_name(name)

    async def _add_end_point_name(self, name: str) -> None:
        """
        Note: always call under _instances_lock
        """
        LOGGER.info("Adding endpoint %s", name)
        await super(Agent, self).add_end_point_name(name)

        # Make mypy happy
        assert self.agent_map is not None

        hostname = "local:"
        if name in self.agent_map:
            hostname = self.agent_map[name]

        self._instances[name] = AgentInstance(self, name, hostname)

    async def remove_end_point_name(self, name: str) -> None:
        async with self._instances_lock:
            await self._remove_end_point_name(name)

    async def _remove_end_point_name(self, name: str) -> None:
        """
        Note: always call under _instances_lock
        """
        LOGGER.info("Removing endpoint %s", name)
        await super(Agent, self).remove_end_point_name(name)

        agent_instance = self._instances[name]
        del self._instances[name]
        await agent_instance.stop()

    @protocol.handle(methods_v2.update_agent_map)
    async def update_agent_map(self, agent_map: Dict[str, str]) -> None:
        if not cfg.use_autostart_agent_map.get():
            LOGGER.warning(
                "Agent received an update_agent_map() trigger, but agent is not running with "
                "the use_autostart_agent_map option."
            )
        else:
            LOGGER.debug("Received update_agent_map() trigger with agent_map %s", agent_map)
            await self._update_agent_map(agent_map)

    async def _update_agent_map(self, agent_map: Dict[str, str]) -> None:
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

            to_be_gathered = [self._add_end_point_name(agent_name) for agent_name in agents_to_add]
            to_be_gathered += [self._remove_end_point_name(agent_name) for agent_name in agents_to_remove + update_uri_agents]
            await asyncio.gather(*to_be_gathered)
            # Re-add agents with updated URI
            await asyncio.gather(*[self._add_end_point_name(agent_name) for agent_name in update_uri_agents])
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

    async def get_latest_version(self) -> None:
        """
        Get the latest version of managed resources for all agents
        """
        for agent in self._instances.values():
            await agent.get_latest_version_for_agent(reason="call to get_latest_version on agent")

    async def ensure_code(self, environment: uuid.UUID, version: int, resource_types: Sequence[str]) -> Set[str]:
        """Ensure that the code for the given environment and version is loaded"""
        failed_to_load: Set[str] = set()
        if self._loader is None:
            return failed_to_load

        for rt in set(resource_types):
            # only one logical thread can load a particular resource type at any time
            async with self._resource_loader_lock.get(rt):
                # stop if the last successful load was this one
                # The combination of the lock and this check causes the reloads to naturally 'batch up'
                if self._last_loaded[rt] == version:
                    LOGGER.debug("Code already present for %s version=%d", rt, version)
                    continue
                # clear cache, for retry on failure
                self._last_loaded[rt] = -1

                result: protocol.Result = await self._client.get_source_code(environment, version, rt)
                if result.code == 200 and result.result is not None:
                    try:
                        sync_client = SyncClient(client=self._client, ioloop=self._io_loop)
                        LOGGER.debug("Installing handler %s version=%d", rt, version)
                        requirements = set()
                        sources = []
                        for source in result.result["data"]:
                            sources.append(
                                ModuleSource(
                                    name=source["module_name"],
                                    is_byte_code=source["is_byte_code"],
                                    hash_value=source["hash"],
                                    _client=sync_client,
                                )
                            )
                            requirements.update(source["requirements"])

                        await self._install(sources, list(requirements))
                        LOGGER.debug("Installed handler %s version=%d", rt, version)
                        self._last_loaded[rt] = version
                    except Exception:
                        LOGGER.exception("Failed to install handler %s version=%d", rt, version)
                        failed_to_load.add(rt)

        return failed_to_load

    async def _install(self, sources: list[ModuleSource], requirements: Sequence[str]) -> None:
        if self._env is None or self._loader is None:
            raise Exception("Unable to load code when agent is started with code loading disabled.")

        async with self._loader_lock:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self.thread_pool, self._env.install_from_list, requirements)
            await loop.run_in_executor(self.thread_pool, self._loader.deploy_version, sources)

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
            instance.get_latest_version_for_agent(reason="call to trigger_update", incremental_deploy=incremental_deploy)
        )
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
        changes: Dict[ResourceVersionIdStr, Dict[str, AttributeStateChange]],
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

    def check_storage(self) -> Dict[str, str]:
        """
        Check if the server storage is configured and ready to use.
        """

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

        return dir_map

    @protocol.handle(methods.get_parameter, env="tid")
    async def get_facts(self, env: uuid.UUID, agent: str, resource: Dict[str, Any]) -> Apireturn:
        instance = self._instances.get(agent)
        if not instance:
            return 200

        return await instance.get_facts(resource)

    @protocol.handle(methods.get_status)
    async def get_status(self) -> Apireturn:
        return 200, collect_report(self)
