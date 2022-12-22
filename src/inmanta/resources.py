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
import json
import logging
import re
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

import inmanta.util
from inmanta import plugins
from inmanta.ast import CompilerException, ExplicitPluginException, ExternalException
from inmanta.data.model import ResourceIdStr, ResourceVersionIdStr
from inmanta.execute import proxy, util
from inmanta.stable_api import stable_api
from inmanta.types import JsonType

if TYPE_CHECKING:
    from inmanta import export
    from inmanta.data import ResourceAction
    from inmanta.execute import runtime

LOGGER = logging.getLogger(__name__)


class ResourceException(Exception):
    pass


T = TypeVar("T", bound="Resource")


@stable_api
class resource(object):  # noqa: N801
    """
    A decorator that registers a new resource. The decorator must be applied to classes that inherit from
    :class:`~inmanta.resources.Resource`

    :param name: The name of the entity in the configuration model it creates a resources from. For example
                 :inmanta:entity:`std::File`
    :param id_attribute: The attribute of `this` resource that uniquely identifies a resource on an agent. This attribute
                         can be mapped.
    :param agent: This string indicates how the agent of this resource is determined. This string points to an attribute,
                  but it can navigate relations (this value cannot be mapped). For example, the agent argument could be
                  ``host.name``
    """

    _resources: Dict[str, Tuple[Type["Resource"], Dict[str, str]]] = {}

    def __init__(self, name: str, id_attribute: str, agent: str):
        if not isinstance(agent, str):
            raise ResourceException(f"The agent parameter has to be a string, got {agent} of type {type(agent)}")
        self._cls_name = name
        self._options = {"agent": agent, "name": id_attribute}

    def __call__(self, cls: Type[T]) -> Type[T]:
        """
        The wrapping
        """
        if self._cls_name in resource._resources:
            LOGGER.info("Reloading module %s" % self._cls_name)
            del resource._resources[self._cls_name]

        resource._resources[self._cls_name] = (cls, self._options)
        return cls

    @classmethod
    def validate(cls) -> None:
        for resource, _ in cls._resources.values():
            resource.validate()

    @classmethod
    def get_entity_resources(cls) -> Iterable[str]:
        """
        Returns a list of entity types for which a resource has been registered
        """
        return cls._resources.keys()

    @classmethod
    def get_class(cls, name: str) -> Tuple[Optional[Type["Resource"]], Optional[Dict[str, str]]]:
        """
        Get the class definition for the given entity.
        """
        if name in cls._resources:
            return cls._resources[name]

        return (None, None)

    @classmethod
    def get_resources(cls) -> Iterator[Tuple[str, Type["Resource"]]]:
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
    def _get_parent_fields(cls, bases: Sequence[Type["Resource"]]) -> List[str]:
        fields: List[str] = []
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


