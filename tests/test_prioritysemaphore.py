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
import pytest
from inmanta.agent.util import PrioritySemaphore
from tornado import gen


@pytest.mark.gen_test(timeout=1)
def test_prio_semaphore():
    sema = PrioritySemaphore(0)
    collector = []

    @gen.coroutine
    def worker(mid):
        with (yield sema.acquire(mid)):
            collector.append(mid)

    prios = [5, 4, 2, 3, 1, 6]

    all = [worker(x) for x in prios]

    sema.release()

    yield all

    assert collector == [1, 2, 3, 4, 5, 6]
