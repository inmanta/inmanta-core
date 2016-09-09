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
from inmanta.config import Config
from inmanta.loader import CodeLoader
from inmanta.protocol import Scheduler, AgentEndPoint
from inmanta.resources import Resource, Id
from tornado.concurrent import Future
from inmanta.agent.cache import AgentCache
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

    def __init__(self, agent, env_id):
        self.generation = {}
        self._env_id = env_id
        self.agent = agent

    def reload(self, resources):
        for ra in self.generation.values():
            ra.cancel()
        self.generation = {r.id.resource_str(): ResourceAction(self, r) for r in resources}
        dummy = ResourceAction(self, None)
        for r in self.generation.values():
            r.execute(dummy, self.generation, self.agent.cache)
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
        super().__init__("agent", io_loop, heartbeat_interval=int(Config.get("config", "heartbeat-interval", 10)))

        if agent_map is None:
            agent_map = Config.get("config", "agent-map", None)

        self.agent_map = self._process_map(agent_map)
        self._storage = self.check_storage()

        self._last_update = 0

        if env_id is None:
            env_id = Config.get("config", "environment")
            if env_id is None:
                raise Exception("The agent requires an environment to be set.")
        self.set_environment(env_id)
        self._nq = ResourceScheduler(self, env_id)

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
            agent_names = Config.get("config", "agent-names", None)
            if agent_names is not None:
                names = [x.strip() for x in agent_names.split(",")]
                for name in names:
                    if "$" in name:
                        name = name.replace("$node-name", self.node_name)

                    self.add_end_point_name(name)

        # do regular deploys
        self._deploy_interval = int(Config.get("config", "agent-interval", "600"))
        self._splay_interval = int(Config.get("config", "agent-splay", "600"))
        self._splay_value = random.randint(0, self._splay_interval)

        self.latest_version = 0
        self.latest_code_version = 0

        self._sched = Scheduler(io_loop=self._io_loop)
        if self._splay_interval > 0 and Config.getboolean("config", "agent-run-at-start", False):
            self._io_loop.add_callback(self.get_latest_version)
        self._sched.add_action(self.get_latest_version, self._deploy_interval, self._splay_value)

        self.thread_pool = ThreadPoolExecutor(poolsize)

        self.cache = AgentCache()

    def _process_map(self, agent_map):
        """
            Process the agent mapping
        """
        agent_dict = {}
        if agent_map is not None:
            mappings = agent_map.split(",")

            for mapping in mappings:
                parts = mapping.strip().split("=")
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    if key != "" and value != "":
                        agent_dict[key] = value

        return agent_dict

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

    @protocol.handle(methods.NodeMethod.trigger_agent)
    @gen.coroutine
    def trigger_update(self, tid, id):
        """
            Trigger an update
        """
        if id not in self.end_point_names:
            return 200

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

            self._nq.reload(resources)

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

        self.cache.open_version(version)

        for res in result.result["resources"]:
            provider = None
            try:
                data = res["fields"]
                data["id"] = res["id"]
                resource = Resource.deserialize(data)
                LOGGER.debug("Running dryrun for %s", resource.id)

                try:
                    provider = Commander.get_provider(self, resource)
                    provider.set_cache(self.cache)
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

        self.cache.close_version(version)

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
        if "config" not in Config.get() or "state-dir" not in Config.get()["config"]:
            raise Exception("The Inmanta requires a state directory to be configured")

        state_dir = Config.get("config", "state-dir")

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
        self.cache.open_version(version)

        for restore, resource in resources:
            start = datetime.datetime.now()
            provider = None
            try:
                data = resource["fields"]
                data["id"] = resource["id"]
                resource_obj = Resource.deserialize(data)
                provider = Commander.get_provider(self, resource_obj)
                provider.set_cache(self.cache)

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
        self.cache.close_version(version)

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
        self.cache.open_version(version)

        for resource in resources:
            start = datetime.datetime.now()
            provider = None
            try:
                data = resource["fields"]
                data["id"] = resource["id"]
                resource_obj = Resource.deserialize(data)
                provider = Commander.get_provider(self, resource_obj)
                provider.set_cache(self.cache)

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

        self.cache.close_version(version)
        return 200

    def status(self, operation, body):
        if "id" not in body:
            return 500

        if operation is None:
            id = Id.parse_id(body["id"])
            resource = id.get_instance()

            if resource is None:
                return 500

            version = id.get_version()
            self.cache.open_version(version)

            try:
                provider = Commander.get_provider(self, resource)
                provider.set_cache(self.cache)
            except Exception:
                LOGGER.exception("Unable to find a handler for %s" % resource)
                return 500

            try:
                result = yield self.thread_pool.submit(provider.check_resource, resource)
                return 200, result
            except Exception:
                LOGGER.exception("Unable to check status of %s" % resource)
                return 500

            self.cache.close_version(version)

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
                self.cache.open_version(version)
                provider.set_cache(self.cache)

                result = yield self.thread_pool.submit(provider.check_facts, resource_obj)
                parameters = [{"id": name, "value": value, "resource_id": resource_obj.id.resource_str(), "source": "fact"}
                              for name, value in result.items()]
                yield self._client.set_parameters(tid=tid, parameters=parameters)

            except Exception:
                LOGGER.exception("Unable to retrieve fact")

            finally:
                self.cache.close_version(version)

        except Exception:
            LOGGER.exception("Unable to find a handler for %s", resource["id"])
            return 500

        finally:
            if provider is not None:
                provider.close()
        return 200

    def queue(self, operation, body):
        """
            Return the current items in the queue
        """
        return 200, {"queue": ["%s" % (x.id) for x in self._nq.generation.values()]}

    def info(self, operation, body):
        """
            Return statistics about this agent
        """
        return 200, {"threads": [x.name for x in enumerate()],
                     "queue length": self._queue.size(),
                     "queue ready length": self._queue.ready_size()}

    @protocol.handle(methods.AgentReporting.get_status)
    @gen.coroutine
    def get_status(self):
        return 200, collect_report(self)
