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
import warnings
from collections.abc import Iterator, Sequence
from typing import Optional

from inmanta.ast import (
    Anchor,
    AttributeAnchor,
    CompilerException,
    CompilerRuntimeWarning,
    DuplicateException,
    HyphenException,
    Import,
    IndexException,
    LocatableString,
    Namespace,
    NotFoundException,
    Range,
    RuntimeException,
    TypeAnchor,
    TypeNotFoundException,
    TypeReferenceAnchor,
    TypingException,
)
from inmanta.ast.attribute import Attribute, RelationAttribute
from inmanta.ast.blocks import BasicBlock
from inmanta.ast.entity import Entity, Implement, Implementation
from inmanta.ast.statements import BiStatement, ExpressionStatement, Literal, Statement, TypeDefinitionStatement
from inmanta.ast.type import TYPES, ConstraintType, NullableType, OrReferenceType, Type, TypedList
from inmanta.execute.runtime import ExecutionUnit, QueueScheduler, Resolver, ResultVariable
from inmanta.plugins import Plugin

from . import DefinitionStatement

LOGGER = logging.getLogger(__name__)


class TypeDeclaration(Statement):
    """
    Declaration of a type. A type declaration consists of a base type string and can be
    multi ('basetype[]'), nullable ('basetype?') or both ('basetype[]?').
    """

    def __init__(
        self,
        basetype: LocatableString,
        multi: bool = False,
        nullable: bool = False,
    ) -> None:
        Statement.__init__(self)
        self.basetype: LocatableString = basetype
        self.multi: bool = multi
        self.nullable: bool = nullable

    def get_basetype(self, namespace: Namespace) -> Type:
        """
        Returns the base type for this declaration as a Type.
        """
        return namespace.get_type(self.basetype)

    def get_type(self, namespace: Namespace) -> Type:
        """
        Returns the type for this declaration as a Type.
        """
        tp: Type = self.get_basetype(namespace)
        if self.multi:
            tp = TypedList(tp)
        if self.nullable:
            tp = NullableType(tp)
        return tp

    def __str__(self) -> str:
        return f"{self.basetype}{'[]' if self.multi else ''}{'?' if self.nullable else ''}"


class DefineAttribute(Statement):
    def __init__(
        self,
        attr_type: TypeDeclaration,
        name: LocatableString,
        default_value: Optional[ExpressionStatement] = None,
        remove_default: bool = True,
    ) -> None:
        """
        if default_value is None, this is an explicit removal of a default value
        """
        super().__init__()
        if "-" in name.value:
            raise HyphenException(name)
        self.type = attr_type
        self.name = name
        self.default = default_value
        self.remove_default = remove_default

    def __str__(self) -> str:
        return f"{self.type} {self.name} = {str(self.default) if self.default else ''}"


