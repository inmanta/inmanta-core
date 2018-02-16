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

from inmanta.ast.type import Type, NamedType
from inmanta.ast.blocks import BasicBlock
from inmanta.execute.runtime import Resolver, QueueScheduler
from inmanta.ast.statements.generator import SubConstructor
from inmanta.ast import RuntimeException, DuplicateException, NotFoundException, Namespace, Location, \
    Named, Locatable
from inmanta.util import memoize
from inmanta.execute.runtime import Instance
from inmanta.execute.util import AnyType

from typing import Any, Dict, Sequence, List, Optional, Union, Tuple, Set  # noqa: F401

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from inmanta.execute.runtime import ExecutionContext, ResultVariable  # noqa: F401
    from inmanta.ast.statements import Statement, ExpressionStatement  # noqa: F401
    from inmanta.ast.statements.define import DefineImport  # noqa: F401
    from inmanta.ast.attribute import Attribute  # noqa: F401


class Entity(NamedType):
    """
        This class models a defined entity in the domain model of the configuration model.

        Each entity can contain attributes that are either data types or
        relations and each entity can inherit from parent entities.

        :param name: The name of this entity. This name can not be changed
            after this object has been created
    """

    def __init__(self, name: str, namespace: Namespace) -> None:
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
        self.__default_value = {}  # type: Dict[str,object]

        self._index_def = []  # type: List[List[str]]
        self._index = {}  # type: Dict[str,Instance]
        self.index_queue = {}  # type: Dict[str,List[Tuple[ResultVariable, Statement]]]

        self._instance_list = set()  # type: Set[Instance]

        self.comment = ""

        self.normalized = False

    def normalize(self) -> None:
        for d in self.implementations:
            d.normalize()

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

    def add_default_value(self, name: str, value: object) -> None:
        """
            Add a default value for an attribute
        """
        self.__default_value[name] = value

    def get_defaults(self) -> "Dict[str,ExpressionStatement]":
        return self.get_default_values()

    def get_default_values(self) -> "Dict[str,ExpressionStatement]":
        """
            Return the dictionary with default values
        """
        values = []  # type: List[Tuple[str,ExpressionStatement]]

        # left most parent takes precedence
        for parent in reversed(self.parent_entities):
            values.extend(parent.get_default_values().items())

        # self takes precedence
        values.extend(self.__default_value.items())
        # make dict, remove doubles
        dvalues = dict(values)
        # remove erased defaults
        return {k: v for k, v in dvalues.items() if v is not None}

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

    attributes = property(get_attributes, set_attributes, None, None)

    def is_parent(self, entity: "Entity") -> bool:
        """
            Check if the given entity is a parent of this entity
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
        if attribute not in self._attributes:
            self._attributes[attribute.name] = attribute
        else:
            raise Exception("attribute already exists")

    def get_attribute(self, name: str) -> "Attribute":
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

    @memoize
    def __get_related(self) -> "Set[Entity]":
        # down
        all_children = [self]  # type: List[Entity]
        done = set()  # type: Set[Entity]
        while len(all_children) != 0:
            current = all_children.pop()
            if current not in done:
                all_children.extend(current.child_entities)
                done.add(current)
        # up
        parents = set()  # type: Set[Entity]
        work = list(done)
        while len(work) != 0:
            current = work.pop()
            if current not in parents:
                work.extend(current.parent_entities)
                parents.add(current)

        return parents

    def get_attribute_from_related(self, name: str) -> "Attribute":
        """
            Get the attribute with the given name, in both parents and children
            (for type checking)
        """

        for parent in self.__get_related():
            if name in parent._attributes:
                return parent._attributes[name]

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

    def get_instance(self,
                     attributes: Dict[str, object],
                     resolver: Resolver,
                     queue: QueueScheduler,
                     location: Location) -> "Instance":
        """
            Return an instance of the class defined in this entity
        """
        out = Instance(self, resolver, queue)
        out.location = location
        for k, v in attributes.items():
            out.set_attribute(k, v, location)

        self.add_instance(out)
        return out

    def is_subclass(self, cls: "Entity") -> bool:
        """
            Is the given class a subclass of this class
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
        return "Entity(%s::%s)" % (self.namespace, self.name)

    def __str__(self) -> str:
        """
            The pretty string of this type
        """
        return "%s::%s" % (self.namespace, self.name)

    @classmethod
    def cast(cls, value):
        """
            Cast a value
        """
        return value

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

    def lookup_index(self,
                     params: "List[str,object]",
                     stmt: "Statement",
                     target: "Optional[ResultVariable]"=None) -> "Optional[Instance]":
        """
            Search an instance in the index.
        """
        attributes = set([x[0] for x in params])

        found_index = False
        for index_attributes in self.get_indices():
            if set(index_attributes) == attributes:
                found_index = True

        if not found_index:
            raise NotFoundException(
                stmt, self.get_full_name(), "No index defined on %s for this lookup: " % self.get_full_name() + str(params))

        key = ", ".join(["%s=%s" % (k, repr(v)) for (k, v) in sorted(params, key=lambda x:x[0])])

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

    def get_entity(self) -> "Entity":
        """
            Get the entity (follow through defaults if needed)
        """
        return self

    def final(self, excns: List[Exception]) -> None:
        for key, indices in self.index_queue.items():
            for _, stmt in indices:
                excns.append(NotFoundException(stmt, key,
                                               "No match in index on type %s with key %s" % (self.get_full_name(), key)))
        for _, attr in self.get_attributes().items():
            attr.final(excns)

    def get_double_defined_exception(self, other: "Namespaced") -> "DuplicateException":
        return DuplicateException(
            self, other, "Entity %s is already defined" % (self.get_full_name()))

    def get_location(self) -> Location:
        return self.location


