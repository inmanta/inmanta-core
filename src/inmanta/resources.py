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

import logging
import re
import typing
import uuid
from collections.abc import Iterable, Iterator, Sequence
from typing import TYPE_CHECKING, Any, Callable, Optional, Union, cast

import inmanta.ast
import inmanta.util
from inmanta import const, references
from inmanta.execute import proxy, util
from inmanta.stable_api import stable_api
from inmanta.types import JsonType, ResourceIdStr, ResourceVersionIdStr

if TYPE_CHECKING:
    from inmanta import export
    from inmanta.agent import handler
    from inmanta.data import ResourceAction
    from inmanta.execute import runtime

LOGGER = logging.getLogger(__name__)


class ResourceException(Exception):
    pass


@stable_api
class resource:  # noqa: N801
    """
    A decorator that registers a new resource. The decorator must be applied to classes that inherit from
    :class:`~inmanta.resources.Resource`

    :param name: The name of the entity in the configuration model it creates a resource from. For example
        :inmanta:entity:`std::testing::NullResource`
    :param id_attribute: The attribute of `this` resource that uniquely identifies a resource on a logical agent.
        This attribute can be mapped.
    :param agent: This string indicates how the agent of this resource is determined. This string points to an attribute,
        but it can navigate relations (this value cannot be mapped). For example, the agent argument could be ``host.name``.
    """

    # The _resources dict is accessed by the compile function in pytest-inmanta.
    # see https://github.com/inmanta/pytest-inmanta/pull/381
    _resources: dict[str, tuple[type["Resource"], dict[str, str]]] = {}

    def __init__(self, name: str, id_attribute: str, agent: str):
        if not isinstance(agent, str):
            raise ResourceException(f"The agent parameter has to be a string, got {agent} of type {type(agent)}")
        self._cls_name = name
        self._options = {"agent": agent, "name": id_attribute}

    def __call__[R: Resource](self, cls: type[R]) -> type[R]:
        """
        The wrapping
        """
        if self._cls_name in resource._resources:
            LOGGER.info("Reloading module %s" % self._cls_name)
            del resource._resources[self._cls_name]

        resource._resources[self._cls_name] = (cls, self._options)
        return cls

    @classmethod
    def add_resource(cls, cls_name: str, resource_type: type["Resource"], options: dict[str, str]) -> None:
        cls._resources[cls_name] = (resource_type, options)

    @classmethod
    def validate(cls) -> None:
        fq_name_resource_decorator = f"{cls.__module__}.{cls.__name__}"
        fq_name_resource_class = f"{Resource.__module__}.{Resource.__name__}"
        for resource, _ in cls._resources.values():
            if issubclass(resource, cls):
                # If a Resource inherits from the resource decorator, the server goes into an infinite recursion.
                # Here we make sure the user gets a clear error message (https://github.com/inmanta/inmanta-core/issues/8817).
                fq_name_current_resource = f"{resource.__module__}.{resource.__name__}"
                raise inmanta.ast.RuntimeException(
                    stmt=None,
                    msg=(
                        f"Resource {fq_name_current_resource} is inheriting from the {fq_name_resource_decorator} decorator."
                        f" Did you intend to inherit from {fq_name_resource_class} instead?"
                    ),
                )
            resource.validate()

    @classmethod
    def get_entity_resources(cls) -> Iterable[str]:
        """
        Returns a list of entity types for which a resource has been registered
        """
        return cls._resources.keys()

    @classmethod
    def get_class(cls, name: str) -> tuple[Optional[type["Resource"]], Optional[dict[str, str]]]:
        """
        Get the class definition for the given entity.
        """
        if name in cls._resources:
            return cls._resources[name]

        return (None, None)

    @classmethod
    def get_resources(cls) -> Iterator[tuple[str, type["Resource"]]]:
        """Return an iterator over resource type, resource definition"""
        return (
            (resource_type, resource_definition) for resource_type, (resource_definition, _options) in cls._resources.items()
        )

    @classmethod
    def reset(cls) -> None:
        """
        Clear the list of registered resources
        """
        cls._resources = {}


class ResourceNotFoundExcpetion(Exception):
    """
    This exception is thrown when a resource is not found
    """


@stable_api
class IgnoreResourceException(Exception):
    """
    Throw this exception when a resource should not be included by the exported.
    Typically resources use this to indicate that they are not managed by the orchestrator.
    """


