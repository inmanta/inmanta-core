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

import logging


from impera.execute import NotFoundException
from impera.execute.util import Unset
from setuptools.ssl_support import is_available
from impera.execute.runtime import ResultVariable, WaitUnit, ExecutionContext, ExecutionUnit
from fileinput import filename

LOGGER = logging.getLogger(__name__)


class Reference(object):
    """
        This class represents a reference to a value
    """

    def __init__(self, name, namespace=None):
        self.line = 0
        self.filename = ""

        self.name = name
        if namespace is None:
            self.namespace = []
        else:
            if not isinstance(namespace, list):
                # should add namespace as list here
                raise Exception()
            self.namespace = namespace

        fullName = ""
        if len(self.namespace) > 0:
            fullName = "::".join(self.namespace)
            fullName = fullName + "::"

        self.full_name = fullName + name

    def normalize(self, resolver):
        pass

    def requires(self):
        return [self.full_name]

    def requires_emit(self, resolver, queue):
        # FIXME: may be done more efficient?
        out = {self.full_name: resolver.lookup(self.full_name)}
        return out

    def execute(self, requires, resolver, queue):
        return requires[self.full_name]

    def is_available(self, scope):
        """
            Is the value this reference points to available in the given scope
        """
        try:
            var = scope.resolve_reference(self)
            return var.is_available(scope)
        except NotFoundException:
            return False

    def __repr__(self):
        name = ""
        if len(self.namespace) > 0:
            name = "::".join(self.namespace)
            name = name + "::"

        return name + self.name

    def get_containing_namespace(self,):
        return self.onamespace


class Variable(object):
    """
        A variable in the configuration. It represents a value. Comparison and
        mathematical operations are forwarded to the value
    """

    def __init__(self, value):
        self.line = 0
        self.filename = ""

        self.__value = value
        self._version = 1

    def copy_location(self, statement):
        """
            Copy the location of this statement in the given statement
        """
        statement.filename = self.filename
        statement.line = self.line

    def can_compare(self):
        """
            A variable can always be compared to other variables because its
            value is available.
        """
        return True

    def get_version(self):
        """
            Get the version of the variable. Always returns a value > 0 if the value is available.
        """
        return self._version

    def __repr__(self):
        return repr(self.value)

    def validate(self, function):
        """
            Validate this variable using the given function, Validation is
            performed by the variable to support validation in lazy variables.
        """
        if function is not None:
            function(self.get_value())

    def cast(self, function):
        """
            Cast the value in this variable with the given function. Casting is performed by the
            variable to support validation in lazy variables.
        """
        if function is not None:
            self.value = function(self.get_value())

    def get_value(self):
        """
            Get the value of this variable
        """
        return self.__value

    def set_value(self, value):
        """
            Set the value of this variable. If the variable is set it becomes
            readonly.
        """
        self.__value = value

    value = property(get_value, set_value)

    def has_value(self):
        """
            Check if this variable has a value
        """
        return self.__value is not None

    def get_name(self):
        """
            The name of the variable, this will be the internal python name
        """
        return repr(self)

    name = property(get_name)

    def get_full_name(self):
        """
            This full name of this variable
        """
        return self.name

    def is_available(self, scope):
        """
            Is the value of this variable available?
        """
        return True

    def __eq__(self, other):
        if other.__class__ != Variable:  # isinstance is much slower
            return False

        return self.value == other.value

    __hash__ = object.__hash__

    def compare_key(self):
        """
            Return a value that is used to compare objects of this type. This
            key is used to use hashing to narrow down that list of exact
            compares.
        """
        return self.value

    def get_value_type(self):
        """
            Return the type of the value
        """
        # can only be called when the value is available
        if isinstance(self.__value, EntityType):
            return self.__value.__definition__.get_attribute(self.attribute).type

        return self.__value.__class__

    type = property(get_value_type)


class AttributeRef(object):

    def __init__(self, target, instance, attribute):
        self.attribute = attribute
        self.target = target
        self.instance = instance

    def resume(self, requires, resolver, queue_scheduler):
        obj = self.instance.execute(requires, resolver, queue_scheduler).get_value()
        if isinstance(obj, list):
            print("KAK")
        attr = obj.get_attribute(self.attribute)
        self.attr = attr

        if attr.is_ready():
            # go ahead
            self.target.set_value(attr.get_value())
        elif attr.is_delayed():
            # wait on delay queue
            ExecutionUnit(queue_scheduler, resolver, self.target, {"x": attr}, self)
        else:
            # wait on execute queue
            ExecutionUnit(queue_scheduler, resolver, self.target, {"x": attr}, self)

    def execute(self, requires, resolver, queue):
        return self.attr.get_value()


