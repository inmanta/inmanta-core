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

# pylint: disable-msg=R0902,R0904

from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union  # noqa: F401

from inmanta.ast import (
    CompilerException,
    DuplicateException,
    Locatable,
    Location,
    Named,
    Namespace,
    NotFoundException,
    RuntimeException,
)
from inmanta.ast.blocks import BasicBlock
from inmanta.ast.statements.generator import SubConstructor
from inmanta.ast.type import NamedType, Type
from inmanta.execute.runtime import Instance, QueueScheduler, Resolver, dataflow
from inmanta.execute.util import AnyType

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from inmanta.ast import Namespaced
    from inmanta.ast.attribute import Attribute, RelationAttribute  # noqa: F401
    from inmanta.ast.statements import ExpressionStatement, Statement  # noqa: F401
    from inmanta.ast.statements.define import DefineAttribute, DefineImport  # noqa: F401
    from inmanta.execute.runtime import ExecutionContext, ResultVariable  # noqa: F401

import inmanta.ast.attribute


class Entity(NamedType):
    """
    This class models a defined entity in the domain model of the configuration model.

    Each entity can contain attributes that are either data types or
    relations and each entity can inherit from parent entities.

    :param name: The name of this entity. This name can not be changed
        after this object has been created
    """

    comment: Optional[str]

    def __init__(self, name: str, namespace: Namespace, comment: Optional[str] = None) -> None:
        NamedType.__init__(self)

        self.__name = name  # type: str

        self.__namespace = namespace

        self.parent_entities = []  # type: List[Entity]
        self.child_entities = []  # type: List[Entity]
        self._attributes = {}  # type: Dict[str,Attribute]

        self.implementations = []  # type: List[Implementation]
        self.implements = []  # type: List[Implement]
        self.implements_inherits = False

        # default values
        self.__default_values = {}  # type: Dict[str, DefineAttribute]

        self._index_def = []  # type: List[List[str]]
        self._index = {}  # type: Dict[str,Instance]
        self.index_queue = {}  # type: Dict[str,List[Tuple[ResultVariable, Statement]]]

        self._instance_list = set()  # type: Set[Instance]

        self.comment = comment

        self.normalized = False

    def normalize(self) -> None:
        for attribute in self.__default_values.values():
            if attribute.default is not None:
                default_type: Type = attribute.type.get_type(self.namespace)
                try:
                    default_type.validate(attribute.default.as_constant())
                except RuntimeException as exception:
                    if exception.stmt is None or isinstance(exception.stmt, Type):
                        exception.set_statement(attribute)
                        exception.location = attribute.location
                    raise exception

        # check for duplicate relations in parent entities
        for name, my_attribute in self.get_attributes().items():
            if isinstance(my_attribute, inmanta.ast.attribute.RelationAttribute):
                for parent in self.parent_entities:
                    parent_attr = parent.get_attribute(name)
                    if parent_attr is not None:
                        raise DuplicateException(
                            my_attribute,
                            parent_attr,
                            f"Attribute name {name} is already defined in {parent_attr.entity.name},"
                            " unable to define relationship",
                        )

        # normalize implements but not implementations because they contain subblocks that require full type normalization first
        for i in self.implements:
            i.normalize()

        self.subc = [SubConstructor(self, i) for i in self.get_implements()]
        for sub in self.subc:
            sub.normalize()

    def get_sub_constructor(self) -> List[SubConstructor]:
        return self.subc

    def get_implements(self) -> "List[Implement]":
        if self.implements_inherits:
            return self.implements + [i for p in self.parent_entities for i in p.get_implements()]
        else:
            return self.implements

    def add_default_value(self, name: str, value: "DefineAttribute") -> None:
        """
        Add a default value for an attribute
        """
        self.__default_values[name] = value

    def _get_own_defaults(self) -> "Dict[str, Optional[ExpressionStatement]]":
        return dict((k, v.default) for k, v in self.__default_values.items() if v.default is not None or v.remove_default)

    def get_namespace(self) -> Namespace:
        """
        The namespace of this entity
        """
        return self.__namespace

    namespace = property(get_namespace)

    def __hash__(self) -> "int":
        """
        The hashcode of this entity is defined as the hash of the name
        of this entity
        """
        return hash(self.__name)

    def get_name(self) -> str:
        """
        Return the name of this entity. The name string has been
        internalised for faster dictionary lookups
        """
        return self.__name

    name = property(get_name)

    def get_full_name(self) -> str:
        """
        Get the full name of the entity
        """
        return self.__namespace.get_full_name() + "::" + self.__name

    def get_attributes(self) -> "Dict[str,Attribute]":
        """
        Get a set with all attributes that are defined in this entity
        """
        return self._attributes

    def set_attributes(self, attributes: "Dict[str,Attribute]") -> None:
        """
        Set a set of attributes that are defined in this entities
        """
        self._attributes = attributes

    attributes: "Dict[str,Attribute]" = property(get_attributes, set_attributes, None, None)

    def is_parent(self, entity: "Entity") -> bool:
        """
        Check if the given entity is a parent of this entity. Does not consider an entity its own parent.
        """
        if entity in self.parent_entities:
            return True
        else:
            for parent in self.parent_entities:
                if parent.is_parent(entity):
                    return True
        return False

    def get_all_parent_names(self) -> "List[str]":
        """
        Get a set with all parents of this entity
        """
        parents = [str(x) for x in self.parent_entities]
        for entity in self.parent_entities:
            parents.extend(entity.get_all_parent_names())

        return parents

    def get_all_parent_entities(self) -> "Set[Entity]":
        parents = [x for x in self.parent_entities]
        for entity in self.parent_entities:
            parents.extend(entity.get_all_parent_entities())
        return set(parents)

    def get_all_attribute_names(self) -> "List[str]":
        """
        Return a list of all attribute names, including parents
        """
        names = list(self._attributes.keys())

        for parent in self.parent_entities:
            names.extend(parent.get_all_attribute_names())

        return names

    def add_attribute(self, attribute: "Attribute") -> None:
        """
        Add an attribute to this entity. The attribute should not exist yet.
        """
        if attribute.name not in self._attributes:
            self._attributes[attribute.name] = attribute
        else:
            raise DuplicateException(self._attributes[attribute.name], attribute, "attribute already exists")

    def get_attribute(self, name: str) -> Optional["Attribute"]:
        """
        Get the attribute with the given name
        """
        if name in self._attributes:
            return self._attributes[name]
        else:
            for parent in self.parent_entities:
                attr = parent.get_attribute(name)
                if attr is not None:
                    return attr
        return None

    def has_attribute(self, attribute: str) -> bool:
        """
        Does the attribute already exist in this entity.
        """
        if attribute not in self._attributes:
            for parent in self.parent_entities:
                if parent.has_attribute(attribute):
                    return True

            return False
        else:
            return True

    def get_all_instances(self) -> "List[Instance]":
        """
        Return all instances of this entity
        """
        return list(self._instance_list)

    def add_instance(self, obj: "Instance") -> None:
        """
        Register a new instance
        """
        self._instance_list.add(obj)
        self.add_to_index(obj)

        for parent in self.parent_entities:
            parent.add_instance(obj)

    def get_instance(
        self,
        attributes: Dict[str, object],
        resolver: Resolver,
        queue: QueueScheduler,
        location: Location,
        node: Optional[dataflow.InstanceNodeReference] = None,
    ) -> "Instance":
        """
        Return an instance of the class defined in this entity.
        If the corresponding node is not None, passes it on the instance.
        """
        out = Instance(self, resolver, queue, node)
        out.set_location(location)
        for k, v in attributes.items():
            out.set_attribute(k, v, location)

        self.add_instance(out)
        return out

    def is_subclass(self, cls: "Entity") -> bool:
        """
        Is the given class a subclass of this class. Does not consider entities a subclass of themselves.
        """
        return cls.is_parent(self)

    def validate(self, value: object) -> bool:
        """
        Validate the given value
        """
        if isinstance(value, AnyType):
            return True

        if not isinstance(value, Instance):
            raise RuntimeException(None, "Invalid type for value '%s', should be type %s" % (value, self))

        value_definition = value.type
        if not (value_definition is self or self.is_subclass(value_definition)):
            raise RuntimeException(None, "Invalid class type for %s, should be %s" % (value, self))

        return True

    def add_implementation(self, implement: "Implementation") -> None:
        """
        Register an implementation for this entity
        """
        self.implementations.append(implement)

    def add_implement(self, implement: "Implement") -> None:
        """
        Register an implementation for this entity
        """
        self.implements.append(implement)

    def __repr__(self) -> str:
        """
        The representation of this type
        """
        return "Entity(%s)" % (self.get_full_name())

    def __str__(self) -> str:
        """
        The pretty string of this type
        """
        return self.get_full_name()

    def __eq__(self, other: object) -> bool:
        """
        Override list eq method
        """
        if not isinstance(other, Entity):
            return False

        return self.name == other.name and self.namespace == other.namespace

    def add_index(self, attributes: List[str]) -> None:
        """
        Add an index over the given attributes.
        """
        # duplicate check
        for index in self._index_def:
            if len(index) == len(attributes) and all((a == b for a, b in zip(index, attributes))):
                return

        self._index_def.append(sorted(attributes))
        for child in self.child_entities:
            child.add_index(attributes)

    def get_indices(self) -> List[List[str]]:
        return self._index_def

    def add_to_index(self, instance: Instance) -> None:
        """
        Update indexes based on the instance and the attribute that has
        been set
        """
        attributes = {k: repr(v.get_value()) for (k, v) in instance.slots.items() if v.is_ready()}
        # check if an index entry can be added
        for index_attributes in self.get_indices():
            index_ok = True
            key = []
            for attribute in index_attributes:
                if attribute not in attributes:
                    index_ok = False
                else:
                    key.append("%s=%s" % (attribute, attributes[attribute]))

            if index_ok:
                keys = ", ".join(key)

                if keys in self._index and self._index[keys] is not instance:
                    raise DuplicateException(instance, self._index[keys], "Duplicate key in index. %s" % keys)

                self._index[keys] = instance

                if keys in self.index_queue:
                    for x, stmt in self.index_queue[keys]:
                        x.set_value(instance, stmt.location)
                    self.index_queue.pop(keys)

    def lookup_index(
        self, params: "List[Tuple[str,object]]", stmt: "Statement", target: "Optional[ResultVariable]" = None
    ) -> "Optional[Instance]":
        """
        Search an instance in the index.
        """
        all_attributes: List[str] = [x[0] for x in params]
        attributes: Set[str] = set(())
        for attr in all_attributes:
            if attr in attributes:
                raise RuntimeException(stmt, "Attribute %s provided twice in index lookup" % attr)
            attributes.add(attr)

        found_index = False
        for index_attributes in self.get_indices():
            if set(index_attributes) == attributes:
                found_index = True

        if not found_index:
            raise NotFoundException(
                stmt, self.get_full_name(), "No index defined on %s for this lookup: " % self.get_full_name() + str(params)
            )

        key = ", ".join(["%s=%s" % (k, repr(v)) for (k, v) in sorted(params, key=lambda x: x[0])])

        if target is None:
            if key in self._index:
                return self._index[key]
            else:
                return None
        elif key in self._index:
            target.set_value(self._index[key], stmt.location)
        else:
            if key in self.index_queue:
                self.index_queue[key].append((target, stmt))
            else:
                self.index_queue[key] = [(target, stmt)]
        return None

    def get_default_values(self) -> "Dict[str,ExpressionStatement]":
        """
        Return the dictionary with default values
        """
        values = []  # type: List[Tuple[str,Optional[ExpressionStatement]]]

        # left most parent takes precedence
        for parent in reversed(self.parent_entities):
            values.extend(parent.get_default_values().items())

        # self takes precedence
        values.extend(self._get_own_defaults().items())
        # make dict, remove doubles
        dvalues = dict(values)
        # remove erased defaults
        return {k: v for k, v in dvalues.items() if v is not None}

    def get_default(self, name: str) -> "ExpressionStatement":
        """
        Get a default value for a given name
        """
        defaults = self.get_default_values()
        if name not in defaults:
            raise AttributeError(name)
        return defaults[name]

    def final(self, excns: List[CompilerException]) -> None:
        for key, indices in self.index_queue.items():
            for _, stmt in indices:
                excns.append(
                    NotFoundException(stmt, key, "No match in index on type %s with key %s" % (self.get_full_name(), key))
                )
        for _, attr in self.get_attributes().items():
            attr.final(excns)

    def get_double_defined_exception(self, other: "Namespaced") -> "DuplicateException":
        return DuplicateException(self, other, "Entity %s is already defined" % (self.get_full_name()))

    def get_location(self) -> Location:
        return self.location


