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

from inmanta import const, resources
from inmanta.agent import handler
from inmanta.agent.handler import CRUDHandler, HandlerContext, provider
from inmanta.export import unknown_parameters
from inmanta.resources import PurgeableResource, resource


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
    _WRITE_COUNT = defaultdict(lambda: defaultdict(int))
    _RELOAD_COUNT = defaultdict(lambda: defaultdict(int))
    _READ_COUNT = defaultdict(lambda: defaultdict(int))

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
