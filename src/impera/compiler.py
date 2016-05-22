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

import os
import sys
import logging
import glob
import imp

from impera.execute import scheduler
from impera.ast import Namespace
from impera.ast.statements.define import DefineEntity, DefineRelation, PluginStatement
from impera.module import Project
from impera.plugins import PluginMeta

LOGGER = logging.getLogger(__name__)


def do_compile():
    """
        Run run run
    """
    # module.Project.get().verify()
    compiler = Compiler(os.path.join(Project.get().project_path, "main.cf"))

    LOGGER.debug("Starting compile")

    (statements, blocks) = compiler.compile()
    sched = scheduler.Scheduler()
    success = sched.run(compiler, statements, blocks)

    LOGGER.debug("Compile done")

    if not success:
        sys.stderr.write("Unable to execute all statements.\n")
    return (sched.get_types(), sched.get_scopes())


class Compiler(object):
    """
        An inmanta compiler

        @param options: Options passed to the application
        @param config: The parsed configuration file
    """

    def __init__(self, cf_file="main.cf"):
        self.__init_cf = "_init.cf"

        self.__cf_file = cf_file
        self.__root_ns = Namespace("__root__")

        self.loaded_modules = {}  # a map of the paths of all loaded modules
        self._units = []
        self.types = {}

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
        with open(path, "r") as file_d:
            return file_d.read()

    def _load_plugins(self, plugin_dir, namespace):
        """
            Load all modules in plugin_dir
        """
        if not os.path.exists(os.path.join(plugin_dir, "__init__.py")):
            raise Exception("The plugin directory %s should be a valid python package with a __init__.py file" % plugin_dir)

        mod_name = ".".join(namespace.to_path())
        imp.load_package(mod_name, plugin_dir)

        for py_file in glob.glob(os.path.join(plugin_dir, "*.py")):
            if not py_file.endswith("__init__.py"):
                # name of the python module
                sub_mod = mod_name + "." + os.path.basename(py_file).split(".")[0]

                # create a namespace for the submodule
                new_ns = Namespace(sub_mod.split(".")[-1])
                new_ns.parent = namespace
                self.graph.add_namespace(new_ns, namespace)

                # load the python file
                imp.load_source(sub_mod, py_file)

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
        self.__root_ns = project.ns

        statements, blocks = project.get_complete_ast()

        # load plugins
        for name, cls in PluginMeta.get_functions().items():

            mod_ns = cls.__module__.split(".")
            if mod_ns[0] != "impera_plugins":
                raise Exception("All plugin modules should be loaded in the impera_plugins package")

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
        entity = DefineEntity(Namespace("std", self.__root_ns), "Entity", "The entity all other entities inherit from.", [], [])

        requires_rel = DefineRelation(("std::Entity", "requires", [0, None], False),
                                      ("std::Entity", "provides", [0, None], False))
        requires_rel.namespace = Namespace("std", self.__root_ns)

        statements.append(entity)
        statements.append(requires_rel)

        return (statements, blocks)
