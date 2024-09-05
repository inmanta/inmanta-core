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

import pytest

from inmanta.util.async_lru import async_lru_cache


async def test_async_lru():
    hit_count = []

    @async_lru_cache
    async def coro(arg: str) -> str:
        hit_count.append(arg)
        await asyncio.sleep(0.01)
        return arg

    async def work(arg: str) -> str:
        return await coro("A")

    a_fut_1 = asyncio.create_task(work("A"))
    a_fut_2 = asyncio.create_task(work("A"))
    assert "A" == await a_fut_1
    assert len(hit_count) == 1
    assert "A" == await a_fut_2
    assert len(hit_count) == 1
    assert "A" == await coro("A")
    assert "B" == await coro("B")
    assert len(hit_count) == 2


async def test_async_lru_raising():
    hit_count = []

    @async_lru_cache
    async def coro(arg: str) -> str:
        hit_count.append(arg)
        await asyncio.sleep(0.01)
        raise Exception(arg)

    async def work(arg: str) -> str:
        return await coro(arg)

    a_fut_1 = asyncio.create_task(work("A"))
    a_fut_2 = asyncio.create_task(work("A"))
    with pytest.raises(Exception, match="A"):
        await a_fut_1
    with pytest.raises(Exception, match="A"):
        await a_fut_2
    assert len(hit_count) == 1

    with pytest.raises(Exception, match="A"):
        await coro("A")

    with pytest.raises(Exception, match="B"):
        await coro("B")
    assert len(hit_count) == 2