class DefineEntity(TypeDefinitionStatement):
    """
    Define a new entity in the configuration
    """

    type: Entity

    def __init__(
        self,
        namespace: Namespace,
        lname: LocatableString,
        comment: Optional[LocatableString],
        parents: list[LocatableString],
        attributes: list[DefineAttribute],
    ) -> None:
        name = str(lname)
        TypeDefinitionStatement.__init__(self, namespace, name)
        if "-" in name:
            raise HyphenException(lname)

        self.name = name
        self.attributes = attributes
        if comment is not None:
            self.comment = str(comment)

        self.parents = parents
        self.anchors = [TypeReferenceAnchor(self.namespace, x) for x in self.parents]

        if len(self.parents) == 0 and not (self.name == "Entity" and self.namespace.name == "std"):
            dummy_location: Range = Range("__internal__", 1, 1, 1, 1)
            self.parents.append(LocatableString("std::Entity", dummy_location, -1, namespace))

        self.type = Entity(self.name, namespace, self.comment)
        self.type.location = lname.location

    def add_attribute(
        self, attr_type: LocatableString, name: LocatableString, default_value: Optional[ExpressionStatement] = None
    ) -> None:
        """
        Add an attribute to this entity
        """
        self.attributes.append(DefineAttribute(TypeDeclaration(attr_type), name, default_value))

    def __repr__(self) -> str:
        """
        A textual representation of this entity
        """
        return "Entity(%s)" % self.name

    def get_full_parent_names(self) -> list[str]:
        def resolve_parent(parent: LocatableString) -> str:
            ptype = self.namespace.get_type(parent)
            assert isinstance(ptype, Entity), f"Parents of entities should be entities, but {parent} is a {type(ptype)}"
            return ptype.get_full_name()

        try:
            return [resolve_parent(parent) for parent in self.parents]
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
            is_dataclass = False

            add_attributes: dict[str, Attribute] = {}
            attribute: DefineAttribute
            for attribute in self.attributes:
                attr_type: Type = attribute.type.get_type(self.namespace)
                if not isinstance(attr_type, (Type, type)):
                    raise TypingException(self, "Attributes can only be a type. Entities need to be defined as relations.")

                name = str(attribute.name)
                attr_obj = Attribute(
                    entity_type,
                    OrReferenceType(attribute.type.get_basetype(self.namespace)),
                    name,
                    attribute.get_location(),
                    attribute.type.multi,
                    attribute.type.nullable,
                )
                self.anchors.append(TypeReferenceAnchor(self.namespace, attribute.type.basetype))

                if name in add_attributes:
                    raise DuplicateException(attr_obj, add_attributes[name], "Same attribute defined twice in one entity")

                add_attributes[name] = attr_obj

                if attribute.default is not None or attribute.remove_default:
                    entity_type.add_default_value(name, attribute)

            if len({str(p) for p in self.parents}) != len(self.parents):
                raise TypingException(self, "same parent defined twice")
            for parent in self.parents:
                parent_type = self.namespace.get_type(parent)
                if parent_type is self.type:
                    raise TypingException(self, "Entity can not be its own parent (%s) " % parent)
                if not isinstance(parent_type, Entity):
                    raise TypingException(
                        self,
                        "Parents of an entity need to be entities. "
                        "Default constructors are not supported. %s is not an entity" % parent,
                    )

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
                            raise DuplicateException(my_attr, other_attr, "Incompatible attributes")
                is_dataclass |= parent_type.get_full_name() == "std::Dataclass"

            if is_dataclass:
                entity_type.pair_dataclass_stage1()
            # verify all attribute compatibility
        except TypeNotFoundException as e:
            e.set_statement(self)
            raise e


class DefineImplementation(TypeDefinitionStatement):
    """
    Define a new implementation that has a name and contains statements

    :param name: The name of the implementation
    """

    type: Implementation

    def __init__(
        self,
        namespace: Namespace,
        name: LocatableString,
        target_type: LocatableString,
        statements: BasicBlock,
        comment: LocatableString,
    ):
        TypeDefinitionStatement.__init__(self, namespace, str(name))
        self.name = str(name)
        if "-" in self.name:
            raise HyphenException(name)

        self.block = statements
        self.entity = target_type

        if comment is not None:
            self.comment = str(comment)

        self.location = name.get_location()

        self.type = Implementation(str(self.name), self.block, self.namespace, str(target_type), self.comment)
        self.type.location = name.get_location()

    def __repr__(self) -> str:
        """
        The representation of this implementation
        """
        return "Implementation(%s)" % self.name

    def evaluate(self) -> None:
        """
        Evaluate this statement in the given scope
        """
        try:
            cls = self.namespace.get_type(self.entity)
            self.anchors = [TypeAnchor(self.entity, cls)]
            if not isinstance(cls, Entity):
                raise TypingException(self, f"Implementation can only be define for an Entity, but {self.entity} is a {cls}")
            self.type.set_type(cls)
            self.copy_location(self.type)
        except TypeNotFoundException as e:
            e.set_statement(self)
            raise e

    def get_anchors(self) -> list[Anchor]:
        """
        This method overrides the default get_anchors() to accommodate the two-stage normalization process.
        DefineImplementations register anchors for their blocks. However, these anchors only come into existence
        after the type normalization phase.
        This implementation ensures that anchors are correctly gathered from both the type statements and
        the block itself.
        """
        return [*self.type.statements.get_anchors(), *self.anchors]

    def nested_blocks(self) -> Iterator["BasicBlock"]:
        """
        Returns an iterator over blocks contained within this statement.
        """
        yield self.block


