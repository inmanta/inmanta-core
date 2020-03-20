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

from inmanta import const
from inmanta.ast import CompilerException, LocatableString, Range
from inmanta.ast.statements.define import DefineEntity, DefineRelation, PluginStatement
from inmanta.compiler import config as compiler_config
from inmanta.execute import scheduler
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
    sched = scheduler.Scheduler(compiler_config.datatrace_enable.get())
    try:
        success = sched.run(compiler, statements, blocks)
    except CompilerException as e:
        e.attach_compile_info(compiler)
        raise e

    LOGGER.debug("Compile done")

    if not success:
        sys.stderr.write("Unable to execute all statements.\n")
    return (sched.get_types(), compiler.get_ns())


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