# Kept for backwards compatibility. May be dropped from iso7 onwards.
EntityLike = Entity


class Implementation(NamedType):
    """
    A module functions as a grouping of objects. This can be used to create
    high level roles that do not have any arguments, or they can be used
    to create mixin like aspects.
    """

    def __init__(
        self, name: str, stmts: BasicBlock, namespace: Namespace, target_type: str, comment: Optional[str] = None
    ) -> None:
        Named.__init__(self)
        self.name = name
        self.statements = stmts
        self.namespace = namespace
        self.target_type = target_type
        self.comment = comment

    def set_type(self, entity: Entity) -> None:
        self.entity = entity
        entity.add_implementation(self)

    def __repr__(self) -> str:
        return "Implementation(name = %s)" % self.name

    def normalize(self) -> None:
        try:
            self.statements.normalize()
        except CompilerException as e:
            e.set_location(self.location)
            raise

    def get_full_name(self) -> str:
        return self.namespace.get_full_name() + "::" + self.name

    def get_namespace(self) -> Namespace:
        return self.namespace

    def get_double_defined_exception(self, other: "Namespaced") -> "DuplicateException":
        raise DuplicateException(
            self, other, "Implementation %s for type %s is already defined" % (self.get_full_name(), self.target_type)
        )

    def get_location(self) -> Location:
        return self.location


class Implement(Locatable):
    """
    Define an implementation of an entity in functions of implementations
    """

    comment: Optional[str]

    def __init__(self) -> None:
        Locatable.__init__(self)
        self.constraint = None  # type: ExpressionStatement
        self.implementations = []  # type: List[Implementation]
        self.comment = None  # type: str
        self.normalized = False

    def normalize(self) -> None:
        if self.normalized:
            return
        self.normalized = True
        self.constraint.normalize()
