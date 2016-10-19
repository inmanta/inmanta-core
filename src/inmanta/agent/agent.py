"""
    Copyright 2016 Inmanta

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


from tornado import gen
from inmanta import env
from inmanta import methods
from inmanta import protocol
from inmanta.agent.handler import Commander
from inmanta.loader import CodeLoader
from inmanta.protocol import Scheduler, AgentEndPoint
from inmanta.resources import Resource, Id
from tornado.concurrent import Future
from inmanta.agent.cache import AgentCache
from inmanta.agent import config as cfg
from inmanta.agent.reporting import collect_report

LOGGER = logging.getLogger(__name__)


class ResourceActionResult(object):

    def __init__(self, success, reload, cancel):
        self.success = success
        self.reload = reload
        self.cancel = cancel

    def __add__(self, other):
        return ResourceActionResult(self.success and other.success,
                                    self.reload or other.reload,
                                    self.cancel or other.cancel)

    def __str__(self, *args, **kwargs):
        return "%r %r %r" % (self.success, self.reload, self.cancel)


class ResourceAction(object):

    def __init__(self, scheduler, resource):
        self.scheduler = scheduler
        self.resource = resource
        self.future = Future()
        self.running = False

    def is_running(self):
        return self.running

    def is_done(self):
        return self.future.done()

    def cancel(self):
        if not self.is_running() and not self.is_done():
            LOGGER.info("Cancelled deploy of %s", self.resource)
            self.future.set_result(ResourceActionResult(False, False, True))

    @gen.coroutine
    def __complete(self, success, reload, changes={}, status="", log_msg=""):
        action = "deploy"
        if status == "skipped" or status == "dry" or status == "deployed":
            level = "INFO"
        else:
            level = "ERROR"

        yield self.scheduler.agent._client.resource_updated(tid=self.scheduler._env_id,
                                                            id=str(self.resource.id),
                                                            level=level,
                                                            action=action,
                                                            status=status,
                                                            message="%s: %s" % (status, log_msg),
                                                            extra_data=changes)

        self.future.set_result(ResourceActionResult(success, reload, False))
        LOGGER.info("end run %s" % self.resource)
        self.running = False

    @gen.coroutine
    def execute(self, dummy, generation, cache):
        cache.open_version(self.resource.version)

        self.dependencies = [generation[x.resource_str()] for x in self.resource.requires]
        waiters = [x.future for x in self.dependencies]
        waiters.append(dummy.future)
        results = yield waiters

        LOGGER.info("run %s" % self.resource)
        self.running = True
        if self.is_done():
            # Action is cancelled
            self.running = False
            return

        result = sum(results, ResourceActionResult(True, False, False))

        if result.cancel:
            return

        if not result.success:
            self.__complete(False, False, changes={}, status="skipped")
        else:
            resource = self.resource

            LOGGER.debug("Start deploy of resource %s" % resource)
            provider = None

            try:
                provider = Commander.get_provider(self.scheduler.agent, resource)
                provider.set_cache(cache)
            except Exception:
                provider.close()
                cache.close_version(self.resource.version)
                LOGGER.exception("Unable to find a handler for %s" % resource.id)
                return self.__complete(False, False, changes={}, status="unavailable")

            results = yield self.scheduler.agent.thread_pool.submit(provider.execute, resource)

            status = results["status"]
            if status == "failed" or status == "skipped":
                provider.close()
                cache.close_version(self.resource.version)
                return self.__complete(False, False,
                                       changes=results["changes"],
                                       status=results["status"],
                                       log_msg=results["log_msg"])

            if result.reload and provider.can_reload():
                LOGGER.warning("Reloading %s because of updated dependencies" % resource.id)
                yield self.scheduler.agent.thread_pool.submit(provider.do_reload, resource)

            provider.close()
            cache.close_version(self.resource.version)

            reload = results["changed"] and hasattr(resource, "reload") and resource.reload
            return self.__complete(True, reload=reload, changes=results["changes"],
                                   status=results["status"], log_msg=results["log_msg"])

            LOGGER.debug("Finished %s" % resource)

    def __str__(self, *args, **kwargs):
        if self.resource is None:
            return "DUMMY"

        status = ""
        if self.is_done():
            status = "Done"
        elif self.is_running():
            status = "Running"

        return self.resource.id.resource_str() + status

    def long_string(self):
        return "%s awaits %s" % (self.resource.id.resource_str(), " ".join([str(aw) for aw in self.dependencies]))


class ResourceScheduler(object):

    def __init__(self, agent, env_id, cache):
        self.generation = {}
        self._env_id = env_id
        self.agent = agent
        self.cache = cache

    def reload(self, resources):
        for ra in self.generation.values():
            ra.cancel()
        self.generation = {r.id.resource_str(): ResourceAction(self, r) for r in resources}
        dummy = ResourceAction(self, None)
        for r in self.generation.values():
            r.execute(dummy, self.generation, self.cache)
        dummy.future.set_result(ResourceActionResult(True, False, False))

    def dump(self):
        print("Waiting:")
        for r in self.generation.values():
            print(r.long_string())
        print("Ready to run:")
        for r in self.queue:
            print(r.long_string())


class Agent(AgentEndPoint):
    """
        An agent to enact changes upon resources. This agent listens to the
        message bus for changes.
    """

    def __init__(self, io_loop, hostname=None, agent_map=None, code_loader=True, env_id=None, poolsize=1):
        super().__init__("agent", io_loop, cfg.heartbeat.get())

        if agent_map is None:
            agent_map = cfg.agent_map.get()

        self.agent_map = agent_map
        self._storage = self.check_storage()

        self._last_update = 0

        if env_id is None:
            env_id = cfg.environment.get()
            if env_id is None:
                raise Exception("The agent requires an environment to be set.")
        self.set_environment(env_id)

        self._nqs = {}
        self._cache = {}
        self._enabled = {}

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

        # do regular deploys
        self._deploy_interval = cfg.agent_interval.get()
        self._splay_interval = cfg.agent_splay.get()
        self._splay_value = random.randint(0, self._splay_interval)

        self.latest_version = 0
        self.latest_code_version = 0

        self._sched = Scheduler(io_loop=self._io_loop)

        self.thread_pool = ThreadPoolExecutor(poolsize)

    def start(self):
        AgentEndPoint.start(self)
        self.add_future(self.initialize())

    def add_end_point_name(self, name):
        AgentEndPoint.add_end_point_name(self, name)
        cache = AgentCache()
        self._nqs[name] = ResourceScheduler(self, self._env_id, cache)
        self._cache[name] = cache
        self._enabled[name] = None

    def unpause(self, name):
        if name not in self._enabled:
            return 404, "No such agent"

        if self._enabled[name] is not None:
            return

        LOGGER.info("Agent assuming primary role for %s" % name)

        @gen.coroutine
        def action():
            yield self.get_latest_version_for_agent(name)
        self._enabled[name] = action
        self._sched.add_action(action, self._deploy_interval)
        return 200

    def pause(self, name):
        if name not in self._enabled:
            return 404, "No such agent"

        if self._enabled[name] is None:
            return

        LOGGER.info("Agent lost primary role for %s" % name)

        token = self._enabled[name]
        self._sched.remove(token)
        self._enabled[name] = None
        return 200

    @protocol.handle(methods.AgentState.set_state)
    @gen.coroutine
    def set_state(self, agent, enabled):
        if enabled:
            return self.unpause(agent)
        else:
            return self.pause(agent)

    @gen.coroutine
    def initialize(self):
        for name in self._enabled.keys():
            result = yield self._client.get_state(tid=self._env_id, sid=self.sessionid, agent=name)
            if result.code == 200:
                state = result.result
                if "enabled" in state and isinstance(state["enabled"], bool):
                    self.set_state(name, state["enabled"])
                else:
                    LOGGER.warn("Server reported invalid state %s" % (repr(state)))
            else:
                LOGGER.warn("could not get state from the server")

    def is_local(self, agent_name):
        """
            Check if the given agent name is a local or a remote agent
        """
        return self._client.node_name == agent_name or agent_name == "localhost"

    @gen.coroutine
    def get_latest_version(self):
        """
            Get the latest version of managed resources for all agents
        """
        for agent in self.end_point_names:
            yield self.get_latest_version_for_agent(agent)

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

    @protocol.handle(methods.AgentState.trigger)
    @gen.coroutine
    def trigger_update(self, tid, id):
        """
            Trigger an update
        """
        if id not in self.end_point_names:
            return 200

        if self._enabled[id] is None:
            return 500, "Agent is not enabled"

        LOGGER.info("Agent %s got a trigger to update in environment %s", id, tid)
        future = self.get_latest_version_for_agent(id)
        self.add_future(future)
        return 200

    @gen.coroutine
    def get_latest_version_for_agent(self, agent):
        """
            Get the latest version for the given agent (this is also how we are notified)
        """
        if agent not in self.end_point_names:
            return 200

        LOGGER.debug("Getting latest resources for %s" % agent)
        result = yield self._client.get_resources_for_agent(tid=self._env_id, agent=agent)
        if result.code == 404:
            LOGGER.info("No released configuration model version available for agent %s", agent)
        elif result.code != 200:
            LOGGER.warning("Got an error while pulling resources for agent %s", agent)

        else:
            restypes = set([res["id_fields"]["entity_type"] for res in result.result["resources"]])
            resources = []
            yield self._ensure_code(self._env_id, result.result["version"], restypes)
            try:
                for res in result.result["resources"]:
                    data = res["fields"]
                    data["id"] = res["id"]
                    resource = Resource.deserialize(data)
                    resources.append(resource)
                    LOGGER.debug("Received update for %s", resource.id)
            except TypeError as e:
                LOGGER.error("Failed to receive update", e)

            self._nqs[agent].reload(resources)

    @protocol.handle(methods.AgentDryRun.do_dryrun)
    @gen.coroutine
    def run_dryrun(self, tid, id, agent, version):
        """
           Run a dryrun of the given version
        """
        if agent not in self.end_point_names:
            return 200

        LOGGER.info("Agent %s got a trigger to run dryrun %s for version %s in environment %s", agent, id, version, tid)
        assert tid == self._env_id

        result = yield self._client.get_resources_for_agent(tid=self._env_id, agent=agent, version=version)
        if result.code == 404:
            LOGGER.info("Version %s does not exist", version)
            return 404

        elif result.code != 200:
            LOGGER.warning("Got an error while pulling resources for agent %s and version %s", agent, version)
            return 500

        restypes = set([res["id_fields"]["entity_type"] for res in result.result["resources"]])

        yield self._ensure_code(self._env_id, version, restypes)  # TODO: handle different versions for dryrun and deploy!

        self._cache[agent].open_version(version)

        for res in result.result["resources"]:
            provider = None
            try:
                data = res["fields"]
                data["id"] = res["id"]
                resource = Resource.deserialize(data)
                LOGGER.debug("Running dryrun for %s", resource.id)

                try:
                    provider = Commander.get_provider(self, resource)
                    provider.set_cache(self._cache[agent])
                except Exception:
                    LOGGER.exception("Unable to find a handler for %s" % resource.id)
                    self._client.dryrun_update(tid=self._env_id, id=id, resource=res["id"],
                                               changes={}, log_msg="No handler available")
                    continue

                results = yield self.thread_pool.submit(provider.execute, resource, dry_run=True)
                yield self._client.dryrun_update(tid=self._env_id, id=id, resource=res["id"],
                                                 changes=results["changes"], log_msg=results["log_msg"])

            except TypeError:
                LOGGER.exception("Unable to process resource for dryrun.")
                return 500
            finally:
                if provider is not None:
                    provider.close()

        self._cache[agent].close_version(version)

        return 200

    def get_agent_hostname(self, agent_name):
        """
            Convert the agent name to a hostname using the agent map
        """
        if agent_name in self.agent_map:
            return self.agent_map[agent_name]

        return agent_name

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

    @protocol.handle(methods.AgentRestore.do_restore)
    @gen.coroutine
    def do_restore(self, tid, agent, restore_id, snapshot_id, resources):
        """
            Restore a snapshot
        """
        if agent not in self.end_point_names:
            return 200

        LOGGER.info("Start a restore %s", restore_id)

        yield self._ensure_code(tid, resources[0][1]["id_fields"]["version"],
                                [res[1]["id_fields"]["entity_type"] for res in resources])

        version = resources[0][1]["id_fields"]["version"]
        self._cache[agent].open_version(version)

        for restore, resource in resources:
            start = datetime.datetime.now()
            provider = None
            try:
                data = resource["fields"]
                data["id"] = resource["id"]
                resource_obj = Resource.deserialize(data)
                provider = Commander.get_provider(self, resource_obj)
                provider.set_cache(self._cache[agent])

                if not hasattr(resource_obj, "allow_restore") or not resource_obj.allow_restore:
                    yield self._client.update_restore(tid=tid, id=restore_id, resource_id=str(resource_obj.id),
                                                      start=start, stop=datetime.datetime.now(), success=False, error=False,
                                                      msg="Resource %s does not allow restore" % resource["id"])
                    continue

                try:
                    yield self.thread_pool.submit(provider.restore, resource_obj, restore["content_hash"])
                    yield self._client.update_restore(tid=tid, id=restore_id,
                                                      resource_id=str(resource_obj.id), success=True, error=False,
                                                      start=start, stop=datetime.datetime.now(), msg="")
                except NotImplementedError:
                    yield self._client.update_restore(tid=tid, id=restore_id,
                                                      resource_id=str(resource_obj.id), success=False, error=False,
                                                      start=start, stop=datetime.datetime.now(),
                                                      msg="The handler for resource "
                                                      "%s does not support restores" % resource["id"])

            except Exception:
                LOGGER.exception("Unable to find a handler for %s", resource["id"])
                yield self._client.update_restore(tid=tid, id=restore_id, resource_id=resource_obj.id.resource_str(),
                                                  success=False, error=False, start=start, stop=datetime.datetime.now(),
                                                  msg="Unable to find a handler to restore a snapshot of resource %s" %
                                                  resource["id"])
            finally:
                if provider is not None:
                    provider.close()
        self._cache[agent].close_version(version)

        return 200

    @protocol.handle(methods.AgentSnapshot.do_snapshot)
    @gen.coroutine
    def do_snapshot(self, tid, agent, snapshot_id, resources):
        """
            Create a snapshot of stateful resources managed by this agent
        """
        if agent not in self.end_point_names:
            return 200

        LOGGER.info("Start snapshot %s", snapshot_id)

        yield self._ensure_code(tid, resources[0]["id_fields"]["version"],
                                [res["id_fields"]["entity_type"] for res in resources])

        version = resources[0]["id_fields"]["version"]
        self._cache[agent].open_version(version)

        for resource in resources:
            start = datetime.datetime.now()
            provider = None
            try:
                data = resource["fields"]
                data["id"] = resource["id"]
                resource_obj = Resource.deserialize(data)
                provider = Commander.get_provider(self, resource_obj)
                provider.set_cache(self._cache[agent])

                if not hasattr(resource_obj, "allow_snapshot") or not resource_obj.allow_snapshot:
                    yield self._client.update_snapshot(tid=tid, id=snapshot_id,
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
                        yield self._client.upload_file(id=content_id, content=base64.b64encode(result).decode("ascii"))

                        yield self._client.update_snapshot(tid=tid, id=snapshot_id,
                                                           resource_id=resource_obj.id.resource_str(),
                                                           snapshot_data=content_id, start=start, stop=datetime.datetime.now(),
                                                           size=len(result), success=True, error=False,
                                                           msg="")
                    else:
                        raise Exception("Snapshot returned no data")

                except NotImplementedError:
                    yield self._client.update_snapshot(tid=tid, id=snapshot_id, error=False,
                                                       resource_id=resource_obj.id.resource_str(), snapshot_data="",
                                                       start=start, stop=datetime.datetime.now(), size=0, success=False,
                                                       msg="The handler for resource "
                                                       "%s does not support snapshots" % resource["id"])
                except Exception:
                    LOGGER.exception("An exception occurred while creating the snapshot of %s", resource["id"])
                    yield self._client.update_snapshot(tid=tid, id=snapshot_id, snapshot_data="",
                                                       resource_id=resource_obj.id.resource_str(), error=True,
                                                       start=start, stop=datetime.datetime.now(), size=0, success=False,
                                                       msg="The handler for resource "
                                                       "%s does not support snapshots" % resource["id"])

            except Exception:
                LOGGER.exception("Unable to find a handler for %s", resource["id"])
                yield self._client.update_snapshot(tid=tid, id=snapshot_id, snapshot_data="",
                                                   resource_id=resource_obj.id.resource_str(), error=False,
                                                   start=start, stop=datetime.datetime.now(), size=0, success=False,
                                                   msg="Unable to find a handler for %s" % resource["id"])
            finally:
                if provider is not None:
                    provider.close()

        self._cache[agent].close_version(version)
        return 200

    def status(self, operation, body):
        if "id" not in body:
            return 500

        if operation is None:
            id = Id.parse_id(body["id"])
            resource = id.get_instance()
            agent = id.get_agent_name()

            if agent not in self._cache[agent]:
                LOGGER.exception("Agent unknown" % resource)
                return 500

            cache = self._cache[agent]

            if resource is None:
                return 500

            version = id.get_version()
            cache.open_version(version)

            try:
                provider = Commander.get_provider(self, resource)
                provider.set_cache(cache)
            except Exception:
                LOGGER.exception("Unable to find a handler for %s" % resource)
                return 500

            try:
                result = yield self.thread_pool.submit(provider.check_resource, resource)
                return 200, result
            except Exception:
                LOGGER.exception("Unable to check status of %s" % resource)
                return 500

            cache.close_version(version)

        else:
            return 501

    @protocol.handle(methods.AgentParameterMethod.get_parameter)
    @gen.coroutine
    def get_facts(self, tid, agent, resource):
        if agent not in self.end_point_names:
            return 200

        provider = None
        try:
            data = resource["fields"]
            data["id"] = resource["id"]
            resource_obj = Resource.deserialize(data)

            version = resource_obj.version

            provider = Commander.get_provider(self, resource_obj)

            try:
                self._cache[agent].open_version(version)
                provider.set_cache(self._cache[agent])
                result = yield self.thread_pool.submit(provider.check_facts, resource_obj)
                parameters = [{"id": name, "value": value, "resource_id": resource_obj.id.resource_str(), "source": "fact"}
                              for name, value in result.items()]
                yield self._client.set_parameters(tid=tid, parameters=parameters)

            except Exception:
                LOGGER.exception("Unable to retrieve fact")
            finally:
                self._cache[agent].close_version(version)

        except Exception:
            LOGGER.exception("Unable to find a handler for %s", resource["id"])
            return 500
        finally:
            if provider is not None:
                provider.close()
        return 200

    @protocol.handle(methods.AgentReporting.get_status)
    @gen.coroutine
    def get_status(self):
        return 200, collect_report(self)
