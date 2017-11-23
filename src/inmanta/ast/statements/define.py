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
# pylint: disable-msg=R0923,W0613

import logging

from . import DefinitionStatement
from inmanta.ast.type import ConstraintType, Type
from inmanta.ast.attribute import Attribute, RelationAttribute
from inmanta.ast.entity import Implementation, Entity, Default, Implement
from inmanta.ast.constraint.expression import Equals
from inmanta.ast.statements import TypeDefinitionStatement, Statement, ExpressionStatement, Literal, BiStatement
from inmanta.ast import Namespace, TypingException, DuplicateException, TypeNotFoundException, NotFoundException
from typing import List
from inmanta.execute.runtime import ResultVariable, ExecutionUnit


LOGGER = logging.getLogger(__name__)


class DefineAttribute(Statement):

    def __init__(self, attr_type: str, name: str, default_value: ExpressionStatement=None,
                 multi=False, remove_default=True, nullable=False) -> None:
        """
            if default_value is None, this is an explicit removal of a default value
        """
        self.type = attr_type
        self.name = name
        self.default = default_value
        self.multi = multi
        self.remove_default = remove_default
        self.nullable = nullable


class DefineEntity(TypeDefinitionStatement):
    """
        Define a new entity in the configuration
    """

    def __init__(self,
                 namespace: Namespace,
                 name: str,
                 comment: str,
                 parents: List[str],
                 attributes: List[DefineAttribute]) -> None:
        TypeDefinitionStatement.__init__(self, namespace, name)
        self.name = name
        self.attributes = attributes
        self.comment = comment

        self.parents = parents

        if len(self.parents) == 0 and not (self.name == "Entity" and self.namespace.name == "std"):
            self.parents.append("std::Entity")

        self.type = Entity(self.name, namespace)
        self.type.location = self.location

    def add_attribute(self, attr_type: str, name: str, default_value: ExpressionStatement=None):
        """
            Add an attribute to this entity
        """
        self.attributes.append(DefineAttribute(attr_type, name, default_value))

    def __repr__(self) -> str:
        """
            A textual representation of this entity
        """
        return "Entity(%s)" % self.name

    def get_full_parent_names(self) -> List[str]:
        try:
            return [self.namespace.get_type(str(parent)).get_full_name() for parent in self.parents]
        except TypeNotFoundException as e:
            e.set_statement(self)
            raise e

    def evaluate(self) -> None:
        """
            Evaluate this statement.
        """
        try:
            entity_type = self.type
            entity_type.comment = self.comment

            add_attributes = {}
            for attribute in self.attributes:
                attr_type = self.namespace.get_type(attribute.type)
                if not isinstance(attr_type, (Type, type)):
                    raise TypingException(self, "Attributes can only be a type. Entities need to be defined as relations.")

                attr_obj = Attribute(entity_type, attr_type, attribute.name, attribute.multi, attribute.nullable)
                attribute.copy_location(attr_obj)

                if attribute.name in add_attributes:
                    raise DuplicateException(
                        attr_obj,
                        add_attributes[attribute.name],
                        "Same attribute defined twice in one entity")

                add_attributes[attribute.name] = attr_obj

                if attribute.default is not None:
                    entity_type.add_default_value(attribute.name, attribute.default)
                elif attribute.remove_default:
                    entity_type.add_default_value(attribute.name, None)

            if len(set(self.parents)) != len(self.parents):
                raise TypingException(self, "same parent defined twice")
            for parent in self.parents:
                parent_type = self.namespace.get_type(str(parent))
                if parent_type is self.type:
                    raise TypingException(self, "Entity can not be its own parent (%s) " % parent)
                if not isinstance(parent_type, Entity):
                    raise TypingException(self, "Parents of an entity need to be entities. "
                                          "Default constructors are not supported. %s is not an entity" % parent)

                entity_type.parent_entities.append(parent_type)
                parent_type.child_entities.append(entity_type)

            for parent_type in entity_type.get_all_parent_entities():
                for attr_name, other_attr in parent_type.attributes.items():
                    if attr_name not in add_attributes:
                        add_attributes[attr_name] = other_attr
                    else:
                        # allow compatible attributes
                        my_attr = add_attributes[attr_name]

                        if my_attr.type == other_attr.type:
                            add_attributes[attr_name] = other_attr
                        else:
                            raise DuplicateException(
                                my_attr, other_attr, "Incompatible attributes")
            # verify all attribute compatibility
        except TypeNotFoundException as e:
            e.set_statement(self)
            raise e


