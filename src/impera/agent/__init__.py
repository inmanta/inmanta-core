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

from collections import defaultdict
import logging
from threading import enumerate
import time
import os

from impera import protocol, methods
from impera.agent.handler import Commander
from impera.config import Config
from impera.loader import CodeLoader
from impera.protocol import ServerClientEndpoint, DirectTransport, AMQPTransport
from impera.resources import Resource, Id
from impera import env

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


class Agent(ServerClientEndpoint):
    """
        An agent to enact changes upon resources. This agent listens to the
        message bus for changes.
    """
    __transports__ = [DirectTransport, AMQPTransport]

    def __init__(self, hostname=None, remote=None, code_loader=True):
        super().__init__("agent", role="agent")
        self.remote = remote
        self._storage = self.check_storage()

        self._dm = DependencyManager()
        self._queue = QueueManager()

        self._last_update = 0

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

    def _busy_deploy(self):
        if self._queue.size() > 0:
            self.deploy_config()

        time.sleep(1)

    def start(self):
        """
            Start the agent and execute the deployment main loop here
        """
        LOGGER.debug("Starting agent")
        super().start(self._busy_deploy)

    def stop(self):
        super().stop()
        Commander.close()

    @protocol.handle(methods.PingMethod)
    def ping(self, operation, body):
        return 200, dict(end_point_names=self.end_point_names, nodename=self.node_name, role=self.role)

    @protocol.handle(methods.StatusMethod)
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

    @protocol.handle(methods.RetrieveFacts)
    def facts(self, operation, body):
        if "resource_id" not in body or "resource" not in body:
            return 500

        if operation is None:
            resource_id = Id.parse_id(body["resource_id"])

            try:
                resource = Resource.deserialize(body["resource"])
                provider = Commander.get_provider(self, resource)

                try:
                    result = provider.check_facts(resource)
                    return 200, {"resource_id": body["resource_id"], "facts": result}

                except Exception:
                    LOGGER.exception("Unable to retrieve fact")
                    return 404, {"resource_id": body["resource_id"]}

            except Exception:
                LOGGER.exception("Unable to find a handler for %s" % resource_id)
                return 500

        return 501

    @protocol.handle(methods.GetQueue)
    def queue(self, operation, body):
        """
            Return the current items in the queue
        """
        return 200, {"queue": ["%s" % (x.id) for x in self._queue.all()]}

    @protocol.handle(methods.GetAgentInfo)
    def info(self, operation, body):
        """
            Return statistics about this agent
        """
        return 200, {"threads": [x.name for x in enumerate()],
                     "queue length": self._queue.size(),
                     "queue ready length": self._queue.ready_size()}

    @protocol.handle(methods.CodeDeploy)
    def code_deploy(self, operation, body):
        version = body["version"]
        modules = body["modules"]
        requires = body["requires"]

        if self._loader is not None:
            self._env.install_from_list(requires)
            self._loader.deploy_version(version, modules)

        return 200

    def update(self, res_obj):
        """
            Process an update
        """
        for req in res_obj.requires:
            self._dm.add_dependency(res_obj, req.version, req.resource_str())

        self._queue.add_resource(res_obj)
        self._last_update = time.time()

    @protocol.handle(methods.ResourceUpdate)
    def resource_update(self, operation, body):
        resource = Resource.deserialize(body["resource"])

        # depending on the transport we still need to filter out resources not meant for this agent
        if resource.id.agent_name in self.end_point_names:
            if "dry_run" in body and body["dry_run"]:
                resource.dry_run = True

            self.update(resource)
            LOGGER.debug("Received update for %s", body["resource"]["id"])
            return 200

        return 404

    @protocol.handle(methods.ResourceUpdated)
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
                continue

            provider.execute(resource)

            if resource.do_reload and provider.can_reload():
                LOGGER.warning("Reloading %s because of updated dependencies" % resource.id)
                provider.do_reload(resource)

            LOGGER.debug("Finished %s" % resource)
            self._queue.remove(resource)

        return

    def get_file(self, hash_id):
        """
            Retrieve a file from the fileserver identified with the given hash
        """
        result = self._client.call(methods.FileMethod, operation="GET", id=hash_id)

        if result.code == 404:
            return None
        else:
            return result.result["content"]

    def resource_updated(self, resource, reload_requires=False, changes={}, status=""):
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

        # send out the resource update
        self._client.call(methods.ResourceUpdated, destination="*", id=resource.id.resource_str(),
                          version=resource.id.version, reload=reload_resource, changes=changes, status=status)

        return 200
