"""
    Copyright 2018 Inmanta

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
from tornado.locks import _ReleasingContextManager
from tornado.concurrent import Future
from tornado import gen
from bisect import insort


class WeightedWaiter(object):

    def __init__(self, future, prio):
        self.future = future
        self.prio = prio

    def __lt__(self, other):
        return self.prio < other.prio

    def __le__(self, other):
        return self.prio <= other.prio

    def __eq__(self, other):
        return self.prio == other.prio

    def __ne__(self, other):
        return self.prio != other.prio

    def __gt__(self, other):
        return self.prio > other.prio

    def __ge__(self, other):
        return self.prio >= other.prio


class PrioritySemaphore(object):
    """Based on tornado Semaphore"""

    def __init__(self, count=1):
        self._count = count
        self._waiters = []

    def release(self):
        self._count += 1
        while self._waiters:
            waiter = self._waiters.pop(0).future
            if not waiter.done():
                self._count -= 1
                waiter.set_result(_ReleasingContextManager(self))
                break

    def acquire(self, priority=1000):
        waiter = Future()
        if self._count > 0:
            self._count -= 1
            waiter.set_result(_ReleasingContextManager(self))
        else:
            insort(self._waiters, WeightedWaiter(waiter, priority))
        return waiter

    def __enter__(self):
        raise RuntimeError(
            "Use Semaphore like 'with (yield semaphore.acquire())', not like"
            " 'with semaphore'")

    __exit__ = __enter__

    @gen.coroutine
    def __aenter__(self):
        yield self.acquire()

    @gen.coroutine
    def __aexit__(self, typ, value, tb):
        self.release()
