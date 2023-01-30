"""
    Copyright 2022 Inmanta

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
import inspect
import itertools
import logging
import os
import socket
import time
import uuid
import warnings
from abc import ABC, abstractmethod
from asyncio import CancelledError, Future, Lock, Task, ensure_future, gather
from collections import abc, defaultdict
from dataclasses import dataclass
from logging import Logger
from types import TracebackType
from typing import Awaitable, BinaryIO, Callable, Coroutine, Dict, Iterator, List, Optional, Set, Tuple, Type, TypeVar, Union

from tornado import gen
from tornado.ioloop import IOLoop

from crontab import CronTab
from inmanta import COMPILER_VERSION
from inmanta.stable_api import stable_api
from inmanta.types import JsonType, PrimitiveTypes, ReturnTypes

LOGGER = logging.getLogger(__name__)
SALT_SIZE = 16
HASH_ROUNDS = 100000

T = TypeVar("T")
S = TypeVar("S")


def get_compiler_version() -> str:
    return COMPILER_VERSION


def groupby(mylist: List[T], f: Callable[[T], S]) -> Iterator[Tuple[S, Iterator[T]]]:
    return itertools.groupby(sorted(mylist, key=f), f)


def ensure_directory_exist(directory: str, *subdirs: str) -> str:
    directory = os.path.join(directory, *subdirs)
    if not os.path.exists(directory):
        os.mkdir(directory)
    return directory


def is_sub_dict(subdct: Dict[PrimitiveTypes, PrimitiveTypes], dct: Dict[PrimitiveTypes, PrimitiveTypes]) -> bool:
    return not any(True for k, v in subdct.items() if k not in dct or dct[k] != v)


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


def is_call_ok(result: Union[int, Tuple[int, JsonType]]) -> bool:
    if isinstance(result, tuple):
        if len(result) == 2:
            code, reply = result
        else:
            raise Exception("Handlers for method call can only return a status code and a reply")

    else:
        code = result

    return code == 200


def ensure_future_and_handle_exception(
    logger: Logger, msg: str, action: Awaitable[T], notify_done_callback: Callable[[asyncio.Task[T]], None]
) -> asyncio.Task[T]:
    """Fire off a coroutine from the ioloop thread and log exceptions to the logger with the message"""
    future = ensure_future(action)

    def handler(future):
        try:
            exc = future.exception()
            if exc is not None:
                logger.exception(msg, exc_info=exc)
        except CancelledError:
            pass
        finally:
            notify_done_callback(future)

    future.add_done_callback(handler)
    return future


TaskMethod = Callable[[], Awaitable[object]]


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
            raise ValueError("'%s' is not a valid cron expression: %s" % (self.cron, e))
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
class Scheduler(object):
    """
    An event scheduler class. Identifies tasks based on an action and a schedule. Considers tasks with the same action and the
    same schedule to be the same. Callers that wish to be able to delete the tasks they add should make sure to use unique
    `call` functions.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._scheduled: Dict[ScheduledTask, object] = {}
        self._stopped = False
        # Keep track of all tasks that are currently executing to be
        # able to cancel them when the scheduler is stopped.
        self._executing_tasks: Dict[TaskMethod, List[asyncio.Task[object]]] = defaultdict(list)
        # Keep track of tasks that should be awaited before the scheduler is stopped
        self._await_tasks: Dict[TaskMethod, List[asyncio.Task[object]]] = defaultdict(list)

    def _add_to_executing_tasks(self, action: TaskMethod, task: asyncio.Task[object], cancel_on_stop: bool = True) -> None:
        """
        Add task that is currently executing to `self._executing_tasks`.
        """
        if action in self._executing_tasks and self._executing_tasks[action]:
            LOGGER.warning("Multiple instances of background task %s are executing simultaneously", action.__name__)
        self._executing_tasks[action].append(task)
        if not cancel_on_stop:
            self._await_tasks[action].append(task)

    def _notify_done(self, action: TaskMethod, task: asyncio.Task[object]) -> None:
        """
        Called by the callback function of executing task when the task has finished executing.
        """

        def remove_action_from_task_dict(task_dict: Dict[TaskMethod, List[asyncio.Task[object]]]) -> None:
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
    ) -> ScheduledTask:
        """
        Add a new action

        :param action: A function to call periodically
        :param schedule: The schedule for this action
        :param cancel_on_stop: Cancel the task when the scheduler is stopped. If false, the coroutine will be awaited.
        """
        assert is_coroutine(action)

        if self._stopped:
            LOGGER.warning("Scheduling action '%s', while scheduler is stopped", action.__name__)
            return

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
            LOGGER.info("Calling %s" % action)
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
                    ihandle = IOLoop.current().call_later(schedule_typed.get_next_delay(), action_function)
                    self._scheduled[task_spec] = ihandle

        handle = IOLoop.current().call_later(schedule_typed.get_initial_delay(), action_function)
        self._scheduled[task_spec] = handle
        return task_spec

    @stable_api
    def remove(self, task: ScheduledTask) -> None:
        """
        Remove a scheduled action
        """
        if task in self._scheduled:
            IOLoop.current().remove_timeout(self._scheduled[task])
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
                IOLoop.current().remove_timeout(handle)
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


