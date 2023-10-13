"""
    Copyright 2019 Inmanta

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
import base64
import inspect
import logging
import traceback
import typing
import uuid
from abc import ABC, abstractmethod
from collections import abc, defaultdict
from concurrent.futures import Future
from functools import partial
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, Type, TypeVar, Union, cast, overload

from tornado import concurrent

import inmanta
from inmanta import const, data, protocol, resources
from inmanta.agent import io
from inmanta.agent.cache import AgentCache
from inmanta.const import ParameterSource, ResourceState
from inmanta.data.model import AttributeStateChange, DiscoveredResource, ResourceIdStr
from inmanta.protocol import Result, json_encode
from inmanta.stable_api import stable_api
from inmanta.types import SimpleTypes
from inmanta.util import hash_file

if typing.TYPE_CHECKING:
    import inmanta.agent.agent
    from inmanta.agent.io.local import IOBase


LOGGER = logging.getLogger(__name__)

T = TypeVar("T")
# A resource present in the model that describes the resources that should be discovered
TDiscovery = TypeVar("TDiscovery", bound=resources.DiscoveryResource)
# The type of elements produced by the resource discovery process.
TDiscovered = TypeVar("TDiscovered")
T_FUNC = TypeVar("T_FUNC", bound=Callable[..., Any])
TResource = TypeVar("TResource", bound=resources.Resource)


@stable_api
class provider(object):  # noqa: N801
    """
    A decorator that registers a new handler.

    :param resource_type: The type of the resource this handler is responsible for.
                          For example, :inmanta:entity:`std::File`
    :param name: A name to reference this provider.
    """

    def __init__(self, resource_type: str, name: str) -> None:
        self._resource_type = resource_type
        self._name = name

    def __call__(self, function):
        """
        The wrapping
        """
        Commander.add_provider(self._resource_type, self._name, function)
        return function


@stable_api
class SkipResource(Exception):
    """
    A handler should raise this exception when a resource should be skipped. The resource will be marked as skipped
    instead of failed.
    """


@stable_api
class ResourcePurged(Exception):
    """
    If the :func:`~inmanta.agent.handler.CRUDHandler.read_resource` method raises this exception, the agent will
    mark the current state of the resource as purged.
    """


class InvalidOperation(Exception):
    """
    This exception is raised by the context or handler methods when an invalid operation is performed.
    """


@stable_api
def cache(
    func: Optional[T_FUNC] = None,
    ignore: typing.List[str] = [],
    timeout: int = 5000,
    for_version: bool = True,
    cache_none: bool = True,
    # deprecated parameter kept for backwards compatibility: if set, overrides cache_none
    cacheNone: Optional[bool] = None,  # noqa: N803
    call_on_delete: Optional[Callable[[Any], None]] = None,
) -> Union[T_FUNC, Callable[[T_FUNC], T_FUNC]]:
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

    :param timeout: the number of second this cache entry should live
    :param for_version: if true, this value is evicted from the cache when this deploy is ready
    :param ignore: a list of argument names that should not be part of the cache key
    :param cache_none: cache returned none values
    :param call_on_delete: A callback function that is called when the value is removed from the cache,
            with the value as argument.
    """

    def actual(f: Callable) -> T_FUNC:
        myignore = set(ignore)
        sig = inspect.signature(f)
        myargs = list(sig.parameters.keys())[1:]

        def wrapper(self, *args: object, **kwds: object) -> object:
            kwds.update(dict(zip(myargs, args)))

            def bound(**kwds):
                return f(self, **kwds)

            return self.cache.get_or_else(
                f.__name__,
                bound,
                for_version,
                timeout,
                myignore,
                cacheNone if cacheNone is not None else cache_none,
                **kwds,
                call_on_delete=call_on_delete,
            )

        # Too much magic to type statically
        return cast(T_FUNC, wrapper)

    if func is None:
        return actual
    else:
        return actual(func)


@stable_api
class LoggerABC(ABC):
    """
    Minimal logging interface exposing logging methods for commonly used
    logging levels.

    Child classes are responsible for implementing a _log_msg method with the
    concrete logging implementation.
    """

    def critical(self, msg: str, *args: object, exc_info: bool = False, **kwargs: object) -> None:
        self._log_msg(logging.CRITICAL, msg, *args, exc_info=exc_info, **kwargs)

    def error(self, msg: str, *args: object, exc_info: bool = False, **kwargs: object) -> None:
        self._log_msg(logging.ERROR, msg, *args, exc_info=exc_info, **kwargs)

    def warning(self, msg: str, *args: object, exc_info: bool = False, **kwargs: object) -> None:
        self._log_msg(logging.WARNING, msg, *args, exc_info=exc_info, **kwargs)

    def info(self, msg: str, *args: object, exc_info: bool = False, **kwargs: object) -> None:
        self._log_msg(logging.INFO, msg, *args, exc_info=exc_info, **kwargs)

    def debug(self, msg: str, *args: object, exc_info: bool = False, **kwargs: object) -> None:
        self._log_msg(logging.DEBUG, msg, *args, exc_info=exc_info, **kwargs)

    def exception(self, msg: str, *args: object, exc_info: bool = True, **kwargs: object) -> None:
        self.error(msg, *args, exc_info=exc_info, **kwargs)

    @abstractmethod
    def _log_msg(
        self,
        level: int,
        msg: str,
        *args: object,
        exc_info: bool = False,
        **kwargs: object,
    ) -> None:
        raise NotImplementedError


