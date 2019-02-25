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
from tornado import gen
from inmanta.app import setup_signal_handlers
from tornado.ioloop import IOLoop


class MiniApp:

    def __init__(self):
        self.running = True

    @gen.coroutine
    def stop(self):
        print("STOP")
        self.running = False
        yield gen.sleep(0.2)

    @gen.coroutine
    def run(self):
        i = 0
        while self.running:
            yield gen.sleep(0.1)
            print(i)
            i += 1
        print("DONE")


if __name__ == '__main__':
    a = MiniApp()
    setup_signal_handlers(a.stop)
    IOLoop.current().add_callback(a.run)
    IOLoop.current().start()
