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

import logging
import os
import time
import base64
from typing import Dict, List

from inmanta import protocol, const
from inmanta.agent.handler import Commander
from inmanta.execute.util import Unknown, NoneValue
from inmanta.resources import resource, Resource, to_id, IgnoreResourceException
from inmanta.config import Option, is_uuid_opt, is_list, is_str
from inmanta.execute.proxy import DynamicProxy, UnknownException
from inmanta.ast import RuntimeException, CompilerException, Locatable
from tornado.ioloop import IOLoop
from tornado import gen
from inmanta.execute.runtime import Instance, ResultVariable
from inmanta.util import hash_file
import itertools
from inmanta.ast.entity import Entity
from inmanta.util import groupby
from inmanta.ast.attribute import RelationAttribute
import inmanta.model as model
LOGGER = logging.getLogger(__name__)

unknown_parameters = []

cfg_env = Option("config", "environment", None, "The environment this model is associated with", is_uuid_opt)
cfg_export = Option("config", "export", "", "The list of exporters to use", is_list)
cfg_unknown_handler = Option("unknown_handler", "default", "prune-agent", "default method to handle unknown values ", is_str)


class DependencyCycleException(Exception):

    def __init__(self, start):
        super().__init__()
        self.start = start
        self.cycle = [start]
        self.running = True

    def add_to_cycle(self, node):
        if node == self.start:
            self.running = False
        elif self.running:
            self.cycle.append(node)

    def __str__(self, *args, **kwargs):
        return "Cycle in dependencies: %s" % self.cycle


