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

import argparse
import base64
import itertools
import logging
import os
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple, Union

import inmanta.model as model
from inmanta import const, loader, protocol
from inmanta.agent.handler import Commander
from inmanta.ast import CompilerException, Locatable, Namespace, OptionalValueException
from inmanta.ast.attribute import RelationAttribute
from inmanta.ast.entity import Entity
from inmanta.config import Option, is_list, is_str, is_uuid_opt
from inmanta.const import ResourceState
from inmanta.data.model import ResourceVersionIdStr
from inmanta.execute.proxy import DynamicProxy, UnknownException
from inmanta.execute.runtime import Instance, ResultVariable
from inmanta.execute.util import NoneValue, Unknown
from inmanta.resources import Id, IgnoreResourceException, Resource, resource, to_id
from inmanta.stable_api import stable_api
from inmanta.util import get_compiler_version, groupby, hash_file

LOGGER = logging.getLogger(__name__)

unknown_parameters: List[Dict[str, str]] = []

cfg_env = Option("config", "environment", None, "The environment this model is associated with", is_uuid_opt)
cfg_export = Option(
    "config",
    "export",
    "",
    "The list of exporters to use. This option is ignored when the --export-plugin option is used.",
    is_list,
)
cfg_unknown_handler = Option("unknown_handler", "default", "prune-agent", "default method to handle unknown values ", is_str)


ModelDict = Dict[str, Entity]
ResourceDict = Dict[Id, Resource]
ProxiedType = Dict[str, Sequence[Union[str, tuple, int, float, bool, "DynamicProxy"]]]


class DependencyCycleException(Exception):
    def __init__(self, start: Resource) -> None:
        super().__init__()
        self.start = start
        self.cycle = [start]
        self.running = True

    def add_to_cycle(self, node: Resource) -> None:
        if node == self.start:
            self.running = False
        elif self.running:
            self.cycle.append(node)

    def __str__(self) -> str:
        return "Cycle in dependencies: %s" % self.cycle


def upload_code(conn: protocol.Client, tid: uuid.UUID, version: int, code_manager: loader.CodeManager) -> None:
    res = conn.stat_files(list(code_manager.get_file_hashes()))
    if res is None or res.code != 200:
        raise Exception("Unable to upload handler plugin code to the server (msg: %s)" % res.result)

    for file in res.result["files"]:
        content = code_manager.get_file_content(file)
        res = conn.upload_file(id=file, content=base64.b64encode(content.encode()).decode("ascii"))
        if res is None or res.code != 200:
            raise Exception("Unable to upload handler plugin code to the server (msg: %s)" % res.result)

    source_map = {
        resource_name: {source.hash: (source.path, source.module_name, source.requires) for source in sources}
        for resource_name, sources in code_manager.get_types()
    }

    res = conn.upload_code_batched(tid=tid, id=version, resources=source_map)
    if res is None or res.code != 200:
        raise Exception("Unable to upload handler plugin code to the server (msg: %s)" % res.result)


