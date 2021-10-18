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

import asyncio
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
from asyncio import CancelledError, Future, Task, ensure_future, gather, sleep
from logging import Logger
from typing import Callable, Coroutine, Dict, Iterator, List, Optional, Set, Tuple, TypeVar, Union

from tornado import gen
from tornado.ioloop import IOLoop

from inmanta import COMPILER_VERSION
from inmanta.stable_api import stable_api
from inmanta.types import JsonType, PrimitiveTypes, ReturnTypes

LOGGER = logging.getLogger(__name__)
SALT_SIZE = 16
HASH_ROUNDS = 100000

T = TypeVar("T")
S = TypeVar("S")


def memoize(obj):
    cache = obj.cache = {}

    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        if args not in cache:
            cache[args] = obj(*args, **kwargs)
        return cache[args]

    return memoizer


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


def is_call_ok(result: Union[int, Tuple[int, JsonType]]) -> bool:
    if isinstance(result, tuple):
        if len(result) == 2:
            code, reply = result
        else:
            raise Exception("Handlers for method call can only return a status code and a reply")

    else:
        code = result

    return code == 200


def ensure_future_and_handle_exception(logger: Logger, msg: str, action: Union[Coroutine]) -> None:
    """ Fire off a coroutine from the ioloop thread and log exceptions to the logger with the message """
    future = ensure_future(action)

    def handler(future):
        try:
            exc = future.exception()
            if exc is not None:
                logger.exception(msg, exc_info=exc)
        except CancelledError:
            pass

    future.add_done_callback(handler)


class Scheduler(object):
    """
    An event scheduler class
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._scheduled: Dict[Callable, object] = {}
        self._stopped = False

    def add_action(
        self,
        action: Union[Callable[[], None], Coroutine[None, None, None]],
        interval: float,
        initial_delay: Optional[float] = None,
    ) -> None:
        """
        Add a new action

        :param action: A function to call periodically
        :param interval: The interval between execution of actions
        :param initial_delay: Delay to the first execution, defaults to interval
        """
        assert inspect.iscoroutinefunction(action) or gen.is_coroutine_function(action)

        if self._stopped:
            LOGGER.warning("Scheduling action '%s', while scheduler is stopped", action.__name__)
            return

        if initial_delay is None:
            initial_delay = interval

        LOGGER.debug("Scheduling action %s every %d seconds with initial delay %d", action, interval, initial_delay)

        def action_function() -> None:
            LOGGER.info("Calling %s" % action)
            if action in self._scheduled:
                try:
                    ensure_future_and_handle_exception(LOGGER, "Uncaught exception while executing scheduled action", action())
                except Exception:
                    LOGGER.exception("Uncaught exception while executing scheduled action")
                finally:
                    # next iteration
                    ihandle = IOLoop.current().call_later(interval, action_function)
                    self._scheduled[action] = ihandle

        handle = IOLoop.current().call_later(initial_delay, action_function)
        self._scheduled[action] = handle

    def remove(self, action: Callable) -> None:
        """
        Remove a scheduled action
        """
        if action in self._scheduled:
            IOLoop.current().remove_timeout(self._scheduled[action])
            del self._scheduled[action]

    def stop(self) -> None:
        """
        Stop the scheduler
        """
        self._stopped = True
        try:
            # remove can still run during stop. That is why we loop until we get a keyerror == the dict is empty
            while True:
                action, handle = self._scheduled.popitem()
                IOLoop.current().remove_timeout(handle)
        except KeyError:
            pass

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
        return custom_json_encoder(o if o.tzinfo is not None else o.astimezone())

    return custom_json_encoder(o)


@stable_api
def api_boundary_json_encoder(o: object) -> Union[ReturnTypes, "JSONSerializable"]:
    """
    A custom json encoder that knows how to encode other types commonly used by Inmanta from standard python libraries. This
    encoder is meant to be used for API boundaries.
    """
    if isinstance(o, datetime.datetime):
        # Accross API boundaries, all naive datetime instances are assumed UTC. Returns ISO timestamp implicitly in UTC.
        return datetime_utc_isoformat(o, naive_utc=True)

    return custom_json_encoder(o)


def custom_json_encoder(o: object) -> Union[ReturnTypes, "JSONSerializable"]:
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


async def retry_limited(fun: Callable[[], bool], timeout: float, interval: float = 0.1) -> None:
    start = time.time()
    while time.time() - start < timeout and not fun():
        await sleep(interval)
    if not fun():
        raise asyncio.TimeoutError()


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