class Implementation(Named):
    """
        A module functions as a grouping of objects. This can be used to create
        high level roles that do not have any arguments, or they can be used
        to create mixin like aspects.
    """

    def __init__(self,
                 name: str,
                 stmts: BasicBlock,
                 namespace: Namespace,
                 target_type: str,
                 comment: Optional[str]=None) -> None:
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
        self.statements.normalize()

    def get_full_name(self) -> str:
        return self.namespace.get_full_name() + "::" + self.name

    def get_namespace(self) -> Namespace:
        return self.namespace

    def get_double_defined_exception(self, other: "Namespaced") -> "DuplicateException":
        raise DuplicateException(self, other, "Implementation %s for type %s is already defined" %
                                 (self.get_full_name(), self.target_type))

    def get_location(self) -> Location:
        return self.location


class Implement(Locatable):
    """
        Define an implementation of an entity in functions of implementations
    """

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


class Default(Type):
    """
        This class models default values for a constructor.
    """

    def __init__(self, name: str) -> None:
        Type.__init__(self)
        self.name = name
        self.entity = None  # type: Entity
        self._defaults = {}  # type: Dict[str,ExpressionStatement]
        self.comment = None  # type: str

    def get_defaults(self) -> "Dict[str, ExpressionStatement]":
        return self._defaults

    def set_entity(self, entity: Entity) -> None:
        self.entity = entity

    def add_default(self, name: str, value: "ExpressionStatement") -> None:
        """
            Add a default value
        """
        self._defaults[name] = value

    def get_default(self, name: str) -> "ExpressionStatement":
        """
            Get a default value for a given name
        """
        if name in self._defaults:
            return self._defaults[name]

        if isinstance(self._entity, Default):
            return self._entity.get_default(name)

        raise AttributeError(name)

    def get_entity(self) -> Entity:
        """
            Get the entity (follow through defaults if needed)
        """
        return self.entity.get_entity()

    def __repr__(self) -> str:
        return "Default(%s)" % self.name
