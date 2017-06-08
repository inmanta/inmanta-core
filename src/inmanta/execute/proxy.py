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

from copy import copy
from collections import Mapping

from inmanta.execute.util import Unknown, NoneValue
from inmanta.ast import RuntimeException


class UnsetException(RuntimeException):
    """
        This exception is thrown when an attribute is read that was not yet
        available.
    """

    def __init__(self, msg, instance=None, attribute=None):
        RuntimeException.__init__(self, None, msg)
        self.instance = instance
        self.attribute = attribute
        self.msg = msg

    def get_result_variable(self):
        return self.instance


class UnknownException(Exception):
    """
        This exception is thrown when code tries to access a value that is
        unknown and cannot be determined during this evaluation. The code
        receiving this exception is responsible for invalidating any results
        depending on this value by return an instance of Unknown as well.
    """

    def __init__(self, unknown):
        self.unknown = unknown


class DynamicProxy(object):
    """
        This class wraps an object and makes sure that a model is never modified
        by native code.
    """

    def __init__(self, instance):
        object.__setattr__(self, "__instance", instance)

    def _get_instance(self):
        return object.__getattribute__(self, "__instance")

    @classmethod
    def unwrap(cls, item):
        if isinstance(item, DynamicProxy):
            return item._get_instance()

        if isinstance(item, list):
            return [cls.unwrap(x) for x in item]

        return item

    @classmethod
    def return_value(cls, value):
        if value is None:
            return None

        if isinstance(value, NoneValue):
            return None

        if isinstance(value, Unknown):
            raise UnknownException(value)

        if isinstance(value, (str, tuple, int, float, bool)):
            return copy(value)

        if isinstance(value, DynamicProxy):
            return value

        if isinstance(value, dict):
            return DictProxy(value)

        if hasattr(value, "__len__"):
            return SequenceProxy(value)

        if hasattr(value, "__call__"):
            return CallProxy(value)

        return DynamicProxy(value)

    def __getattr__(self, attribute):
        instance = self._get_instance()
        value = instance.get_attribute(attribute).get_value()

        return DynamicProxy.return_value(value)

    def __setattr__(self, attribute, value):
        raise Exception("Readonly object")

    def _type(self):
        """
            Return the type of the proxied instance
        """
        return self._get_instance().type

    def is_unknown(self):
        """
            Return true if this value is unknown and cannot be determined
            during this compilation run
        """
        if isinstance(self._get_instance(), Unknown):
            return True
        return False

    def __hash__(self):
        return hash(self._get_instance())

    def __eq__(self, other):
        if hasattr(other, "_get_instance"):
            other = other._get_instance()

        return self._get_instance() == other

    def __lt__(self, other):
        if hasattr(other, "_get_instance"):
            other = other._get_instance()

        return self._get_instance() < other

    def __repr__(self):
        return "@%s" % repr(self._get_instance())


class SequenceProxy(DynamicProxy):

    def __init__(self, iterator):
        DynamicProxy.__init__(self, iterator)

    def __getitem__(self, key):
        instance = self._get_instance()
        if isinstance(key, str):
            raise RuntimeException(self, "can not get a attribute %s, %s is a list" % (key, self._get_instance()))

        return DynamicProxy.return_value(instance[key])

    def __len__(self):
        return len(self._get_instance())

    def __iter__(self):
        instance = self._get_instance()

        return IteratorProxy(instance.__iter__())


class DictProxy(DynamicProxy, Mapping):

    def __init__(self, mydict):
        DynamicProxy.__init__(self, mydict)

    def __getitem__(self, key):
        instance = self._get_instance()
        if not isinstance(key, str):
            raise RuntimeException(self, "Expected string key, but got %s, %s is a dict" % (key, self._get_instance()))

        return DynamicProxy.return_value(instance[key])

    def __len__(self):
        return len(self._get_instance())

    def __iter__(self):
        instance = self._get_instance()

        return IteratorProxy(instance.__iter__())


class CallProxy(DynamicProxy):
    """
        Proxy a value that implements a __call__ function
    """

    def __init__(self, instance):
        DynamicProxy.__init__(self, instance)

    def __call__(self, *args, **kwargs):
        instance = self._get_instance()

        return instance(*args, **kwargs)


class IteratorProxy(DynamicProxy):
    """
        Proxy an iterator call
    """

    def __init__(self, iterator):
        DynamicProxy.__init__(self, iterator)

    def __iter__(self):
        return self

    def __next__(self):
        i = self._get_instance()
        return DynamicProxy.return_value(next(i))
