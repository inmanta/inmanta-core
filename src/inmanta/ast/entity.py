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
import importlib
import inspect
import logging
import typing
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple, Union  # noqa: F401

import inmanta.ast.attribute
from inmanta import plugins
from inmanta.ast import (
    CompilerException,
    DataClassException,
    DataClassMismatchException,
    DuplicateException,
    Locatable,
    Location,
    MultiUnsetException,
    Named,
    Namespace,
    NotFoundException,
    RuntimeException,
    TypingException,
    WithComment,
)
from inmanta.ast.statements.generator import SubConstructor
from inmanta.ast.type import Any as inm_Any
from inmanta.ast.type import Float, NamedType, NullableType, Type
from inmanta.execute.runtime import Instance, QueueScheduler, Resolver, ResultVariable, dataflow
from inmanta.execute.util import AnyType, NoneValue, Unknown
from inmanta.references import AttributeReference, PrimitiveTypes, Reference
from inmanta.types import DataclassProtocol

if TYPE_CHECKING:
    from inmanta.ast import Namespaced
    from inmanta.ast.attribute import Attribute, RelationAttribute  # noqa: F401
    from inmanta.ast.blocks import BasicBlock
    from inmanta.ast.statements import ExpressionStatement, Statement  # noqa: F401
    from inmanta.ast.statements.define import DefineAttribute, DefineImport, DefineIndex  # noqa: F401
    from inmanta.execute.runtime import ExecutionContext  # noqa: F401


LOGGER = logging.getLogger(__name__)


