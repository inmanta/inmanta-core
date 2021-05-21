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
from collections import defaultdict

import pytest

from agent_server.conftest import get_agent, stop_agent
from inmanta import const, data, resources
from inmanta.agent import handler
from inmanta.agent.handler import CRUDHandler, HandlerContext, provider
from inmanta.export import unknown_parameters
from inmanta.loader import SourceInfo
from inmanta.resources import PurgeableResource, resource
from inmanta.types import JsonType
from utils import _wait_until_deployment_finishes


def reset_all_objects():
    resources.resource.reset()
    handler.Commander.reset()
    unknown_parameters.clear()


class Provider(CRUDHandler):
    def read_resource(self, ctx, current):
        self.read(current.id.get_agent_name(), current.key)
        assert current.value != const.UNKNOWN_STRING
        current.purged = not self.isset(current.id.get_agent_name(), current.key)

        if not current.purged:
            current.value = self.get(current.id.get_agent_name(), current.key)
        else:
            current.value = None

    def calculate_diff(self, ctx: HandlerContext, current: resources.Resource, desired: resources.Resource):
        diff = super().calculate_diff(ctx, current, desired)
        ctx.info("Diff was called")
        return diff

    def create_resource(self, ctx: HandlerContext, resource: PurgeableResource) -> None:
        self.touch(resource.id.get_agent_name(), resource.key)
        self.set(resource.id.get_agent_name(), resource.key, resource.value)
        ctx.set_created()

    def delete_resource(self, ctx: HandlerContext, resource: PurgeableResource) -> None:
        self.delete(resource.id.get_agent_name(), resource.key)
        ctx.set_purged()

    def update_resource(self, ctx: HandlerContext, changes: dict, resource: PurgeableResource) -> None:
        self.touch(resource.id.get_agent_name(), resource.key)
        self.set(resource.id.get_agent_name(), resource.key, resource.value)
        ctx.set_updated()

    _STATE = defaultdict(dict)
    _WRITE_COUNT = defaultdict(lambda: defaultdict(lambda: 0))
    _RELOAD_COUNT = defaultdict(lambda: defaultdict(lambda: 0))
    _READ_COUNT = defaultdict(lambda: defaultdict(lambda: 0))

    @classmethod
    def touch(cls, agent, key):
        cls._WRITE_COUNT[agent][key] += 1

    @classmethod
    def read(cls, agent, key):
        cls._READ_COUNT[agent][key] += 1

    @classmethod
    def set(cls, agent, key, value):
        cls._STATE[agent][key] = value

    @classmethod
    def get(cls, agent, key):
        if key in cls._STATE[agent]:
            return cls._STATE[agent][key]
        return None

    @classmethod
    def isset(cls, agent, key):
        return key in cls._STATE[agent]

    @classmethod
    def delete(cls, agent, key):
        if cls.isset(agent, key):
            del cls._STATE[agent][key]

    @classmethod
    def changecount(cls, agent, key):
        return cls._WRITE_COUNT[agent][key]

    @classmethod
    def readcount(cls, agent, key):
        return cls._READ_COUNT[agent][key]


def resource_container_a():
    reset_all_objects()

    @resource("__config__::Resource", agent="agent", id_attribute="key")
    class MyResource(PurgeableResource):
        """
        A file on a filesystem
        """

        fields = ("key", "value", "purged", "purge_on_delete")

    @provider("__config__::Resource", name="test_resource")
    class AProvider(Provider):
        pass

    return AProvider


def resource_container_b():
    reset_all_objects()

    @resource("__config__::Resource", agent="agent", id_attribute="uid")
    class MyResource(PurgeableResource):
        fields = ("uid", "key", "value", "purged", "purge_on_delete")

        def populate(self, fields: JsonType = None, force_fields: bool = False):
            if "uid" not in fields:
                # capture old format, cause by purge on delete
                fields["uid"] = None
            super().populate(fields, force_fields)

    @provider("__config__::Resource", name="test_resource")
    class BProvider(Provider):
        def read_resource(self, ctx, resource):
            if resource.uid is None:
                resource.purged = True
                return
            super().read_resource(ctx, resource)

        def create_resource(self, ctx: HandlerContext, resource: PurgeableResource) -> None:
            if resource.uid is None:
                return
            super().create_resource(ctx, resource)

        def delete_resource(self, ctx: HandlerContext, resource: PurgeableResource) -> None:
            if resource.uid is None:
                return
            super().delete_resource(ctx, resource)

        def update_resource(self, ctx: HandlerContext, changes: dict, resource: PurgeableResource) -> None:
            if resource.uid is None:
                return
            super().update_resource(ctx, resource)

    return BProvider


@pytest.mark.asyncio(timeout=150)
async def test_resource_evolution(server, client, environment, no_agent_backoff, snippetcompiler, monkeypatch, async_finalizer):

    provider = resource_container_a()

    agent = await get_agent(server, environment, "agent1")
    async_finalizer(agent.stop)

    # Enable purge_on_delete at the environment level
    result = await client.set_setting(tid=environment, id=data.PURGE_ON_DELETE, value=True)
    assert result.code == 200

    # override origin check
    monkeypatch.setattr(SourceInfo, "_get_module_name", lambda s: s.module_name)
    monkeypatch.setattr(SourceInfo, "get_siblings", lambda s: iter([s]))
    monkeypatch.setattr(SourceInfo, "requires", [])

    snippetcompiler.setup_for_snippet(
        """
    entity Resource extends std::PurgeableResource:
        string key
        string value
        string agent
    end

    implement Resource using std::none

    Resource(key="a", value="b", agent="agent1", purge_on_delete=true)
    """
    )

    version, _ = await snippetcompiler.do_export_and_deploy()
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version)

    await stop_agent(server, agent)

    assert provider.isset("agent1", "a")
    assert provider.changecount("agent1", "a") == 1

    provider = resource_container_b()

    agent = await get_agent(server, environment, "agent1")
    async_finalizer(agent.stop)

    snippetcompiler.setup_for_snippet(
        """
    entity Resource extends std::PurgeableResource:
        string key
        string value
        string agent
        string uid
    end

    implement Resource using std::none

    Resource(key="a", value="b", agent="agent1", uid="alpha", purge_on_delete=true)
    """
    )

    version, _ = await snippetcompiler.do_export_and_deploy()
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200
    assert result.result["model"]["total"] == 2  # purge_on_delete

    await _wait_until_deployment_finishes(client, environment, version)
    assert provider.isset("agent1", "a")
    assert provider.changecount("agent1", "a") == 1

    snippetcompiler.reset()
    version, _ = await snippetcompiler.do_export_and_deploy()
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200
    assert result.result["model"]["total"] == 1

    await _wait_until_deployment_finishes(client, environment, version)
    assert provider.isset("agent1", "a")
    assert provider.changecount("agent1", "a") == 1
