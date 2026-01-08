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
import json
import logging
import traceback
import typing
import uuid
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Mapping, Sequence
from concurrent.futures import Future
from functools import partial
from typing import Any, Callable, Generic, Optional, TypeVar, Union, cast, overload

from tornado import concurrent

import inmanta
from inmanta import const, data, protocol, resources, tracing
from inmanta.agent.cache import AgentCache
from inmanta.const import ParameterSource, ResourceState
from inmanta.data.model import AttributeStateChange, BaseModel, DiscoveredResourceInput
from inmanta.protocol import Result, json_encode
from inmanta.stable_api import stable_api
from inmanta.types import ResourceIdStr, SimpleTypes
from inmanta.util import hash_file

if typing.TYPE_CHECKING:
    import inmanta.agent.executor


LOGGER = logging.getLogger(__name__)

T = TypeVar("T")
# A resource present in the model that describes the resources that should be discovered
TDiscovery = TypeVar("TDiscovery", bound=resources.DiscoveryResource)
# The type of elements produced by the resource discovery process.
TDiscovered = TypeVar("TDiscovered", bound=BaseModel)
T_FUNC = TypeVar("T_FUNC", bound=Callable[..., object])
TResource = TypeVar("TResource", bound=resources.Resource)


@stable_api
class provider:  # noqa: N801
    """
    A decorator that registers a new handler.

    :param resource_type: The type of the resource this handler is responsible for.
                          For example, :inmanta:entity:`std::testing::NullResource`
    :param name: A name to reference this provider.
    """

    def __init__(self, resource_type: str, name: Optional[str] = None) -> None:
        self._resource_type = resource_type
        # name is no longer used but deprecating it would create a lot warnings for little gain

    def __call__(self, function: type["ResourceHandler[TResource]"]) -> "type[ResourceHandler[TResource]]":
        """
        The wrapping
        """
        Commander.add_provider(self._resource_type, function)
        return function


@stable_api
class SkipResource(Exception):
    """
    A handler should raise this exception when a resource should be skipped. The resource will be marked as skipped
    instead of failed. We will try to deploy again later .
    """