class DefineImplement(DefinitionStatement):
    """
    Define a new implementation for a given entity

    :param entity: The name of the entity that is implemented
    :param implementations: A list of implementations
    :param select: A clause that determines when this implementation is "active"
    :param inherit: True iff the entity should inherit all implementations from its parents
    """

    comment: Optional[str] = None

    def __init__(
        self,
        entity_name: LocatableString,
        implementations: list[LocatableString],
        select: ExpressionStatement,
        inherit: bool = False,
        comment: Optional[LocatableString] = None,
    ) -> None:
        DefinitionStatement.__init__(self)
        self.entity = entity_name
        self.entity_location = entity_name.get_location()
        self.implementations = implementations
        self.location = entity_name.get_location()
        if inherit and (not isinstance(select, Literal) or select.value is not True):
            raise RuntimeException(self, "Conditional implementation with parents not allowed")
        self.select = select
        self.inherit: bool = inherit
        if comment is not None:
            self.comment = str(comment)

    def __repr__(self) -> str:
        """
        Returns a representation of this class
        """
        return "Implement(%s)" % (self.entity)

    def get_anchors(self) -> list[Anchor]:
        """
        This method overrides the default get_anchors() to accommodate the two-stage normalization process.
        DefineImplement should register anchors for an ExpressionStatement. This one is not yet normalized during
        evaluation and so its anchors come into existence only after the type normalization phase.
        This implementation ensures that anchors are also correctly gathered from the type statement.
        """
        return [*self.anchors, *self.select.get_anchors()]

    def evaluate(self) -> None:
        """
        Evaluate this statement.
        """
        try:
            entity_type = self.namespace.get_type(self.entity)
            if not isinstance(entity_type, Entity):
                raise TypingException(
                    self, f"Implementation can only be define for an Entity, but {self.entity} is a {entity_type}"
                )
            self.anchors.append(TypeAnchor(self.entity, entity_type))

            # If one implements statement has parent declared, set to true
            entity_type.implements_inherits |= self.inherit

            implement = Implement()
            implement.comment = self.comment
            implement.constraint = self.select
            implement.location = self.entity_location

            i = 0
            for _impl in self.implementations:
                i += 1

                # check if the implementation has the correct type
                impl_obj = self.namespace.get_type(_impl)
                assert isinstance(impl_obj, Implementation), "%s is not an implementation" % (_impl)

                if impl_obj.entity is not None and not (
                    entity_type is impl_obj.entity or entity_type.is_parent(impl_obj.entity)
                ):
                    raise TypingException(
                        self,
                        "Type mismatch: cannot use %s as implementation for "
                        " %s because its implementing type is %s" % (impl_obj.name, entity_type, impl_obj.entity),
                    )

                # add it
                self.anchors.append(TypeAnchor(_impl, impl_obj))
                implement.implementations.append(impl_obj)

            entity_type.add_implement(implement)
        except TypeNotFoundException as e:
            e.set_statement(self)
            raise e