class DefineImplementation(TypeDefinitionStatement):
    """
        Define a new implementation that has a name and contains statements

        @param name: The name of the implementation
    """

    def __init__(self, namespace: Namespace, name: str, target_type: str, statements: List[Statement], comment: str):
        TypeDefinitionStatement.__init__(self, namespace, name)
        self.name = name
        self.block = statements
        self.entity = target_type
        self.type = Implementation(self.name, self.block, self.namespace, target_type, comment)
        self.comment = comment

    def __repr__(self) -> str:
        """
            The representation of this implementation
        """
        return "Implementation(%s)" % self.name

    def evaluate(self) -> str:
        """
            Evaluate this statement in the given scope
        """
        cls = self.namespace.get_type(self.entity)
        self.type.set_type(cls)
        self.copy_location(self.type)


class DefineImplementInherits(DefinitionStatement):

    def __init__(self, entity_name: str, comment: str=None):
        DefinitionStatement.__init__(self)
        self.entity = entity_name
        self.comment = comment

    def __repr__(self):
        """
            Returns a representation of this class
        """
        return "ImplementParent(%s)" % (self.entity)

    def evaluate(self):
        """
            Evaluate this statement.
        """
        try:
            entity_type = self.namespace.get_type(self.entity)

            entity_type = entity_type.get_entity()

            entity_type.implements_inherits = True
        except TypeNotFoundException as e:
            e.set_statement(self)
            raise e


class DefineImplement(DefinitionStatement):
    """
        Define a new implementation for a given entity

        @param entity: The name of the entity that is implemented
        @param implementations: A list of implementations
        @param whem: A clause that determines when this implementation is "active"
    """

    def __init__(self,
                 entity_name: str,
                 implementations: List[str],
                 select: ExpressionStatement=None,
                 comment: str=None) -> None:
        DefinitionStatement.__init__(self)
        self.entity = entity_name
        self.implementations = implementations
        self.select = select
        self.comment = comment

    def __repr__(self):
        """
            Returns a representation of this class
        """
        return "Implement(%s)" % (self.entity)

    def evaluate(self):
        """
            Evaluate this statement.
        """
        try:
            entity_type = self.namespace.get_type(self.entity)

            entity_type = entity_type.get_entity()

            implement = Implement()
            implement.comment = self.comment
            implement.constraint = self.select
            implement.location = self.location

            i = 0
            for _impl in self.implementations:
                i += 1

                # check if the implementation has the correct type
                impl_obj = self.namespace.get_type(_impl)

                if (impl_obj.entity is not None and not
                        (entity_type is impl_obj.entity or entity_type.is_parent(impl_obj.entity))):
                    raise Exception("Type mismatch: cannot use %s as implementation for "
                                    " %s because its implementing type is %s" %
                                    (impl_obj.name, entity_type, impl_obj.entity))

                # add it
                implement.implementations.append(impl_obj)

            entity_type.add_implement(implement)
        except TypeNotFoundException as e:
            e.set_statement(self)
            raise e


class DefineTypeConstraint(TypeDefinitionStatement):
    """
        Define a new data type in the configuration. This type is a constrained
        version of a the built-in datatypes

        @param name: The name of the new  type
        @param basetype: The name of the type that is "refined"
    """

    def __init__(self, namespace, name, basetype, expression):
        TypeDefinitionStatement.__init__(self, namespace, name)
        self.basetype = basetype
        self.__expression = None
        self.set_expression(expression)
        self.type = ConstraintType(self.namespace, name)
        self.comment = None

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

        if hasattr(expression, "arguments"):
            # some sort of function call
            expression = Equals(expression, Literal(True))

        for var in expression.requires():
            if var == self.name or var == "self":
                contains_var = True

        if not contains_var:
            raise TypingException(self, "typedef expressions should reference the self variable")

        self.__expression = expression

    expression = property(get_expression, set_expression)

    def __repr__(self):
        """
            A representation of this definition
        """
        return "Type(%s)" % self.name

    def evaluate(self):
        """
            Evaluate this statement.
        """
        basetype = self.namespace.get_type(self.basetype)

        constraint_type = self.type

        constraint_type.comment = self.comment
        constraint_type.basetype = basetype
        constraint_type.constraint = self.expression
        self.expression.normalize()