def to_id(entity: "proxy.DynamicProxy") -> Optional[str]:
    """
    Convert an entity instance from the model to its resource id
    """
    entity_name = str(entity._type())
    for cls_name in [entity_name] + entity._type().get_all_parent_names():
        cls, options = resource.get_class(cls_name)

        if cls is not None:
            break

    if cls is not None and options is not None:
        obj_id = cls.object_to_id(entity, cls_name, options["name"], options["agent"])
        return str(obj_id)

    return None


class ResourceMeta(type):
    @classmethod
    def _get_parent_fields(cls, bases: Sequence[type["Resource"]]) -> list[str]:
        fields: list[str] = []
        for base in bases:
            if "fields" in base.__dict__:
                if not isinstance(base.__dict__["fields"], (tuple, list)):
                    raise Exception("fields attribute of %s should be a tuple or list" % base)

                fields.extend(base.__dict__["fields"])

            fields.extend(cls._get_parent_fields(base.__bases__))

        return fields

    def __new__(cls, class_name, bases, dct):
        fields = cls._get_parent_fields(bases)
        if "fields" in dct:
            if not isinstance(dct["fields"], (tuple, list)):
                raise Exception("fields attribute of %s should be a tuple or list" % class_name)

            fields.extend(dct["fields"])

        dct["fields"] = tuple(set(fields))
        return type.__new__(cls, class_name, bases, dct)


RESERVED_FOR_RESOURCE = {"id", "version", "model", "requires", "unknowns", "set_version", "clone", "is_type", "serialize"}


class ReferenceSubCollector:
    """
    A collector for references that:
    1. keeps track of all references it has seen
    2. keeps track of the paths at which these references have been seen
    """

    def __init__(self) -> None:
        self.references: dict[uuid.UUID, references.ReferenceModel] = {}
        self.replacements: dict[str, references.ReferenceModel] = {}

    def collect_reference(self, value: object) -> None:
        """Add a value reference and recursively add any other references."""
        match value:
            case list():
                for v in value:
                    self.collect_reference(v)

            case dict():
                for k, v in value.items():
                    self.collect_reference(v)

            case references.Reference():
                ref = value.serialize()
                self.references[ref.id] = ref
                for arg in value.arguments.values():
                    self.collect_reference(arg)

            case _:
                pass

    def add_reference(self, path: str, reference: "references.Reference[references.PrimitiveTypes]") -> None:
        """Add a new attribute map to a value reference that we found at the given path.

        :param path: The path where the value needs to be inserted
        :param reference: The attribute reference
        """
        self.collect_reference(reference)
        self.replacements[path] = reference.serialize()

    def collect_references(self, value: object, path: str) -> object:
        """
        Collect value references. This method also ensures that there are no values in the resources that are not serializable.
        This includes:
            - Unknowns
            - DynamicProxy


        :param value: The value to recursively find value references on
        :param path: The current path we are working on in the tree
        """

        def allow_references[T](v: T) -> T:
            if isinstance(v, proxy.DynamicProxy):
                # fails on stable mypy, but runs fine on master
                return v._allow_references()
            return v

        match value:
            case list() | proxy.SequenceProxy():
                return [
                    self.collect_references(value, f"{path}[{index}]") for index, value in enumerate(allow_references(value))
                ]

            case dict() | proxy.DictProxy():
                return {
                    key: self.collect_references(value, f"{path}.'{key.replace("'", "\\'")}'")
                    for key, value in allow_references(value).items()
                }

            case references.Reference():
                self.add_reference(path, value)
                return None

            case proxy.DynamicProxy() | util.Unknown():
                raise TypeError(f"{value!r} in resource is not JSON serializable at path {path}")

            case _:
                return value


class ReferenceCollector(ReferenceSubCollector):
    """Collect and organize all references and mutators for a specific resource"""

    def __init__(self, resource: "Resource") -> None:
        super().__init__()
        self.mutators: list[references.MutatorModel] = []
        self.resource = resource

    def add_reference(self, path: str, reference: "references.Reference[references.PrimitiveTypes]") -> None:
        """Add a new attribute map to a value reference that we found at the given path.

        :param path: The path where the value needs to be inserted
        :param reference: The attribute reference
        """
        super().add_reference(path, reference)
        self.mutators.append(
            references.ReplaceValue(
                resource=self.resource,
                value=reference,
                destination=path,
            ).serialize()
        )