@stable_api
class HandlerContext(LoggerABC):
    """
    Context passed to handler methods for state related "things"
    """

    def __init__(
        self,
        resource: resources.Resource,
        dry_run: bool = False,
        action_id: Optional[uuid.UUID] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._resource = resource
        self._dry_run = dry_run
        self._cache: Dict[str, Any] = {}

        self._purged = False
        self._updated = False
        self._created = False
        self._change = const.Change.nochange

        self._changes: Dict[str, AttributeStateChange] = {}

        if action_id is None:
            action_id = uuid.uuid4()
        self._action_id = action_id
        self._status: Optional[ResourceState] = None
        self._logs: List[data.LogLine] = []
        self.logger: logging.Logger
        if logger is None:
            self.logger = LOGGER
        else:
            self.logger = logger

        self._facts: List[Dict[str, Any]] = []

    def set_fact(self, fact_id: str, value: str) -> None:
        """
        Send a fact to the Inmanta server.

        :param fact_id: The name of the fact.
        :param value: The actual value of the fact.
        """
        resource_id = self._resource.id.resource_str()
        fact = {
            "id": fact_id,
            "source": ParameterSource.fact.value,
            "value": value,
            "resource_id": resource_id,
        }
        self._facts.append(fact)

    @property
    def facts(self) -> List[Dict[str, Any]]:
        return self._facts

    @property
    def action_id(self) -> uuid.UUID:
        return self._action_id

    @property
    def status(self) -> Optional[const.ResourceState]:
        return self._status

    @property
    def logs(self) -> List[data.LogLine]:
        return self._logs

    def set_status(self, status: const.ResourceState) -> None:
        """
        Set the status of the handler operation.
        """
        self._status = status

    def is_dry_run(self) -> bool:
        """
        Is this a dryrun?
        """
        return self._dry_run

    def get(self, name: str) -> Any:
        return self._cache[name]

    def contains(self, key: str) -> bool:
        return key in self._cache

    def set(self, name: str, value: Any) -> None:
        self._cache[name] = value

    def set_created(self) -> None:
        self._created = True
        if self._change is not const.Change.nochange:
            raise InvalidOperation(f"Unable to set {const.Change.created} operation, {self._change} already set.")

        self._change = const.Change.created

    def set_purged(self) -> None:
        self._purged = True

        if self._change is not const.Change.nochange:
            raise InvalidOperation(f"Unable to set {const.Change.purged} operation, {self._change} already set.")

        self._change = const.Change.purged

    def set_updated(self) -> None:
        self._updated = True

        if self._change is not const.Change.nochange:
            raise InvalidOperation(f"Unable to set {const.Change.updated} operation, {self._change} already set.")

        self._change = const.Change.updated

    @property
    def changed(self) -> bool:
        return self._created or self._updated or self._purged

    @property
    def change(self) -> const.Change:
        return self._change

    def add_change(self, name: str, desired: object, current: object = None) -> None:
        """
        Report a change of a field. This field is added to the set of updated fields

        :param name: The name of the field that was updated
        :param desired: The desired value to which the field was updated (or should be updated)
        :param current: The value of the field before it was updated
        """
        self._changes[name] = AttributeStateChange(current=current, desired=desired)

    def add_changes(self, **kwargs: SimpleTypes) -> None:
        """
        Report a list of changes at once as kwargs

        :param key: The name of the field that was updated. This field is also added to the set of updated fields
        :param value: The desired value of the field.

        To report the previous value of the field, use the add_change method
        """
        for field, value in kwargs.items():
            self._changes[field] = AttributeStateChange(desired=value)

    def fields_updated(self, fields: str) -> None:
        """
        Report that fields have been updated
        """
        for field in fields:
            if field not in self._changes:
                self._changes[fields] = AttributeStateChange()

    @overload  # noqa: F811
    def update_changes(self, changes: Dict[str, AttributeStateChange]) -> None:
        pass

    @overload  # noqa: F811
    def update_changes(self, changes: Dict[str, Dict[str, Optional[SimpleTypes]]]) -> None:
        pass

    @overload  # noqa: F811
    def update_changes(self, changes: Dict[str, Tuple[SimpleTypes, SimpleTypes]]) -> None:
        pass

    def update_changes(  # noqa: F811
        self,
        changes: Union[
            Dict[str, AttributeStateChange],
            Dict[str, Dict[str, Optional[SimpleTypes]]],
            Dict[str, Tuple[SimpleTypes, SimpleTypes]],
        ],
    ) -> None:
        """
        Update the changes list with changes

        :param changes: This should be a dict with a value a dict containing "current" and "desired" keys
        """
        for attribute, change in changes.items():
            if isinstance(change, dict):
                self._changes[attribute] = AttributeStateChange(
                    current=change.get("current", None), desired=change.get("desired", None)
                )
            elif isinstance(change, tuple):
                if len(change) != 2:
                    raise InvalidOperation(
                        f"Reported changes for {attribute} not valid. Tuple changes should contain 2 element."
                    )
                self._changes[attribute] = AttributeStateChange(current=change[0], desired=change[1])
            elif isinstance(change, AttributeStateChange):
                self._changes[attribute] = change
            else:
                raise InvalidOperation(f"Reported changes for {attribute} not in a type that is recognized.")

    @property
    def changes(self) -> Dict[str, AttributeStateChange]:
        return self._changes

    def _log_msg(self, level: int, msg: str, *args: object, exc_info: bool = False, **kwargs: object) -> None:
        if len(args) > 0:
            raise Exception("Args not supported")
        if exc_info:
            kwargs["traceback"] = traceback.format_exc()

        for k, v in kwargs.items():
            try:
                json_encode(v)
            except TypeError:
                if inmanta.RUNNING_TESTS:
                    # Fail the test when the value is not serializable
                    raise Exception(f"Failed to serialize argument for log message {k}={v}")
                else:
                    # In production, try to cast the non-serializable value to str to prevent the handler from failing.
                    kwargs[k] = str(v)

            except Exception as e:
                raise Exception("Exception during serializing log message arguments") from e
        log = data.LogLine.log(level, msg, **kwargs)
        self.logger.log(level, "resource %s: %s", self._resource.id.resource_version_str(), log._data["msg"], exc_info=exc_info)
        self._logs.append(log)


# Explicitly not yet part of the stable API until the interface has had some time to mature.
class HandlerAPI(ABC, Generic[TResource]):
    """
    Base class describing the interface between the agent and the handler. This class first defines the interface.
    At the end, it also defines a number of utility methods.

    New handlers are registered with the :func:`~inmanta.agent.handler.provider` decorator.
    The implementation of a handler should use the ``self._io`` instance to execute io operations. This io objects
    makes abstraction of local or remote operations. See :class:`~inmanta.agent.io.local.LocalIO` for the available
    operations.
    """

    def __init__(self, agent: "inmanta.agent.agent.AgentInstance", io: Optional["IOBase"] = None) -> None:
        """
        :param agent: The agent that is executing this handler.
        :param io: The io object to use.
        """
        self._agent = agent
        if io is None:
            raise Exception("Unsupported: no resource mgmt in RH")
        else:
            self._io = io
        self._client: Optional[protocol.SessionClient] = None
        # explicit ioloop reference, as we don't want the ioloop for the current thread, but the one for the agent
        self._ioloop = agent.process._io_loop

    # Interface

    def close(self) -> None:
        """
        Override this method to implement custom logic called by the agent on handler deactivation. i.e. when the
        instantiated handler will no longer be used by the agent.
        """
        pass

    def deploy(
        self,
        ctx: HandlerContext,
        resource: TResource,
        requires: abc.Mapping[ResourceIdStr, ResourceState],
    ) -> None:
        """
        Main entrypoint of the handler that will be called by the agent to deploy a resource on the server.
        The agent calls this method for a given resource as soon as all its dependencies (`requires` relation) are ready.
        It is always called, even when one of the dependencies failed to deploy.

        Takes appropriate action based on the state of its dependencies. Calls `execute` iff the handler should actually
        execute, i.e. enforce the intent represented by the resource. A handler may choose not to proceed to this execution
        stage, e.g. when one of the resource's dependencies failed.

        :param ctx: Context object to report changes and logs to the agent and server.
        :param resource: The resource to deploy
        :param requires: A dictionary mapping the resource id of each dependency of the given resource to its resource state.
        """

        def _call_resource_did_dependency_change() -> typing.Awaitable[Result]:
            return self.get_client().resource_did_dependency_change(
                tid=self._agent.environment, rvid=resource.id.resource_version_str()
            )

        def _should_reload() -> bool:
            if not self.can_reload():
                return False
            result = self.run_sync(_call_resource_did_dependency_change)
            if not result.result:
                raise Exception("Failed to determine whether resource should reload")

            if result.code != 200:
                error_msg_from_server = f": {result.result['message']}" if "message" in result.result else ""
                raise Exception(f"Failed to determine whether resource should reload{error_msg_from_server}")
            return result.result["data"]

        def filter_resources_in_unexpected_state(
            reqs: abc.Mapping[ResourceIdStr, ResourceState]
        ) -> abc.Mapping[ResourceIdStr, ResourceState]:
            """
            Return a sub-dictionary of reqs with only those resources that are in an unexpected state.
            """
            unexpected_states = {
                const.ResourceState.available,
                const.ResourceState.dry,
                const.ResourceState.undefined,
                const.ResourceState.skipped_for_undefined,
                const.ResourceState.deploying,
            }
            return {rid: state for rid, state in reqs.items() if state in unexpected_states}

        resources_in_unexpected_state = filter_resources_in_unexpected_state(requires)
        if resources_in_unexpected_state:
            ctx.set_status(const.ResourceState.skipped)
            ctx.warning(
                "Resource %(resource)s skipped because a dependency is in an unexpected state: %(unexpected_states)s",
                resource=resource.id.resource_version_str(),
                unexpected_states=str({rid: state.value for rid, state in resources_in_unexpected_state.items()}),
            )
            return

        failed_dependencies = [req for req, status in requires.items() if status != ResourceState.deployed]
        if not any(failed_dependencies):
            self.execute(ctx, resource)
            if _should_reload():
                self.do_reload(ctx, resource)
        else:
            ctx.set_status(const.ResourceState.skipped)
            ctx.info(
                "Resource %(resource)s skipped due to failed dependencies: %(failed)s",
                resource=resource.id.resource_version_str(),
                failed=str(failed_dependencies),
            )

    @abstractmethod
    def execute(self, ctx: HandlerContext, resource: TResource, dry_run: bool = False) -> None:
        """
        Enforce a resource's intent and inform the handler context of any relevant changes (e.g. set deployed status,
        report attribute changes). Called only when all of its dependencies have successfully deployed.

        :param ctx: Context object to report changes and logs to the agent and server.
        :param resource: The resource to deploy.
        :param dry_run: If set to true, the intent is not enforced, only the set of changes it would bring is computed.
        """
        pass

    def available(self, resource: TResource) -> bool:
        """
        Kept for backwards compatibility, new handler implementations should never override this.

        :param resource: Resource for which to check whether this handler is available.
        """
        return True

    @abstractmethod
    def check_facts(self, ctx: HandlerContext, resource: TResource) -> dict[str, object]:
        """
        This method is called by the agent to query for facts.

        :param ctx: Context object to report changes and logs to the agent and server.
        :param resource: The resource to query facts for.
        :return: A dict with fact names as keys and facts values.
        """
        raise NotImplementedError()

    def set_cache(self, cache: AgentCache) -> None:
        """
        The agent calls this method when it has deemed this handler suitable for a given resource. This cache will be
        used for methods decorated with @cache.

        :param cache: The AgentCache to use.
        """
        self.cache = cache

    # Utility methods

    def can_reload(self) -> bool:
        """
        Can this handler reload?

        :return: Return true if this handler needs to reload on requires changes.
        """
        return False

    def do_reload(self, ctx: HandlerContext, resource: TResource) -> None:
        """
        Perform a reload of this resource.

        :param ctx: Context object to report changes and logs to the agent and server.
        :param resource: The resource to reload.
        """
        pass

    def pre(self, ctx: HandlerContext, resource: TResource) -> None:
        """
        Method executed before a handler operation (Facts, dryrun, real deployment, ...) is executed. Override this method
        to run before an operation.

        :param ctx: Context object to report changes and logs to the agent and server.
        :param resource: The resource being handled.
        """
        pass

    def post(self, ctx: HandlerContext, resource: TResource) -> None:
        """
        Method executed after a handler operation. Override this method to run after an operation.

        :param ctx: Context object to report changes and logs to the agent and server.
        :param resource: The resource being handled.
        """
        pass

    def facts(self, ctx: HandlerContext, resource: TResource) -> dict[str, object]:
        """
        Override this method to implement fact querying. A queried fact can be reported back in two different ways:
        either via the return value of this method or by adding the fact to the HandlerContext via the
        :func:`~inmanta.agent.handler.HandlerContext.set_fact` method. :func:`~inmanta.agent.handler.HandlerAPI.pre`
        and :func:`~inmanta.agent.handler.HandlerAPI.post` are called before and after this method.

        :param ctx: Context object to report changes, logs and facts to the agent and server.
        :param resource: The resource to query facts for.
        :return: A dict with fact names as keys and facts values.
        """
        return {}

    def run_sync(self, func: typing.Callable[[], abc.Awaitable[T]]) -> T:
        """
        Run the given async function on the ioloop of the agent. It will block the current thread until the future
        resolves.

        :param func: A function that returns a yieldable future.
        :return: The result of the async function.
        """
        f: Future[T] = Future()

        # This function is not typed because of generics, the used methods and currying
        def run() -> None:
            try:
                result = func()
                if result is not None:
                    from tornado.gen import convert_yielded

                    result = convert_yielded(result)
                    concurrent.chain_future(result, f)
            except Exception as e:
                f.set_exception(e)

        self._ioloop.call_soon_threadsafe(run)

        return f.result()

    def get_client(self) -> protocol.SessionClient:
        """
        Get the client instance that identifies itself with the agent session.

        :return: A client that is associated with the session of the agent that executes this handler.
        """
        if self._client is None:
            self._client = protocol.SessionClient("agent", self._agent.sessionid)
        return self._client

    def get_file(self, hash_id: str) -> Optional[bytes]:
        """
        Retrieve a file from the fileserver identified with the given id.

        :param hash_id: The id of the content/file to retrieve from the server.
        :return: The content in the form of a bytestring or none is the content does not exist.
        """

        def call() -> abc.Awaitable[Result]:
            return self.get_client().get_file(hash_id)

        result = self.run_sync(call)
        if result.code == 404:
            return None
        elif result.result and result.code == 200:
            file_contents = base64.b64decode(result.result["content"])
            actual_hash_of_file = hash_file(file_contents)
            if hash_id != actual_hash_of_file:
                raise Exception(f"File hash verification failed, expected: {hash_id} but got {actual_hash_of_file}")
            return file_contents
        else:
            raise Exception("An error occurred while retrieving file %s" % hash_id)

    def stat_file(self, hash_id: str) -> bool:
        """
        Check if a file exists on the server.

        :param hash_id: The id of the file on the server. The convention is the use the sha1sum of the content as id.
        :return: True if the file is available on the server.
        """

        def call() -> typing.Awaitable[Result]:
            return self.get_client().stat_file(hash_id)

        result = self.run_sync(call)
        return result.code == 200

    def upload_file(self, hash_id: str, content: bytes) -> None:
        """
        Upload a file to the server

        :param hash_id: The id to identify the content. The convention is to use the sha1sum of the content to identify it.
        :param content: A byte string with the content
        """

        def call() -> abc.Awaitable[Result]:
            return self.get_client().upload_file(id=hash_id, content=base64.b64encode(content).decode("ascii"))

        try:
            self.run_sync(call)
        except Exception:
            raise Exception("Unable to upload file to the server.")


@stable_api
class ResourceHandler(HandlerAPI[TResource]):
    """
    A class that handles resources.
    """

    def _diff(self, current: TResource, desired: TResource) -> dict[str, dict[str, typing.Any]]:
        """
        Calculate the diff between the current and desired resource state.

        :param current: The current state of the resource
        :param desired: The desired state of the resource
        :return: A dict with key the name of the field and value another dict with "current" and "desired" as keys for
                 fields that require changes.
        """
        changes = {}

        # check attributes
        for field in current.__class__.fields:
            current_value = getattr(current, field)
            desired_value = getattr(desired, field)

            if current_value != desired_value and desired_value is not None:
                changes[field] = {"current": current_value, "desired": desired_value}

        return changes

    def check_resource(self, ctx: HandlerContext, resource: TResource) -> TResource:
        """
        Check the current state of a resource

        :param ctx: Context object to report changes and logs to the agent and server.
        :param resource: The resource to check the current state of.
        :return: A resource to represents the current state. Use the :func:`~inmanta.resources.Resource.clone` to create
                 clone of the given resource that can be modified.
        """
        raise NotImplementedError()

    def list_changes(self, ctx: HandlerContext, resource: TResource) -> dict[str, dict[str, typing.Any]]:
        """
        Returns the changes required to bring the resource on this system in the state described in the resource entry.
        This method calls :func:`~inmanta.agent.handler.ResourceHandler.check_resource`

        :param ctx: Context object to report changes and logs to the agent and server.
        :param resource: The resource to check the current state of.
        :return: A dict with key the name of the field and value another dict with "current" and "desired" as keys for
                 fields that require changes.
        """
        current = self.check_resource(ctx, resource)
        return self._diff(current, resource)

    def do_changes(self, ctx: HandlerContext, resource: TResource, changes: abc.Mapping[str, abc.Mapping[str, object]]) -> None:
        """
        Do the changes required to bring the resource on this system in the state of the given resource.

        :param ctx: Context object to report changes and logs to the agent and server.
        :param resource: The resource to check the current state of.
        :param changes: The changes that need to occur as reported by
                        :func:`~inmanta.agent.handler.ResourceHandler.list_changes`
        """
        raise NotImplementedError()

    def execute(self, ctx: HandlerContext, resource: TResource, dry_run: bool = False) -> None:
        try:
            self.pre(ctx, resource)

            changes = self.list_changes(ctx, resource)
            ctx.update_changes(changes)

            if not dry_run:
                self.do_changes(ctx, resource, changes)
                ctx.set_status(const.ResourceState.deployed)
            else:
                ctx.set_status(const.ResourceState.dry)
        except SkipResource as e:
            ctx.set_status(const.ResourceState.skipped)
            ctx.warning(msg="Resource %(resource_id)s was skipped: %(reason)s", resource_id=resource.id, reason=e.args)
        except Exception as e:
            ctx.set_status(const.ResourceState.failed)
            ctx.exception(
                "An error occurred during deployment of %(resource_id)s (exception: %(exception)s)",
                resource_id=resource.id,
                exception=f"{e.__class__.__name__}('{e}')",
            )
        finally:
            try:
                self.post(ctx, resource)
            except Exception as e:
                ctx.exception(
                    "An error occurred after deployment of %(resource_id)s (exception: %(exception)s)",
                    resource_id=resource.id,
                    exception=f"{e.__class__.__name__}('{e}')",
                )

    def check_facts(self, ctx: HandlerContext, resource: TResource) -> dict[str, object]:
        """
        This method is called by the agent to query for facts. It runs :func:`~inmanta.agent.handler.HandlerAPI.pre`
        and :func:`~inmanta.agent.handler.HandlerAPI.post`. This method calls
        :func:`~inmanta.agent.handler.HandlerAPI.facts` to do the actual querying.

        :param ctx: Context object to report changes and logs to the agent and server.
        :param resource: The resource to query facts for.
        :return: A dict with fact names as keys and facts values.
        """
        facts = {}
        try:
            self.pre(ctx, resource)
            facts = self.facts(ctx, resource)
        finally:
            try:
                self.post(ctx, resource)
            except Exception as e:
                ctx.exception(
                    "An error occurred after getting facts about %(resource_id)s (exception: %(exception)s)",
                    resource_id=resource.id,
                    exception=f"{e.__class__.__name__}('{e}')",
                )

        return facts


TPurgeableResource = TypeVar("TPurgeableResource", bound=resources.PurgeableResource)


@stable_api
class CRUDHandler(ResourceHandler[TPurgeableResource]):
    """
    This handler base class requires CRUD methods to be implemented: create, read, update and delete. Such a handler
    only works on purgeable resources.
    """

    def read_resource(self, ctx: HandlerContext, resource: TPurgeableResource) -> None:
        """
        This method reads the current state of the resource. It provides a copy of the resource that should be deployed,
        the method implementation should modify the attributes of this resource to the current state.

        :param ctx: Context can be used to pass value discovered in the read method to the CUD methods. For example, the
                   id used in API calls
        :param resource: A clone of the desired resource state. The read method need to set values on this object.
        :raise SkipResource: Raise this exception when the handler should skip this resource
        :raise ResourcePurged: Raise this exception when the resource does not exist yet.
        """

    def create_resource(self, ctx: HandlerContext, resource: TPurgeableResource) -> None:
        """
        This method is called by the handler when the resource should be created.

        :param context: Context can be used to get values discovered in the read method. For example, the id used in API
                        calls. This context should also be used to let the handler know what changes were made to the
                        resource.
        :param resource: The desired resource state.
        """

    def delete_resource(self, ctx: HandlerContext, resource: TPurgeableResource) -> None:
        """
        This method is called by the handler when the resource should be deleted.

        :param ctx: Context can be used to get values discovered in the read method. For example, the id used in API
                    calls. This context should also be used to let the handler know what changes were made to the
                    resource.
        :param resource: The desired resource state.
        """

    def update_resource(self, ctx: HandlerContext, changes: Dict[str, Dict[str, Any]], resource: TPurgeableResource) -> None:
        """
        This method is called by the handler when the resource should be updated.

        :param ctx: Context can be used to get values discovered in the read method. For example, the id used in API
                    calls. This context should also be used to let the handler know what changes were made to the
                    resource.
        :param changes: A map of resource attributes that should be changed. Each value is a tuple with the current and the
                        desired value.
        :param resource: The desired resource state.
        """

    def calculate_diff(
        self, ctx: HandlerContext, current: TPurgeableResource, desired: TPurgeableResource
    ) -> typing.Dict[str, typing.Dict[str, typing.Any]]:
        """
        Calculate the diff between the current and desired resource state.

        :param ctx: Context can be used to get values discovered in the read method. For example, the id used in API
                    calls. This context should also be used to let the handler know what changes were made to the
                    resource.
        :param current: The current state of the resource
        :param desired: The desired state of the resource
        :return: A dict with key the name of the field and value another dict with "current" and "desired" as keys for
                 fields that require changes.
        """
        return self._diff(current, desired)

    def execute(self, ctx: HandlerContext, resource: TPurgeableResource, dry_run: bool = False) -> None:
        try:
            self.pre(ctx, resource)

            # current is clone, except for purged is set to false to prevent a bug that occurs often where the desired
            # state defines purged=true but the read_resource fails to set it to false if the resource does exist
            desired = resource
            current: TPurgeableResource = desired.clone(purged=False)
            changes: typing.Dict[str, typing.Dict[str, typing.Any]] = {}
            try:
                ctx.debug("Calling read_resource")
                self.read_resource(ctx, current)
                changes = self.calculate_diff(ctx, current, desired)

            except ResourcePurged:
                if not desired.purged:
                    changes["purged"] = dict(desired=desired.purged, current=True)

            for field, values in changes.items():
                ctx.add_change(field, desired=values["desired"], current=values["current"])

            if not dry_run:
                if "purged" in changes:
                    if not changes["purged"]["desired"]:
                        ctx.debug("Calling create_resource")
                        self.create_resource(ctx, desired)
                    else:
                        ctx.debug("Calling delete_resource")
                        self.delete_resource(ctx, desired)

                elif not desired.purged and len(changes) > 0:
                    ctx.debug("Calling update_resource", changes=changes)
                    self.update_resource(ctx, dict(changes), desired)

                ctx.set_status(const.ResourceState.deployed)
            else:
                ctx.set_status(const.ResourceState.dry)

        except SkipResource as e:
            ctx.set_status(const.ResourceState.skipped)
            ctx.warning(msg="Resource %(resource_id)s was skipped: %(reason)s", resource_id=resource.id, reason=e.args)

        except Exception as e:
            ctx.set_status(const.ResourceState.failed)
            ctx.exception(
                "An error occurred during deployment of %(resource_id)s (exception: %(exception)s)",
                resource_id=resource.id,
                exception=f"{e.__class__.__name__}('{e}')",
                traceback=traceback.format_exc(),
            )
        finally:
            try:
                self.post(ctx, resource)
            except Exception as e:
                ctx.exception(
                    "An error occurred after deployment of %(resource_id)s (exception: %(exception)s)",
                    resource_id=resource.id,
                    exception=f"{e.__class__.__name__}('{e}')",
                )


# This is kept for backwards compatibility with versions explicitly importing CRUDHandlerGeneric
CRUDHandlerGeneric = CRUDHandler


@stable_api
class DiscoveryHandler(HandlerAPI[TDiscovery], Generic[TDiscovery, TDiscovered]):
    """
    The DiscoveryHandler is generic with regard to two resource types:
        - TDiscovery denotes the handler's Discovery Resource type, used to drive resource discovery. This is not a
          conventional resource type expected to be deployed on a network, but rather a way to express
          the intent to discover resources of the second type TDiscovered already present on the network.
        - TDiscovered denotes the handler's Unmanaged Resource type. This is the type of the resources that have been
          discovered and reported to the server. Objects of this type must be either:
             1. A pydantic object
             2. An object that has a `to_dict()` method that returns a serializable dictionary
             3. A serializable dictionary
    """

    def check_facts(self, ctx: HandlerContext, resource: TDiscovery) -> Dict[str, object]:
        return {}

    @abstractmethod
    def discover_resources(
        self, ctx: HandlerContext, discovery_resource: TDiscovery
    ) -> abc.Mapping[ResourceIdStr, TDiscovered]:
        """
        This method implements the resource discovery logic. This method will be called
        by the handler during deployment of the corresponding discovery resource.
        """
        raise NotImplementedError()

    def execute(self, ctx: HandlerContext, resource: TDiscovery, dry_run: bool = False) -> None:
        """
        Logic to perform during resource discovery. This method is called when the agent wants
        to deploy the corresponding discovery resource. The default behaviour of this method is to call
        the `discover_resources` method, serialize the returned values and report them to the server.
        """
        if dry_run:
            return

        try:
            self.pre(ctx, resource)

            def _call_discovered_resource_create_batch(
                discovered_resources: abc.Sequence[DiscoveredResource],
            ) -> typing.Awaitable[Result]:
                return self.get_client().discovered_resource_create_batch(
                    tid=self._agent.environment, discovered_resources=discovered_resources
                )

            discovered_resources_raw: abc.Mapping[ResourceIdStr, TDiscovered] = self.discover_resources(ctx, resource)
            discovered_resources: abc.Sequence[DiscoveredResource] = [
                DiscoveredResource(discovered_resource_id=resource_id, values=values)
                for resource_id, values in discovered_resources_raw.items()
            ]
            result = self.run_sync(partial(_call_discovered_resource_create_batch, discovered_resources))

            if result.code != 200:
                assert result.result is not None  # Make mypy happy
                ctx.set_status(const.ResourceState.failed)
                error_msg_from_server = f": {result.result['message']}" if "message" in result.result else ""
                ctx.error(
                    "Failed to report discovered resources to the server (status code: %(code)s)%(error_msg_from_server)s",
                    code=result.code,
                    error_msg_from_server=error_msg_from_server,
                )
            else:
                ctx.set_status(const.ResourceState.deployed)
        except SkipResource as e:
            ctx.set_status(const.ResourceState.skipped)
            ctx.warning(msg="Resource %(resource_id)s was skipped: %(reason)s", resource_id=resource.id, reason=e.args)
        except Exception as e:
            ctx.set_status(const.ResourceState.failed)
            ctx.exception(
                "An error occurred during deployment of %(resource_id)s (exception: %(exception)s)",
                resource_id=resource.id,
                exception=f"{e.__class__.__name__}('{e}')",
                traceback=traceback.format_exc(),
            )
        finally:
            try:
                self.post(ctx, resource)
            except Exception as e:
                ctx.exception(
                    "An error occurred after deployment of %(resource_id)s (exception: %(exception)s)",
                    resource_id=resource.id,
                    exception=f"{e.__class__.__name__}('{e}')",
                )


class Commander(object):
    """
    This class handles commands
    """

    __command_functions: dict[str, dict[str, Type[ResourceHandler[Any]]]] = defaultdict(dict)

    @classmethod
    def get_handlers(cls) -> Dict[str, Dict[str, Type[ResourceHandler[Any]]]]:
        return cls.__command_functions

    @classmethod
    def reset(cls) -> None:
        cls.__command_functions = defaultdict(dict)

    @classmethod
    def close(cls) -> None:
        pass

    @classmethod
    def _get_instance(
        cls, handler_class: Type[ResourceHandler[Any]], agent: "inmanta.agent.agent.AgentInstance", io: "IOBase"
    ) -> ResourceHandler[Any]:
        new_instance = handler_class(agent, io)
        return new_instance

    @classmethod
    def get_provider(
        cls, cache: AgentCache, agent: "inmanta.agent.agent.AgentInstance", resource: resources.Resource
    ) -> HandlerAPI[Any]:
        """
        Return a provider to handle the given resource
        """
        resource_id = resource.id
        resource_type = resource_id.get_entity_type()
        try:
            agent_io = io.get_io(cache, agent.uri, resource_id.get_version())
        except Exception:
            LOGGER.exception("Exception raised during creation of IO for uri %s", agent.uri)
            raise Exception("No handler available for %s (no io available)" % resource_id)

        if agent_io is None:
            # Skip this resource
            raise Exception("No handler available for %s (no io available)" % resource_id)

        available = []
        if resource_type in cls.__command_functions:
            for handlr in cls.__command_functions[resource_type].values():
                h = cls._get_instance(handlr, agent, agent_io)
                if h.available(resource):
                    available.append(h)
                else:
                    h.close()

        if len(available) > 1:
            for h in available:
                h.close()

            agent_io.close()
            raise Exception("More than one handler selected for resource %s" % resource.id)

        elif len(available) == 1:
            return available[0]

        raise Exception("No resource handler registered for resource of type %s" % resource_type)

    @classmethod
    def add_provider(cls, resource: str, name: str, provider: Type[ResourceHandler[Any]]) -> None:
        """
        Register a new provider

        :param resource: the name of the resource this handler applies to
        :param name: the name of the handler itself
        :param provider: the handler function
        """
        if resource in cls.__command_functions and name in cls.__command_functions[resource]:
            del cls.__command_functions[resource][name]

        cls.__command_functions[resource][name] = provider

    @classmethod
    def get_providers(cls) -> typing.Iterator[Tuple[str, typing.Type[ResourceHandler[Any]]]]:
        """Return an iterator over resource type, handler definition"""
        for resource_type, handler_map in cls.__command_functions.items():
            for handle_name, handler_class in handler_map.items():
                yield (resource_type, handler_class)

    @classmethod
    def get_provider_class(cls, resource_type: str, name: str) -> Optional[typing.Type[ResourceHandler[Any]]]:
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


@stable_api
class PythonLogger(LoggerABC):
    """
    This class implements the LoggerABC interface and is a standalone wrapper around a logging.Logger.
    """

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def _log_msg(
        self,
        level: int,
        msg: str,
        *args: object,
        exc_info: bool = False,
        **kwargs: object,
    ) -> None:
        if len(args) > 0:
            raise Exception("Args not supported")

        if kwargs:
            self.logger.log(level, msg, kwargs, exc_info=exc_info)
        else:
            self.logger.log(level, msg, exc_info=exc_info)
