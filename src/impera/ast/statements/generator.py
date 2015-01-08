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

    Contect: bart@impera.io
"""

# pylint: disable-msg=W0613,R0201

from . import GeneratorStatement
from impera.ast import Namespace
from impera.ast.entity import Default
from impera.ast.statements.assign import SetAttribute
from impera.ast.variables import AttributeVariable, Reference, Variable
from impera.execute import DuplicateVariableException, NotFoundException
from impera.execute.scope import Scope
from impera.execute.state import DynamicState
from impera.stats import Stats


class Import(GeneratorStatement):
    """
        This class models importing statements from a module

        @param name: The name of the statement to include
    """
    def __init__(self, name):
        GeneratorStatement.__init__(self)
        self.name = name
        self.child_namespace = True

    def types(self):
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


class Implement(GeneratorStatement):
    """
        This statement selects an implementation for a given object and
        imports the statements
    """
    def __init__(self, instance_type, instance):
        GeneratorStatement.__init__(self)
        self.instance_type = instance_type
        self.instance = instance

    def _get_required_variables(self):
        """
            Get a dictionary of all variables that the combined expressions
            require.
        """
        required = {}
        for impl in self.instance_type.implementations:
            if impl.constraint is not None:
                variables = impl.constraint.get_variables()
                for var in variables:
                    required[var.name] = var

        return required

    def types(self):
        """
            @see DynamicStatement#types
        """
        types = []
        for implementation in self.instance_type.implementations:
            if implementation.constraint is not None:
                types.extend(implementation.constraint.types())

        return types

    def references(self):
        """
            @see DynamicStatement#references
        """
        refs = []

        for var_name, value in self._get_required_variables().items():
            refs.append((var_name, value))

        return refs

    def get_implementation(self, state, local_scope):
        """
            Search in the list of implementation for an implementation that
            matches the select clause. If no select clause matches and a default
            implementation exists, this is chosen.

            If more then one select clause matches an exception will be thrown.
        """
        defaults = []
        select_list = []
        for implementation in self.instance_type.implementations:
            if implementation.constraint is None:
                defaults.append(implementation)

            else:  # evaluate the expression
                expr = implementation.constraint
                variables = expr.get_variables()
                parameters = {}

                for var in variables:
                    ref = state.get_ref(var.name)
                    parameters[var.name] = ref

                if expr.eval(variables=parameters, state=state):
                    select_list.append(implementation)

        implementations = []
        implementations.extend(select_list)
        implementations.extend(defaults)

        return implementations

    def evaluate(self, state, local_scope):
        """
            Evaluate this statement
        """
        implement_list = self.get_implementation(state, local_scope)

        if len(implement_list) == 0:
            raise Exception("Unable to select implementation for entity %s" %
                            self.instance_type.name)

        implementations = []
        for impl in implement_list:
            implementations.extend(impl.implementations)

        for impl in implementations:
            # generate a subscope/namespace for each loop
            object_id = Scope.object_to_name(impl)
            namespace = Namespace(object_id, state.namespace)

            # create the scope and restrict it to the entity we implement
            Scope.get_or_create_scope(state.graph, namespace.to_path(), restrict_to_parent=True)

            for stmt in impl.statements:
                child_state = DynamicState(state.compiler, namespace, stmt)
                child_state.add_to_graph(state.graph)
                state._child_statements[stmt] = child_state

        Stats.get("refine").increment(len(implementations))

    def __repr__(self):
        return "EntityImplement(%s)" % self.instance


class For(GeneratorStatement):
    """
        A for loop
    """
    def __init__(self, variable, loop_var, module_name):
        GeneratorStatement.__init__(self)
        self.variable = variable
        self.loop_var = loop_var
        self.module_name = module_name

    def __repr__(self):
        return "For(%s)" % self.variable

    def references(self):
        """
            @see DynamicStatement#references
        """
        return [("variable", self.variable)]

    def actions(self, state):
        """
            @see DynamicStatement#actions
        """
        actions = []
        instance = state.get_ref("variable")
        actions.append(("get", instance))
        return actions

    def evaluate(self, state, local_scope):
        """
            Evaluate this statement.
        """
        var = state.get_ref("variable").value

        for loop_var in var:
            # generate a subscope/namespace for each loop
            object_id = Scope.object_to_name(loop_var)
            namespace = Namespace(object_id, state.namespace)

            sub_scope = Scope.get_or_create_scope(state.graph,
                                                  namespace.to_path())

            # add the loop variable to the scope
            if not isinstance(loop_var, Variable):
                loop_var = Variable(loop_var)

            sub_scope.add_variable(self.loop_var, loop_var)

            # generate the import statement
            import_stmt = Import(self.module_name)
            import_stmt.namespace = namespace
            import_stmt.child_namespace = False

            child_state = DynamicState(state.compiler, namespace, import_stmt)
            child_state.add_to_graph(state.graph)
            state._child_statements[import_stmt] = child_state


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

    def types(self):
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

        for attribute_name in type_class.get_all_attribute_names():
            # Set a attributes with low multiplicity == 0 -> set []
            attribute_obj = type_class.get_attribute(attribute_name)
            if hasattr(attribute_obj, "low") and attribute_obj.low == 0:
                actions.append(("add",
                                AttributeVariable.create(object_ref, attribute_name)))

        return actions

    def new_statements(self, state):
        """
            Add any arguments that need to be validated to the graph
        """
        attributes = set()

        # Set the value from the constructor
        object_ref = state.get_result_reference()
        for name, value in self.__attributes.items():
            # set the attributes passed with the constructor
            stmt = SetAttribute(object_ref, name, value)
            self.copy_location(stmt)
            stmt.namespace = self.namespace
            state.add_statement(stmt)

            attributes.add(name)

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
                        self.copy_location(stmt)
                        stmt.namespace = self.namespace
                        state.add_statement(stmt)

                        attributes.add(attribute.name)
                    except AttributeError:
                        pass

        # Set default values if they have not been set yet
        for name, value in type_class.get_default_values().items():
            if name not in attributes and value is not None:
                stmt = SetAttribute(object_ref, name, value)
                self.copy_location(stmt)
                stmt.namespace = self.namespace
                state.add_statement(stmt)

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

            # Set a attributes with low multiplicity == 0 -> set []
            attribute_obj = type_class.get_attribute(attribute)
            if hasattr(attribute_obj, "low") and attribute_obj.low == 0:
                value = Variable(list())
                stmt = SetAttribute(object_ref, attribute_obj.name, value)
                self.copy_location(stmt)
                stmt.namespace = self.namespace
                state.add_statement(stmt)

        # set the self variable
        scope.add_variable("self", object_ref)

        # now check that all variables that have indexes on them, are already
        # defined and add the instance to the index
        for index in type_class._index_def:
            for attr in index:
                if attr not in attributes:
                    raise Exception("%s is part of an index and should be set in the constructor." % attr)

    def evaluate(self, state, local_scope):
        """
            Evaluate this statement.
        """
        ctor_id = Scope.object_to_name(state)

        # the type to construct
        type_class = state.get_type("classtype")
        if isinstance(type_class, Default):
            type_class = type_class.get_entity()

        object_instance = type_class.get_instance(ctor_id, local_scope)
        object_instance.__statement__ = state

        try:
            local_scope.get_variable("self").value.add_child(object_instance)
        except NotFoundException:
            pass

        if self.implemented:
            # generate an import for the module
            name = Reference(hex(id(self)))
            stmt = Import(name)
            stmt.namespace = self.namespace
            self.copy_location(stmt)
            stmt.child_namespace = False

            state.add_statement(stmt, child_ns=True)

        else:
            # generate an implementation
            stmt = Implement(type_class, object_instance)
            self.copy_location(stmt)
            stmt.namespace = self.namespace
            state.add_statement(stmt, child_ns=True)

        if self.register:
            object_name = str(hex(id(object_instance)))
            local_scope.add_variable(object_name, Variable(object_instance))

        return object_instance

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
