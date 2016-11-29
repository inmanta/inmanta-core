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

# pylint: disable-msg=R0902,R0904

from inmanta.ast.type import Type
from inmanta.ast.blocks import BasicBlock
from inmanta.execute.runtime import Instance, ResultVariable
from inmanta.ast.statements.generator import SubConstructor
from inmanta.ast import RuntimeException, DuplicateException, NotFoundException
from inmanta.util import memoize


class Entity(Type):
    """
        This class models a defined entity in the domain model of the configuration model.

        Each entity can contain attributes that are either data types or
        relations and each entity can inherit from parent entities.

        :param name: The name of this entity. This name can not be changed
            after this object has been created
    """

    def __init__(self, name, namespace="__root__"):
        Type.__init__(self)

        self.__name = name  # : string

        self.__namespace = namespace

        self.parent_entities = set()  # : Entity<>
        self.child_entities = set()
        self._attributes = {}

        self.__cls_type = None
        self.implementations = []
        self.implements = []

        # default values
        self.__default_value = {}

        self.ids = {}

        self._index_def = []
        self._index = {}
        self._instance_attributes = {}
        self.index_queue = {}

        self._instance_list = []

        self.comment = ""

    def normalize(self):
        for d in self.implementations:
            d.normalize()

        for i in self.implements:
            i.normalize()

        self.subc = [SubConstructor(self, i) for i in self.implements]
        for sub in self.subc:
            sub.normalize()

    def get_sub_constructor(self):
        return self.subc

    def get_implements(self):
        return self.implements + [i for p in self.parent_entities for i in p.get_implements()]

    """
        A list of all instances that exist in the configuration model
    """
    instances = []

    def add_default_value(self, name, value):
        """
            Add a default value for an attribute
        """
        if value is None:
            return
        self.__default_value[name] = value

    def get_defaults(self):
        return {}

    def get_default_values(self):
        """
            Return the dictionary with default values
        """
        values = []
        values.extend(self.__default_value.items())

        for parent in self.parent_entities:
            values.extend(parent.get_default_values().items())

        return dict(values)

    def get_namespace(self):
        """
            The namespace of this entity
        """
        return self.__namespace

    namespace = property(get_namespace)

    def __hash__(self):
        """
            The hashcode of this entity is defined as the hash of the name
            of this entity
        """
        return hash(self.__name)

    def get_name(self):
        """
            Return the name of this entity. The name string has been
            internalised for faster dictionary lookups
        """
        return self.__name

    name = property(get_name)

    def get_full_name(self):
        """
            Get the full name of the entity
        """
        return self.__namespace.get_full_name() + "::" + self.__name

    def get_attributes(self):
        """
            Get a set with all attributes that are defined in this entity
        """
        return self._attributes

    def set_attributes(self, attributes):
        """
            Set a set of attributes that are defined in this entities
        """
        self._attributes = attributes

    attributes = property(get_attributes, set_attributes, None, None)

    def is_parent(self, entity):
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

    def get_all_parent_names(self):
        """
            Get a set with all parents of this entity
        """
        parents = [str(x) for x in self.parent_entities]
        for entity in self.parent_entities:
            parents.extend(entity.get_all_parent_names())

        return parents

    def get_all_parent_entities(self):
        parents = [x for x in self.parent_entities]
        for entity in self.parent_entities:
            parents.extend(entity.get_all_parent_entities())
        return set(parents)

    def get_all_attribute_names(self):
        """
            Return a list of all attribute names, including parents
        """
        names = list(self._attributes.keys())

        for parent in self.parent_entities:
            names.extend(parent.get_all_attribute_names())

        return names

    def add_attribute(self, attribute):
        """
            Add an attribute to this entity. The attribute should not exist yet.
        """
        if attribute not in self._attributes:
            self._attributes[attribute.name] = attribute
        else:
            raise Exception("attribute already exists")

    def get_attribute(self, name):
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
    def __get_related(self):
        # down
        all_children = [self]
        done = set()
        while len(all_children) != 0:
            current = all_children.pop()
            if current not in done:
                all_children.extend(current.child_entities)
                done.add(current)
        # up
        parents = set()
        work = list(done)
        while len(work) != 0:
            current = work.pop()
            if current not in parents:
                work.extend(current.parent_entities)
                parents.add(current)

        return parents

    def get_attribute_from_related(self, name):
        """
            Get the attribute with the given name, in both parents and children
            (for type checking)
        """

        for parent in self.__get_related():
            if name in parent._attributes:
                return parent._attributes[name]

        return None

    def has_attribute(self, attribute):
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

    def get_all_instances(self):
        """
            Return all instances of this entity
        """
        return self._instance_list

    def add_instance(self, obj):
        """
            Register a new instance
        """
        self._instance_list.append(obj)
        self.add_to_index(obj)

        for parent in self.parent_entities:
            parent.add_instance(obj)

    def get_instance(self, attributes, resolver, queue, location):
        """
            Return an instance of the class defined in this entity
        """
        out = Instance(self, resolver, queue)
        out.location = location
        for k, v in attributes.items():
            out.set_attribute(k, v, location)

        self.add_instance(out)
        return out

    def is_subclass(self, cls):
        """
            Is the given class a subclass of this class
        """
        return cls.is_parent(self)

    def validate(self, value):
        """
            Validate the given value
        """
        if not isinstance(value, Instance):
            raise RuntimeException(None, "Invalid type for value '%s', should be type %s" % (value, self))

        value_definition = value.type
        if not (value_definition is self or self.is_subclass(value_definition)):
            raise RuntimeException(None, "Invalid class type for %s, should be %s" % (value, self))

        return True

    def add_implementation(self, implement):
        """
            Register an implementation for this entity
        """
        self.implementations.append(implement)

    def add_implement(self, implement):
        """
            Register an implementation for this entity
        """
        self.implements.append(implement)

    def __repr__(self):
        """
            The representation of this type
        """
        return "Entity(%s::%s)" % (self.namespace, self.name)

    def __str__(self):
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

    def __eq__(self, other):
        """
            Override list eq method
        """
        if not isinstance(other, Entity):
            return False

        return self.name == other.name and self.namespace == other.namespace

    def add_index(self, attributes):
        """
            Add an index over the given attributes.
        """
        self._index_def.append(attributes)

    def get_indices(self):
        base = []
        base.extend(self._index_def)
        for parent in self.parent_entities:
            base.extend(parent.get_indices())
        return base

    def add_to_index(self, instance):
        """
            Update indexes based on the instance and the attribute that has
            been set
        """
        attributes = {k: v.get_value() for (k, v) in instance.slots.items() if v.is_ready()}
        # check if an index entry can be added
        for index_attributes in self._index_def:
            index_ok = True
            key = []
            for attribute in index_attributes:
                if attribute not in attributes:
                    index_ok = False
                else:
                    key.append("%s=%s" % (attribute, attributes[attribute]))

            if index_ok:
                key = ", ".join(key)

                if key in self._index and self._index[key] is not instance:
                    raise DuplicateException(instance, self._index[key], "Duplicate key in index. %s" % key)

                self._index[key] = instance

                if key in self.index_queue:
                    for x, stmt in self.index_queue[key]:
                        x.set_value(instance, stmt.location)
                    self.index_queue.pop(key)

    def lookup_index(self, params, stmt, target: ResultVariable=None):
        """
            Search an instance in the index.
        """
        attributes = set([x[0] for x in params])

        found_index = False
        for index_attributes in self._index_def:
            if set(index_attributes) == attributes:
                found_index = True

        if not found_index:
            raise NotFoundException(
                stmt, self.get_full_name(), "No index defined on %s for this lookup: " % self.get_full_name() + str(params))

        key = ", ".join(["%s=%s" % x for x in params])

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

    def get_entity(self):
        """
            Get the entity (follow through defaults if needed)
        """
        return self

    def final(self, excns):
        for key, indices in self.index_queue.items():
            for _, stmt in indices:
                excns.append(NotFoundException(stmt, key,
                                               "No match in index on type %s with key %s" % (self.get_full_name(), key)))