class Entity(NamedType, WithComment):
    """
    This class models a defined entity in the domain model of the configuration model.

    Each entity can contain attributes that are either data types or
    relations and each entity can inherit from parent entities.

    :param name: The name of this entity. This name can not be changed
        after this object has been created
    """

    def __init__(self, name: str, namespace: Namespace, comment: Optional[str] = None) -> None:
        NamedType.__init__(self)

        self.__name = name  # type: str

        self.__namespace = namespace

        self.parent_entities = []  # type: List[Entity]
        self.child_entities = []  # type: List[Entity]
        self._attributes = {}  # type: Dict[str,Attribute]

        self.implementations = []  # type: List[Implementation]
        self.implements = []  # type: List[Implement]
        self.implements_inherits = False

        # default values
        self.__default_values = {}  # type: Dict[str, DefineAttribute]

        self._index_def = []  # type: List[List[str]]
        self._indexes = []  # type: list[DefineIndex]
        self._index = {}  # type: Dict[str,Instance]
        self.index_queue = {}  # type: Dict[str,List[Tuple[ResultVariable, Statement]]]

        self._instance_list = set()  # type: Set[Instance]

        self.comment = comment

        self.normalized = False

        self._paired_dataclass: type[DataclassProtocol] | None = None
        self._paired_dataclass_field_types: dict[str, Type] = {}
        # Entities can be paired up to python dataclasses
        # If such a sibling exists, the type is kept here
        # Every instance of such entity can cary the associated python object in a slot called `DATACLASS_SELF_FIELD`

    def is_entity(self) -> bool:
        return True

    def normalize(self) -> None:
        self.normalized = True
        for attribute in self.__default_values.values():
            if attribute.default is not None:
                default_type: Type = attribute.type.get_type(self.namespace)
                try:
                    default_type.validate(attribute.default.as_constant())
                except RuntimeException as exception:
                    if exception.stmt is None or isinstance(exception.stmt, Type):
                        exception.set_statement(attribute)
                        exception.location = attribute.location
                    raise exception

        # check for duplicate relations in parent entities
        for name, my_attribute in self.get_attributes().items():
            if isinstance(my_attribute, inmanta.ast.attribute.RelationAttribute):
                for parent in self.parent_entities:
                    parent_attr = parent.get_attribute(name)
                    if parent_attr is not None:
                        raise DuplicateException(
                            my_attribute,
                            parent_attr,
                            f"Attribute name {name} is already defined in {parent_attr.entity.name},"
                            " unable to define relationship",
                        )

        # normalize implements but not implementations because they contain subblocks that require full type normalization first
        for i in self.implements:
            i.normalize()

        self.subc = [SubConstructor(self, i) for i in self.get_implements()]
        for sub in self.subc:
            sub.normalize()

        if self._paired_dataclass:
            self.pair_dataclass()

    def get_sub_constructor(self) -> list[SubConstructor]:
        return self.subc

    def get_implements(self) -> "List[Implement]":
        if self.implements_inherits:
            return self.implements + [i for p in self.parent_entities for i in p.get_implements()]
        else:
            return self.implements

    def add_default_value(self, name: str, value: "DefineAttribute") -> None:
        """
        Add a default value for an attribute
        """
        self.__default_values[name] = value

    def _get_own_defaults(self) -> "Dict[str, Optional[ExpressionStatement]]":
        return {k: v.default for k, v in self.__default_values.items() if v.default is not None or v.remove_default}

    def get_namespace(self) -> Namespace:
        """
        The namespace of this entity
        """
        return self.__namespace

    namespace = property(get_namespace)

    def __hash__(self) -> "int":
        """
        The hashcode of this entity is defined as the hash of the name
        of this entity
        """
        return hash(self.__name)

    def get_name(self) -> str:
        """
        Return the name of this entity. The name string has been
        internalised for faster dictionary lookups
        """
        return self.__name

    name = property(get_name)

    def get_full_name(self) -> str:
        """
        Get the full name of the entity
        """
        return self.__namespace.get_full_name() + "::" + self.__name

    def get_attributes(self) -> "Dict[str,Attribute]":
        """
        Get a set with all attributes that are defined in this entity
        """
        return self._attributes

    def set_attributes(self, attributes: "Dict[str,Attribute]") -> None:
        """
        Set a set of attributes that are defined in this entities
        """
        self._attributes = attributes

    attributes: "Dict[str,Attribute]" = property(get_attributes, set_attributes, None, None)

    def is_parent(self, parent_candidate: "Entity") -> bool:
        """
        Check if the given parent_candidate entity is a parent of this entity. Does not consider an entity its own parent.
        """
        if parent_candidate in self.parent_entities:
            return True
        else:
            for parent in self.parent_entities:
                if parent.is_parent(parent_candidate):
                    return True
        return False

    def get_all_parent_names(self) -> "List[str]":
        """
        Get a set with all parents of this entity
        """
        parents = [str(x) for x in self.parent_entities]
        for entity in self.parent_entities:
            parents.extend(entity.get_all_parent_names())

        return parents

    def get_all_parent_entities(self) -> "Set[Entity]":
        parents = [x for x in self.parent_entities]
        for entity in self.parent_entities:
            parents.extend(entity.get_all_parent_entities())
        return set(parents)

    def get_all_child_entities(self) -> "Set[Entity]":
        children = [x for x in self.child_entities]
        for entity in self.child_entities:
            children.extend(entity.get_all_child_entities())
        return set(children)

    def get_all_attribute_names(self) -> "List[str]":
        """
        Return a list of all attribute names, including parents
        """
        names = list(self._attributes.keys())

        for parent in self.parent_entities:
            names.extend(parent.get_all_attribute_names())

        return names

    def add_attribute(self, attribute: "Attribute") -> None:
        """
        Add an attribute to this entity. The attribute should not exist yet.
        """
        if attribute.name not in self._attributes:
            self._attributes[attribute.name] = attribute
        else:
            raise DuplicateException(
                self._attributes[attribute.name],
                attribute,
                "attribute '%s' already exists on entity '%s'" % (attribute.name, self.name),
            )

    def get_attribute(self, name: str) -> Optional["Attribute"]:
        """
        Get the attribute with the given name
        """
        if name in self._attributes:
            return self._attributes[name]
        else:
            for parent in self.parent_entities:
                attr = parent.get_attribute(name)
                if attr is not None:
                    return attr
        return None

    def has_attribute(self, attribute: str) -> bool:
        """
        Does the attribute already exist in this entity.
        """
        if attribute not in self._attributes:
            for parent in self.parent_entities:
                if parent.has_attribute(attribute):
                    return True

            return False
        else:
            return True

    def get_all_instances(self) -> "List[Instance]":
        """
        Return all instances of this entity
        """
        return list(self._instance_list)

    def add_instance(self, obj: "Instance") -> None:
        """
        Register a new instance
        """
        self._instance_list.add(obj)
        self.add_to_index(obj)

        for parent in self.parent_entities:
            parent.add_instance(obj)

    def get_instance(
        self,
        attributes: dict[str, object],
        resolver: Resolver,
        queue: QueueScheduler,
        location: Location,
        node: Optional[dataflow.InstanceNodeReference] = None,
    ) -> "Instance":
        """
        Return an instance of the class defined in this entity.
        If the corresponding node is not None, passes it on the instance.
        """
        out = Instance(self, resolver, queue, node)
        out.set_location(location)
        for k, v in attributes.items():
            out.set_attribute(k, v, location)

        self.add_instance(out)
        return out

    def is_subclass(self, superclass_candidate: "Entity", *, strict: bool = True) -> bool:
        """
        Check if self is a subclass of the given superclass_candidate.
        Does not consider entities a subclass of themselves in strict mode (the default).

        :param strict: Only return True for entities that are a strict subtype, i.e. not of the same type.
        """
        return (not strict and superclass_candidate == self) or self.is_parent(superclass_candidate)

    def issubtype(self, other: "Type") -> bool:
        if isinstance(other, Entity):
            return self.is_subclass(other, strict=False)
        return other.issupertype(self)

    def validate(self, value: object) -> bool:
        """
        Validate the given value
        """
        if isinstance(value, AnyType):
            return True

        if not isinstance(value, Instance):
            raise RuntimeException(None, f"Invalid type for value '{value}', should be type {self}")

        value_definition = value.type
        if not (value_definition is self or value_definition.is_subclass(self)):
            raise RuntimeException(None, f"Invalid class type for {value}, should be {self}")

        # Note on references:
        #
        # References to dataclasses are a special case in the sense that they are represented as plain instances in the DSL.
        # Their attributes get additional runtime validation on the boundary (see to_python()), so we can simply let them
        # pass validation here.
        #
        # Even non-reference instances may contain reference attributes so they get additional runtime validation
        # on plugin attribute access (see DynamicProxy.__getattr__). So these can be accepted here as well.

        return True

    def add_implementation(self, implement: "Implementation") -> None:
        """
        Register an implementation for this entity
        """
        self.implementations.append(implement)

    def add_implement(self, implement: "Implement") -> None:
        """
        Register an implementation for this entity
        """
        self.implements.append(implement)

    def __repr__(self) -> str:
        """
        The representation of this type
        """
        return "Entity(%s)" % (self.get_full_name())

    def __str__(self) -> str:
        """
        The pretty string of this type
        """
        return self.get_full_name()

    def __eq__(self, other: object) -> bool:
        """
        Override list eq method
        """
        if not isinstance(other, Entity):
            return False

        return self.name == other.name and self.namespace == other.namespace

    def add_index(self, attributes: list[str], index_def: "DefineIndex") -> None:
        """
        Add an index over the given attributes.
        """
        # duplicate check
        for index in self._index_def:
            if len(index) == len(attributes) and all((a == b for a, b in zip(index, attributes))):
                return

        self._index_def.append(sorted(attributes))
        self._indexes.append(index_def)
        for child in self.child_entities:
            child.add_index(attributes, index_def)

    def get_indices(self) -> list[list[str]]:
        return self._index_def

    def add_to_index(self, instance: Instance) -> None:
        """
        Update indexes based on the instance and the attribute that has
        been set
        """

        def index_value_gate(key: str, value: object) -> str:
            if isinstance(value, Reference):
                raise TypingException(
                    None,
                    f"Invalid value `{value}` in index for attribute {key} on instance {instance}: "
                    f"references can not be used in indexes.",
                )
            return repr(value)

        attributes = {k: v for k, v in instance.slots.items() if v.is_ready()}

        # check if an index entry can be added
        for index_attributes in self.get_indices():
            index_ok = True
            key = []
            for attribute in index_attributes:
                if attribute not in attributes:
                    index_ok = False
                else:
                    key.append(f"{attribute}={index_value_gate(attribute, attributes[attribute].get_value())}")

            if index_ok:
                keys = ", ".join(key)

                if keys in self._index and self._index[keys] is not instance:
                    raise DuplicateException(instance, self._index[keys], "Duplicate key in index. %s" % keys)

                self._index[keys] = instance

                if keys in self.index_queue:
                    for x, stmt in self.index_queue[keys]:
                        x.set_value(instance, stmt.location)
                    self.index_queue.pop(keys)

    def lookup_index(
        self, params: "List[Tuple[str,object]]", stmt: "Statement", target: "Optional[ResultVariable]" = None
    ) -> "Optional[Instance]":
        """
        Search an instance in the index.
        """
        all_attributes: list[str] = [x[0] for x in params]
        attributes: set[str] = set()
        for attr in all_attributes:
            if attr in attributes:
                raise RuntimeException(stmt, "Attribute %s provided twice in index lookup" % attr)
            attributes.add(attr)

        found_index = False
        for index_attributes in self.get_indices():
            if set(index_attributes) == attributes:
                found_index = True

        if not found_index:
            raise NotFoundException(
                stmt, self.get_full_name(), "No index defined on %s for this lookup: " % self.get_full_name() + str(params)
            )

        def coerce(key: str, t: Type, v: object) -> object:
            """
            Coerce float-typed values to float (e.g. 1 -> 1.0)
            """
            if isinstance(v, Reference):
                raise TypingException(
                    None, f"Invalid value `{v}` in index for attribute {key}: " f"references can not be used in indexes."
                )

            match t:
                case Float():
                    return t.cast(v)
                case NullableType(element_type=Float() as float):
                    return v if isinstance(v, NoneValue) else float.cast(v)
                case _:
                    return v

        key = ", ".join(
            [
                "%s=%s"
                % (
                    k,
                    repr(coerce(k, self.get_attribute(k).type, v)),
                )
                for k, v in sorted(params, key=lambda x: x[0])
            ]
        )
        if target is None:
            if key in self._index:
                return self._index[key]
            else:
                return None
        elif key in self._index:
            target.set_value(self._index[key], stmt.location)
        else:
            if key in self.index_queue:
                self.index_queue[key].append((target, stmt))
            else:
                self.index_queue[key] = [(target, stmt)]
        return None

    def get_default_values(self) -> "Dict[str,ExpressionStatement]":
        """
        Return the dictionary with default values
        """
        values = []  # type: List[Tuple[str,Optional[ExpressionStatement]]]

        # left most parent takes precedence
        for parent in reversed(self.parent_entities):
            values.extend(parent.get_default_values().items())

        # self takes precedence
        values.extend(self._get_own_defaults().items())
        # make dict, remove doubles
        dvalues = dict(values)
        # remove erased defaults
        return {k: v for k, v in dvalues.items() if v is not None}

    def get_default(self, name: str) -> "ExpressionStatement":
        """
        Get a default value for a given name
        """
        defaults = self.get_default_values()
        if name not in defaults:
            raise AttributeError(name)
        return defaults[name]

    def final(self, excns: list[CompilerException]) -> None:
        for key, indices in self.index_queue.items():
            for _, stmt in indices:
                excns.append(NotFoundException(stmt, key, f"No match in index on type {self.get_full_name()} with key {key}"))
        for _, attr in self.get_attributes().items():
            attr.final(excns)

    def get_double_defined_exception(self, other: "Namespaced") -> "DuplicateException":
        return DuplicateException(self, other, "Entity %s is already defined" % (self.get_full_name()))

    def get_location(self) -> Location:
        return self.location

    def pair_dataclass_stage1(self) -> None:
        """
        Attach the associated dataclass in the python domain

        should only be called on children of std::Dataclass

        Called early to make plugins able to resolve this type from python domain
        """
        # Find the dataclass name
        namespace = self.namespace.get_full_name()
        module_name = "inmanta_plugins." + namespace.replace("::", ".")
        # Find the dataclass
        dataclass_module = importlib.import_module(module_name)
        dataclass_raw = getattr(dataclass_module, self.name, None)
        self._paired_dataclass = dataclass_raw
        if dataclass_raw is not None:
            dataclass_raw._paired_inmanta_entity = self

    def pair_dataclass(self) -> None:
        """
        Validate the associated dataclass in the python domain

        should only be called on children of std::Dataclass
        should be called after normalization
        """
        assert self.normalized

        namespace = self.namespace.get_full_name()
        module_name = "inmanta_plugins." + namespace.replace("::", ".")
        dataclass_name = module_name + "." + self.name

        dataclass_raw = self._paired_dataclass
        if dataclass_raw is None:
            raise DataClassMismatchException(
                self,
                None,
                dataclass_name,
                f"The dataclass {self.get_full_name()} defined at {self.location} has no corresponding python dataclass. "
                "Dataclasses must have a python counterpart that is a frozen dataclass.",
            )

        if not dataclasses.is_dataclass(dataclass_raw):
            raise DataClassMismatchException(
                self,
                None,
                dataclass_name,
                f"The python object {module_name}.{dataclass_raw.__name__} associated to  {self.get_full_name()} "
                f"defined at {self.location} is not a dataclass. "
                "Dataclasses must have a python counterpart that is a frozen dataclass.",
            )
        dataclass: type[DataclassProtocol] = dataclass_raw
        if not dataclass.__dataclass_params__.frozen:
            raise DataClassMismatchException(
                self,
                None,
                dataclass_name,
                f"The python object {module_name}.{dataclass.__name__} associated to  {self.get_full_name()} "
                f"defined at {self.location} is not frozen. "
                "Dataclasses must have a python counterpart that is a frozen dataclass.",
            )

        # Validate fields, collect errors
        dc_fields = {f.name: f for f in dataclasses.fields(dataclass)}
        dc_types = typing.get_type_hints(dataclass)
        failures = []

        for rel_or_attr_name in self.get_all_attribute_names():
            rel_or_attr = self.get_attribute(rel_or_attr_name)
            match rel_or_attr:
                case inmanta.ast.attribute.RelationAttribute() as rel:
                    # No relations except for requires and provides
                    if not (rel.entity.get_full_name() == "std::Entity" and rel.name in ["requires", "provides"]):
                        failures.append(
                            f"a relation called {rel_or_attr_name} is defined at {rel.location}. "
                            "Dataclasses are not allowed to have relations"
                        )
                case inmanta.ast.attribute.Attribute() as attr:
                    if rel_or_attr_name not in dc_fields:
                        failures.append(
                            f"The attribute {rel_or_attr_name} has no counterpart in the python domain. "
                            "All attributes of a dataclasses must be identical in both the python and inmanta domain.",
                        )
                        continue
                    inm_type = attr.type_internal

                    # all own fields are primitive
                    if not inm_type.is_attribute_type():
                        failures.append(
                            f"The attribute {rel_or_attr_name} of type `{inm_type}` is not primitive. "
                            "All attributes of a dataclasses have to be of a primitive type.",
                        )
                        continue

                    dc_fields.pop(rel_or_attr_name)
                    # Type correspondence
                    try:
                        dsl_type = plugins.to_dsl_type(dc_types[rel_or_attr_name], self.location, self.namespace)
                        self._paired_dataclass_field_types[rel_or_attr_name] = dsl_type
                        if not inm_type.corresponds_to(dsl_type):
                            failures.append(
                                f"The attribute {rel_or_attr_name} does not have the same type as "
                                "the associated field in the python domain. "
                                "All attributes of a dataclasses must be identical in both the python and inmanta domain.",
                            )
                    except TypingException:
                        # Can't even convert the type
                        failures.append(
                            f"The attribute {rel_or_attr_name} does not have the same type as "
                            "the associated field in the python domain. "
                            "All attributes of a dataclasses must be identical in both the python and inmanta domain.",
                        )

        # Anything left in the dict has no counterpart
        for dcfield in dc_fields.keys():
            failures.append(
                f"The field {dcfield} doesn't exist in the inmanta domain. "
                "All attributes of a dataclasses must be identical in both the python and inmanta domain",
            )

        if failures:
            python_file = inspect.getfile(dataclass)
            _, python_lnr = inspect.getsourcelines(dataclass)
            msgs = "\n".join(" " * 4 + "-" + failure for failure in failures)
            raise DataClassMismatchException(
                self,
                dataclass,
                dataclass_name,
                f"The dataclass {self.get_full_name()} defined at {self.location} does not match"
                f" the corresponding python dataclass at {python_file}:{python_lnr}. {len(failures)} errors:\n" + msgs + "\n",
            )

        # Only std::none as implementation
        for implement in self.get_implements():
            for imp in implement.implementations:
                if imp.get_full_name() != "std::none":
                    raise DataClassException(
                        self,
                        f"The dataclass {self.get_full_name()} defined at {self.location} "
                        f"has an implementation other than 'std::none', defined at {implement.location}. "
                        "Dataclasses can only have std::none as implemenation.",
                    )
        # No index
        if self.get_indices():
            index_locations = ",".join([str(i.location) for i in self._indexes])
            raise DataClassException(
                self,
                f"The dataclass {self.get_full_name()} defined at {self.location} has an indexes "
                f"defined at {index_locations}. Dataclasses can not have any indexes.",
            )

    def get_paired_dataclass(self) -> Optional[type[object]]:
        return self._paired_dataclass

    def corresponds_to(self, type: Type) -> bool:
        if isinstance(type, inm_Any):
            return True
        return type is self

    def as_python_type_string(self) -> "str | None":
        if self._paired_dataclass is None:
            return None
        namespace = self.namespace.get_full_name()
        module_name = "inmanta_plugins." + namespace.replace("::", ".")
        dataclass_name: str = module_name + "." + self.name
        return dataclass_name

    def has_custom_to_python(self) -> bool:
        return self._paired_dataclass is not None

    def to_python(self, instance: object, *, path: str) -> object:
        if self._paired_dataclass is None:
            assert False, f"This class {self.get_full_name()} has no associated python type, this conversion is not supported"

        assert isinstance(instance, Instance)

        if instance.type is not self:
            # allow inheritance: delegate to child type
            return instance.type.to_python(instance, path=path)

        def domain_conversion(value: object, *, field_name: str) -> object:
            if isinstance(value, Unknown):
                # For now, we simply reject unknowns. Eventually, we want to support `| Unknown` declaration, similar to what
                # we allow for references. When we do, it will have to be integrated into `Type.validate()` rather than here
                # during conversion. One of the blockers is consistency with unknowns in plugin arguments, and how to gradually
                # migrate from the old `allow_unknowns: bool` to the new, more fine-grained unknown declaration.
                raise TypingException(
                    None,
                    (
                        f"Encountered unknown in field {field_name!r}."
                        " Unknowns are not currently supported in dataclass instances in the Python domain."
                    ),
                )
            if isinstance(value, NoneValue):
                return None
            if isinstance(value, list):
                return [domain_conversion(v, field_name=field_name) for v in value]
            if isinstance(value, dict):
                return {k: domain_conversion(v, field_name=field_name) for k, v in value.items()}
            return value

        def create() -> object:
            # Convert values
            # All values are primitive, so this is trivial
            kwargs = {k: v.get_value() for k, v in instance.slots.items() if k not in ["self", "requires", "provides"]}
            for k, v in kwargs.items():
                assert k in self._paired_dataclass_field_types
                # dynamic validation, mostly in case of references, because they are allowed in the model while they have to be
                # declared (potentially nested) in the Python domain.
                self._paired_dataclass_field_types[k].validate(v)
            assert self._paired_dataclass is not None
            return self._paired_dataclass(**{k: domain_conversion(v, field_name=k) for k, v in kwargs.items()})

        if instance.dataclass_self is None:
            # Handle unsets
            unset = [v for k, v in instance.slots.items() if k not in ["self", "requires", "provides"] if not v.is_ready()]
            if unset:
                raise MultiUnsetException("Unset values when converting instance to dataclass", unset)

            instance.dataclass_self = create()

        if isinstance(instance.dataclass_self, Reference):
            LOGGER.debug(
                "Coercing dataclass reference `%s` to a dataclass with reference attributes to satisfy plugin type constraints",
                instance.dataclass_self,
            )
            # coerce if the dataclass definition is reference-compatible. Do not overwrite dataclass_self
            return create()
        else:
            # or simply return the linked dataclass instance
            return instance.dataclass_self

    def from_python(self, value: object, resolver: Resolver, queue: QueueScheduler, location: Location) -> Instance:
        """
        Construct the instance for the associated python object

        Should only be called on objects of the proper type,
         i.e. for which 'corresponds_to' returns True
         i.e. instances of the associated dataclass
        """
        assert self._paired_dataclass is not None  # make mypy happy

        def convert_none(x: object | None) -> object:
            return x if x is not None else NoneValue()

        def convert_to_attr_ref(name: str) -> AttributeReference[PrimitiveTypes]:
            ar: AttributeReference[PrimitiveTypes] = AttributeReference(
                reference=value,
                attribute_name=name,
            )
            attribute = self.get_attribute(name)
            assert attribute is not None  # Mypy
            ar._model_type = attribute.get_type()
            return ar

        if isinstance(value, Reference):
            instance = self.get_instance(
                {k.name: convert_to_attr_ref(k.name) for k in dataclasses.fields(self._paired_dataclass)},
                resolver,
                queue,
                location,
                None,
            )
        else:
            instance = self.get_instance(
                {k.name: convert_none(getattr(value, k.name)) for k in dataclasses.fields(value)},
                resolver,
                queue,
                location,
                None,
            )

        instance.dataclass_self = value
        # generate an implementation
        for stmt in self.get_sub_constructor():
            stmt.emit(instance, queue)
        return instance