@gen.coroutine
def upload_code(conn, tid, version, resource_to_sourcemap):
    allfiles = {myhash: source_code for sourcemap in resource_to_sourcemap.values()
                for myhash, (file_name, module, source_code, req) in sourcemap.items()}

    res = yield conn.stat_files(list(allfiles.keys()))
    if res is None or res.code != 200:
        raise Exception("Unable to upload handler plugin code to the server (msg: %s)" % res.result)

    for file in res.result["files"]:
        res = yield conn.upload_file(id=file, content=base64.b64encode(allfiles[file].encode()).decode("ascii"))
        if res is None or res.code != 200:
            raise Exception("Unable to upload handler plugin code to the server (msg: %s)" % res.result)

    compactmap = {resource: {myhash: (file_name, module, req) for
                             myhash, (file_name, module, source_code, req)in sourcemap.items()}
                  for resource, sourcemap in resource_to_sourcemap.items()}

    res = yield conn.upload_code_batched(tid=tid, id=version, resources=compactmap)
    if res is None or res.code != 200:
        raise Exception("Unable to upload handler plugin code to the server (msg: %s)" % res.result)


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
        self._resource_state = {}
        self._unknown_objects = set()
        self._version = 0
        self._scope = None

        self._file_store = {}
        self._io_loop = IOLoop.current()

    def _get_instance_proxies_of_types(self, types):
        """
            Returns a dict of instances for the given types
        """
        proxies = {}
        for t in types:
            if self.types is not None and t in self.types:
                proxies[t] = [DynamicProxy.return_value(i) for i in self.types[t].get_all_instances()]
            else:
                proxies[t] = []

        return proxies

    def _load_resources(self, types):
        """
            Load all registered resources
        """
        entities = resource.get_entity_resources()
        resource_mapping = {}
        ignored_set = set()

        for entity in entities:
            if entity not in types:
                continue
            instances = types[entity].get_all_instances()
            if len(instances) > 0:
                for instance in instances:
                    try:
                        res = Resource.create_from_model(self, entity, DynamicProxy.return_value(instance))
                        resource_mapping[instance] = res
                        self.add_resource(res)
                    except UnknownException:
                        ignored_set.add(instance)
                        # We get this exception when the attribute that is used to create the object id contains an unknown.
                        # We can safely ignore this resource == prune it
                        LOGGER.debug("Skipped resource of type %s because its id contains an unknown (location: %s)",
                                     entity, instance.location)

                    except IgnoreResourceException:
                        ignored_set.add(instance)
                        LOGGER.info("Ignoring resource of type %s because it requested to ignore it. (location: %s)",
                                    entity, instance.location)

        Resource.convert_requires(resource_mapping, ignored_set)

    def _run_export_plugins(self):
        """
            Run any additional export plug-ins
        """
        export = []
        for pl in cfg_export.get():
            export.append(pl.strip())

        for name in export:
            if name.strip() == '':
                continue

            if name not in self.__class__.__export_functions:
                raise Exception("Export function %s does not exist." % name)

            types, function = self.__class__.__export_functions[name]

            if len(types) > 0:
                function(self, types=self._get_instance_proxies_of_types(types))
            else:
                function(self)

    def _call_dep_manager(self, types):
        """
            Call all dep managers and let them add dependencies
        """
        for fnc in self.__class__.__dep_manager:
            try:
                fnc(types, self._resources)
            except UnknownException:
                LOGGER.debug("Dependency manager %s caused an unknown exception", fnc)

        # TODO: check for cycles

    def _validate_graph(self):
        """
            Validate the graph and if requested by the user, dump it
        """
        done = set()

        def find_cycle(current, working):
            if current in done:
                return
            if current in working:
                raise DependencyCycleException(current)
            working.add(current)
            for dep in current.requires:
                try:
                    find_cycle(dep, working)
                except DependencyCycleException as e:
                    e.add_to_cycle(current)
                    raise e
            done.add(current)
            working.remove(current)

        for res in self._resources.values():
            if res not in done:
                find_cycle(res, set())

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

    def run(self, types, scopes, metadata={}, no_commit=False, include_status=False, model_export=False):
        """
        Run the export functions
        """
        self.types = types
        self.scopes = scopes
        self._version = int(time.time())

        # first run other export plugins
        self._run_export_plugins()

        if types is not None:
            # then process the configuration model to submit it to the mgmt server
            self._load_resources(types)

            # call dependency managers
            self._call_dep_manager(types)

        # validate the dependency graph
        self._validate_graph()

        resources = self.resources_to_list()

        if len(self._resources) == 0:
            LOGGER.warning("Empty deployment model.")

        model = {}

        if self.options and self.options.json:
            with open(self.options.json, "wb+") as fd:
                fd.write(protocol.json_encode(resources).encode("utf-8"))
            if len(self._resources) > 0 or len(unknown_parameters) > 0:
                model = ModelExporter(types).export_all()
                with open(self.options.json + ".types", "wb+") as fd:
                    fd.write(protocol.json_encode(model).encode("utf-8"))
        elif len(self._resources) > 0 or len(unknown_parameters) > 0 and not no_commit:
            model = None
            if types is not None and model_export:
                model = ModelExporter(types).export_all()

            self.commit_resources(self._version, resources, metadata, model)
            LOGGER.info("Committed resources with version %d" % self._version)

        if include_status:
            return self._version, self._resources, self._resource_state, model
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
        except RuntimeException:
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

        resource.set_version(self._version)

        if resource.id in self._resources:
            raise CompilerException("Resource %s exists more than once in the configuration model" % resource.id)

        is_undefined = False
        for unknown in resource.unknowns:
            is_undefined = True
            value = getattr(resource, unknown)
            if value.source is not None and hasattr(value.source, "_type"):
                self._unknown_objects.add(to_id(value.source))

        if is_undefined:
            self._resource_state[resource.id.resource_str()] = const.ResourceState.undefined
        else:
            self._resource_state[resource.id.resource_str()] = const.ResourceState.available

        self._resources[resource.id] = resource
        self._resource_to_host[resource.id] = resource.id.agent_name

    def resources_to_list(self) -> List[Dict[str, str]]:
        """
        Convert the resource list to a json representation
        @return: A json string
        """
        resources = []

        for res in self._resources.values():
            resources.append(res.serialize())

        return resources

    def run_sync(self, function):
        return self._io_loop.run_sync(function, 300)

    def deploy_code(self, tid, version=None):
        """
            Deploy code to the server
        """
        if version is None:
            version = int(time.time())

        def merge_dict(a, b):
            """Very specific impl to this particular data structure."""
            for k, v in b.items():
                if k not in a:
                    a[k] = v
                elif isinstance(v, dict):
                    merge_dict(a[k], v)
                else:
                    if a[k] != v:
                        raise Exception("Hash collision!", k, a[k], v)

        LOGGER.info("Sending resources and handler source to server")
        sources = resource.sources()
        merge_dict(sources, Commander.sources())

        LOGGER.info("Uploading source files")

        conn = protocol.Client("compiler")

        @gen.coroutine
        def call():
            yield upload_code(conn, tid, version, sources)

        self.run_sync(call)

    def commit_resources(self, version: int, resources: List[Dict[str, str]],
                         metadata: Dict[str, str], model: Dict) -> None:
        """
            Commit the entire list of resource to the configurations server.
        """
        tid = cfg_env.get()
        if tid is None:
            LOGGER.error("The environment for this model should be set!")
            return

        self.deploy_code(tid, version)

        conn = protocol.Client("compiler")
        LOGGER.info("Uploading %d files" % len(self._file_store))

        # collect all hashes and send them at once to the server to check
        # if they are already uploaded
        hashes = list(self._file_store.keys())

        def call():
            return conn.stat_files(files=hashes)

        res = self.run_sync(call)

        if res.code != 200:
            raise Exception("Unable to check status of files at server")

        to_upload = res.result["files"]

        LOGGER.info("Only %d files are new and need to be uploaded" % len(to_upload))
        for hash_id in to_upload:
            content = self._file_store[hash_id]

            def call():
                return conn.upload_file(id=hash_id, content=base64.b64encode(content).decode("ascii"))

            res = self.run_sync(call)

            if res.code != 200:
                LOGGER.error("Unable to upload file with hash %s" % hash_id)
            else:
                LOGGER.debug("Uploaded file with hash %s" % hash_id)

        # Collecting version information
        version_info = {"export_metadata": metadata,
                        "model": model}

        # TODO: start transaction
        LOGGER.info("Sending resource updates to server")
        for res in resources:
            LOGGER.debug("  %s", res["id"])

        def put_call():
            return conn.put_version(tid=tid, version=version, resources=resources, unknowns=unknown_parameters,
                                    resource_state=self._resource_state, version_info=version_info)

        res = self.run_sync(put_call)

        if res.code != 200:
            LOGGER.error("Failed to commit resource updates (%s)", res.result["message"])

    def get_unknown_resources(self, hostname):
        """
            This method returns the resources that have unknown values for a
            given host
        """
        if hostname in self._unknown_per_host:
            return self._unknown_per_host[hostname]

        return set()

    def upload_file(self, content=None):
        """
            Upload a file to the configuration server. This operation is not
            executed in the transaction.
        """
        if not isinstance(content, bytes):
            content = content.encode('utf-8')

        hash_id = hash_file(content)
        self._file_store[hash_id] = content

        return hash_id


