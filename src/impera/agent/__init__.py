"""
    Copyright 2015 Impera

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Contact: bart@impera.io
"""

import base64
from collections import defaultdict
from concurrent.futures.thread import ThreadPoolExecutor
import datetime
import hashlib
import logging
import os
import time

from tornado import gen

from impera import env
from impera import methods
from impera import protocol
from impera.agent.handler import Commander
from impera.config import Config
from impera.loader import CodeLoader
from impera.protocol import Scheduler, AgentEndPoint
from impera.resources import Resource, Id


LOGGER = logging.getLogger(__name__)


class DependencyManager(object):
    """
        This class manages depencies between resources
    """
    def __init__(self):
        self._local_resources = {}

        # contains a set of version of a certain resource and a list
        # of resource that depend on a certain version
        self._deps = defaultdict(set)

        # a hash that indicates the latest version of every resource that
        # has been updated since we started
        self._resource_versions = {}

    def add_dependency(self, resource, version, required_id):
        """
            Register the dependency of resource_id on require_id with version.

            :param resource The resource that has dependencies
            :param version The version the of the required resource
            :param required_id The id of the required resource
        """
        # check if this resource was already updated
        if required_id in self._resource_versions:
            v = self._resource_versions[required_id]
            if v >= version:
                # ignore the dep
                return

        resource.add_require(required_id, version)

        resource_id = str(resource.id)

        # add the version to the list of versions
        self._deps[required_id].add(version)

        # add the dependency
        versioned_id = "%s,v=%d" % (required_id, version)
        self._deps[versioned_id].add(resource_id)

        # save the resource
        self._local_resources[resource_id] = resource

    def get_dependencies(self, resource_id, version):
        """
            Get all dependencies on resource_id for all versions that are
            equal or lower than version
        """
        versions = [int(x) for x in self._deps[resource_id]]
        sorted(versions)

        resource_list = []
        for v in versions:
            if v <= version:
                versioned_id = "%s,v=%d" % (resource_id, version)
                dep_list = self._deps[versioned_id]
                resource_list += [self._local_resources[dep] for dep in dep_list if dep in self._local_resources]

        # TODO cleanup?
        return resource_list

    def resource_update(self, resource_id, version, reload_requires=False, deploy_status=True):
        """
            This method should be called to indicate that a resource has been
            updated.

            :param resource_id The id of the resource that has been deployed
            :param version The version of the resource that was deployed
            :param reload_requires The deployed resource requires its dependants to be reloaded
            :param deploy_status A boolean that indicates if the deploy was successful and requires can be notified, or if false
                                 the requires should be skipped.
        """
        resource_id = str(resource_id)

        self._resource_versions[resource_id] = version

        for res in self.get_dependencies(resource_id, version):
            if deploy_status:
                res.update_require(resource_id, version)
                if reload_requires:
                    res.do_reload = reload_requires
                    LOGGER.debug("Marking %s to reload, triggered by %s" % (res, resource_id))
                    LOGGER.debug("Resource %s: do_reload=%s, %d" % (res, res.do_reload, id(res)))

            else:
                res.update_require(resource_id, version, failed=True)


class QueueManager(object):
    """
        This class manages the update queue (including the versioning)
    """
    def __init__(self):
        self._queue = list()
        self._ready_queue = list()
        self._resources = {}

    def add_resource(self, resource):
        """
            Add a resource to the queue. When an older version of the resource
            is already in the queue, replace it.
        """
        if resource.id in self._resources:
            res, version, queue = self._resources[resource.id]

            if version <= resource.version:
                try:
                    queue.remove(res)
                    del self._resources[resource.id]
                except Exception:
                    pass

            else:
                # a newer version
                return

        if len(resource.requires_queue) == 0:
            self._ready_queue.append(resource)
            self._resources[resource.id] = (resource, resource.version, self._ready_queue)
        else:
            self._queue.append(resource)
            self._resources[resource.id] = (resource, resource.version, self._queue)

    def notify_ready(self, resource):
        """
            This resource can be processed because all of its deps are finished
        """