class Exporter(object):
    """
    This class handles exporting the compiled configuration model
    """

    # instance vars
    types: Optional[Dict[str, Entity]]
    scopes: Optional[Namespace]
    failed: bool  # did the compile fail?

    # class vars
    __export_functions: Dict[str, Tuple[List[str], Callable[["Exporter", ProxiedType], None]]] = {}
    # type is not entirely right, ProxiedType argument can be absent
    __dep_manager: List[Callable[[ModelDict, ResourceDict], None]] = []

    @classmethod
    def add(cls, name: str, types: List[str], function: Callable[["Exporter", ProxiedType], None]) -> None:
        """
        Add a new export function
        """
        cls.__export_functions[name] = (types, function)

    @classmethod
    def add_dependency_manager(cls, function: Callable[[ModelDict, ResourceDict], None]) -> None:
        """
        Register a new dependency manager
        """
        cls.__dep_manager.append(function)

    def __init__(self, options: argparse.Namespace = None) -> None:
        self.options = options

        self._resources: ResourceDict = {}
        self._resource_state: Dict[str, ResourceState] = {}
        self._unknown_objects: Set[str] = set()
        self._version = 0
        self._scope = None
        self.failed = False

        self._file_store: Dict[str, bytes] = {}

    def _get_instance_proxies_of_types(self, types: List[str]) -> Dict[str, ProxiedType]:
        """Returns a dict of instances for the given types"""
        proxies: Dict[str, ProxiedType] = {}
        for t in types:
            if self.types is not None and t in self.types:
                proxies[t] = [DynamicProxy.return_value(i) for i in self.types[t].get_all_instances()]
            else:
                proxies[t] = []

        return proxies

    def _load_resources(self, types: Dict[str, Entity]) -> None:
        """
        Load all registered resources
        """
        resource.validate()
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
                        LOGGER.debug(
                            "Skipped resource of type %s because its id contains an unknown (location: %s)",
                            entity,
                            instance.location,
                        )

                    except IgnoreResourceException:
                        ignored_set.add(instance)
                        LOGGER.info(
                            "Ignoring resource of type %s because it requested to ignore it. (location: %s)",
                            entity,
                            instance.location,
                        )

        Resource.convert_requires(resource_mapping, ignored_set)

    def _run_export_plugins_specified_in_config_file(self) -> None:
        """
        Run any additional export plug-ins
        """
        export = []
        for pl in cfg_export.get():
            export.append(pl.strip())

        for name in export:
            if name.strip() == "":
                continue
            self.run_export_plugin(name)

    def run_export_plugin(self, name: str) -> None:
        if name not in Exporter.__export_functions:
            raise Exception("Export function %s does not exist." % name)

        types, function = Exporter.__export_functions[name]
        if len(types) > 0:
            function(self, types=self._get_instance_proxies_of_types(types))
        else:
            function(self)

    def _call_dep_manager(self, types: ModelDict) -> None:
        """
        Call all dep managers and let them add dependencies
        """
        for fnc in self.__class__.__dep_manager:
            try:
                fnc(types, self._resources)
            except UnknownException:
                LOGGER.debug("Dependency manager %s caused an unknown exception", fnc)

        # Because dependency managers are only semi-trusted code, we can not assume they respect the proper typing
        # There are already many dependency manager who are somewhat liberal in what they put into the requires set

        def cleanup(requires: Union[ResourceVersionIdStr, Resource, Id]) -> Id:
            """
            Main type cleanup

            :param requires: a requirement, can be a string, resource, Id
            :return: the same requirement, but as an Id
            :raises Exception: the requirement can not be converted
            """

            if isinstance(requires, str):
                myid = Id.parse_id(requires)
                if myid.version == 0:
                    raise Exception(
                        f"A dependency manager inserted a resource id without version this is not allowed {requires}"
                    )
                return myid
            if isinstance(requires, Resource):
                return requires.id
            if isinstance(requires, Id):
                return requires
            raise Exception(
                f"A dependency manager inserted the object {repr(requires)} of type {type(requires)} "
                "into a requires relation. However, only string, Resource or Id are allowable types "
            )

        # Clean up requires and resource_requires
        for res in self._resources.values():
            res.requires = set((cleanup(r) for r in res.requires))
            res.resource_requires = set(self._resources[r] for r in res.requires)

    def _validate_graph(self) -> None:
        """
        Validate the graph and if requested by the user, dump it
        """
        done: Set[Resource] = set()

        def find_cycle(current: Resource, working: Set[Resource]) -> None:
            if current in done:
                return
            if current in working:
                raise DependencyCycleException(current)
            working.add(current)
            for dep in current.resource_requires:
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
                res_id = res.id.resource_version_str()
                dot += '\t"%s";\n' % res_id

                for req in res.resource_requires:
                    dot += '\t"%s" -> "%s";\n' % (res_id, str(req))

            dot += "}\n"

            with open("dependencies.dot", "wb+") as fd:
                fd.write(dot.encode())

    def get_version(self, no_commit=False):
        if no_commit:
            return 0
        tid = cfg_env.get()
        if tid is None:
            LOGGER.warning("The environment for this model should be set for export to server!")
            return 0
        else:
            conn = protocol.SyncClient("compiler")
            result = conn.reserve_version(tid)
            if result.code != 200:
                raise Exception(f"Unable to reserve version number from server (msg: {result.result})")
            return result.result["data"]

    def run(
        self,
        types: Optional[Dict[str, Entity]],
        scopes: Optional[Namespace],
        metadata: Dict[str, str] = {},
        no_commit: bool = False,
        include_status: bool = False,
        model_export: bool = False,
        export_plugin: Optional[str] = None,
    ) -> None:
        """
        Run the export functions
        """
        self.types = types
        self.scopes = scopes
        self._version = self.get_version(no_commit)

        if types is not None:
            # then process the configuration model to submit it to the mgmt server
            self._load_resources(types)

            # call dependency managers
            self._call_dep_manager(types)
            metadata[const.META_DATA_COMPILE_STATE] = const.Compilestate.success.name
            self.failed = False
        else:
            metadata[const.META_DATA_COMPILE_STATE] = const.Compilestate.failed.name
            self.failed = True
            LOGGER.warning("Compilation of model failed.")

        if not self.failed:
            if export_plugin is not None:
                # Run export plugin specified on CLI
                self.run_export_plugin(export_plugin)
            else:
                self._run_export_plugins_specified_in_config_file()

        # validate the dependency graph
        self._validate_graph()

        resources = self.resources_to_list()

        if len(self._resources) == 0:
            LOGGER.warning("Empty deployment model.")

        model: Optional[Dict[str, Any]] = {}

        if self.options and self.options.json:
            with open(self.options.json, "wb+") as fd:
                fd.write(protocol.json_encode(resources).encode("utf-8"))
            if types is not None and model_export:
                if len(self._resources) > 0 or len(unknown_parameters) > 0:
                    model = ModelExporter(types).export_all()
                    with open(self.options.json + ".types", "wb+") as fd:
                        fd.write(protocol.json_encode(model).encode("utf-8"))
        elif (not self.failed or len(self._resources) > 0 or len(unknown_parameters) > 0) and not no_commit:
            model = None
            if types is not None and model_export:
                model = ModelExporter(types).export_all()

            self.commit_resources(self._version, resources, metadata, model)
            LOGGER.info("Committed resources with version %d" % self._version)

        if include_status:
            return self._version, self._resources, self._resource_state, model
        return self._version, self._resources

    def add_resource(self, resource: Resource) -> None:
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

    def resources_to_list(self) -> List[Dict[str, Any]]:
        """Convert the resource list to a json representation"""
        resources = []

        for res in self._resources.values():
            resources.append(res.serialize())

        return resources

    def deploy_code(self, conn: protocol.Client, tid: uuid.UUID, version: int = None) -> None:
        """Deploy code to the server"""
        if version is None:
            version = int(time.time())

        code_manager = loader.CodeManager()
        LOGGER.info("Sending resources and handler source to server")

        # Load both resource definition and handlers
        for type_name, resource_definition in resource.get_resources():
            code_manager.register_code(type_name, resource_definition)

        for type_name, handler_definition in Commander.get_providers():
            code_manager.register_code(type_name, handler_definition)

        LOGGER.info("Uploading source files")

        upload_code(conn, tid, version, code_manager)

    def commit_resources(self, version: int, resources: List[Dict[str, str]], metadata: Dict[str, str], model: Dict) -> None:
        """
        Commit the entire list of resource to the configurations server.
        """
        tid = cfg_env.get()
        if tid is None:
            LOGGER.error("The environment for this model should be set!")
            raise Exception("The environment for this model should be set!")

        conn = protocol.SyncClient("compiler")
        self.deploy_code(conn, tid, version)

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

            res = conn.upload_file(id=hash_id, content=base64.b64encode(content).decode("ascii"))

            if res.code != 200:
                LOGGER.error("Unable to upload file with hash %s" % hash_id)
            else:
                LOGGER.debug("Uploaded file with hash %s" % hash_id)

        # Collecting version information
        version_info = {const.EXPORT_META_DATA: metadata, "model": model}

        # TODO: start transaction
        LOGGER.info("Sending resource updates to server")
        for res in resources:
            LOGGER.debug("  %s", res["id"])

        res = conn.put_version(
            tid=tid,
            version=version,
            resources=resources,
            unknowns=unknown_parameters,
            resource_state=self._resource_state,
            version_info=version_info,
            compiler_version=get_compiler_version(),
        )

        if res.code != 200:
            LOGGER.error("Failed to commit resource updates (%s)", res.result["message"])
            raise Exception("Failed to commit resource updates (%s)" % res.result["message"])

    def upload_file(self, content: Union[str, bytes]) -> str:
        """
        Upload a file to the configuration server. This operation is not
        executed in the transaction.
        """
        bcontent: bytes

        if not isinstance(content, bytes):
            bcontent = content.encode("utf-8")
        else:
            bcontent = content

        hash_id = hash_file(bcontent)
        self._file_store[hash_id] = bcontent

        return hash_id

    def get_environment_id(self) -> str:
        env = str(cfg_env.get())

        if env is None:
            raise Exception("The environment of the model should be configured in config>environment")

        return env


