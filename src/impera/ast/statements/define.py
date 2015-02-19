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
# pylint: disable-msg=R0923,W0613

import logging

from . import DefinitionStatement
from impera.ast.variables import Variable, Reference
from impera.ast.type import ConstraintType, Type
from impera.ast.attribute import Attribute, RelationAttribute
from impera.ast.entity import Implementation, Entity, Default, Implement
from impera.ast.constraint.expression import Equals
from impera.execute.scheduler import CallbackHandler


LOGGER = logging.getLogger(__name__)


class DefineEntity(DefinitionStatement):
    """
        Define a new entity in the configuration
    """
    def __init__(self, name, comment):
        DefinitionStatement.__init__(self)
        self.name = name
        self.attributes = []
        self.comment = comment

        self.parents = []

    def add_attribute(self, attr_type, name, default_value=None):
        """
            Add an attribute to this entity
        """
        self.attributes.append((attr_type, name, default_value))

    def types(self, recursive=False):
        """
            Return a list of tupples with the first element the name of how the
            type should be available and the second element the type.
        """
        type_list = []

        # make entity the parent of this type
        if len(self.parents) == 0 and not (self.name == "Entity" and self.namespace.name == "std"):
            self.parents.append(Reference("Entity", ["std"]))

        for parent in self.parents:
            type_list.append((str(parent), parent))

        for attr_type, _name, _default_value in self.attributes:
            type_list.append((str(attr_type), attr_type))

        return type_list

    def __repr__(self):
        """
            A textual representation of this entity
        """
        return "Entity(%s)" % self.name

    def evaluate(self, state, local_scope):
        """
            Evaluate this statement.
        """
        entity_type = Entity(self.name, str(state.namespace))

        add_attributes = set()
        for attribute in self.attributes:
            attr_type = state.get_type(str(attribute[0]))
            if not isinstance(attr_type, (Type, type)):
                raise Exception("Attributes can only be a type. Entities need to be defined as relations.")

            add_attributes.add(attribute[1])
            Attribute(entity_type, attr_type, attribute[1])

            entity_type.add_default_value(attribute[1], attribute[2])

        for parent in self.parents:
            parent_type = state.get_type(str(parent))
            if not isinstance(parent_type, Entity):
                raise Exception("Parents of an entity need to be entities. Default constructors " +
                                "are not supported. %s is not an entity" % parent)

            for attr_name in parent_type.attributes.keys():
                if attr_name not in add_attributes:
                    add_attributes.add(attr_name)

                else:
                    raise Exception("Hiding attributes with inheritance is not allowed. %s is already defined" % attr_name)

            entity_type.parent_entities.add(parent_type)

        local_scope.add_variable(self.name, Variable(entity_type))


class DefineImplementation(DefinitionStatement):
    """
        Define a new implementation that has a name and contains statements

        @param name: The name of the implementation
    """
    def __init__(self, name):
        DefinitionStatement.__init__(self)
        self.name = name
        self.statements = []
        self.entity = None

    def types(self, recursive=True):
        """
            The types this statement requires
        """
        types = []

        if recursive:
            for stmt in self.statements:
                types.extend(stmt.types(recursive=True))

        if self.entity is not None:
            types.append(("entity", self.entity))

        else:
            LOGGER.warning("Deprecated: defining implementations without a reference to the entity they implement " +
                           "is deprecated and will be removed in future versions. Use the " +
                           "'implementation %s for std::Entity:' syntax. at line %d of %s" %
                           (self.name, self.line, self.filename))

        return types

    def add_statement(self, statement):
        """
            Add a statement that is included in the implementation to this
            class.
        """
        self.statements.append(statement)

    def __repr__(self):
        """
            The representation of this implementation
        """
        return "Implementation(%s)" % self.name

    def evaluate(self, state, local_scope):
        """
            Evaluate this statement in the given scope
        """
        if self.entity is not None:
            cls = Implementation(self.name, state.get_type("entity"))
        else:
            cls = Implementation(self.name)

        cls.statements = self.statements
        local_scope.add_variable(self.name, Variable(cls))


class DefineImplement(DefinitionStatement):
    """
        Define a new implementation for a given entity

        @param entity: The name of the entity that is implemented
        @param implementations: A list of implementations
        @param whem: A clause that determines when this implementation is "active"
    """
    def __init__(self, entity_name, implementations, select=None):
        DefinitionStatement.__init__(self)
        self.entity = entity_name
        self.implementations = implementations
        self.select = select

    def __repr__(self):
        """
            Returns a representation of this class
        """
        return "Implement(%s)" % (self.entity)

    def types(self, recursive=False):
        """
            The types this statement requires
        """
        types = [("entity", self.entity)]

        i = 0
        for impl in self.implementations:
            i += 1
            types.append(("impl%d" % i, impl))

        return types

    def evaluate(self, state, local_scope):
        """
            Evaluate this statement.
        """
        entity_type = state.get_type("entity")
        if isinstance(entity_type, Default):
            entity_type = entity_type.get_entity()

        implement = Implement()
        implement.constraint = self.select

        i = 0
        for _impl in self.implementations:
            i += 1
            # check if the implementation has the correct type
            impl_obj = state.get_type("impl%d" % i)
            if impl_obj.entity is not None and not (entity_type is impl_obj.entity or entity_type.is_parent(impl_obj.entity)):
                raise Exception("Type mismatch: cannot use %s as implementation for %s because its implementing type is %s" %
                                (impl_obj.name, entity_type, impl_obj.entity))

            # add it
            implement.implementations.append(impl_obj)

        entity_type.add_implementation(implement)


