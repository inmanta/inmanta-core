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
from itertools import chain
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Set, Tuple

import inmanta.ast.type as inmanta_type
import inmanta.execute.dataflow as dataflow
from inmanta import const, module
from inmanta.ast import (
    AttributeException,
    CompilerException,
    DoubleSetException,
    LocatableString,
    Location,
    MultiException,
    Namespace,
    Range,
)
from inmanta.ast.entity import Entity
from inmanta.ast.statements.define import DefineEntity, DefineRelation, PluginStatement
from inmanta.compiler import config as compiler_config
from inmanta.compiler.data import CompileData
from inmanta.execute import scheduler
from inmanta.execute.dataflow.datatrace import DataTraceRenderer
from inmanta.execute.dataflow.root_cause import UnsetRootCauseAnalyzer
from inmanta.execute.proxy import UnsetException
from inmanta.execute.runtime import ResultVariable
from inmanta.parser import ParserException
from inmanta.plugins import Plugin, PluginMeta
from inmanta.stable_api import stable_api

LOGGER: logging.Logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from inmanta.ast import BasicBlock, Statement  # noqa: F401


def do_compile(refs: Dict[Any, Any] = {}) -> Tuple[Dict[str, inmanta_type.Type], Namespace]:
    """
    Perform a complete compilation run for the current project (as returned by :py:meth:`inmanta.module.Project.get`)

    :param refs: Datastructure used to pass on mocking information to the compiler. Supported options:
                    * key="facts"; value=Dict with the following structure: {"<resource_id": {"<fact_name>": "<fact_value"}}
    """
    compiler = Compiler(refs=refs)

    LOGGER.debug("Starting compile")

    project = module.Project.get()
    try:
        (statements, blocks) = compiler.compile()
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

    types: Dict[str, inmanta_type.Type] = scheduler.get_types()
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


def anchormap(refs: Dict[Any, Any] = {}) -> Sequence[Tuple[Location, Location]]:
    """
    Return all lexical references

    Performs compilation up to and including the type resolution, but doesn't start executing

    :param refs: Datastructure used to pass on mocking information to the compiler. Supported options:
                    * key="facts"; value=Dict with the following structure: {"<resource_id": {"<fact_name>": "<fact_value"}}
    """
    compiler = Compiler(refs=refs)

    LOGGER.debug("Starting compile")

    (statements, blocks) = compiler.compile()
    sched = scheduler.Scheduler()
    return sched.anchormap(compiler, statements, blocks)


def get_types_and_scopes() -> Tuple[Dict[str, inmanta_type.Type], Namespace]:
    """
    Only run the compilation steps required to extract the different types and scopes.
    """
    compiler = Compiler()
    (statements, blocks) = compiler.compile()
    sched = scheduler.Scheduler(compiler_config.track_dataflow())
    sched.define_types(compiler, statements, blocks)
    return sched.get_types(), compiler.get_ns()


class Compiler(object):
    """
    An inmanta compiler

    :param cf_file: DEPRECATED
    :param refs: Datastructure used to pass on mocking information to the compiler. Supported keys:
                    * key="facts"; value=Dict with the following structure: {"<resource_id": {"<fact_name>": "<fact_value"}}
    """

    def __init__(self, cf_file: str = "main.cf", refs: Dict[Any, Any] = {}) -> None:
        self.__root_ns: Optional[Namespace] = None
        self._data: CompileData = CompileData()
        self.plugins: Dict[str, Plugin] = {}
        self.refs = refs

    def get_plugins(self) -> Dict[str, Plugin]:
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
        with open(path, "r", encoding="utf-8") as file_d:
            return file_d.read()

    def compile(self) -> Tuple[List["Statement"], List["BasicBlock"]]:
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

        # load plugins
        for name, cls in PluginMeta.get_functions().items():

            mod_ns = cls.__module__.split(".")
            if mod_ns[0] != const.PLUGINS_PACKAGE:
                raise Exception(
                    "All plugin modules should be loaded in the %s package not in %s" % (const.PLUGINS_PACKAGE, cls.__module__)
                )

            mod_ns = mod_ns[1:]

            ns: Optional[Namespace] = self.__root_ns
            for part in mod_ns:
                if ns is None:
                    break
                ns = ns.get_child(part)

            if ns is None:
                raise Exception("Unable to find namespace for plugin module %s" % (cls.__module__))

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
            file.write("%s\n" % self._data.export().json())

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
                unset_attrs: Dict[dataflow.AttributeNode, UnsetException] = {
                    cause.instance.instance_node.node().register_attribute(cause.attribute.name): cause
                    for cause in exception.get_causes()
                    if isinstance(cause, UnsetException)
                    if cause.instance is not None
                    if cause.instance.instance_node is not None
                    if cause.attribute is not None
                }
                root_causes: Set[dataflow.AttributeNode] = UnsetRootCauseAnalyzer(unset_attrs.keys()).root_causes()
                for attr, e in unset_attrs.items():
                    if attr not in root_causes:
                        exception.others.remove(e)
                handled = True
            causes: List[CompilerException] = exception.get_causes()
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