@stable_api
class dependency_manager(object):  # noqa: N801
    """
    Register a function that manages dependencies in the configuration model that will be deployed.
    """

    def __init__(self, function: Callable[[ModelDict, ResourceDict], None]) -> None:
        Exporter.add_dependency_manager(function)


class code_manager(object):  # noqa: N801
    """Register a function that will be invoked after all resource and handler code is collected. A code manager can add
    or modify code before it is uploaded to the server.
    """

    def __init__(self, function: Callable[[], None]) -> None:
        pass


class export(object):  # noqa: N801
    """
    A decorator that registers an export function
    """

    def __init__(self, name: str, *args: str) -> None:
        self.name = name
        self.types = args

    def __call__(self, function: Callable[["Exporter", ProxiedType], None]) -> Callable[["Exporter", ProxiedType], None]:
        """
        The wrapping
        """
        Exporter.add(self.name, self.types, function)
        return function


@export("dump", "std::File", "std::Service", "std::Package")
def export_dumpfiles(exporter: Exporter, types: ProxiedType) -> None:
    prefix = "dump"

    if not os.path.exists(prefix):
        os.mkdir(prefix)

    for file in types["std::File"]:
        path = os.path.join(prefix, file.host.name + file.path.replace("/", "+"))
        with open(path, "w+", encoding="utf-8") as fd:
            if isinstance(file.content, Unknown):
                fd.write("UNKNOWN -> error")
            else:
                fd.write(file.content)

    path = os.path.join(prefix, "services")
    with open(path, "w+", encoding="utf-8") as fd:
        for svc in types["std::Service"]:
            fd.write("%s -> %s\n" % (svc.host.name, svc.name))

    path = os.path.join(prefix, "packages")
    with open(path, "w+", encoding="utf-8") as fd:
        for pkg in types["std::Package"]:
            fd.write("%s -> %s\n" % (pkg.host.name, pkg.name))


