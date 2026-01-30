"""
Copyright 2023 Inmanta

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

import asyncio
import contextlib
import dataclasses
import datetime
import enum
import functools
import hashlib
import importlib.metadata
import inspect
import itertools
import json
import logging
import os
import pathlib
import socket
import threading
import time
import typing
import uuid
import warnings
from abc import ABC, abstractmethod
from asyncio import AbstractEventLoop, CancelledError, Lock, Task, ensure_future, gather
from collections import abc, defaultdict
from collections.abc import Awaitable, Callable, Collection, Coroutine, Iterable, Iterator, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from logging import Logger
from types import TracebackType
from typing import TYPE_CHECKING, BinaryIO, Generic, Optional, TypeVar, Union

import asyncpg
import click
import pydantic
from tornado import gen

import packaging
import packaging.requirements
import packaging.utils
import pydantic_core
from crontab import CronTab
from inmanta import COMPILER_VERSION, const, types
from inmanta.stable_api import stable_api
from inmanta.types import JsonType, PrimitiveTypes, ReturnTypes
from packaging.utils import NormalizedName

if TYPE_CHECKING:
    from inmanta.data.model import ResourceId

LOGGER = logging.getLogger(__name__)
SALT_SIZE = 16
HASH_ROUNDS = 100000

T = TypeVar("T")
S = TypeVar("S")


def get_compiler_version() -> str:
    return COMPILER_VERSION


def groupby(mylist: list[T], f: Callable[[T], S]) -> Iterator[tuple[S, Iterator[T]]]:
    return itertools.groupby(sorted(mylist, key=f), f)


def ensure_directory_exist(directory: str, *subdirs: str) -> str:
    directory = os.path.join(directory, *subdirs)
    if not os.path.exists(directory):
        os.mkdir(directory)
    return directory


def is_sub_dict(subdct: dict[PrimitiveTypes, PrimitiveTypes], dct: dict[PrimitiveTypes, PrimitiveTypes]) -> bool:
    return not any(True for k, v in subdct.items() if k not in dct or dct[k] != v)


def strtobool(val: str) -> bool:
    """Convert a string representation of truth to True or False.

    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.

    This function is based on a function in the Python distutils package. Is is subject
    to the following license:

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to
    deal in the Software without restriction, including without limitation the
    rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
    sell copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in
    all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
    IN THE SOFTWARE.
    """
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    elif val in ("n", "no", "f", "false", "off", "0"):
        return False
    else:
        raise ValueError("invalid truth value %r" % (val,))


def hash_file(content: bytes) -> str:
    """
    Create a hash from the given content
    """
    sha1sum = hashlib.new("sha1")
    sha1sum.update(content)

    return sha1sum.hexdigest()


def hash_file_streaming(file_handle: BinaryIO) -> str:
    h = hashlib.new("sha1")
    while True:
        # Reading is buffered, so we can read smaller chunks.
        chunk = file_handle.read(h.block_size)
        if not chunk:
            break
        h.update(chunk)

    return h.hexdigest()


def is_call_ok(result: Union[int, tuple[int, JsonType]]) -> bool:
    if isinstance(result, tuple):
        if len(result) == 2:
            code, reply = result
        else:
            raise Exception("Handlers for method call can only return a status code and a reply")

    else:
        code = result

    return code == 200


def ensure_future_and_handle_exception(
    logger: Logger, msg: str, action: Coroutine[object, None, T], notify_done_callback: Callable[[Task[T]], None]
) -> Task[T]:
    """Fire off a coroutine from the ioloop thread and log exceptions to the logger with the message"""
    future: Task[T] = ensure_future(action)

    def handler(task: Task[T]) -> None:
        try:
            exc = task.exception()
            if exc is not None:
                logger.exception(msg, exc_info=exc)
        except CancelledError:
            pass
        finally:
            notify_done_callback(task)

    future.add_done_callback(handler)
    return future


# In this module we use Coroutine[object, None, T] instead of Awaitable[T]. The reason for this is:
# - We use the methods here to background coroutines, which generates tasks.
# - Future is a subclass of Awaitable
# - ensure_future which is used in a number of methods here, returns Task unless you pass it a future.
# By only allowing Coroutines, we can make the typing more strict and only consider tasks.

TaskMethod = Callable[[], Coroutine[object, None, object]]


@stable_api
class TaskSchedule(ABC):
    """
    Abstract base class for a task schedule specification. Offers methods to inspect when the task should be scheduled, relative
    to the current time. Stateless.
    """

    @abstractmethod
    def get_initial_delay(self) -> float:
        """
        Returns the number of seconds from now until this task should be scheduled for the first time.
        """

    @abstractmethod
    def get_next_delay(self) -> float:
        """
        Returns the number of seconds from now until this task should be scheduled again. Uses the current time as reference,
        i.e. assumes the task has already run at least once and a negligible amount of time has passed since the last run
        completed.
        """

    @abstractmethod
    def log(self, action: TaskMethod) -> None:
        """
        Log a message about the action being scheduled according to this schedule.
        """


@stable_api
@dataclass(frozen=True)
class ScheduledTask:
    action: TaskMethod
    schedule: TaskSchedule


@stable_api
@dataclass(frozen=True)
class IntervalSchedule(TaskSchedule):
    """
    Simple interval schedule for tasks.

    :param interval: The interval in seconds between execution of actions.
    :param initial_delay: Delay in seconds to the first execution. If not set, interval is used.
    """

    interval: float
    initial_delay: Optional[float] = None

    def get_initial_delay(self) -> float:
        return self.initial_delay if self.initial_delay is not None else self.interval

    def get_next_delay(self) -> float:
        return self.interval

    def log(self, action: TaskMethod) -> None:
        LOGGER.debug(
            "Scheduling action %s every %d seconds with initial delay %d", action, self.interval, self.get_initial_delay()
        )


@stable_api
@dataclass(frozen=True)
class CronSchedule(TaskSchedule):
    """
    Current-time based scheduler: interval is calculated dynamically based on cron specifier and current time. Cron schedule is
    always interpreted as UTC.
    """

    cron: str
    _crontab: CronTab = dataclasses.field(init=False, compare=False)

    def __post_init__(self) -> None:
        crontab: CronTab
        try:
            crontab = CronTab(self.cron)
        except ValueError as e:
            raise ValueError(f"'{self.cron}' is not a valid cron expression: {e}")
        # can not assign directly on frozen dataclass, see dataclass docs
        object.__setattr__(self, "_crontab", crontab)

    def get_initial_delay(self) -> float:
        # no special treatment for first execution
        return self.get_next_delay()

    def get_next_delay(self) -> float:
        # always interpret cron schedules as UTC
        now: datetime.datetime = datetime.datetime.now(datetime.timezone.utc)
        return self._crontab.next(now=now)

    def log(self, action: TaskMethod) -> None:
        LOGGER.debug("Scheduling action %s according to cron specifier '%s'", action, self.cron)


def is_coroutine(function: object) -> bool:
    return (
        inspect.iscoroutinefunction(function)
        or gen.is_coroutine_function(function)
        or isinstance(function, functools.partial)
        and is_coroutine(function.func)
    )


@stable_api
class Scheduler:
    """
    An event scheduler class. Identifies tasks based on an action and a schedule. Considers tasks with the same action and the
    same schedule to be the same. Callers that wish to be able to delete the tasks they add should make sure to use unique
    `call` functions.
    Assumes an event loop is already running on this thread.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._scheduled: dict[ScheduledTask, asyncio.TimerHandle] = {}
        self._stopped = False
        # Keep track of all tasks that are currently executing to be
        # able to cancel them when the scheduler is stopped.
        self._executing_tasks: dict[TaskMethod, list[asyncio.Task[object]]] = defaultdict(list)
        # Keep track of tasks that should be awaited before the scheduler is stopped
        self._await_tasks: dict[TaskMethod, list[asyncio.Task[object]]] = defaultdict(list)

    def _add_to_executing_tasks(self, action: TaskMethod, task: asyncio.Task[object], cancel_on_stop: bool = True) -> None:
        """
        Add task that is currently executing to `self._executing_tasks`.
        """
        # requires: RequiresProvidesMapping = dataclasses.field(default_factory=RequiresProvidesMapping)
        # # types per agent keeps track of which resource types live on which agent by doing a reference count
        # # the dict is agent_name -> resource_type -> resource_count
        # types_per_agent: dict[str, dict["ResourceType", int]] = dataclasses.field(
        #     default_factory=lambda: defaultdict(lambda: defaultdict(lambda: 0))
        # )
        if action in self._executing_tasks and self._executing_tasks[action]:
            LOGGER.warning("Multiple instances of background task %s are executing simultaneously", action.__name__)
        self._executing_tasks[action].append(task)
        if not cancel_on_stop:
            self._await_tasks[action].append(task)

    def _notify_done(self, action: TaskMethod, task: asyncio.Task[object]) -> None:
        """
        Called by the callback function of executing task when the task has finished executing.
        """

        def remove_action_from_task_dict(task_dict: dict[TaskMethod, list[asyncio.Task[object]]]) -> None:
            if action in task_dict:
                try:
                    task_dict[action].remove(task)
                except ValueError:
                    pass

        for task_dict in [self._executing_tasks, self._await_tasks]:
            remove_action_from_task_dict(task_dict)

    @stable_api
    def add_action(
        self,
        action: TaskMethod,
        schedule: Union[TaskSchedule, int],  # int for backward compatibility,
        cancel_on_stop: bool = True,
        quiet_mode: bool = False,
    ) -> Optional[ScheduledTask]:
        """
        Add a new action

        :param action: A function to call periodically
        :param schedule: The schedule for this action
        :param cancel_on_stop: Cancel the task when the scheduler is stopped. If false, the coroutine will be awaited.
        :param quiet_mode: Set to true to disable logging the recurring  notification that the action is being called.
        Use this to avoid polluting the server log for very frequent actions.
        """
        assert is_coroutine(action)

        if self._stopped:
            LOGGER.warning("Scheduling action '%s', while scheduler is stopped", action.__name__)
            return None

        schedule_typed: TaskSchedule
        if isinstance(schedule, int):
            schedule_typed = IntervalSchedule(schedule)
        else:
            schedule_typed = schedule

        schedule_typed.log(action)

        task_spec: ScheduledTask = ScheduledTask(action, schedule_typed)
        if task_spec in self._scheduled:
            # start fresh to respect initial delay, if set
            self.remove(task_spec)

        def action_function() -> None:
            if not quiet_mode:
                LOGGER.info("Calling %s", action.__name__)
            if task_spec in self._scheduled:
                try:
                    task = ensure_future_and_handle_exception(
                        logger=LOGGER,
                        msg="Uncaught exception while executing scheduled action",
                        action=action(),
                        notify_done_callback=functools.partial(self._notify_done, action),
                    )
                    self._add_to_executing_tasks(action, task, cancel_on_stop)
                except Exception:
                    LOGGER.exception("Uncaught exception while executing scheduled action")
                finally:
                    # next iteration
                    ihandle = asyncio.get_running_loop().call_later(schedule_typed.get_next_delay(), action_function)
                    self._scheduled[task_spec] = ihandle

        handle: asyncio.TimerHandle = asyncio.get_running_loop().call_later(schedule_typed.get_initial_delay(), action_function)
        self._scheduled[task_spec] = handle
        return task_spec

    @stable_api
    def remove(self, task: ScheduledTask) -> None:
        """
        Remove a scheduled action
        """
        if task in self._scheduled:
            self._scheduled[task].cancel()
            del self._scheduled[task]

    @stable_api
    async def stop(self) -> None:
        """
        Stop the scheduler
        """
        self._stopped = True
        try:
            # remove can still run during stop. That is why we loop until we get a keyerror == the dict is empty
            while True:
                _, handle = self._scheduled.popitem()
                handle.cancel()
        except KeyError:
            pass

        # Cancel all tasks that are already executing
        for action, tasks in self._executing_tasks.items():
            for task in tasks:
                if task not in self._await_tasks[action]:
                    task.cancel()

        results = await gather(
            *[handle for handles in self._await_tasks.values() for handle in handles], return_exceptions=True
        )

        # Log any exception that happened during shutdown
        for result in results:
            if isinstance(result, CancelledError):
                # Ignore this, it is ok to leak a cancel here
                pass
            if isinstance(result, Exception):
                LOGGER.error("Exception during shutdown", exc_info=result)

    def __del__(self) -> None:
        if len(self._scheduled) > 0:
            warnings.warn("Deleting scheduler '%s' that has not been stopped properly." % self.name)


