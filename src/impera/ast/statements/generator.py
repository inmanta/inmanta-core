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

# pylint: disable-msg=W0613,R0201

from . import GeneratorStatement
from impera.ast import Namespace
from impera.ast.statements.assign import SetAttribute
from impera.ast.variables import Reference
from impera.execute import DuplicateVariableException, NotFoundException
from impera.stats import Stats
from impera.execute.util import Unknown
from impera.execute.runtime import ExecutionContext, ResultVariable


class SubConstructor(GeneratorStatement):
    """
        This statement selects an implementation for a given object and
        imports the statements
    """

    def __init__(self, instance_type):
        GeneratorStatement.__init__(self)
        self.type = instance_type

    def normalize(self, resolver):
        # done in define type
        pass

    def requires_emit(self, resolver, queue):
        out = {rk: rv for i in self.type.implements for (
            rk, rv) in i.constraint.requires_emit(resolver, queue).items()}
        return out

    def execute(self, requires, resolver, queue):
        """
            Evaluate this statement
        """
        implement_list = self.get_implementation(requires, resolver, queue)

        if len(implement_list) == 0:
            raise Exception("Unable to select implementation for entity %s" %
                            self.type.name)

        implementations = []
        for impl in implement_list:
            implementations.extend(impl.implementations)

        for impl in implementations:
            # generate a subscope/namespace for each loop
            xc = ExecutionContext(impl.statements, resolver)
            xc.emit(queue)

        Stats.get("refine").increment(len(implementations))
        return "X-I"

    def get_implementation(self, requires, resolver, queue):
        """
            Search in the list of implementation for an implementation that
            matches the select clause. If no select clause matches and a default
            implementation exists, this is chosen.

            If more then one select clause matches an exception will be thrown.
        """

        select_list = []

        for implementation in self.type.implements:
            expr = implementation.constraint
            if expr.execute(requires, resolver, queue):
                select_list.append(implementation)

        return select_list

    def __repr__(self):
        return "EntityImplement(%s)" % self.type


class For(GeneratorStatement):
    """
        A for loop
    """

    def __init__(self, variable, loop_var, module):
        GeneratorStatement.__init__(self)
        self.base = variable
        self.loop_var = loop_var
        self.module = module

    def __repr__(self):
        return "For(%s)" % self.variable

    def normalize(self, resolver):
        self.base.normalize(resolver)
        # self.loop_var.normalize(resolver)
        self.module.normalize(resolver)

    def requires(self):
        base = self.base.requires()
        var = self.loop_var
        ext = self.module.requires
        self.module.add_var(var)
        return list(set(base).union(ext) - set(var))

    def requires_emit(self, resolver, queue):
        return self.base.requires_emit(resolver, queue)

    def execute(self, requires, resolver, queue):
        """
            Evaluate this statement.
        """
        var = self.base.execute(requires, resolver, queue)

        if isinstance(var, Unknown):
            return

        for loop_var in var:
            # generate a subscope/namespace for each loop
            xc = ExecutionContext(self.module, resolver)
            xc.lookup(self.loop_var).set_value(loop_var)
            xc.emit(queue)


class Constructor(GeneratorStatement):
    """
        This class represents the usage of a constructor to create a new object.

        @param class_type: The type of the object that is created by this
            constructor call.
    """

    def __init__(self, class_type, attributes):
        GeneratorStatement.__init__(self)
        self.class_type = class_type
        self.__attributes = {}
        self.implemented = False
        self.register = False
        for a in attributes:
            self.add_attribute(a[0], a[1])

    def normalize(self, resolver):
        self.type = resolver.get_type(self.class_type)
        for (k, v) in self.__attributes.items():
            v.normalize(resolver)

        # now check that all variables that have indexes on them, are already
        # defined and add the instance to the index
        for index in self.type.get_entity().get_indices():
            for attr in index:
                if attr not in self.attributes:
                    raise Exception("%s is part of an index and should be set in the constructor." % attr)

    def requires(self):
        out = [req for (k, v) in self.__attributes.items() for req in v.requires()]
        out.extend([req for (k, v) in self.type.get_defaults().items() for req in v.requires()])
        out.extend([req for (k, v) in self.type.get_entity().get_default_values().items() for req in v.requires()])

        return out

    def requires_emit(self, resolver, queue):
        preout = [x for x in self.__attributes.items()]
        preout.extend([x for x in self.type.get_entity().get_default_values().items()])

        out2 = {rk: rv for (k, v) in self.type.get_defaults().items()
                for (rk, rv) in v.requires_emit(resolver.for_namespace(v.get_containing_namespace()), queue).items()}

        out = {rk: rv for (k, v) in preout for (rk, rv) in v.requires_emit(resolver, queue).items()}
        out.update(out2)
        return out

    def execute(self, requires, resolver, queue):
        """
            Evaluate this statement.
        """
        # the type to construct
        type_class = self.type.get_entity()

        # the attributes
        attributes = {k: v.execute(requires, resolver, queue) for (k, v) in self.__attributes.items()}

        for (k, v) in self.type.get_defaults().items():
            attributes[k] = v.execute(requires, resolver, queue)

        for (k, v) in type_class.get_default_values().items():
            if(k not in attributes):
                attributes[k] = v.execute(requires, resolver, queue)

        # check if the instance already exists in the index (if there is one)
        instances = []
        for index in type_class._index_def:
            params = []
            for attr in index:
                params.append((attr, attributes[attr]))

            obj = type_class.lookup_index(params)
            if obj is not None:
                instances.append(obj)

        if len(instances) > 0:
            # ensure that instances are all the same objects
            first = instances[0]
            for i in instances[1:]:
                if i != first:
                    raise Exception("Inconsistent indexes detected!")

            object_instance = first
        else:
            # create the instance
            object_instance = type_class.get_instance(attributes, resolver, queue)

        # add anonymous implementations
        if self.implemented:
            # generate an import for the module
            raise "don't know this feature"

        else:
            # generate an implementation
            stmt = type_class.get_sub_constructor()
            stmt.emit(object_instance, queue)

        if self.register:
            raise "don't know this feature"

        return object_instance

    def add_attribute(self, name, value):
        """
            Add an attribute to this constructor call
        """
        if name not in self.__attributes:
            self.__attributes[name] = value
        else:
            raise DuplicateVariableException("The attribute %s in the constructor call of %s is already set."
                                             % (name, self.class_type))

    def get_attributes(self):
        """
            Get the attribtues that are set for this constructor call
        """
        return self.__attributes

    attributes = property(get_attributes)

    def __repr__(self):
        """
            The representation of the this statement
        """
        return "Construct(%s)" % (self.class_type)