#         res, version, queue = self._resources[resource.id]
#         queue.remove(res)
#
#         self._ready_queue.append(resource)
#         self._resources[resource.id] = (resource, version, self._ready_queue)

    def _move_ready(self):
        """
            Move resources that are ready to the ready queue
        """
        for res in self._queue:
            if len(res.requires_queue) == 0:
                self._ready_queue.append(res)
                self._queue.remove(res)

    def pop(self):
        """
            Pop a resource from the list
        """
        if self.size() == 0:
            return None

        if len(self._ready_queue) == 0:
            self._move_ready()

        if len(self._ready_queue) == 0:
            return None

        # return the last element. If ready, remove it from the queue
        return self._ready_queue[-1]

    def remove(self, resource):
        try:
            self._ready_queue.remove(resource)
            del self._resources[resource.id]
        except Exception:
            pass
            # this might fail if in the meanwhile a new version was deployed

    def size(self):
        return len(self._queue) + len(self._ready_queue)

    def ready_size(self):
        self._move_ready()
        return len(self._ready_queue)

    def all(self):
        """
            Return all items in the queue
        """
        return self._queue + self._ready_queue

    def dump(self):
        """
            Dump the queue
        """
        LOGGER.info("Dumping queue")
        for r in self.all():
            LOGGER.info(r)
            LOGGER.info("\t-> %s" % r.requires_queue)


