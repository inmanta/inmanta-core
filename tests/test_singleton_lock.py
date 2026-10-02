"""
Copyright 2026 Inmanta

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

import pytest

from inmanta import config, const
from inmanta.server.bootloader import InmantaBootloader
from inmanta.server.protocol import ServerStartFailure
from inmanta.server.services.databaseservice import DatabaseService, SingletonLock
from inmanta.signals import ProcessShutdown


def make_lock(postgres_db, database_name: str) -> SingletonLock:
    return SingletonLock(
        host=postgres_db.host,
        port=postgres_db.port,
        username=postgres_db.user,
        password=postgres_db.password,
        database=database_name,
    )


async def test_singleton_lock_conflict_and_handover(postgres_db, database_name):
    """
    While one instance holds the lock, a second one refuses immediately (wait_time=0). Once the first
    releases the lock, the second can take over.
    """
    lock1 = make_lock(postgres_db, database_name)
    lock2 = make_lock(postgres_db, database_name)
    try:
        await lock1.acquire(wait_time=0)

        with pytest.raises(ServerStartFailure) as exc_info:
            await lock2.acquire(wait_time=0)
        assert "already active" in str(exc_info.value)

        # Hand over: once the holder releases, the second instance can acquire.
        await lock1.stop()
        await lock2.acquire(wait_time=0)
    finally:
        await lock1.stop()
        await lock2.stop()


async def test_singleton_lock_waits_for_release(postgres_db, database_name):
    """
    With a positive wait_time, a second instance blocks until the holder releases the lock, then acquires it.
    """
    lock1 = make_lock(postgres_db, database_name)
    lock2 = make_lock(postgres_db, database_name)
    try:
        await lock1.acquire(wait_time=0)

        async def release_after_delay() -> None:
            await asyncio.sleep(1)
            await lock1.stop()

        releaser = asyncio.ensure_future(release_after_delay())
        start = asyncio.get_event_loop().time()
        # Should block until lock1 is released (~1s), then succeed well within wait_time.
        await lock2.acquire(wait_time=10)
        waited = asyncio.get_event_loop().time() - start
        await releaser
        # acquire must have blocked until lock1 released the lock, not returned immediately.
        assert waited >= 0.5
    finally:
        await lock1.stop()
        await lock2.stop()


async def test_singleton_lock_monitor_detects_loss(postgres_db, database_name):
    """
    When the lock connection drops while the server runs, the monitor invokes the lock-lost callback so the
    server can fail fast.
    """
    lock = make_lock(postgres_db, database_name)
    lock_lost = asyncio.Event()
    try:
        await lock.acquire(wait_time=0)
        lock.MONITOR_INTERVAL = 0.1  # speed up the test
        lock.start_monitor(on_lock_lost=lock_lost.set)

        # Simulate the dedicated connection dropping (e.g. a database failover).
        assert lock._connection is not None
        await lock._connection.close()

        await asyncio.wait_for(lock_lost.wait(), timeout=5)
    finally:
        await lock.stop()


async def test_server_refuses_to_start_when_lock_is_held(server_config, postgres_db, database_name, hard_clean_db):
    """
    A full server refuses to start (with singleton_lock_wait_time=0) when another instance already holds the
    singleton lock on the same database.
    """
    holder = make_lock(postgres_db, database_name)
    await holder.acquire(wait_time=0)
    config.Config.set("database", "singleton_lock_wait_time", "0")

    ibl = InmantaBootloader(configure_logging=True)
    try:
        with pytest.raises(ServerStartFailure) as exc_info:
            await ibl.start()
        assert "singleton lock" in str(exc_info.value)
    finally:
        await ibl.stop(timeout=20)
        await holder.stop()


@pytest.fixture
def signals_sent_to_this_process(monkeypatch) -> list[int]:
    """
    Prevent this process from actually signalling itself and return the list that collects the signals it sent.
    Also make sure that a shutdown request made by a test doesn't leak into other test cases.
    """
    monkeypatch.setattr(ProcessShutdown, "_shutdown_request", None)
    signals: list[int] = []

    def record_signal(pid: int, signal_number: int) -> None:
        assert pid == os.getpid()
        signals.append(signal_number)

    monkeypatch.setattr(os, "kill", record_signal)
    return signals


async def test_database_service_requests_shutdown_on_lock_lost(signals_sent_to_this_process: list[int]) -> None:
    """
    When the singleton lock is lost, the database service requests a shutdown of the process with the exit code
    that indicates that the singleton lock was lost. Once the server is shutting down, the loss of the lock is
    expected and no shutdown is requested anymore.
    """
    database_service = DatabaseService()

    database_service._on_singleton_lock_lost()

    assert signals_sent_to_this_process == [signal.SIGTERM]
    shutdown_request = ProcessShutdown.get_shutdown_request()
    assert shutdown_request is not None  # Make mypy happy
    assert shutdown_request.exit_code == const.EXIT_SINGLETON_LOCK_LOST
    assert "singleton lock" in shutdown_request.reason

    await database_service.prestop()
    database_service._on_singleton_lock_lost()

    assert signals_sent_to_this_process == [signal.SIGTERM]


def test_shutdown_request_keeps_first_request(signals_sent_to_this_process: list[int]) -> None:
    """
    The first shutdown request determines the exit code of the process and reset() clears the request.
    """
    assert ProcessShutdown.get_shutdown_request() is None

    ProcessShutdown.request_shutdown(exit_code=const.EXIT_SINGLETON_LOCK_LOST, reason="first")
    ProcessShutdown.request_shutdown(exit_code=const.EXIT_START_FAILED, reason="second")

    shutdown_request = ProcessShutdown.get_shutdown_request()
    assert shutdown_request is not None  # Make mypy happy
    assert shutdown_request.exit_code == const.EXIT_SINGLETON_LOCK_LOST
    assert shutdown_request.reason == "first"
    # Each request triggers the shutdown, also when another request was recorded before.
    assert signals_sent_to_this_process == [signal.SIGTERM, signal.SIGTERM]

    ProcessShutdown.reset()

    assert ProcessShutdown.get_shutdown_request() is None
