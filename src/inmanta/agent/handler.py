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

from collections import defaultdict
import hashlib
import inspect
import logging
import base64

from inmanta.agent.io import get_io
from inmanta import protocol
from tornado import ioloop
from inmanta.module import Project
from inmanta.agent.cache import AgentCache

LOGGER = logging.getLogger(__name__)


class provider(object):
    """
        A decorator that registers a new implementation
    """

    def __init__(self, resource_type, name):
        self._resource_type = resource_type
        self._name = name

    def __call__(self, function):
        """
            The wrapping
        """
        Commander.add_provider(self._resource_type, self._name, function)
        return function


class SkipResource(Exception):
    pass


def cache(f=None, ignore=[], timeout=5000, forVersion=True):
    """
        decorator for methods in resource handlers to provide caching

        this decorator works similar to memoization:
        when the decorate method is called, its return value is cached,
        for subsequent calls, the cached value is used instead of the actual value

        The name of the method + the arguments of the method form the cache key

        If an argument named version is present and forVersion is True,
        the cache entry is flushed after this version has been deployed
        If an argument named resource is present,
        it is assumed to be a resource and its ID is used, without the version information

        :param timeout the number of second this cache entry should live
        :param forVersion if true, this value is evicted from the cache when this deploy is ready
        :param ignore a list of argument names that should not be part of the cache key
    """

    def actual(f):
        myignore = set(ignore)
        myargs = inspect.getargspec(f).args[1:]

        def wrapper(self, *args, **kwds):

            kwds.update(dict(zip(myargs, args)))

            def bound(**kwds):
                return f(self, **kwds)

            return self.cache.get_or_else(f.__name__, bound, forVersion, timeout, myignore, **kwds)

        return wrapper

    if f is None:
        return actual
    else:
        return actual(f)


class ResourceHandler(object):
    """
        A baseclass for classes that handle resource on a platform
    """

    def __init__(self, agent, io=None):
        self._agent = agent

        if io is None:
            self._io = get_io(self._agent.remote)
        else:
            self._io = io

        self._client = None
        self._ioloop = ioloop.IOLoop()

    def set_cache(self, cache: AgentCache):
        self.cache = cache

    def get_client(self):
        if self._client is None:
            self._client = protocol.Client("agent", self._ioloop)
        return self._client

    def pre(self, resource):
        """
            Method executed before a transaction (Facts, dryrun, real deployment, ...) is executed
        """

    def post(self, resource):
        """
            Method executed after a transaction
        """

    def close(self, with_io=True):
        if with_io:
            self._io.close()
        self._ioloop.close(all_fds=True)

    @classmethod
    def is_available(self, io):
        """
            Check if this handler is available on the current system
        """
        raise NotImplementedError()

    def _diff(self, current, desired):
        changes = {}

        # check attributes
        for field in current.__class__.fields:
            current_value = getattr(current, field)
            desired_value = getattr(desired, field)

            if current_value != desired_value and desired_value is not None:
                changes[field] = (current_value, desired_value)

        return changes

    def can_reload(self):
        """
            Can this handler reload?
        """
        return False

    def check_resource(self, resource):
        """
            Check the status of a resource
        """
        raise NotImplementedError()

    def list_changes(self, resource):
        """
            Returns the changes required to bring the resource on this system
            in the state describted in the resource entry.
        """
        raise NotImplementedError()

    def do_changes(self, resource):
        """
            Do the changes required to bring the resource on this system in the
            state of the given resource.

            :return This method returns true if changes were made
        """
        raise NotImplementedError()

    def execute(self, resource, dry_run=False):
        """
            Update the given resource
        """
        results = {"changed": False, "changes": {}, "status": "nop", "log_msg": ""}

        try:
            self.pre(resource)

            if resource.require_failed:
                LOGGER.info("Skipping %s because of failed dependencies" % resource.id)
                results["status"] = "skipped"

            elif not dry_run:
                changed = self.do_changes(resource)
                changes = {}
                if hasattr(changed, "__len__"):
                    changes = changed
                    changed = len(changes) > 0

                if changed:
                    LOGGER.info("%s was changed" % resource.id)

                results["changed"] = changed
                results["changes"] = changes
                results["status"] = "deployed"

            else:
                changes = self.list_changes(resource)
                results["changes"] = changes
                results["status"] = "dry"

            self.post(resource)
        except SkipResource as e:
            results["log_msg"] = e.args
            results["status"] = "skipped"
            LOGGER.warning("Resource %s was skipped: %s" % (resource.id, e.args))

        except Exception as e:
            LOGGER.exception("An error occurred during deployment of %s" % resource.id)
            results["log_msg"] = repr(e)
            results["status"] = "failed"

        return results

    def facts(self, resource):
        """
            Returns facts about this resource
        """
        return {}

    def check_facts(self, resource):
        """
            Query for facts
        """
        self.pre(resource)
        facts = self.facts(resource)
        self.post(resource)

        return facts

    def available(self, resource):
        """
            Returns true if this handler is available for the given resource
        """
        return True

    def snapshot(self, resource):
        """
            Create a new snapshot and upload it to the server

            :param resource The state of the resource for which a snapshot is created
            :return The data that needs to be uploaded to the server
        """
        raise NotImplementedError()

    def restore(self, resource, snapshot_id):
        """
            Restore a resource from a snapshot
        """
        raise NotImplementedError()

    def get_file(self, hash_id):
        """
            Retrieve a file from the fileserver identified with the given hash
        """
        def call():
            return self.get_client().get_file(hash_id)

        result = self._ioloop.run_sync(call)
        if result.code == 404:
            return None
        elif result.code == 200:
            return base64.b64decode(result.result["content"])
        else:
            raise Exception("An error occurred while retrieving file %s" % hash_id)

    def stat_file(self, hash_id):
        """
            Check if a file exists on the server
        """
        def call():
            return self.get_client().stat_file(hash_id)

        result = self._ioloop.run_sync(call)
        return result.code == 200

    def upload_file(self, hash_id, content):
        """
            Upload a file to the server
        """
        def call():
            return self.get_client().upload_file(id=hash_id, content=base64.b64encode(content).decode("ascii"))

        try:
            self._ioloop.run_sync(call)
        except Exception:
            raise Exception("Unable to upload file to the server.")