class Agent(AgentEndPoint):
    """
        An agent to enact changes upon resources. This agent listens to the
        message bus for changes.
    """
    def __init__(self, io_loop, hostname=None, agent_map=None, code_loader=True, env_id=None):
        super().__init__("agent", io_loop, heartbeat_interval=int(Config.get("config", "heartbeat-interval", 10)))

        if agent_map is None:
            agent_map = Config.get("config", "agent-map", None)

        self.agent_map = self._process_map(agent_map)
        self._storage = self.check_storage()

        self._dm = DependencyManager()
        self._queue = QueueManager()

        self._last_update = 0

        if env_id is None:
            env_id = Config.get("config", "environment")
            if env_id is None:
                raise Exception("The agent requires an environment to be set.")
        self.set_environment(env_id)

        if code_loader:
            self._env = env.VirtualEnv(self._storage["env"])
            self._env.use_virtual_env()
            self._loader = CodeLoader(self._storage["code"])
        else:
            self._loader = None

        self._client = protocol.Client("agent")
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
        self._deploy_interval = 600
        self.latest_version = 0
        self.latest_code_version = 0

        self._sched = Scheduler(io_loop=self._io_loop)
        self._sched.add_action(self.get_latest_version, self._deploy_interval, True)
        self._io_loop.add_callback(self.check_deploy)

        self.thread_pool = ThreadPoolExecutor(4)

    @gen.coroutine
    def check_deploy(self):
        while True:
            if self._queue.size() > 0:
                self.deploy_config()
            else:
                yield gen.sleep(1)

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
            self.get_latest_version_for_agent(agent)

    @gen.coroutine
    def _ensure_code(self, environment, version):
        """
            Ensure that the code for the given environment and version is loaded
        """
        if self.latest_code_version < version and self._loader is not None:
            result = yield self._client.get_code(environment, version)

            if result.code == 200:
                self._env.install_from_list(result.result["requires"])
                self._loader.deploy_version(version, result.result["sources"])

                self.latest_code_version = version

    @protocol.handle(methods.NodeMethod.trigger_agent)
    @gen.coroutine
    def trigger_update(self, tid, id):
        """
            Trigger an update
        """
        LOGGER.info("Agent %s got a trigger to update in environment %s", id, tid)
        future = self.get_latest_version_for_agent(id)
        self.add_future(future)
        return 200

    @gen.coroutine
    def get_latest_version_for_agent(self, agent):
        """
            Get the latest version for the given agent (this is also how we are notified)
        """
        LOGGER.debug("Getting latest resources for %s" % agent)
        result = yield self._client.get_resources_for_agent(tid=self._env_id, agent=agent)
        if result.code == 404:
            LOGGER.info("No released configuration model version available for agent %s", agent)
        elif result.code != 200:
            LOGGER.warning("Got an error while pulling resources for agent %s", agent)

        else:
            yield self._ensure_code(self._env_id, result.result["version"])

            try:
                for res in result.result["resources"]:
                    data = res["fields"]
                    data["id"] = res["id"]
                    resource = Resource.deserialize(data)
                    self.update(resource)
                    LOGGER.debug("Received update for %s", resource.id)
            except TypeError as e:
                LOGGER.error("Failed to receive update", e)

    @protocol.handle(methods.AgentDryRun.do_dryrun)
    @gen.coroutine
    def run_dryrun(self, tid, id, agent, version):
        """
           Run a dryrun of the given version
        """
        LOGGER.info("Agent %s got a trigger to run dryrun %s for version %s in environment %s", agent, id, version, tid)
        assert tid == self._env_id

        result = yield self._client.get_resources_for_agent(tid=self._env_id, agent=agent, version=version)
        if result.code == 404:
            LOGGER.info("Version %s does not exist", version)
            return 404

        elif result.code != 200:
            LOGGER.warning("Got an error while pulling resources for agent %s and version %s", agent, version)
            return 500

        self._ensure_code(self._env_id, version)  # TODO: handle different versions for dryrun and deploy!

        try:
            for res in result.result["resources"]:
                data = res["fields"]
                data["id"] = res["id"]
                resource = Resource.deserialize(data)
                LOGGER.debug("Running dryrun for %s", resource.id)

                try:
                    provider = Commander.get_provider(self, resource)
                except Exception:
                    LOGGER.exception("Unable to find a handler for %s" % resource.id)
                    self.resource_updated(resource, reload_requires=False, changes={}, status="unavailable")
                    continue

                results = provider.execute(resource, dry_run=True)

                yield self._client.dryrun_update(tid=self._env_id, id=id, resource=res["id"],
                                                 changes=results["changes"], log_msg=results["log_msg"])

        except TypeError:
            LOGGER.exception("Unable to process resource for dryrun.")
            return 500

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
            raise Exception("The Impera requires a state directory to be configured")

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
        LOGGER.info("Start a restore %s", restore_id)

        for restore, resource in resources:
            start = datetime.datetime.now()
            try:
                data = resource["fields"]
                data["id"] = resource["id"]
                resource_obj = Resource.deserialize(data)
                provider = Commander.get_provider(self, resource_obj)

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

        return 200

    @protocol.handle(methods.AgentSnapshot.do_snapshot)
    @gen.coroutine
    def do_snapshot(self, tid, agent, snapshot_id, resources):
        """
            Create a snapshot of stateful resources managed by this agent
        """
        LOGGER.info("Start snapshot %s", snapshot_id)

        for resource in resources:
            start = datetime.datetime.now()
            try:
                data = resource["fields"]
                data["id"] = resource["id"]
                resource_obj = Resource.deserialize(data)
                provider = Commander.get_provider(self, resource_obj)

                if not hasattr(resource_obj, "allow_snapshot") or not resource_obj.allow_snapshot:
                    yield self._client.update_snapshot(tid=tid, id=snapshot_id,
                                                       resource_id=resource_obj.id.resource_str(), snapshot_data="",
                                                       start=start, stop=datetime.datetime.now(), size=0,
                                                       success=False, error=False,
                                                       msg="Resource %s does not allow snapshots" % resource["id"])
                    continue

                try:
                    result = provider.snapshot(resource_obj)
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

        return 200

    def status(self, operation, body):
        if "id" not in body:
            return 500

        if operation is None:
            resource = Id.parse_id(body["id"]).get_instance()

            if resource is None:
                return 500

            try:
                provider = Commander.get_provider(self, resource)
            except Exception:
                LOGGER.exception("Unable to find a handler for %s" % resource)
                return 500

            try:
                result = provider.check_resource(resource)
                return 200, result
            except Exception:
                LOGGER.exception("Unable to check status of %s" % resource)
                return 500

        else:
            return 501

    @protocol.handle(methods.AgentParameterMethod.get_parameter)
    @gen.coroutine
    def get_facts(self, tid, agent, resource):
        try:
            data = resource["fields"]
            data["id"] = resource["id"]
            resource_obj = Resource.deserialize(data)
            provider = Commander.get_provider(self, resource_obj)

            try:
                result = provider.check_facts(resource_obj)
                for param, value in result.items():
                    yield self._client.set_param(tid=tid, resource_id=resource["id"], source="fact", id=param, value=value)

            except Exception:
                LOGGER.exception("Unable to retrieve fact")

        except Exception:
            LOGGER.exception("Unable to find a handler for %s", resource["id"])
            return 500

        return 200

    def queue(self, operation, body):
        """
            Return the current items in the queue
        """
        return 200, {"queue": ["%s" % (x.id) for x in self._queue.all()]}

    def info(self, operation, body):
        """
            Return statistics about this agent
        """
        return 200, {"threads": [x.name for x in enumerate()],
                     "queue length": self._queue.size(),
                     "queue ready length": self._queue.ready_size()}

    def update(self, res_obj):
        """
            Process an update
        """
        for req in res_obj.requires:
            self._dm.add_dependency(res_obj, req.version, req.resource_str())

        self._queue.add_resource(res_obj)
        self._last_update = time.time()

    def resource_updated_received(self, operation, body):
        rid = body["id"]
        version = body["version"]
        reload_resource = body["reload"]
        self._dm.resource_update(rid, version, reload_resource)

    def deploy_config(self):
        """
            Deploy a configuration is there are items in the queue
        """
        LOGGER.debug("Execute deploy config")

        LOGGER.info("Need to update %d resources" % self._queue.size())
        while self._queue.size() > 0:
            resource = self._queue.pop()
            if resource is None:
                LOGGER.info("No resources ready for deploy.")
                break

            LOGGER.debug("Start deploy of resource %s" % resource)
            try:
                provider = Commander.get_provider(self, resource)
            except Exception:
                LOGGER.exception("Unable to find a handler for %s" % resource.id)
                self.resource_updated(resource, reload_requires=False, changes={}, status="unavailable")
                self._queue.remove(resource)
                continue

            results = provider.execute(resource)
            self.resource_updated(resource, reload_requires=results["changed"], changes=results["changes"],
                                  status=results["status"], log_msg=results["log_msg"])

            if resource.do_reload and provider.can_reload():
                LOGGER.warning("Reloading %s because of updated dependencies" % resource.id)
                provider.do_reload(resource)

            LOGGER.debug("Finished %s" % resource)
            self._queue.remove(resource)

        return

    @gen.coroutine
    def resource_updated(self, resource, reload_requires=False, changes={}, status="", log_msg=""):
        """
            A resource with id $rid calls this method to indicate that it is now at version $version.
        """
        reload_resource = False
        if hasattr(resource, "reload") and resource.reload and reload_requires:
            LOGGER.info("%s triggered a reload" % resource)
            reload_resource = True

        deploy_result = True
        if status == "failed" or status == "skipped":
            deploy_result = False

        self._dm.resource_update(resource.id.resource_str(), resource.id.version, reload_resource, deploy_result)

        action = "deploy"

        if status == "dry" or status == "deployed":
            level = "INFO"
        else:
            level = "ERROR"

        yield self._client.resource_updated(tid=self._env_id, id=str(resource.id), level=level, action=action, status=status,
                                            message="%s: %s" % (status, log_msg), extra_data=changes)
