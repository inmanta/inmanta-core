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

import imp
import sys


class Unset(object):
    """
        Instances of this class are used as values for attributes to indicate
        that they have not been set yet.
    """
    def is_none(self):
        """
            Unset is always none
        """
        return True


class Optional(object):
    """
        An instance of this class is raised when a value is optional
    """


class Unknown(object):
    """
        An instance of this class is used to indicate that this value can not be determined yet.

        :param source The source object that can determine the value
    """
    def __init__(self, source):
        self.source = source


def ensure_module(name):
    """
        Ensure that the module with the given name is available
    """
    if name not in sys.modules:
        parts = name.split(".")
        mod = imp.new_module(parts[-1])
        sys.modules[name] = mod


class EntityTypeMeta(type):
    """
        A metaclass that transform an object of EntityType to a subclass that is based on the entity definition
    """
    def __new__(cls, class_name, bases, dct):
        if "__definition__" in dct:
            definition = dct['__definition__']

            class_name = definition.name

            if len(bases) == 0:
                bases = (EntityType,)

            dct["__module__"] = definition.namespace.replace("::", ".")
            ensure_module(dct["__module__"])
            attributes = []

            for name, attribute in definition.attributes.items():
                dct[name] = cls.create_property(attribute)
                attributes.append(name)

            dct["__attributes__"] = attributes
            dct["__entity__"] = definition
            dct["__statement__"] = None

        return type.__new__(cls, class_name, bases, dct)

    @classmethod
    def create_property(mcs, attribute):
        """
            Create a property to access this attribute.
        """
        def get_attribute(self):
            """
                Getter for attribute
            """
            if attribute.name not in self._attributes:
                if hasattr(attribute, "high"):
                    if attribute.high == 1 and attribute.low == 1:
                        return Unset()
                    elif attribute.low == 0 and attribute.high == 1:
                        return Optional()
                    else:
                        return list()

                return Unset()

            value = self._attributes[attribute.name]

            # expand optional arguments
            if hasattr(attribute, "high") and attribute.low == 0 and attribute.high == 1:
                if len(value.value) == 1:
                    return value.value[0]
                else:
                    return Unset()

            return value.value

        def set_attribute(self, value):
            """
                Setter for attribute
            """
            # validate and set the value
            attribute.set_attribute(self, value)

        return property(get_attribute, set_attribute)


class EntityType(object, metaclass=EntityTypeMeta):
    """
        Base class for entities in the configuration specification
    """
    __slots__ = ["_attributes", "_childeren", "__scope__"]

    def __init__(self):
        self._attributes = {}
        self._childeren = []

    def __eq__(self, other):
        """
            Is only equal to other id id() is equal
        """
        return id(self) == id(other)

    def __lt__(self, other):
        """
            Ordering is also conducted based on id()
        """
        return id(self) < id(other)

    __hash__ = object.__hash__

    def add_child(self, child):
        _childeren = self._childeren
        _childeren.append(child)

    def __getattr__(self, name):
        if name == "_attributes" or name == "_childeren":
            return object.__getattr__(self, name)
        else:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        if name == "_attributes" or name == "_childeren" or self.__class__.__definition__.has_attribute(name):
            self.__class__.__definition__.update_index(self, name, value)
            return object.__setattr__(self, name, value)

        elif name == "__statement__" or name == "__scope__":
            return object.__setattr__(self, name, value)

        else:
            raise AttributeError(name)

    def __getstate__(self):
        return self._attributes
