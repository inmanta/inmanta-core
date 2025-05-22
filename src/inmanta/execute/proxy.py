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
from typing import TYPE_CHECKING, Callable, Optional, Union

# Keep UnsetException, UnknownException and AttributeNotFound in place for backward compat with <iso8
from inmanta.ast import (
    AttributeNotFound,
    Location,
    NotFoundException,
    RuntimeException,
    UndeclaredReference,
    UnknownException,
)
from inmanta.ast import UnsetException  # noqa F401
from inmanta.execute.util import NoneValue, Unknown
from inmanta.references import Reference
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


# TODO: docstring & name (broader than return_value. Really a proxy context
@dataclasses.dataclass(kw_only=True, frozen=True, slots=True)
class DynamicReturnValueContext:
    """
    :param allow_references: Allow values returned / proxied by this instance to be references.
    """
    # TODO: better name
    allow_references: bool = True
    # TODO: better name + docstring. Name something that indicates "contents" have not been validated
    type_validated: bool = True


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

    # TODO: consider how to integrage JinjaProxy
    def __init__(self, instance: "Instance", *, parent_context: Optional[DynamicReturnValueContext] = None) -> None:
        object.__setattr__(self, "__instance", instance)
        object.__setattr__(self, "__context", self._from_parent_context(parent_context))

    def _get_instance(self) -> "Instance":
        return object.__getattribute__(self, "__instance")

    def _get_context(self) -> DynamicReturnValueContext:
        return object.__getattribute__(self, "__context")

    # TODO: name and docstring
    @classmethod
    def _black_box(cls) -> bool:
        return True

    # TODO: docstring
    @classmethod
    def _from_parent_context(cls, parent_context: Optional[DynamicReturnValueContext]) -> DynamicReturnValueContext:
        parent_context = parent_context if parent_context is not None else DynamicReturnValueContext()
        return (
            dataclasses.replace(parent_context, allow_references=False, type_validated=False)
            if cls._black_box()
            else parent_context
        )

    # TODO: name: imply that it's a copy
    def _allow_references[P: DynamicProxy](self: P) -> P:
        # TODO: docstring
        # don't just call constructor for backwards compatibility: some children outside of core might not have context arg
        new: P = copy(self)
        object.__setattr__(new, "__context", dataclasses.replace(self._get_context(), allow_references=True))
        return new

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
                item._model_type = dataclass_ref_type
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
        *,
        # TODO: docstring
        context: Optional[DynamicReturnValueContext] = None,
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

        if isinstance(value, Reference):
            if context is not None and not context.allow_references:
                # TODO: tailor-made exceptions from child classes, e.g. through class method with context?
                raise UndeclaredReference(
                    reference=value,
                    # TODO: message
                    message="Undeclared reference found",
                )
            else:
                # if a reference gets here, it has been validated, and we want to represent it as a reference, not a proxy
                return value

        # TODO: shift this down?
        new_context: Optional[DynamicReturnValueContext] = (
            # we're proxying one level deeper than the current context => recalculate allow_references for proxied values
            dataclasses.replace(context, allow_references=context.type_validated)
            if context is not None
            else None
        )

        if isinstance(value, DynamicProxy):
            # TODO: set type_validated? + come up with test scenario
            return value

        if isinstance(value, dict):
            return DictProxy(value, parent_context=new_context)

        if hasattr(value, "__len__"):
            return SequenceProxy(value, parent_context=new_context)

        if hasattr(value, "__call__"):
            return CallProxy(value, parent_context=new_context)

        return DynamicProxy(value, parent_context=new_context)

    # TODO: see if we can use traceback.extract_stack() here to add a location to any exceptions, try-except style
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
        if not self._get_context().allow_references and isinstance(value, Reference):
            # TODO: string format accepts reference. Should also raise this exception
            raise UndeclaredReference(
                reference=value,
                message=(
                    "Encountered reference value in instance attribute. Plugins are only allowed to access reference values"
                    " when declared explicitly. Either use a dataclass entity that supports references (e.g."
                    " `int | Reference[int]` attribute annotation), or explicitly allow references on attribute access with the"
                    # TODO: name
                    " `inmanta.plugins.allow_reference_attributes()` wrapper."
                    f" ({attribute}={value} on instance {self._get_instance()})"
                ),
            )

        # TODO: consider the semantics of the context and how it's propagated. We've already checked `value` here, we primarily
        #       want IT to be considered a black box, not to have it rejected if it's a reference. BUT for the other proxy
        #       classes it would be great if they didn't have to all implement a custom check. So how to differentiate between
        #       "I'm a black box calling return_value on an element value" and
        #       "I'm calling return_value on an element value that I know to be a black box"?
        # TODO: review this comment
        # Contents of an entity are always a black box, regardless of the current context
        return DynamicProxy.return_value(value, context=self._get_context())

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
    def __init__(self, iterator: Sequence, *, parent_context: Optional[DynamicReturnValueContext] = None) -> None:
        DynamicProxy.__init__(self, iterator, parent_context=parent_context)

    @classmethod
    def _black_box(cls) -> bool:
        # unless specified otherwise, the elements of this type have been validated at the plugin boundary
        return False

    def __getitem__(self, key: str) -> object:
        instance = self._get_instance()
        if isinstance(key, str):
            raise RuntimeException(self, f"can not get a attribute {key}, {self._get_instance()} is a list")

        return DynamicProxy.return_value(instance[key], context=self._get_context())

    def __len__(self) -> int:
        return len(self._get_instance())

    def __iter__(self) -> Iterable:
        instance = self._get_instance()

        # TODO: is there any way to implement this so the context doesn't have to be passed everywhere explicitly?
        return IteratorProxy(instance.__iter__(), parent_context=self._get_context())

    def json_serialization_step(self) -> list[PrimitiveTypes]:
        # Ensure proper unwrapping by using __getitem__
        return [i for i in self]


