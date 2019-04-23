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

from concurrent.futures.thread import ThreadPoolExecutor
import datetime
import logging
import os
import random
import uuid
import time
import asyncio
from logging import Logger

from tornado import gen, locks, ioloop
from inmanta import env, const
from inmanta import protocol
from inmanta.agent import handler
from inmanta.loader import CodeLoader
from inmanta.protocol import SessionEndpoint, methods
from inmanta.resources import Resource, Id
from tornado.concurrent import Future
from inmanta.agent.cache import AgentCache
from inmanta.agent import config as cfg
from inmanta.agent.reporting import collect_report
from typing import Tuple, Optional, Generator, Any, Dict, List, TYPE_CHECKING
from inmanta.agent.handler import ResourceHandler
from inmanta.types import NoneGen

LOGGER = logging.getLogger(__name__)
GET_RESOURCE_BACKOFF = 5


class ResourceActionResult(object):

    def __init__(self, success: bool, receive_events: bool, cancel: bool) -> None:
        self.success = success
        self.receive_events = receive_events
        self.cancel = cancel

    def __add__(self, other: "ResourceActionResult") -> "ResourceActionResult":
        return ResourceActionResult(self.success and other.success,
                                    self.receive_events or other.receive_events,
                                    self.cancel or other.cancel)

    def __str__(self) -> str:
        return "%r %r %r" % (self.success, self.receive_events, self.cancel)


# https://mypy.readthedocs.io/en/latest/common_issues.html#using-classes-that-are-generic-in-stubs-but-not-at-runtime
if TYPE_CHECKING:
    ResourceActionResultFuture = asyncio.Future[ResourceActionResult]
else:
    ResourceActionResultFuture = asyncio.Future


