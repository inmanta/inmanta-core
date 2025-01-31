"""
Copyright 2024 Inmanta

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
import os
import signal
import sys
import threading
import traceback
from threading import Timer
from types import FrameType
from typing import Any, Callable, Coroutine, Optional

from tornado import gen
from tornado.ioloop import IOLoop
from tornado.util import TimeoutError

from inmanta import const

try:
    import rpdb
except ImportError:
    rpdb = None


def dump_threads() -> None:
    print("----- Thread Dump ----")
    for th in threading.enumerate():
        print("---", th)
        if th.ident:
            traceback.print_stack(sys._current_frames()[th.ident], file=sys.stdout)
        print()
    sys.stdout.flush()


async def dump_ioloop_running() -> None:
    # dump async IO
    print("----- Async IO tasks ----")
    for task in asyncio.all_tasks():
        print(task)
    print()
    sys.stdout.flush()


def context_dump(ioloop: IOLoop) -> None:
    dump_threads()
    if hasattr(asyncio, "all_tasks"):
        ioloop.add_callback_from_signal(dump_ioloop_running)


def setup_signal_handlers(shutdown_function: Callable[[], Coroutine[Any, Any, None]]) -> None:
    """
    Make sure that shutdown_function is called when a SIGTERM or a SIGINT interrupt occurs.

    :param shutdown_function: The function that contains the shutdown logic.
    """
    # ensure correct ioloop
    ioloop = IOLoop.current()

    def hard_exit() -> None:
        context_dump(ioloop)
        sys.stdout.flush()
        # Hard exit, not sys.exit
        # ensure shutdown when the ioloop is stuck
        os._exit(const.EXIT_HARD)

    def handle_signal(signum: signal.Signals, frame: Optional[FrameType]) -> None:
        # force shutdown, even when the ioloop is stuck
        # schedule off the loop
        t = Timer(const.SHUTDOWN_GRACE_HARD, hard_exit)
        t.daemon = True
        t.start()
        ioloop.add_callback_from_signal(safe_shutdown_wrapper, shutdown_function)

    def handle_signal_dump(signum: signal.Signals, frame: Optional[FrameType]) -> None:
        context_dump(ioloop)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGUSR1, handle_signal_dump)
    if rpdb:
        rpdb.handle_trap()


def safe_shutdown(ioloop: IOLoop, shutdown_function: Callable[[], None]) -> None:
    def hard_exit() -> None:
        context_dump(ioloop)
        sys.stdout.flush()
        # Hard exit, not sys.exit
        # ensure shutdown when the ioloop is stuck
        os._exit(const.EXIT_HARD)

    # force shutdown, even when the ioloop is stuck
    # schedule off the loop
    t = Timer(const.SHUTDOWN_GRACE_HARD, hard_exit)
    t.daemon = True
    t.start()
    ioloop.add_callback(safe_shutdown_wrapper, shutdown_function)


async def safe_shutdown_wrapper(shutdown_function: Callable[[], Coroutine[Any, Any, None]]) -> None:
    """
    Wait 10 seconds to gracefully shutdown the instance.
    Afterwards stop the IOLoop
    Wait for 3 seconds to force stop
    """
    future = shutdown_function()
    try:
        timeout = IOLoop.current().time() + const.SHUTDOWN_GRACE_IOLOOP
        await gen.with_timeout(timeout, future)
    except TimeoutError:
        pass
    finally:
        IOLoop.current().stop()