class dependency_manager(object):  # noqa: H801
    """
    Register a function that manages dependencies in the configuration model that will be deployed.
    """

    def __init__(self, function):
        Exporter.add_dependency_manager(function)


class export(object):  # noqa: H801
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


@export("none")
def export_none(options, scope, config):
    pass


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


def location(obj: Locatable):
    loc = obj.get_location()
    return model.Location(loc.file, loc.lnr)


def relation_name(type: Entity, rel: RelationAttribute):
    if rel is None:
        return ""
    return type.get_full_name() + "." + rel.name


class ModelExporter(object):

    def __init__(self, types):
        self.root_type = types["std::Entity"]
        self.types = types

    def export_types(self):
        """
            Run after export_model!!
        """
        def convert_comment(value):
            if value is None:
                return ''
            else:
                return str(value)

        def convert_value_for_type(value):
            if isinstance(value, Unknown):
                raise Exception("annotations should not be unknown")
            if isinstance(value, Instance):
                return model.ReferenceValue(self.entity_ref[value])
            else:
                return model.DirectValue(value)

        def convert_attribute(attr):
            return model.Attribute(attr.type.type_string(), attr.is_optional(), attr.is_multi(),
                                   convert_comment(attr.comment), location(attr))

        def convert_relation(relation: RelationAttribute):

            return model.Relation(relation.type.get_full_name(),
                                  [relation.low, relation.high],
                                  relation_name(relation.type, relation.end),
                                  convert_comment(relation.comment), location(relation),
                                  [convert_value_for_type(x.get_value()) for x in relation.source_annotations],
                                  [convert_value_for_type(x.get_value()) for x in relation.target_annotations])

        def convert_type(mytype):
            return model.Entity([x.get_full_name() for x in mytype.parent_entities],
                                {n: convert_attribute(attr) for n, attr in mytype.get_attributes().items()
                                 if not isinstance(attr, RelationAttribute)},
                                {n: convert_relation(attr) for n, attr in mytype.get_attributes().items()
                                 if isinstance(attr, RelationAttribute)},
                                location(mytype))
        return {k: convert_type(v).to_dict() for k, v in self.types.items() if isinstance(v, Entity)}

    def export_model(self):
        entities = self.root_type.get_all_instances()

        entities_per_type = {t: [e for e in g] for t, g in groupby(entities, lambda x: x.type.get_full_name())}

        entity_ref = {e: t + "_" + str(i) for t, es in entities_per_type.items() for e, i in zip(es, itertools.count(1))}
        self.entity_ref = entity_ref

        def convert(value):
            if isinstance(value, Unknown):
                return "_UNKNOWN_"
            if isinstance(value, Instance):
                return entity_ref[value]
            return value

        def convert_relation(value: ResultVariable):
            if value.is_ready() and value.value is not None:
                rawvalue = value.get_value()
            else:
                # no value present
                return {"values": []}
            if not isinstance(rawvalue, list):
                rawvalue = [rawvalue]
            return {"values": [convert(v) for v in rawvalue]}

        def convert_attribute(value: ResultVariable):
            rawvalue = value.get_value()
            if isinstance(rawvalue, Unknown):
                return {"unknowns": [0]}
            if isinstance(rawvalue, NoneValue):
                return {"nones": [0]}
            if not isinstance(rawvalue, list):
                rawvalue = [rawvalue]
                return {"values": rawvalue}
            else:
                unknowns = []
                offset = 0
                for i in range(0, len(rawvalue)):
                    value = rawvalue[i - offset]
                    if isinstance(value, Unknown):
                        unknowns.append(i)
                        del rawvalue[i - offset]
                        offset += 1
                if len(unknowns) > 0:
                    return {"values": rawvalue, "unknowns": unknowns}
                else:
                    return {"values": rawvalue}

        def convert_entity(original):
            attributes = {}
            relations = {}
            map = {"type": original.type.get_full_name(), "relations": relations, "attributes": attributes}
            for name, value in original.slots.items():
                if name == "self":
                    pass
                elif isinstance(value.type, Entity):
                    relations[name] = convert_relation(value)
                else:
                    attributes[name] = convert_attribute(value)
            return map

        maps = {entity_ref[k]: convert_entity(k) for k in entities}

        return maps

    def export_all(self):
        return {
            "instances": self.export_model(),
            "types": self.export_types()
        }
