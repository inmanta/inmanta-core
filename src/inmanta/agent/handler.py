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
import base64
import traceback
from concurrent.futures import Future
from collections import defaultdict


from inmanta.agent.io import get_io, remote
from inmanta import protocol, resources, const, data
from tornado import ioloop
from inmanta.module import Project
from inmanta.agent.cache import AgentCache
import uuid

LOGGER = logging.getLogger(__name__)


class provider(object):  # noqa: H801
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


class ResourcePurged(Exception):
    pass


def cache(f=None, ignore=[], timeout=5000, for_version=True, cacheNone=True):  # noqa: H801
    """
        decorator for methods in resource handlers to provide caching

        this decorator works similar to memoization:
        when the decorate method is called, its return value is cached,
        for subsequent calls, the cached value is used instead of the actual value

        The name of the method + the arguments of the method form the cache key

        If an argument named version is present and for_version is True,
        the cache entry is flushed after this version has been deployed
        If an argument named resource is present,
        it is assumed to be a resource and its ID is used, without the version information

        :param timeout the number of second this cache entry should live
        :param for_version if true, this value is evicted from the cache when this deploy is ready
        :param ignore a list of argument names that should not be part of the cache key
    """

    def actual(f):
        myignore = set(ignore)
        myargs = inspect.getargspec(f).args[1:]

        def wrapper(self, *args, **kwds):

            kwds.update(dict(zip(myargs, args)))

            def bound(**kwds):
                return f(self, **kwds)

            return self.cache.get_or_else(f.__name__, bound, for_version, timeout, myignore, cacheNone, **kwds)

        return wrapper

    if f is None:
        return actual
    else:
        return actual(f)


