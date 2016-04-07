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
from impera.ast.variables import AttributeVariable, Reference, Variable
from impera.execute import DuplicateVariableException, NotFoundException
from impera.stats import Stats
from impera.execute.util import Unknown
from impera.execute.runtime import ExecutionContext, ResultVariable


class Import(GeneratorStatement):
    """
        This class models importing statements from a module

        @param name: The name of the statement to include
    """

    def __init__(self, name):
        GeneratorStatement.__init__(self)
        self.name = name
        self.child_namespace = True

    def types(self, recursive=False):
        """
            A list of types this statement requires

            @see State#types
        """
        return [("module", self.name)]

    def references(self):
        """
            @see DynamicStatement#references
        """
        refs = []

        return refs

    def __repr__(self):
        """
            The representation of this object
        """
        return "Import(%s)" % self.name

    def evaluate(self, state, local_scope):
        """
            Evaluate the module by clone the statements and inserting them
            in the namespace of this statement
        """
        module = state.get_type("module")

        for statement in module.statements:
            state.add_statement(statement, self.child_namespace)


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
            rk, rv) in i.constraint.stmts[0].requires_emit(resolver, queue).items()}
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
            if len(expr.stmts) != 1:
                raise Exception("Compiler fault: two statements in selector")
            expr = expr.stmts[0]
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
        self.variable = variable
        self.loop_var = loop_var
        self.module = module

    def __repr__(self):
        return "For(%s)" % self.variable

    def normalize(self, resolver):
        self.variable.normalize(resolver)
        # self.loop_var.normalize(resolver)
        self.module.normalize(resolver)

    def requires(self):
        base = self.variable.requires()
        var = self.loop_var
        ext = self.module.requires()
        ext.add_var(var)
        return [set(base + ext) - set(var)]

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
            xc.lookup(self.loop_var, loop_var)
            xc.emit(queue)


class Constructor(GeneratorStatement):
    """
        This class represents the usage of a constructor to create a new object.

        @param class_type: The type of the object that is created by this
            constructor call.
    """

    def __init__(self, class_type):
        GeneratorStatement.__init__(self)
        self.class_type = class_type
        self.__attributes = {}
        self.implemented = False
        self.register = False

    def normalize(self, resolver):
        self.type = resolver.get_type(self.class_type.full_name)
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

    def types(self, recursive=False):
        """
            @see Statement#types()
        """
        return [("classtype", self.class_type)]

    def actions(self, state):
        """
            @see DynamicStatement#actions
        """
        type_class = state.get_type("classtype")
        object_ref = state.get_result_reference()
        actions = [("add", Variable(type_class)), ("set", object_ref)]

        if isinstance(type_class, Default):
            type_class = type_class.get_entity()

        attribute_statements = {}
        if state.has_attribute("new_statements"):
            attribute_statements = state.get_attribute("new_statements")

        local_scope = state.get_local_scope()

        for attribute_name in type_class.get_all_attribute_names():
            # Set a attributes with low multiplicity == 0 -> set []
            attribute_obj = type_class.get_attribute(attribute_name)
            if hasattr(attribute_obj, "low") and attribute_obj.low == 0:
                actions.append(("add", AttributeVariable.create(object_ref, attribute_name)))

            if state.get_ref(attribute_name) is not None and attribute_name in attribute_statements:
                stmt = attribute_statements[attribute_name]
                value_ref = state.get_ref(attribute_name)
                actions.extend(stmt.build_action_list(local_scope, value_ref, object_ref,
                                                      instance_type=type_class.get_class_type()))

        return actions

    def new_statements(self, state):
        """
            Add any arguments that need to be validated to the graph
        """
        set_attribute_stmts = {}
        attributes = set()

        # Set the value from the constructor
        object_ref = state.get_result_reference()
        for name, value in self.__attributes.items():
            # set the attributes passed with the constructor
            stmt = SetAttribute(object_ref, name, value)

            attributes.add(name)
            state.add_ref(name, value)
            set_attribute_stmts[name] = stmt

        # Set values defined in default constructors
        type_class = state.get_type("classtype")
        if isinstance(type_class, Default):
            default = type_class
            type_class = type_class.get_entity()

            # set default values
            for attribute_name in type_class.get_all_attribute_names():
                attribute = type_class.get_attribute(attribute_name)

                if attribute.name not in attributes:
                    try:
                        value = default.get_default(attribute.name)
                        stmt = SetAttribute(object_ref, attribute.name, value)

                        attributes.add(attribute.name)
                        state.add_ref(attribute.name, value)
                        set_attribute_stmts[attribute.name] = stmt
                    except AttributeError:
                        pass

        # Set default values if they have not been set yet
        for name, value in type_class.get_default_values().items():
            if name not in attributes and value is not None:
                stmt = SetAttribute(object_ref, name, value)
                state.add_ref(name, value)
                set_attribute_stmts[name] = stmt

        state.set_attribute("new_statements", set_attribute_stmts)

        # Make values of attributes available in subscopes by defining
        # variables with matching names in the subscope
        object_id = Scope.object_to_name(state)
        namespace = Namespace(object_id, state.namespace)
        scope = Scope.get_or_create_scope(state.graph, namespace.to_path())

        added_variables = set()
        for attribute in type_class.get_all_attribute_names():
            if attribute in added_variables:
                continue

            var = AttributeVariable.create(object_ref, attribute)
            self.copy_location(var)
            added_variables.add(attribute)
            scope.add_variable(attribute, var)

        # set the self variable
        scope.add_variable("self", object_ref)

    def __repr__(self):
        """
            The representation of the this statement
        """
        return "Construct(%s)" % (self.class_type)

    def can_evaluate(self, state):
        """
            A constructor can always be evaluated
        """
        return True
