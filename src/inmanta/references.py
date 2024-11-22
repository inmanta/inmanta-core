"""
    Copyright 2024 Inmanta

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
import collections
import inspect
import typing
import uuid

import pydantic

import inmanta
from inmanta.util import dict_path

# from inmanta.dataclass import Value  # The base class for data classes: see the specific design

ReferenceType = typing.Annotated[str, pydantic.StringConstraints(pattern="^([a-z0-9_]+::)+[A-Z][A-z0-9_-]*$")]
PrimitiveTypes = str | float | int | bool


class Value:
    pass


T = typing.TypeVar("T", bound=Value | PrimitiveTypes)


class Argument(pydantic.BaseModel):
    """Base class for reference (resolver) arguments"""

    type: str
    """ The type of the argument. It is used a discriminator to select the correct class
    """

    name: str
    """ The name of the argument in the reference constructor
    """

    # TODO: we probably need a context like object so that it is easier to pass more data to this method
    @abc.abstractmethod
    def get_arg_value(self, resource: "inmanta.resources.Resource", references: dict[uuid.UUID, "Reference[T]"]) -> object:
        """Get the value for the argument to be able to construct the reference again

        :param resource: The resource on which the reference has been defined
        :param references: A mapping from id to reference. This mapping can be empty when this method is called. This mapping
                           is only complete when the full deserialization process is complete.
        """


class LiteralArgument(Argument):
    """Literal argument to a reference"""

    type: typing.Literal["literal"] = "literal"
    value: PrimitiveTypes

    def get_arg_value(self, resource: "inmanta.resources.Resource", references: dict[uuid.UUID, "Reference[T]"]) -> object:
        return self.value


class ReferenceArgument(Argument):
    """Use the value of another reference as an argument for the reference"""

    type: typing.Literal["reference"] = "reference"
    id: uuid.UUID

    def get_arg_value(self, resource: "inmanta.resources.Resource", references: dict[uuid.UUID, "Reference[T]"]) -> object:
        return ReferencePlaceHolder(self.id, references)


class GetArgument(Argument):
    """Get a value from the resource body as value"""

    type: typing.Literal["get"] = "get"
    dict_path_expression: str

    def get_arg_value(self, resource: "inmanta.resources.Resource", references: dict[uuid.UUID, "Reference[T]"]) -> object:
        return None


class PythonTypeArgument(Argument):
    """Use the python type as an argument. This is mostly used for references that are generic for a
    type, such as core::AttributeReference
    """

    type: typing.Literal["python_type"] = "python_type"
    value: str

    def get_arg_value(self, resource: "inmanta.resources.Resource", references: dict[uuid.UUID, "Reference[T]"]) -> object:
        return None


class ResourceArgument(Argument):
    """This argument provides the resource itself to the reference"""

    type: typing.Literal["resource"] = "resource"

    def get_arg_value(self, resource: "inmanta.resources.Resource", references: dict[uuid.UUID, "Reference[T]"]) -> object:
        return resource


ArgumentTypes = typing.Annotated[
    LiteralArgument | ReferenceArgument | GetArgument | PythonTypeArgument | ResourceArgument,
    pydantic.Field(discriminator="type"),
]
""" A list of all specific types of arguments. Pydantic uses this to instantiate the correct argument class
"""


class BaseModel(pydantic.BaseModel):
    """A base model class for references and mutators"""

    type: ReferenceType
    args: list[ArgumentTypes]


class ReferenceModel(BaseModel):
    """A reference"""

    id: uuid.UUID = pydantic.Field(default_factory=uuid.uuid4)


class MutatorModel(BaseModel):
    """A mutator"""


C = typing.TypeVar("C", bound="Base")


class Base:
    """A base class for references and mutators"""

    type: typing.ClassVar[ReferenceType]

    def __init__(self, **kwargs: object) -> None:
        self._arguments: typing.Mapping[str, object] = kwargs
        self._model: typing.Optional[ReferenceModel] = None
        # TODO: do we want to enfore type correctness when creating a reference? This also has impact on how arguments are
        # are serialized: based on instance types or on static types

    @classmethod
    def deserialize(
        cls: typing.Type[C],
        ref: BaseModel,
        resource: "inmanta.resources.Resource",
        references: dict[uuid.UUID, "Reference[T]"],
    ) -> typing.Type[C]:
        return cls(**{arg.name: arg.get_arg_value(resource, references) for arg in ref.args})

    @abc.abstractmethod
    def serialize(self) -> BaseModel:
        """Serialize to be able to add them to a resource"""

    def serialize_arguments(self) -> list[ArgumentTypes]:
        """Serialize the arguments to this class"""
        parameters = inspect.get_annotations(self.__init__, eval_str=True)

        arguments: list[ArgumentTypes] = []
        for name, value in self._arguments.items():
            param_type = parameters.get(name)
            match name, value, param_type:
                case _, str() | int() | float() | bool(), _:
                    arguments.append(LiteralArgument(name=name, value=value))

                case _, Reference(), _:
                    model = value.serialize()
                    arguments.append(ReferenceArgument(name=name, id=model.id))

                case "resource", _, inmanta.resources.Resource:
                    arguments.append(ResourceArgument(name=name))

                case _:
                    raise TypeError(f"Unable to serialize argument {name} of {self}")

        return arguments

    def get_argument(self, name: str) -> object:
        """Get an argument from the reference."""
        if name not in self._arguments:
            raise KeyError(f"{type(self).__qualname__} does not have an argument with name {name}")

        arg = self._arguments[name]
        if isinstance(arg, Reference):
            return arg.get()

        return arg

    @property
    def arguments(self) -> collections.abc.Mapping[str, object]:
        return self._arguments


class Mutator(Base):
    """A mutator that has side effects when executed"""

    @abc.abstractmethod
    def run(self) -> None:
        """Execute the mutator"""

    def serialize(self) -> MutatorModel:
        """Emit the correct pydantic objects to serialize the reference in the exporter."""
        if self._model:
            return self._model

        self._model = MutatorModel(type=self.type, args=self.serialize_arguments())
        return self._model


class Reference(Base, typing.Generic[T]):
    """Instances of this class can create references to a value and resolve them."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._reference_value: T
        self._reference_value_cached: bool = False

    @abc.abstractmethod
    def resolve(self) -> T:
        """This method resolves the reference and returns the object that it refers to"""

    def get(self) -> T:
        """Get the value. If we have already resolved it a cached value is returned, otherwise resolve() is called"""
        if not self._reference_value_cached:
            self._reference_value = self.resolve()
            self._reference_value_cached = True

        return self._reference_value

    def serialize(self) -> ReferenceModel:
        """Emit the correct pydantic objects to serialize the reference in the exporter."""
        if self._model:
            return self._model

        self._model = ReferenceModel(type=self.type, args=self.serialize_arguments())
        return self._model

    def _get_T(self) -> type[T]:
        """Get the type of reference that we are"""
        generic_args = [typing.get_args(base)[0] for base in self.__orig_bases__]
        if len(generic_args) == 1:
            return generic_args[0]
        raise AttributeError(f"Unable to determine type of T for {type(self)}")

    def __getattr__(self, name: str) -> object:
        """If our reference is a subclass of Value (dataclass), we return a reference to the
        attribute instead of the attribute itself.

        Note: something similar can be implemented for dict access using __getitem__

        :param name: The name of the attribute to fetch
        :return: A reference to the attribute
        """
        value_type = self._get_T()
        if issubclass(value_type, Value) and name in value_type.__annotations__:
            return AttributeReference(
                resolver=self,
                attribute_name=name,
                attribute_type=value_type.__annotations__[name],
            )
        raise AttributeError(name=name, obj=self)


