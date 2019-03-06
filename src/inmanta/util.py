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
import itertools
import logging
import warnings

import pkg_resources
from pkg_resources import DistributionNotFound
from tornado.ioloop import IOLoop
from typing import Callable, Dict, Union, Tuple, Any

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


def is_call_ok(result: Union[int, Tuple[int, Dict[str, Any]]]) -> bool:
    if isinstance(result, tuple):
        if len(result) == 2:
            code, reply = result
        else:
            raise Exception("Handlers for method call can only return a status code and a reply")

    else:
        code = result

    return code == 200


class Scheduler(object):
    """
        An event scheduler class
    """
    def __init__(self, name: str) -> None:
        self.name = name
        self._scheduled: Dict[Callable, object] = {}

    def add_action(self, action: Callable, interval: float, initial_delay: float = None) -> None:
        """
            Add a new action

            :param action: A function to call periodically
            :param interval: The interval between execution of actions
            :param initial_delay: Delay to the first execution, defaults to interval
        """
        if initial_delay is None:
            initial_delay = interval

        LOGGER.debug("Scheduling action %s every %d seconds with initial delay %d", action, interval, initial_delay)

        def action_function():
            LOGGER.info("Calling %s" % action)
            if action in self._scheduled:
                try:
                    action()
                except Exception:
                    LOGGER.exception("Uncaught exception while executing scheduled action")

                finally:
                    handle = IOLoop.current().call_later(interval, action_function)
                    self._scheduled[action] = handle

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