class ResourceAction(object):

    resource: Resource
    resource_id: Id
    future: ResourceActionResultFuture

    def __init__(self, scheduler: "ResourceScheduler", resource: Resource, gid: uuid.UUID, reason: str) -> None:
        """
            :param gid A unique identifier to identify a deploy. This is local to this agent.
        """
        self.scheduler: "ResourceScheduler" = scheduler
        self.resource: Resource = resource
        if self.resource is not None:
            self.resource_id: Id = resource.id
        self.future: ResourceActionResultFuture = Future()
        self.running: bool = False
        self.gid: uuid.UUID = gid
        self.status: Optional[const.ResourceState] = None
        self.change: Optional[const.Change] = None
        # resourceid -> attribute -> {current: , desired:}
        self.changes: Optional[Dict[str, Dict[str, Dict[str, str]]]] = None
        self.undeployable: Optional[const.ResourceState] = None
        self.reason: str = reason
        self.logger: Logger = self.scheduler.logger

    def is_running(self) -> bool:
        return self.running

    def is_done(self) -> bool:
        return self.future.done()

    def cancel(self) -> None:
        if not self.is_running() and not self.is_done():
            LOGGER.info("Cancelled deploy of %s %s", self.gid, self.resource)
            self.future.set_result(ResourceActionResult(False, False, True))

    @gen.coroutine
    def send_in_progress(self,
                         action_id: uuid.UUID,
                         start: float,
                         status: const.ResourceState = const.ResourceState.deploying) -> NoneGen:
        yield self.scheduler.get_client().resource_action_update(tid=self.scheduler._env_id,
                                                                 resource_ids=[str(self.resource.id)],
                                                                 action_id=action_id,
                                                                 action=const.ResourceAction.deploy,
                                                                 started=start,
                                                                 status=status)

    @gen.coroutine
    def _execute(self, ctx: handler.HandlerContext, events: dict, cache: AgentCache, start: float,
                 event_only: bool=False) -> Generator[Any, Any, Tuple[bool, bool]]:
        """
            :param ctx The context to use during execution of this deploy
            :param events Possible events that are available for this resource
            :param cache The cache instance to use
            :param event_only: don't execute, only do event propagation
            :param state: start time
            :return (success, send_event) Return whether the execution was successful and whether a change event should be sent
                                          to provides of this resource.
        """
        ctx.debug("Start deploy %(deploy_id)s of resource %(resource_id)s",
                  deploy_id=self.gid, resource_id=self.resource_id)
        provider: Optional[ResourceHandler] = None

        if not event_only:
            yield self.send_in_progress(ctx.action_id, start)
        else:
            yield self.send_in_progress(ctx.action_id, start, status=const.ResourceState.processing_events)

        # setup provider
        try:
            provider = yield self.scheduler.agent.get_provider(self.resource)
        except Exception:
            if provider is not None:
                provider.close()

            cache.close_version(self.resource.id.version)
            ctx.set_status(const.ResourceState.unavailable)
            ctx.exception("Unable to find a handler for %(resource_id)s", resource_id=str(self.resource.id))
            return False, False

        success = True
        # no events by default, i.e. don't send events if you are not executed
        send_event = False

        # main execution
        if not event_only:
            send_event = (hasattr(self.resource, "send_event") and self.resource.send_event)

            try:
                yield self.scheduler.agent.thread_pool.submit(provider.execute, ctx, self.resource)
            except Exception as e:
                ctx.set_status(const.ResourceState.failed)
                ctx.exception("An error occurred during deployment of %(resource_id)s (exception: %(exception)s",
                              resource_id=self.resource.id, exception=repr(e))

            if ctx.status is not const.ResourceState.deployed:
                success = False

        # event processing
        if len(events) > 0 and provider.can_process_events():
            if not event_only:
                yield self.send_in_progress(ctx.action_id, start, status=const.ResourceState.processing_events)
            try:
                ctx.info("Sending events to %(resource_id)s because of modified dependencies",
                         resource_id=str(self.resource.id))
                yield self.scheduler.agent.thread_pool.submit(provider.process_events, ctx, self.resource, events)
            except Exception:
                ctx.exception("Could not send events for %(resource_id)s",
                              resource_id=str(self.resource.id),
                              events=str(events))

        provider.close()
        cache.close_version(self.resource_id.version)

        return success, send_event

    def skipped_because(self, results):
        return [resource.resource_id.resource_str()
                for resource, result in zip(self.dependencies, results) if not result.success]

    @gen.coroutine
    def execute(self, dummy: "ResourceAction", generation: "Dict[str, ResourceAction]", cache: AgentCache) -> NoneGen:
        self.logger.log(const.LogLevel.TRACE.value, "Entering %s %s", self.gid, self.resource)
        cache.open_version(self.resource.id.version)

        self.dependencies = [generation[x.resource_str()] for x in self.resource.requires]
        waiters = [x.future for x in self.dependencies]
        waiters.append(dummy.future)
        results = yield waiters

        with (yield self.scheduler.ratelimiter.acquire()):
            start = datetime.datetime.now()
            ctx = handler.HandlerContext(self.resource, logger=self.logger)

            ctx.debug(
                "Start run for resource %(resource)s because %(reason)s",
                resource=str(self.resource.id),
                deploy_id=self.gid,
                agent=self.scheduler.agent.name,
                reason=self.reason
            )

            self.running = True
            if self.is_done():
                # Action is cancelled
                LOGGER.log(const.LogLevel.TRACE.value, "%s %s is no longer active" % (self.gid, self.resource))
                self.running = False
                if self.undeployable is not None:
                    # don't overwrite undeployable
                    ctx.set_status(self.undeployable)
                else:
                    ctx.set_status(const.ResourceState.cancelled)
                return

            result = sum(results, ResourceActionResult(True, False, False))

            if result.cancel:
                # self.running will be set to false when self.cancel is called
                # Only happens when global cancel has not cancelled us but our predecessors have already been cancelled
                if self.undeployable is not None:
                    # don't overwrite undeployable
                    ctx.set_status(self.undeployable)
                else:
                    ctx.set_status(const.ResourceState.cancelled)
                return

            if result.receive_events:
                received_events = {x.resource_id: dict(status=x.status, change=x.change,
                                                       changes=x.changes.get(str(x.resource_id), {}))
                                   for x in self.dependencies}
            else:
                received_events = {}

            if self.undeployable is not None:
                ctx.set_status(self.undeployable)
                success = False
                send_event = False
            elif not result.success:
                ctx.set_status(const.ResourceState.skipped)
                ctx.info(
                    "Resource %(resource)s skipped due to failed dependency %(failed)s",
                    resource=str(self.resource.id),
                    failed=self.skipped_because(results)
                )
                success = False
                send_event = False
                yield self._execute(ctx=ctx, events=received_events, cache=cache, event_only=True, start=start)
            else:
                success, send_event = yield self._execute(ctx=ctx, events=received_events, cache=cache, start=start)

            ctx.debug(
                "End run for resource %(resource)s in deploy %(deploy_id)s", resource=str(self.resource.id), deploy_id=self.gid
            )

            end = datetime.datetime.now()
            changes = {str(self.resource.id): ctx.changes}
            result = yield self.scheduler.get_client().resource_action_update(tid=self.scheduler._env_id,
                                                                              resource_ids=[str(self.resource.id)],
                                                                              action_id=ctx.action_id,
                                                                              action=const.ResourceAction.deploy,
                                                                              started=start, finished=end, status=ctx.status,
                                                                              changes=changes,
                                                                              messages=ctx.logs, change=ctx.change,
                                                                              send_events=send_event)
            if result.code != 200:
                LOGGER.error("Resource status update failed %s", result.result)

            self.status = ctx.status
            self.change = ctx.change
            self.changes = changes
            self.future.set_result(ResourceActionResult(success, send_event, False))
            self.running = False

    def __str__(self) -> str:
        if self.resource is None:
            return "DUMMY"

        status = ""
        if self.is_done():
            status = " Done"
        elif self.is_running():
            status = " Running"

        return self.resource.id.resource_str() + status

    def long_string(self) -> str:
        return "%s awaits %s" % (self.resource.id.resource_str(), " ".join([str(aw) for aw in self.dependencies]))