class DefineTypeConstraint(TypeDefinitionStatement):
    """
    Define a new data type in the configuration. This type is a constrained
    version of a the built-in datatypes

    :param name: The name of the new  type
    :param basetype: The name of the type that is "refined"
    """

    __expression: ExpressionStatement
    type: ConstraintType

    def __init__(
        self, namespace: Namespace, name: LocatableString, basetype: LocatableString, expression: ExpressionStatement
    ) -> None:
        TypeDefinitionStatement.__init__(self, namespace, str(name))
        self.set_location(name.get_location())
        self.basetype = basetype
        self.set_expression(expression)
        self.type = ConstraintType(self.namespace, str(name))
        self.type.location = name.get_location()
        if self.name in TYPES:
            warnings.warn(CompilerRuntimeWarning(self, "Trying to override a built-in type: %s" % self.name))
        if "-" in self.name:
            raise HyphenException(name)

    def get_expression(self) -> ExpressionStatement:
        """
        Get the expression that constrains the basetype
        """
        return self.__expression

    def set_expression(self, expression: ExpressionStatement) -> None:
        """
        Set the expression that constrains the basetype. This expression
        should reference the value that will be assign to a variable of this
        type. This variable has the same name as the type.
        """
        contains_var = False

        for var in expression.requires():
            if var == self.name or var == "self":
                contains_var = True

        if not contains_var:
            raise TypingException(self, "typedef expressions should reference the self variable")

        self.__expression = expression

    expression: ExpressionStatement = property(get_expression, set_expression)

    def __repr__(self) -> str:
        """
        A representation of this definition
        """
        return "Type(%s)" % self.name

    def evaluate(self) -> None:
        """
        Evaluate this statement.
        """
        basetype = self.namespace.get_type(self.basetype)
        assert not basetype.supports_references()
        self.anchors.append(TypeAnchor(self.basetype, basetype))
        constraint_type = self.type

        constraint_type.comment = self.comment
        constraint_type.basetype = basetype
        constraint_type.constraint = self.expression

    def get_anchors(self) -> list[Anchor]:
        """
        This method overrides the default get_anchors() to accommodate the two-stage normalization process.
        DefineTypeConstraint registers anchors for its condition expression. However, these anchors only come into existence
        after the type normalization phase.
        This implementation ensures that anchors are correctly gathered from both the condition expression and
        the statement itself.
        """
        return [*self.anchors, *self.expression.get_anchors()]


Relationside = tuple[LocatableString, Optional[LocatableString], Optional[tuple[int, Optional[int]]]]


class DefineRelation(BiStatement):
    """
    Define a relation
    """

    annotation_expression: list[tuple[ResultVariable, ExpressionStatement]]

    def __init__(self, left: Relationside, right: Relationside, annotations: list[ExpressionStatement] = []) -> None:
        DefinitionStatement.__init__(self)
        if "-" in str(right[1]):
            raise HyphenException(right[1])

        if "-" in str(left[1]):
            raise HyphenException(left[1])
        # for later evaluation
        self.annotation_expression = [(ResultVariable(), exp) for exp in annotations]
        # for access to results
        self.annotations = [exp[0] for exp in self.annotation_expression]

        self.left: Relationside = left
        self.right: Relationside = right

        self.comment = None

    def __repr__(self) -> str:
        """
        The represenation of this relation
        """
        return f"Relation({self.left[0]}, {self.right[0]})"

    def evaluate(self) -> None:
        """
        Add this relation to the participating ends
        """
        try:
            left = self.namespace.get_type(self.left[0])
        except TypeNotFoundException as e:
            e.set_location(self.location)
            raise e

        assert isinstance(left, Entity), "%s is not an entity" % left

        # Duplicate checking is in entity.normalize
        # Because here we don't know if all entities have been defined

        try:
            right = self.namespace.get_type(self.right[0])
        except TypeNotFoundException as e:
            e.set_location(self.location)
            raise e

        assert isinstance(right, Entity), "%s is not an entity" % right
        # Duplicate checking is in entity.normalize
        # Because here we don't know if all entities have been defined

        left_end: Optional[RelationAttribute]
        if self.left[1] is not None:
            left_end = RelationAttribute(right, left, str(self.left[1]), self.left[1].get_location())
            left_end.target_annotations = self.annotations
            left_end.set_multiplicity(self.left[2])
            left_end.comment = self.comment
        else:
            left_end = None

        right_end: Optional[RelationAttribute]
        if self.right[1] is not None:
            if right == left and str(self.left[1]) == str(self.right[1]):
                # relation is its own inverse
                right_end = left_end
            else:
                right_end = RelationAttribute(left, right, str(self.right[1]), self.right[1].get_location())
                right_end.source_annotations = self.annotations
                right_end.set_multiplicity(self.right[2])
                right_end.comment = self.comment
        else:
            right_end = None

        if left_end is not None and right_end is not None:
            left_end.end = right_end
            right_end.end = left_end

    def emit(self, resolver: Resolver, queue: QueueScheduler) -> None:
        for rv, exp in self.annotation_expression:
            reqs = exp.requires_emit(resolver, queue)
            ExecutionUnit(queue, resolver, rv, reqs, exp)

    def normalize(self) -> None:
        for _, exp in self.annotation_expression:
            exp.normalize()
            self.anchors.extend(exp.get_anchors())

        self.anchors.append(TypeReferenceAnchor(self.left[0].namespace, self.left[0]))
        self.anchors.append(TypeReferenceAnchor(self.right[0].namespace, self.right[0]))


