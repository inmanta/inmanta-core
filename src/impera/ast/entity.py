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

# pylint: disable-msg=R0902,R0904

from impera.execute.util import EntityTypeMeta
from impera.ast.type import Type
from impera import stats


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
        self._attributes = {}

        self.__cls_type = None
        self.implementations = []

        # default values
        self.__default_value = {}

        self.ids = {}

        self._index_def = []
        self._index = {}
        self._instance_attributes = {}

        self._instance_list = []

        self.comment = ""

    """
        A list of all instances that exist in the configuration model
    """
    instances = []

    def add_default_value(self, name, value):
        """
            Add a default value for an attribute
        """
        self.__default_value[name] = value

    def get_default_values(self):
        """
            Return the dictionary with default values
        """
        values = []
        values.extend(self.__default_value.items())

        for parent in self.parent_entities:
            values.extend(parent.__default_value.items())

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
        return self.__namespace + "::" + self.__name

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

    def add_instance(self, constructor_id, obj):
        """
            Register a new instance
        """
        self._instance_list.append(obj)
        self.ids[obj] = constructor_id

        for parent in self.parent_entities:
            parent.add_instance(constructor_id, obj)

    def get_instance(self, constructor_id, local_scope):
        """
            Return an instance of the class defined in this entity
        """
        cls_type = self.get_class_type()
        instance = cls_type()
        instance.__scope__ = local_scope

        self.add_instance(constructor_id, instance)

        stats.Stats.get("construct").increment()
        return instance

    def get_class_type(self):
        """
            Get the generated class type
        """
        if self.__cls_type is None:
            parents = []
            # create a tuple of parent entities and check attributes
            attributes = set(self._attributes.keys())
            for parent in self.parent_entities:
                for attr in parent.attributes.keys():
                    if attr not in attributes:
                        attributes.add(attr)

                    else:
                        raise Exception("Hiding attributes with inheritance is not allowed. %s is already defined" % attr)

                cls = parent.get_class_type()
                parents.append(cls)

            # generate the class with voodoo
            self.__cls_type = EntityTypeMeta.__new__(EntityTypeMeta, "", tuple(parents), {"__definition__": self})

        return self.__cls_type

    def is_subclass(self, cls):
        """
            Is the given class a subclass of this class
        """
        return cls.is_parent(self)

    def validate(self, value):
        """
            Validate the given value
        """
        if not hasattr(value.__class__, "__definition__"):
            raise ValueError("Invalid class type %s, should be %s" % (value.__class__.__name__, self))

        value_definition = value.__class__.__definition__
        if not (value_definition is self or self.is_subclass(value_definition)):
            raise ValueError("Invalid class type for %s, should be %s" % (value, self))

        return True

    def add_implementation(self, implement):
        """
            Register an implementation for this entity
        """
        self.implementations.append(implement)

    def __repr__(self):
        """
            The representation of this type
        """
        return "Entity(%s)" % self.name

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

    def validate_indexes(self):
        """
            Check if all index that have been defined are valid. Each attribute
            in each index should exist.
        """
        attributes = set(self.get_all_attribute_names())
        for index_attributes in self._index_def:
            for attribute in index_attributes:
                if attribute not in attributes:
                    raise Exception(("Index with attributes %s defined on entity %s is invalid. Attribute %s " +
                                     "does not exist in this entity.")
                                    % (", ".join(index_attributes), self.__name, attribute))

    def update_index(self, instance, attribute, value):
        """
            Update indexes based on the instance and the attribute that has
            been set
        """
        if instance not in self._instance_attributes:
            self._instance_attributes[instance] = {}

        self._instance_attributes[instance][attribute] = value

        # check if an index entry can be added
        attributes = self._instance_attributes[instance].keys()
        for index_attributes in self._index_def:
            index_ok = True
            key = []
            for attribute in index_attributes:
                if attribute not in attributes:
                    index_ok = False
                else:
                    attr_value = self._instance_attributes[instance][attribute].value
                    key.append("%s=%s" % (attribute, attr_value))

            if index_ok:
                key = ", ".join(key)

                if key in self._index and self._index[key] is not instance:
                    raise Exception("Duplicate key in index. %s" % key)

                self._index[key] = instance

    def lookup_index(self, params):
        """
            Search an instance in the index.
        """
        attributes = set([x[0] for x in params])

        found_index = False
        for index_attributes in self._index_def:
            if set(index_attributes) == attributes:
                found_index = True

        if not found_index:
            raise Exception("No index defined for this lookup: " + str(params))

        key = ", ".join(["%s=%s" % x for x in params])

        if key in self._index:
            return self._index[key]

        return None


class Implementation(object):
    """
        A module functions as a grouping of objects. This can be used to create
        high level roles that do not have any arguments, or they can be used
        to create mixin like aspects.
    """
    def __init__(self, name, entity=None):
        self.statements = []
        self.name = name
        self.entity = entity

    def __repr__(self):
        return "Implementation(name = %s)" % self.name


class Implement(object):
    """
        Define an implementation of an entity in functions of implementations
    """
    def __init__(self):
        self.constraint = None
        self.implementations = []


class Default(object):
    """
        This class models default values for a constructor.
    """
    def __init__(self, name, entity):
        self.name = name
        self._entity = entity
        self._defaults = {}

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
        if isinstance(self._entity, Default):
            return self._entity.get_entity()

        return self._entity

    def __repr__(self):
        return "Default(%s)" % self.name