class Commander(object):
    """
        This class handles commands
    """
    __command_functions = defaultdict(dict)
    __handlers = []
    __handler_cache = {}

    @classmethod
    def close(cls):
        pass
        # for h in cls.__handlers:
        # h.close()
        # del h

    @classmethod
    def _get_instance(cls, handler_class: type, agent, io) -> ResourceHandler:
        new_instance = handler_class(agent, io)
        return new_instance

    @classmethod
    def get_provider(cls, agent, resource) -> ResourceHandler:
        """
            Return a provider to handle the given resource
        """
        resource_id = resource.id
        resource_type = resource_id.entity_type
        agent_name = agent.get_agent_hostname(resource.id.agent_name)
        if agent.is_local(agent_name):
            io = get_io()
        else:
            io = get_io(agent_name)

        available = []
        if resource_type in cls.__command_functions:
            for handlr in cls.__command_functions[resource_type].values():
                h = cls._get_instance(handlr, agent, io)
                if h.available(resource):
                    available.append(h)
                else:
                    h.close(with_io=False)

        if len(available) > 1:
            for h in available:
                h.close()
            raise Exception("More than one handler selected for resource %s" % resource.id)

        elif len(available) == 1:
            return available[0]

        raise Exception("No resource handler registered for resource of type %s" % resource_type)

    @classmethod
    def add_provider(cls, resource: str, name: str, provider):
        """
            Register a new provider

            :param resource the name of the resource this handler applies to
            :param name the name of the handler itself
            :param provider the handler function
        """
        if resource in cls.__command_functions and name in cls.__command_functions[resource]:
            del cls.__command_functions[resource][name]

        cls.__command_functions[resource][name] = provider

    @classmethod
    def sources(cls):
        """
        Get all source files that define resources
        """
        resource_to_sources = {}
        for resource, providers in cls.__command_functions.items():
            sources = {}
            resource_to_sources[resource] = sources
            for provider in providers.values():
                file_name = inspect.getsourcefile(provider)

                source_code = ""
                with open(file_name, "r") as fd:
                    source_code = fd.read()

                sha1sum = hashlib.new("sha1")
                sha1sum.update(source_code.encode("utf-8"))

                hv = sha1sum.hexdigest()

                if hv not in sources:
                    module_name = provider.__module__.split(".")[1]
                    req = Project.get().modules[module_name].get_python_requirements_as_list()
                    sources[hv] = (file_name, provider.__module__, source_code, req)

        return resource_to_sources

    @classmethod
    def get_provider_class(cls, resource_type, name):
        """
            Return the class of the handler for the given type and with the given name
        """
        if resource_type not in cls.__command_functions:
            return None

        if name not in cls.__command_functions[resource_type]:
            return None

        return cls.__command_functions[resource_type][name]


class HandlerNotAvailableException(Exception):
    """
        This exception is thrown when a resource handler cannot perform its job. For example, the admin interface
        it connects to is not available.
    """
