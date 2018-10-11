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
import logging

from pkg_resources import DistributionNotFound
import pkg_resources
import itertools
import hashlib


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


def get_compiler_version():
    try:
        return pkg_resources.get_distribution("inmanta").version
    except DistributionNotFound:
        LOGGER.error(
            "Could not find version number for the inmanta compiler." +
            "Is inmanta installed? Use stuptools install or setuptools dev to install.")
        return None


def groupby(mylist, f):
    return itertools.groupby(sorted(mylist, key=f), f)


def hash_file(content):
    """
        Create a hash from the given content
    """
    sha1sum = hashlib.new("sha1")
    sha1sum.update(content)

    return sha1sum.hexdigest()


def is_call_ok(result):
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

    def __init__(self, io_loop):
        self._scheduled = set()
        self._io_loop = io_loop

    def add_action(self, action, interval, initial_delay=None):
        """
            Add a new action

            :param action A function to call periodically
            :param interval The interval between execution of actions
            :param initial_delay Delay to the first execution, default to interval
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
                    self._io_loop.call_later(interval, action_function)

        self._io_loop.call_later(initial_delay, action_function)
        self._scheduled.add(action)

    def remove(self, action):
        """
            Remove a scheduled action
        """
        if action in self._scheduled:
            self._scheduled.remove(action)
