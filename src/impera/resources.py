"""
    Copyright 2016 Inmanta

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

import hashlib
import inspect
import logging
import re

from impera.execute import util
from impera.execute.proxy import DynamicProxy, UnknownException, UnsetException


LOGGER = logging.getLogger(__name__)


class resource(object):
    """
    A decorator that registers a new resource and the typename used in the protocol
    """
    _resources = {}

    def __init__(self, name, id_attribute, agent):
        self._cls_name = name
        self._options = {"agent": agent, "name": id_attribute}

    def __call__(self, cls):
        """
        The wrapping
        """
        if self._cls_name in resource._resources:
            LOGGER.info("Reloading module %s" % self._cls_name)
            del resource._resources[self._cls_name]

        resource._resources[self._cls_name] = (cls, self._options)
        return cls

    @classmethod
    def get_entity_resources(cls):
        """
        Returns a list of entity types for which a resource has been registered
        """
        return cls._resources.keys()

    @classmethod
    def get_class(cls, name):
        """
        Get the class definition for the given imp entity.
        """
        if name in cls._resources:
            return cls._resources[name]

        return (None, None)

    @classmethod
    def sources(cls) -> dict:
        """
        Get all source files that define resources
        """
        sources = {}
        for resource, _options in cls._resources.values():
            file_name = inspect.getsourcefile(resource)

            source_code = ""
            with open(file_name, "r") as fd:
                source_code = fd.read()

            sha1sum = hashlib.new("sha1")
            sha1sum.update(source_code.encode("utf-8"))

            hv = sha1sum.hexdigest()

            if hv not in sources:
                sources[hv] = (file_name, resource.__module__, source_code)

        return sources


class ResourceNotFoundExcpetion(Exception):
    """
    This exception is thrown when a resource is not found
    """


def to_id(entity):
    """
        Convert an entity from the model to its resource id
    """
    entity_name = str(entity.type())
    for cls_name in [entity_name] + entity.type().get_all_parent_names():
        cls, options = resource.get_class(cls_name)

        if cls is not None:
            break

    if cls is not None:
        obj_id = cls.object_to_id(entity, cls_name, options["name"], options["agent"])
        return str(obj_id)

    return None


class Resource(object):
    """
    A managed resource on a system
    """
    __create_cache = {}

    @classmethod
    def clear_cache(cls):
        """
        Clear the cache of created resources
        """

    @classmethod
    def convert_requires(cls):
        """
        Convert all requires
        """
        for res in cls.__create_cache.values():
            res.requires = set([cls.__create_cache[r] for r in res.requires])

    @classmethod
    def get_resource(cls, model_object):
        """
        Get the converted resource for the given model object. If the object has not been converted, return None

        @param model_object:
        @return:
        """
        model_object = model_object._get_instance()
        if model_object in cls.__create_cache:
            return cls.__create_cache[model_object]

        return None

    @classmethod
    def object_to_id(cls, model_object, entity_name, attribute_name, agent_attribute):
        """
        Convert the given object to a textual id

        :param model_object The object to convert to an id
        :param entity_name The entity type
        :param attribute_name The name of the attribute that uniquely identifies the entity
        :param agent_attribute The "path" to the attribute that defines the agent
        """
        # first get the agent attribute
        path_elements = agent_attribute.split(".")
        agent_value = model_object
        for el in path_elements:
            try:
                # TODO cleanup this hack
                if isinstance(agent_value, list):
                    agent_value = agent_value[0]

                agent_value = getattr(agent_value, el)

            except UnsetException as e:
                raise e
            except Exception:
                raise Exception("Unable to get the name of agent %s belongs to. In path %s, '%s' does not exist"
                                % (model_object, agent_attribute, el))

        attribute_value = getattr(model_object, attribute_name)

        return Id(entity_name, agent_value, attribute_name, attribute_value)

    @classmethod
    def create_from_model(cls, exporter, entity_name, model_object):
        """
        Build a resource from a given configuration model entity
        """
        cls, options = resource.get_class(entity_name)

        if cls is None:
            raise TypeError("No resource class registered for entity %s" % entity_name)

        # build the id of the object
        obj_id = cls.object_to_id(model_object, entity_name, options["name"], options["agent"])

        obj = cls(obj_id)

        for field in cls.fields:
            try:
                if hasattr(cls, "map") and field in cls.map:
                    try:
                        value = cls.map[field](exporter, DynamicProxy.return_value(model_object))
                        setattr(obj, field, value)
                    except UnknownException as e:
                        setattr(obj, field, e.unknown)

                else:
                    try:
                        # setattr(obj, field, DynamicProxy.return_value(model_object.get_attribute(field).get_value()))
                        setattr(obj, field, getattr(model_object, field))
                    except UnknownException as e:
                        setattr(obj, field, e.unknown)

            except AttributeError:
                raise AttributeError("Attribute %s does not exist on entity of type %s" % (field, entity_name))

        obj.requires = getattr(model_object, "requires")
        obj.model = model_object

        cls.__create_cache[model_object] = obj
        return obj

    @classmethod
    def deserialize(cls, obj_map):
        """
        Deserialize the resource from the given dictionary
        """
        obj_id = Id.parse_id(obj_map["id"])
        cls, _options = resource.get_class(obj_id.entity_type)

        if cls is None:
            raise TypeError("No resource class registered for entity %s" % obj_id.entity_type)

        obj = cls(obj_id)

        for field in cls.fields:
            if field in obj_map:
                setattr(obj, field, obj_map[field])
            else:
                raise Exception("Resource with id %s does not have field %s" % (obj_map["id"], field))

        for require in obj_map["requires"]:
            obj.requires.add(Id.parse_id(require))

        return obj

    def __init__(self, _id):
        self.id = _id
        self.version = 0
        self.requires = set()
        self.requires_queue = {}
        self.unknowns = set()
        self.model = None
        self.do_reload = False
        self.require_failed = False

        if not hasattr(self.__class__, "fields"):
            raise Exception("A resource should have a list of fields")

        else:
            for field in self.__class__.fields:
                setattr(self, field, None)

    def set_version(self, version):
        """
            Set the version of this resource
        """
        self.version = version
        self.id.version = version

    def __setattr__(self, name, value):
        if isinstance(value, util.Unknown):
            self.unknowns.add(name)

        self.__dict__[name] = value

    def add_require(self, rid, version):
        """
            This resource required resource with id $rid to be at version $version
            or higher.
        """
        self.requires_queue[rid] = version

    def update_require(self, rid, version, failed=False):
        """
            This method is called when a resource with id $rid is updated to
            $version
        """
        if failed:
            self.require_failed = True

        if rid in self.requires_queue and self.requires_queue[rid] <= version:
            del self.requires_queue[rid]

        return len(self.requires_queue) == 0

    def __str__(self):
        return str(self.id)

    def __repr__(self):
        return str(self)

    def clone(self, **kwargs):
        res = Resource.deserialize(Resource.serialize(self))
        for k, v in kwargs.items():
            setattr(res, k, v)

        return res

    def serialize(self):
        """
            Serialize this resource to its dictionary representation
        """
        dictionary = {}

        for field in self.__class__.fields:
            dictionary[field] = getattr(self, field)

        dictionary["requires"] = [str(x.id) for x in self.requires]
        dictionary["version"] = self.version
        dictionary["id"] = str(self.id)

        return dictionary

    def is_type(self, type: str):
        return str(self.model._get_instance().get_type()) == type


class Id(object):
    """
        A unique id that idenfies a resource that is managed by an agent
    """

    def __init__(self, entity_type, agent_name, attribute, attribute_value, version=0):
        self._entity_type = entity_type
        self._agent_name = agent_name
        self._attribute = attribute
        self._attribute_value = attribute_value
        self._version = version

    def to_dict(self):
        return {"entity_type": self._entity_type,
                "agent_name": self.agent_name,
                "attribute": self.attribute,
                "attribute_value": self.attribute_value,
                "version": self.version
                }

    def get_entity_type(self):
        return self._entity_type

    def get_agent_name(self):
        return self._agent_name

    def get_attribute(self):
        return self._attribute

    def get_attribute_value(self):
        return self._attribute_value

    def get_version(self):
        return self._version

    def set_version(self, version):
        if self._version > 0:
            raise AttributeError("can't set attribute version")

        self._version = version

    def __str__(self):
        if self._version > 0:
            return "%(type)s[%(agent)s,%(attribute)s=%(value)s],v=%(version)s" % {
                "type": self._entity_type,
                "agent": self._agent_name,
                "attribute": self._attribute,
                "value": self._attribute_value,
                "version": self._version,
            }

        return self.resource_str()

    def resource_str(self):
        return "%(type)s[%(agent)s,%(attribute)s=%(value)s]" % {
            "type": self._entity_type,
            "agent": self._agent_name,
            "attribute": self._attribute,
            "value": self._attribute_value,
        }

    def __repr__(self):
        return str(self)

    def get_instance(self):
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
    def parse_id(cls, resource_id):
        """
            Parse the resource id and return the type, the hostname and the
            resource identifier.
        """
        result = re.search("^(?P<id>(?P<type>(?P<ns>[\w-]+::)+(?P<class>[\w-]+))\[(?P<hostname>[^,]+)," +
                           "(?P<attr>[^=]+)=(?P<value>[^\]]+)\])(,v=(?P<version>[0-9]+))?$", resource_id)

        if result is None:
            raise Exception("Invalid id for resource %s" % resource_id)

        version = result.group("version")

        if version is not None:
            version = int(version)
        else:
            version = 0

        parts = {
            "type": result.group("type"),
            "hostname": result.group("hostname"),
            "attr": result.group("attr"),
            "value": result.group("value"),
            "id": result.group("id"),
        }

        id_obj = Id(parts["type"], parts["hostname"], parts["attr"], parts["value"], version)
        return id_obj

    entity_type = property(get_entity_type)
    agent_name = property(get_agent_name)
    attribute = property(get_attribute)
    attribute_value = property(get_attribute_value)
    version = property(get_version, set_version)


class HostNotFoundException(Exception):
    """
        This exception is raise when the deployment agent cannot access a host to manage a resource (Use mainly with remote io)
    """

    def __init__(self, hostname, user, error):
        self.hostname = hostname
        self.user = user
        self.error = error

    def to_action(self):
        from impera.data import ResourceAction
        ra = ResourceAction()  # @UndefinedVariable
        ra.message = "Failed to access host %s as user %s over ssh." % (self.hostname, self.user)
        ra.data = {"host": self.hostname, "user": self.user, "error": self.error}

        return ra