class Implementation(NamedType):
    """
    A module functions as a grouping of objects. This can be used to create
    high level roles that do not have any arguments, or they can be used
    to create mixin like aspects.
    """

    def __init__(
        self, name: str, stmts: "BasicBlock", namespace: Namespace, target_type: str, comment: Optional[str] = None
    ) -> None:
        Named.__init__(self)
        self.name = name
        self.statements = stmts
        self.namespace = namespace
        self.target_type = target_type
        self.comment = comment

    def set_type(self, entity: Entity) -> None:
        self.entity = entity
        entity.add_implementation(self)

    def __repr__(self) -> str:
        return "Implementation(name = %s)" % self.name

    def normalize(self) -> None:
        try:
            self.statements.normalize()
        except RuntimeException as e:
            e.set_statement(self, False)
            raise
        except CompilerException as e:
            e.set_location(self.location)
            raise

    def get_full_name(self) -> str:
        return self.namespace.get_full_name() + "::" + self.name

    def get_namespace(self) -> Namespace:
        return self.namespace

    def get_double_defined_exception(self, other: "Namespaced") -> "DuplicateException":
        raise DuplicateException(
            self, other, f"Implementation {self.get_full_name()} for type {self.target_type} is already defined"
        )

    def get_location(self) -> Location:
        return self.location

    def as_python_type_string(self) -> "str | None":
        raise NotImplementedError("Implementations should not be arguments to plugins, this code is not expected to be called")

    def corresponds_to(self, type: Type) -> bool:
        raise NotImplementedError("Implementations should not be arguments to plugins, this code is not expected to be called")

    def to_python(self, instance: object, *, path: str) -> object:
        raise NotImplementedError("Implementations should not be arguments to plugins, this code is not expected to be called")


class Implement(Locatable):
    """
    Define an implementation of an entity in functions of implementations
    """

    comment: Optional[str]

    def __init__(self) -> None:
        Locatable.__init__(self)
        self.constraint = None  # type: ExpressionStatement
        self.implementations = []  # type: List[Implementation]
        self.comment = None  # type: str
        self.normalized = False

    def normalize(self) -> None:
        if self.normalized:
            return
        self.normalized = True
        self.constraint.normalize()