class DefineIndex(DefinitionStatement):
    """
    This defines an index over attributes in an entity
    """

    def __init__(self, entity_type: LocatableString, attributes: list[LocatableString]):
        DefinitionStatement.__init__(self)
        self.type = entity_type
        self.attributes: Sequence[LocatableString] = attributes

    def types(self, recursive: bool = False) -> list[tuple[str, LocatableString]]:
        """
        @see Statement#types
        """
        return [("type", self.type)]

    def __repr__(self) -> str:
        return "index {}({})".format(self.type, ", ".join([str(a) for a in self.attributes]))

    def evaluate(self) -> None:
        """
        Add the index to the entity
        """
        entity_type = self.namespace.get_type(self.type)
        assert isinstance(entity_type, Entity), "%s is not an entity" % entity_type
        self.anchors.append(TypeAnchor(self.type, entity_type))

        allattributes = entity_type.get_all_attribute_names()
        for attribute in self.attributes:
            str_attribute = str(attribute)
            if str_attribute not in allattributes:
                raise NotFoundException(
                    self,
                    str_attribute,
                    f"Attribute '{str_attribute}' referenced in index is not defined in entity {entity_type}",
                )
            else:
                rattribute = entity_type.get_attribute(str_attribute)
                self.anchors.append(AttributeAnchor(attribute.get_location(), rattribute))
                assert rattribute is not None  # Make mypy happy
                if rattribute.is_optional() and isinstance(rattribute, RelationAttribute):
                    raise IndexException(
                        self,
                        f"Index can not contain optional relations, Relation ' {attribute}.{entity_type}' is optional",
                    )
                if rattribute.is_multi():
                    raise IndexException(
                        self, f"Index can not contain list attributes, Attribute ' {attribute}.{entity_type}' is a list"
                    )

        entity_type.add_index([str(a) for a in self.attributes], self)


class PluginStatement(TypeDefinitionStatement):
    """
    This statement defines a plugin function
    """

    def __init__(self, namespace: Namespace, name: str, function_class: type[Plugin]) -> None:
        TypeDefinitionStatement.__init__(self, namespace, name)
        self._name = name
        self._function_class = function_class
        self.type = self._function_class(namespace)

    def __repr__(self) -> str:
        """
        The representation of this function
        """
        return "Function(%s)" % self._name

    def evaluate(self) -> None:
        """
        Evaluate this plugin
        """


class DefineImport(TypeDefinitionStatement, Import):
    def __init__(self, name: LocatableString, toname: LocatableString) -> None:
        DefinitionStatement.__init__(self)
        self.name = str(name)
        if "-" in self.name:
            raise CompilerException(
                "%s is not a valid module name: hyphens are not allowed, please use underscores instead." % (self.name)
            )
        self.toname = str(toname)
        if "-" in self.toname:
            raise HyphenException(toname)

    def register_types(self) -> None:
        self.target = self.namespace.get_ns_from_string(self.name)
        if self.target is None:
            raise TypeNotFoundException(self.name, self.namespace)
        self.namespace.import_ns(self.toname, self)

    def evaluate(self) -> None:
        """
        Evaluate this plugin
        """

    def __str__(self) -> str:
        if self.toname == self.name:
            return f"import {self.name}"
        else:
            return f"import {self.name} as {self.toname}"