class DefineTypeConstraint(DefinitionStatement):
    """
        Define a new data type in the configuration. This type is a constrained
        version of a the built-in datatypes

        @param name: The name of the new  type
        @param basetype: The name of the type that is "refined"
    """
    def __init__(self, name, basetype):
        DefinitionStatement.__init__(self)
        self.name = name
        self.basetype = basetype
        self.__expression = None
        self.__expression_requires = None

    def get_expression(self):
        """
            Get the expression that constrains the basetype
        """
        return self.__expression

    def set_expression(self, expression):
        """
            Set the expression that constrains the basetype. This expression
            should reference the value that will be assign to a variable of this
            type. This variable has the same name as the type.
        """
        contains_var = False
        self.__expression_requires = []

        if hasattr(expression, "arguments"):
            # some sort of function call
            expression = Equals(expression, True)

        for var in expression.get_variables():
            if var.name == self.name or var.name == "self":
                contains_var = True
            else:
                self.__expression_requires.append(var)

        if not contains_var:
            raise Exception("typedef expressions should reference the self variable")

        self.__expression = expression

    expression = property(get_expression, set_expression)

    def types(self, recursive=False):
        """
            @see Statement#types
        """
        return [("basetype", self.basetype)]

    def __repr__(self):
        """
            A representation of this definition
        """
        return "Type(%s)" % self.name

    def evaluate(self, state, local_scope):
        """
            Evaluate this statement.
        """
        basetype = state.get_type("basetype")
        constraint_type = ConstraintType(basetype, self.namespace, self.name)
        constraint_type.constraint = self.expression

        local_scope.add_variable(self.name, Variable(constraint_type))


class DefineTypeDefault(DefinitionStatement):
    """
        Define a new entity that is based on an existing entity and default values for attributes.

        @param name: The name of the new type
        @param class_ctor: A constructor statement
    """
    def __init__(self, name, class_ctor):
        DefinitionStatement.__init__(self)
        self.name = name
        self.ctor = class_ctor

    def __repr__(self):
        """
            Get a representation of this default
        """
        return "Constructor(%s, %s)" % (self.name, self.ctor)

    def types(self, recursive=False):
        """
            @see Statement#types
        """
        return [("classtype", self.ctor.class_type)]

    def evaluate(self, state, local_scope):
        """
            Evaluate this statement.
        """
        # the base class
        type_class = state.get_type("classtype")

        default = Default(self.name, type_class)

        for name, value in self.ctor.get_attributes().items():
            default.add_default(name, value)

        local_scope.add_variable(self.name, Variable(default))


class DefineRelation(DefinitionStatement):
    """
        Define a relation
    """
    def __init__(self, left, right):
        DefinitionStatement.__init__(self)

        self.left = left
        self.right = right

        self.requires = None

    def __repr__(self):
        """
            The represenation of this relation
        """
        return "Relation(%s, %s)" % (self.left[0], self.right[0])

    def types(self, recursive=False):
        """
            @see Statement#types
        """
        return [("left", self.left[0]), ("right", self.right[0])]

    def evaluate(self, state, local_scope):
        """
            Add this relation to the participating ends
        """
        left = state.get_type("left")
        if isinstance(left, Default):
            left = left.get_entity()

        if left.get_attribute(self.right[1]) is not None:
            raise Exception(("Attribute name %s is already defined in %s, unable to define relationship")
                            % (self.right[1], left.name))

        right = state.get_type("right")
        if isinstance(right, Default):
            right = right.get_entity()

        if right.get_attribute(self.left[1]) is not None:
            raise Exception(("Attribute name %s is already defined in %s, unable to define relationship")
                            % (self.left[1], right.name))

        left_end = RelationAttribute(right, left, self.left[1], self.left[3])
        left_end.set_multiplicity(self.left[2])

        right_end = RelationAttribute(left, right, self.right[1], self.right[3])
        right_end.set_multiplicity(self.right[2])

        left_end.end = right_end
        right_end.end = left_end

        if self.requires == "<":
            right_end.depends = True
        elif self.requires == ">":
            left_end.depends = True


class DefineIndex(DefinitionStatement):
    """
        This defines an index over attributes in an entity
    """
    def __init__(self, entity_type, attributes):
        DefinitionStatement.__init__(self)
        self.type = entity_type
        self.attributes = attributes

    def types(self, recursive=False):
        """
            @see Statement#types
        """
        return [("type", self.type)]

    def __repr__(self):
        return "index<%s>(%s)" % (self.type, "")

    def evaluate(self, state, local_scope):
        """
            Add the index to the entity
        """
        entity_type = state.get_type("type")
        entity_type.add_index(self.attributes)

        # schedule the entity to check if all attributes in each index exist
        CallbackHandler.schedule_callback("after_types", entity_type.validate_indexes)
