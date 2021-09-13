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

from collections.abc import Mapping
from copy import copy
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from inmanta.ast import NotFoundException, RuntimeException
from inmanta.execute.util import NoneValue, Unknown
from inmanta.stable_api import stable_api
from inmanta.types import PrimitiveTypes
from inmanta.util import JSONSerializable

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from inmanta.ast.attribute import Attribute
    from inmanta.ast.entity import Entity
    from inmanta.execute.runtime import Instance


class UnsetException(RuntimeException):
    """
    This exception is thrown when an attribute is accessed that was not yet
    available (i.e. it has not been frozen yet).
    """

    def __init__(self, msg: str, instance: Optional["Instance"] = None, attribute: Optional["Attribute"] = None) -> None:
        RuntimeException.__init__(self, None, msg)
        self.instance: Optional["Instance"] = instance
        self.attribute: Optional["Attribute"] = attribute
        self.msg = msg

    def get_result_variable(self) -> Optional["Instance"]:
        return self.instance


class UnknownException(Exception):
    """
    This exception is thrown when code tries to access a value that is
    unknown and cannot be determined during this evaluation. The code
    receiving this exception is responsible for invalidating any results
    depending on this value by return an instance of Unknown as well.
    """

    def __init__(self, unknown: Unknown):
        super().__init__()
        self.unknown = unknown


class AttributeNotFound(NotFoundException, AttributeError):
    """
    Exception used for backwards compatibility with try-except blocks around some_proxy.some_attr.
    This previously raised `NotFoundException` which is currently deprecated in this context.
    Its new behavior is to raise an AttributeError for compatibility with Python's builtin `hasattr`.
    """

    pass


@stable_api
class DynamicProxy:
    """
    This class wraps an object and makes sure that a model is never modified
    by native code.
    """

    def __init__(self, instance: "Instance") -> None:
        object.__setattr__(self, "__instance", instance)

    def _get_instance(self) -> "Instance":
        return object.__getattribute__(self, "__instance")

    @classmethod
    def unwrap(cls, item: object) -> object:
        """
        Converts a value from the plugin domain to the internal domain.
        """
        if item is None:
            return NoneValue()

        if isinstance(item, DynamicProxy):
            return item._get_instance()

        if isinstance(item, list):
            return [cls.unwrap(x) for x in item]

        if isinstance(item, dict):

            def recurse_dict_item(key_value: Tuple[object, object]) -> Tuple[object, object]:
                (key, value) = key_value
                if not isinstance(key, str):
                    raise RuntimeException(
                        None, "dict keys should be strings, got %s of type %s with dict value %s" % (key, type(key), value)
                    )
                return (key, cls.unwrap(value))

            return dict(map(recurse_dict_item, item.items()))

        return item

    @classmethod
    def return_value(cls, value: object) -> Union[None, str, Tuple[object, ...], int, float, bool, "DynamicProxy"]:
        """
        Converts a value from the internal domain to the plugin domain.
        """
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

    def __getattr__(self, attribute: str):
        instance = self._get_instance()

        try:
            value = instance.get_attribute(attribute).get_value()
        except NotFoundException as e:
            # allow for hasattr(proxy, "some_attr")
            raise AttributeNotFound(e.stmt, e.name)

        return DynamicProxy.return_value(value)

    def __setattr__(self, attribute: str, value: object) -> None:
        raise Exception("Readonly object")

    def _type(self) -> "Entity":
        """
        Return the type of the proxied instance
        """
        return self._get_instance().type

    def is_unknown(self) -> bool:
        """
        Return true if this value is unknown and cannot be determined
        during this compilation run
        """
        if isinstance(self._get_instance(), Unknown):
            return True
        return False

    def __hash__(self) -> int:
        return hash(self._get_instance())

    def __eq__(self, other: object) -> bool:
        if hasattr(other, "_get_instance"):
            other = other._get_instance()

        return self._get_instance() == other

    def __lt__(self, other: object) -> bool:
        if hasattr(other, "_get_instance"):
            other = other._get_instance()

        return self._get_instance() < other

    def __repr__(self) -> str:
        return "@%s" % repr(self._get_instance())


class SequenceProxy(DynamicProxy, JSONSerializable):
    def __init__(self, iterator: Sequence) -> None:
        DynamicProxy.__init__(self, iterator)

    def __getitem__(self, key: str) -> object:
        instance = self._get_instance()
        if isinstance(key, str):
            raise RuntimeException(self, "can not get a attribute %s, %s is a list" % (key, self._get_instance()))

        return DynamicProxy.return_value(instance[key])

    def __len__(self) -> int:
        return len(self._get_instance())

    def __iter__(self) -> Iterable:
        instance = self._get_instance()

        return IteratorProxy(instance.__iter__())

    def json_serialization_step(self) -> List[PrimitiveTypes]:
        # Ensure proper unwrapping by using __getitem__
        return [i for i in self]


class DictProxy(DynamicProxy, Mapping, JSONSerializable):
    def __init__(self, mydict: Dict[object, object]) -> None:
        DynamicProxy.__init__(self, mydict)

    def __getitem__(self, key):
        instance = self._get_instance()
        if not isinstance(key, str):
            raise RuntimeException(self, "Expected string key, but got %s, %s is a dict" % (key, self._get_instance()))

        return DynamicProxy.return_value(instance[key])

    def __len__(self) -> int:
        return len(self._get_instance())

    def __iter__(self):
        instance = self._get_instance()

        return IteratorProxy(instance.__iter__())

    def json_serialization_step(self) -> Dict[str, PrimitiveTypes]:
        # Ensure proper unwrapping by using __getitem__
        return {k: v for k, v in self.items()}


class CallProxy(DynamicProxy):
    """
    Proxy a value that implements a __call__ function
    """

    def __init__(self, instance: Callable[..., object]) -> None:
        DynamicProxy.__init__(self, instance)

    def __call__(self, *args, **kwargs):
        instance = self._get_instance()

        return instance(*args, **kwargs)


class IteratorProxy(DynamicProxy):
    """
    Proxy an iterator call
    """

    def __init__(self, iterator: Iterable[object]) -> None:
        DynamicProxy.__init__(self, iterator)

    def __iter__(self):
        return self

    def __next__(self):
        i = self._get_instance()
        return DynamicProxy.return_value(next(i))
