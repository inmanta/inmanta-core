"""
Copyright 2017-2019 Inmanta

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
import sys
from collections import abc
from collections.abc import Sequence
from itertools import chain
from typing import TYPE_CHECKING, Any, ClassVar, Optional, Type

import inmanta.ast.type as inmanta_type
import inmanta.execute.dataflow as dataflow
from inmanta import const, module, references, resources
from inmanta.agent import handler
from inmanta.ast import (
    AnchorTarget,
    AttributeException,
    CompilerException,
    DoubleSetException,
    LocatableString,
    Location,
    MultiException,
    Namespace,
    Range,
    UnsetException,
)
from inmanta.ast.entity import Entity
from inmanta.ast.statements.define import DefineEntity, DefineRelation, PluginStatement
from inmanta.compiler import config as compiler_config
from inmanta.compiler.data import CompileData
from inmanta.execute import scheduler
from inmanta.execute.dataflow.datatrace import DataTraceRenderer
from inmanta.execute.dataflow.root_cause import UnsetRootCauseAnalyzer
from inmanta.execute.runtime import ResultVariable
from inmanta.parser import ParserException
from inmanta.plugins import Plugin, PluginMeta
from inmanta.stable_api import stable_api

LOGGER: logging.Logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from inmanta.ast import BasicBlock, Statement  # noqa: F401


def do_compile(refs: Optional[abc.Mapping[object, object]] = None) -> tuple[dict[str, inmanta_type.Type], Namespace]:
    """
    Perform a complete compilation run for the current project (as returned by :py:meth:`inmanta.module.Project.get`)

    :param refs: Datastructure used to pass on mocking information to the compiler. Supported options:
                    * key="facts"; value=Dict with the following structure: {"<resource_id": {"<fact_name>": "<fact_value"}}
    """
    compiler = Compiler(refs=refs)

    LOGGER.debug("Starting compile")

    project = module.Project.get()
    try:
        statements, blocks = compiler.compile()
    except ParserException as e:
        compiler.handle_exception(e)
    sched = scheduler.Scheduler(compiler_config.track_dataflow(), project.get_relation_precedence_policy())
    raised_compile_exception: bool = False
    try:
        success = sched.run(compiler, statements, blocks)
    except CompilerException as e:
        raised_compile_exception = True
        if compiler_config.dataflow_graphic_enable.get():
            show_dataflow_graphic(sched, compiler)
        compiler.handle_exception(e)
        success = False
    finally:
        Finalizers.call_finalizers(raised_compile_exception)
    LOGGER.debug("Compile done")

    if not success:
        sys.stderr.write("Unable to execute all statements.\n")
    if compiler_config.export_compile_data.get():
        compiler.export_data()
    if compiler_config.dataflow_graphic_enable.get():
        show_dataflow_graphic(sched, compiler)
    return (sched.get_types(), compiler.get_ns())


def show_dataflow_graphic(scheduler: scheduler.Scheduler, compiler: "Compiler") -> None:
    from inmanta.execute.dataflow.graphic import GraphicRenderer

    types: dict[str, inmanta_type.Type] = scheduler.get_types()
    ns: Namespace = compiler.get_ns()
    config_ns: Namespace = ns.get_child("__config__")
    GraphicRenderer.view(
        config_ns.get_scope().slots.values(),
        list(
            chain.from_iterable(
                tp.get_all_instances() for tp in types.values() if isinstance(tp, Entity) and tp.namespace is config_ns
            )
        ),
    )


def anchormap(refs: Optional[abc.Mapping[object, object]] = None) -> Sequence[tuple[Location, AnchorTarget]]:
    """
    Return all lexical references

    Performs compilation up to and including the type resolution, but doesn't start executing

    :param refs: Datastructure used to pass on mocking information to the compiler. Supported options:
                    * key="facts"; value=Dict with the following structure: {"<resource_id": {"<fact_name>": "<fact_value"}}
    """
    compiler = Compiler(refs=refs)

    LOGGER.debug("Starting compile")

    statements, blocks = compiler.compile()
    sched = scheduler.Scheduler()
    return sched.get_anchormap(compiler, statements, blocks)


def get_types_and_scopes() -> tuple[dict[str, inmanta_type.Type], Namespace]:
    """
    Only run the compilation steps required to extract the different types and scopes.
    """
    compiler = Compiler()
    statements, blocks = compiler.compile()
    sched = scheduler.Scheduler(compiler_config.track_dataflow())
    sched.define_types(compiler, statements, blocks)
    return sched.get_types(), compiler.get_ns()


@stable_api
class ProjectLoader:
    """
    Singleton providing methods for managing project loading and associated side effects when (sequentially) loading
    more than one project within the same process. Since these operations have global
    side effects, managing them calls for a centralized manager rather than managing them on the Project instance level.
    This class is used by pytest-inmanta, because it executes multiple compiles within the same process.

    This class manages the setting and loading of a project, as well as the following side effects:
        - Python modules: under normal operation, an inmanta module's Python modules are loaded when the project is loaded.
            These modules should not be cleaned up in between two sequential project load operations to prevent that
            object identities of top-level imports change. Dynamic modules are always forcefully cleaned up,
            forcing a reload when next imported.
        - Python module state: since Python module objects are kept alive (see above), any state kept on those objects is
            carried over across compiles. To start each compile from a fresh state, any stateful modules must define one or
            more cleanup functions. This class is responsible for calling these functions when appropriate.
        - Objects registered using decorators: plugins, resources, providers, references and mutators are registered using
            their corresponding decorator. Under normal operation, loading a project registers all these objects as a side
            effect of loading each module's Python modules. When loading more than one project sequentially, this class
            is responsible for completing the set with appropriate previously registered plugins.
    """

    _registered_plugins: ClassVar[dict[str, Type[Plugin]]] = {}
    _registered_resources: ClassVar[dict[str, tuple[type["resources.Resource"], dict[str, str]]]] = {}
    _registered_providers: ClassVar[dict[str, type[handler.ResourceHandler[Any]]]] = {}
    _registered_references: ClassVar[dict[str, type[references.Reference[references.RefValue]]]] = {}
    _registered_mutators: ClassVar[dict[str, type[references.Mutator]]] = {}
    _dynamic_modules: ClassVar[set[str]] = set()

    @classmethod
    def reset(cls) -> None:
        """
        Fully resets the ProjectLoader. For normal pytest-inmanta use this is not required (or even desired). It is used for
        resetting the singleton state in between distinct module tests for pytest-inmanta's own test suite.
        """
        cls._registered_plugins = {}
        cls._registered_resources = {}
        cls._registered_providers = {}
        cls._registered_references = {}
        cls._registered_mutators = {}
        cls._dynamic_modules = set()

    @classmethod
    def load(cls, project: "module.Project") -> None:
        """
        Sets and loads the given project.
        """
        # unload dynamic modules before fetching currently registered objects: they should not be included
        cls._unload_dynamic_modules()
        # add currently registered objects to tracked them before loading the project
        cls._save_compiler_state()
        # reset modules' state
        cls._reset_module_state()

        cls._reset_compiler_state()

        module.Project.set(project, clean=False)
        project.load()

        # complete the set of registered plugins from the previously registered ones
        cls._restore_compiler_state(project)

    @classmethod
    def _save_compiler_state(cls) -> None:
        cls._registered_plugins.update(PluginMeta.get_functions())
        cls._registered_resources.update(dict(resources.resource._resources))
        cls._registered_providers.update(dict(handler.Commander.get_handlers()))
        cls._registered_references.update(dict(references.reference.get_references()))
        cls._registered_mutators.update(dict(references.mutator.get_mutators()))

    @classmethod
    def _reset_compiler_state(cls) -> None:
        PluginMeta.clear()
        resources.resource.reset()
        handler.Commander.reset()
        references.reference.reset()
        references.mutator.reset()

    @classmethod
    def _restore_compiler_state(cls, project: "module.Project") -> None:
        """
        Re-register all compiler state objects.
        """
        for state_type_name, saved_registered, currently_registered_names, register_fnc in [
            (
                "plugin",
                cls._registered_plugins,
                set(PluginMeta.get_functions().keys()),
                lambda name, cls_obj, rest: PluginMeta.add_function(cls_obj),
            ),
            (
                "resource",
                cls._registered_resources,
                set(resources.resource.get_entity_resources()),
                (lambda name, cls_obj, rest: resources.resource.add_resource(name, cls_obj, rest)),
            ),
            (
                "provider",
                cls._registered_providers,
                {fq_prov_name for fq_prov_name, _ in handler.Commander.get_providers()},
                (lambda name, cls_obj, rest: handler.Commander.add_provider(name, cls_obj)),
            ),
            (
                "reference",
                cls._registered_references,
                {ref_name for ref_name, _ in references.reference.get_references()},
                (lambda name, cls_obj, rest: references.reference.add_reference(name, cls_obj)),
            ),
            (
                "mutator",
                cls._registered_mutators,
                {mut_name for mut_name, _ in references.mutator.get_mutators()},
                (lambda name, cls_obj, rest: references.mutator.add_mutator(name, cls_obj)),
            ),
        ]:
            for name, cls_or_tuple in saved_registered.items():
                cls_obj = cls_or_tuple if not isinstance(cls_or_tuple, tuple) else cls_or_tuple[0]
                fq_module_name = cls_obj.__module__
                if fq_module_name.startswith("inmanta."):
                    # Element is not part of a module, it belongs to inmanta-core. No need to register.
                    continue
                if not fq_module_name.startswith("inmanta_plugins."):
                    raise Exception(f"{state_type_name} is not part of the inmanta_plugins package: {fq_module_name}")
                module_name = fq_module_name.removeprefix("inmanta_plugins.").split(".", maxsplit=1)[0]
                if name not in currently_registered_names and module_name in project.modules:
                    register_fnc(name, cls_obj, cls_or_tuple[1] if isinstance(cls_or_tuple, tuple) else None)

    @classmethod
    def register_dynamic_module(cls, module_name: str) -> None:
        """
        Register a module as dynamic by name. Dynamic modules are forcefully reloaded on each project load.
        """
        cls._dynamic_modules.add(module_name)

    @classmethod
    def _unload_dynamic_modules(cls) -> None:
        """
        Unload all registered dynamic modules to force a reload on the next compile. Should be called at least once between
        project loads because it assumes that either a dynamic module is loaded by the currently active project or it was
        not loaded at all.
        """
        project: module.Project
        try:
            project = module.Project.get()
        except module.ProjectNotFoundException:
            # no project has been loaded yet, no need to unload any modules
            return
        for mod in cls._dynamic_modules:
            if mod in project.modules:
                project.modules[mod].unload()

    @classmethod
    def clear_dynamic_modules(cls) -> None:
        """
        Clear the set of registered dynamic modules, unloading them first.
        """
        cls._unload_dynamic_modules()
        cls._dynamic_modules = set()

    @classmethod
    def _reset_module_state(cls) -> None:
        """
        Resets any state kept on Python module objects associated with Inmanta modules by calling predefined cleanup functions.
        """
        for mod_name, mod in sys.modules.items():
            if mod_name.startswith("inmanta_plugins."):
                for func_name, func in mod.__dict__.items():
                    if func_name.startswith("inmanta_reset_state") and callable(func):
                        func()


class Compiler:
    """
    An inmanta compiler

    :param cf_file: DEPRECATED
    :param refs: Datastructure used to pass on mocking information to the compiler. Supported keys:
                    * key="facts"; value=Dict with the following structure: {"<resource_id": {"<fact_name>": "<fact_value"}}
    """

    def __init__(self, cf_file: str = "main.cf", refs: Optional[abc.Mapping[object, object]] = None) -> None:
        self.__root_ns: Optional[Namespace] = None
        self._data: CompileData = CompileData()
        self.plugins: dict[str, Plugin] = {}
        self.refs = refs if refs is not None else {}

    def get_plugins(self) -> dict[str, Plugin]:
        return self.plugins

    def is_loaded(self) -> bool:
        """
        Is everything loaded and the namespace structure built?
        """
        return self.__root_ns is not None

    def get_ns(self) -> Namespace:
        """
        Get the root namespace
        """
        assert self.__root_ns is not None
        return self.__root_ns

    ns = property(get_ns)

    def read(self, path: str) -> str:
        """
        Return the content of the given file
        """
        with open(path, encoding="utf-8") as file_d:
            return file_d.read()

    def compile(self) -> tuple[list["Statement"], list["BasicBlock"]]:
        """
        This method will parse and prepare everything to start evaluation
        the configuration specification.

        This method will:
        - load all modules using Project.get().get_complete_ast()
        - add all plugins
        - create std::Entity
        """
        project = module.Project.get()
        self.__root_ns = project.get_root_namespace()

        project.load()
        statements, blocks = project.get_complete_ast()
        project.log_installed_modules()

        # This lookup variable provides efficiency in the loop below by skipping iterations for plugins
        # that are part of modules that are not imported in the model.
        non_imported_modules: set[str] = set()

        # load plugins
        for name, cls in PluginMeta.get_functions().items():
            if cls.__module__ in non_imported_modules:
                continue

            mod_ns = cls.__module__.split(".")
            if mod_ns[0] != const.PLUGINS_PACKAGE:
                raise Exception(
                    f"All plugin modules should be loaded in the {const.PLUGINS_PACKAGE} package not in {cls.__module__}"
                )

            mod_ns = mod_ns[1:]

            ns: Optional[Namespace] = self.__root_ns
            for part in mod_ns:
                if ns is None:
                    break
                ns = ns.get_child(part)

            if ns is None:
                # This plugin is part of a module that is not imported in the model. We mark this module as such
                # so that future iterations on other plugins from this module can be skipped.
                non_imported_modules.add(cls.__module__)
            else:
                name = name.split("::")[-1]
                statement = PluginStatement(ns, name, cls)
                statements.append(statement)

        # add the entity type (hack?)
        ns = self.__root_ns.get_child_or_create("std")
        nullrange = Range("internal", 1, 0, 0, 0)
        entity = DefineEntity(
            ns,
            LocatableString("Entity", nullrange, 0, ns),
            LocatableString("The entity all other entities inherit from.", nullrange, 0, ns),
            [],
            [],
        )
        str_std_entity = LocatableString("std::Entity", nullrange, 0, ns)

        requires_rel = DefineRelation(
            (str_std_entity, LocatableString("requires", nullrange, 0, ns), (0, None)),
            (str_std_entity, LocatableString("provides", nullrange, 0, ns), (0, None)),
        )
        requires_rel.namespace = self.__root_ns.get_ns_from_string("std")

        statements.append(entity)
        statements.append(requires_rel)
        return (statements, blocks)

    def export_data(self) -> None:
        """
        Exports compiler data if the option has been set.
        """
        with open(compiler_config.export_compile_data_file.get(), "w") as file:
            file.write("%s\n" % self._data.export().model_dump_json())

    def handle_exception(self, exception: CompilerException) -> None:
        try:
            self._handle_exception_datatrace(exception)
        except CompilerException as e:
            self._handle_exception_export(e)

    def _handle_exception_export(self, exception: CompilerException) -> None:
        self._data.add_error(exception)
        if compiler_config.export_compile_data.get():
            self.export_data()
        raise exception

    def _handle_exception_datatrace(self, exception: CompilerException) -> None:
        if not compiler_config.datatrace_enable.get():
            raise exception

        def add_trace(exception: CompilerException) -> bool:
            """
            Add the trace to the deepest possible causes.
            """
            handled: bool = False
            if isinstance(exception, MultiException):
                unset_attrs: dict[dataflow.AttributeNode, UnsetException] = {
                    cause.instance.instance_node.node().register_attribute(cause.attribute.name): cause
                    for cause in exception.get_causes()
                    if isinstance(cause, UnsetException)
                    if cause.instance is not None
                    if cause.instance.instance_node is not None
                    if cause.attribute is not None
                }
                root_causes: set[dataflow.AttributeNode] = UnsetRootCauseAnalyzer(unset_attrs.keys()).root_causes()
                for attr, e in unset_attrs.items():
                    if attr not in root_causes:
                        exception.others.remove(e)
                handled = True
            causes: list[CompilerException] = exception.get_causes()
            for cause in causes:
                if add_trace(cause):
                    handled = True
            if not handled:
                trace: Optional[str] = None
                if isinstance(exception, UnsetException):
                    if (
                        exception.instance is not None
                        and exception.instance.instance_node is not None
                        and exception.attribute is not None
                    ):
                        attribute: dataflow.AttributeNode = exception.instance.instance_node.node().register_attribute(
                            exception.attribute.name
                        )
                        if len(list(attribute.assignments())) > 0:
                            trace = DataTraceRenderer.render(
                                dataflow.InstanceAttributeNodeReference(attribute.instance, attribute.name)
                            )
                if isinstance(exception, DoubleSetException):
                    variable: ResultVariable = exception.variable
                    trace = DataTraceRenderer.render(variable.get_dataflow_node())
                elif isinstance(exception, AttributeException):
                    node_ref: Optional[dataflow.InstanceNodeReference] = exception.instance.instance_node
                    assert node_ref is not None
                    trace = DataTraceRenderer.render(
                        dataflow.InstanceAttributeNodeReference(node_ref.top_node(), exception.attribute)
                    )
                if trace is not None:
                    exception.msg += "\ndata trace:\n%s" % trace
                    handled = True
            return handled

        add_trace(exception)
        exception.attach_compile_info(self)
        raise exception


class Finalizers:
    """
    This class keeps all the finalizers that need to be called right after the compilation finishes
    """

    __finalizers: list[abc.Callable[[], object]] = []

    @classmethod
    def add_function(cls, fnc: abc.Callable[[], object]) -> None:
        cls.__finalizers.append(fnc)

    @classmethod
    def call_finalizers(cls, should_log: bool = False) -> None:
        """
        by default this function will raise exceptions caused by errors in the finalizer functions
        if 'should_log' is set to True the exceptions will not be raised but logged instead.
        """
        excns: list[CompilerException] = []
        for fnc in cls.__finalizers:
            try:
                fnc()
            except Exception as e:
                excns.append(CompilerException("Finalizer failed: " + str(e)))
        if excns:
            if should_log:
                for exception in excns:
                    LOGGER.error(exception.msg)
            else:
                raise excns[0] if len(excns) == 1 else MultiException(excns)

    @classmethod
    def reset_finalizers(cls) -> None:
        cls.__finalizers = []


@stable_api
def finalizer(fnc: abc.Callable[[], object]) -> None:
    """
    Python decorator to register functions with inmanta as Finalizers
    :param fnc: The function to register with inmanta as a finalizer. When used as a decorator this is the function to which the
     decorator is attached.
    """
    Finalizers.add_function(fnc)
