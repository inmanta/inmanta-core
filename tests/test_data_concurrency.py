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

"""
This module contains tests related to database concurrency issues. Whenever we fix a concurrency issue, be it performance
or deadlock related, a test should be added to ensure this occurence can not accidentally be introduced again.
"""

import asyncio
import datetime
import uuid
from collections import abc
from typing import Optional, Type, TypeVar

import asyncpg
import pytest

from inmanta import const, data
from inmanta.data import model
from inmanta.protocol.common import Result


def slowdown_queries(
    monkeypatch,
    *,
    cls: Type[data.BaseDocument] = data.BaseDocument,
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
@pytest.mark.parametrize("endpoint_to_use", ["resource_deploy_done", "resource_action_update"])
async def test_4889_deadlock_delete_resource_action_update(
    monkeypatch, server, client, environment: str, agent, endpoint_to_use: str
) -> None:
    """
    Verify that no deadlock exists between the delete of a version and the deploy_done/resource_action_update (background task)
    on that same version.
    """
    env_id: uuid.UUID = uuid.UUID(environment)

    version: int = 1
    await data.ConfigurationModel(
        environment=env_id,
        version=version,
        date=datetime.datetime.now().astimezone(),
        total=1,
        version_info={},
    ).insert()

    resource = model.ResourceVersionIdStr(f"std::File[agent1,path=/etc/file1],v={version}")
    await data.Resource.new(
        environment=env_id,
        status=const.ResourceState.available,
        resource_version_id=resource,
        attributes={"purge_on_delete": False, "purged": True, "requires": []},
    ).insert()

    # Add parameter for resource
    parameter_id = "test_param"
    result = await client.set_param(
        tid=env_id,
        id=parameter_id,
        source=const.ParameterSource.user,
        value="val",
        resource_id="std::File[agent1,path=/etc/file1]",
    )
    assert result.code == 200

    action_id = uuid.uuid4()
    result = await agent._client.resource_deploy_start(tid=env_id, rvid=resource, action_id=action_id)
    assert result.code == 200, result.result

    # artificially slow down queries to increase deadlock probability
    slowdown_queries(monkeypatch, cls=data.ResourceAction, query_funcs=["set_and_save"], delay=2)

    # request delete
    async def delete() -> Result:
        # Make sure insert starts first so it can acquire its first lock.
        await asyncio.sleep(1)
        return await client.delete_version(tid=environment, id=version)

    # request deploy_done
    now: datetime.datetime = datetime.datetime.now()
    deploy_done: abc.Awaitable[Result]
    if endpoint_to_use == "resource_deploy_done":
        deploy_done = agent._client.resource_deploy_done(
            tid=env_id,
            rvid=resource,
            action_id=action_id,
            status=const.ResourceState.deployed,
            messages=[
                model.LogLine(level=const.LogLevel.DEBUG, msg="message", kwargs={"keyword": 123, "none": None}, timestamp=now),
                model.LogLine(level=const.LogLevel.INFO, msg="test", kwargs={}, timestamp=now),
            ],
            changes={"attr1": model.AttributeStateChange(current=None, desired="test")},
            change=const.Change.purged,
        )
    elif endpoint_to_use == "resource_action_update":
        deploy_done = agent._client.resource_action_update(
            tid=env_id,
            resource_ids=[resource],
            action_id=action_id,
            action=const.ResourceAction.deploy,
            started=None,
            finished=now,
            status=const.ResourceState.deployed,
            messages=[
                data.LogLine.log(level=const.LogLevel.DEBUG, msg="message", timestamp=now, keyword=123, none=None),
                data.LogLine.log(level=const.LogLevel.INFO, msg="test", timestamp=now),
            ],
            changes={resource: {"attr1": model.AttributeStateChange(current=None, desired="test")}},
            change=const.Change.purged,
            send_events=True,
        )
    else:
        raise ValueError("Unknown value for endpoint_to_use parameter")

    # wait for both concurrent requests
    results: abc.Sequence[Result] = await asyncio.gather(deploy_done, delete())
    assert all(result.code == 200 for result in results), "\n".join(
        str(result.result) for result in results if result.code != 200
    )


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
    )
    await confmodel.insert()

    resource = model.ResourceVersionIdStr(f"mymod::myresource[myagent,id=1],v={version}")
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
