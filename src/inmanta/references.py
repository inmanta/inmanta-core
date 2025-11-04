"""
Copyright 2025 Inmanta

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

import abc
import builtins
import collections
import dataclasses
import hashlib
import json
import typing
import uuid
from typing import Generic, Literal, Never, Optional, Tuple

import pydantic
import typing_inspect
from pydantic import ValidationError

import inmanta
import inmanta.resources
import jsonpath_ng
import typing_extensions
from inmanta import util
from inmanta.types import JsonType, ResourceIdStr, StrictJson

ReferenceType = typing.Annotated[str, pydantic.StringConstraints(pattern="^([a-z0-9_]+::)+[A-Z][A-z0-9_-]*$")]
PrimitiveTypes = str | float | int | bool | None


# The name of an attribute on the class where dataclasses store field information. This is an integral part of the
# dataclasses protocol. All the helpers in dataclasses rely on this field, however `dataclasses._FIELDS` that has
# the same value is not exported.
DATACLASS_FIELDS = "__dataclass_fields__"

# Typing of dataclass.* methods relies entirely on the definition in typeshed that only exists during typechecking.
# This ensures that our code works during typechecking and at runtime.
if not typing.TYPE_CHECKING:
    DataclassProtocol = object
else:
    import _typeshed

    DataclassProtocol = _typeshed.DataclassInstance

    import inmanta.ast.type as inm_type
    from inmanta.agent import handler

type RefValue = PrimitiveTypes | DataclassProtocol


class ReferenceCycleException(Exception):
    """Exception raised when a reference refers to itself"""

    def __init__(self, first_ref: "Reference[RefValue]") -> None:
        self.references: list[Reference[RefValue]] = [first_ref]
        self.complete = False

    def add(self, element: "Reference") -> None:
        """Collect parent entities while traveling up the stack"""
        if self.complete:
            return
        if element in self.references:
            self.complete = True
        self.references.append(element)

    def get_message(self) -> str:
        trace = " -> ".join([repr(x) for x in self.references])
        return "Reference cycle detected: %s" % (trace)

    def __str__(self) -> str:
        return self.get_message()


class Argument(pydantic.BaseModel):
    """Base class for reference (resolver) arguments"""

    type: str
    """ The type of the argument. It is used as a discriminator to select the correct class
    """

    name: str
    """ The name of the argument in the reference constructor
    """

    @abc.abstractmethod
    def get_arg_value(
        self,
        resource: "inmanta.resources.Resource",
        logger: "handler.LoggerABC",
    ) -> object:
        """Get the value for the argument to be able to construct the reference again

        :param resource: The resource on which the reference has been defined
        :param logger: The logger context to use while resolving/deserializing
        """


class LiteralArgument(Argument):
    """Literal argument to a reference"""

    type: typing.Literal["literal"] = "literal"
    value: PrimitiveTypes

    def get_arg_value(
        self,
        resource: "inmanta.resources.Resource",
        logger: "handler.LoggerABC",
    ) -> object:
        return self.value


class JsonArgument(Argument):
    """Json-like argument to a reference"""

    type: typing.Literal["json"] = "json"
    value: StrictJson

    def get_arg_value(
        self,
        resource: "inmanta.resources.Resource",
        logger: "handler.LoggerABC",
    ) -> object:
        return self.value


class ReferenceArgument(Argument):
    """Use the value of another reference as an argument for the reference"""

    type: typing.Literal["reference"] = "reference"
    id: uuid.UUID

    def get_arg_value(
        self,
        resource: "inmanta.resources.Resource",
        logger: "handler.LoggerABC",
    ) -> object:
        return resource.get_reference_value(self.id, logger)


class MutatedJsonArgument(Argument):
    """
    Json-like argument that contains another reference in the json structure

    It is stored as
    1. a json value with all reference replaced by None
    2. a mapping of dictpaths to references. Each dict path indicates where the reference should be inserted

    """

    type: typing.Literal["mjson"] = "mjson"
    value: StrictJson
    references: dict[str, ReferenceArgument]

    def get_arg_value(
        self,
        resource: "inmanta.resources.Resource",
        logger: "handler.LoggerABC",
    ) -> object:
        start_value: JsonType = self.value
        for destination, valueref in self.references.items():
            value = valueref.get_arg_value(resource, logger)

            # backward compat between 8.2 and higher
            # jsonpath_ng does not allow starting with ., dictpath does
            if destination.startswith("."):
                destination = "$" + destination
            jsonpath_expr = jsonpath_ng.parse(destination)
            jsonpath_expr.update(start_value, value)
        return start_value


class GetArgument(Argument):
    """Get a value from the resource body as value"""

    type: typing.Literal["get"] = "get"
    dict_path_expression: str

    def get_arg_value(
        self,
        resource: "inmanta.resources.Resource",
        logger: "handler.LoggerABC",
    ) -> object:
        return None


class PythonTypeArgument(Argument):
    """Use the python type as an argument. This is mostly used for references that are generic for a
    type, such as core::AttributeReference
    """

    type: typing.Literal["python_type"] = "python_type"
    value: str

    def get_arg_value(
        self,
        resource: "inmanta.resources.Resource",
        logger: "handler.LoggerABC",
    ) -> object:
        return getattr(builtins, self.value)


class ResourceArgument(Argument):
    """This argument provides the resource itself to the reference"""

    type: typing.Literal["resource"] = "resource"
    id: ResourceIdStr

    def get_arg_value(
        self,
        resource: "inmanta.resources.Resource",
        logger: "handler.LoggerABC",
    ) -> object:
        if not resource.id.resource_str() == self.id:
            raise Exception(
                f"This resource refers to another resource {self.id} instead of "
                f"itself {resource.id.resource_str()}, this is not supported"
            )
        return resource


ArgumentTypes = typing.Annotated[
    LiteralArgument
    | ReferenceArgument
    | GetArgument
    | PythonTypeArgument
    | ResourceArgument
    | JsonArgument
    | MutatedJsonArgument,
    pydantic.Field(discriminator="type"),
]
""" A list of all specific types of arguments. Pydantic uses this to instantiate the correct argument class
"""


class SerializedReferenceLike(pydantic.BaseModel):
    """
    A base model class for references and mutators in their serialized form
    """

    type: ReferenceType
    args: list[ArgumentTypes]


class ReferenceModel(SerializedReferenceLike):
    """A reference"""

    id: uuid.UUID


class MutatorModel(SerializedReferenceLike):
    """A mutator"""


C = typing.TypeVar("C", bound="ReferenceLike")


CYCLE_TOKEN = object()
# Token to perform cycle detection when serializing


class ReferenceLike:
    """A base class for references and mutators"""

    type: typing.ClassVar[ReferenceType]

    def __init__(self) -> None:
        self._model: typing.Optional[SerializedReferenceLike] | Literal[CYCLE_TOKEN] = None

        # Only present in compiler
        # Will be set by DynamicProxy.unwrap at the plugin boundary
        self._model_type: typing.Optional["inm_type.Type"] = None

    def resolve_other[S: RefValue](self, value: "Reference[S] | S", logger: "handler.LoggerABC") -> S:
        """
        Given a reference or a value, either return the value or the value obtained by resolving the reference.

        This method is intended to be used by mutators and references to resolve their own parameters
        (which could be references as well.

        When resolving references on the handler side, all parameters will already be resolved
        and this method only serves to ensure correct typing.

        When resolving reference on the compiler side, not all references will be resolved and using this method is required.
        """
        if isinstance(value, Reference):
            return value.get(logger)
        return value

    @classmethod
    def deserialize(
        cls: typing.Type[C],
        ref: SerializedReferenceLike,
        resource: "inmanta.resources.Resource",
        logger: "handler.LoggerABC",
    ) -> C:
        """Deserialize the reference or mutator.

        :param ref: The model of the reference to deserialize
        :param resource: The resource to use as a read-only reference
        """
        return cls(**{arg.name: arg.get_arg_value(resource, logger) for arg in ref.args})

    @abc.abstractmethod
    def serialize(self) -> SerializedReferenceLike:
        """Serialize to be able to add them to a resource"""
        raise NotImplementedError()

    def serialize_arguments(self) -> Tuple[uuid.UUID, list[ArgumentTypes]]:
        """Serialize the arguments to this class"""

        # The handling of references here is a bit subtle:
        # We replace every reference with a ReferenceArgument that refers to the reference by id
        # The reference itself is not handled here but in inmanta.resources.ReferenceSubCollector.collect_reference
        # There, the raw, unserialized tree of arguments is iterated over as well to collect the references themselves
        # The caches on the Reference prevent this from being too inefficient by serializing only once
        arguments: list[ArgumentTypes] = []
        for name, value in self.arguments.items():
            match value:
                case str() | int() | float() | bool() | None:
                    arguments.append(LiteralArgument(name=name, value=value))
                case dict() | list():
                    collector = inmanta.resources.ReferenceSubCollector()
                    # The collector here is purely to collect the path/reference pairs
                    # The set of reference it collects will be discarded
                    # The root ReferenceCollector will traverse past this point as well to collect the actual reference
                    cleaned_value = collector.collect_references(value, "$")
                    try:
                        if collector.references:
                            arguments.append(
                                MutatedJsonArgument(
                                    name=name,
                                    value=cleaned_value,
                                    references={
                                        path: ReferenceArgument(name=path, id=model.id)
                                        for path, model in collector.replacements.items()
                                    },
                                )
                            )
                        else:
                            arguments.append(JsonArgument(name=name, value=value))
                    except ValidationError:
                        raise ValueError(f"The {name} attribute of {self!r} is not json serializable: {value}")
                case Reference():
                    model = value.serialize()
                    arguments.append(ReferenceArgument(name=name, id=model.id))

                case inmanta.resources.Resource() as v:
                    arguments.append(ResourceArgument(name=name, id=v.id.resource_str()))
                case type() if value in [str, float, int, bool]:
                    arguments.append(PythonTypeArgument(name=name, value=value.__name__))

                case _:
                    raise TypeError(f"Unable to serialize argument `{name}` of `{self!r}` with value {value}")

        data = json.dumps({"type": self.type, "args": arguments}, default=util.api_boundary_json_encoder, sort_keys=True)
        hasher = hashlib.md5()
        hasher.update(data.encode())
        return uuid.uuid3(uuid.NAMESPACE_OID, hasher.digest()), arguments

    @property
    def arguments(self) -> collections.abc.Mapping[str, object]:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False

        assert isinstance(other, ReferenceLike)  # mypy can't figure out the check above

        return self.arguments == other.arguments


class Mutator(ReferenceLike):
    """A mutator that has side effects when executed"""

    @abc.abstractmethod
    def run(self, logger: "handler.LoggerABC") -> None:
        """Execute the mutator"""

    def serialize(self) -> MutatorModel:
        """Emit the correct pydantic objects to serialize the reference in the exporter."""
        if not self._model:
            arg_id, arguments = self.serialize_arguments()
            self._model = MutatorModel(type=self.type, args=arguments)

        assert isinstance(self._model, MutatorModel)
        return self._model


T = typing_extensions.TypeVar("T", bound=RefValue, covariant=True, default=RefValue)


class Reference(ReferenceLike, Generic[T]):
    """Instances of this class can create references to a value and resolve them."""

    def __init__(self) -> None:
        super().__init__()
        self._reference_value: T
        self._reference_value_cached: bool = False

    @classmethod
    def get_reference_type(cls) -> type[T] | None:
        # We are that inherits from Reference[T]
        # We do a best effort here to untangle this, but it is difficult because of
        # https://github.com/ilevkivskyi/typing_inspect/issues/110
        # We can only handle the case where T is a concrete type, not where it is a re-mapped type-var
        # https://github.com/inmanta/inmanta-core/issues/8765
        for g in cls.__orig_bases__:  # type: ignore
            if typing_inspect.is_generic_type(g) and typing.get_origin(g) is Reference:
                return typing.get_args(g)[0]
        return None

    @classmethod
    def is_dataclass_reference(cls) -> bool:
        return dataclasses.is_dataclass(cls.get_reference_type())

    @abc.abstractmethod
    def resolve(self, logger: "handler.LoggerABC") -> T:
        """This method resolves the reference and returns the object that it refers to"""
        pass

    def get(self, logger: "handler.LoggerABC") -> T:
        """Get the value. If we have already resolved it a cached value is returned, otherwise resolve() is called"""
        if not self._reference_value_cached:
            self._reference_value = self.resolve(logger)
            self._reference_value_cached = True

        else:
            logger.debug("Using cached value for reference %(reference)s", reference=repr(self))
        return self._reference_value

    def serialize(self) -> ReferenceModel:
        """Emit the correct pydantic objects to serialize the reference in the exporter."""
        if self._model is CYCLE_TOKEN:
            raise ReferenceCycleException(self)
        if not self._model:
            self._model = CYCLE_TOKEN
            try:
                argument_id, arguments = self.serialize_arguments()
            except ReferenceCycleException as e:
                e.add(self)
                raise
            self._model = ReferenceModel(id=argument_id, type=self.type, args=arguments)

        assert isinstance(self._model, ReferenceModel)
        return self._model

    def __bool__(self) -> Never:
        raise NotImplementedError(f"{self!r} is an inmanta reference, not a boolean.")


class reference:
    """This decorator registers a reference under a specific name"""

    # It is not allowed to use T in a class var so we cannot use T here
    _reference_classes: typing.ClassVar[dict[str, type[Reference[RefValue]]]] = {}

    def __init__(self, name: str) -> None:
        """
        :param name: This name is used to indicate the type of the reference
        """
        self.name = name

    @classmethod
    def add_reference(cls, name: str, reference_type: type[Reference[RefValue]]) -> None:
        cls._reference_classes[name] = reference_type

    def __call__[C: type[Reference]](self, cls: C) -> C:
        """Register a new reference. If we already have it explicitly delete it (reload)"""
        if self.name in type(self)._reference_classes:
            del type(self)._reference_classes[self.name]

        type(self)._reference_classes[self.name] = cls
        cls.type = self.name
        return cls

    @classmethod
    def get_class(cls, name: str) -> type[Reference[RefValue]]:
        """Get the reference class registered with the given name"""
        if name not in cls._reference_classes:
            raise TypeError(f"There is no reference class registered with name {name}")

        return cls._reference_classes[name]

    @classmethod
    def reset(cls) -> None:
        """Reset the registered reference classes"""
        # Keep core ones
        cls._reference_classes = {k: v for k, v in cls._reference_classes.items() if k.startswith("core::")}

    @classmethod
    def get_references(cls) -> typing.Iterator[tuple[str, type[Reference[RefValue]]]]:
        """Return an iterator with all items registered."""
        return (item for item in cls._reference_classes.items())


class mutator:
    """This decorator register a mutator under a specific name"""

    _mutator_classes: typing.ClassVar[dict[str, type[Mutator]]] = {}

    def __init__(self, name: str) -> None:
        """
        :param name: This name is used to indicate the type of the mutator
        """
        self.name = name

    @classmethod
    def add_mutator(cls, name: str, mutator_type: type[Mutator]) -> None:
        cls._mutator_classes[name] = mutator_type

    def __call__[T: Mutator](self, cls: type[T]) -> type[T]:
        """Register a new mutator. If we already have it explicitly delete it (reload)"""
        if self.name in mutator._mutator_classes:
            del mutator._mutator_classes[self.name]

        mutator._mutator_classes[self.name] = cls
        cls.type = self.name
        return cls

    @classmethod
    def get_class(cls, name: str) -> type[Mutator]:
        """Get the mutator class registered with the given name"""
        if name not in cls._mutator_classes:
            raise TypeError(f"There is no mutator class registered with name {name}")

        return cls._mutator_classes[name]

    @classmethod
    def reset(cls) -> None:
        """Reset the registered mutator classes"""
        # Keep core ones
        cls._mutator_classes = {k: v for k, v in cls._mutator_classes.items() if k.startswith("core::")}

    @classmethod
    def get_mutators(cls) -> typing.Iterator[tuple[str, type[Mutator]]]:
        """Return an iterator with all items registered."""
        return (item for item in cls._mutator_classes.items())


@reference(name="core::AttributeReference")
class AttributeReference[T: PrimitiveTypes](Reference[T]):
    """A reference that points to a value in an attribute of a dataclass"""

    def __init__(
        self,
        reference: DataclassProtocol | Reference[DataclassProtocol],
        attribute_name: str,
    ) -> None:
        super().__init__()
        self.attribute_name = attribute_name
        self.reference = reference

    def resolve(self, logger: "handler.LoggerABC") -> T:
        return typing.cast(T, getattr(self.resolve_other(self.reference, logger), self.attribute_name))


@mutator(name="core::Replace")
class ReplaceValue(Mutator):
    """Replace a reference in the provided resource"""

    def __init__(self, resource: "inmanta.resources.Resource", value: Reference[PrimitiveTypes], destination: str) -> None:
        """Change a value in the given resource at the given distination

        :param resource: The resource to replace the value in
        :param value: The value to replace in `resource` at `destination`
        :param destination: A dictpath expression where to replace the value
        """
        super().__init__()
        self.resource = resource
        self.value = value
        self.destination = destination

    def run(self, logger: "handler.LoggerABC") -> None:
        value = self.resolve_other(self.value, logger)
        jsonpath_expr = jsonpath_ng.parse(self.destination)
        jsonpath_expr.update(self.resource, value)


@typing.runtime_checkable
class MaybeReference(typing.Protocol):
    """
    DSL value that may represent a reference in the Python domain, while having a different value in the DSL domain.

    This includes DSL dataclass instances with reference attributes, if they were initially constructed in the Python
    domain as a reference to a dataclass instance (and converted on the boundary).
    """

    __slots__ = ()

    def unwrap_reference(self) -> Optional[Reference]:
        """
        If this DSL value represents a reference value, returns the associated reference object. Otherwise returns None.
        """
        ...


def unwrap_reference(value: object) -> Optional[Reference]:
    """
    Iff the given value is a reference or a DSL value that represents a reference, returns the associated reference.
    Otherwise returns None.

    This includes DSL dataclass instances with reference attributes, if they were initially constructed in the Python
    domain as a reference to a dataclass instance (and converted on the boundary).
    """
    return value if isinstance(value, Reference) else value.unwrap_reference() if isinstance(value, MaybeReference) else None


def is_reference_of(instance: typing.Optional[object], type_class: type[object]) -> bool:
    """Is the given instance a reference to the given type."""
    if instance is None or not isinstance(instance, Reference):
        return False

    return instance.get_reference_type() == type_class