@stable_api
class Resource(metaclass=ResourceMeta):
    """
    Plugins should inherit resource from this class so a resource from a model can be serialized and deserialized.

    Such as class is registered when the :func:`~inmanta.resources.resource` decorator is used. Each class needs to indicate
    the fields the resource will have with a class field named "fields". A metaclass merges all fields lists from the class
    itself and all superclasses. If a field it not available directly in the model object the serializer will look for
    static methods in the class with the name "get_$fieldname".
    """

    fields: Sequence[str] = (
        const.RESOURCE_ATTRIBUTE_SEND_EVENTS,
        const.RESOURCE_ATTRIBUTE_RECEIVE_EVENTS,
        const.RESOURCE_ATTRIBUTE_REFERENCES,
        const.RESOURCE_ATTRIBUTE_MUTATORS,
    )
    send_event: bool  # Deprecated field
    model: "proxy.DynamicProxy"
    map: dict[str, Callable[[Optional["export.Exporter"], "proxy.DynamicProxy"], Any]]

    @staticmethod
    def get_send_event(_exporter: "export.Exporter", obj: "Resource") -> bool:
        try:
            return obj.send_event
        except Exception:
            return False

    @staticmethod
    def get_references(_exporter: "export.Exporter", instance: "Resource") -> "typing.Sequence[references.ReferenceModel]":
        """This method is present so the serialization works correctly. This field is set by the serializer"""
        return []

    @staticmethod
    def get_mutators(_exporter: "export.Exporter", instance: "Resource") -> "typing.Sequence[references.MutatorModel]":
        """This method is present so the serialization works correctly. This field is set by the serializer"""
        return []

    @staticmethod
    def get_receive_events(_exporter: "export.Exporter", obj: "Resource") -> bool:
        try:
            return obj.receive_events
        except Exception:
            # default to True for backward compatibility (all resources used to receive events)
            return True

    @classmethod
    def convert_requires(
        cls, resources: dict["runtime.Instance", "Resource"], ignored_resources: set["runtime.Instance"]
    ) -> None:
        """
        Convert all requires

        :param resources: A dict with a mapping from model objects to resource objects
        :param ignored_resources: A set of model objects that have been ignored (and not converted to resources)
        """
        for res in resources.values():
            final_requires: set["Resource"] = set()
            initial_requires: list["runtime.Instance"] = [x for x in res.model.requires]

            for r in initial_requires:
                if r in resources:
                    final_requires.add(resources[r])

            if len(final_requires) == 0 and not len(initial_requires) == 0:
                for r in initial_requires:
                    # do not warn about resources that either contain unknowns or are ignored
                    if r in ignored_resources:
                        initial_requires.remove(r)

                if len(initial_requires) > 0:
                    LOGGER.warning(
                        "The resource %s had requirements before flattening, but not after flattening."
                        " Initial set was %s. Perhaps provides relation is not wired through correctly?",
                        res,
                        initial_requires,
                    )

            res.resource_requires = final_requires
            res.requires = {x.id for x in final_requires}

    @classmethod
    def object_to_id(
        cls, model_object: "proxy.DynamicProxy", entity_name: str, attribute_name: str, agent_attribute: str
    ) -> "Id":
        """
        Convert the given object to a textual id

        :param model_object: The object to convert to an id
        :param entity_name: The entity type
        :param attribute_name: The name of the attribute that uniquely identifies the entity
        :param agent_attribute: The "path" to the attribute that defines the agent
        """
        # first get the agent attribute
        path_elements: list[str] = agent_attribute.split(".")
        agent_value = model_object
        for i, el in enumerate(path_elements):
            try:
                # TODO cleanup this hack
                if isinstance(agent_value, list):
                    agent_value = agent_value[0]

                agent_value = getattr(agent_value, el)

            except inmanta.ast.UnexpectedReference:
                # Clean up exception
                current_path: str = ".".join(path_elements[: i + 1])
                raise ResourceException(
                    "Encountered reference in resource's agent attribute. Agent attribute values can not be references."
                    f" Encountered at attribute {current_path!r} of resource instance {model_object}"
                )
            except (ResourceException, inmanta.ast.UnsetException, inmanta.ast.UnknownException):
                raise
            except Exception:
                raise Exception(
                    "Unable to get the name of agent %s belongs to. In path %s, '%s' does not exist"
                    % (model_object, agent_attribute, el)
                )
        try:
            attribute_value = cls.map_field(None, entity_name, attribute_name, model_object)
        except inmanta.ast.UnexpectedReference:
            # Clean up exception
            raise ResourceException(
                "Encountered reference in resource's id attribute. Id attribute values can not be references."
                f" Encountered at attribute {attribute_name!r} of resource instance {model_object}"
            )
        if isinstance(attribute_value, util.Unknown):
            raise inmanta.ast.UnknownException(attribute_value)
        if not isinstance(agent_value, str):
            raise ResourceException(
                f"The agent attribute should lead to a string, got {agent_value} of type {type(agent_value)}"
            )

        # agent_value is no longer a proxy.DynamicProxy here, force this for mypy validation
        return Id(entity_name, str(agent_value), attribute_name, str(attribute_value))

    @classmethod
    def map_field(
        cls,
        exporter: Optional["export.Exporter"],
        entity_name: str,
        field_name: str,
        model_object: "proxy.DynamicProxy",
        reference_collector: Optional[ReferenceCollector] = None,
    ) -> object:
        """
        Map a field name to its value.

        :param reference_collector: Collector for references. If None, references may be returned, even if they can not
            be serialized later on. The caller is responsible for validating appropriately.
        """
        try:
            if hasattr(cls, "get_" + field_name):
                mthd = getattr(cls, "get_" + field_name)
                value = mthd(exporter, model_object)
            elif hasattr(cls, "map") and field_name in cls.map:
                value = cls.map[field_name](exporter, model_object)
            else:
                value = getattr(model_object, field_name)

            # walk the entire model to find any value references. Additionally we also want to make sure we raise exceptions on:
            # - Unknowns
            # - DynamicProxys to entities
            # - References if we don't have a reference_collector
            if reference_collector is not None:
                value = reference_collector.collect_references(value, field_name)

            return value
        except IgnoreResourceException:
            raise  # will be handled in _load_resources of export.py
        except inmanta.ast.UnknownException as e:
            return e.unknown
        except inmanta.ast.PluginException as e:
            raise inmanta.ast.ExplicitPluginException(
                None, f"Failed to get attribute '{field_name}' for export on '{entity_name}'", e
            )
        except inmanta.ast.CompilerException:
            # Internal exceptions (like UnsetException) should be propagated without being wrapped
            # as they are used later on and wrapping them would break the compiler
            raise
        except Exception as e:
            raise inmanta.ast.ExternalException(
                None, f"Failed to get attribute '{field_name}' for export on '{entity_name}'", e
            )

    @classmethod
    def create_from_model(cls, exporter: "export.Exporter", entity_name: str, model_object: "proxy.DynamicProxy") -> "Resource":
        """
        Build a resource from a given configuration model entity
        """
        resource_cls, options = resource.get_class(entity_name)

        if resource_cls is None or options is None:
            raise TypeError("No resource class registered for entity %s" % entity_name)

        # build the id of the object
        obj_id = resource_cls.object_to_id(model_object, entity_name, options["name"], options["agent"])
        obj = resource_cls(obj_id)

        with proxy.exportcontext:
            # map all fields
            reference_collector = ReferenceCollector(obj)
            fields: dict[str, object] = {
                field: resource_cls.map_field(exporter, entity_name, field, model_object, reference_collector)
                for field in resource_cls.fields
            }

        fields[const.RESOURCE_ATTRIBUTE_REFERENCES] = list(reference_collector.references.values())
        fields[const.RESOURCE_ATTRIBUTE_MUTATORS] = reference_collector.mutators

        obj.populate(fields)
        obj.model = model_object

        return obj

    @classmethod
    def deserialize(cls, obj_map: JsonType) -> "Resource":
        """Deserialize the resource from the given dictionary

        :param obj_map: The json structure that represents all fields of the resource
        """
        obj_id = Id.parse_id(obj_map["id"])
        cls_resource, _options = resource.get_class(obj_id.entity_type)

        force_fields = False
        if cls_resource is None:
            raise TypeError("No resource class registered for entity %s" % obj_id.entity_type)

        # backward compatibility for resources that were exported and stored in serialized form before these fields were
        # introduced:
        # - receive_events
        # - references
        # - mutators
        extra: dict[str, object] = {}
        if const.RESOURCE_ATTRIBUTE_RECEIVE_EVENTS not in obj_map:
            extra[const.RESOURCE_ATTRIBUTE_RECEIVE_EVENTS] = True

        if (
            const.RESOURCE_ATTRIBUTE_MUTATORS not in obj_map
            or obj_map[const.RESOURCE_ATTRIBUTE_MUTATORS] is None
            or const.RESOURCE_ATTRIBUTE_REFERENCES not in obj_map
            or obj_map[const.RESOURCE_ATTRIBUTE_REFERENCES] is None
        ):
            extra[const.RESOURCE_ATTRIBUTE_MUTATORS] = []
            extra[const.RESOURCE_ATTRIBUTE_REFERENCES] = []

        if extra:
            obj_map = {**obj_map, **extra}

        obj = cls_resource(obj_id)
        obj.populate(obj_map, force_fields)
        return obj

    @classmethod
    def validate(cls) -> None:
        for field in cls.fields:
            if field.startswith("_"):
                raise ResourceException("Resource field names can not start with _, reported in %s" % cls.__name__)
            if field in RESERVED_FOR_RESOURCE:
                raise ResourceException(
                    f"Resource {field} is a reserved keyword and not a valid field name, reported in {cls.__name__}"
                )

    def __init__(self, _id: "Id") -> None:
        self.id = _id
        self.requires: set[Id] = set()
        self.resource_requires: set[Resource] = set()
        self.unknowns: set[str] = set()

        if not hasattr(self.__class__, "fields"):
            raise Exception("A resource should have a list of fields")

        for field in self.__class__.fields:
            setattr(self, field, None)

        self.version = _id.version

        self._references_model: dict[uuid.UUID, references.ReferenceModel] = {}
        self._references: dict[uuid.UUID, references.Reference[references.RefValue]] = {}
        self._resolved = False

    def get(self, key: str, default: object = None) -> object:
        if key in self.fields:
            return getattr(self, key)
        return default

    def __getitem__(self, key: str) -> object:
        """Support dict like access on the resource"""
        if key in self.fields:
            return getattr(self, key)

        raise KeyError()

    def __contains__(self, item: str) -> object:
        return item in self.fields

    def __setitem__(self, key: str, value: object) -> None:
        """Support dict like access on the resource. It is not possible to create new
        attributes using setitem
        """
        if key in self.fields:
            return setattr(self, key, value)

        raise KeyError()

    def __delitem__(self, key: str) -> None:
        raise Exception("Deleting fields is not allowed on a resource")

    def clear(self) -> None:
        raise Exception("Deleting fields is not allowed on a resource")

    def items(self) -> Iterator[tuple[str, object]]:
        for key in self.fields:
            yield key, getattr(self, key)

    def get_reference_value(self, id: uuid.UUID, logger: "handler.LoggerABC") -> "references.RefValue":
        """Get a value of a reference"""
        if id not in self._references:
            if id not in self._references_model:
                raise KeyError(f"The reference with id {id} is not defined in resource {self.id}")

            model = self._references_model[id]
            ref = references.reference.get_class(model.type).deserialize(model, self, logger)
            self._references[model.id] = ref

        return self._references[id].get(logger)

    def resolve_all_references(self, logger: "handler.LoggerABC") -> None:
        """Resolve all value references"""
        if self._resolved:
            return
        for ref in self.references:  # type: ignore
            if ref.get("id", None) not in self._references_model:
                model = references.ReferenceModel(**ref)
                self._references_model[model.id] = model

        for mutator in self.mutators:  # type: ignore
            mutator = references.mutator.get_class(mutator["type"]).deserialize(
                references.MutatorModel(**mutator), self, logger
            )
            mutator.run(logger)

        self._resolved = True

    def populate(self, fields: dict[str, object], force_fields: bool = False) -> None:
        for field in self.__class__.fields:
            if field in fields or force_fields:
                setattr(self, field, fields[field])
            else:
                raise Exception("Resource with id {} does not have field {}".format(fields["id"], field))

        if "requires" in fields:
            # parse requires into ID's
            for require in fields["requires"]:  # type: ignore
                self.requires.add(Id.parse_id(require))

    def set_version(self, version: int) -> None:
        """Set the version of this resource"""
        self.version = version
        self.id.version = version

    def __setattr__(self, name: str, value: Any) -> None:
        if isinstance(value, util.Unknown):
            self.unknowns.add(name)

        self.__dict__[name] = value

    def __str__(self) -> str:
        return str(self.id)

    def __repr__(self) -> str:
        return str(self)

    def clone[R: Resource](self: R, **kwargs: Any) -> R:
        """
        Create a clone of this resource. The given kwargs can be used to override attributes.

        :return: The cloned resource
        """
        res = Resource.deserialize(self.serialize())
        for k, v in kwargs.items():
            setattr(res, k, v)

        # Resources are copied in the hanlder, the cache has to be retained!
        res._resolved = self._resolved
        # In every case, share caches with child
        res._references = self._references
        res._references_model = self._references_model

        return res

    def serialize(self) -> JsonType:
        """
        Serialize this resource to its dictionary representation
        """
        dictionary: dict[str, Any] = {}

        for field in self.__class__.fields:
            dictionary[field] = getattr(self, field)

        dictionary["requires"] = [str(x) for x in self.requires]
        dictionary["version"] = self.version
        dictionary["id"] = self.id.resource_version_str()

        return dictionary

    def is_type(self, type_name: str) -> bool:
        return str(self.model._get_instance().get_type()) == type_name


