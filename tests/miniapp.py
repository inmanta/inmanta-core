"""
    Copyright 2019 Inmanta

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
import sys
import threading

from tornado import gen
from tornado.ioloop import IOLoop

import inmanta.const
from inmanta.app import setup_signal_handlers

inmanta.const.SHUTDOWN_GRACE_IOLOOP = 1
inmanta.const.SHUTDOWN_GRACE_HARD = 2


class MiniApp:
    def __init__(self):
        self.running = True
        self.lock = threading.Semaphore(0)

    @gen.coroutine
    def stop(self):
        print("STOP")
        self.running = False
        yield gen.sleep(0.2)

    @gen.coroutine
    def run(self):
        i = 0
        while self.running:
            yield asyncio.sleep(0.1)
            print(i)
            i += 1
        print("DONE")

    @gen.coroutine
    def bad_run(self):
        i = 0
        while self.running:
            print(i)
            i += 1
            yield asyncio.sleep(0.1)
            with self.lock:
                print(i)
        print("DONE")


if __name__ == "__main__":
    print("Start")
    a = MiniApp()
    setup_signal_handlers(a.stop)
    if "bad" in sys.argv:
        IOLoop.current().add_callback(a.bad_run)
    else:
        IOLoop.current().add_callback(a.run)
    IOLoop.current().start()
    print("SHUTDOWN COMPLETE")
    sys.exit(0)