class RemoteResourceAction(ResourceAction):

    def __init__(self, scheduler: "ResourceScheduler", resource_id: Id, gid: uuid.UUID, reason: str):
        super(RemoteResourceAction, self).__init__(scheduler, None, gid, reason)
        self.resource_id = resource_id

    @gen.coroutine
    def execute(self, dummy: "ResourceAction", generation: "Dict[str, ResourceAction]", cache: AgentCache) -> NoneGen:
        yield dummy.future
        try:
            result = yield self.scheduler.get_client().get_resource(self.scheduler.agent._env_id, str(self.resource_id),
                                                                    logs=True, log_action=const.ResourceAction.deploy,
                                                                    log_limit=1)
            if result.code != 200:
                LOGGER.error("Failed to get the status for remote resource %s (%s)", str(self.resource_id),
                             result.result)

            status = const.ResourceState[result.result["resource"]["status"]]
            if status in const.TRANSIENT_STATES or self.future.done():
                # wait for event
                pass
            else:
                if status == const.ResourceState.deployed:
                    success = True
                else:
                    success = False

                send_event = False
                if "logs" in result.result and len(result.result["logs"]) > 0:
                    log = result.result["logs"][0]

                    if "change" in log:
                        self.change = const.Change[log["change"]]
                    else:
                        self.change = const.Change.nochange

                    if "changes" in log and str(self.resource_id) in log["changes"]:
                        self.changes = log["changes"]
                    else:
                        self.changes = {}
                    self.status = status
                    send_event = log["send_event"]

                self.future.set_result(ResourceActionResult(success, send_event, False))

            self.running = False
        except Exception:
            LOGGER.exception("could not get status for remote resource")

    def notify(self,
               send_events: bool,
               status: const.ResourceState,
               change: const.Change,
               changes: Dict[str, Dict[str, Dict[str, str]]]) -> None:
        if not self.future.done():
            self.status = status
            self.change = change
            self.changes = changes
            self.future.set_result(ResourceActionResult(True, send_events, False))


