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

import pytest

from inmanta import config
from inmanta.server.bootloader import InmantaBootloader
from inmanta.server.protocol import ServerStartFailure
from inmanta.server.services.databaseservice import SingletonLock


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
        # Should block for ~1s until lock1 is released, then succeed well within wait_time.
        await lock2.acquire(wait_time=10)
        # acquire only returned because lock1 was released, so the releaser must already be done.
        assert releaser.done()
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
