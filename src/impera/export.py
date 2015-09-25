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
import hashlib
import json
import logging
import os
import time
import glob

from impera import protocol
from impera.agent.handler import Commander
from impera.execute import NotFoundException
from impera.execute.util import Unknown
from impera.resources import resource, Resource
from impera.config import Config
from impera.module import Project

LOGGER = logging.getLogger(__name__)

unknown_parameters = []


def classes(t):
    if t.__name__ == "EntityType" and t.__module__.startswith("impera"):
        return []

    cls_name = t.__name__
    nm_name = t.__module__.replace(".", "::")
    clslist = ["%s::%s" % (nm_name, cls_name)]

    for nt in t.__bases__:
        clslist += classes(nt)

    return clslist


class Exporter(object):
    """
        This class handles exporting the compiled configuration model
    """
    __export_functions = {}
    __id_conversion = {}
    __dep_manager = []

    @classmethod
    def add(cls, name, types, function):
        """
            Add a new export function
        """
        cls.__export_functions[name] = (types, function)

    @classmethod
    def add_id(cls, type_id, function):
        """
            Add a new id conversion function
        """
        cls.__id_conversion[type_id] = function

    @classmethod
    def get_id(cls, resource):
        """
            Get an id using a registered id conversion function
        """
        for cls_name in classes(resource.type()):
            if cls_name in cls.__id_conversion:
                function = cls.__id_conversion[cls_name]

                return function(resource)

        return None

    @classmethod
    def reset(cls):
        """
            Reset the state
        """
        cls.__id_conversion = {}

    @classmethod
    def add_dependency_manager(cls, function):
        """
            Register a new dependency manager
        """
        cls.__dep_manager.append(function)

    def __init__(self, options=None):
        self.options = options

        self._resources = {}
        self._resource_to_host = {}
        self._unknown_hosts = set()
        self._unknown_objects = set()
        self._unknown_per_host = defaultdict(set)
        self._version = 0
        self._scope = None

        self._offline = False
        self._file_store = {}

    def _get_instances_of_types(self, types):
        """
            Returns a dict of instances for the given types
        """
        values = {}
        for t in types:
            variable = self.get_variable(t)

            if variable is not None:
                values[t] = set([x for x in variable.get_all_instances()])

        return values

    def _load_resources(self, scope):
        """
            Load all registered resources
        """
        entities = resource.get_entity_resources()
        for entity in entities:
            instances = self._get_instances_of_types([entity])
            if len(instances) > 0:
                for instance in instances[entity]:
                    self.add_resource(Resource.create_from_model(self, entity, instance))

        Resource.convert_requires()

    def _run_export_plugins(self):
        """
            Run any additional export plug-ins
        """
        export = []
        for pl in Config.get("config", "export", "").split(","):
            export.append(pl.strip())

        for name in export:
            if name.strip() == '':
                continue

            if name not in self.__class__.__export_functions:
                raise Exception("Export function %s does not exist." % name)

            types, function = self.__class__.__export_functions[name]

            if len(types) > 0:
                function(self, types=self._get_instances_of_types(types))
            else:
                function(self)

    def _call_dep_manager(self, scope):
        """
            Call all dep managers and let them add dependencies
        """
        for fnc in self.__class__.__dep_manager:
            fnc(scope, self._resources)

        # TODO: check for cycles

    def _validate_graph(self):
        """
            Validate the graph and if requested by the user, dump it
        """
        if self.options and self.options.depgraph:
            dot = "digraph G {\n"
            for res in self._resources.values():
                res_id = str(res.id)
                dot += '\t"%s";\n' % res_id

                for req in res.requires:
                    dot += '\t"%s" -> "%s";\n' % (res_id, str(req))

            dot += "}\n"

            with open("dependencies.dot", "wb+") as fd:
                fd.write(dot.encode())

    def _get_unkown_policy(self, agent_name):
        """
            Determine the unknown handling policy for the given agent
        """
        default_policy = Config.get("unknown_handler", "default", "prune-agent")

        if "unknown_handler" not in Config._get_instance():
            return default_policy

        for agent_pattern, policy in Config._get_instance()["unknown_handler"].items():
            if agent_pattern == "default":
                continue

            if glob.fnmatch.fnmatchcase(agent_name, agent_pattern):
                return policy

        return default_policy

    def _filter_unknowns(self):
        """
            Filter unknown resources from the configuration model
        """
        pruned_all = set()
        pruned_resources = set()
        for res_id in list(self._resources.keys()):
            res = self._resources[res_id]
            host = self._resource_to_host[res_id]
            policy = self._get_unkown_policy(host)
            if host in self._unknown_hosts and policy == "prune-agent":
                del self._resources[res_id]
                pruned_all.add(host)

            elif len(res.unknowns) > 0 and policy == "prune-resource":
                # will not happen in current code, resource is never added to the model
                del self._resources[res_id]
                pruned_resources.add(host)

        if len(self._unknown_hosts) > 0:
            LOGGER.info("The configuration of the following hosts is not exported due to unknown " +
                        "configuration parameters (prune-agent policy):")
            hosts = sorted(list(pruned_all))
            for host in hosts:
                LOGGER.info(" - %s" % host)

            LOGGER.info("Some resources of the following hosts is not exported due to unknown " +
                        "configuration parameters (prune-resource policy):")
            hosts = sorted(list(pruned_resources))
            for host in hosts:
                LOGGER.info(" - %s" % host)

    def run(self, scope, offline=False):
        """
        Run the export functions
        """
        self._offline = offline
        self._scope = scope
        self._version = int(time.time())
        Resource.clear_cache()

        # first run other export plugins
        self._run_export_plugins()

        # then process the configuration model to submit it to the mgmt server
        self._load_resources(scope)

        # call dependency managers
        self._call_dep_manager(scope)

        # filter out any resource that belong to hosts that have unknown values
        self._filter_unknowns()

        # validate the dependency graph
        self._validate_graph()

        resources = self.resources_to_list()

        if len(self._resources) == 0:
            LOGGER.warning("Empty deployment model.")

        if self.options and self.options.json:
            with open(self.options.json, "wb+") as fd:
                fd.write(json.dumps(resources).encode("utf-8"))

        elif len(self._resources) > 0 and not offline:
            self.commit_resources(self._version, resources)

        LOGGER.info("Committed resources with version %d" % self._version)
        return self._version, self._resources

    def get_variable(self, name):
        """
        Searches a variables and returns its value.
        """
        parts = name.split("::")
        variable_name = parts[-1]
        namespace = parts[0:-1]

        try:
            variable = self._scope.get_variable(variable_name, namespace).value
        except NotFoundException:
            return None

        return variable

    def get_scope(self, scope_name):
        """
        Return the scope with the given name
        """
        return self._scope.get_scope(["__config__"])

    def add_resource(self, resource):
        """
            Add a new resource to the list of exported resources. When
            commit_resources is called, the entire list of resources is send
            to the the server.

            A resource is a map of attributes. This method validates the id
            of the resource and will add a version (if it is not set already)
        """
        if resource.version > 0:
            raise Exception("Versions should not be added to resources during model compilation.")

        for unknown in resource.unknowns:
            value = getattr(resource, unknown)
            self._unknown_hosts.add(resource.id.agent_name)
            if value.source is not None:
                self._unknown_objects.add(Exporter.get_id(value.source))

            self._unknown_per_host[resource.id.agent_name].add(str(resource.id))
            LOGGER.debug("Host %s has unknown values (in resource %s)" % (resource.id.agent_name, resource.id))

        resource.set_version(self._version)
        self._resources[resource.id] = resource
        self._resource_to_host[resource.id] = resource.id.agent_name

    def resources_to_list(self):
        """
        Convert the resource list to a json representation
        @return: A json string
        """
        resources = []

        for res in self._resources.values():
            resources.append(res.serialize())

        return resources

    def deploy_code(self, tid, version=None):
        """
            Deploy code to the server
        """
        if version is None:
            version = int(time.time())

        if not self._offline:
            LOGGER.info("Sending resources and handler source to server")
            sources = resource.sources()
            sources.update(Commander.sources())

            requires = Project.get().collect_requirements()

            LOGGER.info("Uploading source files")

            conn = protocol.Client("compiler", "client")
            res = conn.upload_code(tid=tid, id=version, sources=sources, requires=list(requires))

            if res is None or res.code != 200:
                raise Exception("Unable to upload handler plugin code to the server (msg: %s)" % res.result)

        else:
            LOGGER.info("Offline mode, so not sending configuration to the server")

    def commit_resources(self, version, resources):
        """
            Commit the entire list of resource to the configurations server.
        """
        tid = Config.get("config", "environment", None)
        if tid is None:
            LOGGER.error("The environment for this model should be set!")
            return

        self.deploy_code(tid, version)

        conn = protocol.Client("compiler", "client")
        if not self._offline:
            LOGGER.info("Uploading %d files" % len(self._file_store))

            # collect all hashes and send them at once to the server to check
            # if they are already uploaded
            hashes = list(self._file_store.keys())

            res = conn.stat_files(files=hashes)

            if res.code != 200:
                raise Exception("Unable to check status of files at server")

            to_upload = res.result["files"]

            LOGGER.info("Only %d files are new and need to be uploaded" % len(to_upload))
            for hash_id in to_upload:
                content = self._file_store[hash_id]
                res = conn.upload_file(id=hash_id, content=content)

                if res.code != 200:
                    LOGGER.error("Unable to upload file with hash %s" % hash_id)
                else:
                    LOGGER.debug("Uploaded file with hash %s" % hash_id)

        # TODO: start transaction
        LOGGER.info("Sending resource updates to server")
        for res in resources:
            LOGGER.debug("  %s", res["id"])

        res = conn.put_version(tid=tid, version=version, resources=resources, unknowns=unknown_parameters)
        if res.code != 200:
            LOGGER.error("Failed to commit resource updates")

    def get_unknown_resources(self, hostname):
        """
            This method returns the resources that have unknown values for a
            given host
        """
        if hostname in self._unknown_per_host:
            return self._unknown_per_host[hostname]

        return set()

    def _hash_file(self, content):
        """
            Create a hash from the given content
        """
        sha1sum = hashlib.new("sha1")
        sha1sum.update(content)

        return sha1sum.hexdigest()

    def upload_file(self, content=None):
        """
            Upload a file to the configuration server. This operation is not
            executed in the transaction.
        """
        content_str = content
        if isinstance(content, bytes):
            content_str = content.decode('utf-8')
        else:
            content = content.encode('utf-8')

        hash_id = self._hash_file(content)

        self._file_store[hash_id] = content_str

        return hash_id

    def get_offline_files(self):
        return self._file_store


