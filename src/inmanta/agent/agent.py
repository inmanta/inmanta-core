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

import base64
from concurrent.futures.thread import ThreadPoolExecutor
import datetime
import hashlib
import logging
import os
import random
import uuid
import time

from tornado import gen, locks
from inmanta import env, const
from inmanta import methods
from inmanta import protocol
from inmanta.agent import handler
from inmanta.loader import CodeLoader
from inmanta.protocol import Scheduler, AgentEndPoint
from inmanta.resources import Resource
from tornado.concurrent import Future
from inmanta.agent.cache import AgentCache
from inmanta.agent import config as cfg
from inmanta.agent.reporting import collect_report

LOGGER = logging.getLogger(__name__)
GET_RESOURCE_BACKOFF = 5


class ResourceActionResult(object):

    def __init__(self, success, receive_events, cancel):
        self.success = success
        self.receive_events = receive_events
        self.cancel = cancel

    def __add__(self, other):
        return ResourceActionResult(self.success and other.success,
                                    self.receive_events or other.receive_events,
                                    self.cancel or other.cancel)

    def __str__(self, *args, **kwargs):
        return "%r %r %r" % (self.success, self.receive_events, self.cancel)


class ResourceAction(object):

    def __init__(self, scheduler, resource, gid):
        """
            :param gid A unique identifier to identify a deploy. This is local to this agent.
        """
        self.scheduler = scheduler
        self.resource = resource
        if self.resource is not None:
            self.resource_id = resource.id
        self.future = Future()
        self.running = False
        self.gid = gid
        self.status = None
        self.change = None
        self.changes = None
        self.undeployable = None

    def is_running(self):
        return self.running

    def is_done(self):
        return self.future.done()

    def cancel(self):
        if not self.is_running() and not self.is_done():
            LOGGER.info("Cancelled deploy of %s %s", self.gid, self.resource)
            self.future.set_result(ResourceActionResult(False, False, True))

    @gen.coroutine
    def _execute(self, ctx: handler.HandlerContext, events: dict, cache: AgentCache) -> (bool, bool):
        """
            :param ctx The context to use during execution of this deploy
            :param events Possible events that are available for this resource
            :param cache The cache instance to use
            :return (success, send_event) Return whether the execution was successful and whether a change event should be sent
                                          to provides of this resource.
        """
        ctx.debug("Start deploy %(deploy_id)s of resource %(resource_id)s",
                  deploy_id=self.gid, resource_id=self.resource_id)
        provider = None

        try:
            provider = yield self.scheduler.agent.get_provider(self.resource)
        except Exception:
            if provider is not None:
                provider.close()

            cache.close_version(self.resource.id.version)
            ctx.set_status(const.ResourceState.unavailable)
            ctx.exception("Unable to find a handler for %(resource_id)s", resource_id=str(self.resource.id))
            return False, False

        yield self.scheduler.agent.thread_pool.submit(provider.execute, ctx, self.resource)

        send_event = (hasattr(self.resource, "send_event") and self.resource.send_event)

        if ctx.status is not const.ResourceState.deployed:
            provider.close()
            cache.close_version(self.resource.id.version)
            return False, send_event

        if len(events) > 0 and provider.can_process_events():
            ctx.info("Sending events to %(resource_id)s because of modified dependencies", resource_id=str(self.resource.id))
            yield self.scheduler.agent.thread_pool.submit(provider.process_events, ctx, self.resource, events)

        provider.close()
        cache.close_version(self.resource_id.version)

        return True, send_event

    @gen.coroutine
    def execute(self, dummy, generation, cache):
        LOGGER.log(const.LogLevel.TRACE.value, "Entering %s %s", self.gid, self.resource)
        cache.open_version(self.resource.id.version)

        self.dependencies = [generation[x.resource_str()] for x in self.resource.requires]
        waiters = [x.future for x in self.dependencies]
        waiters.append(dummy.future)
        results = yield waiters

        with (yield self.scheduler.ratelimiter.acquire()):
            start = datetime.datetime.now()
            ctx = handler.HandlerContext(self.resource)

            LOGGER.info("start run %s %s", self.gid, self.resource.id)
            ctx.debug("start run for resource with id %(deploy_id)s", deploy_id=self.gid)
            self.running = True
            if self.is_done():
                # Action is cancelled
                LOGGER.log(const.LogLevel.TRACE.value, "%s %s is no longer active" % (self.gid, self.resource))
                self.running = False
                ctx.set_status(const.ResourceState.cancelled)
                return

            result = sum(results, ResourceActionResult(True, False, False))

            if result.cancel:
                # self.running will be set to false when self.cancel is called
                # Only happens when global cancel has not cancelled us but our predecessors have already been cancelled
                ctx.set_status(const.ResourceState.cancelled)
                return

            if not result.success:
                ctx.set_status(const.ResourceState.skipped)
                success = False
                send_event = False
            elif self.undeployable is not None:
                ctx.set_status(self.undeployable)
                success = False
                send_event = False
            else:
                if result.receive_events:
                    received_events = {x.resource_id: dict(status=x.status, change=x.change,
                                                           changes=x.changes.get(str(x.resource_id), {}))
                                       for x in self.dependencies}
                else:
                    received_events = {}
                success, send_event = yield self._execute(ctx=ctx, events=received_events, cache=cache)

            LOGGER.info("end run %s", self.resource)

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

    def __str__(self):
        if self.resource is None:
            return "DUMMY"

        status = ""
        if self.is_done():
            status = " Done"
        elif self.is_running():
            status = " Running"

        return self.resource.id.resource_str() + status

    def long_string(self):
        return "%s awaits %s" % (self.resource.id.resource_str(), " ".join([str(aw) for aw in self.dependencies]))