@stable_api
class SkipResourceForDependencies(SkipResource):
    """
    A handler should raise this exception when a resource should be skipped as a result of unsuccessful dependencies.
    The resource will be marked as skipped instead of failed.
    We will try to deploy again when its dependencies are successfully deployed for their latest intent.
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


@typing.overload
def cache(
    func: None = None,
    ignore: list[str] = [],
    timeout: Optional[int] = None,
    for_version: Optional[bool] = None,
    cache_none: bool = True,
    cacheNone: Optional[bool] = None,  # noqa: N803
    call_on_delete: Optional[Callable[[Any], None]] = None,
    evict_after_creation: float = 0.0,
    evict_after_last_access: float = 0.0,
) -> Callable[[T_FUNC], T_FUNC]: ...


@typing.overload
def cache(
    func: T_FUNC,
    ignore: list[str] = [],
    timeout: Optional[int] = None,
    for_version: Optional[bool] = None,
    cache_none: bool = True,
    cacheNone: Optional[bool] = None,  # noqa: N803
    call_on_delete: Optional[Callable[[Any], None]] = None,
    evict_after_creation: float = 0.0,
    evict_after_last_access: float = 0.0,
) -> T_FUNC: ...


@stable_api
def cache(
    func: Optional[T_FUNC] = None,
    ignore: list[str] = [],
    # deprecated parameter kept for backwards compatibility: alias for evict_after_creation
    timeout: Optional[int] = None,
    # deprecated parameter kept for backwards compatibility: if set, overrides evict_after_creation/evict_after_last_access
    for_version: Optional[bool] = None,
    cache_none: bool = True,
    # deprecated parameter kept for backwards compatibility: if set, overrides cache_none
    cacheNone: Optional[bool] = None,  # noqa: N803
    call_on_delete: Optional[Callable[[Any], None]] = None,
    evict_after_creation: float = 0.0,
    evict_after_last_access: float = 0.0,
) -> Union[T_FUNC, Callable[[T_FUNC], T_FUNC]]:
    """
    decorator for methods in resource handlers to provide caching

    this decorator works similar to memoization:
    when the decorate method is called, its return value is cached,
    for subsequent calls, the cached value is used instead of the actual value

    The name of the method + the arguments of the method form the cache key

    If an argument named resource is present,
    it is assumed to be a resource and its ID is used, without the version information

    :param ignore: a list of argument names that should not be part of the cache key
    :param cache_none: allow the caching of None values
    :param call_on_delete: A callback function that is called when the value is removed from the cache,
            with the value as argument.
    :param evict_after_creation: This cache item will be considered stale this number of seconds after
        entering the cache.
    :param evict_after_last_access: This cache item will be considered stale this number of seconds after
        it was last accessed.
    """

    def actual(f: Callable[..., object]) -> T_FUNC:
        myignore = set(ignore)
        sig = inspect.signature(f)
        myargs = list(sig.parameters.keys())[1:]  # Starts at 1 because 0 is self.
        if evict_after_creation > 0 and timeout and timeout > 0:
            LOGGER.warning(
                "Both the `evict_after_creation` and the deprecated `timeout` parameter are set "
                "for cached method %s.%s. The `timeout` parameter will be ignored and cached entries will "
                "be kept in the cache for %.2fs after entering it. The `timeout` parameter should no"
                "longer be used. Please refer to the handler documentation "
                "for more information about setting a retention policy.",
                f.__module__,
                f.__name__,
                evict_after_creation,
            )

        def wrapper(self: HandlerAPI[TResource], *args: object, **kwds: object) -> object:
            kwds.update(dict(zip(myargs, args)))

            def bound(**kwds: object) -> object:
                return f(self, **kwds)

            return self.cache.get_or_else(
                key=f.__name__,
                function=bound,
                for_version=for_version,
                timeout=timeout,
                evict_after_last_access=evict_after_last_access,
                evict_after_creation=evict_after_creation,
                ignore=myignore,
                cache_none=cacheNone if cacheNone is not None else cache_none,
                call_on_delete=call_on_delete,
                **kwds,
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
        self._cache: dict[str, Any] = {}

        self._purged = False
        self._updated = False
        self._created = False
        self._change = const.Change.nochange

        self._changes: dict[str, AttributeStateChange] = {}

        if action_id is None:
            action_id = uuid.uuid4()
        self._action_id = action_id
        self._status: Optional[ResourceState] = None
        self._resource_state: Optional[const.HandlerResourceState] = None
        self._logs: list[data.LogLine] = []
        self.logger: logging.Logger
        if logger is None:
            self.logger = LOGGER
        else:
            self.logger = logger

        self._facts: list[dict[str, Any]] = []

    def set_fact(self, fact_id: str, value: str, expires: bool = True) -> None:
        """
        Send a fact to the Inmanta server.

        :param fact_id: The name of the fact.
        :param value: The actual value of the fact.
        :param expires: Whether this fact expires or not.
        """
        resource_id = self._resource.id.resource_str()
        fact = {
            "id": fact_id,
            "source": ParameterSource.fact.value,
            "value": value,
            "resource_id": resource_id,
            "expires": expires,
        }
        self._facts.append(fact)

    @property
    def facts(self) -> list[dict[str, Any]]:
        return self._facts

    @property
    def action_id(self) -> uuid.UUID:
        return self._action_id

    @property
    def status(self) -> Optional[const.ResourceState]:
        return self._status

    @property
    def resource_state(self) -> Optional[const.HandlerResourceState]:
        return self._resource_state

    @property
    def logs(self) -> list[data.LogLine]:
        return self._logs

    def set_status(self, status: const.ResourceState) -> None:
        """
        Set the status of the handler operation and translate it to HandlerResourceState
        """
        self._status = status
        try:
            self._resource_state = const.HandlerResourceState(status)
        except ValueError:
            self._resource_state = const.HandlerResourceState.failed
            self.logger.warning("Called set_status with status %s which is not supported on the handler API", status)

    def set_resource_state(self, new_state: const.HandlerResourceState) -> None:
        """
        Set the state of the resource.
        If setting the state to non_compliant, requires that the changes are registered first.
        It is not possible to set the state to non_compliant and not register changes.
        """
        if new_state is const.HandlerResourceState.non_compliant and len(self._changes) == 0:
            raise InvalidOperation("Unable to set state to non_compliant before changes are set.")

        self._resource_state = new_state
        if new_state is const.HandlerResourceState.skipped_for_dependency:
            # This is the only state that is not present in const.ResourceState
            self._status = const.ResourceState.skipped
        else:
            self._status = const.ResourceState(new_state)

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
    def update_changes(self, changes: dict[str, AttributeStateChange]) -> None:
        pass

    @overload  # noqa: F811
    def update_changes(self, changes: dict[str, dict[str, Optional[SimpleTypes]]]) -> None:
        pass

    @overload  # noqa: F811
    def update_changes(self, changes: dict[str, tuple[SimpleTypes, SimpleTypes]]) -> None:
        pass

    def update_changes(  # noqa: F811
        self,
        changes: Union[
            dict[str, AttributeStateChange],
            dict[str, dict[str, Optional[SimpleTypes]]],
            dict[str, tuple[SimpleTypes, SimpleTypes]],
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
    def changes(self) -> dict[str, AttributeStateChange]:
        return self._changes

    def _log_msg(self, level: int, msg: str, *args: object, exc_info: bool = False, **kwargs: object) -> None:
        if len(args) > 0:
            raise Exception("Args not supported")
        if exc_info:
            kwargs["traceback"] = traceback.format_exc()

        def clean_arg_value(k: str, v: object) -> object:
            """
            Make sure we have a clean dict.

            These values will be pickled and json serialized later down the stream.
            As such we have to make sure both things are possible.

            Clean json is both json serializable and (safely) pickleable

            Also, the data will only be accessed via json endpoints,
            so anything not picked up by the json serializer will be lost anyways.
            """
            try:
                return json.loads(json_encode(v))
            except TypeError:
                if inmanta.RUNNING_TESTS:
                    # Fail the test when the value is not serializable
                    raise Exception(f"Failed to serialize argument for log message {k}={v}")
                else:
                    # In production, try to cast the non-serializable value to str to prevent the handler from failing.
                    return str(v)
            except Exception as e:
                raise Exception("Exception during serializing log message arguments") from e

        packaged_kwargs = {k: clean_arg_value(k, v) for k, v in kwargs.items()}

        log = data.LogLine.log(level, msg, **packaged_kwargs)
        self.logger.log(level, "resource %s: %s", self._resource.id.resource_version_str(), log._data["msg"], exc_info=exc_info)
        self._logs.append(log)


# Explicitly not yet part of the stable API until the interface has had some time to mature.
class HandlerAPI(ABC, Generic[TResource]):
    """
    Base class describing the interface between the agent and the handler. This class first defines the interface.
    At the end, it also defines a number of utility methods.

    New handlers are registered with the :func:`~inmanta.agent.handler.provider` decorator.
    """

    def __init__(self, agent: "inmanta.agent.executor.AgentInstance", io: object = None) -> None:
        """
        :param agent: The agent that is executing this handler.
        :param io: Parameter for backwards compatibility. It is not used by the handler.
        """
        self._agent = agent
        self._client: Optional[protocol.SessionClient] = None

        # explicit ioloop reference, as we don't want the ioloop for the current thread, but the one for the agent
        self._ioloop = agent.eventloop

    # Interface

    def close(self) -> None:
        """
        Override this method to implement custom logic called by the agent on handler deactivation. i.e. when the
        instantiated handler will no longer be used by the agent.
        """

    def deploy(
        self,
        ctx: HandlerContext,
        resource: TResource,
        requires: Mapping[ResourceIdStr, ResourceState],
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

        def _call_resource_did_dependency_change() -> Awaitable[Result[bool]]:
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

        def filter_resources_by_state(
            reqs: Mapping[ResourceIdStr, ResourceState], states: typing.Set[ResourceState]
        ) -> Mapping[ResourceIdStr, ResourceState]:
            """
            Return a sub-dictionary of dependencies of this resource.
            Only keeping dependencies that are in a state that is in the provided set.

            :param reqs: The list of requirements of this resource
            :param states: The list of states that we want to keep in this sub-dictionary
            """

            return {rid: state for rid, state in reqs.items() if state in states}

        def execute_and_reload() -> None:
            self.execute(ctx, resource)
            if _should_reload():
                self.do_reload(ctx, resource)

        # report-only resources don't care about dependencies
        if resource.report_only:
            execute_and_reload()
            return
        # Check if any dependencies got into any unexpected state
        dependencies_in_unexpected_state = filter_resources_by_state(
            requires,
            {
                const.ResourceState.dry,
                const.ResourceState.undefined,
                const.ResourceState.skipped_for_undefined,
            },
        )
        if dependencies_in_unexpected_state:
            ctx.set_resource_state(const.HandlerResourceState.skipped_for_dependency)
            ctx.warning(
                "Resource %(resource)s skipped because a dependency is in an unexpected state: %(unexpected_states)s",
                resource=resource.id.resource_version_str(),
                unexpected_states=str({rid: state.value for rid, state in dependencies_in_unexpected_state.items()}),
            )
            return

        # Check if any dependencies got a new desired state while this resource was waiting to deploy
        dependencies_waiting_to_be_deployed = filter_resources_by_state(
            requires, {const.ResourceState.available, const.ResourceState.deploying}
        )
        if dependencies_waiting_to_be_deployed:
            ctx.set_resource_state(const.HandlerResourceState.skipped_for_dependency)
            ctx.info(
                "Resource %(resource)s skipped because some dependencies %(reqs)s "
                "got a new desired state while we were preparing to deploy."
                " We will retry when all dependencies get deployed successfully",
                resource=resource.id.resource_version_str(),
                reqs=str({rid for rid in dependencies_waiting_to_be_deployed.keys()}),
            )
            return

        failed_dependencies = [req for req, status in requires.items() if status != ResourceState.deployed]
        if not any(failed_dependencies):
            execute_and_reload()
        else:
            ctx.set_resource_state(const.HandlerResourceState.skipped_for_dependency)
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

    @abstractmethod
    def check_facts(self, ctx: HandlerContext, resource: TResource) -> dict[str, str]:
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

    def pre(self, ctx: HandlerContext, resource: TResource) -> None:
        """
        Method executed before a handler operation (Facts, dryrun, real deployment, ...) is executed. Override this method
        to run before an operation.

        :param ctx: Context object to report changes and logs to the agent and server.
        :param resource: The resource being handled.
        """

    def post(self, ctx: HandlerContext, resource: TResource) -> None:
        """
        Method executed after a handler operation. Override this method to run after an operation.

        :param ctx: Context object to report changes and logs to the agent and server.
        :param resource: The resource being handled.
        """

    def facts(self, ctx: HandlerContext, resource: TResource) -> dict[str, str]:
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

    def run_sync(self, func: typing.Callable[[], Awaitable[T]]) -> T:
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

        def call() -> Awaitable[Result]:
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

        def call() -> Awaitable[Result]:
            return self.get_client().stat_file(hash_id)

        result = self.run_sync(call)
        return result.code == 200

    def upload_file(self, hash_id: str, content: bytes) -> None:
        """
        Upload a file to the server

        :param hash_id: The id to identify the content. The convention is to use the sha1sum of the content to identify it.
        :param content: A byte string with the content
        """

        def call() -> Awaitable[Result]:
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

    def do_changes(self, ctx: HandlerContext, resource: TResource, changes: Mapping[str, Mapping[str, object]]) -> None:
        """
        Do the changes required to bring the resource on this system in the state of the given resource.

        :param ctx: Context object to report changes and logs to the agent and server.
        :param resource: The resource to check the current state of.
        :param changes: The changes that need to occur as reported by
                        :func:`~inmanta.agent.handler.ResourceHandler.list_changes`
        """
        raise NotImplementedError()

    @tracing.instrument("ResourceHandler.execute", extract_args=True)
    def execute(self, ctx: HandlerContext, resource: TResource, dry_run: bool = False) -> None:
        try:
            with tracing.span("pre"):
                self.pre(ctx, resource)

            with tracing.span("list_changes"):
                changes = self.list_changes(ctx, resource)
                ctx.update_changes(changes)

            if resource.report_only:
                if changes:
                    ctx.set_resource_state(const.HandlerResourceState.non_compliant)
                    ctx.info(
                        msg="Resource %(resource_id)s was marked as non-compliant.",
                        resource_id=resource.id.resource_str(),
                        changes=changes,
                    )
                else:
                    ctx.set_resource_state(const.HandlerResourceState.deployed)
            elif not dry_run:
                with tracing.span("do_changes"):
                    self.do_changes(ctx, resource, changes)
                    ctx.set_resource_state(const.HandlerResourceState.deployed)
            else:
                ctx.set_resource_state(const.HandlerResourceState.dry)
        except SkipResourceForDependencies as e:
            ctx.set_resource_state(const.HandlerResourceState.skipped_for_dependency)
            ctx.warning(
                msg="Resource %(resource_id)s was skipped: %(reason)s",
                resource_id=resource.id.resource_str(),
                reason=e.args,
            )
        except SkipResource as e:
            ctx.set_resource_state(const.HandlerResourceState.skipped)
            ctx.warning(
                msg="Resource %(resource_id)s was skipped: %(reason)s", resource_id=resource.id.resource_str(), reason=e.args
            )
        except Exception as e:
            ctx.set_resource_state(const.HandlerResourceState.failed)
            ctx.exception(
                "An error occurred during deployment of %(resource_id)s (exception: %(exception)s)",
                resource_id=resource.id.resource_str(),
                exception=f"{e.__class__.__name__}('{e}')",
            )
        finally:
            try:
                self.post(ctx, resource)
            except Exception as e:
                ctx.exception(
                    "An error occurred after deployment of %(resource_id)s (exception: %(exception)s)",
                    resource_id=resource.id.resource_str(),
                    exception=f"{e.__class__.__name__}('{e}')",
                )

    @tracing.instrument("ResourceHandler.check_facts", extract_args=True)
    def check_facts(self, ctx: HandlerContext, resource: TResource) -> dict[str, str]:
        """
        This method is called by the agent to query for facts. It runs :func:`~inmanta.agent.handler.HandlerAPI.pre`
        and :func:`~inmanta.agent.handler.HandlerAPI.post`. This method calls
        :func:`~inmanta.agent.handler.HandlerAPI.facts` to do the actual querying.

        :param ctx: Context object to report changes and logs to the agent and server.
        :param resource: The resource to query facts for.
        :return: A dict with fact names as keys and facts values.
        """
        facts: dict[str, str] = {}
        try:
            self.pre(ctx, resource)
            facts = self.facts(ctx, resource)
        finally:
            try:
                self.post(ctx, resource)
            except Exception as e:
                ctx.exception(
                    "An error occurred after getting facts about %(resource_id)s (exception: %(exception)s)",
                    resource_id=resource.id.resource_str(),
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
        :raise SkipResourceForDependencies: Raise this exception when the handler should skip this resource and retry only
            when its dependencies succeed.
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

    def update_resource(self, ctx: HandlerContext, changes: dict[str, dict[str, Any]], resource: TPurgeableResource) -> None:
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
    ) -> dict[str, dict[str, typing.Any]]:
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

    @tracing.instrument("CRUDHandler.execute", extract_args=True)
    def execute(self, ctx: HandlerContext, resource: TPurgeableResource, dry_run: bool = False) -> None:
        try:
            self.pre(ctx, resource)

            # current is clone, except for purged is set to false to prevent a bug that occurs often where the desired
            # state defines purged=true but the read_resource fails to set it to false if the resource does exist
            desired = resource
            current: TPurgeableResource = desired.clone(purged=False)
            changes: dict[str, dict[str, typing.Any]] = {}
            try:
                ctx.debug("Calling read_resource")
                with tracing.span("read_resource"):
                    self.read_resource(ctx, current)

                with tracing.span("calculate_diff"):
                    changes = self.calculate_diff(ctx, current, desired)

            except ResourcePurged:
                if not desired.purged:
                    changes["purged"] = dict(desired=desired.purged, current=True)

            for field, values in changes.items():
                ctx.add_change(field, desired=values["desired"], current=values["current"])

            if resource.report_only:
                if changes:
                    ctx.set_resource_state(const.HandlerResourceState.non_compliant)
                    ctx.info(
                        msg="Resource %(resource_id)s was marked as non-compliant.",
                        resource_id=resource.id.resource_str(),
                        changes=changes,
                    )
                else:
                    ctx.set_resource_state(const.HandlerResourceState.deployed)
            elif not dry_run:
                if "purged" in changes:
                    if not changes["purged"]["desired"]:
                        ctx.debug("Calling create_resource")
                        with tracing.span("create_resource"):
                            self.create_resource(ctx, desired)
                    else:
                        ctx.debug("Calling delete_resource")
                        with tracing.span("delete_resource"):
                            self.delete_resource(ctx, desired)

                elif not desired.purged and len(changes) > 0:
                    ctx.debug("Calling update_resource", changes=changes)
                    with tracing.span("update_resource"):
                        self.update_resource(ctx, dict(changes), desired)

                ctx.set_resource_state(const.HandlerResourceState.deployed)
            else:
                ctx.set_resource_state(const.HandlerResourceState.dry)

        except SkipResourceForDependencies as e:
            ctx.set_resource_state(const.HandlerResourceState.skipped_for_dependency)
            ctx.warning(
                msg="Resource %(resource_id)s was skipped: %(reason)s",
                resource_id=resource.id.resource_str(),
                reason=e.args,
            )
        except SkipResource as e:
            ctx.set_resource_state(const.HandlerResourceState.skipped)
            ctx.warning(
                msg="Resource %(resource_id)s was skipped: %(reason)s", resource_id=resource.id.resource_str(), reason=e.args
            )
        except Exception as e:
            ctx.set_resource_state(const.HandlerResourceState.failed)
            ctx.exception(
                "An error occurred during deployment of %(resource_id)s (exception: %(exception)s)",
                resource_id=resource.id.resource_str(),
                exception=f"{e.__class__.__name__}('{e}')",
                traceback=traceback.format_exc(),
            )
        finally:
            try:
                self.post(ctx, resource)
            except Exception as e:
                ctx.exception(
                    "An error occurred after deployment of %(resource_id)s (exception: %(exception)s)",
                    resource_id=resource.id.resource_str(),
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
          discovered and reported to the server. Objects of this type must be pydantic objects.
    """

    def check_facts(self, ctx: HandlerContext, resource: TDiscovery) -> dict[str, str]:
        return {}

    @abstractmethod
    def discover_resources(self, ctx: HandlerContext, discovery_resource: TDiscovery) -> Mapping[ResourceIdStr, TDiscovered]:
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
                discovered_resources: Sequence[DiscoveredResourceInput],
            ) -> Awaitable[Result]:
                return self.get_client().discovered_resource_create_batch(
                    tid=self._agent.environment,
                    discovered_resources=discovered_resources,
                )

            discovered_resources_raw: Mapping[ResourceIdStr, TDiscovered] = self.discover_resources(ctx, resource)
            discovered_resources: Sequence[DiscoveredResourceInput] = [
                DiscoveredResourceInput(
                    discovered_resource_id=resource_id,
                    values=values.model_dump(),
                    discovery_resource_id=resource.id.resource_str(),
                )
                for resource_id, values in discovered_resources_raw.items()
            ]
            result = self.run_sync(partial(_call_discovered_resource_create_batch, discovered_resources))

            if result.code != 200:
                assert result.result is not None  # Make mypy happy
                ctx.set_resource_state(const.HandlerResourceState.failed)
                error_msg_from_server = f": {result.result['message']}" if "message" in result.result else ""
                ctx.error(
                    "Failed to report discovered resources to the server (status code: %(code)s)%(error_msg_from_server)s",
                    code=result.code,
                    error_msg_from_server=error_msg_from_server,
                )
            else:
                ctx.set_resource_state(const.HandlerResourceState.deployed)
        except SkipResourceForDependencies as e:
            ctx.set_resource_state(const.HandlerResourceState.skipped_for_dependency)
            ctx.warning(
                msg="Resource %(resource_id)s was skipped: %(reason)s",
                resource_id=resource.id,
                reason=e.args,
            )
        except SkipResource as e:
            ctx.set_resource_state(const.HandlerResourceState.skipped)
            ctx.warning(
                msg="Resource %(resource_id)s was skipped: %(reason)s", resource_id=resource.id.resource_str(), reason=e.args
            )
        except Exception as e:
            ctx.set_resource_state(const.HandlerResourceState.failed)
            ctx.exception(
                "An error occurred during deployment of %(resource_id)s (exception: %(exception)s)",
                resource_id=resource.id.resource_str(),
                exception=f"{e.__class__.__name__}('{e}')",
                traceback=traceback.format_exc(),
            )
        finally:
            try:
                self.post(ctx, resource)
            except Exception as e:
                ctx.exception(
                    "An error occurred after deployment of %(resource_id)s (exception: %(exception)s)",
                    resource_id=resource.id.resource_str(),
                    exception=f"{e.__class__.__name__}('{e}')",
                )