class DictProxy(DynamicProxy, Mapping, JSONSerializable):
    def __init__(self, mydict: dict[object, object], *, parent_context: Optional[DynamicReturnValueContext] = None) -> None:
        DynamicProxy.__init__(self, mydict, parent_context=parent_context)

    @classmethod
    def _black_box(cls) -> bool:
        # unless specified otherwise, the elements of this type have been validated at the plugin boundary
        return False

    def __getitem__(self, key):
        instance = self._get_instance()
        if not isinstance(key, str):
            raise RuntimeException(self, f"Expected string key, but got {key}, {self._get_instance()} is a dict")

        return DynamicProxy.return_value(instance[key], context=self._get_context())

    def __len__(self) -> int:
        return len(self._get_instance())

    def __iter__(self):
        instance = self._get_instance()

        return IteratorProxy(instance.__iter__(), parent_context=self._get_context())

    def json_serialization_step(self) -> dict[str, PrimitiveTypes]:
        # Ensure proper unwrapping by using __getitem__
        return {k: v for k, v in self.items()}


class CallProxy(DynamicProxy):
    """
    Proxy a value that implements a __call__ function
    """

    def __init__(self, instance: Callable[..., object], *, parent_context: Optional[DynamicReturnValueContext] = None) -> None:
        DynamicProxy.__init__(self, instance, parent_context=parent_context)

    @classmethod
    def _black_box(cls) -> bool:
        # unless specified otherwise, the elements of this type have been validated at the plugin boundary
        return False

    def __call__(self, *args, **kwargs):
        instance = self._get_instance()

        return instance(*args, **kwargs)


class IteratorProxy(DynamicProxy):
    """
    Proxy an iterator call
    """

    def __init__(self, iterator: Iterable[object], *, parent_context: Optional[DynamicReturnValueContext] = None) -> None:
        DynamicProxy.__init__(self, iterator, parent_context=parent_context)

    @classmethod
    def _black_box(cls) -> bool:
        # unless specified otherwise, the elements of this type have been validated at the plugin boundary
        return False

    def __iter__(self):
        return self

    def __next__(self):
        i = self._get_instance()
        return DynamicProxy.return_value(next(i), context=self._get_context())
