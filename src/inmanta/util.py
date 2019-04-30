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

import functools
import hashlib
import inspect
import itertools
import logging
import socket
import warnings
import uuid
import datetime
import enum
from asyncio import ensure_future, CancelledError
from logging import Logger

import pkg_resources
from pkg_resources import DistributionNotFound
from tornado.ioloop import IOLoop
from typing import Callable, Dict, Union, Tuple, List, Coroutine
from tornado import gen

from inmanta.types import JsonType

LOGGER = logging.getLogger(__name__)
SALT_SIZE = 16
HASH_ROUNDS = 100000


def memoize(obj):
    cache = obj.cache = {}

    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        if args not in cache:
            cache[args] = obj(*args, **kwargs)
        return cache[args]

    return memoizer


def get_compiler_version() -> str:
    try:
        return pkg_resources.get_distribution("inmanta").version
    except DistributionNotFound:
        LOGGER.error(
            "Could not find version number for the inmanta compiler."
            "Is inmanta installed? Use stuptools install or setuptools dev to install."
        )
        return None


def groupby(mylist, f):
    return itertools.groupby(sorted(mylist, key=f), f)


def hash_file(content: str) -> str:
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

    def add_action(self, action: Union[Callable, Coroutine], interval: float, initial_delay: float = None) -> None:
        """
            Add a new action

            :param action: A function to call periodically
            :param interval: The interval between execution of actions
            :param initial_delay: Delay to the first execution, defaults to interval
        """
        assert inspect.iscoroutinefunction(action) or gen.is_coroutine_function(action)

        if initial_delay is None:
            initial_delay = interval

        LOGGER.debug("Scheduling action %s every %d seconds with initial delay %d", action, interval, initial_delay)

        def action_function():
            LOGGER.info("Calling %s" % action)
            if action in self._scheduled:
                try:
                    ensure_future_and_handle_exception(
                        LOGGER,
                        "Uncaught exception while executing scheduled action",
                        action()
                    )
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
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.bind(('', 0))
    _addr, port = tcp.getsockname()
    tcp.close()
    return str(port)


def custom_json_encoder(o: object) -> Union[Dict, str, List]:
    """
        A custom json encoder that knows how to encode other types commonly used by Inmanta from standard python libraries
    """
    if isinstance(o, uuid.UUID):
        return str(o)

    if isinstance(o, datetime.datetime):
        return o.isoformat(timespec='microseconds')

    if hasattr(o, "to_dict"):
        return o.to_dict()

    if isinstance(o, enum.Enum):
        return o.name

    if isinstance(o, Exception):
        # Logs can push exceptions through RPC. Return a string representation.
        return str(o)

    LOGGER.error("Unable to serialize %s", o)
    raise TypeError(repr(o) + " is not JSON serializable")
