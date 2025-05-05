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

import dataclasses
from collections.abc import Iterable, Mapping, Sequence
from copy import copy
from dataclasses import is_dataclass
from typing import TYPE_CHECKING, Callable, Union

# Keep UnsetException, UnknownException and AttributeNotFound in place for backward compat with <iso8
from inmanta.ast import AttributeNotFound as AttributeNotFound
from inmanta.ast import Location, NotFoundException, RuntimeException
from inmanta.ast import UnknownException as UnknownException
from inmanta.ast import UnsetException as UnsetException  # noqa F401
from inmanta.execute.util import NoneValue, Unknown
from inmanta.references import Reference, UnexpectedReferenceException
from inmanta.stable_api import stable_api
from inmanta.types import PrimitiveTypes
from inmanta.util import JSONSerializable

if TYPE_CHECKING:
    from inmanta.ast.entity import Entity
    from inmanta.ast.type import Type as inm_Type
    from inmanta.execute.runtime import Instance, QueueScheduler, Resolver

    TypeResolver = Callable[[type[object]], inm_Type]
else:
    TypeResolver = object


@dataclasses.dataclass(frozen=True, slots=True)
class DynamicUnwrapContext:
    """A set of context information that allows dynamic proxy unwrapping to construct instances"""

    resolver: "Resolver"
    queue: "QueueScheduler"
    location: Location
    # this last one is purely there to prevent import loops
    type_resolver: TypeResolver


# this is here to avoid import loops
# It would be nicer to have it as class method on entity, but that would cause proxy to import the entire compiler
def get_inmanta_type_for_dataclass(for_type: type[object]) -> "Entity | None":
    if hasattr(for_type, "_paired_inmanta_entity"):
        return for_type._paired_inmanta_entity
    return None


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
    def unwrap(cls, item: object, *, dynamic_context: DynamicUnwrapContext | None = None) -> object:
        """
        Converts a value from the plugin domain to the internal domain.

        :param dynamic_context: a type resolver context. When passed in, dataclasses are converted as well.
        """
        if item is None:
            return NoneValue()

        if isinstance(item, DynamicProxy):
            return item._get_instance()

        if isinstance(item, list):
            return [cls.unwrap(x, dynamic_context=dynamic_context) for x in item]

        if isinstance(item, dict):

            def recurse_dict_item(key_value: tuple[object, object]) -> tuple[object, object]:
                (key, value) = key_value
                if not isinstance(key, str):
                    raise RuntimeException(
                        None, f"dict keys should be strings, got {key} of type {type(key)} with dict value {value}"
                    )
                return (key, cls.unwrap(value, dynamic_context=dynamic_context))

            return dict(map(recurse_dict_item, item.items()))

        if isinstance(item, Reference):
            ref_type = item.get_reference_type()
            if ref_type is None:
                raise RuntimeException(
                    None,
                    f"Could not determine the reference type of {item}, "
                    f"make sure the reference extends Reference[concrete_type] or override `get_reference_type`",
                )

            if dataclasses.is_dataclass(ref_type):
                if dynamic_context is None:
                    raise RuntimeException(
                        None,
                        f"{item} is a dataclass of type {ref_type}. "
                        "It can only be converted to an inmanta entity at the plugin boundary",
                    )
                dataclass_ref_type = dynamic_context.type_resolver(ref_type)
                # Can not be typed correctly due to import loops
                return dataclass_ref_type.from_python(
                    item, dynamic_context.resolver, dynamic_context.queue, dynamic_context.location
                )
            else:
                if item._model_type is None:
                    if dynamic_context is None:
                        raise RuntimeException(
                            None,
                            f"{item} is a reference of type {ref_type}. "
                            "It can only be typed at the plugin boundary or "
                            "by explicitly setting `_model_type` to the relevant inmanta type",
                        )
                    reference_type = dynamic_context.type_resolver(ref_type)
                    item._model_type = reference_type
                return item

        if is_dataclass(item) and not isinstance(item, type):
            # dataclass instance
            dataclass_type = get_inmanta_type_for_dataclass(type(item))
            if dataclass_type is not None:
                if dynamic_context is not None:
                    return dataclass_type.from_python(
                        item, dynamic_context.resolver, dynamic_context.queue, dynamic_context.location
                    )
                else:
                    raise RuntimeException(
                        None,
                        f"{item} is a dataclass of type {dataclass_type.get_full_name()}. "
                        "It can only be converted to an inmanta entity at the plugin boundary",
                    )

        return item

    @classmethod
    def return_value(
        cls,
        value: object,
    ) -> Union[None, str, tuple[object, ...], int, float, bool, "DynamicProxy"]:
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

        if isinstance(value, (Reference, DynamicProxy)):
            return value

        # TODO: test cases
        #   - plain plugin that gets a reference: allowed iff declared (or any)
        #   - plugin that gets a reference in list/dict: allowed iff declared
        #   - plugin that gets an entity with a reference attribute. Allowed but error on attr access unless allow_references()
        #   - plugin that gets a dataclass with reference attributes. Allowed if declared
        #       => How about a reference to a dataclass? Translated internally as dataclass of references, but that violates
        #           the signature
        #   - plugin that iterates over list with a reference in there

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

        # Non-dataclass entities can not be explicit about reference support.
        # The Python domain is a black box. We don't want to transparently pass unexpected values in there.
        # TODO: allow_references() name
        # => don't allow references in attributes. Can be explicitly allowed via allow_references() wrapper
        if isinstance(value, Reference):
            # TODO: message
            # TODO: string format accepts reference. Should also raise this exception
            raise UnexpectedReferenceException(
                (
                    "Encountered reference attribute in instance. Plugins are only allowed to access reference attributes"
                    " when declared explicitly. Either use a dataclass entity with attributes annotated with declared reference"
                    " attributes (e.g. `int | Reference[int]`), or explicitly allow references on attribute access with the"
                    # TODO: name
                    " `inmanta.plugins.allow_reference_attributes()` wrapper."
                    f" ({attribute}={value} on instance {self._get_instance()})"
                    #f"(self._get_instance()
                ),
                reference=value,
            )

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