class ReferencePlaceHolder(Reference[T]):
    """This class is a placeholder that is used during deserialization. Once the entire tree has been deserialized, this
    reference is replaced by the correct one. It inherits from Reference to make typing easier.
    """

    def __init__(self, id: uuid.UUID, references: collections.abc.Mapping[uuid.UUID, Reference]) -> None:
        super().__init__()
        self.id = id
        self.references = references

    def serialize(self) -> ReferenceModel:
        raise ValueError("This reference is a placeholder and should never be serialized.")

    def resolve(self) -> T:
        """Get the value from the correct references"""
        if self.id not in self.references:
            raise ValueError(f"The reference with id {self.id} does not exist.")

        return self.references[self.id].get()


R = typing.TypeVar("R", bound=Reference)


# TODO: we need to make sure that the executor knows it should load the mutator and executor code before running the handler
#       of a resource that uses references.


class reference:
    """This decorator register a reference under a specific name"""

    _reference_classes: typing.ClassVar[dict[str, Reference]] = {}

    def __init__(self, name: str) -> None:
        """
        :param name: This name is used to indicate the type of the reference
        """
        self.name = name

    def __call__(self, cls: type[T]) -> type[T]:
        """Register a new reference. If we already have it explictly delete it (reload)"""
        if self.name in reference._reference_classes:
            del reference._reference_classes[self.name]

        reference._reference_classes[self.name] = cls
        cls.type = self.name
        return cls

    @classmethod
    def get_class(cls, name: str) -> type[Reference]:
        """Get the class of registered with the given name"""
        if name not in cls._reference_classes:
            raise TypeError(f"There is no reference class registered with name {name}")

        return cls._reference_classes[name]

    @classmethod
    def reset(cls) -> None:
        """Reset the registered reference classes"""
        cls._reference_classes = {}