class Implementation(object):
    """
        A module functions as a grouping of objects. This can be used to create
        high level roles that do not have any arguments, or they can be used
        to create mixin like aspects.
    """

    def __init__(self, name, stmts: BasicBlock):
        self.name = name
        self.statements = stmts

    def set_type(self, entity):
        self.entity = entity
        entity.add_implementation(self)

    def __repr__(self):
        return "Implementation(name = %s)" % self.name

    def normalize(self):
        self.statements.normalize()


class Implement(object):
    """
        Define an implementation of an entity in functions of implementations
    """

    def __init__(self):
        self.constraint = None
        self.implementations = []

    def normalize(self):
        self.constraint.normalize()


class Default(Type):
    """
        This class models default values for a constructor.
    """

    def __init__(self, name):
        self.name = name
        self.entity = None
        self._defaults = {}

    def get_defaults(self):
        return self._defaults

    def set_entity(self, entity: Entity):
        self.entity = entity

    def add_default(self, name, value):
        """
            Add a default value
        """
        self._defaults[name] = value

    def get_default(self, name):
        """
            Get a default value for a given name
        """
        if name in self._defaults:
            return self._defaults[name]

        if isinstance(self._entity, Default):
            return self._entity.get_default(name)

        raise AttributeError(name)

    def get_entity(self):
        """
            Get the entity (follow through defaults if needed)
        """
        return self.entity.get_entity()

    def __repr__(self):
        return "Default(%s)" % self.name