def datetime_utc_isoformat(timestamp: datetime.datetime, *, naive_utc: bool = False) -> str:
    """
    Returns a timestamp ISO string in implicit UTC.

    :param timestamp: The timestamp to get the ISO string for.
    :param naive_utc: Whether to interpret naive timestamps as UTC. By default naive timestamps are assumed to be in local time.
    """
    naive_utc_timestamp: datetime.datetime = (
        timestamp
        if timestamp.tzinfo is None and naive_utc
        else timestamp.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    )
    return naive_utc_timestamp.isoformat(timespec="microseconds")


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
def api_boundary_json_encoder(o: object) -> Union[ReturnTypes, "JSONSerializable"]:
    """
    A custom json encoder that knows how to encode other types commonly used by Inmanta from standard python libraries. This
    encoder is meant to be used for API boundaries.
    """
    if isinstance(o, datetime.datetime):
        # Accross API boundaries, all naive datetime instances are assumed UTC. Returns ISO timestamp implicitly in UTC.
        return datetime_utc_isoformat(o, naive_utc=True)

    return _custom_json_encoder(o)


def _custom_json_encoder(o: object) -> Union[ReturnTypes, "JSONSerializable"]:
    """
    A custom json encoder that knows how to encode other types commonly used by Inmanta from standard python libraries
    """
    if isinstance(o, JSONSerializable):
        return o.json_serialization_step()

    if isinstance(o, uuid.UUID):
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

    if isinstance(o, BaseModel):
        return o.dict(by_alias=True)

    LOGGER.error("Unable to serialize %s", o)
    raise TypeError(repr(o) + " is not JSON serializable")


def add_future(future: Union[Future, Coroutine]) -> Task:
    """
    Add a future to the ioloop to be handled, but do not require the result.
    """

    def handle_result(f: Task) -> None:
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


class TaskHandler(object):
    """
    This class provides a method to add a background task based on a coroutine. When the coroutine ends, any exceptions
    are reported. If stop is invoked, all background tasks are cancelled.
    """

    def __init__(self) -> None:
        super().__init__()
        self._background_tasks: Set[Task] = set()
        self._await_tasks: Set[Task] = set()
        self._stopped = False

    def is_stopped(self) -> bool:
        return self._stopped

    def is_running(self) -> bool:
        return not self._stopped

    def add_background_task(self, future: Union[Future, Coroutine], cancel_on_stop: bool = True) -> Task:
        """Add a background task to the event loop. When stop is called, the task is cancelled.

        :param future: The future or coroutine to run as background task.
        :param cancel_on_stop: Cancel the task when stop is called. If false, the coroutine is awaited.
        """
        if self._stopped:
            LOGGER.warning("Not adding background task because we are stopping.")
            raise StoppedException("A background tasks are not added to the event loop while stopping")

        task = ensure_future(future)

        def handle_result(task: Task) -> None:
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


def stable_depth_first(nodes: List[str], edges: Dict[str, List[str]]) -> List[str]:
    """Creates a linear sequence based on a set of "comes after" edges, same graph yields the same solution,
    independent of order given to this function"""
    nodes = sorted(nodes)
    edges = {k: sorted(v) for k, v in edges.items()}
    out = []

    def dfs(node: str, seen: Set[str] = set()) -> None:
        if node in out:
            return
        if node in seen:
            raise CycleException(node)
        try:
            if node in edges:
                for edge in edges[node]:
                    dfs(edge, seen | set(node))
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
        self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException], traceback: Optional[TracebackType]
    ) -> None:
        await self.parent.release(self.name)


class NamedLock:
    """Create fine grained locks"""

    def __init__(self) -> None:
        self._master_lock: Lock = Lock()
        self._named_locks: Dict[str, Lock] = {}
        self._named_locks_counters: Dict[str, int] = {}

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
