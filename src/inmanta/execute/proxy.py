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

import contextvars
import dataclasses
import enum
from collections.abc import Iterator, Mapping, Sequence
from copy import copy
from dataclasses import is_dataclass
from types import TracebackType
from typing import TYPE_CHECKING, Callable, ContextManager, Optional, Self, Union

# Keep UnsetException and UnknownException in place for backward compat with <iso8
from inmanta import references
from inmanta.ast import UnsetException  # noqa F401
from inmanta.ast import Location, NotFoundException, RuntimeException, UnexpectedReference, UnknownException
from inmanta.execute.util import NoneValue, Unknown
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


class ProxyMode(enum.Enum):
    """
    The mode to proxy values for. Export mode is more lax than plugin mode when it comes to references.
    """

    PLUGIN = enum.auto()
    EXPORT = enum.auto()


global_proxy_mode: contextvars.ContextVar[ProxyMode] = contextvars.ContextVar("global_proxy_mode", default=ProxyMode.PLUGIN)
"""
This variable controls the behavior of all proxy objects

It is global variable for performance reasons. Dynamic proxies are extremely performance sensitive because the are use a lot
"""


class ExportContext(ContextManager[None]):

    def __enter__(self) -> None:
        global_proxy_mode.set(ProxyMode.EXPORT)

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, traceback: TracebackType | None
    ) -> None:
        global_proxy_mode.set(ProxyMode.PLUGIN)


exportcontext = ExportContext()


class ProxyContext:
    """
    Context for creating proxy objects. Declares whether the object has already passed certain validation or whether certain
    special values are expected in the object's values (attributes, list elements, ...).

    E.g. a top-level plugin argument will have been validated at the boundary, and an undeclared reference would have been
    rejected by that validation. In contrast, an opaque DSL instance's attributes have had no boundary validation, and may
    contain references that are not (can not be) declared. Since we require reference support to always be explicit, we have
    to reject reference values in such cases.

    The global_proxy_mode determines the overall behavior:
    1. when in export mode, references are always allowed
    2. when in plugin mode, reference access is controlled by allow_reference_values and validated


    :param validated: True iff the object to proxy has been validated at the plugin boundary.
    :param allow_reference_values: Allow references for values accessed through this proxy. Either because they have been
        declared and validated, or because explicitly requested. Defaults to allow references iff the object has been
        validated. Kept as a separate field to allow overrides for a single proxy object while maintaining behavior for
        nested proxies. This value is not passed on to children.
    :param path: The path, within the plugin's argument namespace, where this object lives. Should be compatible with
        composition at the tail, e.g. `list_arg[0].attr`.
    """

    __slots__ = ("path", "validated", "allow_reference_values")

    def __init__(self, *, path: str, validated: bool = True, allow_reference_values: Optional[bool] = None) -> None:
        self.path = path
        self.validated = validated
        self.allow_reference_values = allow_reference_values

    def nested(self, *, relative_path: str) -> "ProxyContext":
        """
        Returns a context object for values nested one level deeper than the current context.

        :param relative_path: The path of new object, relative to the current context.
        """
        return ProxyContext(
            path=self.path + relative_path,
            validated=self.validated,
            # we're proxying elements one level deeper than the current context
            # => reset allow_reference_values to default behavior
            allow_reference_values=None,
        )

    def allow_references(self) -> "ProxyContext":
        return ProxyContext(
            path=self.path,
            validated=self.validated,
            allow_reference_values=True,
        )

    def should_allow_references(self) -> bool:
        if global_proxy_mode.get() is ProxyMode.EXPORT:
            return True
        return self.allow_reference_values if self.allow_reference_values is not None else self.validated


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

    def __init__(self, instance: "Instance", *, context: Optional[ProxyContext] = None) -> None:
        """
        :param instance: The object to proxy.
        :param context: The context this object lives in.
        """
        # str() is expensive. And also not helpful for e.g. dicts.
        # => Fall back to object.__repr__ for externally created objects (internal calls should all pass a context)
        context = context if context is not None else ProxyContext(path=object.__repr__(instance))
        object.__setattr__(self, "__instance", instance)
        object.__setattr__(self, "__context", context)

    def _get_instance(self) -> "Instance":
        return object.__getattribute__(self, "__instance")

    def _get_context(self) -> ProxyContext:
        return object.__getattribute__(self, "__context")

    def _allow_references(self: Self) -> Self:
        """
        Returns a copy of this proxy object that allows access to its elements even if they are references.

        Allows references for a single object, not nested.
        """
        # don't just call constructor for backwards compatibility: some children outside of core might not have context arg
        new: Self = copy(self)
        object.__setattr__(new, "__context", self._get_context().allow_references())
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
                key, value = key_value
                if not isinstance(key, str):
                    raise RuntimeException(
                        None, f"dict keys should be strings, got {key!r} of type {type(key)} with dict value {value!r}"
                    )
                return (key, cls.unwrap(value, dynamic_context=dynamic_context))

            return dict(map(recurse_dict_item, item.items()))

        if isinstance(item, references.Reference):
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
        context: Optional[ProxyContext] = None,  # optional for backwards compatibility
    ) -> Union[None, str, tuple[object, ...], int, float, bool, "DynamicProxy", "references.Reference"]:
        """
        Converts a value from the internal domain to the plugin domain.

        :param context: The context in which the given object lives. If None, assumes that the value has already passed
            validation. When None, the object's string representation, rather than its name is used for error reporting.
        """

        if value is None:
            return None

        if isinstance(value, NoneValue):
            return None

        if isinstance(value, Unknown):
            raise UnknownException(value)

        if isinstance(value, (str, tuple, int, float, bool)):
            return copy(value)

        if isinstance(value, references.Reference):
            # if a reference gets here, it has been validated, and we want to represent it as a reference, not a proxy
            return value

        if isinstance(value, DynamicProxy):
            return value

        # str() is expensive. And also not helpful for e.g. dicts.
        # => Fall back to object.__repr__ for externally created objects (internal calls should all pass a context)
        context = context if context is not None else ProxyContext(path=object.__repr__(value))

        if isinstance(value, dict):
            return DictProxy(value, context=context)

        if hasattr(value, "__len__"):
            return SequenceProxy(value, context=context)

        if hasattr(value, "__call__"):
            return CallProxy(value, context=context)

        return DynamicProxy(
            value,
            # DSL instances are a black box as far as boundary validation is concerned
            # => from here on out, consider the object not validated, except during export
            context=(
                ProxyContext(
                    path=context.path,
                    validated=False,
                    allow_reference_values=None,
                )
                if context.validated
                else context
            ),
        )

    def _return_value(self, value: object, *, relative_path: str) -> object:
        """
        Return a value that was accessed through this proxy object. Validates for undeclared references and propagates context
        appropriately.
        """
        context: ProxyContext = self._get_context()
        value_context: ProxyContext = context.nested(relative_path=relative_path)

        if isinstance(value, references.Reference) and not context.should_allow_references():
            # Non-dataclass entities can not be explicit about reference support.
            # The Python domain is a black box. We don't want to transparently pass unexpected values in there.
            # => don't allow references in attributes. Can be explicitly allowed via allow_reference_attributes() wrapper
            raise UnexpectedReference(
                reference=value,
                message=(
                    "Encountered unexpected reference value during plugin execution. Plugins are only allowed to access"
                    " reference values when declared explicitly. Either use a dataclass entity that supports references (e.g."
                    " `int | Reference[int]` attribute annotation), or explicitly allow references on attribute access with the"
                    " `inmanta.plugins.allow_reference_values()` wrapper."
                    f" Encountered at {value_context.path} (= `{value!r}`)."
                ),
            )

        return DynamicProxy.return_value(value, context=value_context)

    def __getattr__(self, attribute: str):
        instance = self._get_instance()

        try:
            value = instance.get_attribute(attribute).get_value()
        except NotFoundException as e:
            # allow for hasattr(proxy, "some_attr")
            raise AttributeError(e.stmt, e.name)

        return self._return_value(value, relative_path=f".{attribute}")

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
    def __init__(self, iterator: Sequence[object], *, context: Optional[ProxyContext] = None) -> None:
        DynamicProxy.__init__(self, iterator, context=context)

    def __getitem__(self, key: int) -> object:
        instance = self._get_instance()
        if isinstance(key, str):
            raise RuntimeException(self, f"can not get a attribute {key}, {self._get_instance()} is a list")

        return self._return_value(instance[key], relative_path=f"[{key!r}]")

    def __iter__(self):
        return IteratorProxy(iter(self._get_instance()), context=self._get_context(), sequence=True)

    def __len__(self) -> int:
        return len(self._get_instance())

    def json_serialization_step(self) -> list[PrimitiveTypes]:
        # Ensure proper unwrapping by using __getitem__
        return [i for i in self]