class WithReferenceAttributes(DynamicProxy):
    # TODO: docstring

    def __init__(self, delegate: DynamicProxy) -> None:
        object.__setattr__(self, "__delegate", delegate)

    def _get_delegate(self) -> "Instance":
        return object.__getattribute__(self, "__delegate")

    def _get_instance(self) -> "Instance":
        return self._get_delegate()._get_instance()

    def __getattr__(self, attribute: str):
        delegate = self._get_delegate()

        try:
            return getattr(delegate, attribute)
        # simulated with Unknown here to simplify the PoC
        except UnexpectedReferenceException as e:
            return e.reference


class SequenceProxy(DynamicProxy, JSONSerializable):
    def __init__(self, iterator: Sequence) -> None:
        DynamicProxy.__init__(self, iterator)

    def __getitem__(self, key: str) -> object:
        instance = self._get_instance()
        if isinstance(key, str):
            raise RuntimeException(self, f"can not get a attribute {key}, {self._get_instance()} is a list")

        return DynamicProxy.return_value(instance[key])

    def __len__(self) -> int:
        return len(self._get_instance())

    def __iter__(self) -> Iterable:
        instance = self._get_instance()

        return IteratorProxy(instance.__iter__())

    def json_serialization_step(self) -> list[PrimitiveTypes]:
        # Ensure proper unwrapping by using __getitem__
        return [i for i in self]


class DictProxy(DynamicProxy, Mapping, JSONSerializable):
    def __init__(self, mydict: dict[object, object]) -> None:
        DynamicProxy.__init__(self, mydict)

    def __getitem__(self, key):
        instance = self._get_instance()
        if not isinstance(key, str):
            raise RuntimeException(self, f"Expected string key, but got {key}, {self._get_instance()} is a dict")

        return DynamicProxy.return_value(instance[key])

    def __len__(self) -> int:
        return len(self._get_instance())

    def __iter__(self):
        instance = self._get_instance()

        return IteratorProxy(instance.__iter__())

    def json_serialization_step(self) -> dict[str, PrimitiveTypes]:
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
