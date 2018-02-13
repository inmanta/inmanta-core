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
