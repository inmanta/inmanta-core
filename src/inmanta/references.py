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
from typing import Literal, Tuple

import pydantic
import typing_inspect

import inmanta
import inmanta.resources
from inmanta import util
from inmanta.types import ResourceIdStr
from inmanta.util import dict_path

ReferenceType = typing.Annotated[str, pydantic.StringConstraints(pattern="^([a-z0-9_]+::)+[A-Z][A-z0-9_-]*$")]
PrimitiveTypes = str | float | int | bool


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

T = typing.TypeVar("T", bound=RefValue)


class ReferenceCycleException(Exception):
    """Exception raised when a reference refers to itself"""

    def __init__(self, first_ref: "Reference[RefValue]") -> None:
        self.references: list[Reference[RefValue]] = [first_ref]
        self.complete = False

    def add(self, element: "Reference[RefValue]") -> None:
        """Collect parent entities while traveling up the stack"""
        if self.complete:
            return
        if element in self.references:
            self.complete = True
        self.references.append(element)

    def get_message(self) -> str:
        trace = " -> ".join([str(x) for x in self.references])
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
    LiteralArgument | ReferenceArgument | GetArgument | PythonTypeArgument | ResourceArgument,
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
        arguments: list[ArgumentTypes] = []
        for name, value in self.arguments.items():
            match value:
                case str() | int() | float() | bool():
                    arguments.append(LiteralArgument(name=name, value=value))

                case Reference():
                    model = value.serialize()
                    arguments.append(ReferenceArgument(name=name, id=model.id))

                case inmanta.resources.Resource():
                    arguments.append(ResourceArgument(name=name, id=value.id.resource_str()))

                case type() if value in [str, float, int, bool]:
                    arguments.append(PythonTypeArgument(name=name, value=value.__name__))

                case _:
                    raise TypeError(f"Unable to serialize argument `{name}` of `{self}` with value {value}")

        data = json.dumps({"type": self.type, "args": arguments}, default=util.api_boundary_json_encoder, sort_keys=True)
        hasher = hashlib.md5()
        hasher.update(data.encode())
        return uuid.uuid3(uuid.NAMESPACE_OID, hasher.digest()), arguments

    @property
    def arguments(self) -> collections.abc.Mapping[str, object]:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


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


class Reference[T: RefValue](ReferenceLike):
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
            logger.debug("Using cached value for reference %(reference)s", reference=str(self))
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


class reference:
    """This decorator registers a reference under a specific name"""

    # It is not allowed to use T in a class var so we cannot use T here
    _reference_classes: typing.ClassVar[dict[str, type[Reference[RefValue]]]] = {}

    def __init__(self, name: str) -> None:
        """
        :param name: This name is used to indicate the type of the reference
        """
        self.name = name

    def __call__[T: Reference[RefValue]](self, cls: type[T]) -> type[T]:
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
        dict_path_expr = dict_path.to_path(self.destination)
        dict_path_expr.set_element(self.resource, value)


def is_reference_of(instance: typing.Optional[object], type_class: type[object]) -> bool:
    """Is the given instance a reference to the given type."""
    if instance is None or not isinstance(instance, Reference):
        return False

    return instance.get_reference_type() == type_class