class AttributeVariable(Variable):
    """
        This variable refers to an attribute. This is mostly used to refer to
        attributes of a class or class instance.
    """

    def __init__(self, instance, attribute):
        Variable.__init__(self, None)
        self.attribute = attribute

        # a reference to the instance
        self.instance = instance

        # if the reference resolves, this attribute contains the instance
        self._instance_value = None

    def normalize(self, resolver):
        self.instance.normalize(resolver)

    def requires(self):
        return self.instance.requires()

    def requires_emit(self, resolver, queue):
        # The tricky one!
        # make wait chain on right queue
        temp = ResultVariable()
        temp.set_provider(self)
        resumer = AttributeRef(temp, self.instance, self.attribute)
        self.copy_location(resumer)
        WaitUnit(queue, resolver, self.instance.requires_emit(resolver, queue), resumer)
        return {self: temp}

    def execute(self, requires, resolver, queue):
        return requires[self]

    def get_value_type(self):
        """
            Return the type of the value
        """
        # can only be called when the value is available
        return self._instance_value.value.__definition__.get_attribute(self.attribute).type

    type = property(get_value_type)

    def can_compare(self):
        """
            An attribute variable can be compared when the instance is available.
        """
        return self.get_version() > 0

    def get_version(self):
        """
            Return the version of the instance variable
        """
        return self.instance.get_version()

    def get_full_name(self):
        """
            Get the full name of the attribute
        """
        return repr(self.instance) + "." + self.attribute

    def _get_instance(self, scope):
        """
            Get the instance
        """
        if isinstance(self.instance, Variable):
            return self.instance
        elif isinstance(self.instance, Reference):
            try:
                return scope.resolve_reference(self.instance)
            except NotFoundException:
                return None
        else:
            raise Exception("Unable to get the value of the instance")

    def get_value(self):
        """
            Get the value of the attribute that this variables refers to
        """
        if self._instance_value is None:
            raise Exception("First check if value is available")

        value = getattr(self._instance_value.value, self.attribute)
        return value

    value = property(get_value)

    def __repr__(self):
        return self.get_full_name()

    def is_available(self, scope):
        """
            Is the value of this variable available?
        """
        self._instance_value = self._get_instance(scope)

        if self._instance_value is None:
            return False

        self.instance = self._instance_value
        if not self.instance.is_available(scope):
            return False

        value = self.get_value()
        if value.__class__ == Unset:  # or value.__class__ == Optional:
            return False
        return True

    def __eq__(self, other):
        if other.__class__ != AttributeVariable:  # isinstance is much slower
            return False

        if self.attribute != other.attribute:
            return False

        # return self.instance.value == other.instance.value
        if self.instance.get_version() > 0 and other.instance.get_version() > 0:
            # try to get the values
            return self.instance.value == other.instance.value
        else:
            # best effort
            return self.instance == other.instance

    def compare_key(self):
        """
            @see Variable#compare_key
        """
        # return (self.instance, self.attribute)
        return self.attribute

    __instance_cache = {}

    __hash__ = Variable.__hash__

    @classmethod
    def create(cls, instance, attribute):
        """
            Returns an attribute variable. If it already exists this instance
            is returned. Otherwise an other instance is returned
        """
        key = (instance, attribute)
        if key in cls.__instance_cache:
            return cls.__instance_cache[key]

        obj = cls(instance, attribute)
        cls.__instance_cache[key] = obj

        return obj


class LazyVariable(Variable):
    """
        The value of this variable is available as a Python functions that needs to be evaluated. The
        purpose of this type of variable is waiting as long as possible to evaluate the statement which
        is encapsulated in the Python function.
    """

    def __init__(self, value_generator, value_type):
        Variable.__init__(self, None)

        self._value_generator = value_generator
        self._type = value_type

    def get_value(self):
        """
            Get the value and if it does not exist yet, execute the generator.
        """
        if not self.has_value():
            self.set_value(self._value_generator())

        return Variable.get_value(self)

    value = property(get_value, None)

    def get_value_type(self):
        """
            Return the type of the value
        """
        return self._type

    type = property(get_value_type)