class Commander:
    """
    This class handles commands
    """

    __command_functions: dict[str, type[ResourceHandler[Any]]] = {}

    @classmethod
    def get_handlers(cls) -> dict[str, type[ResourceHandler[Any]]]:
        return cls.__command_functions

    @classmethod
    def reset(cls) -> None:
        cls.__command_functions = {}

    @classmethod
    def close(cls) -> None:
        pass

    @classmethod
    def get_provider(cls, agent: "inmanta.agent.executor.AgentInstance", resource: resources.Resource) -> HandlerAPI[Any]:
        """
        Return a provider to handle the given resource
        """
        resource_type = resource.id.get_entity_type()

        if resource_type not in cls.__command_functions:
            raise Exception("No resource handler registered for resource of type %s" % resource_type)

        return cls.__command_functions[resource_type](agent)

    @classmethod
    def add_provider(cls, resource: str, provider: type[ResourceHandler[Any]]) -> None:
        """
        Register a new provider

        :param resource: the name of the resource this handler applies to
        :param provider: the handler function
        """
        # When a new version of a handler is available, it will register and should replace the existing one.
        cls.__command_functions[resource] = provider

    @classmethod
    def get_providers(cls) -> typing.Iterator[tuple[str, type[ResourceHandler[Any]]]]:
        """Return an iterator over resource type, handler definition"""
        for resource_type, handler_class in cls.__command_functions.items():
            yield (resource_type, handler_class)

    @classmethod
    def get_provider_class(cls, resource_type: str, name: str) -> Optional[type[ResourceHandler[Any]]]:
        """Return the class of the handler for the given type and with the given name"""
        return cls.__command_functions.get(resource_type, None)


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