@stable_api
class PurgeableResource(Resource):
    """
    See :inmanta:entity:`std::PurgeableResource` for more information.
    """

    fields = ("purged", "purge_on_delete")
    purged: bool
    purge_on_delete: bool


@stable_api
class DiscoveryResource(Resource):
    """
    See :inmanta:entity:`std::DiscoveryResource` for more information.
    """

    fields = ()


@stable_api
class ManagedResource(Resource):
    """
    See :inmanta:entity:`std::ManagedResource` for more information.
    """

    fields = ("managed",)

    managed: bool

    @staticmethod
    def get_managed(exporter: "export.Exporter", obj: "ManagedResource") -> bool:
        if not obj.managed:
            raise IgnoreResourceException()
        return obj.managed


PARSE_ID_REGEX = re.compile(
    r"^(?P<id>(?P<type>(?P<ns>[\w-]+(::[\w-]+)*)::(?P<class>[\w-]+))\[(?P<hostname>[^,]+),"
    r"(?P<attr>[^=]+)=(?P<value>[^\]]+)\])(,v=(?P<version>[0-9]+))?$"
)

PARSE_RVID_REGEX = re.compile(
    r"^(?P<id>(?P<type>(?P<ns>[\w-]+(::[\w-]+)*)::(?P<class>[\w-]+))\[(?P<hostname>[^,]+),"
    r"(?P<attr>[^=]+)=(?P<value>[^\]]+)\]),v=(?P<version>[0-9]+)$"
)


