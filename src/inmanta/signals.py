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
from dataclasses import dataclass
from threading import Timer
from types import FrameType
from typing import Any, Callable, ClassVar, Coroutine, NoReturn, Optional

from tornado import gen
from tornado.ioloop import IOLoop
from tornado.util import TimeoutError

from inmanta import const
from inmanta.command import CLIException

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


@dataclass(frozen=True)
class ShutdownRequest:
    """
    A request to stop the current process because of a condition it cannot recover from.
    """

    exit_code: int
    reason: str

    def raise_cli_exception(self) -> NoReturn:
        """
        Raise the CLIException that makes the entry point of this process report the reason and the
        exit code of this shutdown request.
        """
        raise CLIException(self.reason, exitcode=self.exit_code)


class ProcessShutdown:
    """
    Process-wide handle to shut down the current process from within the ioloop.

    A component that hits a condition it cannot recover from calls request_shutdown(). The process then
    shuts down gracefully, exactly like it does on an operator-issued SIGTERM, but the entry point of the
    process reports the requested exit code instead of 0 once the ioloop has stopped. A shutdown requested by
    an operator does not pass through this class and therefore keeps exit code 0.

    This class relies on setup_signal_handlers() having installed the signal handlers of this process.
    """

    _shutdown_request: ClassVar[Optional[ShutdownRequest]] = None

    @classmethod
    def request_shutdown(cls, exit_code: int, reason: str) -> None:
        """
        Record the given exit code and reason, and request a graceful shutdown of this process. The first
        request wins: a later request doesn't overwrite the recorded exit code and reason.
        """
        if cls._shutdown_request is None:
            cls._shutdown_request = ShutdownRequest(exit_code=exit_code, reason=reason)
        os.kill(os.getpid(), signal.SIGTERM)

    @classmethod
    def get_shutdown_request(cls) -> Optional[ShutdownRequest]:
        """
        The shutdown that was requested for this process or None if no such request was made.
        """
        return cls._shutdown_request

    @classmethod
    def reset(cls) -> None:
        """
        Forget a previously recorded shutdown request. This method is intended for test cases that run
        a server in-process.
        """
        cls._shutdown_request = None


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