M = typing.TypeVar("M", bound=Mutator)


class mutator:
    """This decorator register a mutator under a specific name"""

    _mutator_classes: typing.ClassVar[dict[str, Mutator]] = {}

    def __init__(self, name: str) -> None:
        """
        :param name: This name is used to indicate the type of the mutator
        """
        self.name = name

    def __call__(self, cls: type[M]) -> type[M]:
        """Register a new mutator. If we already have it explictly delete it (reload)"""
        if self.name in mutator._mutator_classes:
            del mutator._mutator_classes[self.name]

        mutator._mutator_classes[self.name] = cls
        cls.type = self.name
        return cls

    @classmethod
    def get_class(cls, name: str) -> type[Mutator]:
        """Get the class of registered with the given name"""
        if name not in cls._mutator_classes:
            raise TypeError(f"There is no mutator class registered with name {name}")

        return cls._mutator_classes[name]

    @classmethod
    def reset(cls) -> None:
        """Reset the registered mutator classes"""
        cls._mutator_classes = {}


@reference(name="core::AttributeReference")
class AttributeReference(Reference[T]):
    """A reference that points to a value in an attribute"""

    def __init__(
        self,
        resolver: Reference[Value],
        attribute_name: str,
        attribute_type: typing.Type[
            T
        ],  # This allows to have "relations" so we might need to constraint this to primitive types only
    ) -> None:
        super().__init__(resolver=resolver, attribute_name=attribute_name)

    def resolve(self) -> T:
        return getattr(self._resolver.resolve(), self._attribute_name)


@mutator(name="core::Replace")
class ReplaceValue(Mutator):
    """Replace a reference in the provided resource"""

    def __init__(self, resource: "inmanta.resources.Resource", value: Reference[PrimitiveTypes], destination: str) -> None:
        """Change a value in the given resource at the given distination

        :param resource: The resource to replace the value in
        :param value: The value to replace in `resource` at `destination`
        :param destination: A dictpath expression where to replace the value
        """
        super().__init__(resource=resource, value=value, destination=destination)
        self.resource = resource
        self.value = value
        self.destination = destination

    def run(self) -> None:
        value = self.value.get()
        dict_path_expr = dict_path.to_path(self.destination)
        dict_path_expr.set_element(self.resource, value)


def is_reference_of(instance: typing.Optional[object], type_class: type[PrimitiveTypes]) -> bool:
    """Is the given instance a reference to the given type."""
    if instance is None or not isinstance(instance, Reference):
        return False

    generic_args = [typing.get_args(base)[0] for base in instance.__orig_bases__]
    if len(generic_args) == 1:
        return generic_args[0]
    return False