@stable_api
class Id:
    """
    A unique id that identifies a resource that is managed by an agent
    """

    def __init__(self, entity_type: str, agent_name: str, attribute: str, attribute_value: str, version: int = 0) -> None:
        """
        :attr entity_type: The resource type, as defined in the configuration model.
            For example :inmanta:entity:`std::testing::NullResource`.
        :attr agent_name: The agent responsible for this resource.
        :attr attribute: The key attribute that uniquely identifies this resource on the agent
        :attr attribute_value: The corresponding value for this key attribute.
        :attr version: The version number for this resource.
        """
        self._entity_type = entity_type
        self._agent_name = agent_name
        self._attribute = attribute
        self._attribute_value = attribute_value
        self._version = version

    def to_dict(self) -> JsonType:
        return {
            "entity_type": self._entity_type,
            "agent_name": self.agent_name,
            "attribute": self.attribute,
            "attribute_value": self.attribute_value,
            "version": self.version,
        }

    def get_entity_type(self) -> str:
        return self._entity_type

    def get_agent_name(self) -> str:
        return self._agent_name

    def get_attribute(self) -> str:
        return self._attribute

    def get_attribute_value(self) -> str:
        return self._attribute_value

    def get_version(self) -> int:
        return self._version

    def set_version(self, version: int) -> None:
        if self._version > 0 and version != self._version:
            raise AttributeError("can't set attribute version")

        self._version = version

    def get_inmanta_module(self) -> str:
        """
        Utility method to parse the Inmanta module out of
        the entity type for this Id.

        e.g. Returns `std` for resources of type `std::testing::NullResource`
        """
        ns = self._entity_type.split("::", maxsplit=1)
        return ns[0]

    def copy(self, *, version: int) -> "Id":
        """
        Creates a copy of this resource id for another model version.
        """
        return Id(self.entity_type, self.agent_name, self.attribute, self.attribute_value, version)

    def __str__(self) -> str:
        if self._version > 0:
            return self.resource_version_str()
        return self.resource_str()

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, other: object) -> bool:
        return str(self) == str(other) and type(self) is type(other)

    def resource_str(self) -> ResourceIdStr:
        """
        String representation for this resource id with the following format:
            <type>[<agent>,<attribute>=<value>]

            - type: The resource type, as defined in the configuration model.
                For example :inmanta:entity:`std::testing::NullResource`.
            - agent: The agent responsible for this resource.
            - attribute: The key attribute that uniquely identifies this resource on the agent
            - value: The corresponding value for this key attribute.

        :return: Returns a :py:class:`inmanta.data.model.ResourceIdStr`
        """
        return cast(
            ResourceIdStr,
            "%(type)s[%(agent)s,%(attribute)s=%(value)s]"
            % {
                "type": self._entity_type,
                "agent": self._agent_name,
                "attribute": self._attribute,
                "value": self._attribute_value,
            },
        )

    def resource_version_str(self) -> ResourceVersionIdStr:
        return cast(
            ResourceVersionIdStr,
            "%(type)s[%(agent)s,%(attribute)s=%(value)s],v=%(version)s"
            % {
                "type": self._entity_type,
                "agent": self._agent_name,
                "attribute": self._attribute,
                "value": self._attribute_value,
                "version": self._version,
            },
        )

    def __repr__(self) -> str:
        return str(self)

    def get_instance(self) -> Optional[Resource]:
        """
        Create an instance of this class and set the identifying attribute already
        """
        cls, _ = resource.get_class(self.entity_type)

        if cls is None:
            return None

        obj = cls(self)

        setattr(obj, self.attribute, self.attribute_value)
        return obj

    @classmethod
    def parse_resource_version_id(cls, resource_id: ResourceVersionIdStr) -> "Id":
        id: Id = Id.parse_id(resource_id)
        if id.version == 0:
            raise ValueError(f"Version is missing from resource id: {resource_id}")
        return id

    @classmethod
    def parse_id(cls, resource_id: Union[ResourceVersionIdStr, ResourceIdStr], version: Optional[int] = None) -> "Id":
        """
        Parse the resource id and return the type, the hostname and the
        resource identifier.

        :param version: If provided, the version field of the returned Id will be set to this version.
        """
        result = PARSE_ID_REGEX.search(resource_id)

        if result is None:
            raise ValueError("Invalid id for resource %s" % resource_id)

        if version is None:
            version_match: str = result.group("version")

            version = 0
            if version_match is not None:
                version = int(version_match)

        id_obj = Id(result.group("type"), result.group("hostname"), result.group("attr"), result.group("value"), version)
        return id_obj

    @classmethod
    def is_resource_version_id(cls, value: str) -> bool:
        """
        Check whether the given value is a resource version id
        """
        result = PARSE_RVID_REGEX.search(value)
        return result is not None

    @classmethod
    def is_resource_id(cls, value: str) -> bool:
        """
        Check whether the given value is a resource id
        """
        result = PARSE_ID_REGEX.search(value)
        return result is not None

    def is_resource_version_id_obj(self) -> bool:
        """
        Check whether this object represents a resource version id
        """
        return self.version != 0

    @classmethod
    def set_version_in_id(cls, id_str: Union[ResourceVersionIdStr, ResourceIdStr], new_version: int) -> ResourceVersionIdStr:
        """
        Return a copy of the given id_str with the version number set to new_version.
        """
        parsed_id = cls.parse_id(id_str)
        new_id = parsed_id.copy(version=new_version)
        return new_id.resource_version_str()

    entity_type = property(get_entity_type)
    agent_name = property(get_agent_name)
    attribute = property(get_attribute)
    attribute_value = property(get_attribute_value)
    version = property(get_version, set_version)


class HostNotFoundException(Exception):
    """
    This exception is raise when the deployment agent cannot access a host to manage a resource (Use mainly with remote io)
    """

    def __init__(self, hostname: str, user: str, error: str) -> None:
        self.hostname = hostname
        self.user = user
        self.error = error

    def to_action(self) -> "ResourceAction":
        from inmanta.data import ResourceAction

        ra = ResourceAction()  # @UndefinedVariable
        ra.message = f"Failed to access host {self.hostname} as user {self.user} over ssh."
        ra.data = {"host": self.hostname, "user": self.user, "error": self.error}

        return ra
