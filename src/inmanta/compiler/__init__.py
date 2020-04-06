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
import os
import sys
from itertools import chain
from typing import Dict, List, Optional, Set

import inmanta.ast.type as inmanta_type
import inmanta.execute.dataflow as dataflow
from inmanta import const
from inmanta.ast import (
    AttributeException,
    CompilerException,
    DoubleSetException,
    LocatableString,
    MultiException,
    Namespace,
    Range,
)
from inmanta.ast.entity import Entity
from inmanta.ast.statements.define import DefineEntity, DefineRelation, PluginStatement
from inmanta.compiler import config as compiler_config
from inmanta.execute import scheduler
from inmanta.execute.dataflow.datatrace import DataTraceRenderer
from inmanta.execute.dataflow.root_cause import UnsetRootCauseAnalyzer
from inmanta.execute.proxy import UnsetException
from inmanta.execute.runtime import ResultVariable
from inmanta.module import Project
from inmanta.plugins import PluginMeta

LOGGER = logging.getLogger(__name__)


def do_compile(refs={}):
    """
        Run run run
    """
    project = Project.get()
    compiler = Compiler(os.path.join(project.project_path, project.main_file), refs=refs)

    LOGGER.debug("Starting compile")

    (statements, blocks) = compiler.compile()
    sched = scheduler.Scheduler(compiler_config.track_dataflow())
    try:
        success = sched.run(compiler, statements, blocks)
    except CompilerException as e:
        if compiler_config.dataflow_graphic_enable.get():
            show_dataflow_graphic(sched, compiler)
        compiler.handle_exception(e)

    LOGGER.debug("Compile done")

    if not success:
        sys.stderr.write("Unable to execute all statements.\n")
    if compiler_config.dataflow_graphic_enable.get():
        show_dataflow_graphic(sched, compiler)
    return (sched.get_types(), compiler.get_ns())


def show_dataflow_graphic(scheduler, compiler):
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


def anchormap(refs={}):
    """
        Run run run
    """
    project = Project.get()
    compiler = Compiler(os.path.join(project.project_path, project.main_file), refs=refs)

    LOGGER.debug("Starting compile")

    (statements, blocks) = compiler.compile()
    sched = scheduler.Scheduler()
    return sched.anchormap(compiler, statements, blocks)


class Compiler(object):
    """
        An inmanta compiler

        :param options: Options passed to the application
        :param config: The parsed configuration file
    """

    def __init__(self, cf_file="main.cf", refs={}):
        self.__init_cf = "_init.cf"

        self.__cf_file = cf_file
        self.__root_ns = None
        self.refs = refs

    def get_plugins(self):
        return self.plugins

    def is_loaded(self):
        """
            Is everything loaded and the namespace structure built?
        """
        return self.__root_ns is not None

    def get_ns(self):
        """
            Get the root namespace
        """
        if not self.is_loaded():
            self.load()
        return self.__root_ns

    ns = property(get_ns)

    def read(self, path):
        """
            Return the content of the given file
        """
        with open(path, "r", encoding="utf-8") as file_d:
            return file_d.read()

    def compile(self):
        """
            This method will compile and prepare everything to start evaluation
            the configuration specification.

            This method will:
            - load all namespaces
            - compile the __config__ namespace
            - start resolving it and importing unknown namespaces
        """
        project = Project.get()
        self.__root_ns = project.get_root_namespace()

        project.load()
        statements, blocks = project.get_complete_ast()

        # load plugins
        for name, cls in PluginMeta.get_functions().items():

            mod_ns = cls.__module__.split(".")
            if mod_ns[0] != const.PLUGINS_PACKAGE:
                raise Exception(
                    "All plugin modules should be loaded in the %s package not in %s" % (const.PLUGINS_PACKAGE, cls.__module__)
                )

            mod_ns = mod_ns[1:]

            ns = self.__root_ns
            for part in mod_ns:
                if ns is None:
                    break
                ns = ns.get_child(part)

            if ns is None:
                raise Exception("Unable to find namespace for plugin module %s" % (cls.__module__))

            cls.namespace = ns

            name = name.split("::")[-1]
            statement = PluginStatement(ns, name, cls)
            statements.append(statement)

        # add the entity type (hack?)
        ns = self.__root_ns.get_child_or_create("std")
        nullrange = Range("internal", 1, 0, 0, 0)
        entity = DefineEntity(
            ns, LocatableString("Entity", nullrange, 0, ns), "The entity all other entities inherit from.", [], []
        )
        str_std_entity = LocatableString("std::Entity", nullrange, 0, ns)

        requires_rel = DefineRelation(
            (str_std_entity, LocatableString("requires", nullrange, 0, ns), [0, None], False),
            (str_std_entity, LocatableString("provides", nullrange, 0, ns), [0, None], False),
        )
        requires_rel.namespace = self.__root_ns.get_ns_from_string("std")

        statements.append(entity)
        statements.append(requires_rel)
        return (statements, blocks)

    def handle_exception(self, exception: CompilerException) -> None:
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