class ResourceScheduler(object):
    """Class responsible for managing sequencing of actions performed by the agent.

    State of the last run is not removed after the run but remains.

    By not removing e.g. the generation,
    1 - the class is always in a valid state
    2 - we don't need to figure out exactly when a run is done
    """

    def __init__(self,
                 agent: "AgentInstance",
                 env_id: uuid.UUID,
                 name: str,
                 cache: AgentCache,
                 ratelimiter: locks.Semaphore) -> None:
        self.generation: Dict[str, ResourceAction] = {}
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

    def get_scheduled_resource_actions(self) -> List[ResourceAction]:
        return list(self.generation.values())

    def finished(self) -> bool:
        for resource_action in self.generation.values():
            if not resource_action.is_done():
                return False
        return True

    def is_normal_deploy_running(self) -> bool:
        return not self.finished() and not self.is_repair

    def reload(self, resources, undeployable={}, reason: str="RELOAD", is_repair=False) -> None:
        """
        Schedule a new set of resources for execution.

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
                    self._resume_reason = "Restarting run '%s', interrupted for '%s'" % (self.reason,
                                                                                         reason)
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
            for ra in self.generation.values():
                ra.cancel()

        # start new run
        self.reason = reason
        self.is_repair = is_repair
        version = resources[0].id.get_version
        self.version = version
        gid = uuid.uuid4()
        self.logger.info("Running %s for reason: %s" % (gid, reason))

        # re-generate generation
        self.generation = {r.id.resource_str(): ResourceAction(self, r, gid, reason) for r in resources}

        # mark undeployable
        for key, res in self.generation.items():
            vid = str(res.resource.id)
            if vid in undeployable:
                self.generation[key].undeployable = undeployable[vid]

        # hook up Cross Agent Dependencies
        cross_agent_dependencies = [q for r in resources for q in r.requires if q.get_agent_name() != self.name]
        for cad in cross_agent_dependencies:
            ra = RemoteResourceAction(self, cad, gid, reason)
            self.cad[str(cad)] = ra
            self.generation[cad.resource_str()] = ra

        # Create dummy to give start signal
        dummy = ResourceAction(self, None, gid, reason)
        # Dispatch all actions
        # Will block on dependencies and dummy
        for r in self.generation.values():
            self.agent.add_future(r.execute(dummy, self.generation, self.cache))

        # Listen for completion
        self.agent.add_future(self.mark_deployment_as_finished(self.generation.values(), reason, gid))

        # Start running
        dummy.future.set_result(ResourceActionResult(True, False, False))

    @gen.coroutine
    def mark_deployment_as_finished(self, resource_actions, reason, gid):
        futures = [resource_action.future for resource_action in resource_actions]
        yield futures  # Wait until deployment finishes
        with (yield self.agent.critical_ratelimiter.acquire()):
            if not self.finished():
                return
            if self._resume_reason is not None:
                self.logger.info("Resuming run '%s'", self._resume_reason)
                self.agent.add_future(self.agent.get_latest_version_for_agent(reason=self._resume_reason,
                                                                              incremental_deploy=False, is_repair_run=True))
                self._resume_reason = None

    def notify_ready(self, resourceid, send_events, state, change, changes):
        if resourceid not in self.cad:
            # received CAD notification for which no resource are waiting, so return
            return
        self.cad[resourceid].notify(send_events, state, change, changes)

    def dump(self):
        print("Waiting:")
        for r in self.generation.values():
            print(r.long_string())
        print("Ready to run:")
        for r in self.queue:
            print(r.long_string())

    def get_client(self):
        return self.agent.get_client()


class AgentInstance(object):

    def __init__(self, process: "Agent", name: str, uri: str) -> None:
        self.process = process
        self.name = name
        self._uri = uri

        self.logger: Logger = LOGGER.getChild(self.name)

        # the lock for changing the current ongoing deployment
        self.critical_ratelimiter = locks.Semaphore(1)
        # lock for dryrun tasks
        self.dryrunlock = locks.Semaphore(1)

        # multi threading control
        # threads to setup connections
        self.provider_thread_pool: ThreadPoolExecutor = ThreadPoolExecutor(1, thread_name_prefix="ProviderPool_%s" % name)
        # threads to work
        self.thread_pool: ThreadPoolExecutor = ThreadPoolExecutor(process.poolsize, thread_name_prefix="Pool_%s" % name)
        self.ratelimiter = locks.Semaphore(process.poolsize)

        self._env_id: uuid.UUID = process._env_id

        self.sessionid = process.sessionid

        # init
        self._cache = AgentCache()
        self._nq = ResourceScheduler(self, self.process.environment, name, self._cache, ratelimiter=self.ratelimiter)
        self._time_triggered_actions = set()
        self._enabled = False

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

    @gen.coroutine
    def stop(self):
        self.provider_thread_pool.shutdown(wait=False)
        self.thread_pool.shutdown(wait=False)

    @property
    def environment(self):
        return self.process.environment

    def get_client(self):
        return self.process._client

    @property
    def uri(self):
        return self._uri

    def is_enabled(self):
        return self._enabled

    def add_future(self, future):
        self.process.add_future(future)

    def unpause(self):
        if self.is_enabled():
            return 200, "already running"

        self.logger.info("Agent assuming primary role for %s", self.name)

        self._enable_time_triggers()
        self._enabled = True
        return 200, "unpaused"

    def pause(self, reason="agent lost primary role"):
        if not self.is_enabled():
            return 200, "already paused"

        self.logger.info("Agent %s stopped because %s", self.name, reason)

        self._disable_time_triggers()
        self._enabled = False
        return 200, "paused"

    def _enable_time_triggers(self):

        @gen.coroutine
        def deploy_action():
            now = datetime.datetime.now()
            yield self.get_latest_version_for_agent(
                reason="Periodic deploy started at %s" % (now.strftime(const.TIME_LOGFMT)),
                incremental_deploy=True,
                is_repair_run=False)

        @gen.coroutine
        def repair_action():
            now = datetime.datetime.now()
            yield self.get_latest_version_for_agent(
                reason="Repair run started at %s" % (now.strftime(const.TIME_LOGFMT)),
                incremental_deploy=False,
                is_repair_run=True)

        now = datetime.datetime.now()
        if self._deploy_interval > 0:
            self.logger.info("Scheduling periodic deploy with interval %d and splay %d (first run at %s)",
                             self._deploy_interval,
                             self._deploy_splay_value,
                             (now + datetime.timedelta(seconds=self._deploy_splay_value)).strftime(const.TIME_LOGFMT)
                             )
            self._enable_time_trigger(deploy_action, self._deploy_interval, self._deploy_splay_value)
        if self._repair_interval > 0:
            self.logger.info("Scheduling repair with interval %d and splay %d (first run at %s)",
                             self._repair_interval,
                             self._repair_splay_value,
                             (now + datetime.timedelta(seconds=self._repair_splay_value)).strftime(const.TIME_LOGFMT)
                             )
            self._enable_time_trigger(repair_action, self._repair_interval, self._repair_splay_value)

    def _enable_time_trigger(self, action, interval, splay):
        self.process._sched.add_action(action, interval, splay)
        self._time_triggered_actions.add(action)

    def _disable_time_triggers(self):
        for action in self._time_triggered_actions:
            self.process._sched.remove(action)
        self._time_triggered_actions.clear()

    def notify_ready(self, resourceid, send_events, state, change, changes):
        self._nq.notify_ready(resourceid, send_events, state, change, changes)

    def _can_get_resources(self):
        if self._getting_resources:
            self.logger.info("Attempting to get resource while get is in progress")
            return False
        if time.time() < self._get_resource_timeout:
            self.logger.info("Attempting to get resources during backoff %g seconds left, last download took %d seconds",
                             self._get_resource_timeout - time.time(), self._get_resource_duration)
            return False
        return True

    @gen.coroutine
    def get_provider(self, resource: Resource) -> Generator[Any, Any, ResourceHandler]:
        provider = yield self.provider_thread_pool.submit(handler.Commander.get_provider, self._cache, self, resource)
        provider.set_cache(self._cache)
        return provider

    @gen.coroutine
    def get_latest_version_for_agent(self, reason="Unknown", incremental_deploy=False, is_repair_run=False):
        """
            Get the latest version for the given agent (this is also how we are notified)

            :param reason: the reason this deploy was started
        """
        if not self._can_get_resources():
            self.logger.warning("%s aborted by rate limiter", reason)
            return
        with (yield self.critical_ratelimiter.acquire()):
            if not self._can_get_resources():
                self.logger.warning("%s aborted by rate limiter", reason)
                return

            self.logger.debug("Getting latest resources for %s", reason)
            self._getting_resources = True
            start = time.time()
            try:
                result = yield self.get_client().get_resources_for_agent(tid=self._env_id, agent=self.name,
                                                                         incremental_deploy=incremental_deploy)
            finally:
                self._getting_resources = False
            end = time.time()
            self._get_resource_duration = end - start
            self._get_resource_timeout = GET_RESOURCE_BACKOFF * self._get_resource_duration + end
            if result.code == 404:
                self.logger.info("No released configuration model version available for %s", reason)
            elif result.code == 409:
                self.logger.warning("We are not currently primary during %s: %s", reason, result.result)
            elif result.code != 200:
                self.logger.warning("Got an error while pulling resources for %s. %s",
                                    reason,
                                    result.result)

            else:
                restypes = set([res["resource_type"] for res in result.result["resources"]])
                resources = []
                yield self.process._ensure_code(self._env_id, result.result["version"], restypes)
                try:
                    undeployable = {}
                    for res in result.result["resources"]:
                        state = const.ResourceState[res["status"]]
                        if state in const.UNDEPLOYABLE_STATES:
                            undeployable[res["id"]] = state

                        data = res["attributes"]
                        data["id"] = res["id"]
                        resource = Resource.deserialize(data)
                        resources.append(resource)
                        self.logger.debug("Received update for %s", resource.id)
                except TypeError:
                    self.logger.exception("Failed to receive update for %s", reason)

                self.logger.debug("Pulled %d resources because %s", len(resources), reason)

                if len(resources) > 0:
                    self._nq.reload(resources, undeployable, reason=reason, is_repair=is_repair_run)

    @gen.coroutine
    def dryrun(self, dry_run_id, version):
        self.add_future(self.do_run_dryrun(version, dry_run_id))
        return 200

    @gen.coroutine
    def do_run_dryrun(self, version, dry_run_id):
        with (yield self.dryrunlock.acquire()):
            with (yield self.ratelimiter.acquire()):
                result = yield self.get_client().get_resources_for_agent(tid=self._env_id, agent=self.name, version=version)
                if result.code == 404:
                    self.logger.warning("Version %s does not exist, can not run dryrun", version)
                    return

                elif result.code != 200:
                    self.logger.warning("Got an error while pulling resources and version %s", version)
                    return

                resources = result.result["resources"]
                restypes = set([res["resource_type"] for res in resources])

                # TODO: handle different versions for dryrun and deploy!
                yield self.process._ensure_code(self._env_id, version, restypes)

                self._cache.open_version(version)

                for res in resources:
                    ctx = handler.HandlerContext(res, True)
                    started = datetime.datetime.now()
                    provider = None
                    try:
                        if const.ResourceState[res["status"]] in const.UNDEPLOYABLE_STATES:
                            ctx.exception("Skipping %(resource_id)s because in undeployable state %(status)s",
                                          resource_id=res["id"], status=res["status"])
                            yield self.get_client().dryrun_update(tid=self._env_id, id=dry_run_id, resource=res["id"],
                                                                  changes={})
                            continue

                        data = res["attributes"]
                        data["id"] = res["id"]
                        resource = Resource.deserialize(data)
                        self.logger.debug("Running dryrun for %s", resource.id)

                        try:
                            provider = yield self.get_provider(resource)
                        except Exception as e:
                            ctx.exception("Unable to find a handler for %(resource_id)s (exception: %(exception)s",
                                          resource_id=str(resource.id), exception=str(e))
                            yield self.get_client().dryrun_update(tid=self._env_id, id=dry_run_id, resource=res["id"],
                                                                  changes={"handler": {"current": "FAILED",
                                                                                       "desired": "Unable to find a handler"}})
                        else:
                            try:
                                yield self.thread_pool.submit(provider.execute, ctx, resource, dry_run=True)
                                changes = ctx.changes
                                if changes is None:
                                    changes = {}
                                if(ctx.status == const.ResourceState.failed):
                                    changes["handler"] = {"current": "FAILED", "desired": "Handler failed"}
                                yield self.get_client().dryrun_update(tid=self._env_id, id=dry_run_id, resource=res["id"],
                                                                      changes=changes)
                            except Exception as e:
                                ctx.exception("Exception during dryrun for %(resource_id)s (exception: %(exception)s",
                                              resource_id=str(resource.id), exception=str(e))
                                changes = ctx.changes
                                if changes is None:
                                    changes = {}
                                changes["handler"] = {"current": "FAILED", "desired": "Handler failed"}
                                yield self.get_client().dryrun_update(tid=self._env_id, id=dry_run_id, resource=res["id"],
                                                                      changes=changes)

                    except Exception:
                        ctx.exception("Unable to process resource for dryrun.")
                        changes = {}
                        changes["handler"] = {"current": "FAILED", "desired": "Resource Deserialization Failed"}
                        yield self.get_client().dryrun_update(tid=self._env_id, id=dry_run_id, resource=res["id"],
                                                              changes=changes)
                    finally:
                        if provider is not None:
                            provider.close()

                        finished = datetime.datetime.now()
                        yield self.get_client().resource_action_update(tid=self._env_id, resource_ids=[res["id"]],
                                                                       action_id=ctx.action_id,
                                                                       action=const.ResourceAction.dryrun,
                                                                       started=started,
                                                                       finished=finished,
                                                                       messages=ctx.logs,
                                                                       status=const.ResourceState.dry)

                self._cache.close_version(version)

    @gen.coroutine
    def get_facts(self, resource):
        with (yield self.ratelimiter.acquire()):
            yield self.process._ensure_code(self._env_id, resource["model"], [resource["resource_type"]])
            ctx = handler.HandlerContext(resource)
            started = datetime.datetime.now()
            provider = None
            try:
                data = resource["attributes"]
                data["id"] = resource["id"]
                resource_obj = Resource.deserialize(data)

                version = resource_obj.id.version
                try:
                    self._cache.open_version(version)
                    provider = yield self.get_provider(resource_obj)
                    result = yield self.thread_pool.submit(provider.check_facts, ctx, resource_obj)
                    parameters = [{"id": name, "value": value, "resource_id": resource_obj.id.resource_str(), "source": "fact"}
                                  for name, value in result.items()]
                    yield self.get_client().set_parameters(tid=self._env_id, parameters=parameters)
                    finished = datetime.datetime.now()
                    yield self.get_client().resource_action_update(tid=self._env_id,
                                                                   resource_ids=[resource_obj.id.resource_str()],
                                                                   action_id=ctx.action_id,
                                                                   action=const.ResourceAction.getfact,
                                                                   started=started,
                                                                   finished=finished,
                                                                   messages=ctx.logs)

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


class Agent(SessionEndpoint):
    """
        An agent to enact changes upon resources. This agent listens to the
        message bus for changes.
    """

    def __init__(self, hostname=None, agent_map=None, code_loader=True, environment=None, poolsize=1,
                 cricital_pool_size=5):
        super().__init__("agent", timeout=cfg.server_timeout.get(), reconnect_delay=cfg.agent_reconnect_delay.get())

        self.poolsize = poolsize
        self.ratelimiter = locks.Semaphore(poolsize)
        self.critical_ratelimiter = locks.Semaphore(cricital_pool_size)
        self.thread_pool = ThreadPoolExecutor(poolsize, thread_name_prefix="mainpool")

        if agent_map is None:
            agent_map = cfg.agent_map.get()

        self.agent_map = agent_map
        self._storage = self.check_storage()

        if environment is None:
            environment = cfg.environment.get()
            if environment is None:
                raise Exception("The agent requires an environment to be set.")
        self.set_environment(environment)

        self._instances = {}

        if code_loader:
            self._env = env.VirtualEnv(self._storage["env"])
            self._env.use_virtual_env()
            self._loader = CodeLoader(self._storage["code"])
        else:
            self._loader = None

        if hostname is not None:
            self.add_end_point_name(hostname)

        else:
            # load agent names from the config file
            agent_names = cfg.agent_names.get()
            if agent_names is not None:
                names = [x.strip() for x in agent_names.split(",")]
                for name in names:
                    if "$" in name:
                        name = name.replace("$node-name", self.node_name)

                    self.add_end_point_name(name)

        # cache reference to THIS ioloop for handlers to push requests on it
        # defer to start, just to be sure
        self._io_loop = None

    @gen.coroutine
    def stop(self):
        yield super(Agent, self).stop()
        self.thread_pool.shutdown(wait=False)
        for instance in self._instances.values():
            yield instance.stop()

    @gen.coroutine
    def start(self):
        # cache reference to THIS ioloop for handlers to push requests on it
        self._io_loop = ioloop.IOLoop.current()
        yield super(Agent, self).start()

    def add_end_point_name(self, name):
        SessionEndpoint.add_end_point_name(self, name)

        hostname = "local:"
        if name in self.agent_map:
            hostname = self.agent_map[name]

        self._instances[name] = AgentInstance(self, name, hostname)

    def unpause(self, name):
        if name not in self._instances:
            return 404, "No such agent"

        return self._instances[name].unpause()

    def pause(self, name):
        if name not in self._instances:
            return 404, "No such agent"

        return self._instances[name].pause()

    @protocol.handle(methods.set_state)
    @gen.coroutine
    def set_state(self, agent, enabled):
        if enabled:
            return self.unpause(agent)
        else:
            return self.pause(agent)

    @gen.coroutine
    def on_reconnect(self) -> NoneGen:
        for name in self._instances.keys():
            result = yield self._client.get_state(tid=self._env_id, sid=self.sessionid, agent=name)
            if result.code == 200:
                state = result.result
                if "enabled" in state and isinstance(state["enabled"], bool):
                    self.set_state(name, state["enabled"])
                else:
                    LOGGER.warning("Server reported invalid state %s" % (repr(state)))
            else:
                LOGGER.warning("could not get state from the server")

    @gen.coroutine
    def on_disconnect(self) -> NoneGen:
        LOGGER.warning("Connection to server lost, taking agents offline")
        for agent_instance in self._instances.values():
            agent_instance.pause("Connection to server lost")

    @gen.coroutine
    def get_latest_version(self):
        """
            Get the latest version of managed resources for all agents
        """
        for agent in self._instances.values():
            yield agent.get_latest_version_for_agent(reason="call to get_latest_version on agent")

    @gen.coroutine
    def _ensure_code(self, environment, version, resourcetypes):
        """
            Ensure that the code for the given environment and version is loaded
        """
        if self._loader is not None:
            for rt in resourcetypes:
                result = yield self._client.get_code(environment, version, rt)

                if result.code == 200:
                    for hash_value, (path, name, content, requires) in result.result["sources"].items():
                        try:
                            LOGGER.debug("Installing handler %s for %s", rt, name)
                            yield self._install(hash_value, name, content, requires)
                            LOGGER.debug("Installed handler %s for %s", rt, name)
                        except Exception:
                            LOGGER.exception("Failed to install handler %s for %s", rt, name)

    @gen.coroutine
    def _install(self, hash_value, module_name, module_source, module_requires):
        yield self.thread_pool.submit(self._env.install_from_list, module_requires, True)
        yield self.thread_pool.submit(self._loader.deploy_version, hash_value, module_name, module_source)

    @protocol.handle(methods.trigger, env="tid", agent="id")
    @gen.coroutine
    def trigger_update(self, env, agent, incremental_deploy):
        """
            Trigger an update
        """
        if agent not in self._instances:
            return 200

        if not self._instances[agent].is_enabled():
            return 500, "Agent is not _enabled"

        LOGGER.info("Agent %s got a trigger to update in environment %s", agent, env)
        future = self._instances[agent].get_latest_version_for_agent(reason="call to trigger_update",
                                                                     incremental_deploy=incremental_deploy)
        self.add_future(future)
        return 200

    @protocol.handle(methods.resource_event, env="tid", agent="id")
    @gen.coroutine
    def resource_event(self, env, agent: str, resource: str, send_events: bool,
                       state: const.ResourceState, change: const.Change, changes: dict):
        if env != self._env_id:
            LOGGER.warning("received unexpected resource event: tid: %s, agent: %s, resource: %s, state: %s, tid unknown",
                           env, agent, resource, state)
            return 200

        if agent not in self._instances:
            LOGGER.warning("received unexpected resource event: tid: %s, agent: %s, resource: %s, state: %s, agent unknown",
                           env, agent, resource, state)
            return 200

        LOGGER.debug("Agent %s got a resource event: tid: %s, agent: %s, resource: %s, state: %s",
                     agent, env, agent, resource, state)
        self._instances[agent].notify_ready(resource, send_events, state, change, changes)

        return 200

    @protocol.handle(methods.do_dryrun, env="tid", dry_run_id="id")
    @gen.coroutine
    def run_dryrun(self, env, dry_run_id, agent, version):
        """
           Run a dryrun of the given version
        """
        assert env == self._env_id

        if agent not in self._instances:
            return 200

        LOGGER.info("Agent %s got a trigger to run dryrun %s for version %s in environment %s",
                    agent, dry_run_id, version, env)

        return (yield self._instances[agent].dryrun(dry_run_id, version))

    def check_storage(self):
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
    @gen.coroutine
    def get_facts(self, env, agent, resource):
        if agent not in self._instances:
            return 200

        return (yield self._instances[agent].get_facts(resource))

    @protocol.handle(methods.get_status)
    @gen.coroutine
    def get_status(self):
        return 200, collect_report(self)
