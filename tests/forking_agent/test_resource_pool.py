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
import itertools

from inmanta.agent.resourcepool import PoolManager, PoolMember, SingleIdPoolManager, TimeBasedPoolManager


async def test_resource_pool():
    """Test basic functionality of the resource pool:
    - produce members
    - cache them
    - track membership if members are closed
    """

    counter = itertools.count()

    class SimplePoolMember(PoolMember[str]):

        def __init__(self, my_id: str) -> None:
            super().__init__(my_id)
            self.count = next(counter)

        def __repr__(self):
            return self.id + str(self.count)

        async def request_shutdown(self) -> None:
            await super().request_shutdown()
            await self.set_shutdown()

    class SimplePoolManager(SingleIdPoolManager[str, SimplePoolMember]):
        async def create_member(self, executor_id: str) -> SimplePoolMember:
            return SimplePoolMember(my_id=executor_id)

    manager = SimplePoolManager()
    await manager.start()

    a1 = await manager.get("a")
    a2 = await manager.get("a")
    b = await manager.get("b")

    assert a1.count == a2.count
    assert a1.id != b.id

    await a2.request_shutdown()

    a3 = await manager.get("a")
    assert a1.count != a3.count

    await a1.request_shutdown()

    await a3.request_shutdown()


async def test_timed_resource_pool():
    """Test time based expiry"""

    counter = itertools.count()

    class SimplePoolMember(PoolMember[str]):

        def __init__(self, my_id: str) -> None:
            super().__init__(my_id)
            self.count = next(counter)
            # wait point for shutdown!
            self.anchor = asyncio.Event()

        def __repr__(self):
            return self.id + str(self.count)

        async def request_shutdown(self) -> None:
            await super().request_shutdown()
            await self.set_shutdown()
            self.anchor.set()

    class SimplePoolManager(TimeBasedPoolManager[str, str, SimplePoolMember]):
        async def create_member(self, executor_id: str) -> SimplePoolMember:
            return SimplePoolMember(my_id=executor_id)

        def _id_to_internal(self, ext_id: str) -> str:
            return ext_id

    # Very short expirey
    manager = SimplePoolManager(0.02)
    await manager.start()

    a1 = await manager.get("a")
    a1_2 = await manager.get("a")
    b1 = await manager.get("b")

    # Caching works
    assert a1.count == a1_2.count
    assert b1.id != a1.id

    # wait for the youngest to be down
    await asyncio.wait_for(b1.anchor.wait(), 2)
    # all dead
    assert not a1.running
    assert not b1.running
    assert not manager.pool


async def test_resource_pool_stacking():
    """
    Test the specific setup needed for the forking executor, as described in that file

    Simplified to not have any of the underlying complexity, just test that the pooling works
    """
    counter = itertools.count()

    class SimplePoolMember(PoolMember[str]):

        def __init__(self, my_id: str) -> None:
            super().__init__(my_id)
            self.count = next(counter)

        def __repr__(self):
            return self.id + str(self.count)

        async def request_shutdown(self) -> None:
            await super().request_shutdown()
            await self.set_shutdown()

        def _id_to_internal(self, ext_id: str) -> str:
            return ext_id

    dcounter = itertools.count()

    class DoublePoolManager(PoolManager[str, str, SimplePoolMember], PoolMember[str]):
        async def create_member(self, executor_id: str) -> SimplePoolMember:
            return SimplePoolMember(my_id=executor_id)

        def __init__(self, my_id: str) -> None:
            PoolMember.__init__(self, my_id)
            PoolManager.__init__(self)
            self.count = next(dcounter)

        def _id_to_internal(self, ext_id: str) -> str:
            return ext_id

        def __repr__(self):
            return "M" + self.id + str(self.count)

        async def request_shutdown(self) -> None:
            await PoolMember.request_shutdown(self)
            await PoolManager.request_shutdown(self)
            await self.set_shutdown()

        async def notify_member_shutdown(self, pool_member: SimplePoolMember) -> bool:
            await super().notify_member_shutdown(pool_member)
            if len(self.pool) == 0:
                await self.request_shutdown()

    class UpperManager(PoolManager[str, str, DoublePoolManager]):

        def _id_to_internal(self, ext_id: str) -> str:
            return ext_id

        async def create_member(self, executor_id: str) -> SimplePoolMember:
            dpm = DoublePoolManager(my_id=executor_id)
            await dpm.start()
            return dpm

    um = UpperManager()

    await um.start()

    a1 = await um.get("a")
    a1_2 = await um.get("a")
    b1 = await um.get("b")

    assert a1.count == a1_2.count
    assert b1.id != a1.id

    a1_a1 = await a1.get("A")
    a1_a1_2 = await a1.get("A")
    assert a1_a1.count == a1_a1_2.count

    b1_a1 = await b1.get("A")
    assert a1_a1.count != b1_a1.count

    class OverManager(PoolManager[str, str, SimplePoolMember]):

        def __init__(self):
            super().__init__()
            self.sub_manager = UpperManager()

        async def start(self) -> None:
            await super().start()
            await self.sub_manager.start()

        async def create_member(self, executor_id: str) -> SimplePoolMember:
            pre = executor_id.split(".")[0]
            producer = await self.sub_manager.get(pre)
            return await producer.get(executor_id)

        def _id_to_internal(self, ext_id: str) -> str:
            return ext_id

    om = OverManager()
    await om.start()
    aa = await om.get("a.a")
    aa2 = await om.get("a.a")
    assert aa.count == aa2.count

    await aa.request_shutdown()

    assert len(om.pool) == 0
    assert len(om.sub_manager.pool) == 0