class RemoteResourceAction(ResourceAction):

    def __init__(self, scheduler, resource_id, gid):
        super(RemoteResourceAction, self).__init__(scheduler, None, gid)
        self.resource_id = resource_id

    @gen.coroutine
    def execute(self, dummy, generation, cache):
        yield dummy.future
        try:
            result = yield self.scheduler.get_client().get_resource(self.scheduler.agent._env_id, str(self.resource_id),
                                                                    logs=True, log_action=const.ResourceAction.deploy,
                                                                    log_limit=1)
            if result.code != 200:
                LOGGER.error("Failed to get the status for remote resource %s (%s)", str(self.resource_id),
                             result.result)

            status = const.ResourceState[result.result["resource"]["status"]]
            if status == const.ResourceState.available or self.future.done():
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

    def notify(self, send_events, status, change, changes):
        if not self.future.done():
            self.status = status
            self.change = change
            self.changes = changes
            self.future.set_result(ResourceActionResult(True, send_events, False))


class ResourceScheduler(object):

    def __init__(self, agent, env_id, name, cache, ratelimiter):
        self.generation = {}
        self.cad = {}
        self._env_id = env_id
        self.agent = agent
        self.cache = cache
        self.name = name
        self.ratelimiter = ratelimiter
        self.version = 0

    def reload(self, resources, undeployable={}):
        version = resources[0].id.get_version

        self.version = version

        for ra in self.generation.values():
            ra.cancel()

        gid = uuid.uuid4()
        self.generation = {r.id.resource_str(): ResourceAction(self, r, gid) for r in resources}

        for key, res in self.generation.items():
            vid = str(res.resource.id)
            if vid in undeployable:
                self.generation[key].undeployable = undeployable[vid]

        cross_agent_dependencies = [q for r in resources for q in r.requires if q.get_agent_name() != self.name]
        for cad in cross_agent_dependencies:
            ra = RemoteResourceAction(self, cad, gid)
            self.cad[str(cad)] = ra
            self.generation[cad.resource_str()] = ra

        dummy = ResourceAction(self, None, gid)
        for r in self.generation.values():
            r.execute(dummy, self.generation, self.cache)
        dummy.future.set_result(ResourceActionResult(True, False, False))

    def notify_ready(self, resourceid, send_events, state, change, changes):
        if resourceid not in self.cad:
            LOGGER.warning("Agent %s received CAD notification that was not required, %s", self.name, resourceid)
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

    def __init__(self, process, name: str, uri: str):
        self.process = process
        self.name = name
        self._uri = uri

        # the lock for changing the current ongoing deployment
        self.critical_ratelimiter = locks.Semaphore(1)
        # lock for dryrun tasks
        self.dryrunlock = locks.Semaphore(1)

        # multi threading control
        # threads to setup connections
        self.provider_thread_pool = ThreadPoolExecutor(1)
        # threads to work
        self.thread_pool = ThreadPoolExecutor(process.poolsize)
        self.ratelimiter = locks.Semaphore(process.poolsize)

        self._env_id = process._env_id

        self.sessionid = process.sessionid

        # init
        self._cache = AgentCache()
        self._nq = ResourceScheduler(self, self.process.environment, name, self._cache, ratelimiter=self.ratelimiter)
        self._enabled = None

        # do regular deploys
        self._deploy_interval = cfg.agent_interval.get()
        self._splay_interval = cfg.agent_splay.get()
        self._splay_value = random.randint(0, self._splay_interval)

        self._getting_resources = False
        self._get_resource_timeout = 0

    @property
    def environment(self):
        return self.process.environment

    def get_client(self):
        return self.process._client

    @property
    def uri(self):
        return self._uri

    def is_enabled(self):
        return self._enabled is not None

    def add_future(self, future):
        self.process.add_future(future)

    def unpause(self):
        if self._enabled is not None:
            return 200, "already running"

        LOGGER.info("Agent assuming primary role for %s" % self.name)

        @gen.coroutine
        def action():
            yield self.get_latest_version_for_agent()

        self._enabled = action
        self.process._sched.add_action(action, self._deploy_interval, self._splay_value)
        return 200, "unpaused"

    def pause(self):
        if self._enabled is None:
            return 200, "already paused"

        LOGGER.info("Agent lost primary role for %s" % self.name)

        token = self._enabled
        self.process._sched.remove(token)
        self._enabled = None
        return 200, "paused"

    def notify_ready(self, resourceid, send_events, state, change, changes):
        self._nq.notify_ready(resourceid, send_events, state, change, changes)

    def _can_get_resources(self):
        if self._getting_resources:
            LOGGER.info("%s Attempting to get resource while get is in progress", self.name)
            return False
        if time.time() < self._get_resource_timeout:
            LOGGER.info("%s Attempting to get resources during backoff %g seconds left, last download took %d seconds",
                        self.name, self._get_resource_timeout - time.time(), self._get_resource_duration)
            return False
        return True

    @gen.coroutine
    def get_provider(self, resource):
        provider = yield self.provider_thread_pool.submit(handler.Commander.get_provider, self._cache, self, resource)
        provider.set_cache(self._cache)
        return provider

    @gen.coroutine
    def get_latest_version_for_agent(self):
        """
            Get the latest version for the given agent (this is also how we are notified)
        """
        if not self._can_get_resources():
            return
        with (yield self.critical_ratelimiter.acquire()):
            if not self._can_get_resources():
                return
            LOGGER.debug("Getting latest resources for %s" % self.name)
            self._getting_resources = True
            start = time.time()
            try:
                result = yield self.get_client().get_resources_for_agent(tid=self._env_id, agent=self.name)
            finally:
                self._getting_resources = False
            end = time.time()
            self._get_resource_duration = end - start
            self._get_resource_timeout = GET_RESOURCE_BACKOFF * self._get_resource_duration + end
            if result.code == 404:
                LOGGER.info("No released configuration model version available for agent %s", self.name)
            elif result.code != 200:
                LOGGER.warning("Got an error while pulling resources for agent %s. %s", self.name, result.result)

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
                        LOGGER.debug("Received update for %s", resource.id)
                except TypeError:
                    LOGGER.exception("Failed to receive update")

                if len(resources) > 0:
                    self._nq.reload(resources, undeployable)

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
                    LOGGER.warning("Version %s does not exist, can not run dryrun", version)
                    return

                elif result.code != 200:
                    LOGGER.warning("Got an error while pulling resources for agent %s and version %s", self.name, version)
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
                        LOGGER.debug("Running dryrun for %s", resource.id)

                        try:
                            provider = yield self.get_provider(resource)
                        except Exception as e:
                            ctx.exception("Unable to find a handler for %(resource_id)s (exception: %(exception)s",
                                          resource_id=str(resource.id), exception=str(e))
                            yield self.get_client().dryrun_update(tid=self._env_id, id=dry_run_id, resource=res["id"],
                                                                  changes={})
                        else:
                            yield self.thread_pool.submit(provider.execute, ctx, resource, dry_run=True)
                            yield self.get_client().dryrun_update(tid=self._env_id, id=dry_run_id, resource=res["id"],
                                                                  changes=ctx.changes)

                    except TypeError:
                        ctx.exception("Unable to process resource for dryrun.")

                    finally:
                        if provider is not None:
                            provider.close()

                        finished = datetime.datetime.now()
                        self.get_client().resource_action_update(tid=self._env_id, resource_ids=[res["id"]],
                                                                 action_id=ctx.action_id, action=const.ResourceAction.dryrun,
                                                                 started=started, finished=finished, messages=ctx.logs,
                                                                 status=const.ResourceState.dry)

                self._cache.close_version(version)

    @gen.coroutine
    def do_restore(self, restore_id, snapshot_id, resources):
        with (yield self.ratelimiter.acquire()):

            LOGGER.info("Start a restore %s", restore_id)

            yield self.process._ensure_code(self._env_id, resources[0][1]["model"],
                                            [res[1]["resource_type"] for res in resources])

            version = resources[0][1]["model"]
            self._cache.open_version(version)

            for restore, resource in resources:
                start = datetime.datetime.now()
                provider = None
                try:
                    data = resource["attributes"]
                    data["id"] = resource["id"]
                    resource_obj = Resource.deserialize(data)
                    provider = yield self.get_provider(resource_obj)
                    if not hasattr(resource_obj, "allow_restore") or not resource_obj.allow_restore:
                        yield self.get_client().update_restore(tid=self._env_id,
                                                               id=restore_id,
                                                               resource_id=str(resource_obj.id),
                                                               start=start,
                                                               stop=datetime.datetime.now(),
                                                               success=False,
                                                               error=False,
                                                               msg="Resource %s does not allow restore" % resource["id"])
                        continue

                    try:
                        yield self.thread_pool.submit(provider.restore, resource_obj, restore["content_hash"])
                        yield self.get_client().update_restore(tid=self._env_id, id=restore_id,
                                                               resource_id=str(resource_obj.id),
                                                               success=True, error=False,
                                                               start=start, stop=datetime.datetime.now(), msg="")
                    except NotImplementedError:
                        yield self.get_client().update_restore(tid=self._env_id, id=restore_id,
                                                               resource_id=str(resource_obj.id),
                                                               success=False, error=False,
                                                               start=start, stop=datetime.datetime.now(),
                                                               msg="The handler for resource "
                                                               "%s does not support restores" % resource["id"])

                except Exception:
                    LOGGER.exception("Unable to find a handler for %s", resource["id"])
                    yield self.get_client().update_restore(tid=self._env_id, id=restore_id,
                                                           resource_id=resource_obj.id.resource_str(),
                                                           success=False, error=False,
                                                           start=start, stop=datetime.datetime.now(),
                                                           msg="Unable to find a handler to restore a snapshot of resource %s" %
                                                           resource["id"])
                finally:
                    if provider is not None:
                        provider.close()
            self._cache.close_version(version)

            return 200

    @gen.coroutine
    def do_snapshot(self, snapshot_id, resources):
        with (yield self.ratelimiter.acquire()):
            LOGGER.info("Start snapshot %s", snapshot_id)

            yield self.process._ensure_code(self._env_id, resources[0]["model"],
                                            [res["resource_type"] for res in resources])

            version = resources[0]["model"]
            self._cache.open_version(version)

            for resource in resources:
                start = datetime.datetime.now()
                provider = None
                try:
                    data = resource["attributes"]
                    data["id"] = resource["id"]
                    resource_obj = Resource.deserialize(data)
                    provider = yield self.get_provider(resource_obj)

                    if not hasattr(resource_obj, "allow_snapshot") or not resource_obj.allow_snapshot:
                        yield self.get_client().update_snapshot(tid=self._env_id, id=snapshot_id,
                                                                resource_id=resource_obj.id.resource_str(), snapshot_data="",
                                                                start=start, stop=datetime.datetime.now(), size=0,
                                                                success=False, error=False,
                                                                msg="Resource %s does not allow snapshots" % resource["id"])
                        continue

                    try:
                        result = yield self.thread_pool.submit(provider.snapshot, resource_obj)
                        if result is not None:
                            sha1sum = hashlib.sha1()
                            sha1sum.update(result)
                            content_id = sha1sum.hexdigest()
                            yield self.get_client().upload_file(id=content_id, content=base64.b64encode(result).decode("ascii"))

                            yield self.get_client().update_snapshot(tid=self._env_id, id=snapshot_id,
                                                                    resource_id=resource_obj.id.resource_str(),
                                                                    snapshot_data=content_id,
                                                                    start=start, stop=datetime.datetime.now(),
                                                                    size=len(result), success=True, error=False,
                                                                    msg="")
                        else:
                            raise Exception("Snapshot returned no data")

                    except NotImplementedError:
                        yield self.get_client().update_snapshot(tid=self._env_id, id=snapshot_id, error=False,
                                                                resource_id=resource_obj.id.resource_str(),
                                                                snapshot_data="",
                                                                start=start, stop=datetime.datetime.now(),
                                                                size=0, success=False,
                                                                msg="The handler for resource "
                                                                "%s does not support snapshots" % resource["id"])
                    except Exception:
                        LOGGER.exception("An exception occurred while creating the snapshot of %s", resource["id"])
                        yield self.get_client().update_snapshot(tid=self._env_id, id=snapshot_id, snapshot_data="",
                                                                resource_id=resource_obj.id.resource_str(), error=True,
                                                                start=start,
                                                                stop=datetime.datetime.now(),
                                                                size=0, success=False,
                                                                msg="The handler for resource "
                                                                "%s does not support snapshots" % resource["id"])

                except Exception:
                    LOGGER.exception("Unable to find a handler for %s", resource["id"])
                    yield self.get_client().update_snapshot(tid=self._env_id,
                                                            id=snapshot_id, snapshot_data="",
                                                            resource_id=resource_obj.id.resource_str(), error=False,
                                                            start=start, stop=datetime.datetime.now(),
                                                            size=0, success=False,
                                                            msg="Unable to find a handler for %s" % resource["id"])
                finally:
                    if provider is not None:
                        provider.close()

            self._cache.close_version(version)
            return 200

    @gen.coroutine
    def get_facts(self, resource):
        with (yield self.ratelimiter.acquire()):
            yield self.process._ensure_code(self._env_id, resource["model"], [resource["resource_type"]])
            ctx = handler.HandlerContext(resource)

            provider = None
            try:
                data = resource["attributes"]
                data["id"] = resource["id"]
                resource_obj = Resource.deserialize(data)

                version = resource_obj.id.version
                try:
                    if const.ResourceState[resource["status"]] in const.UNDEPLOYABLE_STATES:
                        LOGGER.exception("Skipping %s because in undeployable state %s", resource["id"], resource["status"])
                        return 200

                    self._cache.open_version(version)
                    provider = yield self.get_provider(resource_obj)
                    result = yield self.thread_pool.submit(provider.check_facts, ctx, resource_obj)
                    parameters = [{"id": name, "value": value, "resource_id": resource_obj.id.resource_str(), "source": "fact"}
                                  for name, value in result.items()]
                    yield self.get_client().set_parameters(tid=self._env_id, parameters=parameters)

                except Exception:
                    LOGGER.exception("Unable to retrieve fact")
                finally:
                    self._cache.close_version(version)

            except Exception:
                LOGGER.exception("Unable to find a handler for %s", resource["id"])
                return 500
            finally:
                if provider is not None:
                    provider.close()
            return 200