def location(obj: Locatable) -> model.Location:
    loc = obj.get_location()
    return model.Location(loc.file, loc.lnr)


def relation_name(type: Entity, rel: RelationAttribute) -> str:
    if rel is None:
        return ""
    return type.get_full_name() + "." + rel.name


class ModelExporter(object):
    def __init__(self, types: ModelDict):
        self.root_type = types["std::Entity"]
        self.types = types

    def export_types(self) -> Dict[str, Any]:
        """
        Run after export_model!!
        """

        def convert_comment(value):
            if value is None:
                return ""
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
            type_string: Optional[str] = attr.type.get_base_type().type_string()
            if type_string is None:
                raise Exception("Type %s can not be represented in the inmanta DSL" % attr.type.get_base_type())
            return model.Attribute(
                type_string, attr.is_optional(), attr.is_multi(), convert_comment(attr.comment), location(attr)
            )

        def convert_relation(relation: RelationAttribute):

            return model.Relation(
                relation.type.get_full_name(),
                (relation.low, relation.high),
                relation_name(relation.type, relation.end),
                convert_comment(relation.comment),
                location(relation),
                [convert_value_for_type(x.get_value()) for x in relation.source_annotations],
                [convert_value_for_type(x.get_value()) for x in relation.target_annotations],
            )

        def convert_type(mytype):
            return model.Entity(
                [x.get_full_name() for x in mytype.parent_entities],
                {
                    n: convert_attribute(attr)
                    for n, attr in mytype.get_attributes().items()
                    if not isinstance(attr, RelationAttribute)
                },
                {
                    n: convert_relation(attr)
                    for n, attr in mytype.get_attributes().items()
                    if isinstance(attr, RelationAttribute)
                },
                location(mytype),
            )

        return {k: convert_type(v).to_dict() for k, v in self.types.items() if isinstance(v, Entity)}

    def export_model(self) -> Dict[str, Any]:
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
            try:
                rawvalue = value.get_value()
            except OptionalValueException:
                return {"nones": [0]}
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

    def export_all(self) -> Dict[str, Any]:
        return {"instances": self.export_model(), "types": self.export_types()}