class DictProxy(DynamicProxy, Mapping[str, object], JSONSerializable):
    def __init__(self, mydict: dict[str, object], *, context: Optional[ProxyContext] = None) -> None:
        DynamicProxy.__init__(self, mydict, context=context)

    def __getitem__(self, key):
        instance = self._get_instance()
        if not isinstance(key, str):
            raise RuntimeException(self, f"Expected string key, but got {key}, {self._get_instance()} is a dict")

        return self._return_value(instance[key], relative_path=f"[{key!r}]")

    def __iter__(self):
        return IteratorProxy(iter(self._get_instance()), context=self._get_context(), sequence=False)

    def __len__(self) -> int:
        return len(self._get_instance())

    def json_serialization_step(self) -> dict[str, PrimitiveTypes]:
        # Ensure proper unwrapping by using __getitem__
        return {k: v for k, v in self.items()}


class IteratorProxy(DynamicProxy, Iterator[object]):
    """
    Proxy an iterator call.

    A custom proxy allows us to continue iteration after exceptions are raised and caught by the caller, i.e. special exception
    types like UnknownException.
    """

    def __init__(self, iterator: Iterator[object], *, context: Optional[ProxyContext] = None, sequence: bool = False) -> None:
        """
        :param sequence: True iff the given iterator represents a sequence, i.e. the index is meaningful for error reporting.
        """
        DynamicProxy.__init__(self, enumerate(iterator), context=context)
        object.__setattr__(self, "__sequence", sequence)

    def _is_sequence(self) -> bool:
        return object.__getattribute__(self, "__sequence")

    def __iter__(self) -> Iterator[object]:
        return self

    def __next__(self) -> object:
        enumerator = self._get_instance()
        i, v = next(enumerator)
        return self._return_value(
            v,
            # if it's not a sequence, pointing to the object itself is the best we can do
            relative_path=f"[{i}]" if self._is_sequence() else "",
        )


class CallProxy(DynamicProxy):
    """
    Proxy a value that implements a __call__ function
    """

    def __init__(self, instance: Callable[..., object], *, context: Optional[ProxyContext] = None) -> None:
        DynamicProxy.__init__(self, instance, context=context)

    def __call__(self, *args, **kwargs):
        instance = self._get_instance()

        return instance(*args, **kwargs)