class DefineTypeDefault(TypeDefinitionStatement):
    """
        Define a new entity that is based on an existing entity and default values for attributes.

        @param name: The name of the new type
        @param class_ctor: A constructor statement
    """

    def __init__(self, namespace, name, class_ctor):
        TypeDefinitionStatement.__init__(self, namespace, name)
        self.type = Default(self.name)
        self.ctor = class_ctor
        self.comment = None

    def __repr__(self):
        """
            Get a representation of this default
        """
        return "Constructor(%s, %s)" % (self.name, self.ctor)

    def evaluate(self):
        """
            Evaluate this statement.
        """
        # the base class
        type_class = self.namespace.get_type(self.ctor.class_type)

        self.type.comment = self.comment

        default = self.type
        default.set_entity(type_class)

        for name, value in self.ctor.get_attributes().items():
            default.add_default(name, value)


class DefineRelation(BiStatement):
    """
        Define a relation
    """

    def __init__(self, left, right, annotations=[]):
        DefinitionStatement.__init__(self)
        # for later evaluation
        self.annotation_expression = [(ResultVariable(), exp) for exp in annotations]
        # for access to results
        self.annotations = [exp[0] for exp in self.annotation_expression]

        self.left = left
        self.right = right

        self.requires = None
        self.comment = None

    def __repr__(self):
        """
            The represenation of this relation
        """
        return "Relation(%s, %s)" % (self.left[0], self.right[0])

    def evaluate(self):
        """
            Add this relation to the participating ends
        """
        try:
            left = self.namespace.get_type(self.left[0])
        except TypeNotFoundException as e:
            e.set_location(self.location)
            raise e

        if isinstance(left, Default):
            raise TypingException(
                self,
                "Can not define relation on a default constructor %s, use base type instead: %s " % (
                    left.name, left.get_entity().get_full_name())
            )

        if left.get_attribute_from_related(self.right[1]) is not None:
            raise DuplicateException(self, left.get_attribute_from_related(self.right[1]),
                                     ("Attribute name %s is already defined in %s, unable to define relationship")
                                     % (self.right[1], left.name))

        try:
            right = self.namespace.get_type(self.right[0])
        except TypeNotFoundException as e:
            e.set_location(self.location)
            raise e

        if isinstance(right, Default):
            raise TypingException(
                self,
                "Can not define relation on a default constructor %s, use base type instead: %s " % (
                    right.name, right.get_entity().get_full_name())
            )

        if right.get_attribute_from_related(self.left[1]) is not None:
            raise DuplicateException(self, right.get_attribute_from_related(self.left[1]),
                                     ("Attribute name %s is already defined in %s, unable to define relationship")
                                     % (self.left[1], right.name))

        if self.left[1] is not None:
            left_end = RelationAttribute(right, left, self.left[1])
            left_end.target_annotations = self.annotations
            left_end.set_multiplicity(self.left[2])
            left_end.comment = self.comment
            self.copy_location(left_end)
        else:
            left_end = None

        if self.right[1] is not None:
            right_end = RelationAttribute(left, right, self.right[1])
            right_end.source_annotations = self.annotations
            right_end.set_multiplicity(self.right[2])
            right_end.comment = self.comment
            self.copy_location(right_end)
        else:
            right_end = None

        if left_end is not None and right_end is not None:
            left_end.end = right_end
            right_end.end = left_end

    def emit(self, resolver, queue) -> None:
        for rv, exp in self.annotation_expression:
            reqs = exp.requires_emit(resolver, queue)
            ExecutionUnit(queue, resolver, rv, reqs, exp)

    def normalize(self) -> None:
        for _, exp in self.annotation_expression:
            exp.normalize()


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

    def evaluate(self):
        """
            Add the index to the entity
        """
        entity_type = self.namespace.get_type(self.type)

        allattributes = entity_type.get_all_attribute_names()
        for attribute in self.attributes:
            if attribute not in allattributes:
                raise NotFoundException(self, attribute, "Index defined on attribute that does not exist")

        entity_type.add_index(self.attributes)


class PluginStatement(TypeDefinitionStatement):
    """
        This statement defines a plugin function
    """

    def __init__(self, namespace, name, function_class):
        TypeDefinitionStatement.__init__(self, namespace, name)
        self._name = name
        self._function_class = function_class
        self.type = self._function_class(namespace)

    def __repr__(self):
        """
            The representation of this function
        """
        return "Function(%s)" % self._name

    def evaluate(self):
        """
            Evaluate this plugin
        """


class DefineImport(TypeDefinitionStatement):

    def __init__(self, name, toname):
        DefinitionStatement.__init__(self)
        self.name = name
        self.toname = toname

    def register_types(self):
        self.target = self.namespace.get_ns_from_string(self.name)
        if self.target is None:
            raise TypeNotFoundException(self.name, self.namespace)
        self.namespace.import_ns(self.toname, self)

    def evaluate(self):
        """
            Evaluate this plugin
        """
