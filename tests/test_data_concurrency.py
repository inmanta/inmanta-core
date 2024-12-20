"""
    Copyright 2022 Inmanta

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

import inmanta.types
from utils import get_resource

"""
This module contains tests related to database concurrency issues. Whenever we fix a concurrency issue, be it performance
or deadlock related, a test should be added to ensure this occurence can not accidentally be introduced again.
"""

import asyncio
import datetime
import uuid
from collections import abc
from typing import Optional, TypeVar

import asyncpg
import pytest

from inmanta import const, data


def slowdown_queries(
    monkeypatch,
    *,
    cls: type[data.BaseDocument] = data.BaseDocument,
    query_funcs: Optional[abc.Collection[str]] = None,
    delay: float = 1,
) -> None:
    """
    Introduces an artificial delay after each query execution through data.Document in order to increase the likelyhood of
    concurrent transactions.

    :param cls: The class to slow down the methods for.
    :param query_funcs: The names of the methods to add a delay to.
    :param delay: The amount of seconds to delay.
    """
    query_funcs = (
        query_funcs
        if query_funcs
        else [
            "select_query",
            "_fetchval",
            "_fetch_int",
            "_fetchrow",
            "_fetch_query",
            "_execute_query",
            "insert_many",
        ]
    )

    F = TypeVar("F", bound=abc.Coroutine)

    def patch_method(method: F) -> F:
        clsmethod: bool = hasattr(method, "__func__")
        func: F = method.__func__ if clsmethod else method

        async def patched(*args, **kwargs) -> object:
            # call unbound original method with cls object bound to the patched method
            result: object = await func(*args, **kwargs)
            await asyncio.sleep(delay)
            return result

        return classmethod(patched) if clsmethod else patched

    for query_func in query_funcs:
        monkeypatch.setattr(cls, query_func, patch_method(getattr(cls, query_func)))


@pytest.mark.slowtest
async def test_4889_deadlock_delete_resource_action_insert(monkeypatch, environment: str) -> None:
    """
    Verify that no deadlock exists between the delete of a version and the insert of a ResourceAction for that same version.
    """
    env_id: uuid.UUID = uuid.UUID(environment)

    version: int = 1
    confmodel: data.ConfigurationModel = data.ConfigurationModel(
        environment=env_id,
        version=version,
        date=datetime.datetime.now().astimezone(),
        total=1,
        version_info={},
        is_suitable_for_partial_compiles=False,
    )
    await confmodel.insert()

    resource = inmanta.types.ResourceVersionIdStr(f"mymod::myresource[myagent,id=1],v={version}")
    await data.Resource.new(
        environment=env_id,
        status=const.ResourceState.available,
        resource_version_id=resource,
        attributes={},
    ).insert()

    # artificially slow down ResourceAction queries to increase deadlock probability
    slowdown_queries(monkeypatch, cls=data.ResourceAction, delay=1)

    insert: abc.Awaitable[None] = data.ResourceAction(
        environment=env_id,
        version=version,
        resource_version_ids=[resource],
        action_id=uuid.uuid4(),
        action=const.ResourceAction.deploy,
        started=datetime.datetime.now(),
    ).insert()

    async def delete() -> None:
        # Make sure insert starts first so it can acquire its first lock.
        await asyncio.sleep(0.5)
        await confmodel.delete_cascade()

    # Verify that this does not raise a deadlock exception. A failure on the insert is expected and acceptable if the delete
    # wins the race.
    try:
        await asyncio.gather(insert, delete())
    except asyncpg.ForeignKeyViolationError:
        pass


@pytest.mark.slowtest
@pytest.mark.parametrize("no_agent", [True])
async def test_release_version_concurrently(
    monkeypatch, server, client, environment: str, clienthelper, no_agent: bool
) -> None:
    version1 = await clienthelper.get_version()
    resource1 = get_resource(version1, key="test1")
    await clienthelper.put_version_simple(resources=[resource1], version=version1)

    version2 = await clienthelper.get_version()
    resource1 = get_resource(version2, key="test1")
    await clienthelper.put_version_simple(resources=[resource1], version=version2)

    slowdown_queries(monkeypatch)

    f1 = asyncio.create_task(client.release_version(environment, version2))
    f2 = asyncio.create_task(client.release_version(environment, version2))

    # get results
    r1 = await f1
    r2 = await f2

    # One should have made it, the other was too late
    assert {r1.code, r2.code} == {200, 409}

    # releasing an older version is always too late
    r3 = await client.release_version(environment, version1)
    assert r3.code == 409