class HandlerContext(object):
    """
        Context passed to handler methods for state related "things"
    """
    def __init__(self, resource, dry_run=False, action_id=None):
        self._resource = resource
        self._dry_run = dry_run
        self._cache = {}

        self._purged = False
        self._updated = False
        self._created = False
        self._change = None

        self._changes = {}

        if action_id is None:
            action_id = uuid.uuid4()
        self._action_id = action_id
        self._status = None
        self._logs = []

    @property
    def action_id(self) -> uuid.UUID:
        return self._action_id

    @property
    def status(self) -> const.ResourceState:
        return self._status

    @property
    def logs(self) -> list:
        return self._logs

    def set_status(self, status: const.ResourceState) -> None:
        """
            Set the status of the handler operation.
        """
        self._status = status

    def is_dry_run(self):
        """
            Is this a dryrun?
        """
        return self._dry_run

    def get(self, name):
        return self._cache[name]

    def contains(self, key):
        return key in self._cache

    def set(self, name, value):
        self._cache[name] = value

    def set_created(self):
        self._created = True
        if self._change is None or self._change.value < const.Change.created.value:
            self._change = const.Change.created

    def set_purged(self):
        self._purged = True
        if self._change is None or self._change.value < const.Change.purged.value:
            self._change = const.Change.purged

    def set_updated(self):
        self._updated = True
        if self._change is None or self._change.value < const.Change.updated.value:
            self._change = const.Change.updated

    @property
    def changed(self):
        return self._created or self._updated or self._purged

    @property
    def change(self):
        return self._change

    def add_change(self, name, desired, current=None):
        """
            Report a change of a field. This field is added to the set of updated fields

            :param name The name of the field that was updated
            :param desired The desired value to which the field was updated (or should be updated)
            :param current The value of the field before it was updated
        """
        self._changes[name] = {"current": current, "desired": desired}

    def add_changes(self, **kwargs):
        """
            Report a list of changes at once as kwargs

            :param key The name of the field that was updated. This field is also adde to the set of updated fields
            :param value The desired value of the field.

            To report the previous value of the field, use the add_change method
        """
        for field, value in kwargs.items():
            self._changes[field] = {"desired": value}

    def fields_updated(self, fields):
        """
            Report that fields have been updated
        """
        for field in fields:
            if field not in self._changes:
                self._changes[fields] = {}

    def update_changes(self, changes: dict):
        """
            Update the changes list with changes

            :param changes This should be a dict with a value a dict containing "current" and "desired" keys
        """
        self._changes.update(changes)

    @property
    def changes(self):
        return self._changes

    def log_msg(self, level: int, msg: str, args: list, kwargs: dict) -> dict:
        if len(args) > 0:
            raise Exception("Args not supported")
        log = data.LogLine.log(level, msg, **kwargs)
        LOGGER.log(level, log._data["msg"])
        self._logs.append(log)

    def debug(self, msg: str, *args, **kwargs) -> None:
        """
        Log 'msg % args' with severity 'DEBUG'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.debug("Houston, we have a %s", "thorny problem", exc_info=1)
        """
        self.log_msg(logging.DEBUG, msg, args, kwargs)

    def info(self, msg: str, *args, **kwargs) -> None:
        """
        Log 'msg % args' with severity 'INFO'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.info("Houston, we have a %s", "interesting problem", exc_info=1)
        """
        self.log_msg(logging.INFO, msg, args, kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        """
        Log 'msg % args' with severity 'WARNING'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.warning("Houston, we have a %s", "bit of a problem", exc_info=1)
        """
        self.log_msg(logging.WARNING, msg, args, kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        """
        Log 'msg % args' with severity 'ERROR'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.error("Houston, we have a %s", "major problem", exc_info=1)
        """
        self.log_msg(logging.ERROR, msg, args, kwargs)

    def exception(self, msg: str, *args, exc_info=True, **kwargs) -> None:
        """
        Convenience method for logging an ERROR with exception information.
        """
        self.error(msg, *args, exc_info=exc_info, **kwargs)

    def critical(self, msg: str, *args, **kwargs) -> None:
        """
        Log 'msg % args' with severity 'CRITICAL'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.critical("Houston, we have a %s", "major disaster", exc_info=1)
        """
        self.log_msg(logging.CRITICAL, msg, args, kwargs)


class ResourceHandler(object):
    """
        A baseclass for classes that handle resource on a platform
    """

    def __init__(self, agent, io=None) -> None:
        self._agent = agent

        if io is None:
            self._io = get_io(self._agent.remote)
        else:
            self._io = io

        self._client = None
        self._ioloop = ioloop.IOLoop.current(instance=True)

    def run_sync(self, func):
        f = Future()

        def future_to_future(future):
            exc = future.exception()
            if exc is not None:
                f.set_exception(exc)
            else:
                f.set_result(future.result())

        def run():
            try:
                result = func()
                if result is not None:
                    from tornado.gen import convert_yielded
                    result = convert_yielded(result)
                    result.add_done_callback(future_to_future)
            except Exception as e:
                f.set_exception(e)
        self._ioloop.add_callback(run)

        return f.result()

    def set_cache(self, cache: AgentCache) -> None:
        self.cache = cache

    def get_client(self):
        if self._client is None:
            self._client = protocol.AgentClient("agent", self._agent.sessionid, self._ioloop)
        return self._client

    def process_events(self, ctx: HandlerContext, resource: resources.Resource, events: dict):
        """
            Process events generated by changes to required resources
        """
        if self.can_reload():
            self.do_reload(ctx, resource)

    def can_process_events(self) -> bool:
        """
            Can this handler process events? This is a more generic version of the reload mechanism
        """
        return self.can_reload()

    def can_reload(self) -> bool:
        """
            Can this handler reload?
        """
        return False

    def do_reload(self, ctx: HandlerContext, resource: resources.Resource) -> None:
        """
            Perform a reload of this resource
        """

    def pre(self, ctx: HandlerContext, resource: resources.Resource) -> None:
        """
            Method executed before a transaction (Facts, dryrun, real deployment, ...) is executed
        """

    def post(self, ctx: HandlerContext, resource: resources.Resource) -> None:
        """
            Method executed after a transaction
        """

    def close(self) -> None:
        pass

    @classmethod
    def is_available(cls, io) -> bool:
        """
            Check if this handler is available on the current system
        """
        return True

    def _diff(self, current: resources.Resource, desired: resources.Resource):
        changes = {}

        # check attributes
        for field in current.__class__.fields:
            current_value = getattr(current, field)
            desired_value = getattr(desired, field)

            if current_value != desired_value and desired_value is not None:
                changes[field] = {"current": current_value, "desired": desired_value}

        return changes

    def check_resource(self, ctx: HandlerContext, resource: resources.Resource):
        """
            Check the status of a resource
        """
        raise NotImplementedError()

    def list_changes(self, ctx: HandlerContext, resource: resources.Resource):
        """
            Returns the changes required to bring the resource on this system
            in the state describted in the resource entry.
        """
        current = self.check_resource(ctx, resource)
        return self._diff(current, resource)

    def do_changes(self, ctx: HandlerContext, resource: resources.Resource, changes: dict) -> None:
        """
            Do the changes required to bring the resource on this system in the
            state of the given resource.
        """
        raise NotImplementedError()

    def execute(self, ctx: HandlerContext, resource: resources.Resource, dry_run=False) -> None:
        """
            Update the given resource
        """
        try:
            self.pre(ctx, resource)

            if resource.require_failed:
                ctx.info(msg="Skipping %(resource_id)s because of failed dependencies", resource_id=resource.id)
                ctx.set_status(const.ResourceState.skipped)
                return

            changes = self.list_changes(ctx, resource)
            ctx.update_changes(changes)

            if not dry_run:
                self.do_changes(ctx, resource, changes)
                ctx.set_status(const.ResourceState.deployed)

            else:
                ctx.set_status(const.ResourceState.dry)

            self.post(ctx, resource)
        except SkipResource as e:
            ctx.set_status(const.ResourceState.skipped)
            ctx.warning(msg="Resource %(resource_id)s was skipped: %(reason)s", resource_id=resource.id, reason=e.args)

        except Exception as e:
            ctx.set_status(const.ResourceState.failed)
            ctx.exception("An error occurred during deployment of %(resource_id)s (excp: %(exception)s",
                          resource_id=resource.id, exception=repr(e), traceback=traceback.format_exc())

    def facts(self, ctx: HandlerContext, resource: resources.Resource) -> dict:
        """
            Returns facts about this resource
        """
        return {}

    def check_facts(self, ctx: HandlerContext, resource: resources.Resource) -> dict:
        """
            Query for facts
        """
        self.pre(ctx, resource)
        facts = self.facts(ctx, resource)
        self.post(ctx, resource)

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

        result = self.run_sync(call)
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

        result = self.run_sync(call)
        return result.code == 200

    def upload_file(self, hash_id, content):
        """
            Upload a file to the server
        """
        def call():
            return self.get_client().upload_file(id=hash_id, content=base64.b64encode(content).decode("ascii"))

        try:
            self.run_sync(call)
        except Exception:
            raise Exception("Unable to upload file to the server.")


class CRUDHandler(ResourceHandler):
    """
        This handler base class requires CRUD methods to be implemented: create, read, update and delete. Such a handler
        only works on purgeable resources.
    """

    def read_resource(self, ctx: HandlerContext, resource: resources.PurgeableResource) -> None:
        """
            This method reads the current state of the resource. It provides a copy of the resource that should be deployed,
            the method implementation should modify the attributes of this resource to the current state.

            :param ctx Context can be used to pass value discovered in the read method to the CUD methods. For example, the
                       id used in API calls
            :param resource A clone of the desired resource state. The read method need to set values on this object.
            :raise SkipResource: Raise this exception when the handler should skip this resource
            :raise ResourcePurged: Raise this exception when the resource does not exist yet.
        """

    def create_resource(self, ctx: HandlerContext, resource: resources.PurgeableResource) -> None:
        """
            This method is called by the handler when the resource should be created.

            :param context Context can be used to get values discovered in the read method. For example, the id used in API
                           calls. This context should also be used to let the handler know what changes were made to the
                           resource.
            :param resource The desired resource state.
        """

    def delete_resource(self, ctx: HandlerContext, resource: resources.PurgeableResource) -> None:
        """
            This method is called by the handler when the resource should be deleted.

            :param ctx Context can be used to get values discovered in the read method. For example, the id used in API
                       calls. This context should also be used to let the handler know what changes were made to the
                       resource.
            :param resource The desired resource state.
        """

    def update_resource(self, ctx: HandlerContext, changes: dict, resource: resources.PurgeableResource) -> None:
        """
            This method is called by the handler when the resource should be updated.

            :param ctx Context can be used to get values discovered in the read method. For example, the id used in API
                       calls. This context should also be used to let the handler know what changes were made to the
                       resource.
            :param changes A map of resource attributes that should be changed. Each value is a tuple with the current and the
                           desired value.
            :param resource The desired resource state.
        """

    def execute(self, ctx: HandlerContext, resource, dry_run=None) -> None:
        """
            Update the given resource
        """
        try:
            self.pre(ctx, resource)

            if resource.require_failed:
                ctx.info("Skipping %(resource_id)s because of failed dependencies", resource_id=resource.id)
                ctx.set_status(const.ResourceState.skipped)

            else:
                current = resource.clone()
                changes = {}
                try:
                    self.read_resource(ctx, current)
                    changes = self._diff(current, resource)

                except ResourcePurged:
                    if not resource.purged:
                        changes["purged"] = dict(desired=resource.purged, current=True)

                for field, values in changes.items():
                    ctx.add_change(field, desired=values["desired"], current=values["current"])

                if not dry_run:
                    if "purged" in changes:
                        if not changes["purged"]["desired"]:
                            self.create_resource(ctx, resource)
                        else:
                            self.delete_resource(ctx, resource)

                    elif len(changes) > 0:
                        self.update_resource(ctx, changes, resource)

                    ctx.set_status(const.ResourceState.deployed)
                else:
                    ctx.set_status(const.ResourceState.dry)

            self.post(ctx, resource)
        except SkipResource as e:
            ctx.set_status(const.ResourceState.skipped)
            ctx.warning(msg="Resource %(resource_id)s was skipped: %(reason)s", resource_id=resource.id, reason=e.args)

        except Exception as e:
            ctx.set_status(const.ResourceState.failed)
            ctx.exception("An error occurred during deployment of %(resource_id)s (exception: %(exception)s)",
                          resource_id=resource.id, exception=repr(e), traceback=traceback.format_exc())


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

    @classmethod
    def _get_instance(cls, handler_class: type, agent, io) -> ResourceHandler:
        new_instance = handler_class(agent, io)
        return new_instance

    @classmethod
    def get_provider(cls, cache, agent, resource) -> ResourceHandler:
        """
            Return a provider to handle the given resource
        """
        resource_id = resource.id
        resource_type = resource_id.entity_type
        agent_name = agent.get_hostname()
        if agent.is_local():
            io = get_io()
        else:
            key_name = "remote_io_" + agent_name
            try:
                io = cache.find(key_name, version=resource_id.version)
            except KeyError:
                try:
                    io = get_io(agent_name)
                except (remote.CannotLoginException, resources.HostNotFoundException):
                    # Unable to login, show an error and ignore this agent
                    LOGGER.error("Unable to login to host %s (for resource %s)", agent_name, resource_id)
                    io = None

                # TODO: do not add expire to remoteio!!
                cache.cache_value(key_name, io, version=resource_id.version)

            if io is None:
                # Skip this resource
                raise Exception("No handler available for %s (no io available)" % resource_id)

        available = []
        if resource_type in cls.__command_functions:
            for handlr in cls.__command_functions[resource_type].values():
                h = cls._get_instance(handlr, agent, io)
                if h.available(resource):
                    available.append(h)
                else:
                    h.close()

        if len(available) > 1:
            for h in available:
                h.close()

            io.close()
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