@stable_api
class Resource(metaclass=ResourceMeta):
    """
    Plugins should inherit resource from this class so a resource from a model can be serialized and deserialized.

    Such as class is registered when the :func:`~inmanta.resources.resource` decorator is used. Each class needs to indicate
    the fields the resource will have with a class field named "fields". A metaclass merges all fields lists from the class
    itself and all superclasses. If a field it not available directly in the model object the serializer will look for
    static methods in the class with the name "get_$fieldname".
    """

    fields: Sequence[str] = ("send_event",)
    send_event: bool  # Deprecated field
    model: "proxy.DynamicProxy"
    map: Dict[str, Callable[[Optional["export.Exporter"], "proxy.DynamicProxy"], Any]]

    @staticmethod
    def get_send_event(_exporter: "export.Exporter", obj: "Resource") -> bool:
        try:
            return obj.send_event
        except Exception:
            return False

    @classmethod
    def convert_requires(
        cls, resources: Dict["runtime.Instance", "Resource"], ignored_resources: Set["runtime.Instance"]
    ) -> None:
        """
        Convert all requires

        :param resources: A dict with a mapping from model objects to resource objects
        :param ignored_resources: A set of model objects that have been ignored (and not converted to resources)
        """
        for res in resources.values():
            final_requires: Set["Resource"] = set()
            initial_requires: List["runtime.Instance"] = [x for x in res.model.requires]

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
        path_elements: List[str] = agent_attribute.split(".")
        agent_value = model_object
        for el in path_elements:
            try:
                # TODO cleanup this hack
                if isinstance(agent_value, list):
                    agent_value = agent_value[0]

                agent_value = getattr(agent_value, el)

            except proxy.UnsetException as e:
                raise e
            except proxy.UnknownException as e:
                raise e
            except Exception:
                raise Exception(
                    "Unable to get the name of agent %s belongs to. In path %s, '%s' does not exist"
                    % (model_object, agent_attribute, el)
                )

        attribute_value = cls.map_field(None, entity_name, attribute_name, model_object)
        if isinstance(attribute_value, util.Unknown):
            raise proxy.UnknownException(attribute_value)
        if not isinstance(agent_value, str):
            raise ResourceException(
                f"The agent attribute should lead to a string, got {agent_value} of type {type(agent_value)}"
            )

        # agent_value is no longer a proxy.DynamicProxy here, force this for mypy validation
        return Id(entity_name, str(agent_value), attribute_name, attribute_value)

    @classmethod
    def map_field(
        cls, exporter: Optional["export.Exporter"], entity_name: str, field_name: str, model_object: "proxy.DynamicProxy"
    ) -> str:
        try:
            if hasattr(cls, "get_" + field_name):
                mthd = getattr(cls, "get_" + field_name)
                value = mthd(exporter, model_object)
            elif hasattr(cls, "map") and field_name in cls.map:
                value = cls.map[field_name](exporter, model_object)
            else:
                value = getattr(model_object, field_name)
            # serialize to weed out all unknowns
            # not very efficient, but the tree has to be traversed anyways
            # passing along the serialized version would break the resource apis
            json.dumps(value, default=inmanta.util.api_boundary_json_encoder)
            return value
        except IgnoreResourceException:
            raise  # will be handled in _load_resources of export.py
        except proxy.UnknownException as e:
            return e.unknown
        except plugins.PluginException as e:
            raise ExplicitPluginException(None, f"Failed to get attribute '{field_name}' for export on '{entity_name}'", e)
        except CompilerException:
            # Internal exceptions (like UnsetException) should be propagated without being wrapped
            # as they are used later on and wrapping them would break the compiler
            raise
        except Exception as e:
            raise ExternalException(None, f"Failed to get attribute '{field_name}' for export on '{entity_name}'", e)

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

        # map all fields
        fields = {field: resource_cls.map_field(exporter, entity_name, field, model_object) for field in resource_cls.fields}

        obj = resource_cls(obj_id)
        obj.populate(fields)
        obj.model = model_object

        return obj

    @classmethod
    def deserialize(cls, obj_map: JsonType, use_generic: bool = False) -> "Resource":
        """
        Deserialize the resource from the given dictionary
        """
        obj_id = Id.parse_id(obj_map["id"])
        cls_resource, _options = resource.get_class(obj_id.entity_type)

        force_fields = False
        if cls_resource is None:
            if not use_generic:
                raise TypeError("No resource class registered for entity %s" % obj_id.entity_type)
            else:
                cls_resource = cls
                force_fields = True

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
                    "Resource %s is a reserved keyword and not a valid field name, reported in %s" % (field, cls.__name__)
                )

    def __init__(self, _id: "Id") -> None:
        self.id = _id
        self.version = 0
        self.requires: Set[Id] = set()
        self.resource_requires: Set[Resource] = set()
        self.unknowns: Set[str] = set()

        if not hasattr(self.__class__, "fields"):
            raise Exception("A resource should have a list of fields")

        for field in self.__class__.fields:
            setattr(self, field, None)

    def populate(self, fields: Dict[str, Any], force_fields: bool = False) -> None:
        for field in self.__class__.fields:
            if field in fields or force_fields:
                setattr(self, field, fields[field])
            else:
                raise Exception("Resource with id %s does not have field %s" % (fields["id"], field))
        if "requires" in fields:
            # parse requires into ID's
            for require in fields["requires"]:
                self.requires.add(Id.parse_id(require))

    def set_version(self, version: int) -> None:
        """
        Set the version of this resource
        """
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

    def clone(self, **kwargs: Any) -> "Resource":
        """
        Create a clone of this resource. The given kwargs can be used to override attributes.

        :return: The cloned resource
        """
        res = Resource.deserialize(self.serialize())
        for k, v in kwargs.items():
            setattr(res, k, v)

        return res

    def serialize(self) -> JsonType:
        """
        Serialize this resource to its dictionary representation
        """
        dictionary: Dict[str, Any] = {}

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
class Id(object):
    """
    A unique id that identifies a resource that is managed by an agent
    """

    def __init__(self, entity_type: str, agent_name: str, attribute: str, attribute_value: str, version: int = 0) -> None:
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
        return str(self) == str(other) and type(self) == type(other)

    def resource_str(self) -> ResourceIdStr:
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
    def parse_id(cls, resource_id: Union[ResourceVersionIdStr, ResourceIdStr]) -> "Id":
        """
        Parse the resource id and return the type, the hostname and the
        resource identifier.
        """
        result = PARSE_ID_REGEX.search(resource_id)

        if result is None:
            raise ValueError("Invalid id for resource %s" % resource_id)

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
        ra.message = "Failed to access host %s as user %s over ssh." % (self.hostname, self.user)
        ra.data = {"host": self.hostname, "user": self.user, "error": self.error}

        return ra