class Offline(object):
    """
        Handles offline stuff
    """
    _instance = None

    @classmethod
    def get(cls, new=False):
        if cls._instance is None or new:
            cls._instance = Offline()

        return cls._instance

    def __init__(self):
        self._facts = {}

    def set_facts(self, resource, facts):
        """
            Set the facts for a given resource
        """
        self._facts[resource] = facts

    def get_fact(self, resource, name, default=None):
        if resource not in self._facts or name not in self._facts[resource]:
            return default

        return self._facts[resource][name]


class dependency_manager(object):
    """
    Register a function that manages dependencies in the configuration model that will be deployed.
    """
    def __init__(self, function):
        Exporter.add_dependency_manager(function)


class export(object):
    """
        A decorator that registers an export function
    """
    def __init__(self, name, *args):
        self.name = name
        self.types = args

    def __call__(self, function):
        """
            The wrapping
        """
        Exporter.add(self.name, self.types, function)
        return function


class resource_to_id(object):
    """
        Register a function to convert a resource to an id
    """
    def __init__(self, type_id):
        self.type_id = type_id

    def __call__(self, function):
        """
            The wrapping
        """
        Exporter.add_id(self.type_id, function)
        return function


@export("none")
def export_none(options, scope, config):
    pass


@export("report", "std::File", "std::Host", "drm::Logconfig")
def export_report(options, types):
    # prefix = types["drm::Logconfig"][0].prefix
    prefix = "report"

    with open(prefix + "_host.csv", "w+") as fd:
        # first, generate stats about each host
        fd.write("hostname, files, services, packages, directories\n")
        for host in types["std::Host"]:
            fd.write("%s,%d,%d,%d,%d\n" % (host.name, len(host.files),
                                           len(host.services), len(host.packages), len(host.directories)))

    report = defaultdict(int)
    with open(prefix + "_parameters.csv", "w+") as fd:
        # print out template stats
        fd.write("hostname, template, filename, name, value, type, index\n")
        for host in types["std::Host"]:
            for file in host.files:
                if hasattr(file.content, "stats"):
                    stats = file.content.stats
                    row = "%s,%s,%s" % (host.name, file.content.template, file.path)

                    for stat in stats:
                        fd.write("%s,%s,%s,%s,%s\n" % (row, stat[0], stat[1], stat[3], stat[2]))
                        report[stat[3]] += 1

    with open(prefix + "_param_summary.csv", "w+") as fd:
        for t, value in report.items():
            fd.write("%s,%s\n" % (t, value))

    if not os.path.exists(prefix):
        os.mkdir(prefix)

    for file in types["std::File"]:
        path = os.path.join(prefix, file.host.name + file.path.replace("/", "+"))
        with open(path, "w+") as fd:
            fd.write(file.content)


@export("dump", "std::File", "std::Service", "std::Package")
def export_dumpfiles(options, types):
    prefix = "dump"

    if not os.path.exists(prefix):
        os.mkdir(prefix)

    for file in types["std::File"]:
        path = os.path.join(prefix, file.host.name + file.path.replace("/", "+"))
        with open(path, "w+") as fd:
            if isinstance(file.content, Unknown):
                fd.write("UNKNOWN -> error")
            else:
                fd.write(file.content)

    path = os.path.join(prefix, "services")
    with open(path, "w+") as fd:
        for svc in types["std::Service"]:
            fd.write("%s -> %s\n" % (svc.host.name, svc.name))

    path = os.path.join(prefix, "packages")
    with open(path, "w+") as fd:
        for pkg in types["std::Package"]:
            fd.write("%s -> %s\n" % (pkg.host.name, pkg.name))