class Agent(AgentEndPoint):
    """
        An agent to enact changes upon resources. This agent listens to the
        message bus for changes.
    """

    def __init__(self, io_loop, hostname=None, agent_map=None, code_loader=True, environment=None, poolsize=1,
                 cricital_pool_size=5):
        super().__init__("agent", io_loop, timeout=cfg.server_timeout.get(), reconnect_delay=cfg.agent_reconnect_delay.get())

        self.poolsize = poolsize
        self.ratelimiter = locks.Semaphore(poolsize)
        self.critical_ratelimiter = locks.Semaphore(cricital_pool_size)
        self._sched = Scheduler(io_loop=self._io_loop)
        self.thread_pool = ThreadPoolExecutor(poolsize)

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

    def add_end_point_name(self, name):
        AgentEndPoint.add_end_point_name(self, name)

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

    @protocol.handle(methods.AgentState.set_state)
    @gen.coroutine
    def set_state(self, agent, enabled):
        if enabled:
            return self.unpause(agent)
        else:
            return self.pause(agent)

    @gen.coroutine
    def on_reconnect(self):
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
    def get_latest_version(self):
        """
            Get the latest version of managed resources for all agents
        """
        for agent in self._instances.values():
            yield agent.get_latest_version_for_agent()

    @gen.coroutine
    def _ensure_code(self, environment, version, resourcetypes):
        """
            Ensure that the code for the given environment and version is loaded
        """
        if self._loader is not None:
            for rt in resourcetypes:
                result = yield self._client.get_code(environment, version, rt)

                if result.code == 200:
                    for key, source in result.result["sources"].items():
                        try:
                            LOGGER.debug("Installing handler %s for %s", rt, source[1])
                            yield self._install(key, source)
                            LOGGER.debug("Installed handler %s for %s", rt, source[1])
                        except Exception:
                            LOGGER.exception("Failed to install handler %s for %s", rt, source[1])

    @gen.coroutine
    def _install(self, key, source):
        yield self.thread_pool.submit(self._env.install_from_list, source[3], True)
        yield self.thread_pool.submit(self._loader.deploy_version, key, source)

    @protocol.handle(methods.AgentState.trigger, env="tid", agent="id")
    @gen.coroutine
    def trigger_update(self, env, agent):
        """
            Trigger an update
        """
        if agent not in self._instances:
            return 200

        if not self._instances[agent].is_enabled():
            return 500, "Agent is not _enabled"

        LOGGER.info("Agent %s got a trigger to update in environment %s", agent, env)
        future = self._instances[agent].get_latest_version_for_agent()
        self.add_future(future)
        return 200

    @protocol.handle(methods.AgentResourceEvent.resource_event, env="tid", agent="id")
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

    @protocol.handle(methods.AgentDryRun.do_dryrun, env="tid", dry_run_id="id")
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

    @protocol.handle(methods.AgentRestore.do_restore, env="tid")
    @gen.coroutine
    def do_restore(self, env, agent, restore_id, snapshot_id, resources):
        """
            Restore a snapshot
        """
        if agent not in self._instances:
            return 200

        return (yield self._instances[agent].do_restore(restore_id, snapshot_id, resources))

    @protocol.handle(methods.AgentSnapshot.do_snapshot, env="tid")
    @gen.coroutine
    def do_snapshot(self, env, agent, snapshot_id, resources):
        """
            Create a snapshot of stateful resources managed by this agent
        """
        if agent not in self._instances:
            return 200

        return (yield self._instances[agent].do_snapshot(snapshot_id, resources))

    @protocol.handle(methods.AgentParameterMethod.get_parameter, env="tid")
    @gen.coroutine
    def get_facts(self, env, agent, resource):
        if agent not in self._instances:
            return 200

        return (yield self._instances[agent].get_facts(resource))

    @protocol.handle(methods.AgentReporting.get_status)
    @gen.coroutine
    def get_status(self):
        return 200, collect_report(self)
