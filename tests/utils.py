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
import time

from tornado import gen
from tornado.gen import sleep


@gen.coroutine
def retry_limited(fun, timeout):
    start = time.time()
    while time.time() - start < timeout and not fun():
        yield sleep(0.1)


UNKWN = object()


def assertEqualIsh(minimal, actual, sortby=[]):
    if isinstance(minimal, dict):
        for k in minimal.keys():
            assertEqualIsh(minimal[k], actual[k], sortby)
    elif isinstance(minimal, list):
        assert len(minimal) == len(actual), "list not equal %s != %s" % (minimal, actual)
        if len(sortby) > 0:
            def keyfunc(val):
                if not isinstance(val, dict):
                    return val
                key = [str(val[x]) for x in sortby if x in val]
                return '_'.join(key)
            actual = sorted(actual, key=keyfunc)
        for (m, a) in zip(minimal, actual):
            assertEqualIsh(m, a, sortby)
    elif minimal is UNKWN:
        return
    else:
        assert minimal == actual