def get_free_tcp_port() -> str:
    """
    Semi safe method for getting a random port. This may contain a race condition.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp:
        tcp.bind(("", 0))
        _addr, port = tcp.getsockname()
        return str(port)


def datetime_iso_format(timestamp: datetime.datetime, *, tz_aware: bool = True) -> str:
    """
    Returns a timestamp ISO string.


    :param timestamp: The timestamp to get the ISO string for.
    :param tz_aware: Whether to return timezone aware timestamps or naive, implicit UTC timestamp.
    """

    def convert_timestamp() -> datetime.datetime:
        if tz_aware:
            if timestamp.tzinfo:
                return timestamp
            return timestamp.replace(tzinfo=datetime.timezone.utc)

        if timestamp.tzinfo:
            return timestamp.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return timestamp

    return convert_timestamp().isoformat(timespec="microseconds")


def parse_timestamp(timestamp: str) -> datetime.datetime:
    """
    Parse a timestamp into a timezone aware object. Naive timestamps are assumed to be UTC.
    """
    try:
        return datetime.datetime.strptime(timestamp, const.TIME_ISOFMT + "%z")
    except ValueError:
        # interpret naive datetimes as UTC
        return datetime.datetime.strptime(timestamp, const.TIME_ISOFMT).replace(tzinfo=datetime.timezone.utc)


class JSONSerializable(ABC):
    """
    Instances of this class are JSON serializable. Concrete subclasses should implement json_serialization_step.
    """

    @abstractmethod
    def json_serialization_step(self) -> Union[ReturnTypes, "JSONSerializable"]:
        """
        Perform a step in the serialization process. Returns an other serializable object.
        The implementation should make sure each step progresses serialization so that successively
        calling JSONSerializable.default eventually resolves to a trivially serializable object.
        """
        raise NotImplementedError()


@stable_api
def internal_json_encoder(o: object) -> Union[ReturnTypes, "JSONSerializable"]:
    """
    A custom json encoder that knows how to encode other types commonly used by Inmanta from standard python libraries. This
    encoder is meant to be used internally.
    """
    if isinstance(o, datetime.datetime):
        # Internally, all naive datetime instances are assumed local. Returns ISO timestamp with explicit timezone offset.
        return _custom_json_encoder(o if o.tzinfo is not None else o.astimezone())

    return _custom_json_encoder(o)


@stable_api
def api_boundary_json_encoder(o: object, tz_aware: bool = True) -> Union[ReturnTypes, "JSONSerializable"]:
    """
    A custom json encoder that knows how to encode other types commonly used by Inmanta from standard python libraries. This
    encoder is meant to be used for API boundaries.
    :param tz_aware: Whether to serialize timestamps as timezone aware objects or as naive implicit UTC.
    """
    if isinstance(o, datetime.datetime):
        # Accross API boundaries, all naive datetime instances are assumed UTC.
        return datetime_iso_format(o, tz_aware=tz_aware)

    return _custom_json_encoder(o)


def _custom_json_encoder(o: object) -> Union[ReturnTypes, "JSONSerializable"]:
    """
    A custom json encoder that knows how to encode other types commonly used by Inmanta from standard python libraries
    """
    if isinstance(o, JSONSerializable):
        return o.json_serialization_step()

    if isinstance(o, (uuid.UUID, pydantic.AnyUrl, pydantic_core.Url)):
        return str(o)

    if isinstance(o, datetime.datetime):
        return o.isoformat(timespec="microseconds")

    if hasattr(o, "to_dict"):
        return o.to_dict()  # type: ignore

    if isinstance(o, enum.Enum):
        return o.name

    if isinstance(o, Exception):
        # Logs can push exceptions through RPC. Return a string representation.
        return str(o)

    from inmanta.data.model import BaseModel

    if isinstance(o, (BaseModel, pydantic.BaseModel)):
        return o.model_dump(by_alias=True)

    if dataclasses.is_dataclass(o) and not isinstance(o, type):
        return dataclasses.asdict(o)

    LOGGER.error("Unable to serialize %s", o)
    raise TypeError(repr(o) + " is not JSON serializable")


def add_future(future: Coroutine[object, None, T]) -> Task[T]:
    """
    Add a future to the ioloop to be handled, but do not require the result.
    """

    def handle_result(f: Task[T]) -> None:
        try:
            f.result()
        except Exception as e:
            LOGGER.exception("An exception occurred while handling a future: %s", str(e))

    task = ensure_future(future)
    task.add_done_callback(handle_result)
    return task


async def retry_limited(
    fun: Union[abc.Callable[..., bool], abc.Callable[..., abc.Awaitable[bool]]],
    timeout: float,
    interval: float = 0.1,
    *args: object,
    **kwargs: object,
) -> None:
    """
    This function makes use of the INMANTA_RETRY_LIMITED_MULTIPLIER env variable. If set, INMANTA_RETRY_LIMITED_MULTIPLIER
    serves as multiplier: The timeout given as argument becomes a 'soft limit' and the 'soft limit' multiplied by the
    multiplier (from the env var) becomes a 'hard limit'. If the hard limit is reached before the wait condition is fulfilled
    a Timeout exception is raised. If the wait condition is fulfilled before the hard limit is reached but after the soft
    limit is reached, a different Timeout exception is raised. if the Env var is not set, then the soft and hard limit are
    the same.
    """

    async def fun_wrapper() -> bool:
        if inspect.iscoroutinefunction(fun):
            return await fun(*args, **kwargs)
        else:
            return fun(*args, **kwargs)

    multiplier: int = int(os.environ.get("INMANTA_RETRY_LIMITED_MULTIPLIER", 1))
    if multiplier < 1:
        raise ValueError("value of INMANTA_RETRY_LIMITED_MULTIPLIER must be bigger or equal to 1.")
    hard_timeout = timeout * multiplier
    start = time.time()
    result = await fun_wrapper()
    while time.time() - start < hard_timeout and not result:
        await asyncio.sleep(interval)
        result = await fun_wrapper()
    if not result:
        raise asyncio.TimeoutError(f"Wait condition was not reached after hard limit of {hard_timeout} seconds")
    if time.time() - start > timeout:
        raise asyncio.TimeoutError(
            f"Wait condition was met after {time.time() - start} seconds, but soft limit was set to {timeout} seconds"
        )


class StoppedException(Exception):
    """This exception is raised when a background task is added to the taskhandler when it is shutting down."""


class TaskHandler(Generic[T]):
    """
    This class provides a method to add a background task based on a coroutine. When the coroutine ends, any exceptions
    are reported. If stop is invoked, all background tasks are cancelled.
    """

    def __init__(self) -> None:
        super().__init__()
        self._background_tasks: set[Task[T]] = set()
        self._await_tasks: set[Task[T]] = set()
        self._stopped = False

    def is_stopped(self) -> bool:
        return self._stopped

    def is_running(self) -> bool:
        return not self._stopped

    def add_background_task(self, future: Awaitable[T], cancel_on_stop: bool = True) -> Task[T]:
        """Add a background task to the event loop. When stop is called, the task is cancelled.

        :param future: The future or coroutine to run as background task.
        :param cancel_on_stop: Cancel the task when stop is called. If false, the coroutine is awaited.
        """
        if self._stopped:
            LOGGER.warning("Not adding background task because we are stopping.")
            raise StoppedException("A background tasks are not added to the event loop while stopping")

        task: Task[T] = ensure_future(future)

        def handle_result(task: Task[T]) -> None:
            try:
                task.result()
            except CancelledError:
                LOGGER.warning("Task %s was cancelled.", task)

            except Exception as e:
                LOGGER.exception("An exception occurred while handling a future: %s", str(e))
            finally:
                self._background_tasks.discard(task)
                self._await_tasks.discard(task)

        task.add_done_callback(handle_result)
        self._background_tasks.add(task)

        if not cancel_on_stop:
            self._await_tasks.add(task)

        return task

    async def stop(self) -> None:
        """Stop all background tasks by requesting a cancel"""
        self._stopped = True
        await gather(*self._await_tasks)
        self._background_tasks.difference_update(self._await_tasks)

        cancelled_tasks = []
        try:
            while True:
                task = self._background_tasks.pop()
                task.cancel()
                cancelled_tasks.append(task)
        except KeyError:
            pass

        await gather(*cancelled_tasks, return_exceptions=True)


class CycleException(Exception):
    def __init__(self, node: str) -> None:
        self.nodes = [node]
        self.done = False

    def add(self, node: str) -> None:
        if not self.done:
            if node not in self.nodes:
                self.nodes.insert(0, node)
            else:
                self.done = True


def stable_depth_first(nodes: Collection[str], edges: Mapping[str, Collection[str]]) -> list[str]:
    """Creates a linear sequence based on a set of "comes after" edges, same graph yields the same solution,
    independent of order given to this function"""
    nodes = sorted(nodes)
    edges = {k: sorted(v) for k, v in edges.items()}
    out = []

    def dfs(node: str, seen: set[str] = set()) -> None:
        if node in out:
            return
        if node in seen:
            raise CycleException(node)
        try:
            if node in edges:
                for edge in edges[node]:
                    dfs(edge, seen | {node})
            out.append(node)
        except CycleException as e:
            e.add(node)
            raise e

    while nodes:
        dfs(nodes.pop(0))

    return out


class NamedSubLock:
    def __init__(self, parent: "NamedLock", name: str) -> None:
        self.parent = parent
        self.name = name

    async def __aenter__(self) -> None:
        await self.parent.acquire(self.name)

    async def __aexit__(
        self, exc_type: Optional[type[BaseException]], exc_value: Optional[BaseException], traceback: Optional[TracebackType]
    ) -> None:
        await self.parent.release(self.name)


class NamedLock:
    """Create fine grained locks"""

    def __init__(self) -> None:
        self._master_lock: Lock = Lock()
        self._named_locks: dict[str, Lock] = {}
        self._named_locks_counters: dict[str, int] = {}

    def get(self, name: str) -> NamedSubLock:
        return NamedSubLock(self, name)

    async def acquire(self, name: str) -> None:
        async with self._master_lock:
            if name in self._named_locks:
                lock = self._named_locks[name]
                self._named_locks_counters[name] += 1
            else:
                lock = Lock()
                self._named_locks[name] = lock
                self._named_locks_counters[name] = 1
        await lock.acquire()

    async def release(self, name: str) -> None:
        async with self._master_lock:
            lock = self._named_locks[name]
            lock.release()
            self._named_locks_counters[name] -= 1
            # This relies on the internal mechanics of the lock
            if self._named_locks_counters[name] <= 0:
                del self._named_locks[name]
                del self._named_locks_counters[name]


class nullcontext(contextlib.nullcontext[T], contextlib.AbstractAsyncContextManager[T]):
    """
    nullcontext ported from Python 3.10 to support async
    """

    async def __aenter__(self) -> T:
        return self.enter_result

    async def __aexit__(self, *excinfo: object) -> None:
        pass


class FinallySet(contextlib.AbstractAsyncContextManager[asyncio.Event]):
    def __init__(self, event: asyncio.Event) -> None:
        self.event = event

    async def __aenter__(self) -> asyncio.Event:
        return self.event

    async def __aexit__(self, *exc_info: object) -> None:
        self.event.set()


async def join_threadpools(threadpools: list[ThreadPoolExecutor]) -> None:
    """
    Asynchronously join a set of threadpools

    idea borrowed from BaseEventLoop.shutdown_default_executor

    We implemented this method because:
    1. ThreadPoolExecutor.shutdown(wait=True)` is a blocking call, blocking the ioloop.
       This doesn't work because we often have back-and-forth between the ioloop and the thread
       due to our `ResourceHandler.run_sync` method.
    2.The python sdk has no support for async awaiting threadpool shutdown (except for the default pool)
    """

    loop = asyncio.get_running_loop()
    future = loop.create_future()

    def join() -> None:
        for threadpool in threadpools:
            try:
                threadpool.shutdown(wait=True)
            except Exception:
                LOGGER.exception("Exception during threadpool shutdown")
        loop.call_soon_threadsafe(future.set_result, None)

    thread = threading.Thread(target=join)
    thread.start()
    try:
        await future
    finally:
        thread.join()


def ensure_event_loop() -> asyncio.AbstractEventLoop:
    """
    Returns the event loop for this thread. Creates a new one if none exists yet and registers it with asyncio's active event
    loop policy. Does not ensure that the event loop is running.
    """
    try:
        # nothing needs to be done if this thread already has an event loop
        # known issue: asyncio offers no way to get the active event loop if it's not running. So we may be too eager
        #   in creating a new one.
        return asyncio.get_running_loop()
    except RuntimeError:
        # asyncio.set_event_loop sets the event loop for this thread only
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        return new_loop


def wait_sync[T](
    awaitable: Awaitable[T] | asyncio.Future[T],
    *,
    timeout: int = 120,
    ioloop: Optional[asyncio.AbstractEventLoop] = None,
) -> T:
    """
    Blocks on an async awaitable from a syncronous context. Must not be called from an async context.

    Must not be called from handlers, see Handler.run_sync for that.

    :param ioloop: await on an existing io loop, on another thread.
    If not given, the default loop (see `get_default_event_loop()`) is used.
    If it is not set an io loop is started on the current thread.
    """
    with_timeout: types.AsyncioCoroutine[T] = asyncio.wait_for(awaitable, timeout)

    if ioloop is None:
        # Fallback to ensure the agent doesn't leak ioloops via its threadpool
        ioloop = get_default_event_loop()

    if ioloop is not None:
        # run it on the given loop
        return asyncio.run_coroutine_threadsafe(with_timeout, ioloop).result()
    # no running loop given: create a loop for this thread if it doesn't exist already and run it
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # no loop running for this thread. Use asyncio.run
        return asyncio.run(with_timeout)
    else:
        raise Exception("wait_sync can not be called from an async context")


class ExhaustedPoolWatcher:
    """
    This class keeps track of database pool exhaustion events and offers reporting capabilities.

    """

    def __init__(self, pool: asyncpg.pool.Pool) -> None:
        self._exhausted_pool_events_count: int = 0
        self._last_report: int = 0
        self._pool: asyncpg.pool.Pool = pool

    def report_and_reset(self, logger: logging.Logger) -> None:
        """
        Log how many exhausted pool events were recorded since the last time the counter
        was reset, if any, and reset the counter.
        """
        since_last = self._exhausted_pool_events_count - self._last_report
        if since_last > 0:
            logger.warning("Database pool was exhausted %d times in the past 24h.", since_last)
            self._last_report = self._exhausted_pool_events_count

    def check_for_pool_exhaustion(self) -> None:
        """
        Checks if the database pool is exhausted
        """
        pool_exhausted: bool = (self._pool.get_size() == self._pool.get_max_size()) and self._pool.get_idle_size() == 0
        if pool_exhausted:
            self._exhausted_pool_events_count += 1


def remove_comment_part_from_specifier(to_clean: str) -> str:
    """
    Remove the comment part of a requirement specifier

    :param to_clean: The requirement specifier to clean
    :return: A cleaned requirement specifier
    """
    # Refer to PEP 508. A requirement could contain a hashtag
    to_clean = to_clean.strip()
    drop_comment, _, _ = to_clean.partition(" #")
    # We make sure whitespaces are not counted in the length of this string, e.g. "        #"
    drop_comment = drop_comment.strip()
    return drop_comment


if typing.TYPE_CHECKING:

    class CanonicalRequirement(packaging.requirements.Requirement):
        name: NormalizedName

        def __init__(self, requirement: packaging.requirements.Requirement) -> None:
            raise Exception("Typing dummy, should never be seen")

else:
    CanonicalRequirement = typing.NewType("CanonicalRequirement", packaging.requirements.Requirement)
    """
    A CanonicalRequirement is a packaging.requirements.Requirement except that the name of this Requirement is canonicalized,
    which allows us to compare names without dealing afterwards with the format of these requirements.
    """


def parse_requirement(requirement: str) -> CanonicalRequirement:
    """
    Parse the given requirement string into a requirement object with a canonicalized name, meaning that we are sure that
    every CanonicalRequirement will follow the same convention regarding the name. This will allow us compare requirements.
    This function supposes to receive an actual requirement.

    :param requirement: The requirement's name
    :return: A new requirement instance
    """
    # We canonicalize the name of the requirement to be able to compare requirements and check if the requirement is
    # already installed
    # The following line could cause issue because we are not supposed to modify fields of an existing instance
    # The version of packaging is constrained to ensure this can not cause problems in production.
    requirement_instance = packaging.requirements.Requirement(requirement_string=requirement)
    requirement_instance.name = packaging.utils.canonicalize_name(requirement_instance.name)
    canonical_requirement_instance = CanonicalRequirement(requirement_instance)
    return canonical_requirement_instance


def parse_requirements(requirements: Sequence[str]) -> list[CanonicalRequirement]:
    """
    Parse the given requirements (sequence of strings) into requirement objects with a canonicalized name, meaning that we
    are sure that every CanonicalRequirement will follow the same convention regarding the name. This will allow us compare
    requirements. This function supposes to receive actual requirements. Commented strings will not be handled and result in
    a ValueError

    :param requirements: The names of the different requirements
    :return: list[CanonicalRequirement]
    """
    return [parse_requirement(requirement=e) for e in requirements]


def parse_requirements_from_file(file_path: pathlib.Path) -> list[CanonicalRequirement]:
    """
    Parse the given requirements (line by line) from a file into requirement objects with a canonicalized name, meaning that we
    are sure that every CanonicalRequirement will follow the same convention regarding the name. This will allow us compare
    requirements.

    :param file_path: The path to the read the requirements from
    :return: list[CanonicalRequirement]
    """
    if not file_path.exists():
        raise RuntimeError(f"The provided path does not exist: `{file_path}`!")

    with open(file_path) as f:
        file_contents: list[str] = f.readlines()
        requirements = [
            parse_requirement(remove_comment_part_from_specifier(line))
            for line in file_contents
            if (stripped := line.lstrip()) and not stripped.startswith("#")  # preprocessing
        ]

    return requirements


# Retaken from the `click-plugins` repo which is now unmaintained
def click_group_with_plugins(plugins: Iterable[importlib.metadata.EntryPoint]) -> Callable[[click.Group], click.Group]:
    """
    A decorator to register external CLI commands to an instance of `click.Group()`.

    :param plugins: An iterable producing one `pkg_resources.EntryPoint()` per iteration
    :return: The provided click group with the new commands
    """

    def decorator(group: click.Group) -> click.Group:
        for entry_point in plugins:
            try:
                group.add_command(entry_point.load())
            except Exception as e:
                # Catch this so a busted plugin doesn't take down the CLI.
                # Handled by registering a dummy command that does nothing
                # other than explain the error.
                def print_error(error: Exception) -> None:
                    click.echo(f"Error: could not load this plugin for the following reason: {error}")

                new_print_error = functools.partial(print_error, e)
                group.add_command(click.Command(name=entry_point.name, callback=new_print_error))

        return group

    return decorator


def make_attribute_hash(resource_id: "ResourceId", attributes: Mapping[str, object]) -> str:
    """
    This method returns the attribute hash for the attributes of the given resource.
    """
    from inmanta.protocol.common import custom_json_encoder

    character = json.dumps(
        {k: v for k, v in attributes.items() if k not in ["requires", "provides", "version"]},
        default=custom_json_encoder,
        sort_keys=True,  # sort the keys for stable hashes when using dicts, see #5306
    )
    m = hashlib.md5()
    m.update(resource_id.encode("utf-8"))
    m.update(character.encode("utf-8"))
    return m.hexdigest()


def get_pkg_name_and_version(path_distribution_pkg: str) -> tuple[str, str]:
    """
    Returns a tuple that holds the name and version number of the given
    distribution package. This method is compatible with both wheels and sdist packages.

    Sdist file format: `{name}-{version}.tar.gz`
    Wheel file format: `{distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl`
    """
    filename = os.path.basename(path_distribution_pkg)
    if filename.endswith(".tar.gz"):
        filename = filename.removesuffix(".tar.gz")
    pkg_name, version = filename.split("-")[0:2]
    normalized_pkg_name = parse_requirement(pkg_name.removeprefix("inmanta-module-")).name
    return normalized_pkg_name, version


def get_module_name(path_distribution_pkg: str) -> str:
    """
    Returns the name of the Inmanta module that belongs to the given python package.
    """
    filename = os.path.basename(path_distribution_pkg)
    pkg_name: str = filename.split("-", maxsplit=1)[0]
    return pkg_name.removeprefix("inmanta_module_")


default_event_loop: AbstractEventLoop | None = None


def set_default_event_loop(eventloop: AbstractEventLoop | None) -> None:
    global default_event_loop
    default_event_loop = eventloop


@stable_api
def get_default_event_loop() -> AbstractEventLoop | None:
    """
    Returns the default event loop.

    This is intended to be used by other threads, that want to run code on the eventloop of the main thread.

    It should be used to prevent leaking eventloops when using threadpools.
    The main use case is the `Client` class

    Only thread safe methods of the eventloop should be used.

    If an event loop is returned it will be running.
    """
    return default_event_loop
